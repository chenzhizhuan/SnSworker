#!/usr/bin/env python3
"""桌面客户端一键发版（HTTP 自建更新源形态）。

用法（服务器宿主机，/www/wwwroot/SnSworker 仓库根目录）：
  python3 scripts/community/publish-desktop-release.py \
      --exe /path/to/智算方舟\ Setup\ 1.0.4.exe \
      --version 1.0.4 \
      --notes "更新说明"

做四件事：
  1. 计算 exe 的 sha512(base64) 与 size
  2. 拷贝 exe → desktop-updates/snsworker-<version>-x64.exe（ASCII 文件名，
     避免 latest.yml path 的中文 URL 编码问题）
  3. 生成 desktop-updates/latest.yml（electron-updater NSIS generic feed）
  4. upsert Django AppRelease 发布记录（已发布 + 100% 灰度）

之后所有已安装「带更新能力」版本（≥1.0.4）的 Windows 客户端在
启动 / 轮询 / 手动检查时都会发现新版本并提示更新。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FEED_DIR = REPO_ROOT / "desktop-updates"
FEED_PUBLIC_BASE = "http://221.237.179.2:13490/desktop-updates"
DJANGO_CONTAINER = "snsworker-django-1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True, help="安装包路径（本地任意位置）")
    parser.add_argument("--version", required=True, help="语义化版本号，如 1.0.4")
    parser.add_argument("--notes", default="", help="发布说明（可省略）")
    parser.add_argument("--platform", default="win", choices=["win", "mac", "linux"])
    parser.add_argument("--arch", default="x64", choices=["x64", "arm64"])
    parser.add_argument("--channel", default="stable", choices=["stable", "beta", "alpha"])
    parser.add_argument("--mandatory", action="store_true", help="标记为强制更新（自动下载并阻断）")
    return parser.parse_args()


def sha512_base64(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii")


def upsert_release_record(args: argparse.Namespace, asset_name: str, checksum: str, size: int) -> None:
    file_url = f"{FEED_PUBLIC_BASE}/{asset_name}"
    feed_url = f"{FEED_PUBLIC_BASE}/"
    payload = {
        "version": args.version,
        "platform": args.platform,
        "arch": args.arch,
        "channel": args.channel,
        "file_url": file_url,
        "feed_url": feed_url,
        "file_size": size,
        "checksum_sha512": checksum,
        "release_notes": args.notes or f"SnSworker Desktop {args.version}",
        "is_mandatory": args.mandatory,
    }
    inner = (
        "import json, sys\n"
        "from apps.updater.models import AppRelease\n"
        "from django.utils import timezone\n"
        "payload = json.loads(sys.stdin.read())\n"
        "keys = ['version', 'platform', 'arch', 'channel']\n"
        "release, created = AppRelease.objects.get_or_create(\n"
        "    **{k: payload[k] for k in keys},\n"
        "    defaults={k: payload[k] for k in payload if k not in keys},\n"
        ")\n"
        "if not created:\n"
        "    for k, v in payload.items():\n"
        "        setattr(release, k, v)\n"
        "release.is_draft = False\n"
        "release.rollout_percentage = 100\n"
        "release.published_at = timezone.now()\n"
        "release.deprecated_at = None\n"
        "release.save()\n"
        "print(json.dumps({'version': release.version, 'published_at': str(release.published_at), 'file_url': release.file_url, 'feed_url': release.feed_url}))\n"
    )
    proc = subprocess.run(
        ["docker", "exec", "-i", DJANGO_CONTAINER, "python", "manage.py", "shell", "-c", inner],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-2000:])
        raise SystemExit("Django 发布记录写入失败")
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            print("发布记录：", line)


def main() -> None:
    args = parse_args()
    exe = Path(args.exe).expanduser().resolve()
    if not exe.is_file():
        raise SystemExit(f"安装包不存在：{exe}")

    asset_name = f"snsworker-{args.version}-{args.arch}.exe"
    checksum = sha512_base64(exe)
    size = exe.stat().st_size

    FEED_DIR.mkdir(parents=True, exist_ok=True)
    target = FEED_DIR / asset_name
    shutil.copyfile(exe, target)

    release_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    manifest_file = "latest.yml" if args.channel == "stable" else f"{args.channel}.yml"
    latest_yml = FEED_DIR / manifest_file
    latest_yml.write_text(
        "\n".join(
            [
                f"version: {args.version}",
                f"path: {asset_name}",
                f"sha512: {checksum}",
                f"size: {size}",
                f"releaseDate: '{release_date}'",
                f"releaseNotes: {args.notes or args.version}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"安装包：{target}（{size / 1024 / 1024:.1f} MB）")
    print(f"清单：{latest_yml}")
    print(f"sha512：{checksum}")

    upsert_release_record(args, asset_name, checksum, size)

    print(
        "\n发版完成。验证：\n"
        f"  curl {FEED_PUBLIC_BASE}/{manifest_file}\n"
        f"  curl -X POST {FEED_PUBLIC_BASE.replace('http://', 'http://127.0.0.1:')}"
    )


if __name__ == "__main__":
    main()
