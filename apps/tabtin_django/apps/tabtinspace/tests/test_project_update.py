"""Project 设置更新（PUT /context/projects/{id}）契约测试。

覆盖：编辑者权限校验、名称非空校验、CAS 乐观并发控制（expected_version）、
config_version 自增与路由序列化输出。
"""
from __future__ import annotations

import json

from django.http import JsonResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.tabtinspace.models import OrganizationMember, Project, ProjectMembership
from apps.tabtinspace.routers.project import ProjectUpdateIn, update_project
from apps.tabtinspace.services.base import ServiceError
from apps.tabtinspace.services.project_service import ProjectService
from apps.tabtinspace.tests.fixtures import create_test_organization, create_test_user


@override_settings(TABTIN_ENABLE_PROJECTS=True)
class ProjectUpdateTests(TestCase):
    """Project 名称/描述更新：编辑者权限 + CAS 并发控制。"""

    databases = {"default", "postgresql"}

    def setUp(self) -> None:
        self.rf = RequestFactory()
        self.owner = create_test_user(prefix="proj_upd_owner")
        self.viewer = create_test_user(prefix="proj_upd_viewer")
        self.organization = create_test_organization(owner=self.owner, prefix="proj_upd")
        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.viewer,
            role="viewer",
        )
        self.project = Project.objects.create(
            organization=self.organization,
            name="发布准备",
            description="发布前准备工作",
            status=Project.Status.ACTIVE,
            config_version=1,
        )
        ProjectMembership.objects.create(
            project=self.project,
            user=self.owner,
            role="owner",
            is_active=True,
            status=ProjectMembership.Status.ACTIVE,
        )

    def _call_update(self, user, payload: dict, project_id=None):
        pid = project_id or self.project.id
        request = self.rf.put(
            f"/api/context/projects/{pid}",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.auth = user
        return update_project(request, pid, ProjectUpdateIn(**payload))

    def _error_body(self, resp) -> dict:
        self.assertIsInstance(resp, JsonResponse)
        return json.loads(resp.content.decode())

    def _refresh(self) -> Project:
        return Project.objects.get(id=self.project.id)

    # ── service 层 ──

    def test_service_updates_name_description_and_bumps_version(self) -> None:
        updated = ProjectService(user=self.owner).update_project(
            project_id=self.project.id,
            name="  发布准备更新  ",
            description="  更新后的说明  ",
            expected_version=1,
        )
        self.assertEqual(updated.name, "发布准备更新")
        self.assertEqual(updated.description, "更新后的说明")
        self.assertEqual(updated.config_version, 2)

        fresh = self._refresh()
        self.assertEqual(fresh.name, "发布准备更新")
        self.assertEqual(fresh.config_version, 2)

    def test_service_without_expected_version_skips_cas(self) -> None:
        updated = ProjectService(user=self.owner).update_project(
            project_id=self.project.id,
            name="直接改名",
        )
        self.assertEqual(updated.name, "直接改名")
        self.assertEqual(updated.config_version, 2)

    def test_service_rejects_stale_expected_version(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            ProjectService(user=self.owner).update_project(
                project_id=self.project.id,
                name="过期写入",
                expected_version=0,
            )
        self.assertEqual(ctx.exception.code, "PROJECT_VERSION_CONFLICT")
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(self._refresh().name, "发布准备")

    def test_service_rejects_blank_name(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            ProjectService(user=self.owner).update_project(
                project_id=self.project.id,
                name="   ",
            )
        self.assertEqual(ctx.exception.code, "PROJECT_NAME_REQUIRED")
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(self._refresh().name, "发布准备")

    def test_service_denies_viewer(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            ProjectService(user=self.viewer).update_project(
                project_id=self.project.id,
                name="越权改名",
            )
        self.assertEqual(ctx.exception.code, "PERMISSION_DENIED")
        self.assertEqual(ctx.exception.status, 403)
        self.assertEqual(self._refresh().name, "发布准备")

    def test_service_project_not_found(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            ProjectService(user=self.owner).update_project(
                project_id=Project.objects.create(
                    organization=self.organization,
                    name="回收站项目",
                    status=Project.Status.TRASHED,
                    trashed_at=timezone.now(),
                ).id,
                name="改名",
            )
        self.assertEqual(ctx.exception.code, "PROJECT_NOT_FOUND")
        self.assertEqual(ctx.exception.status, 404)

    # ── 路由层 ──

    def test_route_updates_project_settings(self) -> None:
        resp = self._call_update(
            self.owner,
            {"name": "发布准备更新", "description": "更新后的说明", "expected_version": 1},
        )
        self.assertIsInstance(resp, dict)
        self.assertTrue(resp.get("success"))
        data = resp["data"]
        self.assertEqual(data["name"], "发布准备更新")
        self.assertEqual(data["description"], "更新后的说明")
        self.assertEqual(data["config_version"], 2)
        self.assertEqual(data["type"], "team_space")

    def test_route_returns_409_on_version_conflict(self) -> None:
        resp = self._call_update(
            self.owner,
            {"name": "并发写入", "expected_version": 0},
        )
        body = self._error_body(resp)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(body["code"], "PROJECT_VERSION_CONFLICT")
        self.assertEqual(self._refresh().name, "发布准备")

    def test_route_returns_400_on_blank_name(self) -> None:
        resp = self._call_update(self.owner, {"name": ""})
        body = self._error_body(resp)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(body["code"], "PROJECT_NAME_REQUIRED")

    def test_route_returns_403_for_viewer(self) -> None:
        resp = self._call_update(self.viewer, {"name": "越权改名"})
        body = self._error_body(resp)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(body["code"], "PERMISSION_DENIED")
        self.assertEqual(self._refresh().name, "发布准备")

    def test_route_returns_404_for_unknown_project(self) -> None:
        resp = self._call_update(
            self.owner,
            {"name": "改名"},
            project_id="00000000-0000-0000-0000-000000000000",
        )
        body = self._error_body(resp)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(body["code"], "PROJECT_NOT_FOUND")
