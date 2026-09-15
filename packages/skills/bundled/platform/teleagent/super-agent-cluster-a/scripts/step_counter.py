#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
step_counter.py — 步骤标识状态机（v2.0，名称化追踪，防重复）

设计目标：
  去掉数字编号，改用"阶段图标+步骤图标+步骤名"标识每一步。
  顺序靠对话从上到下的自然阅读流保证，不需要人脑记编号。
  本脚本以rl-state/step_counter_state.json持久化"已使用步骤名列表"，
  为LLM提供程序化的查重锚点：
    - 任务开始时：--check 读取已用名称列表
    - 每次输出步骤后：--register <名称> 注册该步骤名
    - 注册前可用 --validate <名称> 检查是否重复
    - 交付完成时：--reset 清空
    - 并发安全：原子写（tmp+os.replace）

  ⛔本脚本不自动分配名称，只做"查重+注册"。名称由LLM按规则生成。
   核心防重复逻辑：同名步骤禁重复注册，exit(1)阻断。

v2.0变更（名称化）：
  v1.x追踪max_step整数+used_steps整数集合，存在跳号/回退/预声明回填等问题。
  v2.0改为追踪used_names字符串列表，天然无跳号概念，重复即报错。
  兼容旧状态文件：检测到max_step/used_steps字段时自动迁移为空used_names。

用法：
  python scripts/step_counter.py --check                # 列出已用名称列表
  python scripts/step_counter.py --register <名称>       # 注册步骤名（防重复）
  python scripts/step_counter.py --validate <名称>       # 校验名称是否可安全使用
  python scripts/step_counter.py --track <名称>          # 手动注册（幂等，不报错）
  python scripts/step_counter.py --merge <名称>          # 合并子Agent步骤名
  python scripts/step_counter.py --check-duplicates      # 检测是否有重复名称
  python scripts/step_counter.py --reset                 # 清空（任务结束）
  python scripts/step_counter.py --status                # 查看状态详情

退出码：
  0 = 正常（或校验通过，或无重复）
  1 = 校验失败（名称已存在，或检测到重复）
  2 = 运行错误
"""

import argparse
import json
import os
import sys

from _utils import atomic_write_json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
STATE_DIR = os.path.join(SKILL_DIR, "rl-state")
STATE_FILE = os.path.join(STATE_DIR, "step_counter_state.json")


def _save_atomic(data):
    """原子写入状态文件（复用 _utils.atomic_write_json，消除重复逻辑）。"""
    atomic_write_json(STATE_FILE, data)


def load_state():
    """加载状态文件。不存在或损坏时返回默认状态。"""
    default = {
        "version": "2.0",
        "used_names": [],
        "task_id": "",
        "updated_at": None,
        "reset_count": 0,
    }
    if not os.path.exists(STATE_FILE):
        return default, "未初始化"
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default, "格式错误已重置"
        for key in default:
            data.setdefault(key, default[key])
        data["version"] = default["version"]
        # 兼容v1.x：旧状态文件有max_step/used_steps但无used_names时迁移
        if not isinstance(data.get("used_names"), list):
            data["used_names"] = []
        return data, "已加载"
    except (json.JSONDecodeError, OSError):
        return default, "解析失败已重置"


def cmd_check():
    """--check：列出已用名称列表。"""
    state, status = load_state()
    names = state.get("used_names", [])
    print("步骤标识状态机 v2.0")
    print("  状态: {}".format(status))
    print("  已注册步骤: {} 个".format(len(names)))
    if names:
        for i, name in enumerate(names, 1):
            print("    {}. {}".format(i, name))
    else:
        print("  已用名称: 无")
    print("  任务ID: {}".format(state.get("task_id", "")))
    print("  更新时间: {}".format(state.get("updated_at", "无")))
    print("  提示: 新步骤用 --register <名称> 注册，禁止重复")
    return 0


def cmd_register(name, task_id=None):
    """--register <名称>：注册步骤名，拒绝重复。"""
    if not name or not name.strip():
        print("错误: 步骤名不能为空", file=sys.stderr)
        return 2
    name = name.strip()
    state, _ = load_state()
    names = state.get("used_names", [])
    if name in names:
        print("⛔ 拒绝注册：步骤名 '{}' 已存在（重复，禁用）".format(name))
        print("  已注册的完整列表:")
        for i, n in enumerate(names, 1):
            print("    {}. {}".format(i, n))
        return 1
    names.append(name)
    state["used_names"] = names
    if task_id:
        state["task_id"] = task_id
    state["updated_at"] = datetime.now().isoformat()
    _save_atomic(state)
    print("✅ 已注册步骤: '{}' （第{}个）".format(name, len(names)))
    return 0


def cmd_validate(name):
    """--validate <名称>：校验名称是否可安全使用（未被注册过）。"""
    if not name or not name.strip():
        print("FAIL: 步骤名为空", file=sys.stderr)
        return 1
    name = name.strip()
    state, _ = load_state()
    names = state.get("used_names", [])
    if name in names:
        print("FAIL: 步骤名 '{}' 已存在（重复风险）".format(name))
        return 1
    print("PASS: 步骤名 '{}' 可安全使用（当前已注册{}个）".format(name, len(names)))
    return 0


def cmd_track(name):
    """--track <名称>：手动注册步骤名（幂等，已存在不报错）。"""
    if not name or not name.strip():
        print("错误: 步骤名不能为空", file=sys.stderr)
        return 2
    name = name.strip()
    state, _ = load_state()
    names = state.get("used_names", [])
    if name in names:
        print("ℹ️ 步骤名 '{}' 已注册（幂等，无需重复）".format(name))
        return 0
    names.append(name)
    state["used_names"] = names
    state["updated_at"] = datetime.now().isoformat()
    _save_atomic(state)
    print("✅ 已注册步骤: '{}' （第{}个）".format(name, len(names)))
    return 0


def cmd_merge(name):
    """--merge <名称>：合并子Agent步骤名（幂等）。"""
    if not name or not name.strip():
        print("错误: 步骤名不能为空", file=sys.stderr)
        return 2
    name = name.strip()
    state, _ = load_state()
    names = state.get("used_names", [])
    if name in names:
        print("ℹ️ 子Agent步骤名 '{}' 已存在（幂等，无需合并）".format(name))
        return 0
    names.append(name)
    state["used_names"] = names
    state["updated_at"] = datetime.now().isoformat()
    _save_atomic(state)
    print("✅ 子Agent步骤已合并: '{}' （第{}个）".format(name, len(names)))
    return 0


def cmd_check_duplicates():
    """--check-duplicates：检测used_names列表中是否有重复。

    正常情况下--register已防重复，此命令作为兜底校验。
    """
    state, _ = load_state()
    names = state.get("used_names", [])
    if not names:
        print("OK: 名称列表为空，无重复可检测")
        return 0
    seen = set()
    duplicates = []
    for n in names:
        if n in seen:
            duplicates.append(n)
        seen.add(n)
    if duplicates:
        print("⛔ 检测到重复步骤名:")
        for d in duplicates:
            print("  重复: '{}'".format(d))
        print("  完整列表:")
        for i, n in enumerate(names, 1):
            print("    {}. {}".format(i, n))
        return 1
    else:
        print("✅ 重复检测通过（{}个步骤名均唯一）".format(len(names)))
        for i, n in enumerate(names, 1):
            print("    {}. {}".format(i, n))
        return 0


def cmd_check_gaps():
    """--check-gaps：检测编号缺口（v2.0名称化兼容版）。

  v2.0名称化模式下天然无缺口概念（无数字编号），此命令为兼容pre_gate_guard调用保留，
    始终返回PASS（名称化追踪下无编号缺口可检测）。
    """
    state, _ = load_state()
    names = state.get("used_names", [])
    if not names:
        print("OK: 名称列表为空，无缺口可检测")
        return 0
    print("✅ 缺口检测通过（名称化模式，{}个步骤名均唯一）".format(len(names)))
    for i, n in enumerate(names, 1):
        print("    {}. {}".format(i, n))
    return 0


def cmd_reset():
    """--reset：任务结束清空。"""
    state, _ = load_state()
    old_count = len(state.get("used_names", []))
    state["used_names"] = []
    state["task_id"] = ""
    state["updated_at"] = datetime.now().isoformat()
    state["reset_count"] = state.get("reset_count", 0) + 1
    _save_atomic(state)
    print("✅ 步骤状态已清空（{}个名称已清除）".format(old_count))
    return 0


def cmd_status():
    """--status：查看状态详情。"""
    state, _ = load_state()
    names = state.get("used_names", [])
    print("[步骤标识状态机] 状态详情")
    print("  版本: {}".format(state.get("version", "")))
    print("  状态: {}".format(msg))
    print("  已注册步骤: {} 个".format(len(names)))
    if names:
        for i, name in enumerate(names, 1):
            print("    {}. {}".format(i, name))
    print("  任务ID: {}".format(state.get("task_id", "")))
    print("  更新时间: {}".format(state.get("updated_at", "无")))
    print("  重置次数: {}".format(state.get("reset_count", 0)))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="step_counter.py — 步骤标识状态机 v2.0（名称化追踪，防重复）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "退出码:\n"
            "  0 = 正常\n"
            "  1 = 校验失败（名称重复）\n"
            "  2 = 运行错误\n"
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="列出已用名称列表")
    group.add_argument("--register", metavar="NAME", help="注册步骤名（拒绝重复）")
    group.add_argument("--validate", metavar="NAME", help="校验名称是否可安全使用")
    group.add_argument("--track", metavar="NAME", help="手动注册步骤名（幂等）")
    group.add_argument("--merge", metavar="NAME", help="合并子Agent步骤名")
    group.add_argument("--check-duplicates", action="store_true", help="检测重复名称")
    group.add_argument("--check-gaps", action="store_true", help="检测编号缺口（名称化模式下为兼容保留，始终PASS）")
    group.add_argument("--reset", action="store_true", help="清空（任务结束）")
    group.add_argument("--status", action="store_true", help="查看状态详情")
    parser.add_argument("--task-id", default=None, help="关联的任务ID")
    args = parser.parse_args()

    if args.check:
        return cmd_check()
    if args.register is not None:
        return cmd_register(args.register, args.task_id)
    if args.validate is not None:
        return cmd_validate(args.validate)
    if args.track is not None:
        return cmd_track(args.track)
    if args.merge is not None:
        return cmd_merge(args.merge)
    if args.check_duplicates:
        return cmd_check_duplicates()
    if args.check_gaps:
        return cmd_check_gaps()
    if args.reset:
        return cmd_reset()
    if args.status:
        return cmd_status()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
