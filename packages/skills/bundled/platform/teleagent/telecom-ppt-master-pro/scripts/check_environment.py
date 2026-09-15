#!/usr/bin/env python3
"""Discover local PPT generation and rendering capabilities without mutation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def first_existing(paths: list[Path]) -> str | None:
    for path in paths:
        if path.is_file():
            return str(path.resolve())
    return None


def find_node() -> str | None:
    override = os.environ.get("TELECOM_PPT_NODE")
    if override and Path(override).is_file():
        return str(Path(override).resolve())
    direct = shutil.which("node") or shutil.which("node.exe")
    if direct:
        return str(Path(direct).resolve())
    home = Path.home()
    candidates = sorted(
        home.glob(".cache/codex-runtimes/*/dependencies/node/bin/node.exe"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return first_existing(candidates)


def node_module_available(node: str | None, module: str) -> tuple[bool, str | None]:
    if not node:
        return False, None
    env = os.environ.copy()
    node_path_candidates = [
        str(Path(node).resolve().parents[1] / "node_modules"),
        env.get("NODE_PATH", ""),
    ]
    env["NODE_PATH"] = os.pathsep.join(path for path in node_path_candidates if path)
    try:
        result = subprocess.run(
            [node, "-e", f"process.stdout.write(require.resolve('{module}'))"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, None
    resolved = result.stdout.strip() if result.returncode == 0 else None
    return bool(resolved), resolved


def find_powerpoint() -> str | None:
    candidates: list[Path] = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.extend(Path(root).glob("Microsoft Office/root/Office*/POWERPNT.EXE"))
            candidates.extend(Path(root).glob("Microsoft Office/Office*/POWERPNT.EXE"))
    return first_existing(sorted(candidates))


def inspect() -> dict[str, Any]:
    node = find_node()
    pptxgenjs_ok, pptxgenjs_path = node_module_available(node, "pptxgenjs")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftoppm = shutil.which("pdftoppm")
    powerpoint = find_powerpoint()
    python_pptx = module_available("pptx")
    result = {
        "python": {"available": True, "path": str(Path(sys.executable).resolve()), "version": sys.version.split()[0]},
        "python_pptx": {"available": python_pptx},
        "pillow": {"available": module_available("PIL")},
        "node": {"available": bool(node), "path": node},
        "pptxgenjs": {"available": pptxgenjs_ok, "path": pptxgenjs_path},
        "powerpoint": {"available": bool(powerpoint), "path": powerpoint},
        "libreoffice": {"available": bool(soffice), "path": soffice},
        "pdftoppm": {"available": bool(pdftoppm), "path": pdftoppm},
        "routes": {
            "pptxgenjs": pptxgenjs_ok,
            "python_pptx": python_pptx,
            "powerpoint_native_edit": bool(powerpoint),
            "visual_render": bool(powerpoint or (soffice and pdftoppm)),
            "python_svg": False,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect telecom PPT runtime capabilities")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()
    result = inspect()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for name, value in result["routes"].items():
            print(f"{name}: {'available' if value else 'unavailable'}")
        print("Use --json for detailed paths and dependencies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
