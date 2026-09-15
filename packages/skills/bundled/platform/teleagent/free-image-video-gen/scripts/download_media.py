#!/usr/bin/env python3
"""
下载 Agnes MCP 服务生成的图片/视频到本地。

用法：
  python download_media.py <url> [--out 路径] [--base64] [--timeout 秒数]

参数：
  url       生成结果 URL 或 data URI
  --out     目标保存路径（可选，默认桌面）
  --base64  当传入 base64 data URI 时使用
  --timeout 下载超时秒数，默认 120

注意：URL 下载需要可以访问公网或服务端。
"""

import argparse
import base64
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


def get_default_output_dir() -> Path:
    """跨平台获取用户桌面路径，失败时回退到用户主目录。

    Windows 通过注册表读取真实桌面位置（兼容桌面被改动到其他盘符，
    如 D:\\Desktop 这种自定义情况）；macOS/Linux 取 ~/Desktop 或 ~/桌面。
    最终兜底回退到用户主目录，确保不会因找不到目录而失败。
    """
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            try:
                value, _ = winreg.QueryValueEx(key, "Desktop")
                if value and Path(value).exists():
                    return Path(value)
            finally:
                winreg.CloseKey(key)
        except Exception:
            pass
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            desktop = Path(userprofile) / "Desktop"
            if desktop.exists():
                return desktop
    home = Path.home()
    for _name in ("Desktop", "桌面"):
        candidate = home / _name
        if candidate.exists():
            return candidate
    return home


def get_default_path(ext: str) -> Path:
    name = f"generated_{int(time.time())}.{ext}"
    return get_default_output_dir() / name


def infer_ext_from_base64(data_uri: str) -> str:
    lower = data_uri.lower()
    if "image/png" in lower:
        return "png"
    if "image/webp" in lower:
        return "webp"
    if "image/jpeg" in lower or "image/jpg" in lower:
        return "jpg"
    if "video/mp4" in lower:
        return "mp4"
    return "bin"


def save_base64(data_uri: str, out_path: Path) -> Path:
    if "," not in data_uri:
        raise ValueError("无效的 data URI：缺少逗号分隔符")
    head, payload = data_uri.split(",", 1)
    ext = infer_ext_from_base64(head)
    if not out_path.suffix:
        out_path = out_path.with_suffix(f".{ext}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(payload))
    return out_path


def download(url: str, out_path: Path, timeout: int = 120) -> Path:
    headers = {"User-Agent": "free-media-gen/1.0"}
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if not out_path.suffix:
            ctype = resp.headers.get("Content-Type", "").lower()
            if "png" in ctype:
                ext = "png"
            elif "webp" in ctype:
                ext = "webp"
            elif "jpeg" in ctype or "jpg" in ctype:
                ext = "jpg"
            elif "mp4" in ctype:
                ext = "mp4"
            elif "webm" in ctype:
                ext = "webm"
            else:
                ext = "bin"
            out_path = out_path.with_suffix(f".{ext}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="下载 Agnes MCP 生成结果到本地")
    parser.add_argument("url", help="资源 URL 或 data URI")
    parser.add_argument("--out", default=None, help="目标保存路径")
    parser.add_argument("--base64", action="store_true", help="输入是 base64 data URI")
    parser.add_argument("--timeout", type=int, default=120, help="下载超时秒数")
    args = parser.parse_args()

    is_data_uri = args.base64 or args.url.startswith("data:")
    if is_data_uri:
        out = save_base64(args.url, Path(args.out) if args.out else get_default_path("bin"))
    else:
        out = Path(args.out) if args.out else get_default_path("bin")
        out = download(args.url, out, timeout=args.timeout)

    size_kb = out.stat().st_size / 1024
    if size_kb >= 1024:
        size_str = f"{size_kb / 1024:.2f} MB"
    else:
        size_str = f"{size_kb:.1f} KB"
    print(f"OK saved: {out}")
    print(f"size: {size_str}")
    print(f"path: {out.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
