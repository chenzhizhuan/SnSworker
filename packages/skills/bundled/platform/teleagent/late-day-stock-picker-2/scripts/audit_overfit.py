#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 过拟合审计 / 参数敏感性分析（2026.9.9 新增）

作用：
  1. 样本量诚实统计 —— 用数据说话，避免"几个样本就调参"的过度自信
  2. 名义 vs 净收益口径对照 —— 成本 0.30% 下的真实净值
  3. 分档门槛敏感性分析 —— 70分附近"贴线"风险有多大
  4. 候选池参数敏感性框架 —— 基于 run_and_save 保存的 candidates_pool 做网格扫描

用法：
    python scripts/audit_overfit.py                          # 自动定位 runs 目录
    python scripts/audit_overfit.py --runs_dir <运行数据目录>  # 指定目录

调参纪律（重要）：
  - 历史样本远不足统计显著性（约36交易日/43只一档）时，禁止凭几天行情调参
  - 结论依据：样本量 < 50 → 参数冻结；≥ 50 后复跑本审计再决策
  - 每次调参前：先备份 config_parameters.py，跑本审计留档，改后回测对比
"""

import argparse
import json
import os
import sys

# 成本口径（与 trading_cost.py / config_parameters.COST 保持一致）
ROUND_TRIP_COST = 0.003

# 分档门槛扫描点
SCORE_THRESHOLDS = [50, 55, 60, 65, 68, 70, 73, 76, 80, 85]

# 尝试引入集中参数（扫描范围），失败不影响核心功能
try:
    from config_parameters import SCAN_RANGES
except Exception:
    SCAN_RANGES = None


def default_runs_dir():
    """动态定位默认运行目录：技能包内 workspace_scripts/runs"""
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(os.path.dirname(here), 'workspace_scripts', 'runs')
    if os.path.exists(candidate):
        return candidate
    # 兜底：扫描用户目录下的 late-day-stock-picker-2 技能包
    root = os.environ.get('USERPROFILE', '')
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.endswith('workspace_scripts'):
            p = os.path.join(dirpath, 'runs')
            if os.path.exists(p):
                return p
        if dirpath.count(os.sep) - root.count(os.sep) > 7:
            dirnames[:] = []
    return candidate


def load_runs(runs_dir):
    """读取所有 run JSON，按日期聚合

    返回: {date: {'slot': int, 'data': dict}} 按日期排序
    """
    if not os.path.isdir(runs_dir):
        return {}
    by_date = {}
    for f in sorted(os.listdir(runs_dir)):
        if not f.endswith('.json'):
            continue
        path = os.path.join(runs_dir, f)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            continue
        date = data.get('date', f[:10])
        slot = data.get('run_slot', 0)
        by_date.setdefault(date, {})[slot] = data
    return by_date


def collect_samples(runs):
    """把每日期（取当日最后一轮）的全部候选样本汇总，返回 [{'date','score'}...] 和逐日统计"""
    samples = []
    tier_counts = {}
    for date in sorted(runs.keys()):
        slots = runs[date]
        last_slot = max(slots.keys())
        data = slots[last_slot]
        pool = data.get('candidates_pool') or (data.get('tier1', []) + data.get('tier2', []))
        t1 = len(data.get('tier1', []))
        t2 = len(data.get('tier2', []))
        tier_counts[date] = {'tier1': t1, 'tier2': t2, 'pool': len(pool)}
        for st in pool:
            samples.append({'date': date, 'score': st.get('score', 0)})
    return samples, tier_counts


def sample_honest_stats(all_day, tier_counts):
    """样本量诚实统计"""
    dates = sorted(tier_counts.keys())
    t1_total = sum(v['tier1'] for v in tier_counts.values())
    t2_total = sum(v['tier2'] for v in tier_counts.values())
    pool_total = sum(v['pool'] for v in tier_counts.values())
    print('=' * 62)
    print('  1. 样本量诚实统计')
    print('=' * 62)
    print(f'  有效交易日数   : {len(dates)} 天')
    print(f'  一档累计样本   : {t1_total} 只')
    print(f'  二档累计样本   : {t2_total} 只')
    print(f'  候选池累计样本 : {pool_total} 只')
    print()
    if len(dates) < 30:
        print('  ⚠ 样本量不足30个交易日 → 任何参数结论均不具统计显著性，参数应冻结。')
        print('     建议：待积累≥50个有效样本后复跑本审计再决定是否调参。')
    elif len(dates) < 60:
        print('  ⚠ 样本量中等，结论参考价值有限，谨慎调参。')
    else:
        print('  ✓ 样本量较充分，可进行有意义的敏感性分析。')
    print()
    # 逐日明细（仅打印最近10日）
    print('  最近10个交易日明细：')
    print(f'  {"日期":<12} {"一档":>4} {"二档":>4} {"候选池":>6}')
    for d in dates[-10:]:
        v = tier_counts[d]
        print(f'  {d:<12} {v["tier1"]:>4} {v["tier2"]:>4} {v["pool"]:>6}')
    print()


def threshold_sensitivity(all_day):
    """分档门槛敏感性分析：同一批候选样本在不同分数门槛下的入选数"""
    print('=' * 62)
    print('  2. 分档门槛敏感性分析（70分附近"贴线"风险）')
    print('=' * 62)
    print(f'  {"门槛":>6} {"入选数":>6}  相对70分变化')
    base = sum(1 for s in all_day if s['score'] >= 70)
    for t in SCORE_THRESHOLDS:
        n = sum(1 for s in all_day if s['score'] >= t)
        if t == 70:
            print(f'  {t:>6} {n:>6}   ← 当前一档线')
        else:
            diff = n - base
            marker = '（贴线风险：门槛附近样本密度高）' if abs(diff) <= max(3, base // 5) else ''
            print(f'  {t:>6} {n:>6}  {diff:+5d} {marker}')
    if base > 0:
        near = sum(1 for s in all_day if 65 <= s['score'] < 75)
        print(f'\n  65~75分贴线样本：{near} 只（占比 {near / max(len(all_day), 1) * 100:.1f}%）')
        print('  → 若大量样本贴着70分线，说明分档对该区间参数高度敏感，回测容易失真。')
    print()


def cost_nominal_compare():
    """名义 vs 净收益口径对照表"""
    print('=' * 62)
    print('  3. 交易成本口径对照（往返≈0.30%）')
    print('=' * 62)
    print(f'   {"名义涨幅":>8} {"净收益":>8}')
    for nom in (-5, -3, -2, -1, 0, 1, 2, 3, 5, 8):
        net = nom - ROUND_TRIP_COST * 100
        print(f'   {nom:+6.1f}%  {net:+7.2f}%')
    print(f'\n  结论：平均盈利 +1% 量级时，扣成本后净值显著低于名义，')
    print('  回测/胜率评估必须采用净收益口径（verify_v4 净收益列）。')
    print()


def param_scan_framework(all_day, runs_dir):
    """候选池参数敏感性框架（框架已就位，依赖 candidates_pool 数据积累）"""
    print('=' * 62)
    print('  4. 候选池参数敏感性扫描框架')
    print('=' * 62)
    if not all_day:
        print('  候选池无数据，跳过扫描。')
        print()
        return
    n = len(all_day)
    scores = [s['score'] for s in all_day]
    avg = sum(scores) / n
    print(f'  候选池规模: {n} 只 | 平均分: {avg:.1f} | 分布: min={min(scores):.0f} max={max(scores):.0f}')
    print()
    if SCAN_RANGES:
        print('  已加载 config_parameters.SCAN_RANGES 扫描范围（示例）:')
        for k, v in SCAN_RANGES.items():
            print(f'    {k:<20}: {v}')
        print()
        print('  → 待积累候选池≥20个交易日数据后，启用逐参数网格回测（见 audit 说明）。')
    else:
        print('  未加载扫描范围配置（config_parameters.py 缺失），仅提供框架。')
    print()
    print('  提示：参数敏感性扫描需 candidates_pool 完整候选（run_and_save_v4 已开始保存）。')
    print()


def main():
    parser = argparse.ArgumentParser(description='尾盘选股 过拟合审计 / 参数敏感性分析')
    parser.add_argument('--runs_dir', default=None, help='运行数据目录（run JSON 所在）')
    args = parser.parse_args()

    runs_dir = args.runs_dir or default_runs_dir()
    if not os.path.isdir(runs_dir):
        print(f'[错误] 运行数据目录不存在: {runs_dir}')
        print('  请用 --runs_dir 指定正确的目录，例如: python audit_overfit.py --runs_dir "D:\\...\\workspace_scripts\\runs"')
        return 1

    print('尾盘选股 过拟合审计 / 参数敏感性分析（2026.9.9）')
    print(f'数据目录: {runs_dir}')
    print()

    runs = load_runs(runs_dir)
    if not runs:
        print('[警告] 未找到任何 run JSON，请检查目录内容。')
        return 1

    all_day, tier_counts = collect_samples(runs)
    sample_honest_stats(all_day, tier_counts)
    threshold_sensitivity(all_day)
    cost_nominal_compare()
    param_scan_framework(all_day, runs)

    print('=' * 62)
    print('  审计结论（2026.9.9 基调）')
    print('=' * 62)
    print('  当前样本量不足 → 参数冻结，勿凭几天行情调参；')
    print('  积累≥50个有效样本后复跑本脚本再决定是否调整阈值。')
    return 0


if __name__ == '__main__':
    sys.exit(main())