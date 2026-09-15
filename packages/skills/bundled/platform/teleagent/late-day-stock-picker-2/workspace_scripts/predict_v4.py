#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
早盘预判脚本2026.7.16
每个交易日09:30开盘后运行，读取前日三轮选股结果+当日开盘行情，
输出操作指南（含卖出时间窗口建议、目标价、止损价）。
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(BASE_DIR, 'runs')
PREDICT_HISTORY_DIR = os.path.join(BASE_DIR, 'predict_history')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
SLOT_LABELS = {1: '14:00', 2: '14:30', 3: '14:50'}


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


def load_slot_data(date_str, slot):
    """读取指定日期指定轮次的结果（取最新一次）"""
    if not os.path.exists(RUNS_DIR):
        return None
    files = [f for f in os.listdir(RUNS_DIR)
             if f.startswith(date_str) and f'_slot{slot}_' in f and f.endswith('.json')]
    if not files:
        return None
    files.sort(reverse=True)
    filepath = os.path.join(RUNS_DIR, files[0])
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def get_market_data():
    """获取上证指数和隔夜外盘数据"""
    result = {}
    # 上证指数
    try:
        url = 'https://qt.gtimg.cn/q=sh000001'
        r = requests.get(url, headers=HEADERS, timeout=10)
        parts = r.text.split('="')
        if len(parts) >= 2:
            fields = parts[1].rstrip('"').split('~')
            if len(fields) > 49:
                result['sh_price'] = float(fields[3]) if fields[3] else 0
                result['sh_pre_close'] = float(fields[4]) if fields[4] else 0
                result['sh_open'] = float(fields[5]) if fields[5] else 0
                result['sh_high'] = float(fields[33]) if fields[33] else 0
                result['sh_low'] = float(fields[34]) if fields[34] else 0
                result['sh_change_pct'] = round(float(fields[32]) if fields[32] else 0, 2)
                result['sh_open_pct'] = round(
                    (result['sh_open'] - result['sh_pre_close']) / result['sh_pre_close'] * 100, 2
                ) if result['sh_pre_close'] > 0 else 0
    except Exception as e:
        print(f'  上证指数获取失败: {e}')

    # 道琼斯指数（隔夜外盘参考）
    try:
        url = 'https://qt.gtimg.cn/q=usDJI'
        r = requests.get(url, headers=HEADERS, timeout=10)
        parts = r.text.split('="')
        if len(parts) >= 2:
            fields = parts[1].rstrip('"').split('~')
            if len(fields) > 32:
                result['dji_change_pct'] = round(float(fields[32]) if fields[32] else 0, 2)
    except:
        pass

    # 纳斯达克指数
    try:
        url = 'https://qt.gtimg.cn/q=usIXIC'
        r = requests.get(url, headers=HEADERS, timeout=10)
        parts = r.text.split('="')
        if len(parts) >= 2:
            fields = parts[1].rstrip('"').split('~')
            if len(fields) > 32:
                result['ixic_change_pct'] = round(float(fields[32]) if fields[32] else 0, 2)
    except:
        pass

    return result


def get_current_quotes(codes):
    """通过腾讯API获取个股实时行情"""
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
                change_pct = round(float(fields[32]) if fields[32] else 0, 2)
                volume_ratio = round(float(fields[49]) if len(fields) > 49 and fields[49] else 0, 2)
                turnover = round(float(fields[38]) if len(fields) > 38 and fields[38] else 0, 2)
                if price > 0:
                    open_pct = round((open_price - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0
                    results[code] = {
                        'name': name, 'price': price, 'pre_close': pre_close,
                        'open': open_price, 'change_pct': change_pct,
                        'volume_ratio': volume_ratio, 'turnover': turnover,
                        'open_pct': open_pct,
                    }
        except Exception as e:
            print(f'  API请求异常: {e}')
        import time
        time.sleep(0.2)
    return results


def classify_market(market_data, last_day_market_env):
    """大盘环境预判"""
    sh_open_pct = market_data.get('sh_open_pct', 0)
    sh_ok = last_day_market_env.get('sh_ok', True)
    sh_consecutive_decline = last_day_market_env.get('sh_consecutive_decline', False)
    sh_3d_trend = last_day_market_env.get('sh_3d_trend', '未知')
    sh_3d_decline_count = last_day_market_env.get('sh_3d_decline_count', 0)

    # 判断当日开盘状态
    if sh_open_pct > 0.2:
        open_status = '高开'
    elif sh_open_pct < -0.2:
        open_status = '低开'
    else:
        open_status = '平开'

    # 预判等级：绿灯/黄灯/红灯
    if sh_consecutive_decline and sh_3d_decline_count >= 2:
        light = '红灯'
        light_desc = '大盘连跌≥2日，观望为主'
    elif not sh_ok or sh_open_pct < -0.5:
        light = '黄灯'
        light_desc = '大盘偏弱，降仓≤40%'
    else:
        light = '绿灯'
        light_desc = '大盘正常，可正常操作'

    # 外盘参考
    dji = market_data.get('dji_change_pct', None)
    ixic = market_data.get('ixic_change_pct', None)
    us_market = ''
    if dji is not None:
        us_market += f'道琼斯{dji:+.1f}%'
    if ixic is not None:
        us_market += f' 纳指{ixic:+.1f}%'
    if not us_market:
        us_market = '数据获取失败'

    return {
        'sh_open_pct': sh_open_pct,
        'sh_change_pct': market_data.get('sh_change_pct', 0),
        'open_status': open_status,
        'sh_ok': sh_ok,
        'sh_3d_trend': sh_3d_trend,
        'sh_consecutive_decline': sh_consecutive_decline,
        'sh_3d_decline_count': sh_3d_decline_count,
        'light': light,
        'light_desc': light_desc,
        'us_market': us_market,
    }


def recommend_sell_strategy(market_class, signal_type, sel_price, open_pct, atr_pct=None):
    """根据大盘环境+信号类型推荐卖出策略
    2026.9.9：ATR动态止盈止损——止盈≈1.5×ATR(区间2%-5%)、止损≈1.0×ATR(区间1.5%-3%)，
    波动大的票给更宽区间防噪声扫损；ATR缺失时回落固定阈值。
    """

    def _atp(atr_val, base_val, low, high):
        if atr_val and atr_val > 0:
            return min(max(atr_val, low), high)
        return base_val

    is_up = market_class['sh_ok'] and not market_class['sh_consecutive_decline']
    is_crash = market_class['sh_consecutive_decline'] and market_class['sh_3d_decline_count'] >= 2

    if is_crash:
        return {
            'sell_window_start': '--',
            'sell_window_end': '--',
            'target_price': 0,
            'stop_loss_price': 0,
            'risk_level': '极高',
            'position_advice': '空仓观望',
            'predict_direction': '暴跌日不操作',
        }

    if is_up:
        if signal_type == '持续信号':
            return {
                'sell_window_start': '10:30', 'sell_window_end': '11:30',
                'target_price': round(sel_price * (1 + _atp(atr_pct, 3.0, 2.0, 5.0) / 100), 2),
                'stop_loss_price': round(sel_price * (1 - _atp(atr_pct, 2.0, 1.5, 3.0) / 100), 2),
                'risk_level': '低',
                'position_advice': '正常仓位',
                'predict_direction': '上午强，10:30-11:30冲高',
            }
        else:  # 脉冲信号
            return {
                'sell_window_start': '10:00', 'sell_window_end': '10:30',
                'target_price': round(sel_price * (1 + _atp(atr_pct, 2.0, 2.0, 5.0) / 100), 2),
                'stop_loss_price': round(sel_price * (1 - _atp(atr_pct, 2.0, 1.5, 3.0) / 100), 2),
                'risk_level': '中',
                'position_advice': '半仓',
                'predict_direction': '短冲高，见好就收',
            }
    else:  # 下跌日
        if signal_type == '持续信号':
            return {
                'sell_window_start': '14:30', 'sell_window_end': '15:00',
                'target_price': round(sel_price * (1 + _atp(atr_pct, 1.0, 2.0, 5.0) / 100), 2),
                'stop_loss_price': round(sel_price * (1 - _atp(atr_pct, 1.5, 1.5, 3.0) / 100), 2),
                'risk_level': '中',
                'position_advice': '半仓',
                'predict_direction': '午后修复，尾盘卖出',
            }
        else:  # 脉冲信号
            return {
                'sell_window_start': '09:30', 'sell_window_end': '10:00',
                'target_price': round(sel_price * (1 + _atp(atr_pct, 1.0, 2.0, 5.0) / 100), 2),
                'stop_loss_price': round(sel_price * (1 - _atp(atr_pct, 1.5, 1.5, 3.0) / 100), 2),
                'risk_level': '高',
                'position_advice': '轻仓',
                'predict_direction': '低开反弹，尽快离场',
            }


def main(target_date=None):
    print('=' * 70)
    print('  尾盘选股 早盘预判2026.9.9（ATR动态止损）')
    print('=' * 70)

    # 判断交易日
    is_trading, reason = is_trading_day()
    print(f'\n  今日: {datetime.now().strftime("%Y-%m-%d %H:%M")} | {reason}')
    if not is_trading:
        print('  非交易日，退出。')
        return

    # 找到前一交易日
    last_day = target_date or find_last_trading_day()
    if not last_day:
        print('\n  未找到前一交易日的选股数据，退出。')
        return

    print(f'  前一交易日: {last_day}')
    print(f'  预判时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    # 读取三轮选股数据
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
    slot_tier1 = {}
    slot_all = {}
    for s in available_slots:
        d = slot_data[s]
        slot_tier1[s] = {st['code']: st for st in d.get('tier1', [])}
        slot_all[s] = {st['code']: st for st in d.get('tier1', []) + d.get('tier2', [])}

    # 分类
    all_tier1_sets = [set(slot_tier1[s].keys()) for s in available_slots]
    consensus_tier1 = set.intersection(*all_tier1_sets) if all_tier1_sets else set()
    all_tier_sets = [set(slot_all[s].keys()) for s in available_slots]
    consensus_all = set.intersection(*all_tier_sets) if all_tier_sets else set()
    all_codes_union = set.union(*all_tier_sets) if all_tier_sets else set()
    pulse_only = all_codes_union - consensus_all

    print(f'\n  三轮均一档(最强): {len(consensus_tier1)}只')
    print(f'  三轮均入档(持续): {len(consensus_all - consensus_tier1)}只')
    print(f'  非全轮入选(脉冲): {len(pulse_only)}只')

    all_verify_codes = consensus_all | pulse_only
    if not all_verify_codes:
        print('\n  前日选股为0只，生成空仓预判快照（大盘环境仍需记录）。')

    # 获取前日大盘环境
    last_slot_max = max(available_slots) if available_slots else 1
    last_day_market_env = (slot_data.get(last_slot_max) or {}).get('market_env', {})

    # 获取当日大盘数据
    print(f'\n  获取当日大盘行情...')
    market_data = get_market_data()
    market_class = classify_market(market_data, last_day_market_env)

    print(f'  大盘开盘: {market_class["open_status"]} {market_class["sh_open_pct"]:+.2f}%')
    print(f'  预判等级: {market_class["light"]} - {market_class["light_desc"]}')
    print(f'  外盘参考: {market_class["us_market"]}')

    # 无标的时跳过个股行情获取
    if all_verify_codes:
        print(f'\n  获取{len(all_verify_codes)}只标的实时行情...')
        quotes = get_current_quotes(list(all_verify_codes))
    else:
        quotes = {}

    # 构建标的详情
    all_stocks = {}
    for s in available_slots:
        for st in slot_data[s].get('tier1', []) + slot_data[s].get('tier2', []):
            code = st['code']
            if code not in all_stocks:
                all_stocks[code] = {
                    'name': st['name'],
                    'scores': {},
                    'tiers': {},
                    'price': st['price'],
                    'signal_type': '持续信号' if code in consensus_all else '脉冲信号',
                    'atr_pct': (st.get('deep_info') or {}).get('atr_pct'),  # 2026.9.9 ATR14
                }
            all_stocks[code]['scores'][s] = st['score']
            all_stocks[code]['tiers'][s] = '一档' if st['score'] >= 70 else '二档'

    # 为每只标的生成操作建议（空仓时 stocks_output 为空列表）
    stocks_output = []
    for code in sorted(all_verify_codes):
        info = all_stocks.get(code, {})
        q = quotes.get(code, {})
        name = info.get('name', q.get('name', code))
        sel_price = info.get('price', 0)
        signal_type = info.get('signal_type', '脉冲信号')
        open_pct = q.get('open_pct', 0)

        strategy = recommend_sell_strategy(market_class, signal_type, sel_price, open_pct, atr_pct=info.get('atr_pct'))

        stock_data = {
            'code': code,
            'name': name,
            'signal_type': signal_type,
            'sel_price': sel_price,
            'open_pct': open_pct,
            'current_price': q.get('price', 0),
            'current_pct': q.get('change_pct', 0),
            'volume_ratio': q.get('volume_ratio', 0),
            'turnover': q.get('turnover', 0),
            'predict_direction': strategy['predict_direction'],
            'sell_window_start': strategy['sell_window_start'],
            'sell_window_end': strategy['sell_window_end'],
            'target_price': strategy['target_price'],
            'stop_loss_price': strategy['stop_loss_price'],
            'risk_level': strategy['risk_level'],
            'position_advice': strategy['position_advice'],
            'scores': info.get('scores', {}),
        }
        stocks_output.append(stock_data)

    # ========== 生成预判报告 ==========
    today_str = datetime.now().strftime('%Y-%m-%d')
    lines = []
    lines.append(f'# 尾盘选股 早盘预判报告2026.9.9（ATR动态止损）')
    lines.append('')
    lines.append(f'- 选股日期：{last_day}')
    lines.append(f'- 预判日期：{today_str}')
    lines.append(f'- 预判时间：{datetime.now().strftime("%H:%M")}')
    lines.append('')

    # 大盘环境
    lines.append('## 1. 大盘环境预判')
    lines.append('')
    lines.append('| 指标 | 数值 |')
    lines.append('|------|------|')
    lines.append(f'| 当日开盘 | {market_class["open_status"]} {market_class["sh_open_pct"]:+.2f}% |')
    lines.append(f'| 上证涨跌 | {market_class["sh_change_pct"]:+.2f}% |')
    lines.append(f'| 前日3日趋势 | {market_class["sh_3d_trend"]} |')
    decline_str = f'连跌{market_class["sh_3d_decline_count"]}日' if market_class['sh_consecutive_decline'] else '否'
    lines.append(f'| 是否连跌 | {decline_str} |')
    lines.append(f'| 预判等级 | **{market_class["light"]}** — {market_class["light_desc"]} |')
    lines.append(f'| 外盘参考 | {market_class["us_market"]} |')
    lines.append('')

    # 个股操作建议
    lines.append('## 2. 个股操作建议')
    lines.append('')

    is_crash = market_class['light'] == '红灯'
    if is_crash:
        lines.append('> **红灯预警：大盘连跌≥2日，建议空仓观望，不操作。**')
        lines.append('')

    # 按信号类型排序：持续信号优先
    stocks_sorted = sorted(stocks_output, key=lambda x: (
        0 if x['signal_type'] == '持续信号' else 1,
        -max(x['scores'].values()) if x['scores'] else 0
    ))

    for idx, st in enumerate(stocks_sorted, 1):
        risk_icon = {'低': '✓', '中': '△', '高': '⚠', '极高': '⛔'}.get(st['risk_level'], '')
        lines.append(f'### {idx}. {st["name"]}({st["code"]}) | {st["signal_type"]} | {risk_icon}{st["risk_level"]}')
        lines.append('')

        if is_crash:
            lines.append(f'> 暴跌日不操作，空仓观望。')
            lines.append('')
            continue

        lines.append(f'| 项目 | 值 |')
        lines.append(f'|------|------|')
        lines.append(f'| 选股价 | {st["sel_price"]} |')
        lines.append(f'| 开盘价 | {st["current_price"] if st["current_price"] else "N/A"} |')
        lines.append(f'| 开盘涨跌 | {st["open_pct"]:+.2f}% |')
        lines.append(f'| 量比 | {st["volume_ratio"]} |')
        lines.append(f'| 预判走势 | {st["predict_direction"]} |')
        lines.append(f'| **建议卖出窗口** | **{st["sell_window_start"]}~{st["sell_window_end"]}** |')
        lines.append(f'| 目标价 | {st["target_price"]} ({(st["target_price"]/st["sel_price"]-1)*100:+.2f}%) |')
        lines.append(f'| 止损价 | {st["stop_loss_price"]} ({(st["stop_loss_price"]/st["sel_price"]-1)*100:+.2f}%) |')
        lines.append(f'| 仓位建议 | {st["position_advice"]} |')

        score_str = ' / '.join([f'第{s}轮{st["scores"][s]}分' for s in sorted(st["scores"].keys())]) if st['scores'] else '无'
        lines.append(f'| 评分 | {score_str} |')
        lines.append('')

    # 总体策略
    lines.append('## 3. 总体策略')
    lines.append('')
    if is_crash:
        lines.append('**红灯：大盘连跌≥2日，建议空仓观望，不进场。**')
        lines.append('')
    else:
        cons_count = sum(1 for s in stocks_output if s['signal_type'] == '持续信号')
        pulse_count = sum(1 for s in stocks_output if s['signal_type'] == '脉冲信号')
        lines.append(f'- 持续信号：{cons_count}只（优先操作）')
        lines.append(f'- 脉冲信号：{pulse_count}只（谨慎操作）')
        if market_class['light'] == '黄灯':
            lines.append(f'- 大盘偏弱，总仓位建议≤40%，脉冲信号仅轻仓')
        else:
            lines.append(f'- 大盘正常，总仓位建议≤60%，单票≤15%')
        if stocks_output:
            lines.append(f'- 卖出窗口：持续信号{stocks_output[0]["sell_window_start"]}~{stocks_output[0]["sell_window_end"]}，脉冲信号见好就收')
            lines.append(f'- 下午策略：不宜持有过夜，清仓为主')
    lines.append('')

    # 保存报告
    report_path = os.path.join(BASE_DIR, f'predict_{last_day}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # 保存JSON快照（空仓也保存，保证 review 链路不断）
    os.makedirs(PREDICT_HISTORY_DIR, exist_ok=True)
    json_data = {
        'predict_date': today_str,
        'predict_time': datetime.now().strftime('%H:%M'),
        'sel_date': last_day,
        'market_env': market_class,
        'stocks': stocks_output,
        'is_empty_day': len(all_verify_codes) == 0,
    }
    json_path = os.path.join(PREDICT_HISTORY_DIR, f'predict_{last_day}.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    if all_verify_codes:
        print(f'\n  预判报告已保存: {report_path}')
    else:
        print(f'\n  空仓日预判快照已保存: {json_path}')
    print(f'  JSON快照已保存: {json_path}')
    print('\n' + '\n'.join(lines))


if __name__ == '__main__':
    # 支持手动指定日期参数
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    main(target_date)
