#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre_gate_guard.py — 前置门禁（v2026.09.08 集群Ultra版）

设计目标：
  本脚本在任务开始时（技能加载后）强制运行前置检查，
  确保技能文件完整、规则基线完好、脚本可编译、硬门禁速查块在场，
  并生成检查点状态文件 rl-state/pre_gate_checkpoint.json。
  前置门禁未通过则禁止继续后续流程。

检查项：
  P1: SKILL.md 存在且可读（技能完整性）
  P2: 硬门禁速查块在场（前100行含"硬门禁速查"，防截断丢失）
  P3: 规则护盾 smart-check PASS（规则基线完好，硬门禁7前置化）
  P4: 全部 .py 脚本 ast.parse PASS（脚本可编译性，不产生.pyc）
  P5: 核心脚本文件齐全（check_period/rule_shield）
  P6: SKILL.md 体积未超截断线（≤43KB硬阈值，防规则丢失）
  P7: 步骤标识状态机 step_counter.py 存在且可用（v2.0名称化追踪，防步骤名重复）

用法：
  python scripts/pre_gate_guard.py                     # 前置门禁检查（写检查点）
  python scripts/pre_gate_guard.py --check-only        # 仅检查不写检查点
  python scripts/pre_gate_guard.py --verify-checkpoint  # 验证检查点是否存在且有效
  python scripts/pre_gate_guard.py --target-skill <路径> # 检查指定技能目录

退出码：
  0 = ALL PASS（检查点已写入，任务可继续）
  1 = ANY FAIL（⛔禁止继续，须修复后重跑）
  2 = 运行错误
"""

import argparse
import ast
import json
import os
import subprocess
import sys
from datetime import datetime

# ========== 路径配置 ==========

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
RL_STATE_DIR = os.path.join(SKILL_DIR, "rl-state")
CHECKPOINT_FILE = os.path.join(RL_STATE_DIR, "pre_gate_checkpoint.json")

# 检查点最大有效期（秒），超过则视为过期
CHECKPOINT_MAX_AGE_SEC = 86400  # 24小时

# 核心脚本文件清单（P5 检查）
CORE_SCRIPTS = [
    "check_period.py",
    "rule_shield.py",
]

# P7: 步骤标识状态机 step_counter.py 存在且可用（v2.0名称化追踪，防步骤名重复）
STEP_COUNTER_SCRIPT = "step_counter.py"

# SKILL.md 截断硬阈值（字节）
SKILL_TRUNCATION_HARD = 43000  # 43KB


# ========== 工具函数 ==========

def run_subprocess(cmd, cwd=None, timeout=60):
    """运行子进程，返回 (returncode, stdout, stderr)。

    设置 PYTHONDONTWRITEBYTECODE=1 环境变量，防止子进程导入模块时
    生成 .pyc 文件（避免恶意文件清理检测误报）。
    """
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        r = subprocess.run(
            cmd, cwd=cwd or SKILL_DIR, capture_output=True,
            text=True, timeout=timeout, env=env
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout after {}s".format(timeout)
    except Exception as e:
        return -2, "", str(e)


def ensure_rl_state_dir():
    """确保 rl-state 目录存在。"""
    if not os.path.isdir(RL_STATE_DIR):
        os.makedirs(RL_STATE_DIR, exist_ok=True)


# ========== 前置检查器 ==========

def check_skill_md(skill_dir=None):
    """P1: SKILL.md 存在且可读。"""
    sd = skill_dir or SKILL_DIR
    skill_md = os.path.join(sd, "SKILL.md")
    if not os.path.exists(skill_md):
        return False, "SKILL.md not found: {}".format(skill_md)
    try:
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read(8192)
        if len(content) < 100:
            return False, "SKILL.md too small ({} bytes), likely corrupted".format(len(content))
        return True, "SKILL.md exists ({} bytes head read)".format(len(content))
    except Exception as e:
        return False, "SKILL.md read failed: {}".format(e)


def check_hard_gate_block(skill_dir=None):
    """P2: 硬门禁速查块在场（前100行含"硬门禁速查"）。"""
    sd = skill_dir or SKILL_DIR
    skill_md = os.path.join(sd, "SKILL.md")
    if not os.path.exists(skill_md):
        return False, "SKILL.md not found (P1 dependency)"
    try:
        with open(skill_md, "r", encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                lines.append(line)
                if i >= 100:
                    break
        head = "".join(lines)
        if "硬门禁速查" in head:
            return True, "硬门禁速查块在前100行内确认"
        return False, "硬门禁速查块未在前100行内找到（截断风险）"
    except Exception as e:
        return False, "SKILL.md head read failed: {}".format(e)


def check_rule_shield(skill_dir=None):
    """P3: 规则护盾 smart-check PASS。"""
    sd = skill_dir or SKILL_DIR
    scripts_dir = os.path.join(sd, "scripts")
    rule_shield = os.path.join(scripts_dir, "rule_shield.py")
    if not os.path.exists(rule_shield):
        return False, "rule_shield.py not found"
    rc, out, err = run_subprocess(
        [sys.executable, os.path.join("scripts", "rule_shield.py"), "--smart-check"],
        cwd=sd
    )
    if rc == 0:
        # 提取规则数
        rule_count = 0
        for line in (out or "").split("\n"):
            if "基线规则" in line and "条" in line:
                try:
                    rule_count = int(line.split("基线规则:")[1].split("条")[0].strip())
                except (IndexError, ValueError):
                    pass
        return True, "rule_shield --smart-check PASS ({} rules)".format(rule_count) if rule_count else "rule_shield --smart-check PASS"
    return False, "rule_shield --smart-check FAIL (exit={}) {}".format(rc, (err or out)[-300:] if (err or out) else "")


def check_scripts_compile(skill_dir=None):
    """P4: 全部 .py 脚本 ast.parse PASS（不产生.pyc）。"""
    sd = skill_dir or SKILL_DIR
    scripts_dir = os.path.join(sd, "scripts")
    if not os.path.isdir(scripts_dir):
        return False, "scripts/ directory not found"
    py_files = [f for f in os.listdir(scripts_dir) if f.endswith('.py')]
    if not py_files:
        return False, "No .py files in scripts/"
    failed = []
    for fname in py_files:
        fpath = os.path.join(scripts_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source, filename=fpath)
        except Exception as e:
            failed.append("{}: {}".format(fname, e))
    if failed:
        return False, "ast.parse FAIL on: {}".format("; ".join(failed[:3]))
    return True, "ast.parse {}/{} PASS".format(len(py_files), len(py_files))


def check_core_scripts(skill_dir=None):
    """P5: 核心脚本文件齐全。"""
    sd = skill_dir or SKILL_DIR
    scripts_dir = os.path.join(sd, "scripts")
    missing = []
    for s in CORE_SCRIPTS:
        if not os.path.exists(os.path.join(scripts_dir, s)):
            missing.append(s)
    if missing:
        return False, "Missing core scripts: {}".format(", ".join(missing))
    return True, "All {} core scripts present".format(len(CORE_SCRIPTS))


def check_skill_size(skill_dir=None):
    """P6: SKILL.md 体积未超截断硬阈值。"""
    sd = skill_dir or SKILL_DIR
    skill_md = os.path.join(sd, "SKILL.md")
    if not os.path.exists(skill_md):
        return False, "SKILL.md not found (P1 dependency)"
    size = os.path.getsize(skill_md)
    if size > SKILL_TRUNCATION_HARD:
        return False, "SKILL.md {} bytes > {} hard limit (truncation risk)".format(size, SKILL_TRUNCATION_HARD)
    return True, "SKILL.md {} bytes < {} hard limit".format(size, SKILL_TRUNCATION_HARD)


def check_step_counter(skill_dir=None):
    """P7: 步骤标识状态机可用（v2.0名称化追踪，防步骤名重复）。

    检查三项：
      1. step_counter.py 脚本存在且可编译
      2. 运行 --check 退出码为0（状态机可读写）
      3. 运行 --check-gaps 退出码为0（名称化模式下为兼容保留，始终PASS）
    """
    sd = skill_dir or SKILL_DIR
    scripts_dir = os.path.join(sd, "scripts")
    sc_path = os.path.join(scripts_dir, STEP_COUNTER_SCRIPT)
    if not os.path.exists(sc_path):
        return False, "step_counter.py not found (P7 dependency)"
    # 语法检查
    try:
        with open(sc_path, "r", encoding="utf-8") as f:
            ast.parse(f.read(), filename=sc_path)
    except Exception as e:
        return False, "step_counter.py ast.parse FAIL: {}".format(e)
    # 运行 --check
    rc, out, err = run_subprocess(
        [sys.executable, os.path.join("scripts", STEP_COUNTER_SCRIPT), "--check"],
        cwd=sd
    )
    if rc != 0:
        return False, "step_counter.py --check FAIL (exit={}) {}".format(rc, (err or out)[-300:] if (err or out) else "")
    # v2.0: 提取已注册步骤数（替代旧版"当前最大编号"解析）
    registered_count = 0
    for line in (out or "").split("\n"):
        if "已注册步骤" in line and "个" in line:
            try:
                registered_count = int(line.split("已注册步骤:")[1].split("个")[0].strip())
            except (IndexError, ValueError):
                pass
    # v2.0: 运行 --check-gaps（名称化模式下为兼容保留，始终PASS）
    gaps_info = ""
    rc2, _, _ = run_subprocess(
        [sys.executable, os.path.join("scripts", STEP_COUNTER_SCRIPT), "--check-gaps"],
        cwd=sd
    )
    if rc2 != 0:
        gaps_info = " [⚠️ gaps detected]"
    else:
        gaps_info = " [gaps OK]"
    return True, "step_counter.py --check PASS (registered={}){}".format(registered_count, gaps_info)


# ========== 检查点管理 ==========

def write_checkpoint(checks_result, skill_dir=None):
    """写入检查点状态文件。"""
    sd = skill_dir or SKILL_DIR
    ensure_rl_state_dir()

    skill_md = os.path.join(sd, "SKILL.md")
    skill_md_size = os.path.getsize(skill_md) if os.path.exists(skill_md) else 0
    scripts_dir = os.path.join(sd, "scripts")
    script_count = len([f for f in os.listdir(scripts_dir) if f.endswith('.py')]) if os.path.isdir(scripts_dir) else 0

    # 提取规则数
    rule_count = 0
    for cid, (passed, detail) in checks_result.items():
        if cid == "P3" and passed:
            try:
                rule_count = int(detail.split("(")[1].split(" ")[0]) if "(" in detail else 0
            except (IndexError, ValueError):
                pass

    checkpoint = {
        "checkpoint_time": datetime.now().isoformat(),
        "skill_dir": sd,
        "all_passed": all(r[0] for r in checks_result.values()),
        "checks": {
            cid: {"passed": r[0], "detail": r[1]}
            for cid, r in checks_result.items()
        },
        "skill_md_size": skill_md_size,
        "script_count": script_count,
        "rule_shield_rules": rule_count,
        "version": "1.0",
    }

    try:
        from _utils import atomic_write_json
        atomic_write_json(CHECKPOINT_FILE, checkpoint)
        return True, "Checkpoint written to {}".format(CHECKPOINT_FILE)
    except Exception as e:
        return False, "Failed to write checkpoint: {}".format(e)


def verify_checkpoint(skill_dir=None):
    """验证检查点是否存在且有效（未过期）。

    Args:
        skill_dir: 指定技能目录（默认为本技能目录）。跨技能验证时
                   须传入正确的 skill_dir，否则会检查错误技能的检查点文件。
    """
    sd = skill_dir or SKILL_DIR
    checkpoint_file = os.path.join(sd, "rl-state", "pre_gate_checkpoint.json")
    if not os.path.exists(checkpoint_file):
        return False, "pre_gate_checkpoint.json not found ({} — 前置门禁未运行，⛔禁止交付)".format(checkpoint_file)

    try:
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)
    except json.JSONDecodeError as e:
        return False, "pre_gate_checkpoint.json 解析失败: {}".format(e)
    except Exception as e:
        return False, "pre_gate_checkpoint.json 读取失败: {}".format(e)

    if not isinstance(checkpoint, dict):
        return False, "pre_gate_checkpoint.json 格式错误：顶层应为 dict"

    # 检查 all_passed 字段
    if not checkpoint.get("all_passed"):
        return False, "前置门禁检查未全部通过（all_passed=False），⛔禁止交付"

    # 检查时间有效期
    ts_str = checkpoint.get("checkpoint_time")
    if not ts_str:
        return False, "检查点缺少 timestamp 字段"
    try:
        ts = datetime.fromisoformat(ts_str)
        age = (datetime.now() - ts).total_seconds()
        if age > CHECKPOINT_MAX_AGE_SEC:
            return False, "检查点已过期（{:.0f}小时前），须重新运行前置门禁".format(age / 3600)
        if age < -60:
            return False, "检查点时间异常（未来时间），可能被篡改"
        return True, "前置门禁检查点有效（{:.0f}小时前通过）".format(age / 3600)
    except (ValueError, TypeError):
        return False, "检查点时间格式异常: {}".format(ts_str)


# ========== 主流程 ==========

def run_pre_gate(skill_dir=None, check_only=False):
    """执行前置门禁检查。

    Args:
        skill_dir: 指定技能目录（默认为本技能目录）。
        check_only: 仅检查不写检查点。

    Returns:
        (all_passed: bool, report: str)
    """
    sd = skill_dir or SKILL_DIR
    lines = []
    lines.append("=" * 64)
    lines.append("pre_gate_guard.py — 前置门禁 v1.0 (集群Ultra)")
    lines.append("=" * 64)
    lines.append("")

    # 执行7项前置检查
    checks = [
        ("P1", "SKILL.md完整性", check_skill_md(sd)),
        ("P2", "硬门禁速查块", check_hard_gate_block(sd)),
        ("P3", "规则护盾基线", check_rule_shield(sd)),
        ("P4", "脚本可编译性", check_scripts_compile(sd)),
        ("P5", "核心脚本齐全", check_core_scripts(sd)),
        ("P6", "SKILL.md体积", check_skill_size(sd)),
        ("P7", "步骤标识状态机", check_step_counter(sd)),
    ]

    total_pass = 0
    total_fail = 0
    checks_result = {}

    for cid, name, result in checks:
        passed, detail = result
        checks_result[cid] = (passed, detail)
        if passed:
            total_pass += 1
            status = "OK"
        else:
            total_fail += 1
            status = "XX"
        lines.append("[{}] {}...".format(cid, name))
        lines.append("  {} {}".format(status, detail))
        lines.append("")

    all_passed = total_fail == 0

    # 写检查点
    if all_passed and not check_only:
        cp_passed, cp_detail = write_checkpoint(checks_result, sd)
        lines.append("[CHECKPOINT] 写入检查点...")
        lines.append("  {} {}".format("OK" if cp_passed else "XX", cp_detail))
        lines.append("")
    elif not all_passed and not check_only:
        lines.append("[CHECKPOINT] 跳过（检查未全部通过）")
        lines.append("")

    # 汇总
    lines.append("=" * 64)
    lines.append("Pre-gate summary: {} PASS / {} FAIL".format(total_pass, total_fail))
    lines.append("")

    if all_passed:
        lines.append("=" * 64)
        lines.append("Pre-gate result: PASS (前置门禁通过，任务可继续)")
        lines.append("=" * 64)
    else:
        lines.append("=" * 64)
        lines.append("XX Pre-gate result: FAIL ({}项失败，⛔禁止继续，须修复后重跑)".format(total_fail))
        lines.append("    提示：前置门禁未通过，禁止继续后续流程")
        lines.append("=" * 64)

    return all_passed, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="pre_gate_guard.py — 前置门禁 v1.0 (集群Ultra)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0 = ALL PASS (检查点已写入，任务可继续)\n"
            "  1 = ANY FAIL (⛔禁止继续)\n"
            "  2 = runtime error\n"
        )
    )
    parser.add_argument(
        "--check-only", action="store_true", default=False,
        help="仅检查不写检查点文件"
    )
    parser.add_argument(
        "--verify-checkpoint", action="store_true", default=False,
        help="验证检查点是否存在且有效（供 gate_guard G8 调用）"
    )
    parser.add_argument(
        "--target-skill", default=None,
        help="检查指定技能目录（默认为本技能目录）"
    )
    args = parser.parse_args()

    # 验证检查点模式
    if args.verify_checkpoint:
        passed, detail = verify_checkpoint(skill_dir=args.target_skill)
        print("=" * 64)
        print("pre_gate_guard.py — 检查点验证")
        print("=" * 64)
        print("")
        print("[VERIFY] pre_gate_checkpoint.json...")
        print("  {} {}".format("OK" if passed else "XX", detail))
        print("")
        if passed:
            print("PASS")
        else:
            print("FAIL")
        sys.exit(0 if passed else 1)

    # 确定技能目录
    skill_dir = args.target_skill if args.target_skill else SKILL_DIR
    if args.target_skill and not os.path.isdir(args.target_skill):
        print("Error: target skill directory not found: {}".format(args.target_skill), file=sys.stderr)
        sys.exit(2)

    # 执行前置门禁
    passed, report = run_pre_gate(skill_dir=skill_dir, check_only=args.check_only)
    print(report)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()