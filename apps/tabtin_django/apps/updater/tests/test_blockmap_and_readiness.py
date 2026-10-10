"""blockmap 资产托管 + 发布就绪新检查的回归。

运行方式：
    cd apps/tabtin_django
    ./venv/bin/python manage.py test apps.updater.tests.test_blockmap_and_readiness \\
        --settings=tabtin.settings_updater_progress_test
"""
from unittest.mock import patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings

from apps.updater.models import AppRelease
from apps.updater.services.asset_service import ReleaseAssetService
from apps.updater.services.readiness_service import (
    ReleaseReadinessResult,
    ReleaseReadinessService,
)


class _FakeOSSService:
    def __init__(self):
        self.config = {
            "bucket_name": "tabtin-updater",
            "endpoint": "oss.example.com",
            "access_mode": "public-read",
            "cdn_domain": "cdn.example.com",
        }
        self.existing_keys: set[str] = set()

    def generate_presigned_url(self, object_key, expiration=900, method="PUT", content_type=None):
        return f"https://presign.example.com/{object_key}"

    def build_access_url(self, object_key):
        return f"https://tabtin-updater.oss.example.com/{object_key}"

    def build_cdn_url(self, object_key):
        return f"https://cdn.example.com/{object_key}"

    def file_exists(self, object_key):
        return object_key in self.existing_keys

    def get_file_info(self, object_key):
        return {"success": True, "data": {"content_length": 128}}


def _make_release(**overrides) -> AppRelease:
    fields = dict(
        version="1.2.0",
        platform="mac",
        arch="arm64",
        channel="stable",
        release_notes="notes",
    )
    fields.update(overrides)
    return AppRelease.objects.create(**fields)


class BlockmapAssetServiceTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.fake_oss = _FakeOSSService()
        patcher = patch(
            "apps.updater.services.asset_service.get_updater_oss_service",
            return_value=self.fake_oss,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_package_upload_uses_canonical_short_file_name(self):
        service = ReleaseAssetService()

        win = _make_release(version="0.7.127", platform="win", arch="x64", channel="beta")
        win_intent = service.create_upload_intent(
            win,
            asset_type="package",
            file_name="SnSworker-beta-0.7.127-x64-plain-upload-quick-260805-setup.exe",
            file_size=1024,
        )
        self.assertEqual(win_intent.expected_file_name, "SnSworker-0.7.127-windows.exe")
        self.assertEqual(
            win_intent.object_key,
            "desktop-updates/beta/win/x64/0.7.127/SnSworker-0.7.127-windows.exe",
        )

        mac = _make_release(version="1.0.0", platform="mac", arch="arm64", channel="stable")
        zip_intent = service.create_upload_intent(
            mac,
            asset_type="package",
            file_name="SnSworker-stable-1.0.0-arm64-plain-upload-release-260727-mac.zip",
            file_size=2048,
        )
        self.assertEqual(zip_intent.expected_file_name, "SnSworker-1.0.0-arm64-mac.zip")

        dmg_intent = service.create_upload_intent(
            mac,
            asset_type="website_installer",
            file_name="SnSworker-stable-1.0.0-arm64-plain-upload-release-260727.dmg",
            file_size=4096,
        )
        self.assertEqual(dmg_intent.expected_file_name, "SnSworker-1.0.0-arm64.dmg")

    def test_blockmap_intent_requires_uploaded_package(self):
        release = _make_release()
        service = ReleaseAssetService()
        with self.assertRaisesMessage(ValueError, "请先上传安装包"):
            service.create_upload_intent(
                release,
                asset_type="blockmap",
                file_name="SnSworker-1.2.0-arm64-mac.zip.blockmap",
                file_size=128,
            )

    def test_blockmap_file_name_follows_registered_package(self):
        release = _make_release(
            file_url=(
                "https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/"
                "SnSworker-1.2.0-arm64-mac.zip"
            ),
        )
        service = ReleaseAssetService()
        intent = service.create_upload_intent(
            release,
            asset_type="blockmap",
            # 本地文件名故意不一致：服务端必须按已登记安装包名推导
            file_name="whatever.blockmap",
            file_size=128,
        )
        self.assertEqual(intent.expected_file_name, "SnSworker-1.2.0-arm64-mac.zip.blockmap")
        self.assertEqual(
            intent.object_key,
            "desktop-updates/stable/mac/arm64/1.2.0/SnSworker-1.2.0-arm64-mac.zip.blockmap",
        )

    def test_blockmap_complete_does_not_touch_release_fields(self):
        file_url = (
            "https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/"
            "SnSworker-1.2.0-arm64-mac.zip"
        )
        release = _make_release(file_url=file_url, file_size=1024, checksum_sha256="a" * 64)
        object_key = (
            "desktop-updates/stable/mac/arm64/1.2.0/SnSworker-1.2.0-arm64-mac.zip.blockmap"
        )
        self.fake_oss.existing_keys.add(object_key)

        service = ReleaseAssetService()
        result = service.complete_upload(
            release,
            asset_type="blockmap",
            object_key=object_key,
            file_name="SnSworker-1.2.0-arm64-mac.zip.blockmap",
            file_size=128,
            content_type="application/octet-stream",
        )

        self.assertEqual(result.asset_type, "blockmap")
        release.refresh_from_db()
        self.assertEqual(release.file_url, file_url)
        self.assertEqual(release.file_size, 1024)
        # blockmap 不应改写 feed_url（与安装包同目录，无需回填）
        self.assertEqual(release.feed_url, "")


class WebsiteInstallerAssetServiceTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.fake_oss = _FakeOSSService()
        patcher = patch(
            "apps.updater.services.asset_service.get_updater_oss_service",
            return_value=self.fake_oss,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_website_installer_rejects_zip_on_mac(self):
        release = _make_release()
        service = ReleaseAssetService()
        with self.assertRaisesMessage(ValueError, "官网安装包请上传 .dmg"):
            service.create_upload_intent(
                release,
                asset_type="website_installer",
                file_name="SnSworker-1.2.0-arm64-mac.zip",
                file_size=1024,
            )

    def test_website_installer_complete_sets_website_file_url_only(self):
        file_url = (
            "https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/"
            "SnSworker-1.2.0-arm64-mac.zip"
        )
        release = _make_release(file_url=file_url, file_size=2048, checksum_sha256="b" * 64)
        object_key = "desktop-updates/stable/mac/arm64/1.2.0/SnSworker-1.2.0-arm64.dmg"
        self.fake_oss.existing_keys.add(object_key)

        service = ReleaseAssetService()
        result = service.complete_upload(
            release,
            asset_type="website_installer",
            object_key=object_key,
            file_name="SnSworker-1.2.0-arm64.dmg",
            file_size=4096,
            content_type="application/x-apple-diskimage",
        )

        self.assertEqual(result.asset_type, "website_installer")
        self.assertFalse(result.manifest_generated)
        release.refresh_from_db()
        self.assertEqual(release.file_url, file_url)
        self.assertEqual(release.website_file_url, result.public_url)
        self.assertEqual(release.get_download_file_url(), release.website_file_url)


class WebsiteInstallerReadinessTests(SimpleTestCase):
    def test_mac_stable_missing_website_dmg_is_blocking(self):
        release = AppRelease(
            version="1.2.0",
            platform="mac",
            arch="arm64",
            channel="stable",
            file_url="https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip",
            release_notes="notes",
        )
        result = ReleaseReadinessService().check_release(release)
        codes = {issue.code for issue in result.issues}
        self.assertIn("website_file_url_missing", codes)
        self.assertEqual(result.status, "blocked")

    def test_stable_website_installer_on_preprod_cdn_is_blocking(self):
        release = AppRelease(
            version="1.2.0",
            platform="mac",
            arch="arm64",
            channel="stable",
            file_url="https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip",
            website_file_url=(
                "https://cdn-dev-preprod.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.dmg"
            ),
            release_notes="notes",
        )
        result = ReleaseReadinessResult(manifest_url="", manifest_file="")

        ReleaseReadinessService()._check_stable_distribution_url(
            release, release.get_download_file_url(), result
        )

        self.assertEqual(result.issues[0].code, "stable_asset_on_non_production_domain")


@override_settings(IS_COMMUNITY_EDITION=False)
class ReadinessFeedWhitelistTests(SimpleTestCase):
    """与桌面端 isAllowedFeedUrl 口径对齐的发布前门禁（SaaS 语义）。

    显式锁定 IS_COMMUNITY_EDITION=False：社区容器（TABTIN_EDITION=community）
    里跑测试时也保持 SaaS 判定，语义不受运行环境影响。
    """

    def _check(self, file_url: str) -> ReleaseReadinessResult:
        release = AppRelease(
            version="1.2.0",
            platform="mac",
            arch="arm64",
            channel="stable",
            file_url=file_url,
            release_notes="notes",
        )
        result = ReleaseReadinessResult(manifest_url="", manifest_file="")
        ReleaseReadinessService()._check_feed_url_client_whitelist(release, result)
        return result

    def test_oss_direct_domain_is_blocked(self):
        result = self._check(
            "https://example-assets.oss-cn-wuhan-lr.aliyuncs.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip"
        )
        self.assertEqual(result.issues[0].code, "feed_url_rejected_by_client")
        self.assertEqual(result.issues[0].severity, "error")

    def test_http_scheme_is_blocked(self):
        result = self._check("http://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip")
        self.assertEqual(result.issues[0].code, "feed_url_rejected_by_client")

    def test_tabtin_cdn_domain_passes(self):
        result = self._check("https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip")
        self.assertEqual(result.issues, [])

    def test_stable_release_on_preprod_cdn_warns_without_blocking(self):
        result = self._check(
            "https://cdn-dev-preprod.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip"
        )
        self.assertEqual(result.issues[0].code, "stable_asset_on_non_production_domain")
        self.assertEqual(result.issues[0].severity, "warning")
        self.assertEqual(result.blocking_issue_count, 0)


class ReadinessFeedWhitelistCommunityEditionTests(SimpleTestCase):
    """社区自建部署（community edition）的 feed 门禁。

    与桌面端 isAllowedFeedUrl 的 community 分支对齐：community 打包形态按
    构建期注入的更新源 origin 精确匹配、允许 HTTP（安装包完整性由 latest.yml
    内嵌 sha512 强校验兜底）；服务端门禁仅拦协议非法/内嵌凭据/metadata 主机。
    """

    def _check(self, file_url: str) -> ReleaseReadinessResult:
        release = AppRelease(
            version="1.2.0",
            platform="win",
            arch="x64",
            channel="stable",
            file_url=file_url,
            release_notes="notes",
        )
        result = ReleaseReadinessResult(manifest_url="", manifest_file="")
        ReleaseReadinessService()._check_feed_url_client_whitelist(release, result)
        return result

    @override_settings(IS_COMMUNITY_EDITION=True)
    def test_community_http_ip_port_feed_passes(self):
        result = self._check(
            "http://221.237.179.2:13490/desktop-updates/snsworker-1.2.0-x64.exe"
        )
        self.assertEqual(result.issues, [])

    @override_settings(IS_COMMUNITY_EDITION=True)
    def test_community_https_feed_passes(self):
        result = self._check(
            "https://updates.internal.example.com/desktop-updates/a.exe"
        )
        self.assertEqual(result.issues, [])

    @override_settings(IS_COMMUNITY_EDITION=True)
    def test_community_feed_with_credentials_blocked(self):
        result = self._check(
            "http://user:pass@221.237.179.2:13490/desktop-updates/a.exe"
        )
        self.assertEqual(result.issues[0].code, "feed_url_rejected_by_client")
        self.assertEqual(result.issues[0].severity, "error")

    @override_settings(IS_COMMUNITY_EDITION=True)
    def test_community_metadata_host_blocked(self):
        result = self._check("http://169.254.169.254/desktop-updates/a.exe")
        self.assertEqual(result.issues[0].code, "feed_url_rejected_by_client")

    @override_settings(IS_COMMUNITY_EDITION=True)
    def test_community_non_http_scheme_blocked(self):
        result = self._check("ftp://221.237.179.2:13490/desktop-updates/a.exe")
        self.assertEqual(result.issues[0].code, "feed_url_rejected_by_client")

    @override_settings(IS_COMMUNITY_EDITION=False)
    def test_saas_edition_still_enforces_https_domain_whitelist(self):
        # SaaS 语义不变：http + 任意域名仍被拒（客户端会回落默认 feed）
        result = self._check("http://cdn.example.com/desktop-updates/a.exe")
        self.assertEqual(result.issues[0].code, "feed_url_rejected_by_client")
        self.assertEqual(result.issues[0].severity, "error")


class ProbeUrlRewriteTests(SimpleTestCase):
    """就绪检查探测 URL 的内网改写（hairpin 回环兜底）。"""

    _MAP = {"http://221.237.179.2:13490": "http://web:80"}

    @override_settings(UPDATER_FEED_PROBE_REWRITE_MAP=_MAP)
    def test_public_origin_rewritten_to_internal(self):
        url = "http://221.237.179.2:13490/desktop-updates/latest.yml"
        self.assertEqual(
            ReleaseReadinessService()._probe_url(url),
            "http://web:80/desktop-updates/latest.yml",
        )

    @override_settings(UPDATER_FEED_PROBE_REWRITE_MAP=_MAP)
    def test_query_string_preserved(self):
        url = "http://221.237.179.2:13490/desktop-updates/a.exe?token=x"
        self.assertEqual(
            ReleaseReadinessService()._probe_url(url),
            "http://web:80/desktop-updates/a.exe?token=x",
        )

    @override_settings(UPDATER_FEED_PROBE_REWRITE_MAP=_MAP)
    def test_other_origin_untouched(self):
        url = "https://cdn.example.com/releases/a.exe"
        self.assertEqual(ReleaseReadinessService()._probe_url(url), url)

    @override_settings(UPDATER_FEED_PROBE_REWRITE_MAP={})
    def test_disabled_when_map_empty(self):
        url = "http://221.237.179.2:13490/desktop-updates/latest.yml"
        self.assertEqual(ReleaseReadinessService()._probe_url(url), url)


class ReadinessBlockmapProbeTests(SimpleTestCase):
    def _probe(self, head_side_effect=None, status_code=200) -> ReleaseReadinessResult:
        release = AppRelease(
            version="1.2.0",
            platform="mac",
            arch="arm64",
            channel="stable",
            file_url="https://cdn.example.com/desktop-updates/stable/mac/arm64/1.2.0/a.zip",
            release_notes="notes",
        )
        result = ReleaseReadinessResult(manifest_url="", manifest_file="")

        class _Resp:
            def __init__(self, code):
                self.status_code = code

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.HTTPError(f"{self.status_code}")

            def close(self):
                pass

        with patch("apps.updater.services.readiness_service.requests.head") as head_mock:
            if head_side_effect is not None:
                head_mock.side_effect = head_side_effect
            else:
                head_mock.return_value = _Resp(status_code)
            ReleaseReadinessService()._probe_blockmap(release, result)
        return result

    def test_missing_blockmap_warns(self):
        result = self._probe(status_code=404)
        self.assertEqual(result.issues[0].code, "blockmap_missing")
        self.assertEqual(result.issues[0].severity, "warning")

    def test_network_error_warns(self):
        result = self._probe(head_side_effect=requests.ConnectionError("boom"))
        self.assertEqual(result.issues[0].code, "blockmap_missing")

    def test_existing_blockmap_passes(self):
        result = self._probe(status_code=200)
        self.assertEqual(result.issues, [])
