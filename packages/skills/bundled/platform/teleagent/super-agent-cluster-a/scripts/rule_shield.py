#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule Shield - 强制规则护盾
============================
给技能里的强制规则拍"身份证照"，以后每次升级后重新拍一张对比，
规则少了/被改了立刻报警。

v2026.09.01 增强（双技能同步）：
  - 基线新增 schema_version 版本号字段，检测脚本升级后基线过旧
  - smart-check 新增"净变化保护"：规则消失不自动处理，且净变化为负时报警
  - 新增 SKILL.md 体积预警 --size-check（截断阈值 40KB）
  - 去除高噪音单字词（应该/应当/需要），改用强语义短语（应确保/需确保等）
  - 新增 keyword_stats 与 history 基线字段，记录规则数变化趋势

用法：
  # 首次建立基线（拍存档照）
  python rule_shield.py --init

  # 对比检查（升级后运行）
  python rule_shield.py --check

  # 更新基线（确认规则变更后）
  python rule_shield.py --update

  # 查看当前规则清单
  python rule_shield.py --list

  # SKILL.md 体积预警（截断风险）
  python rule_shield.py --size-check
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

# ============================================================
# 配置
# ============================================================

# 脚本所在目录的上一级 = 技能根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

# 扫描的文件列表（相对于技能根目录）
# v2026.09.06：新增12个拆分文件（pt2/pt3/pt4），确保拆分后规则不脱离扫描范围
SCAN_FILES = [
    "SKILL.md",
    "references/swarm-agents.md",
    "references/swarm-agents-pt2.md",
    "references/communication-protocol.md",
    "references/execution-guide.md",
    "references/execution-guide-pt2.md",
    "references/quality-rules.md",
    "references/k3-enhancement-modules.md",
    "references/k3-enhancement-pt2.md",
    "references/step-transparency-examples.md",
    "references/step-transparency-examples-pt2.md",
    "references/step-transparency-examples-pt3.md",
    "references/security-ops-guide.md",
    "references/security-ops-guide-pt2.md",
    "references/security-ops-guide-pt3.md",
    "references/security-ops-guide-pt4.md",
]

# 基线文件存放位置
BASELINE_PATH = os.path.join(SKILL_DIR, "rl-state", "rule_shield_baseline.json")

# 基线结构版本号——脚本升级后若基线过旧则提示重建
SCHEMA_VERSION = "1.1.0"

# SKILL.md 截断风险阈值（字节）：与执行边界文档中的 43KB 截断线对应
TRUNCATION_WARN_BYTES = 40000
TRUNCATION_HARD_BYTES = 43000
# SKILL.md 体积上限（硬门禁，字节）：v2026.09.04 新增，超限禁止交付
SIZE_LIMIT_BYTES = 36864

# v3.6.2: 使用共享原子写入函数
from _utils import atomic_write_json

# 强制规则关键词——命中任一即认为该行是强制规则
# v2026.09.01：移除高噪音单字词"应该/应当/需要"（命中率过高且多为说明性文本），
# 由 RULE_KEYWORDS_STRONG 强语义短语覆盖（口径对齐 super-hatching-master 版）。
RULE_KEYWORDS = [
    "⛔",
    "强制",
    "禁止",
    "不可跳过",
    "必须",
    "不得",
    "严禁",
    "务必",
    "100%",
    "must",
    "mandatory",
    "must not",
    "never",
    "required",
    "shall",
    "不允许",
    "确保",
    "不得低于",
    "至少",
]

# 强语义短语——替代高噪单字词，命中率低但语义确切的强约束词
# 统计口径 = RULE_KEYWORDS(19) + RULE_KEYWORDS_STRONG(8) = 27 个强约束关键词
RULE_KEYWORDS_STRONG = [
    "应确保",
    "需要确保",
    "需确保",
    "应执行",
    "需要执行",
    "应遵守",
    "应遵循",
    "需要提供",
]

# 排除的关键词——包含这些的行不算强制规则（减少噪音）
EXCLUDE_PATTERNS = [re.compile(p) for p in [
    r"^\s*```",          # 代码块边界
    r"^\s*---",           # YAML边界
    r"^\s*\|.*\|.*\|",   # 纯表格行（含|但不含关键词的不该到这一步）
    r"^\s*#{1,6}\s*$",    # 空标题
]]

# 智能发现模式——正则匹配含有强制语义但未被关键词命中的行
# 这些模式捕捉“遗漏的强制规则”——句子结构暗示强制性
DISCOVERY_PATTERNS = [re.compile(p) for p in [
    r"不可省略",
    r"缺一不可",
    r"不允许省略",
    r"退回.*补",
    r"拒绝.*通过",
    r"判定.*未完成",
    r"判定.*未通过",
    r"否则.*拒绝",
    r"缺少.*退回",
    r"缺失.*退回",
    r"禁止笼统",
    r"独立[Ss]tep",
    r"独立步骤",
]]

# 每条规则记录的字段
# - file: 文件相对路径
# - line_no: 行号
# - text: 行原文（去除首尾空格）
# - keyword: 命中的关键词
# - rule_hash: 该行内容的SHA256前16位（用于检测内容变化）


# ============================================================
# 核心逻辑
# ============================================================

def is_rule_line(line):
    """判断一行是否是强制规则行"""
    stripped = line.strip()
    if not stripped or len(stripped) < 5:
        return False, None

    # 排除模式（已预编译）
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(stripped):
            return False, None

    # 关键词命中
    line_lower = stripped.lower()
    for kw in RULE_KEYWORDS:
        if kw.lower() in line_lower:
            return True, kw

    # 强语义短语命中（替代高噪单字词“应/需要”）
    for kw in RULE_KEYWORDS_STRONG:
        if kw.lower() in line_lower:
            return True, kw

    # 智能发现模式命中（已预编译）
    for pattern in DISCOVERY_PATTERNS:
        match = pattern.search(stripped)
        if match:
            return True, "smart:" + match.group(0)

    return False, None


def extract_text_for_hash(line):
    """提取行文本用于哈希——去除空格变化带来的假阳性"""
    # 移除首尾空格、合并连续空格
    text = re.sub(r"\s+", " ", line.strip())
    return text


def compute_hash(text):
    """计算文本的SHA256前16位"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def scan_rules(skill_dir):
    """扫描所有文件，提取强制规则"""
    rules = []
    for rel_path in SCAN_FILES:
        abs_path = os.path.join(skill_dir, rel_path)
        if not os.path.exists(abs_path):
            print("  [WARN] 文件不存在，跳过: {}".format(rel_path))
            continue

        # B15修复：文件读取异常处理，避免编码损坏或权限不足中断扫描
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    is_rule, keyword = is_rule_line(line)
                    if is_rule:
                        clean_text = extract_text_for_hash(line)
                        rule_hash = compute_hash(clean_text)
                        rules.append({
                            "file": rel_path,
                            "line_no": i,
                            "text": line.strip(),
                            "keyword": keyword,
                            "rule_hash": rule_hash,
                        })
        except (IOError, OSError, UnicodeDecodeError) as e:
            print("  [WARN] 文件读取失败，跳过: {} ({})".format(rel_path, e))
            continue

    return rules


def _build_baseline_dict(rules, old_baseline, skill_dir):
    """构建基线字典（统一入口，消除三处重复构建）。"""
    now = datetime.now().isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": (old_baseline.get("created_at", now) if old_baseline else now),
        "updated_at": now,
        "skill_dir": os.path.basename(skill_dir),
        "total_rules": len(rules),
        "files_scanned": len(SCAN_FILES),
        "keyword_stats": _build_keyword_stats(rules),
        "history": (old_baseline.get("history", []) if old_baseline else [])[-20:],
        "rules": rules,
    }


def build_baseline(skill_dir):
    """建立基线并建立存档照"""
    print("=" * 60)
    print("Rule Shield - 建立基线")
    print("=" * 60)

    rules = scan_rules(skill_dir)

    baseline = _build_baseline_dict(rules, None, skill_dir)
    baseline["created_at"] = datetime.now().isoformat()  # 新建时创建时间=更新时间

    # 确保目录存在
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)

    atomic_write_json(BASELINE_PATH, baseline)

    print("\n基线已建立:")
    print("  基线版本: {}".format(SCHEMA_VERSION))
    print("  扫描文件: {} 个".format(len(SCAN_FILES)))
    print("  提取规则: {} 条".format(len(rules)))
    print("  基线文件: {}".format(BASELINE_PATH))

    # 按文件统计
    file_counts = {}
    for r in rules:
        file_counts[r["file"]] = file_counts.get(r["file"], 0) + 1

    print("\n各文件规则数:")
    for f, c in sorted(file_counts.items()):
        print("  {:<50} {} 条".format(f, c))

    print("\n基线建立完成。以后升级后运行 --check 即可对比。")
    return baseline


def load_baseline():
    """加载基线"""
    if not os.path.exists(BASELINE_PATH):
        print("[ERROR] 基线文件不存在: {}".format(BASELINE_PATH))
        print("请先运行: python rule_shield.py --init")
        return None
    # B16修复：补全异常处理（v3.11: 简化OSError + 补UnicodeDecodeError + total_rules保护）
    try:
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            baseline = json.load(f)
        # 版本号兼容：旧基线无 schema_version 时提示重建（不阻断）
        if "schema_version" not in baseline:
            print("[WARN] 基线缺少 schema_version 字段（旧版基线）。")
            print("  建议运行: python rule_shield.py --update 升级基线结构。")
            baseline["schema_version"] = "unknown"
        elif baseline["schema_version"] != SCHEMA_VERSION:
            print("[WARN] 基线版本 {} 与脚本版本 {} 不一致。".format(
                baseline["schema_version"], SCHEMA_VERSION))
            print("  建议运行: python rule_shield.py --update 升级基线。")
        # v3.11 fix: 补全缺失的 total_rules 字段防 KeyError
        if "total_rules" not in baseline:
            baseline["total_rules"] = 0
        # v5.1 fix: 补全缺失的 rules 键防 _classify_diffs KeyError
        if "rules" not in baseline:
            baseline["rules"] = []
        return baseline
    except json.JSONDecodeError as e:
        print("[ERROR] 基线文件损坏，无法解析JSON: {}".format(e))
        print("请运行: python rule_shield.py --init 重新建立基线")
        return None
    except (OSError, UnicodeDecodeError) as e:
        print("[ERROR] 基线文件读取失败: {}".format(e))
        print("请检查文件权限或运行: python rule_shield.py --init 重新建立基线")
        return None


def _build_keyword_stats(rules):
    """统计规则关键词分布，写入基线供审计"""
    return dict(Counter(r["keyword"] for r in rules))


def _classify_diffs(baseline, current_rules):
    """分类基线与当前规则的差异，返回(disappeared, new_rules, moved)。

    使用 defaultdict(list) 按 rule_hash 分组，避免相同文本规则（不同文件/行号）
    被字典推导式吞并导致检测遗漏（P1-2修复）。
    """
    baseline_hashes = defaultdict(list)
    for r in baseline["rules"]:
        baseline_hashes[r["rule_hash"]].append(r)
    current_hashes = defaultdict(list)
    for r in current_rules:
        current_hashes[r["rule_hash"]].append(r)

    disappeared = []    # 基线有、现在没有 = 规则消失了
    new_rules = []      # 现在有、基线没有 = 新增规则
    moved = []          # 哈希相同但行号变了 = 规则还在但位置变了

    for bh, br_list in baseline_hashes.items():
        cr_list = current_hashes.get(bh, [])
        # 同哈希规则数量比对：基线多出的部分视为消失
        for br in br_list[len(cr_list):]:
            disappeared.append(br)
        # 位置变动比对：逐条配对
        for br, cr in zip(br_list, cr_list):
            if br["file"] != cr["file"] or br["line_no"] != cr["line_no"]:
                moved.append({
                    "rule": br,
                    "old_file": br["file"],
                    "old_line": br["line_no"],
                    "new_file": cr["file"],
                    "new_line": cr["line_no"],
                })

    for ch, cr_list in current_hashes.items():
        br_list = baseline_hashes.get(ch, [])
        # 当前多出的部分判定为新增
        for cr in cr_list[len(br_list):]:
            new_rules.append(cr)

    return disappeared, new_rules, moved


def check_rules(skill_dir):
    """对比检查——升级后运行"""
    print("=" * 60)
    print("Rule Shield - 规则对比检查")
    print("=" * 60)

    baseline = load_baseline()
    if baseline is None:
        return False

    current_rules = scan_rules(skill_dir)

    disappeared, new_rules, moved = _classify_diffs(baseline, current_rules)

    # 输出报告
    print("\n基线时间: {}".format(baseline["updated_at"]))
    print("基线规则: {} 条".format(baseline["total_rules"]))
    print("当前规则: {} 条".format(len(current_rules)))

    all_pass = True

    # 红灯——规则消失
    if disappeared:
        all_pass = False
        print("\n" + "=" * 60)
        print("[RED] 规则消失: {} 条".format(len(disappeared)))
        print("=" * 60)
        for r in disappeared:
            print("\n  文件: {}".format(r["file"]))
            print("  原行号: {}".format(r["line_no"]))
            print("  内容: {}".format(r["text"][:120]))
            print("  哈希: {}".format(r["rule_hash"]))
    else:
        print("\n[GREEN] 规则消失: 0 条")

    # 黄灯——规则位置变了
    if moved:
        print("\n" + "=" * 60)
        print("[YELLOW] 位置变动: {} 条".format(len(moved)))
        print("=" * 60)
        for m in moved:
            print("  {} L{} -> {} L{}".format(
                m["old_file"], m["old_line"],
                m["new_file"], m["new_line"]
            ))
    else:
        print("[GREEN] 位置变动: 0 条")

    # 蓝灯——新增规则
    if new_rules:
        print("\n" + "=" * 60)
        print("[BLUE] 新增规则: {} 条".format(len(new_rules)))
        print("=" * 60)
        for r in new_rules:
            print("\n  文件: {}".format(r["file"]))
            print("  行号: {}".format(r["line_no"]))
            print("  内容: {}".format(r["text"][:120]))
            print("  哈希: {}".format(r["rule_hash"]))
        print("\n  提示: 如果新增规则是有意的，运行 --update 更新基线。")
    else:
        print("[GREEN] 新增规则: 0 条")

    # 最终结论
    print("\n" + "=" * 60)
    if all_pass:
        if new_rules:
            print("[PASS] 所有原有规则完好。发现 {} 条新增规则待确认。".format(len(new_rules)))
        else:
            print("[PASS] 全部规则完好，无变动。")
    else:
        print("[FAIL] 发现 {} 条规则消失！请确认是否故意删除。".format(len(disappeared)))
        print("  - 如果是故意删除/修改: 运行 --update 更新基线")
        print("  - 如果是意外丢失: 回滚修改，恢复规则后重新运行 --check")
    print("=" * 60)

    return all_pass


def smart_check(skill_dir):
    """智能检查——自动纳入新规则，仅规则消失时报警。

    智能化逻辑：
    1. 新增规则 → 自动纳入基线保护（打印日志但不需要手动--update）
    2. 位置变动 → 自动同步基线（纯行号偏移不影响保护）
    3. 规则消失 → 报警并返回False（需人工确认是故意删除还是意外丢失）
    4. 智能发现模式命中 → 同新增规则处理
    5. 净变化保护（v2026.09.01）：规则消失数 > 新增数（净变化为负）时强制报警，
       防止"删2加2"被 smart-check 静默洗白。
    """
    print("=" * 60)
    print("Rule Shield - 智能检查（自动纳入新规则）")
    print("=" * 60)

    baseline = load_baseline()
    if baseline is None:
        return False

    current_rules = scan_rules(skill_dir)

    disappeared, new_rules, moved = _classify_diffs(baseline, current_rules)

    # 输出报告
    print("\n基线时间: {}".format(baseline["updated_at"]))
    print("基线规则: {} 条".format(baseline["total_rules"]))
    print("当前规则: {} 条".format(len(current_rules)))

    all_pass = True

    # 红灯——规则消失（仅此情况报警）
    if disappeared:
        all_pass = False
        print("\n" + "=" * 60)
        print("[RED] 规则消失: {} 条".format(len(disappeared)))
        print("=" * 60)
        for r in disappeared:
            print("\n  文件: {}".format(r["file"]))
            print("  原行号: {}".format(r["line_no"]))
            print("  内容: {}".format(r["text"][:120]))
            print("  哈希: {}".format(r["rule_hash"]))
        print("\n  [!] 规则消失需人工确认，不会自动处理。")
        print("  - 如果是故意删除/修改: 运行 --update 更新基线")
        print("  - 如果是意外丢失: 回滚修改，恢复规则后重新运行 --smart-check")
    else:
        print("\n[GREEN] 规则消失: 0 条")

    # 黄灯——位置变动（自动同步，纯信息性输出）
    if moved:
        print("\n[YELLOW] 位置变动: {} 条（自动同步，无需手动操作）".format(len(moved)))

    # 蓝灯——新增规则（自动纳入保护）
    if new_rules:
        print("\n" + "=" * 60)
        print("[BLUE] 新增规则: {} 条（自动纳入基线保护）".format(len(new_rules)))
        print("=" * 60)
        for r in new_rules:
            print("\n  文件: {}".format(r["file"]))
            print("  行号: {}".format(r["line_no"]))
            print("  命中: {}".format(r["keyword"]))
            print("  内容: {}".format(r["text"][:120]))
            print("  哈希: {}".format(r["rule_hash"]))

    # 净变化保护（v2026.09.01）：消失数 > 新增数 → 净规则减少，禁止自动洗白
    net_change = len(current_rules) - baseline["total_rules"]
    if not disappeared and net_change < 0:
        all_pass = False
        print("\n" + "=" * 60)
        print("[RED] 净变化保护触发: 规则总数净减少 {} 条（{} → {}）".format(
            abs(net_change), baseline["total_rules"], len(current_rules)))
        print("  说明: 存在内容改写导致哈希变化（新增与消失数量差为负）。")
        print("  [!] 禁止自动更新基线掩盖规则减少，需人工确认后 --update。")
        print("=" * 60)

    # 智能化变化更新基线（新增规则+位置变动自动同步，规则消失/净减少不自动处理）
    if (new_rules or moved) and not disappeared and net_change >= 0:
        # 直接用当前规则覆盖基线
        _now = datetime.now().isoformat()
        history = baseline.get("history", [])
        if baseline["total_rules"] != len(current_rules):
            history.append({
                "time": _now,
                "old_total": baseline["total_rules"],
                "new_total": len(current_rules),
                "delta": net_change,
                "disappeared": len(disappeared),
                "added": len(new_rules),
                "reason": "smart-check-auto",
            })
        # 使用统一构建函数，手动注入更新后的 history
        _temp_old = {"created_at": baseline.get("created_at", _now), "history": history}
        new_baseline = _build_baseline_dict(current_rules, _temp_old, skill_dir)
        atomic_write_json(BASELINE_PATH, new_baseline)

        diff = len(current_rules) - baseline["total_rules"]
        print("\n" + "-" * 60)
        print("基线已自动更新:")
        print("  旧规则数: {} → 新规则数: {}".format(
            baseline["total_rules"], len(current_rules)))
        if diff > 0:
            print("  自动纳入: +{} 条新规则".format(diff))
        elif diff < 0:
            print("  自动调整: {} 条（规则内容变更导致哈希变化）".format(abs(diff)))
        else:
            print("  数量不变（位置变动已同步）")
        print("  智能发现模式: {} 条规则通过模式匹配自动捕获".format(
            sum(1 for r in new_rules if r["keyword"].startswith("smart:"))))
        print("-" * 60)

    # 最终结论
    print("\n" + "=" * 60)
    if all_pass:
        if new_rules:
            print("[PASS] 原有规则全部完好。{} 条新增规则已自动纳入保护。".format(len(new_rules)))
        else:
            print("[PASS] 全部规则完好，无变动。")
    else:
        print("[FAIL] 发现 {} 条规则消失！需人工确认。".format(len(disappeared)))
    print("=" * 60)

    return all_pass


def update_baseline(skill_dir):
    """更新基线——确认规则变更后"""
    print("=" * 60)
    print("Rule Shield - 更新基线")
    print("=" * 60)

    old_baseline = load_baseline()
    rules = scan_rules(skill_dir)

    history = old_baseline.get("history", []) if old_baseline else []
    if old_baseline and old_baseline.get("total_rules") != len(rules):
        history = history + [{
            "time": datetime.now().isoformat(),
            "old_total": old_baseline.get("total_rules", 0),
            "new_total": len(rules),
            "delta": len(rules) - old_baseline.get("total_rules", 0),
            "disappeared": 0,
            "added": 0,
            "reason": "manual-update",
        }]
    # 使用统一构建函数，手动注入更新后的 history
    _temp_old = {"created_at": old_baseline.get("created_at", datetime.now().isoformat()) if old_baseline else None, "history": history}
    baseline = _build_baseline_dict(rules, _temp_old, skill_dir)
    if not old_baseline:
        baseline["created_at"] = datetime.now().isoformat()

    atomic_write_json(BASELINE_PATH, baseline)

    if old_baseline:
        diff = len(rules) - old_baseline.get("total_rules", 0)
        print("\n基线已更新:")
        print("  旧规则数: {}".format(old_baseline["total_rules"]))
        print("  新规则数: {}".format(len(rules)))
        if diff > 0:
            print("  新增: {} 条".format(diff))
        elif diff < 0:
            print("  减少: {} 条".format(abs(diff)))
        else:
            print("  总数不变")
    else:
        print("\n基线已建立: {} 条规则".format(len(rules)))

    print("  基线文件: {}".format(BASELINE_PATH))


def list_rules(skill_dir):
    """列出当前所有规则"""
    print("=" * 60)
    print("Rule Shield - 当前规则清单")
    print("=" * 60)

    rules = scan_rules(skill_dir)

    file_counts = {}
    for r in rules:
        file_counts[r["file"]] = file_counts.get(r["file"], 0) + 1

    print("\n总计: {} 条规则，分布在 {} 个文件\n".format(len(rules), len(file_counts)))

    current_file = None
    for r in rules:
        if r["file"] != current_file:
            current_file = r["file"]
            count = file_counts[current_file]
            print("\n--- {} ({} 条) ---".format(current_file, count))

        print("  L{:>4} [{}] {}".format(
            r["line_no"],
            r["keyword"],
            r["text"][:100]
        ))


def check_size(skill_dir):
    """SKILL.md 体积预警——截断风险检测。

    当文件超过 SIZE_LIMIT_BYTES(36KB) 时直接 BLOCKED 禁止交付，
    否则为 NONE。LOW/HIGH 分级已废弃不可达。
    """
    print("=" * 60)
    print("Rule Shield - SKILL.md 体积预警（截断风险）")
    print("=" * 60)

    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        print("[ERROR] SKILL.md 不存在: {}".format(skill_md))
        return 1

    size = os.path.getsize(skill_md)
    try:
        with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
            lines = sum(1 for _ in f)
    except OSError as e:
        print("[ERROR] 读取SKILL.md失败: {}".format(e))
        return 1

    print("\nSKILL.md 文件: {}".format(skill_md))
    print("  大小: {} 字节（{:.1f} KB）".format(size, size / 1024.0))
    print("  行数: {} 行".format(lines))
    print("  截断预警阈值: {} 字节（{:.1f} KB）".format(
        TRUNCATION_WARN_BYTES, TRUNCATION_WARN_BYTES / 1024.0))
    print("  截断硬阈值: {} 字节（{:.1f} KB）".format(
        TRUNCATION_HARD_BYTES, TRUNCATION_HARD_BYTES / 1024.0))
    print("  体积上限（硬门禁）: {} 字节（{:.1f} KB）".format(
        SIZE_LIMIT_BYTES, SIZE_LIMIT_BYTES / 1024.0))

    if size > SIZE_LIMIT_BYTES:
        print("\n体积风险: BLOCKED")
        print("  [⛔] SKILL.md 超过体积上限（{}字节），禁止交付，必须精简后重检。".format(SIZE_LIMIT_BYTES))
        return 1
    else:
        print("\n体积风险: NONE")
        print("  [OK] SKILL.md 体积在安全范围内，无截断风险。")
        print("=" * 60)
        return 0


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Rule Shield - 强制规则护盾",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用法示例:
  python rule_shield.py --init          # 首次建立基线
  python rule_shield.py --check         # 对比检查（升级后运行）
  python rule_shield.py --smart-check   # 智能检查（自动纳入新规则，仅消失时报警）
  python rule_shield.py --update        # 更新基线（确认规则变更后）
  python rule_shield.py --list          # 查看当前规则清单
  python rule_shield.py --size-check    # SKILL.md 体积预警（截断风险）
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true", help="首次建立基线")
    group.add_argument("--check", action="store_true", help="对比检查")
    group.add_argument("--smart-check", action="store_true", help="智能检查（自动纳入新规则）")
    group.add_argument("--update", action="store_true", help="更新基线")
    group.add_argument("--list", action="store_true", help="列出当前规则")
    group.add_argument("--size-check", action="store_true", help="SKILL.md 体积预警（截断风险）")

    args = parser.parse_args()

    if args.init:
        build_baseline(SKILL_DIR)
    elif args.check:
        success = check_rules(SKILL_DIR)
        sys.exit(0 if success else 1)
    elif args.smart_check:
        success = smart_check(SKILL_DIR)
        sys.exit(0 if success else 1)
    elif args.update:
        update_baseline(SKILL_DIR)
    elif args.list:
        list_rules(SKILL_DIR)
    elif args.size_check:
        sys.exit(check_size(SKILL_DIR))


if __name__ == "__main__":
    main()
