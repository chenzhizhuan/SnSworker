#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 运行+保存脚本2026.7.16
每个交易日14:00/14:30/14:50各运行一次，结果保存为JSON供对比
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(BASE_DIR, 'runs')
# 2026.9.9: 动态定位选股脚本，避免硬编码路径（实际技能目录带 users/... 前缀且名称为 -2）
def _locate_screener():
    """优先按本文件相对位置定位技能包内 scripts/，兜底搜索用户目录多级 users"""
    candidate = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'scripts', 'screener_v4.py'
    )
    if os.path.exists(candidate):
        return candidate
    root = os.environ.get('USERPROFILE', '')
    if root:
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.endswith('late-day-stock-picker-2'):
                p = os.path.join(dirpath, 'scripts', 'screener_v4.py')
                if os.path.exists(p):
                    return p
            if dirpath.count(os.sep) - root.count(os.sep) > 6:
                dirnames[:] = []
    return candidate  # 找不到时返回预期路径，调用方会报告不存在


SCREENER_PATH = _locate_screener()

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


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
            volume = float(fields[36]) if len(fields) > 36 and fields[36] else 0
            if volume > 0:
                return True, "交易日"
            else:
                return False, "节假日(无成交)"
    except:
        pass
    return True, "工作日(默认)"


def get_run_slot():
    """根据当前时间确定是哪一轮(1/2/3)"""
    now = datetime.now()
    hour, minute = now.hour, now.minute
    if hour == 14 and minute < 30:
        return 1, "14:00"
    elif hour == 14 and 30 <= minute < 50:
        return 2, "14:30"
    elif hour == 14 and minute >= 50:
        return 3, "14:50"
    else:
        # 非标准时间，按就近原则分配
        t = hour * 60 + minute
        if t < 14 * 60 + 15:
            return 1, "14:00"
        elif t < 14 * 60 + 40:
            return 2, "14:30"
        else:
            return 3, "14:50"


def run_screener():
    """执行选股脚本，返回命名空间"""
    if not os.path.exists(SCREENER_PATH):
        print(f'[错误] 未找到选股脚本: {SCREENER_PATH}')
        return None

    print(f'  执行: {SCREENER_PATH}')
    with open(SCREENER_PATH, 'r', encoding='utf-8-sig') as f:
        code = f.read()

    namespace = {}
    exec(code, namespace)
    return namespace


def serialize_stock(r):
    """序列化单只股票"""
    di = r.get('deep_info', {})
    return {
        'code': r['code'],
        'name': r['name'],
        'price': r['price'],
        'change_pct': r.get('change_pct', 0),
        'volume_ratio': r.get('volume_ratio', 0),
        'turnover': r.get('turnover', 0),
        'amplitude': r.get('amplitude', 0),
        'amount': r.get('amount', 0),
        'avg_price': r.get('avg_price', 0),
        'score': r.get('score', 0),
        'score_details': r.get('score_details', []),
        'penalty_details': r.get('penalty_details', []),
        'market_weak': r.get('market_weak', False),
        'deep_info': {
            'ma5': di.get('ma5'), 'ma10': di.get('ma10'), 'ma20': di.get('ma20'),
            'ma_pass': di.get('ma_pass'), 'vol_pass': di.get('vol_pass'),
            'vol_mult_5d': di.get('vol_mult_5d'),
            'consec_up': di.get('consec_up'), 'cum_5d': di.get('cum_5d'),
            'prev_1d': di.get('prev_1d'), 'dist_from_low': di.get('dist_from_low'),
            'dist_from_high': di.get('dist_from_high'), 'ma20_slope_up': di.get('ma20_slope_up'),
            'ma_deviation': di.get('ma_deviation'),
            'gain_ratio': di.get('gain_ratio'), 'shadow_body_ratio': di.get('shadow_body_ratio'),
            'atr': di.get('atr'), 'atr_pct': di.get('atr_pct'),   # 2026.9.9 ATR14
        }
    }


def save_result(namespace, run_slot, slot_label):
    """保存选股结果为JSON"""
    final_results = namespace.get('final_results', [])
    market_env = namespace.get('market_env', {})
    etf_results = namespace.get('etf_results', [])
    form_pass = namespace.get('form_pass', [])

    # 深度趋势排除列表
    excluded_deep_trend = namespace.get('excluded_deep_trend', [])

    tier1 = [r for r in final_results if r.get('score', 0) >= 70]
    tier2 = [r for r in final_results if 50 <= r.get('score', 0) < 70]

    today_str = datetime.now().strftime('%Y-%m-%d')
    now_str = datetime.now().strftime('%H:%M:%S')

    data = {
        'date': today_str,
        'run_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'run_slot': run_slot,
        'slot_label': slot_label,
        'screener_version': '2026.9.9',
        'market_env': {
            'sh_change_pct': market_env.get('sh_change_pct'),
            'sh_price': market_env.get('sh_price'),
            'sh_amplitude': market_env.get('sh_amplitude'),
            'up_count': market_env.get('up_count'),
            'down_count': market_env.get('down_count'),
            'sh_ok': market_env.get('sh_ok'),
            'ratio_ok': market_env.get('ratio_ok'),
            # 2026.9.9 情绪维度
            'limit_up': market_env.get('limit_up'),
            'limit_down': market_env.get('limit_down'),
            'boom': market_env.get('boom'),
            'boom_rate': market_env.get('boom_rate'),
            'sentiment_hot': market_env.get('sentiment_hot'),
            # 3日趋势
            'sh_3d_trend': market_env.get('sh_3d_trend'),
            'sh_consecutive_decline': market_env.get('sh_consecutive_decline'),
            'sh_3d_decline_count': market_env.get('sh_3d_decline_count'),
            'sh_d1': market_env.get('sh_d1'),
            'sh_d2': market_env.get('sh_d2'),
        },
        'tier1': [serialize_stock(r) for r in tier1],
        'tier2': [serialize_stock(r) for r in tier2],
        # 2026.9.9: 完整候选池（含三档），供 audit_overfit.py 做参数敏感性扫描
        'candidates_pool': [serialize_stock(r) for r in final_results],
        'etf_recommendations': [
            {'code': r.get('code'), 'name': r.get('name'), 'price': r.get('price'),
             'change_pct': r.get('change_pct'), 'volume_ratio': r.get('volume_ratio'),
             'turnover': r.get('turnover')}
            for r in etf_results[:8]
        ],
        # 深度趋势排除列表
        'excluded_deep_trend': [
            {'code': code, 'name': name, 'reason': reason}
            for code, name, reason in excluded_deep_trend
        ],
        'stats': {
            'total_scanned': namespace.get('total_scanned', 0),
            'after_hard_filter': namespace.get('count_after', 0),
            'after_profile_filter': namespace.get('count_after_risk', 0),
            'after_form_filter': len(form_pass),
            'after_deep_trend_exclude': len(excluded_deep_trend),
            'final_count': len(final_results),
            'tier1_count': len(tier1),
            'tier2_count': len(tier2),
        }
    }

    os.makedirs(RUNS_DIR, exist_ok=True)
    filename = f'{today_str}_slot{run_slot}_{now_str.replace(":","")}.json'
    filepath = os.path.join(RUNS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath, data


def main():
    print('=' * 60)
    print('  尾盘选股 三轮运行脚本2026.7.16')
    print('=' * 60)

    # 判断交易日
    is_trading, reason = is_trading_day()
    print(f'\n  今日: {datetime.now().strftime("%Y-%m-%d %H:%M")} | {reason}')
    if not is_trading:
        print('  非交易日，退出。')
        return

    # 确定轮次
    run_slot, slot_label = get_run_slot()
    print(f'  轮次: 第{run_slot}轮 ({slot_label})')

    # 执行选股
    print(f'\n  开始选股...')
    t0 = time.time()
    namespace = run_screener()
    if namespace is None:
        return

    elapsed = round(time.time() - t0, 1)
    print(f'\n  选股完成，耗时{elapsed}秒')

    # 保存结果
    filepath, data = save_result(namespace, run_slot, slot_label)


    print(f'  保存: {filepath}')

    # 输出3日趋势摘要
    me = data.get('market_env', {})
    trend = me.get('sh_3d_trend', '未知')
    consec = me.get('sh_consecutive_decline', False)
    print(f'\n  3日趋势: {trend}')
    if consec:
        print(f'  [2026.7.16] 大盘偏弱不出票')

    print(f'\n{"="*60}')
    print(f'  第{run_slot}轮({slot_label})完成')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
