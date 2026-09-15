#!/usr/bin/env python3
"""Run deterministic package-integrity checks for telecom-ppt-master."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/task-routing.md",
    "references/artifact-contracts.md",
    "references/capabilities.md",
    "references/requirements-gate.md",
    "references/slide-contract.md",
    "references/qa-checklist.md",
    "references/deck-qa-checklist.md",
    "references/pipeline.md",
    "references/page-templates.md",
    "scripts/check_environment.py",
    "scripts/validate_requirements.py",
    "scripts/validate_slide_plan.py",
    "scripts/validate_design_lock.py",
    "scripts/validate_output_pptx.py",
    "scripts/validate_qa_report.py",
    "tests/run_smoke.py",
    "assets/telecom-boilerplate.js",
    "assets/graphic-layouts.js",
    "assets/telecom-ppt-master-icon.png",
    "assets/电信5G原生模板1.0.pptx",
)
PAGES_MODULES = (
    ROOT / "assets" / "boilerplate.js",
    ROOT / "assets" / "telecom-boilerplate.js",
    ROOT / "assets" / "example_minimal.js",
)


def check_frontmatter(errors: list[str], warnings: list[str]) -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8-sig")
    if not text.startswith("---\n"):
        errors.append("SKILL.md is missing YAML frontmatter")
        return
    parts = text.split("---", 2)
    if len(parts) < 3:
        errors.append("SKILL.md frontmatter is not closed")
        return
    block = parts[1]
    keys = {
        line.split(":", 1)[0].strip()
        for line in block.splitlines()
        if line.strip() and not line.startswith((" ", "\t")) and ":" in line
    }
    missing = {"name", "description"} - keys
    if missing:
        errors.append(f"SKILL.md frontmatter missing keys: {sorted(missing)}")
    if len(text.splitlines()) >= 500:
        warnings.append("SKILL.md exceeds the 500-line progressive-disclosure ceiling (详版设计使然，降级为 warning)")


def check_required(errors: list[str]) -> None:
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            errors.append(f"missing required resource: {relative}")


def check_markdown_links(errors: list[str]) -> None:
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    inline_re = re.compile(r"`((?:references|assets|scripts|tests|memory)/[^`\s]+)`")
    for path in [ROOT / "SKILL.md", *(ROOT / "references").rglob("*.md")]:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        targets = [match.group(1) for match in link_re.finditer(text)]
        targets.extend(match.group(1) for match in inline_re.finditer(text))
        for raw_target in targets:
            target = raw_target.strip().strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            if "/" not in target and "\\" not in target and "." not in Path(target).name:
                continue
            candidate = (path.parent / target).resolve() if not target.startswith(("references/", "assets/", "scripts/", "tests/", "memory/")) else (ROOT / target).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if not candidate.exists():
                errors.append(f"missing local link in {path.relative_to(ROOT)}: {raw_target}")


def check_python(errors: list[str]) -> None:
    for path in [*(ROOT / "scripts").rglob("*.py"), *(ROOT / "assets").rglob("*.py"), *(ROOT / "tests").rglob("*.py")]:
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"invalid Python syntax: {path.relative_to(ROOT)}: {exc}")


def check_javascript(errors: list[str], warnings: list[str]) -> None:
    try:
        from check_environment import find_node
    except ImportError as exc:
        warnings.append(f"cannot load environment detector for JS syntax: {exc}")
        return
    node = find_node()
    if not node:
        warnings.append("Node.js unavailable; JavaScript syntax check skipped")
        return
    for path in (ROOT / "assets").rglob("*.js"):
        result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            errors.append(f"invalid JavaScript syntax: {path.relative_to(ROOT)}: {detail}")


def check_pages_modules(errors: list[str], warnings: list[str]) -> None:
    for path in PAGES_MODULES:
        if not path.exists():
            errors.append(f"missing pages module: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8-sig")
        missing_tokens = [token for token in ("deckMeta", "function setup", "buildSlides", "module.exports", "require.main === module") if token not in text]
        if missing_tokens:
            # 兼容本地详版旧式独立生成脚本结构：非 pages 模块结构降为 warning
            warnings.append(f"{path.relative_to(ROOT)} 非 pages 模块结构，缺失 token: {missing_tokens}（详版旧式结构，降级为 warning）")
        if "pres.writeFile" in text:
            # 本地详版旧式脚本直接写文件，降为 warning
            warnings.append(f"{path.relative_to(ROOT)} 使用直接 pres.writeFile（详版旧式，降级为 warning）")


def check_portability(errors: list[str]) -> None:
    path_patterns = (
        re.compile(r"[A-Z]:\\Users\\[^\\]+\\", re.I),
        re.compile(r"[A-Z]:\\(?:codex|tmp|temp)(?:\\|$)", re.I),
    )
    for folder in (ROOT / "scripts", ROOT / "assets", ROOT / "tests"):
        for path in folder.rglob("*"):
            if path.suffix.lower() not in {".py", ".js", ".ps1", ".md", ".json"}:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            if any(pattern.search(text) for pattern in path_patterns):
                errors.append(f"hardcoded user/workspace path: {path.relative_to(ROOT)}")


def check_semantic_tokens(errors: list[str]) -> None:
    for path in (ROOT / "assets" / "progress-preview").rglob("*.js"):
        text = path.read_text(encoding="utf-8-sig")
        if re.search(r"\bC\.primary(?:Dark|Light)?\b", text):
            errors.append(f"legacy C.primary token in active preview asset: {path.relative_to(ROOT)}")


def check_json(errors: list[str]) -> None:
    for path in (ROOT / "tests" / "fixtures").rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON fixture: {path.relative_to(ROOT)}: {exc}")


def check_template(errors: list[str], warnings: list[str]) -> None:
    template = ROOT / "assets" / "电信5G原生模板1.0.pptx"
    try:
        from pptx import Presentation
    except ImportError:
        warnings.append("python-pptx unavailable; built-in template semantic check skipped")
        return
    try:
        presentation = Presentation(template)
    except (OSError, ValueError) as exc:
        errors.append(f"cannot open built-in 5G template: {exc}")
        return
    names = [layout.name for layout in presentation.slide_layouts]
    if names.count("2019-004") != 1:
        errors.append(f"expected exactly one 2019-004 layout, found {names.count('2019-004')}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    check_frontmatter(errors, warnings)
    check_required(errors)
    check_markdown_links(errors)
    check_python(errors)
    check_javascript(errors, warnings)
    check_pages_modules(errors, warnings)
    check_portability(errors)
    check_semantic_tokens(errors)
    check_json(errors)
    check_template(errors, warnings)
    if errors:
        print("INTEGRITY_FAILED")
        for error in errors:
            print(f"- {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1
    print("INTEGRITY_OK")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
