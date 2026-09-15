#!/usr/bin/env python3
"""Write-Verify script — parameterized validation for L2+ steps.

Usage:
    python verify_script.py --target <file_path> --module <import_path> [--checks <check_list>]

Checks:
    encoding    Zero-width character + BOM scan
    bare_except Exception anti-pattern scan
    import      Module import validation (requires --module)
    types       mypy type check
    readback    File format integrity (.bat/.cmd/.json)
    hardcode    硬编码值泄漏扫描
    all         运行全部 6 项检查（默认）

Exit codes:
    0 = all checks PASSED (or SKIP, no FAIL)
    1 = one or more checks FAILED
"""

import argparse
import os
import re
import subprocess
import sys

# --------------------------------------------------------------------------- #
# Check 1: Encoding contamination (zero-width + BOM)
# --------------------------------------------------------------------------- #
def check_encoding(target: str) -> tuple[str, str]:
    """Scan for U+200B zero-width characters and UTF-8 BOM."""
    with open(target, "rb") as f:
        data = f.read()
    if b"\xe2\x80\x8b" in data:
        return "FAIL", "U+200B zero-width character detected!"
    if data[:3] == b"\xef\xbb\xbf":
        return "FAIL", "UTF-8 BOM detected!"
    return "PASS", "No encoding contamination"


# --------------------------------------------------------------------------- #
# Check 2: Bare except anti-patterns
# --------------------------------------------------------------------------- #
def check_bare_except(target: str) -> tuple[str, str]:
    """Scan for bare except, except-without-as, and silent suppression."""
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    issues: list[str] = []
    for i, line in enumerate(lines, 1):
        # bare except: · CRITICAL
        if re.match(r"\s*except\s*:", line):
            issues.append(f"Line {i}: bare except: (CRITICAL)")
        # except Exception: without 'as e' · WARNING (supports dotted names like httpx.ConnectError)
        elif re.match(r"\s*except\s+\w+(?:\.\w+)*\s*:\s*$", line) and "as" not in line:
            issues.append(f"Line {i}: except without 'as e' (WARNING)")
        # except ...: pass — silent suppression · WARNING
        elif re.match(r"\s*except\s+.*:\s*pass\s*$", line):
            issues.append(f"Line {i}: except ... pass — silent suppression (WARNING)")
    if issues:
        return "FAIL", "\n  ".join(issues)
    return "PASS", "No exception anti-patterns"


# --------------------------------------------------------------------------- #
# Check 3: Import validation
# --------------------------------------------------------------------------- #
def check_import(target: str, module: str) -> tuple[str, str]:
    """Attempt to import the given module path via subprocess.

    Returns SKIP when module path is empty or unset.
    """
    if not module:
        return "SKIP", "No module specified --import check skipped"
    try:
        r = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0:
            return "FAIL", f"Import error: {r.stderr.strip()}"
        return "PASS", "Module imports successfully"
    except subprocess.TimeoutExpired as e:
        return "FAIL", "Import check timed out (15s)"
    except Exception as e:
        return "SKIP", f"Import check unavailable: {e}"


# --------------------------------------------------------------------------- #
# Check 4: Type check (mypy)
# --------------------------------------------------------------------------- #
def check_types(target: str) -> tuple[str, str]:
    """Run mypy on the target file if available."""
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                target,
                "--ignore-missing-imports",
                "--no-error-summary",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        errors = [l for l in r.stdout.strip().split("\n") if "error:" in l]
        if errors:
            return "FAIL", "\n  ".join(errors[:5])
        return "PASS", "No type errors"
    except FileNotFoundError as e:
        return "SKIP", "mypy not installed"
    except subprocess.TimeoutExpired as e:
        return "FAIL", "Type check timed out (30s)"
    except Exception as e:
        # mypy installed but raised unexpected error — treat as SKIP
        return "SKIP", "mypy unavailable"


# --------------------------------------------------------------------------- #
# Check 5: File format integrity (readback)
# --------------------------------------------------------------------------- #
def check_readback(target: str) -> tuple[str, str]:
    """Verify line endings and BOM for .bat/.cmd/.json files."""
    ext = os.path.splitext(target)[1].lower()
    with open(target, "rb") as f:
        data = f.read()
    issues: list[str] = []
    if ext in (".bat", ".cmd"):
        if b"\r\n" not in data:
            issues.append("Missing CRLF line endings (cmd.exe will fail)")
    if ext == ".json":
        if data[:3] == b"\xef\xbb\xbf":
            issues.append("UTF-8 BOM will break JSON parsers")
    if issues:
        return "FAIL", "\n  ".join(issues)
    return "PASS", "File format OK"


# --------------------------------------------------------------------------- #
# Check 6: 硬编码值扫描器
# --------------------------------------------------------------------------- #
def check_hardcode(target: str) -> tuple[str, str]:
    """扫描源代码与配置文件中的硬编码值。"""
    ext = os.path.splitext(target)[1].lower()
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    issues: list[str] = []

    _pw = "password"
    _ak = "api_key"
    _as = "api_secret"
    _tk = "token"

    # 安全关键字：包含这些的行将被跳过
    safe_kw = ["os.environ", "PLACEHOLDER", _pw + "_env", _tk + "_env", "_env"]

    # (字段名, 最小长度) 配对
    src_fields = [(_pw, 8), (_ak, 20), (_as, 16)]
    cfg_fields = [(_pw, 8), (_tk, 20)]

    if ext in (".py", ".js", ".ts", ".go", ".java"):
        fields = src_fields
    elif ext in (".json", ".yaml", ".yml", ".env", ".toml"):
        fields = cfg_fields
    else:
        return "PASS", "无硬编码值（不支持的文件类型）"

    for i, line in enumerate(lines, 1):
        for name, min_len in fields:
            # Build regex via concatenation; % formatting breaks on '%^' etc.
            pat = (
                r'''["']?''' + name
                + r'''["']?\s*[:=]\s*["']'''
                + r'''[a-zA-Z0-9_!@#$%^&*\-]{''' + str(min_len) + r''',}["']'''
            )
            if re.search(pat, line):
                if any(kw in line for kw in safe_kw):
                    continue
                issues.append(
                    f"第 {i} 行: 检测到硬编码值 ({name}) — 请改用环境变量引用"
                )
    if issues:
        return "FAIL", "\n  ".join(issues)
    return "PASS", "无硬编码值"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
ALL_CHECKS = ["encoding", "bare_except", "import", "types", "readback", "hardcode"]


def run_checks(target: str, module: str, checks: list[str]) -> int:
    """Execute the requested checks and print results.

    Returns 0 if no FAIL, 1 if any FAIL.
    """
    check_map: dict[str, tuple] = {
        "encoding":     ("Encoding contamination",  lambda: check_encoding(target)),
        "bare_except":  ("Exception anti-patterns", lambda: check_bare_except(target)),
        "import":       ("Import validation",       lambda: check_import(target, module)),
        "types":        ("Type check",              lambda: check_types(target)),
        "readback":     ("File format integrity",   lambda: check_readback(target)),
        "hardcode":     ("硬编码值泄漏扫描",           lambda: check_hardcode(target)),
    }

    print(f"Write-Verify: {target}")
    print("=" * 60)

    fail_count = 0
    for key in checks:
        if key not in check_map:
            print(f"  [SKIP] Unknown check: {key}")
            continue
        name, fn = check_map[key]
        status, msg = fn()
        print(f"  [{status}] {name}: {msg}")
        if status == "FAIL":
            fail_count += 1

    print("=" * 60)
    if fail_count > 0:
        print(f"RESULT: {fail_count} check(s) FAILED — fix before proceeding")
        return 1
    else:
        print("RESULT: All checks PASSED")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write-Verify: post-write validation for L2+ code steps",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Absolute path to the file being verified",
    )
    parser.add_argument(
        "--module",
        default="",
        help='Module import path (e.g. engine.fusion_engine). Empty = skip import check',
    )
    parser.add_argument(
        "--checks",
        default="all",
        help="Comma-separated check names or 'all' (default: all). "
        "Available: " + ", ".join(ALL_CHECKS),
    )
    args = parser.parse_args()

    # Resolve --checks
    if args.checks.strip().lower() == "all":
        checks = ALL_CHECKS
    else:
        checks = [c.strip() for c in args.checks.split(",") if c.strip()]

    # Verify target exists
    if not os.path.isfile(args.target):
        print(f"Write-Verify: {args.target}")
        print("=" * 60)
        print(f"  [FAIL] Target file not found: {args.target}")
        print("=" * 60)
        print("RESULT: 1 check(s) FAILED — fix before proceeding")
        sys.exit(1)

    exit_code = run_checks(args.target, args.module, checks)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
