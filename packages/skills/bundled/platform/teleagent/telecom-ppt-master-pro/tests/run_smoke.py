#!/usr/bin/env python3
"""Run deterministic regression checks for telecom-ppt-master."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
PYTHON = sys.executable


def run(args: list[str], expected: int = 0) -> None:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != expected:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise RuntimeError(
            f"unexpected exit {result.returncode}, expected {expected}: {' '.join(args)}\n{output}"
        )


def main() -> int:
    run([PYTHON, "scripts/validate_requirements.py", str(FIXTURES / "requirements-ready.json")])
    run(
        [PYTHON, "scripts/validate_requirements.py", str(FIXTURES / "requirements-blocked-risk.json")],
        expected=1,
    )
    run([PYTHON, "scripts/validate_slide_plan.py", str(FIXTURES / "slide-plan-valid.json")])
    run([PYTHON, "scripts/validate_slide_plan.py", str(FIXTURES / "slide-plan-invalid.json")], expected=1)
    run([PYTHON, "scripts/validate_design_lock.py", str(FIXTURES / "design-lock-valid.json")])
    run([PYTHON, "scripts/validate_qa_report.py", str(FIXTURES / "qa-report-valid.json")])
    run([PYTHON, "scripts/check_environment.py", "--json"])

    if importlib.util.find_spec("pptx") is None:
        print("SMOKE_OK (template deck skipped: python-pptx unavailable)")
        return 0

    with tempfile.TemporaryDirectory(prefix="telecom-ppt-smoke-") as temp_dir:
        layout_map = Path(temp_dir) / "layout-map.json"
        run(
            [
                PYTHON,
                "assets/template-analyzer.py",
                "--input",
                str(ROOT / "assets" / "电信5G原生模板1.0.pptx"),
                "--output",
                str(layout_map),
                "--sample-slides",
                "3",
            ]
        )
        layout_payload = json.loads(layout_map.read_text(encoding="utf-8"))
        if layout_payload.get("version") != 2 or len(layout_payload.get("source_sha256", "")) != 64:
            raise RuntimeError("template analyzer did not emit the v2 hash-aware Layout Map")

        output = Path(temp_dir) / "minimal.pptx"
        run(
            [
                PYTHON,
                "scripts/build_on_template.py",
                "--template",
                str(ROOT / "assets" / "电信5G原生模板1.0.pptx"),
                "--layout",
                "2019-004",
                "--spec",
                str(FIXTURES / "template-deck-3.json"),
                "--output",
                str(output),
            ]
        )
        run([PYTHON, "scripts/validate_output_pptx.py", str(output)])
    print("SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
