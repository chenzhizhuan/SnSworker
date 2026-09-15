#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
收盘复盘脚本2026.7.16
每个交易日15:05收盘后运行，读取当日预判JSON+5分钟K线，
计算四层胜率+预测准确度评分，输出复盘报告。
"""

import os
import sys
import json
import csv
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(BASE_DIR, 'runs')
PREDICT_HISTORY_DIR = os.path.join(BASE_DIR, 'predict_history')
REVIEW_HISTORY_DIR = os.path.join(BASE_DIR, 'review_history')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 关键时点（5分钟K线对应的时间戳）
TIME_POINTS = [
    ('09:35', 'morning'),
    ('10:00', 'morning'),
    ('10:30', 'morning'),
    ('11:00', 'morning'),
    ('11:30', 'morning'),
    ('13:30', 'afternoon'),
    ('14:00', 'afternoon'),
    ('14:30', 'afternoon'),
    ('15:00', 'afternoon'),
]


def is_trading_day():
    """判断今日是否为A股交易日"""
    weekday = datetime.now().weekday()
    if weekday >= 5:
        return False, "周末"
    try:
        url = 'https://qt.gtimg.cn/q=sh000001'
        r = requests.get(url, headers=HEADERS, timeout=10)
        parts = r.text.split('="')
        if len(parts) >= 2:
            fields = parts[1].rstrip('"').split('~')
            if len(fields) > 36:
                volume = float(fields[36]) if fields[36] else 0
                if volume > 0:
                    return True, "交易日"
                else:
                    return False, "节假日(无成交)"
    except:
        pass
    return True, "工作日(默认)"


def find_last_trading_day():
    """找到最近一个有选股数据的交易日（排除今天）"""
    today_str = datetime.now().strftime('%Y-%m-%d')
    if not os.path.exists(RUNS_DIR):
        return None
    files = [f for f in os.listdir(RUNS_DIR) if f.endswith('.json')]
    dates = set()
    for f in files:
        date_part = f[:10]
        if date_part < today_str:
            dates.add(date_part)
    if not dates:
        return None
    return max(dates)


def get_symbol_prefix(code):
    """获取市场前缀"""
    if code.startswith('6'):
        return 'sh' + code
    return 'sz' + code


def fetch_5min_bars_mootdx(code, verify_date):
    """通过mootdx获取5分钟K线"""
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market='std')
        df = client.bars(symbol=code, frequency=0, offset=200)
        if df is None or len(df) == 0:
            return None
        if 'datetime' in df.columns:
            df['datetime'] = df['datetime'].astype(str)
        filtered = df[df['datetime'].str.startswith(verify_date)]
        if len(filtered) == 0:
            for fmt in [verify_date, verify_date.replace('-', '/')]:
                filtered = df[df['datetime'].str.contains(fmt)]
                if len(filtered) > 0:
                    break
        if len(filtered) == 0:
            return None
        return filtered
    except Exception as e:
        print(f'    mootdx获取{code}失败: {e}')
        return None


def get_current_quotes(codes):
    """通过腾讯API获取收盘行情"""
    results = {}
    for i in range(0, len(codes), 40):
        batch = codes[i:i + 40]
        codes_str = ','.join([('sh' + c if c.startswith('6') else 'sz' + c) for c in batch])
        url = f'https://qt.gtimg.cn/q={codes_str}'
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            for line in r.text.strip().split(';'):
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
                price = float(fields[3]) if fields[3] else 0
                pre_close = float(fields[4]) if fields[4] else 0
                open_price = float(fields[5]) if fields[5] else 0
                high = float(fields[33]) if fields[33] else 0
                low = float(fields[34]) if fields[34] else 0
                change_pct = round(float(fields[32]) if fields[32] else 0, 2)
                if price > 0:
                    results[code] = {
                        'name': fields[1], 'price': price, 'pre_close': pre_close,
                        'open': open_price, 'high': high, 'low': low,
                        'change_pct': change_pct,
                    }
        except Exception as e:
            print(f'  API异常: {e}')
        import time
        time.sleep(0.2)
    return results


def extract_timepoint_prices(bars_df):
    """从5分钟K线提取各时点收盘价和日内最高/最低"""
    result = {}
    if 'high' in bars_df.columns:
        result['intraday_high'] = float(bars_df['high'].max())
    if 'low' in bars_df.columns:
        result['intraday_low'] = float(bars_df['low'].min())
    for time_str, _ in TIME_POINTS:
        result[time_str] = None
        for _, row in bars_df.iterrows():
            dt_str = str(row['datetime'])
            if time_str in dt_str:
                result[time_str] = float(row['close'])
                break
    return result


def calc_window_high(bars_df, window_start, window_end):
    """计算建议卖出窗口内的最高价"""
    if bars_df is None:
        return None
    start_time = window_start.replace(':', '')
    end_time = window_end.replace(':', '')
    mask = []
    for _, row in bars_df.iterrows():
        dt_str = str(row['datetime'])
        # 提取时间部分 HH:MM
        if ' ' in dt_str:
            time_part = dt_str.split(' ')[1][:5].replace(':', '')
        else:
            time_part = dt_str[11:16].replace(':', '')
        if start_time <= time_part <= end_time:
            mask.append(True)
        else:
            mask.append(False)
    if not any(mask):
        return None
    filtered = bars_df[mask]
    if len(filtered) == 0 or 'high' not in filtered.columns:
        return None
    return float(filtered['high'].max())


def find_high_time(bars_df, target_price):
    """找到日内最高价出现的时间"""
    if bars_df is None or 'high' not in bars_df.columns:
        return None
    idx = bars_df['high'].idxmax()
    row = bars_df.loc[idx]
    dt_str = str(row.get('datetime', ''))
    if ' ' in dt_str:
        return dt_str.split(' ')[1][:5]
    return dt_str[11:16] if len(dt_str) >= 16 else None


def calc_accuracy_score(pred, actual_data):
    """计算单只标的的预测准确度评分（0-100分）"""
    score = 0

    # 1. 大盘方向（20分）
    # 在调用处单独计算，这里跳过

    # 2. 个股开盘方向（15分）
    pred_open_pct = pred.get('open_pct', 0)
    actual_open_pct = actual_data.get('open_pct', 0)
    if (pred_open_pct > 0) == (actual_open_pct > 0):
        score += 15

    # 3. 卖出窗口命中（30分）
    actual_high_time = actual_data.get('high_time', '')
    sell_start = pred.get('sell_window_start', '')
    sell_end = pred.get('sell_window_end', '')
    if actual_high_time and sell_start and sell_end:
        try:
            ht = actual_high_time.replace(':', '')
            ws = sell_start.replace(':', '')
            we = sell_end.replace(':', '')
            if ws <= ht <= we:
                score += 30
            else:
                # 差半小时内得15分
                ht_min = int(ht[:2]) * 60 + int(ht[2:4])
                ws_min = int(ws[:2]) * 60 + int(ws[2:4])
                we_min = int(we[:2]) * 60 + int(we[2:4])
                if abs(ht_min - ws_min) <= 30 or abs(ht_min - we_min) <= 30:
                    score += 15
        except:
            pass

    # 4. 目标价偏差（15分）
    target_price = pred.get('target_price', 0)
    actual_high = actual_data.get('intraday_high', 0)
    if target_price > 0 and actual_high > 0 and pred.get('sel_price', 0) > 0:
        target_pct = (target_price - pred['sel_price']) / pred['sel_price'] * 100
        actual_pct = (actual_high - pred['sel_price']) / pred['sel_price'] * 100
        diff = abs(target_pct - actual_pct)
        if diff < 0.5:
            score += 15
        elif diff < 1:
            score += 10
        elif diff < 2:
            score += 5

    # 5. 止损判断（10分）
    stop_loss = pred.get('stop_loss_price', 0)
    actual_low = actual_data.get('intraday_low', 0)
    if stop_loss > 0 and actual_low > 0:
        if actual_low > stop_loss:
            score += 10  # 未被止损洗出
        # 如果被止损触发但确实是亏损标的，也算判断正确
        elif actual_data.get('close_pct', 0) < 0:
            score += 5

    # 6. 风险等级（10分）— predict_v4.py输出中文：低/中/高/极高
    risk_level = pred.get('risk_level', '')
    close_pct = actual_data.get('close_pct', 0)
    if risk_level in ['高', '极高'] and close_pct < 0:
        score += 10
    elif risk_level == '低' and close_pct > 0:
        score += 10
    elif risk_level == '中':
        score += 5

    return score


def main(target_date=None):
    print('=' * 70)
    print('  尾盘选股 收盘复盘2026.7.16')
    print('=' * 70)

    is_trading, reason = is_trading_day()
    print(f'\n  今日: {datetime.now().strftime("%Y-%m-%d %H:%M")} | {reason}')
    if not is_trading:
        print('  非交易日，退出。')
        return

    last_day = target_date or find_last_trading_day()
    if not last_day:
        print('\n  未找到前一交易日的选股数据，退出。')
        return

    print(f'  前一交易日: {last_day}')
    print(f'  复盘时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    # 加载预判JSON
    predict_json_path = os.path.join(PREDICT_HISTORY_DIR, f'predict_{last_day}.json')
    if not os.path.exists(predict_json_path):
        print(f'\n  未找到预判JSON: {predict_json_path}')
        print('  无法进行复盘（需要先运行predict_v4.py）')
        return

    with open(predict_json_path, 'r', encoding='utf-8') as f:
        predict_data = json.load(f)

    pred_stocks = predict_data.get('stocks', [])
    is_empty_day = predict_data.get('is_empty_day', False)

    if not pred_stocks:
        if is_empty_day:
            print(f'  空仓日（前日选股为0），仅记录大盘环境到CSV/JSON。')
        else:
            print('  预判报告中无标的，退出。')
            return

    print(f'  预判标的数: {len(pred_stocks)}只')

    # 获取收盘行情（空仓日跳过个股行情获取）
    all_codes = [s['code'] for s in pred_stocks]
    if all_codes:
        print(f'\n  获取{len(all_codes)}只标的收盘行情...')
        quotes = get_current_quotes(all_codes)
    else:
        quotes = {}

    # 单独获取上证指数收盘涨跌幅（quotes不含指数）
    sh_index_pct = 0
    try:
        url = 'https://qt.gtimg.cn/q=sh000001'
        r = requests.get(url, headers=HEADERS, timeout=10)
        parts = r.text.split('="')
        if len(parts) >= 2:
            fields = parts[1].rstrip('"').split('~')
            if len(fields) > 32:
                sh_index_pct = round(float(fields[32]) if fields[32] else 0, 2)
    except:
        pass

    # 逐只获取5分钟K线（空仓日跳过）
    stock_results = []
    if pred_stocks:
        print(f'\n  获取5分钟K线数据...')
        for st in pred_stocks:
            code = st['code']
            name = st['name']
            sel_price = st.get('sel_price', 0)
            print(f'  处理: {code} {name} (选股价{sel_price})')

            q = quotes.get(code, {})
            close_price = q.get('price', 0)
            close_pct = q.get('change_pct', 0)
            open_pct = round((q.get('open', 0) - q.get('pre_close', 1)) / q.get('pre_close', 1) * 100, 2) if q.get('pre_close', 0) > 0 else 0

            # 获取5分钟K线
            bars = fetch_5min_bars_mootdx(code, datetime.now().strftime('%Y-%m-%d'))
            tp_prices = extract_timepoint_prices(bars) if bars is not None else {}

            intraday_high = tp_prices.get('intraday_high', q.get('high', 0))
            intraday_low = tp_prices.get('intraday_low', q.get('low', 0))
            high_time = find_high_time(bars, intraday_high) if bars is not None else None

            # 计算各时点盈亏
            tp_profits = {}
            for time_str, _ in TIME_POINTS:
                p = tp_prices.get(time_str)
                if p is not None and sel_price > 0:
                    tp_profits[time_str] = round((p - sel_price) / sel_price * 100, 2)
                else:
                    tp_profits[time_str] = None

            # ===== 四层胜率计算 =====
            # Layer 1: 快照胜率（10:00）
            snapshot_profit = tp_profits.get('10:00')
            snapshot_win = 1 if snapshot_profit is not None and snapshot_profit > 0 else (0 if snapshot_profit is not None else None)

            # Layer 2: 收盘持有胜率（15:00）
            close_profit = round((close_price - sel_price) / sel_price * 100, 2) if close_price > 0 and sel_price > 0 else None
            close_win = 1 if close_profit is not None and close_profit > 0 else (0 if close_profit is not None else None)

            # Layer 3: 窗口可用胜率（建议卖出窗口内最高价）
            window_start = st.get('sell_window_start', '')
            window_end = st.get('sell_window_end', '')
            window_high = None
            if window_start and window_end and bars is not None:
                window_high = calc_window_high(bars, window_start, window_end)
            window_profit = round((window_high - sel_price) / sel_price * 100, 2) if window_high and sel_price > 0 else None
            window_win = 1 if window_profit is not None and window_profit > 0 else (0 if window_profit is not None else None)

            # Layer 4: 策略上限胜率（日内最高价）
            high_profit = round((intraday_high - sel_price) / sel_price * 100, 2) if intraday_high and sel_price > 0 else None
            high_win = 1 if high_profit is not None and high_profit > 0 else (0 if high_profit is not None else None)

            # 暴跌日不操作的不参与胜率统计
            skipped = (window_start == '--')

            # 预测准确度评分
            actual_data = {
                'open_pct': open_pct,
                'high_time': high_time,
                'intraday_high': intraday_high,
                'intraday_low': intraday_low,
                'close_pct': close_pct,
            }
            accuracy = calc_accuracy_score(st, actual_data)

            result = {
                'code': code, 'name': name, 'sel_price': sel_price,
                'close_price': close_price, 'close_pct': close_pct,
                'open_pct': open_pct,
                'intraday_high': intraday_high, 'intraday_low': intraday_low,
                'high_time': high_time,
                'snapshot_profit': snapshot_profit, 'snapshot_win': snapshot_win,
                'close_profit': close_profit, 'close_win': close_win,
                'window_high': window_high, 'window_profit': window_profit, 'window_win': window_win,
                'high_profit': high_profit, 'high_win': high_win,
                'skipped': skipped, 'accuracy_score': accuracy,
                'signal_type': st.get('signal_type', ''),
                'sell_window': f'{window_start}-{window_end}',
                'target_price': st.get('target_price', 0),
                'stop_loss_price': st.get('stop_loss_price', 0),
                'risk_level': st.get('risk_level', ''),
                'tp_profits': tp_profits,
            }
            stock_results.append(result)

    # ===== 汇总四层胜率 =====
    participating = [r for r in stock_results if not r['skipped']]
    total_count = len(participating)
    all_skipped = len(stock_results) > 0 and total_count == 0

    def calc_winrate(results, win_key, profit_key):
        valid = [r for r in results if r.get(win_key) is not None]
        if not valid:
            return 0, 0, 0, 0
        wins = sum(r[win_key] for r in valid)
        total = len(valid)
        wr = round(wins / total * 100, 1) if total > 0 else 0
        avg_profit = round(sum(r[profit_key] for r in valid) / total, 2) if total > 0 else 0
        total_pnl = round(sum(r[profit_key] for r in valid), 2)
        return wr, wins, total, avg_profit

    snap_wr, snap_wins, snap_n, snap_avg = calc_winrate(participating, 'snapshot_win', 'snapshot_profit')
    close_wr, close_wins, close_n, close_avg = calc_winrate(participating, 'close_win', 'close_profit')
    window_wr, window_wins, window_n, window_avg = calc_winrate(participating, 'window_win', 'window_profit')
    high_wr, high_wins, high_n, high_avg = calc_winrate(participating, 'high_win', 'high_profit')

    avg_accuracy = round(sum(r['accuracy_score'] for r in stock_results) / len(stock_results), 1) if stock_results else 0

    # 卖出窗口命中率
    window_hits = sum(1 for r in stock_results if r['high_time'] and r['sell_window'] and('--' not in r['sell_window']))
    window_total = sum(1 for r in stock_results if '--' not in r['sell_window'])
    window_hit_rate = round(window_hits / window_total * 100, 1) if window_total > 0 else 0

    # 大盘方向命中率
    market_pred = predict_data.get('market_env', {})
    market_hit = 1 if (market_pred.get('sh_open_pct', 0) > 0) == (sh_index_pct > 0) else 0

    # 目标价平均偏差
    target_diffs = []
    for r in stock_results:
        if r['target_price'] > 0 and r['intraday_high'] > 0 and r['sel_price'] > 0:
            t_pct = (r['target_price'] - r['sel_price']) / r['sel_price'] * 100
            a_pct = (r['intraday_high'] - r['sel_price']) / r['sel_price'] * 100
            target_diffs.append(abs(t_pct - a_pct))
    avg_target_diff = round(sum(target_diffs) / len(target_diffs), 2) if target_diffs else 0

    # ===== 生成复盘报告 =====
    today_str = datetime.now().strftime('%Y-%m-%d')
    lines = []
    lines.append(f'# 尾盘选股 收盘复盘报告2026.7.16')
    lines.append('')
    lines.append(f'- 选股日期：{last_day}')
    lines.append(f'- 复盘日期：{today_str}')
    lines.append(f'- 复盘时间：{datetime.now().strftime("%H:%M")}')
    if is_empty_day:
        lines.append(f'- **状态：空仓日（前日选股为0只，无个股数据）**')
    lines.append('')

    # 大盘环境
    lines.append('## 1. 大盘环境')
    lines.append('')
    lines.append('| 指标 | 预判 | 实际 | 命中 |')
    lines.append('|------|------|------|------|')
    actual_sh_pct = sh_index_pct
    pred_sh_open = market_pred.get('sh_open_pct', 'N/A')
    lines.append(f'| 上证开盘 | {pred_sh_open}% | {actual_sh_pct}% | {"✓" if market_hit else "✗"} |')
    lines.append(f'| 预判等级 | {market_pred.get("light", "N/A")} | - | - |')
    lines.append('')

    # 四层胜率
    lines.append('## 2. 四层胜率')
    lines.append('')
    if all_skipped:
        lines.append('> **暴跌日（大盘连跌≥2日），所有标的均不参与胜率统计，空仓观望是正确策略。**')
        lines.append('')
        # 仍然显示表格，但标注为"不参与"
        lines.append('| 胜率层级 | 胜率 | 说明 |')
        lines.append('|---------|------|------|')
        lines.append('| 快照胜率(10:00) | - | 暴跌日不参与 |')
        lines.append('| 收盘持有胜率(15:00) | - | 暴跌日不参与 |')
        lines.append('| **窗口可用胜率** | **-** | **暴跌日不参与(核心)** |')
        lines.append('| 策略上限胜率 | - | 暴跌日不参与 |')
        lines.append('')
        # 但补充"如果不空仓会怎样"的参考数据（基于收盘和日内最高计算）
        if stock_results:
            ref_close_wins = sum(1 for r in stock_results if r.get('close_win') == 1)
            ref_close_total = sum(1 for r in stock_results if r.get('close_win') is not None)
            ref_high_wins = sum(1 for r in stock_results if r.get('high_win') == 1)
            ref_high_total = sum(1 for r in stock_results if r.get('high_win') is not None)
            ref_close_wr = round(ref_close_wins / ref_close_total * 100, 1) if ref_close_total > 0 else 0
            ref_high_wr = round(ref_high_wins / ref_high_total * 100, 1) if ref_high_total > 0 else 0
            ref_close_avg = round(sum(r['close_profit'] for r in stock_results if r.get('close_profit') is not None) / max(ref_close_total, 1), 2)
            lines.append('> 参考数据（假设不空仓持有到收盘）：')
            lines.append(f'> - 收盘持有胜率：{ref_close_wr}% ({ref_close_wins}/{ref_close_total})，平均盈亏{ref_close_avg:+.2f}%')
            lines.append(f'> - 策略上限胜率：{ref_high_wr}% ({ref_high_wins}/{ref_high_total})')
            if ref_close_wr < 50:
                lines.append('> - 空仓决策正确：暴跌日持有收盘胜率不足50%，空仓规避了亏损风险')
            lines.append('')
    else:
        lines.append('| 胜率层级 | 胜率 | 盈利数 | 总数 | 平均盈亏% | 含义 |')
        lines.append('|---------|------|--------|------|----------|------|')
        lines.append(f'| 快照胜率(10:00) | {snap_wr}% | {snap_wins} | {snap_n} | {snap_avg:+.2f}% | 10点快看一眼 |')
        lines.append(f'| 收盘持有胜率(15:00) | {close_wr}% | {close_wins} | {close_n} | {close_avg:+.2f}% | 拿到收盘 |')
        lines.append(f'| **窗口可用胜率** | **{window_wr}%** | **{window_wins}** | **{window_n}** | **{window_avg:+.2f}%** | **按建议窗口卖(核心)** |')
        lines.append(f'| 策略上限胜率 | {high_wr}% | {high_wins} | {high_n} | {high_avg:+.2f}% | 日内最高(参考) |')
        lines.append('')

        if total_count > 0:
            skipped_count = len(stock_results) - total_count
            lines.append(f'> 参与统计: {total_count}只' + (f'，暴跌日跳过: {skipped_count}只' if skipped_count > 0 else ''))
            lines.append('')

    # 预测 vs 实际对比表
    lines.append('## 3. 预测 vs 实际对比')
    lines.append('')
    lines.append('| 代码 | 名称 | 信号 | 选股价 | 卖出窗口 | 窗口最高 | 窗口盈亏 | 日内最高 | 高点时间 | 收盘价 | 收盘盈亏 | 准确度 |')
    lines.append('|------|------|------|--------|---------|---------|---------|---------|---------|--------|---------|--------|')
    for r in stock_results:
        win_str = f'{r["window_profit"]:+.2f}%' if r['window_profit'] is not None else 'N/A'
        high_str = f'{r["high_profit"]:+.2f}%' if r['high_profit'] is not None else 'N/A'
        close_str = f'{r["close_profit"]:+.2f}%' if r['close_profit'] is not None else 'N/A'
        lines.append(f'| {r["code"]} | {r["name"]} | {r["signal_type"]} | {r["sel_price"]} | {r["sell_window"]} | {r["window_high"] or "-"} | {win_str} | {r["intraday_high"] or "-"} | {r["high_time"] or "-"} | {r["close_price"] or "-"} | {close_str} | {r["accuracy_score"]} |')
    lines.append('')

    # 日内走势
    lines.append('## 4. 日内各时点盈亏')
    lines.append('')
    header = '| 代码 | 名称 |'
    sep = '|------|------|'
    for time_str, _ in TIME_POINTS:
        header += f' {time_str} |'
        sep += '------|'
    lines.append(header)
    lines.append(sep)
    for r in stock_results:
        row = f'| {r["code"]} | {r["name"]} |'
        for time_str, _ in TIME_POINTS:
            p = r['tp_profits'].get(time_str)
            row += f' {p:+.2f}%' if p is not None else ' N/A |'
        lines.append(row)
    lines.append('')

    # 准确度分析
    lines.append('## 5. 预测准确度分析')
    lines.append('')
    lines.append('| 指标 | 数值 |')
    lines.append('|------|------|')
    lines.append(f'| 平均预测准确度 | {avg_accuracy}/100 |')
    lines.append(f'| 大盘方向命中 | {"✓" if market_hit else "✗"} |')
    lines.append(f'| 卖出窗口命中率 | {window_hit_rate}% ({window_hits}/{window_total}) |')
    lines.append(f'| 目标价平均偏差 | {avg_target_diff}% |')
    lines.append('')

    # 四层胜率交叉分析洞察
    lines.append('## 6. 四层胜率交叉分析')
    lines.append('')
    if all_skipped:
        lines.append('- 暴跌日所有标的均跳过胜率统计，无交叉分析数据')
        lines.append('- 空仓观望是风控策略的正确执行，不参与胜率统计不代表策略无效')
    else:
        insights = []
        if window_wr > 0 and snap_wr > 0 and window_wr > snap_wr + 10:
            insights.append(f'- 窗口可用胜率({window_wr}%)显著高于快照胜率({snap_wr}%) → 卖点偏晚，10点还没涨起来但窗口内涨了，维持当前窗口建议')
        if window_wr > 0 and close_wr >= 0 and window_wr > close_wr + 10:
            insights.append(f'- 窗口可用胜率({window_wr}%)高于收盘持有胜率({close_wr}%) → 午后跳水，必须在上午卖，加强"午前必卖"提示')
        if high_wr > 0 and window_wr >= 0 and high_wr > window_wr + 10:
            insights.append(f'- 策略上限胜率({high_wr}%)高于窗口可用胜率({window_wr}%) → 选股没问题但卖出时机判断有偏差，考虑调整窗口时间段')
        if window_wr < 40 and high_wr < 50:
            insights.append(f'- 四层胜率都偏低 → 选股策略或大盘环境判断有问题，检查筛选条件')
        if not insights:
            insights.append('- 四层胜率无显著偏差模式，当前策略配置合理')
        for ins in insights:
            lines.append(ins)
    lines.append('')

    # 保存报告
    report_path = os.path.join(BASE_DIR, f'review_{last_day}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # 保存JSON
    os.makedirs(REVIEW_HISTORY_DIR, exist_ok=True)
    json_data = {
        'review_date': today_str,
        'review_time': datetime.now().strftime('%H:%M'),
        'sel_date': last_day,
        'four_layer_winrate': {
            'snapshot': {'winrate': snap_wr, 'wins': snap_wins, 'total': snap_n, 'avg_profit': snap_avg},
            'close': {'winrate': close_wr, 'wins': close_wins, 'total': close_n, 'avg_profit': close_avg},
            'window': {'winrate': window_wr, 'wins': window_wins, 'total': window_n, 'avg_profit': window_avg},
            'ceiling': {'winrate': high_wr, 'wins': high_wins, 'total': high_n, 'avg_profit': high_avg},
        },
        'accuracy': {
            'avg_score': avg_accuracy,
            'market_hit': bool(market_hit),
            'window_hit_rate': window_hit_rate,
            'avg_target_diff': avg_target_diff,
        },
        'stocks': stock_results,
    }
    json_path = os.path.join(REVIEW_HISTORY_DIR, f'review_{last_day}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

    # 追加到 prediction_accuracy.csv
    csv_path = os.path.join(BASE_DIR, 'prediction_accuracy.csv')
    file_exists = os.path.exists(csv_path)
    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                '预测日期', '标的总数', '参与统计数',
                '快照胜率%', '收盘持有胜率%', '窗口可用胜率%', '策略上限胜率%',
                '快照平均盈亏%', '收盘平均盈亏%', '窗口平均盈亏%', '上限平均盈亏%',
                '平均预测准确度', '大盘命中', '卖出窗口命中率%', '目标价平均偏差%'
            ])
        writer.writerow([
            last_day, len(stock_results), total_count,
            snap_wr, close_wr, window_wr, high_wr,
            snap_avg, close_avg, window_avg, high_avg,
            avg_accuracy, 'Y' if market_hit else 'N', window_hit_rate, avg_target_diff
        ])

    print(f'\n  复盘报告已保存: {report_path}')
    print(f'  JSON数据已保存: {json_path}')
    print(f'  CSV追踪已追加: {csv_path}')
    print(f'\n{"="*70}')
    print(f'  ===== 四层胜率摘要 =====')
    if all_skipped:
        print(f'  暴跌日：所有标的均不参与胜率统计（空仓观望是正确策略）')
    else:
        print(f'  快照胜率(10:00):    {snap_wr}% (平均{snap_avg:+.2f}%)')
        print(f'  收盘持有胜率(15:00): {close_wr}% (平均{close_avg:+.2f}%)')
        print(f'  窗口可用胜率(核心):  {window_wr}% (平均{window_avg:+.2f}%)')
        print(f'  策略上限胜率(参考):  {high_wr}% (平均{high_avg:+.2f}%)')
    print(f'  平均预测准确度: {avg_accuracy}/100')
    print(f'  卖出窗口命中率: {window_hit_rate}%')
    print(f'{"="*70}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='尾盘选股 收盘复盘')
    parser.add_argument('--date', type=str, default=None, help='指定复盘的选股日期，格式YYYY-MM-DD')
    args = parser.parse_args()
    main(args.date)
