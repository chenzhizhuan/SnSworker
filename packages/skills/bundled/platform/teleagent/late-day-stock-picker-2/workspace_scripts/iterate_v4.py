#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三天迭代脚本2026.7.16
每个交易日15:30触发，计数器控制每3个有效交易日执行一次迭代分析。
空仓日（选股为0）不计入迭代计数器，避免连续空仓导致无效迭代。
汇总近3日预测与验证数据，识别偏差模式，输出改进建议（不自动修改参数）。
"""

import os
import sys
import json
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICT_HISTORY_DIR = os.path.join(BASE_DIR, 'predict_history')
REVIEW_HISTORY_DIR = os.path.join(BASE_DIR, 'review_history')
COUNTER_PATH = os.path.join(BASE_DIR, 'iterate_counter.dat')


def read_counter():
    """读取计数器（兼容BOM）"""
    if not os.path.exists(COUNTER_PATH):
        return 0
    try:
        with open(COUNTER_PATH, 'r', encoding='utf-8-sig') as f:
            return int(f.read().strip())
    except:
        return 0


def write_counter(val):
    """写入计数器"""
    with open(COUNTER_PATH, 'w', encoding='utf-8') as f:
        f.write(str(val))


def is_empty_day(review_data):
    """判断某天是否为空仓日（无有效标的参与统计）"""
    if review_data.get('is_empty_day', False):
        return True
    stocks = review_data.get('stocks', [])
    if len(stocks) == 0:
        return True
    # 所有标的都是skipped（暴跌日不操作）也算空仓
    participating = [s for s in stocks if not s.get('skipped', False)]
    return len(participating) == 0


def load_recent_reviews(n=3):
    """加载最近n个有效交易日（非空仓日）的复盘JSON"""
    if not os.path.exists(REVIEW_HISTORY_DIR):
        return []
    files = sorted([f for f in os.listdir(REVIEW_HISTORY_DIR) if f.endswith('.json')], reverse=True)
    reviews = []
    for f in files:
        try:
            with open(os.path.join(REVIEW_HISTORY_DIR, f), 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                reviews.append(data)
        except:
            pass
        if len(reviews) >= n:
            break
    return reviews


def load_recent_predicts(n=3):
    """加载最近n个交易日的预判JSON"""
    if not os.path.exists(PREDICT_HISTORY_DIR):
        return []
    files = sorted([f for f in os.listdir(PREDICT_HISTORY_DIR) if f.endswith('.json')], reverse=True)
    predicts = []
    for f in files[:n]:
        try:
            with open(os.path.join(PREDICT_HISTORY_DIR, f), 'r', encoding='utf-8') as fh:
                predicts.append(json.load(fh))
        except:
            pass
    return predicts


def load_accuracy_csv(n=3):
    """读取prediction_accuracy.csv最近n行"""
    csv_path = os.path.join(BASE_DIR, 'prediction_accuracy.csv')
    if not os.path.exists(csv_path):
        return []
    rows = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except:
        pass
    return rows[-n:] if len(rows) >= n else rows


def load_all_recent_reviews(n=10):
    """加载最近n个交易日（含空仓日）的复盘JSON，用于统计空仓趋势"""
    if not os.path.exists(REVIEW_HISTORY_DIR):
        return []
    files = sorted([f for f in os.listdir(REVIEW_HISTORY_DIR) if f.endswith('.json')], reverse=True)
    reviews = []
    for f in files[:n]:
        try:
            with open(os.path.join(REVIEW_HISTORY_DIR, f), 'r', encoding='utf-8') as fh:
                reviews.append(json.load(fh))
        except:
            pass
    return reviews


def load_predict_map():
    """预加载所有预判JSON的market_env，用于补全review中的大盘环境"""
    predict_map = {}
    if os.path.exists(PREDICT_HISTORY_DIR):
        for f in os.listdir(PREDICT_HISTORY_DIR):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(PREDICT_HISTORY_DIR, f), 'r', encoding='utf-8') as fh:
                        pd = json.load(fh)
                        pd_date = pd.get('sel_date', '') or f.replace('predict_', '').replace('.json', '')
                        predict_map[pd_date] = pd.get('market_env', {})
                except:
                    pass
    return predict_map


def main():
    print('=' * 70)
    print('  尾盘选股 三天迭代分析2026.7.16')
    print('=' * 70)

    # ===== 加载今日复盘数据，判断是否空仓日 =====
    today_reviews = load_recent_reviews(1)
    today_is_empty = False
    if today_reviews:
        today_is_empty = is_empty_day(today_reviews[0])
    
    # 预加载predict数据用于补全大盘环境
    predict_map = load_predict_map()
    
    # ===== 计数器控制（空仓日不计入） =====
    counter = read_counter()
    
    if today_is_empty:
        print(f'\n  今日为空仓日（无有效标的参与统计），不累计迭代计数器。')
        print(f'  当前计数器: {counter}/3（保持不变）')
        
        # 即使不累计计数器，也检查是否有连续空仓的趋势需要提醒
        all_recent = load_all_recent_reviews(10)
        if all_recent:
            empty_count = sum(1 for r in all_recent if is_empty_day(r))
            total_count = len(all_recent)
            empty_ratio = round(empty_count / total_count * 100, 1) if total_count > 0 else 0
            
            # 生成空仓趋势简报
            lines = []
            today_str = datetime.now().strftime('%Y-%m-%d')
            lines.append(f'# 尾盘选股 空仓趋势简报2026.7.16')
            lines.append('')
            lines.append(f'- 日期：{today_str}')
            lines.append(f'- 今日状态：空仓日')
            lines.append('')
            lines.append('## 近期空仓趋势')
            lines.append('')
            lines.append(f'| 统计范围 | 总天数 | 空仓天数 | 空仓占比 | 有标的日 |')
            lines.append(f'|---------|--------|---------|---------|---------|')
            lines.append(f'| 近{total_count}个交易日 | {total_count} | {empty_count} | {empty_ratio}% | {total_count - empty_count} |')
            lines.append('')
            
            if empty_ratio >= 80:
                lines.append('> **警告：近10日空仓占比超过80%，市场持续偏弱。**')
                lines.append('> - 大盘环境可能处于系统性下跌阶段，选股策略的空仓过滤正在发挥作用')
                lines.append('> - 建议：关注大盘是否出现止跌信号（缩量、地量、连续小阳等）')
                lines.append('> - 不建议在空仓占比极高时放宽筛选条件，可能选到弱势股反而亏损')
            elif empty_ratio >= 50:
                lines.append('> 近期空仓占比较高，市场处于弱势震荡阶段。')
                lines.append('> - 空仓观望是正确的风控策略，等待信号明确再操作')
            else:
                lines.append('> 近期市场有涨有跌，空仓属于正常波动，无需特别调整。')
            
            lines.append('')
            lines.append('## 迭代计数器状态')
            lines.append('')
            lines.append(f'| 计数器 | {counter}/3 |')
            lines.append(f'|--------|-----------|')
            lines.append(f'| 说明 | 再有{3 - counter}个有效交易日触发迭代分析 |')
            lines.append('')
            
            # 逐日明细
            lines.append('## 近期逐日状态')
            lines.append('')
            lines.append('| 日期 | 状态 | 标的数 | 参与统计数 | 大盘环境 |')
            lines.append('|------|------|--------|-----------|---------|')
            for r in all_recent:
                sel_date = r.get('sel_date', '')
                empty = is_empty_day(r)
                stock_count = len(r.get('stocks', []))
                participating = sum(1 for s in r.get('stocks', []) if not s.get('skipped', False))
                # 优先从predict获取大盘环境，fallback到review
                market_env = predict_map.get(sel_date, r.get('market_env', {}))
                light = market_env.get('light', 'N/A')
                light_desc = market_env.get('light_desc', '')
                if light == 'N/A' and not light_desc:
                    # 尝试从预判信号推断
                    sh_pct = market_env.get('sh_open_pct', '')
                    consecutive = market_env.get('sh_consecutive_decline', False)
                    if consecutive:
                        light_desc = f'连跌{market_env.get("sh_3d_decline_count","?")}日'
                    elif sh_pct:
                        light_desc = f'开盘{sh_pct}%'
                status = '空仓' if empty else '有标的'
                lines.append(f'| {sel_date} | {status} | {stock_count} | {participating} | {light} {light_desc} |')
            lines.append('')
            
            lines.append('## 声明')
            lines.append('')
            lines.append('- 空仓日不累计迭代计数器，待有有效数据日再累计')
            lines.append('- 空仓是风控策略的正确执行，不代表系统失效')
            lines.append('')
            
            report_path = os.path.join(BASE_DIR, f'iterate_{today_str}.md')
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print(f'  空仓趋势简报已保存: {report_path}')
            print(f'  近{total_count}日空仓占比: {empty_ratio}%')
            
            # 输出简短建议
            if empty_ratio >= 80:
                print(f'\n  ⚠ 近期空仓占比极高({empty_ratio}%)，市场持续偏弱，建议等待止跌信号。')
            elif empty_ratio >= 50:
                print(f'\n  近期空仓占比{empty_ratio}%，市场偏弱，空仓观望是正确策略。')
            
        print(f'\n{"="*70}')
        return

    # 有效交易日：计数器+1
    counter += 1
    print(f'\n  今日为有效交易日，计数器+1')
    print(f'  当前计数器: {counter}/3')

    if counter < 3:
        write_counter(counter)
        print(f'  未满3天，计数器保存，退出。')
        return

    # 满3天，触发迭代
    write_counter(0)
    print(f'  已满3个有效交易日，触发迭代分析，计数器清零。')

    # ===== 加载数据 =====
    # 加载3个有效交易日的复盘数据
    reviews = load_recent_reviews(3)
    predicts = load_recent_predicts(3)
    csv_rows = load_accuracy_csv(3)

    # 同时加载近期所有数据用于空仓趋势
    all_recent = load_all_recent_reviews(10)
    recent_empty_count = sum(1 for r in all_recent if is_empty_day(r))
    recent_total = len(all_recent)

    # 收集所有有效标的（排除skipped）
    all_stocks = []
    all_stocks_incl_skipped = []  # 包含skipped的标的，用于参考分析
    empty_day_count = 0
    for r in reviews:
        if is_empty_day(r):
            empty_day_count += 1
        stocks = r.get('stocks', [])
        all_stocks_incl_skipped.extend(stocks)
        all_stocks.extend([s for s in stocks if not s.get('skipped', False)])

    trading_days_count = len(reviews)
    valid_days_count = trading_days_count - empty_day_count

    print(f'  近{trading_days_count}个有效交易日: {valid_days_count}个有标的, {empty_day_count}个空仓日')
    print(f'  有效标的总数: {len(all_stocks)}只（排除暴跌日跳过的）')
    print(f'  含参考标的: {len(all_stocks_incl_skipped)}只（含暴跌日跳过的）')
    print(f'  近{recent_total}日空仓占比: {round(recent_empty_count/recent_total*100,1) if recent_total > 0 else 0}%')

    # ===== 统计汇总 =====
    # 四层胜率3日均值
    snap_wrs = [r.get('four_layer_winrate', {}).get('snapshot', {}).get('winrate', 0) for r in reviews if not is_empty_day(r)]
    close_wrs = [r.get('four_layer_winrate', {}).get('close', {}).get('winrate', 0) for r in reviews if not is_empty_day(r)]
    window_wrs = [r.get('four_layer_winrate', {}).get('window', {}).get('winrate', 0) for r in reviews if not is_empty_day(r)]
    high_wrs = [r.get('four_layer_winrate', {}).get('ceiling', {}).get('winrate', 0) for r in reviews if not is_empty_day(r)]

    avg_snap = round(sum(snap_wrs) / len(snap_wrs), 1) if snap_wrs else 0
    avg_close = round(sum(close_wrs) / len(close_wrs), 1) if close_wrs else 0
    avg_window = round(sum(window_wrs) / len(window_wrs), 1) if window_wrs else 0
    avg_high = round(sum(high_wrs) / len(high_wrs), 1) if high_wrs else 0

    # 平均准确度
    accuracies = [r.get('accuracy', {}).get('avg_score', 0) for r in reviews]
    avg_acc = round(sum(accuracies) / len(accuracies), 1) if accuracies else 0

    # 窗口命中率
    hit_rates = [r.get('accuracy', {}).get('window_hit_rate', 0) for r in reviews]
    avg_hit = round(sum(hit_rates) / len(hit_rates), 1) if hit_rates else 0

    # ===== 偏差模式识别 =====
    insights = []

    # 0. 空仓趋势分析
    if recent_total > 0:
        empty_ratio = round(recent_empty_count / recent_total * 100, 1)
        if empty_ratio >= 70:
            insights.append(f'近{recent_total}日空仓占比{empty_ratio}%（{recent_empty_count}/{recent_total}日），市场持续偏弱 → 空仓策略正在规避风险，不建议放宽筛选条件')
        elif empty_ratio >= 40:
            insights.append(f'近{recent_total}日空仓占比{empty_ratio}%，市场震荡偏弱 → 维持现有筛选条件，等待明确信号')

    if len(all_stocks) < 5:
        # 有效样本不足
        if len(all_stocks_incl_skipped) > 0:
            # 有被跳过的标的（暴跌日），用参考数据分析
            ref_close_wins = sum(1 for s in all_stocks_incl_skipped if s.get('close_win') == 1)
            ref_close_total = sum(1 for s in all_stocks_incl_skipped if s.get('close_win') is not None)
            ref_close_wr = round(ref_close_wins / ref_close_total * 100, 1) if ref_close_total > 0 else 0
            ref_close_avg = round(sum(s['close_profit'] for s in all_stocks_incl_skipped if s.get('close_profit') is not None) / max(ref_close_total, 1), 2)
            
            insights.append(f'有效样本不足（{len(all_stocks)}只），但参考数据（含暴跌日跳过的{len(all_stocks_incl_skipped)}只）：收盘持有胜率{ref_close_wr}%，平均盈亏{ref_close_avg:+.2f}%')
            if ref_close_wr < 50:
                insights.append(f'参考收盘胜率不足50%，验证了暴跌日空仓决策的正确性')
            else:
                insights.append(f'参考收盘胜率{ref_close_wr}%≥50%，可关注大盘止跌后是否出现信号强化')
        else:
            insights.append(f'有效样本不足（{len(all_stocks)}只标的），数据不足以进行偏差模式分析')
    else:
        # 有效样本充足，正常分析

        # 1. 按大盘环境分组
        up_stocks = []
        down_stocks = []
        for r in reviews:
            me = r.get('market_env') or {}
            sel_date = r.get('sel_date', '')
            for p in predicts:
                if p.get('sel_date') == sel_date:
                    me = p.get('market_env', {})
                    break
            is_up = me.get('sh_ok', True) and not me.get('sh_consecutive_decline', False)
            valid_stocks = [s for s in r.get('stocks', []) if not s.get('skipped', False)]
            if is_up:
                up_stocks.extend(valid_stocks)
            else:
                down_stocks.extend(valid_stocks)

        def calc_wr(stocks, win_key, profit_key):
            valid = [s for s in stocks if s.get(win_key) is not None]
            if not valid:
                return 0, 0
            wins = sum(s[win_key] for s in valid)
            return round(wins / len(valid) * 100, 1), len(valid)

        up_window_wr, up_n = calc_wr(up_stocks, 'window_win', 'window_profit')
        down_window_wr, down_n = calc_wr(down_stocks, 'window_win', 'window_profit')

        if up_n > 0 and down_n > 0:
            if up_window_wr - down_window_wr > 20:
                insights.append(f'大盘环境差异显著：上涨日窗口可用胜率{up_window_wr}%({up_n}只) vs 下跌日{down_window_wr}%({down_n}只) → 下跌日建议收紧操作条件')

        # 2. 按信号类型分组
        cons_stocks = [s for s in all_stocks if '持续' in str(s.get('signal_type', ''))]
        pulse_stocks = [s for s in all_stocks if '脉冲' in str(s.get('signal_type', ''))]

        cons_wr, cons_n = calc_wr(cons_stocks, 'window_win', 'window_profit')
        pulse_wr, pulse_n = calc_wr(pulse_stocks, 'window_win', 'window_profit')

        if cons_n > 0 and pulse_n > 0:
            if cons_wr - pulse_wr > 15:
                insights.append(f'信号类型差异：持续信号窗口可用胜率{cons_wr}%({cons_n}只) vs 脉冲信号{pulse_wr}%({pulse_n}只) → 脉冲信号建议降低仓位或缩短持有时间')

        # 3. 四层胜率交叉分析
        if avg_window > 0 and avg_snap > 0 and avg_window > avg_snap + 10:
            insights.append(f'窗口可用胜率({avg_window}%)显著高于快照胜率({avg_snap}%) → 当前卖出窗口合理，10点验证过早')
        if avg_window > 0 and avg_close >= 0 and avg_window > avg_close + 10:
            insights.append(f'窗口可用胜率({avg_window}%)高于收盘持有胜率({avg_close}%) → 存在午后跳水，加强"午前必卖"提示')
        if avg_high > 0 and avg_window >= 0 and avg_high > avg_window + 15:
            insights.append(f'策略上限胜率({avg_high}%)显著高于窗口可用胜率({avg_window}%) → 卖出窗口可能偏窄，考虑扩大建议窗口或提供分批卖出策略')
        if avg_window < 40 and avg_high < 50:
            insights.append(f'四层胜率均偏低(窗口{avg_window}%/上限{avg_high}%) → 选股策略需收紧，检查筛选条件')

        # 4. 系统性偏差识别
        high_times = []
        for s in all_stocks:
            ht = s.get('high_time')
            if ht:
                high_times.append(ht)

        if high_times:
            morning_count = sum(1 for t in high_times if t < '11:30')
            afternoon_count = sum(1 for t in high_times if t >= '13:00')
            total_ht = len(high_times)
            if morning_count > total_ht * 0.6:
                insights.append(f'日内高点分布：{morning_count}/{total_ht}出现在上午 → 上午卖出策略正确，建议维持10:30-11:30窗口')
            elif afternoon_count > total_ht * 0.6:
                insights.append(f'日内高点分布：{afternoon_count}/{total_ht}出现在下午 → 高点偏下午，考虑延后卖出窗口至13:30-14:30')

    if not insights:
        insights.append('近3日无显著偏差模式，当前策略配置合理，维持现有参数。')

    # ===== 生成迭代报告 =====
    today_str = datetime.now().strftime('%Y-%m-%d')
    lines = []
    lines.append(f'# 尾盘选股 三天迭代报告2026.7.16')
    lines.append('')
    lines.append(f'- 迭代日期：{today_str}')
    lines.append(f'- 迭代时间：{datetime.now().strftime("%H:%M")}')
    lines.append(f'- 数据范围：近{trading_days_count}个有效交易日（其中{empty_day_count}个空仓/暴跌日跳过）')
    lines.append(f'- 有效标的总数：{len(all_stocks)}只')
    if recent_total > 0:
        lines.append(f'- 近{recent_total}日空仓占比：{round(recent_empty_count/recent_total*100,1)}%')
    lines.append('')

    # 空仓趋势
    if recent_total > 0:
        lines.append('## 0. 近期空仓趋势')
        lines.append('')
        empty_ratio = round(recent_empty_count / recent_total * 100, 1)
        lines.append(f'| 统计范围 | 总天数 | 空仓/暴跌日 | 有效日 | 空仓占比 |')
        lines.append(f'|---------|--------|------------|--------|---------|')
        lines.append(f'| 近{recent_total}个交易日 | {recent_total} | {recent_empty_count} | {recent_total - recent_empty_count} | {empty_ratio}% |')
        lines.append('')

    # 四层胜率3日趋势
    lines.append('## 1. 四层胜率趋势')
    lines.append('')
    
    # 逐日展示（空仓日特殊标注）
    lines.append('| 日期 | 状态 | 快照胜率 | 收盘持有 | 窗口可用 | 策略上限 | 平均准确度 | 窗口命中率 |')
    lines.append('|------|------|---------|---------|---------|---------|-----------|-----------|')
    for r in reviews:
        fw = r.get('four_layer_winrate', {})
        acc = r.get('accuracy', {})
        sel_date = r.get('sel_date', '')
        empty = is_empty_day(r)
        status = '空仓/暴跌' if empty else '正常'
        if empty:
            lines.append(f'| {sel_date} | {status} | - | - | - | - | {acc.get("avg_score",0)}/100 | - |')
        else:
            lines.append(f'| {sel_date} | {status} | {fw.get("snapshot",{}).get("winrate",0)}% | {fw.get("close",{}).get("winrate",0)}% | {fw.get("window",{}).get("winrate",0)}% | {fw.get("ceiling",{}).get("winrate",0)}% | {acc.get("avg_score",0)}/100 | {acc.get("window_hit_rate",0)}% |')
    lines.append('')
    
    if valid_days_count > 0:
        lines.append(f'**有效日均值：** 快照{avg_snap}% | 收盘{avg_close}% | 窗口{avg_window}% | 上限{avg_high}% | 准确度{avg_acc}/100 | 命中率{avg_hit}%')
    else:
        lines.append('> 近3个有效交易日均为空仓/暴跌日，无四层胜率数据。空仓是风控策略的正确执行。')
    lines.append('')

    # 分组分析（只有有效样本充足时才展示）
    if len(all_stocks) >= 5:
        lines.append('## 2. 分组分析')
        lines.append('')
        lines.append('### 按大盘环境')
        lines.append('')
        lines.append('| 环境 | 窗口可用胜率 | 标的数 |')
        lines.append('|------|------------|--------|')
        lines.append(f'| 上涨日 | {up_window_wr}% | {up_n} |')
        lines.append(f'| 下跌日 | {down_window_wr}% | {down_n} |')
        lines.append('')
        lines.append('### 按信号类型')
        lines.append('')
        lines.append('| 信号 | 窗口可用胜率 | 标的数 |')
        lines.append('|------|------------|--------|')
        lines.append(f'| 持续信号 | {cons_wr}% | {cons_n} |')
        lines.append(f'| 脉冲信号 | {pulse_wr}% | {pulse_n} |')
        lines.append('')
    else:
        lines.append('## 2. 分组分析')
        lines.append('')
        lines.append(f'> 有效样本不足（{len(all_stocks)}只），跳过分组分析。')
        if len(all_stocks_incl_skipped) > len(all_stocks):
            skipped_count = len(all_stocks_incl_skipped) - len(all_stocks)
            lines.append(f'> 另有{skipped_count}只标的因暴跌日跳过统计，无法参与分组。')
        lines.append('')

    # 偏差模式与建议
    lines.append('## 3. 偏差模式识别与改进建议')
    lines.append('')
    for ins in insights:
        lines.append(ins)
    lines.append('')

    # CSV数据参考
    if csv_rows:
        lines.append('## 4. CSV追踪数据')
        lines.append('')
        lines.append('| 预测日期 | 标的数 | 参与统计 | 快照胜率 | 收盘持有 | 窗口可用 | 策略上限 | 准确度 | 命中率 | 目标偏差 |')
        lines.append('|---------|--------|---------|---------|---------|---------|---------|--------|--------|---------|')
        for row in csv_rows:
            lines.append(f'| {row.get("预测日期","")} | {row.get("标的总数","")} | {row.get("参与统计数","")} | {row.get("快照胜率%","")}% | {row.get("收盘持有胜率%","")}% | {row.get("窗口可用胜率%","")}% | {row.get("策略上限胜率%","")}% | {row.get("平均预测准确度","")}/100 | {row.get("卖出窗口命中率%","")}% | {row.get("目标价平均偏差%","")}% |')
        lines.append('')

    lines.append('## 5. 声明')
    lines.append('')
    lines.append('- 本报告仅输出建议，不自动修改任何脚本参数')
    lines.append('- 人工确认后手动调整相关参数')
    lines.append('- 空仓日不计入迭代计数器，待有有效数据日再累计')
    lines.append('- 计数器已清零，下次迭代将在3个有效交易日后触发')
    lines.append('')

    # 保存报告
    report_path = os.path.join(BASE_DIR, f'iterate_{today_str}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'\n  迭代报告已保存: {report_path}')
    print(f'\n{"="*70}')
    print(f'  ===== 迭代摘要 =====')
    if valid_days_count > 0:
        print(f'  近3个有效日四层胜率均值:')
        print(f'    快照: {avg_snap}% | 收盘: {avg_close}% | 窗口: {avg_window}% | 上限: {avg_high}%')
    else:
        print(f'  近3个有效交易日均为空仓/暴跌日，无四层胜率数据')
    print(f'  平均准确度: {avg_acc}/100')
    print(f'  窗口命中率: {avg_hit}%')
    if recent_total > 0:
        print(f'  近{recent_total}日空仓占比: {round(recent_empty_count/recent_total*100,1)}%')
    print(f'  发现{len(insights)}条改进建议')
    print(f'{"="*70}')


if __name__ == '__main__':
    main()
