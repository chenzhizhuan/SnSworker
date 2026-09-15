"""首次进入游戏时检查并补齐 img / music / video 资源。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

import requests

ASSET_DIRS = ("img", "music", "video")
REPO_URL = "https://gitee.com/jerry_mus/fairyland-hero.git"
REPO_BRANCH = "main"
RAW_BASE = f"https://gitee.com/jerry_mus/fairyland-hero/raw/{REPO_BRANCH}"
MANIFEST_NAME = "asset_manifest.json"
ProgressCb = Callable[[int, int, str], None]


@dataclass
class SyncResult:
    failed: List[Dict[str, Any]] = field(default_factory=list)
    method: str = "none"
    missing_before: List[Dict[str, Any]] = field(default_factory=list)


def project_root(start: Optional[Path] = None) -> Path:
    return Path(start or Path(__file__).resolve().parent)


def gitee_raw_url(rel_path: str) -> str:
    return f"{RAW_BASE}/{quote(str(rel_path).replace(os.sep, '/'), safe='/')}"


def is_safe_asset_path(rel_path: str) -> bool:
    p = Path(str(rel_path).replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        return False
    return p.parts[0] in ASSET_DIRS


def load_manifest(root: Path) -> Dict[str, Any]:
    path = Path(root) / MANIFEST_NAME
    if not path.is_file():
        return {"repo": REPO_URL, "branch": REPO_BRANCH, "files": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"repo": REPO_URL, "branch": REPO_BRANCH, "files": []}
    if not isinstance(data, dict):
        return {"repo": REPO_URL, "branch": REPO_BRANCH, "files": []}
    files = data.get("files") or []
    if not isinstance(files, list):
        files = []
    data["files"] = files
    return data


def find_missing_assets(root: Path) -> List[Dict[str, Any]]:
    root = Path(root)
    missing: List[Dict[str, Any]] = []
    for item in load_manifest(root).get("files") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path") or "").strip()
        if not rel or not is_safe_asset_path(rel):
            continue
        expected = int(item.get("size") or 0)
        dest = root / rel
        if not dest.is_file():
            missing.append({"path": rel, "size": expected})
            continue
        if expected > 0 and int(dest.stat().st_size) != expected:
            missing.append({"path": rel, "size": expected})
    return missing


def git_available() -> bool:
    try:
        r = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            timeout=8,
            check=False,
        )
        return int(r.returncode) == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def copy_missing_from_clone(
    clone_root: Path,
    dest_root: Path,
    missing: List[Dict[str, Any]],
    progress_cb: Optional[ProgressCb] = None,
) -> List[Dict[str, Any]]:
    failed: List[Dict[str, Any]] = []
    total = max(1, len(missing))
    for i, item in enumerate(missing, start=1):
        rel = str(item.get("path") or "")
        if progress_cb:
            progress_cb(i, total, f"正在复制 {rel}")
        if not is_safe_asset_path(rel):
            failed.append(item)
            continue
        src = Path(clone_root) / rel
        dest = Path(dest_root) / rel
        if not src.is_file():
            failed.append(item)
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            expected = int(item.get("size") or 0)
            if expected > 0 and int(dest.stat().st_size) != expected:
                dest.unlink(missing_ok=True)
                failed.append(item)
        except OSError:
            failed.append(item)
    return failed


def clone_repo_to(dest: Path, progress_cb: Optional[ProgressCb] = None) -> None:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if progress_cb:
        progress_cb(0, 1, "正在 git clone 仓库（img / music / video）…")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    cmd = [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        REPO_BRANCH,
        REPO_URL,
        str(dest),
    ]
    subprocess.run(
        cmd,
        check=True,
        timeout=900,
        env=env,
        capture_output=True,
        text=True,
    )


def _git_checkout_existing(
    root: Path,
    missing: List[Dict[str, Any]],
    progress_cb: Optional[ProgressCb] = None,
) -> List[Dict[str, Any]]:
    """当前目录已是 git 仓库时，优先从 origin 取出缺失文件，避免再 clone 一份。"""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    subprocess.run(
        ["git", "-C", str(root), "fetch", "--depth", "1", "origin", REPO_BRANCH],
        check=False,
        timeout=300,
        env=env,
        capture_output=True,
    )
    failed: List[Dict[str, Any]] = []
    total = max(1, len(missing))
    for i, item in enumerate(missing, start=1):
        rel = str(item.get("path") or "")
        if progress_cb:
            progress_cb(i, total, f"正在从仓库取出 {rel}")
        if not is_safe_asset_path(rel):
            failed.append(item)
            continue
        r = subprocess.run(
            ["git", "-C", str(root), "checkout", f"origin/{REPO_BRANCH}", "--", rel],
            capture_output=True,
            timeout=60,
            env=env,
        )
        dest = Path(root) / rel
        expected = int(item.get("size") or 0)
        if r.returncode != 0 or not dest.is_file():
            failed.append(item)
            continue
        if expected > 0 and int(dest.stat().st_size) != expected:
            failed.append(item)
    return failed


def sync_via_git(
    root: Path,
    missing: List[Dict[str, Any]],
    progress_cb: Optional[ProgressCb] = None,
) -> List[Dict[str, Any]]:
    if not missing:
        return []
    root = Path(root)
    remaining = list(missing)
    if (root / ".git").exists():
        if progress_cb:
            progress_cb(0, 1, "检测到本地 Git 仓库，正在取出缺失资源…")
        try:
            remaining = _git_checkout_existing(root, remaining, progress_cb)
        except Exception:
            remaining = list(missing)
        remaining = [
            item
            for item in remaining
            if not (root / str(item.get("path") or "")).is_file()
            or (
                int(item.get("size") or 0) > 0
                and int((root / str(item.get("path") or "")).stat().st_size)
                != int(item.get("size") or 0)
            )
        ]
        if not remaining:
            return []

    tmp = Path(tempfile.mkdtemp(prefix="fairyland_assets_"))
    try:
        clone_repo_to(tmp / "repo", progress_cb)
        return copy_missing_from_clone(tmp / "repo", root, remaining, progress_cb)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def download_url_to_file(
    url: str,
    dest: Path,
    expected_size: int = 0,
    progress_cb: Optional[ProgressCb] = None,
) -> None:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with requests.get(url, stream=True, timeout=180) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        fh.write(chunk)
        got = int(tmp.stat().st_size)
        if expected_size > 0 and got != int(expected_size):
            raise OSError(f"size mismatch: got {got}, expected {expected_size}")
        tmp.replace(dest)
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def sync_via_http(
    root: Path,
    missing: List[Dict[str, Any]],
    progress_cb: Optional[ProgressCb] = None,
) -> List[Dict[str, Any]]:
    failed: List[Dict[str, Any]] = []
    total = max(1, len(missing))
    for i, item in enumerate(missing, start=1):
        rel = str(item.get("path") or "")
        if progress_cb:
            progress_cb(i, total, f"正在从 Gitee 下载 {rel}（{i}/{len(missing)}）")
        if not is_safe_asset_path(rel):
            failed.append(item)
            continue
        dest = Path(root) / rel
        try:
            download_url_to_file(
                gitee_raw_url(rel),
                dest,
                int(item.get("size") or 0),
                progress_cb,
            )
        except Exception:
            failed.append(item)
    return failed


def sync_missing_assets(
    root: Path,
    progress_cb: Optional[ProgressCb] = None,
) -> SyncResult:
    root = Path(root)
    missing = find_missing_assets(root)
    result = SyncResult(missing_before=list(missing))
    if not missing:
        result.method = "none"
        return result

    used = "http"
    failed = list(missing)
    if git_available():
        used = "git"
        if progress_cb:
            progress_cb(0, 1, "检测到 Git，优先从仓库克隆资源…")
        try:
            failed = sync_via_git(root, missing, progress_cb)
        except Exception:
            used = "http"
            if progress_cb:
                progress_cb(0, 1, "Git 克隆失败，改为从 Gitee 逐个下载…")
            failed = list(find_missing_assets(root))

    still = find_missing_assets(root)
    if still:
        if used == "git" and progress_cb:
            progress_cb(0, 1, "克隆后仍有缺失，改为从 Gitee 补下…")
        used = "http" if used != "git" else "git+http"
        failed = sync_via_http(root, still, progress_cb)
        still = find_missing_assets(root)
        failed = still or failed

    result.method = used
    result.failed = failed
    return result


def build_manifest(root: Path) -> Dict[str, Any]:
    root = Path(root)
    files: List[Dict[str, Any]] = []
    for d in ASSET_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.name in {".DS_Store", "Thumbs.db"}:
                continue
            rel = f.relative_to(root).as_posix()
            if not is_safe_asset_path(rel):
                continue
            files.append({"path": rel, "size": int(f.stat().st_size)})
    return {"repo": REPO_URL, "branch": REPO_BRANCH, "files": files}
