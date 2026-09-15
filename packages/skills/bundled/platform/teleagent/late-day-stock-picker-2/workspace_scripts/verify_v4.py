#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 盘中辅助验证脚本2026.7.16
每天10:00运行，精简版盘中辅助模式。
读取前日三轮选股结果+当日09:30预判报告，快速验证10点走势并与预判交叉对比。
详细复盘移至15:05 review_v4.py，本脚本仅控制台打印摘要+追加verify_history.csv+生成精简报告。
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(BASE_DIR, 'runs')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 2026.9.9: 净收益口径（优先引用 trading_cost.py，失败兑底 0.30%）
try:
    sys.path.insert(0, BASE_DIR)
    from trading_cost import round_trip_cost
    ROUND_TRIP_COST = round_trip_cost()
except Exception:
    ROUND_TRIP_COST = 0.003

SLOT_LABELS = {1: '14:00', 2: '14:30', 3: '14:50'}


def find_last_trading_day():
    """找到最近一个有选股数据的交易日（排除今天）"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    if not os.path.exists(RUNS_DIR):
        return None

    files = [f for f in os.listdir(RUNS_DIR) if f.endswith('.json')]
    # 按日期分组，排除今天
    dates = set()
    for f in files:
        date_part = f[:10]
        if date_part < today_str:
            dates.add(date_part)

    if not dates:
        return None

    return max(dates)


def load_slot_data(date_str, slot):
    """读取指定日期指定轮次的结果（取最新一次）"""
    if not os.path.exists(RUNS_DIR):
        return None

    files = [f for f in os.listdir(RUNS_DIR)
             if f.startswith(date_str) and f'_slot{slot}_' in f and f.endswith('.json')]
    if not files:
        return None

    # 取最新的一个
    files.sort(reverse=True)
    filepath = os.path.join(RUNS_DIR, files[0])
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def get_current_quotes(codes):
    """通过腾讯API获取当前实时行情"""
    results = {}
    for i in range(0, len(codes), 40):
        batch = codes[i:i + 40]
        codes_str = ','.join([('sh' + c if c.startswith('6') else 'sz' + c) for c in batch])
        url = f'https://qt.gtimg.cn/q={codes_str}'
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            lines = r.text.strip().split(';')
            for line in lines:
                if not line.strip() or '=' not in line:
                    continue
                parts = line.split('="')
                if len(parts) < 2:
                    continue
                data_str = parts[1].rstrip('"')
                fields = data_str.split('~')
                if len(fields) < 52:
                    continue

                code = fields[2]
                name = fields[1]
                price = float(fields[3]) if fields[3] else 0
                pre_close = float(fields[4]) if fields[4] else 0
                open_price = float(fields[5]) if fields[5] else 0
                high = float(fields[33]) if fields[33] else 0
                low = float(fields[34]) if fields[34] else 0
                change_pct = float(fields[32]) if fields[32] else 0
                volume_ratio = float(fields[49]) if len(fields) > 49 and fields[49] else 0
                turnover = float(fields[38]) if len(fields) > 38 and fields[38] else 0
                amount = float(fields[37]) if len(fields) > 37 and fields[37] else 0

                if price > 0:
                    results[code] = {
                        'name': name,
                        'price': price,
                        'pre_close': pre_close,
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'change_pct': round(change_pct, 2),
                        'volume_ratio': round(volume_ratio, 2),
                        'turnover': round(turnover, 2),
                        'amount': round(amount, 0),
                    }
        except Exception as e:
            print(f'  API请求异常: {e}')
        import time
        time.sleep(0.2)

    return results


def main():
    print('=' * 60)
    print('  尾盘选股 盘中辅助验证2026.7.16')
    print('=' * 60)

    # 找到前一交易日
    last_day = find_last_trading_day()
    if not last_day:
        print('\n  未找到前一交易日的选股数据，退出。')
        return

    print(f'\n  前一交易日: {last_day}')
    print(f'  验证时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    # 读取三轮数据
    slot_data = {}
    for slot in [1, 2, 3]:
        slot_data[slot] = load_slot_data(last_day, slot)

    available_slots = [s for s in [1, 2, 3] if slot_data[s] is not None]

    if not available_slots:
        print(f'\n  {last_day}无任何轮次数据，退出。')
        return

    for s in available_slots:
        d = slot_data[s]
        t1 = len(d.get('tier1', []))
        t2 = len(d.get('tier2', []))
        label = d.get('slot_label', SLOT_LABELS.get(s, ''))
        print(f'  第{s}轮({label}): 一档{t1}只 / 二档{t2}只')

    # 收集各轮标的
    slot_tier1 = {}  # slot -> {code: stock}
    slot_all = {}    # slot -> {code: stock} (一档+二档)
    for s in available_slots:
        d = slot_data[s]
        slot_tier1[s] = {st['code']: st for st in d.get('tier1', [])}
        slot_all[s] = {st['code']: st for st in d.get('tier1', []) + d.get('tier2', [])}

    # ===== 核心验证分类 =====
    # 1. 三轮均在一档 = 最强信号
    all_tier1_sets = [set(slot_tier1[s].keys()) for s in available_slots]
    consensus_tier1 = set.intersection(*all_tier1_sets) if all_tier1_sets else set()

    # 2. 三轮均入档（一档或二档）= 持续信号
    all_tier_sets = [set(slot_all[s].keys()) for s in available_slots]
    consensus_all = set.intersection(*all_tier_sets) if all_tier_sets else set()

    # 3. 仅一轮或两轮出现 = 脉冲信号
    all_codes_union = set.union(*all_tier_sets) if all_tier_sets else set()
    pulse_only = all_codes_union - consensus_all

    print(f'\n  三轮均一档(最强): {len(consensus_tier1)}只')
    print(f'  三轮均入档(持续): {len(consensus_all - consensus_tier1)}只')
    print(f'  非全轮入选(脉冲): {len(pulse_only)}只')

    # 合并所有需验证的标的
    all_verify_codes = consensus_all | pulse_only
    if not all_verify_codes:
        print('\n  前日选股为0只，追加空仓记录到历史CSV。')
        # 追加空仓行
        history_path = os.path.join(BASE_DIR, 'verify_history.csv')
        import csv
        file_exists = os.path.exists(history_path)
        with open(history_path, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['选股日期', '验证日期', '轮次数', '持续信号数', '持续盈利数', '持续亏损数',
                               '持续胜率%', '持续平均盈利%', '持续平均亏损%',
                               '总验证数', '总盈利数', '总亏损数', '总胜率%',
                               '净盈利数', '净亏损数', '净胜率%', '净平均盈亏%'])
            writer.writerow([
                last_day, datetime.now().strftime('%Y-%m-%d'), len(available_slots),
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            ])
        print(f'  空仓记录已追加到: verify_history.csv')
        return

    # 获取次日实时行情
    print(f'\n  获取{len(all_verify_codes)}只标的次日行情...')
    quotes = get_current_quotes(list(all_verify_codes))

    # 构建标的详情映射
    all_stocks = {}
    for s in available_slots:
        for st in slot_data[s].get('tier1', []) + slot_data[s].get('tier2', []):
            code = st['code']
            if code not in all_stocks:
                all_stocks[code] = {'name': st['name'], 'scores': {}, 'tiers': {}, 'price': st['price']}
            all_stocks[code]['scores'][s] = st['score']
            all_stocks[code]['tiers'][s] = '一档' if st['score'] >= 70 else '二档'

    # ===== 加载预判报告进行交叉对比 =====
    predict_json_path = os.path.join(BASE_DIR, 'predict_history', f'predict_{last_day}.json')
    predict_data = None
    if os.path.exists(predict_json_path):
        try:
            with open(predict_json_path, 'r', encoding='utf-8') as f:
                predict_data = json.load(f)
        except:
            pass

    # 生成精简版验证报告
    lines = []
    lines.append(f'# 尾盘选股 盘中辅助验证2026.9.9')
    lines.append('')
    lines.append(f'> **成本口径**：往返成本约{ROUND_TRIP_COST*100:.2f}%（佣金万2.5+印花税0.05%+滑点0.1%），表中“净收益”已扣减，名义与净值双口径评估。')
    lines.append('')
    lines.append(f'- 选股日期：{last_day}')
    lines.append(f'- 验证时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append(f'- 对比轮次：{" / ".join([f"第{s}轮({SLOT_LABELS[s]})" for s in available_slots])}')
    if predict_data:
        lines.append(f'- 交叉对比预判报告: predict_{last_day}.json')
    lines.append('')

    # 前日大盘环境
    me = (slot_data[max(available_slots)] or {}).get('market_env', {})
    lines.append('## 1. 前日大盘环境')
    lines.append('')
    lines.append(f'| 指标 | 数值 |')
    lines.append(f'|------|------|')
    lines.append(f'| 上证涨跌 | {me.get("sh_change_pct","N/A")}% |')
    lines.append(f'| 涨跌比 | {me.get("up_count","?")}:{me.get("down_count","?")} |')
    trend = me.get('sh_3d_trend', '-')
    if me.get('sh_consecutive_decline'):
        trend = '**' + trend + '**'
    lines.append(f'| 3日趋势 | {trend} |')
    lines.append('')

    # ===== 核心验证：三轮入选标的次日表现 =====
    lines.append('## 2. 三轮入选标的次日验证')
    lines.append('')

    # 分类输出
    categories = [
        ('三轮均一档（最强信号）', consensus_tier1, True),
        ('三轮均入档（持续信号）', consensus_all - consensus_tier1, True),
        ('非全轮入选（脉冲信号）', pulse_only, False),
    ]

    total_profit_count = 0
    total_loss_count = 0
    total_profit_pct = 0
    total_loss_pct = 0
    consensus_profit = 0
    consensus_loss = 0
    consensus_profit_pct = 0
    consensus_loss_pct = 0
    # 2026.9.9 净收益口径统计（扣成本）
    net_profit_count = 0
    net_loss_count = 0
    net_profit_pct = 0
    net_loss_pct = 0

    # 构建表头
    score_headers = ' | '.join([f'第{s}轮分' for s in available_slots])
    score_separator = ' | '.join(['------' for _ in available_slots])

    for cat_name, codes, is_consensus in categories:
        if not codes:
            lines.append(f'### {cat_name}：无')
            lines.append('')
            continue

        lines.append(f'### {cat_name}（{len(codes)}只）')
        lines.append('')
        header = f'| 代码 | 名称 | 选股价 | 次日现价 | 涨跌幅 | 量比 | 换手 | {score_headers} | 结果 | 净收益(扣成本) |'
        sep = f'|------|------|--------|---------|--------|------|------| {score_separator} |------|-----------------|'
        lines.append(header)
        lines.append(sep)

        for code in sorted(codes):
            info = all_stocks.get(code, {})
            q = quotes.get(code, {})
            name = info.get('name', q.get('name', code))
            stock_price = info.get('price', '-')

            next_price = q.get('price', 0)
            next_change = q.get('change_pct', 0)
            next_vr = q.get('volume_ratio', '-')
            next_turnover = q.get('turnover', '-')

            score_cols = []
            for s in available_slots:
                score_cols.append(str(info.get('scores', {}).get(s, '-')))
            scores_str = ' | '.join(score_cols)

            if next_price > 0 and isinstance(stock_price, (int, float)) and stock_price > 0:
                result = '盈利' if next_change > 0 else ('亏损' if next_change < 0 else '持平')

                # 2026.9.9 净收益口径（扣往返成本）
                net_chg_v = next_change - ROUND_TRIP_COST * 100
                if net_chg_v > 0:
                    net_profit_count += 1
                    net_profit_pct += net_chg_v
                elif net_chg_v < 0:
                    net_loss_count += 1
                    net_loss_pct += net_chg_v

                if is_consensus:
                    if next_change > 0:
                        consensus_profit += 1
                        consensus_profit_pct += next_change
                    elif next_change < 0:
                        consensus_loss += 1
                        consensus_loss_pct += next_change

                if next_change > 0:
                    total_profit_count += 1
                    total_profit_pct += next_change
                elif next_change < 0:
                    total_loss_count += 1
                    total_loss_pct += next_change
            else:
                result = '无数据'
                next_price = '-'
                next_change = '-'
                next_vr = '-'
                next_turnover = '-'

            if isinstance(next_change, (int, float)):
                net_chg = round(next_change - ROUND_TRIP_COST * 100, 2)
                net_mark = '✓' if net_chg > 0 else '✗'
            else:
                net_chg, net_mark = '-', ''
            lines.append(f'| {code} | {name} | {stock_price} | {next_price} | {next_change}% | {next_vr} | {next_turnover} | {scores_str} | {result} | 净{net_chg}% {net_mark} |')

        lines.append('')

    # ===== 总体统计 =====
    lines.append('## 3. 验证统计')
    lines.append('')

    total_verified = total_profit_count + total_loss_count
    if total_verified > 0:
        win_rate = total_profit_count / total_verified * 100
        avg_profit = total_profit_pct / total_profit_count if total_profit_count > 0 else 0
        avg_loss = total_loss_pct / total_loss_count if total_loss_count > 0 else 0
        lines.append(f'| 指标 | 数值 |')
        lines.append(f'|------|------|')
        lines.append(f'| 总验证标的 | {total_verified}只 |')
        lines.append(f'| 盈利数 | {total_profit_count}只 |')
        lines.append(f'| 亏损数 | {total_loss_count}只 |')
        lines.append(f'| 胜率 | {win_rate:.1f}% |')
        lines.append(f'| 平均盈利 | {avg_profit:.2f}% |')
        lines.append(f'| 平均亏损 | {avg_loss:.2f}% |')
        net_verified_all = net_profit_count + net_loss_count
        net_wr_all = net_profit_count / net_verified_all * 100 if net_verified_all > 0 else 0
        lines.append(f'| 净胜率(扣成本{ROUND_TRIP_COST*100:.2f}%) | {net_wr_all:.1f}% |')
        lines.append(f'| 净平均盈利 | {net_profit_pct / net_profit_count:.2f}% |' if net_profit_count > 0 else '| 净平均盈利 | - |')
        lines.append(f'| 净平均亏损 | {net_loss_pct / net_loss_count:.2f}% |' if net_loss_count > 0 else '| 净平均亏损 | - |')
        lines.append('')

        # 持续信号胜率单独统计
        consensus_verified = consensus_profit + consensus_loss
        if consensus_verified > 0:
            consensus_win_rate = consensus_profit / consensus_verified * 100
            c_avg_profit = consensus_profit_pct / consensus_profit if consensus_profit > 0 else 0
            c_avg_loss = consensus_loss_pct / consensus_loss if consensus_loss > 0 else 0
            lines.append(f'### 持续信号标的（三轮均入选）')
            lines.append('')
            lines.append(f'| 指标 | 数值 |')
            lines.append(f'|------|------|')
            lines.append(f'| 验证数 | {consensus_verified}只 |')
            lines.append(f'| 胜率 | {consensus_win_rate:.1f}% |')
            lines.append(f'| 平均盈利 | {c_avg_profit:.2f}% |')
            lines.append(f'| 平均亏损 | {c_avg_loss:.2f}% |')
            lines.append('')

        # ===== 脉冲信号胜率单独统计 =====
        pulse_profit = total_profit_count - consensus_profit
        pulse_loss = total_loss_count - consensus_loss
        pulse_verified = pulse_profit + pulse_loss
        if pulse_verified > 0:
            pulse_win_rate = pulse_profit / pulse_verified * 100
            lines.append(f'### 脉冲信号标的（非全轮入选）')
            lines.append('')
            lines.append(f'| 指标 | 数值 |')
            lines.append(f'|------|------|')
            lines.append(f'| 验证数 | {pulse_verified}只 |')
            lines.append(f'| 胜率 | {pulse_win_rate:.1f}% |')
            lines.append('')

        # 风险警告
        if pulse_verified > 0 and pulse_win_rate < 40:
            lines.append(f'### > \\u26a0 风险警告')
            lines.append('')
            lines.append(f'**脉冲信号胜率仅{pulse_win_rate:.1f}%，低于40%阈值！**')
            lines.append('- 脉冲信号（仅部分轮次入选）可靠性不足，建议只操作三轮均入选的持续信号标的')
            lines.append('- 大盘弱势环境下脉冲信号尤其不可靠，严格执行"弱势大盘不出票"规则')
            lines.append('')

        if total_verified > 0 and win_rate < 40:
            lines.append(f'### > \\u26a0 总体风险警告')
            lines.append('')
            lines.append(f'**总体胜率仅{win_rate:.1f}%，低于40%阈值！** 建议空仓观望，等待市场企稳。')
            lines.append('')
    else:
        lines.append('无可验证标的。')
        lines.append('')

    # ===== 历史追踪 =====
    lines.append('## 4. 历史胜率追踪')
    lines.append('')
    lines.append('（每次验证自动追加记录）')
    lines.append('')

    # 追加到历史文件
    history_path = os.path.join(BASE_DIR, 'verify_history.csv')
    import csv
    file_exists = os.path.exists(history_path)

    with open(history_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['选股日期', '验证日期', '轮次数', '持续信号数', '持续盈利数', '持续亏损数',
                           '持续胜率%', '持续平均盈利%', '持续平均亏损%',
                           '总验证数', '总盈利数', '总亏损数', '总胜率%',
                           '净盈利数', '净亏损数', '净胜率%', '净平均盈亏%'])

        consensus_verified = consensus_profit + consensus_loss
        c_wr = round(consensus_profit / consensus_verified * 100, 1) if consensus_verified > 0 else 0
        c_ap = round(consensus_profit_pct / consensus_profit, 2) if consensus_profit > 0 else 0
        c_al = round(consensus_loss_pct / consensus_loss, 2) if consensus_loss > 0 else 0
        t_wr = round(total_profit_count / total_verified * 100, 1) if total_verified > 0 else 0

        net_verified = net_profit_count + net_loss_count
        net_wr = round(net_profit_count / net_verified * 100, 1) if net_verified > 0 else 0
        net_avg = round((net_profit_pct + net_loss_pct) / net_verified, 2) if net_verified > 0 else 0

        writer.writerow([
            last_day, datetime.now().strftime('%Y-%m-%d'), len(available_slots),
            consensus_verified,
            consensus_profit, consensus_loss, c_wr, c_ap, c_al,
            total_verified, total_profit_count, total_loss_count, t_wr,
            net_profit_count, net_loss_count, net_wr, net_avg
        ])

    lines.append(f'历史记录已追加到: verify_history.csv')
    lines.append('')

    # ===== 预判交叉对比 =====
    deviate_count = 0
    if predict_data:
        lines.append('## 5. 预判交叉对比')
        lines.append('')
        pred_stocks = {s['code']: s for s in predict_data.get('stocks', [])}
        for code in sorted(all_verify_codes):
            info = all_stocks.get(code, {})
            q = quotes.get(code, {})
            pred = pred_stocks.get(code)
            if not pred or not q:
                continue
            actual_pct = q.get('change_pct', 0)
            pred_direction = pred.get('predict_direction', '')
            # predict_v4.py输出中文方向：上午强/冲高/反弹/修复=看涨，暴跌日不操作=不看涨
            pred_bullish = any(w in pred_direction for w in ['强', '冲高', '反弹', '修复'])
            actual_bullish = actual_pct > 0
            if pred_bullish != actual_bullish:
                deviate_count += 1
                lines.append(f'- **⚠ 预判偏离：{pred["name"]}({code})** 预判"{pred_direction}"，实际{actual_pct:+.2f}%')
        if deviate_count == 0:
            lines.append('✓ 所有标的走势与预判方向一致')
        else:
            lines.append(f'')
            lines.append(f'共{deviate_count}只标的偏离预判，建议关注。')
        lines.append('')

    # 保存报告
    report_path = os.path.join(BASE_DIR, f'verify_{last_day}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'\n  验证报告已保存: {report_path}')
    # 控制台只打印精简摘要
    print(f'\n{"="*60}')
    print(f'  ===== 盘中辅助摘要 =====')
    if total_verified > 0:
        net_verified_c = net_profit_count + net_loss_count
        net_wr_c = net_profit_count / net_verified_c * 100 if net_verified_c > 0 else 0
        print(f'  总验证: {total_verified}只 | 盈利: {total_profit_count} | 亏损: {total_loss_count} | 胜率: {win_rate:.1f}%')
        print(f'  [2026.9.9] 净收益口径: 净盈{net_profit_count} | 净亏{net_loss_count} | 净胜率: {net_wr_c:.1f}%（扣成本{ROUND_TRIP_COST*100:.2f}%）')
    if predict_data:
        if deviate_count > 0:
            print(f'  预判交叉对比: {deviate_count}只偏离')
        else:
            print(f'  预判交叉对比: 全部一致')
    print(f'  详细报告: {report_path}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
