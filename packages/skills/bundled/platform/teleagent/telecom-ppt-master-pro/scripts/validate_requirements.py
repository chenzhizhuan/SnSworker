#!/usr/bin/env python3
"""Validate the telecom PPT requirements gate.

The validator checks workflow readiness only. It does not infer requirements and
does not replace user confirmation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ACCEPTED_STATUSES = {"known", "defaulted", "confirmed"}
STRICT_STATUSES = {"known", "confirmed"}
STRICT_REQUIRED = {
    "purpose",
    "desired_action",
    "audience",
    "source_of_truth",
    "period",
    "scope",
    "page_count",
    "duration_minutes",
}
BASE_REQUIRED = {
    "purpose",
    "desired_action",
    "audience",
    "source_of_truth",
    "template_mode",
    "deliverables",
    "confidentiality",
}
DATA_REQUIRED = {"period", "scope", "unit", "missing_value_policy"}


def _field_ready(fields: dict[str, Any], name: str) -> bool:
    item = fields.get(name)
    if not isinstance(item, dict):
        return False
    value = item.get("value")
    status = item.get("status")
    allowed = STRICT_STATUSES if name in STRICT_REQUIRED else ACCEPTED_STATUSES
    return status in allowed and value not in (None, "", [])


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        return ["fields must be an object"]

    required = set(BASE_REQUIRED)
    if payload.get("has_data") is True:
        required.update(DATA_REQUIRED)

    if not (_field_ready(fields, "page_count") or _field_ready(fields, "duration_minutes")):
        errors.append("either page_count or duration_minutes must be ready")

    for name in sorted(required):
        if not _field_ready(fields, name):
            errors.append(f"required field is not ready: {name}")

    # Do not trust blocking_unknowns as the only source of truth. Any field that
    # declares itself high-risk must be independently ready, including custom
    # fields such as must_exclude or internet_allowed.
    for name, item in sorted(fields.items()):
        if not isinstance(item, dict):
            errors.append(f"field must be an object: {name}")
            continue
        risk = str(item.get("risk", "")).upper()
        status = item.get("status")
        if risk == "A" and status not in STRICT_STATUSES:
            errors.append(f"high-risk field is not confirmed: {name} (status={status!r})")
        if status == "conflict":
            errors.append(f"field has unresolved conflict: {name}")

    conflicts = payload.get("conflicts", [])
    if not isinstance(conflicts, list):
        errors.append("conflicts must be an array")
    elif conflicts:
        errors.append(f"unresolved conflicts: {len(conflicts)}")

    declared_blockers = payload.get("blocking_unknowns", [])
    if not isinstance(declared_blockers, list):
        errors.append("blocking_unknowns must be an array")
    elif declared_blockers:
        errors.append(f"declared blocking unknowns: {len(declared_blockers)}")

    if payload.get("ready_for_planning") is not True:
        errors.append("ready_for_planning must be true")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate telecom PPT requirement lock JSON")
    parser.add_argument("requirements", type=Path, help="Path to deck-requirements.json")
    args = parser.parse_args()

    try:
        payload = json.loads(args.requirements.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.requirements}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print("ERROR: document root must be an object", file=sys.stderr)
        return 2

    errors = validate(payload)
    if errors:
        print("REQUIREMENTS_NOT_READY")
        for error in errors:
            print(f"- {error}")
        return 1

    print("REQUIREMENTS_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
