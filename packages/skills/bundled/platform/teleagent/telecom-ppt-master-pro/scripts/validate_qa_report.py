#!/usr/bin/env python3
"""Validate a QA report and its page-level visual evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CHECK_NAMES = ("file", "content", "visual", "deck")
VALID_STATUSES = {"pass", "fail", "not-run"}
QA_MODES = {"fast", "standard", "strict"}


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(payload.get("deck"), str) or not payload["deck"].strip():
        errors.append("deck must be a non-empty string")
    qa_mode = payload.get("qa_mode")
    if qa_mode not in QA_MODES:
        errors.append(f"qa_mode must be one of {sorted(QA_MODES)}")
    slide_count = payload.get("slide_count")
    if not isinstance(slide_count, int) or isinstance(slide_count, bool) or slide_count < 1:
        errors.append("slide_count must be a positive integer")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
    else:
        for name in CHECK_NAMES:
            check = checks.get(name)
            if not isinstance(check, dict):
                errors.append(f"checks.{name} must be an object")
                continue
            status = check.get("status")
            if status not in VALID_STATUSES:
                errors.append(f"checks.{name}.status must be pass/fail/not-run")
            elif status != "pass":
                errors.append(f"checks.{name} is not pass: {status}")
            evidence = check.get("evidence")
            if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) and x.strip() for x in evidence):
                errors.append(f"checks.{name}.evidence must be a non-empty string array")

    slides = payload.get("slides")
    if not isinstance(slides, list):
        errors.append("slides must be an array")
        slides = []
    seen: set[int] = set()
    for item in slides:
        if not isinstance(item, dict):
            errors.append("each slides entry must be an object")
            continue
        number = item.get("slide")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            errors.append("each slides entry requires a positive slide number")
            continue
        if number in seen:
            errors.append(f"duplicate slide QA entry: {number}")
        seen.add(number)
        if item.get("visual_status") != "pass":
            errors.append(f"slide {number} visual_status is not pass")
        if not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
            errors.append(f"slide {number} requires visual evidence")

    if isinstance(slide_count, int) and slide_count > 0:
        if qa_mode in {"standard", "strict"}:
            expected = set(range(1, slide_count + 1))
            missing = sorted(expected - seen)
            extra = sorted(seen - expected)
            if missing:
                errors.append(f"missing slide visual QA entries: {missing}")
            if extra:
                errors.append(f"out-of-range slide QA entries: {extra}")
        elif qa_mode == "fast" and not seen:
            errors.append("fast mode still requires at least one representative slide visual check")

    limitations = payload.get("limitations", [])
    if not isinstance(limitations, list) or not all(isinstance(x, str) for x in limitations):
        errors.append("limitations must be a string array")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate qa-report.json")
    parser.add_argument("qa_report", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.qa_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("ERROR: document root must be an object", file=sys.stderr)
        return 2
    errors = validate(payload)
    if errors:
        print("QA_REPORT_INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("QA_REPORT_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
