#!/usr/bin/env python3
"""Validate the machine-readable telecom PPT slide plan."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


TEMPLATE_RE = re.compile(r"^(?:T(?:[1-9]|[12][0-9]|3[0-4])(?:\s*\+\s*local variant)?|ED\d+\s*\+\s*T(?:[1-9]|[12][0-9]|3[0-4]))$")
N_A_ROLES = {"cover", "overview", "transition", "section", "closing", "q&a"}
REQUIRED_TEXT = ("role", "claim", "proof_object", "template", "macro_layout")


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(payload.get("deck_title"), str) or not payload["deck_title"].strip():
        errors.append("deck_title must be a non-empty string")
    slides = payload.get("slides")
    if not isinstance(slides, list) or not slides:
        return errors + ["slides must be a non-empty array"]

    macros: list[str] = []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            errors.append(f"slide {index} must be an object")
            continue
        if slide.get("slide") != index:
            errors.append(f"slide {index} must have slide={index}")
        for field in REQUIRED_TEXT:
            value = slide.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"slide {index} requires non-empty {field}")
        template = slide.get("template")
        if isinstance(template, str) and template.strip() and not TEMPLATE_RE.fullmatch(template.strip()):
            errors.append(f"slide {index} has invalid template: {template!r}")
        refs = slide.get("source_refs")
        if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
            errors.append(f"slide {index} source_refs must be a non-empty string array")
        else:
            role = str(slide.get("role", "")).lower()
            if role not in N_A_ROLES and all(ref.strip().upper() == "N/A" for ref in refs):
                errors.append(f"slide {index} content role cannot use only N/A sources")
        macro = slide.get("macro_layout")
        macros.append(macro.strip() if isinstance(macro, str) else "")

    for index in range(2, len(macros)):
        if macros[index] and macros[index] == macros[index - 1] == macros[index - 2]:
            errors.append(f"slides {index - 1}-{index + 1} repeat macro_layout {macros[index]!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate slide-plan.json")
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.plan.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("ERROR: document root must be an object", file=sys.stderr)
        return 2
    errors = validate(payload)
    if errors:
        print("SLIDE_PLAN_INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"SLIDE_PLAN_VALID ({len(payload['slides'])} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
