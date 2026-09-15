#!/usr/bin/env python3
"""Validate design-lock.json before deck generation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
HASH_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
ENGINES = {"pptxgenjs", "python-pptx", "python-svg", "powerpoint-com", "ooxml"}
QA_MODES = {"fast", "standard", "strict"}
TEMPLATE_MODES = {"none", "user", "built-in"}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("version") != 1:
        errors.append("version must be 1")

    canvas = payload.get("canvas")
    if not isinstance(canvas, dict):
        errors.append("canvas must be an object")
    else:
        for key in ("width_in", "height_in"):
            value = canvas.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                errors.append(f"canvas.{key} must be a positive number")
        if not nonempty(canvas.get("aspect_ratio")):
            errors.append("canvas.aspect_ratio must be a non-empty string")

    for field in ("theme", "preset"):
        if not nonempty(payload.get(field)):
            errors.append(f"{field} must be a non-empty string")

    template = payload.get("template")
    if not isinstance(template, dict):
        errors.append("template must be an object")
    else:
        mode = template.get("mode")
        if mode not in TEMPLATE_MODES:
            errors.append(f"template.mode must be one of {sorted(TEMPLATE_MODES)}")
        if mode in {"user", "built-in"}:
            if not nonempty(template.get("path")):
                errors.append("template.path is required for user/built-in mode")
            digest = template.get("sha256")
            if not isinstance(digest, str) or not HASH_RE.fullmatch(digest):
                errors.append("template.sha256 must be a 64-character hexadecimal digest")

    fonts = payload.get("fonts")
    if not isinstance(fonts, dict):
        errors.append("fonts must be an object")
    else:
        for key in ("cjk", "latin"):
            if not nonempty(fonts.get(key)):
                errors.append(f"fonts.{key} must be a non-empty string")
        fallbacks = fonts.get("fallbacks", [])
        if not isinstance(fallbacks, list) or not all(nonempty(item) for item in fallbacks):
            errors.append("fonts.fallbacks must be a string array")

    if payload.get("engine") not in ENGINES:
        errors.append(f"engine must be one of {sorted(ENGINES)}")
    if payload.get("qa_mode") not in QA_MODES:
        errors.append(f"qa_mode must be one of {sorted(QA_MODES)}")

    colors = payload.get("semantic_colors")
    if not isinstance(colors, dict) or not colors:
        errors.append("semantic_colors must be a non-empty object")
    else:
        for name, value in colors.items():
            if not isinstance(value, str) or not HEX_RE.fullmatch(value):
                errors.append(f"semantic_colors.{name} must be #RRGGBB")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate design-lock.json")
    parser.add_argument("design_lock", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.design_lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("ERROR: document root must be an object", file=sys.stderr)
        return 2
    errors = validate(payload)
    if errors:
        print("DESIGN_LOCK_INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("DESIGN_LOCK_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
