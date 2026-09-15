#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 三轮对比脚本2026.7.16
读取同一天14:00/14:30/14:50三次选股结果，对比差异并输出报告
"""

import os
import json
from datetime import datetime
from collections import OrderedDict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(BASE_DIR, 'runs')


def load_runs_for_date(date_str):
    """读取指定日期的所有运行结果"""
    if not os.path.exists(RUNS_DIR):
        return []

    files = [f for f in os.listdir(RUNS_DIR)
             if f.startswith(date_str) and f.endswith('.json')]
    files.sort()

    runs = []
    for fname in files:
        filepath = os.path.join(RUNS_DIR, fname)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            runs.append(data)
        except:
            pass
    return runs


def compare_three_runs(runs):
    """对比三轮选股结果，返回对比报告(Markdown)"""
    lines = []
    today = datetime.now().strftime('%Y-%m-%d')

    lines.append('# 尾盘选股 三轮对比报告2026.7.16')
    lines.append('')
    lines.append(f'- 日期：{today}')
    lines.append(f'- 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('')

    if len(runs) == 0:
        lines.append('**无运行数据**，请先运行选股脚本。')
        return '\n'.join(lines)

    # 按轮次排序
    slot_map = {}
    for r in runs:
        slot = r.get('run_slot', 0)
        if slot not in slot_map:
            slot_map[slot] = r

    slot_labels = {1: '14:00', 2: '14:30', 3: '14:50'}
    available_slots = sorted(slot_map.keys())

    # ===== 1. 大盘环境对比 =====
    lines.append('## 1. 大盘环境变化')
    lines.append('')
    lines.append('| 轮次 | 时间 | 上证指数 | 涨跌幅 | 涨跌比 | 大盘状态 | 3日趋势 |')
    lines.append('|------|------|---------|--------|--------|---------|--------|')
    for s in available_slots:
        r = slot_map[s]
        me = r.get('market_env', {})
        label = r.get('slot_label', slot_labels.get(s, ''))
        sh_ok = '正常' if me.get('sh_ok') else '偏弱'
        ratio_ok = 'OK' if me.get('ratio_ok') else '偏弱'
        up = me.get('up_count', '?')
        down = me.get('down_count', '?')
        trend_3d = me.get('sh_3d_trend', '-')
        if me.get('sh_consecutive_decline'):
            trend_3d = '**' + trend_3d + '**'
        lines.append(f'| 第{s}轮 | {label} | {me.get("sh_price","N/A")} | {me.get("sh_change_pct","N/A")}% | {up}:{down} | {sh_ok}+{ratio_ok} | {trend_3d} |')
    lines.append('')

    # ===== 2. 筛选漏斗对比 =====
    lines.append('## 2. 筛选漏斗对比')
    lines.append('')
    lines.append('| 轮次 | 全量扫描 | 硬性过滤 | 稳健筛选 | 形态过滤 | 趋势排除 | 深度验证 | 一档 | 二档 |')
    lines.append('|------|---------|---------|---------|---------|---------|---------|------|------|')
    for s in available_slots:
        r = slot_map[s]
        st = r.get('stats', {})
        lines.append(f'| 第{s}轮 | {st.get("total_scanned",0)} | {st.get("after_hard_filter",0)} | '
                     f'{st.get("after_profile_filter",0)} | {st.get("after_form_filter",0)} | '
                     f'{st.get("after_deep_trend_exclude",0)} | '
                     f'{st.get("final_count",0)} | {st.get("tier1_count",0)} | {st.get("tier2_count",0)} |')
    lines.append('')

    # ===== 3. 一档推荐对比 =====
    lines.append('## 3. 一档推荐对比(>=70分)')
    lines.append('')

    # 收集所有一档股票，按代码索引
    all_tier1_codes = OrderedDict()
    for s in available_slots:
        for stock in slot_map[s].get('tier1', []):
            code = stock['code']
            if code not in all_tier1_codes:
                all_tier1_codes[code] = {'name': stock['name'], 'scores': {}, 'prices': {}, 'changes': {}}
            all_tier1_codes[code]['scores'][s] = stock['score']
            all_tier1_codes[code]['prices'][s] = stock['price']
            all_tier1_codes[code]['changes'][s] = stock.get('change_pct', 0)

    if not all_tier1_codes:
        lines.append('三轮均无一档推荐。')
    else:
        # 表头
        header = '| 代码 | 名称 |'
        separator = '|------|------|'
        for s in available_slots:
            header += f' 第{s}轮分数 | 第{s}轮价格 | 第{s}轮涨幅 |'
            separator += '------|------|------|'
        header += ' 趋势 |'
        separator += '------|'
        lines.append(header)
        lines.append(separator)

        for code, info in all_tier1_codes.items():
            row = f'| {code} | {info["name"]} |'
            appeared_in = sorted(info['scores'].keys())
            for s in available_slots:
                if s in info['scores']:
                    row += f' **{info["scores"][s]}** | {info["prices"][s]} | {info["changes"][s]}% |'
                else:
                    row += ' - | - | - |'

            # 判断趋势
            if len(appeared_in) == len(available_slots):
                scores_list = [info['scores'][s] for s in available_slots]
                if all(scores_list[i] <= scores_list[i+1] for i in range(len(scores_list)-1)):
                    trend = '评分递增'
                elif all(scores_list[i] >= scores_list[i+1] for i in range(len(scores_list)-1)):
                    trend = '评分递减'
                else:
                    trend = '波动'
            elif len(appeared_in) == 1:
                if appeared_in[0] == max(available_slots):
                    trend = '新增(尾盘才入档)'
                else:
                    trend = '消失(后续被淘汰)'
            else:
                trend = '部分轮次出现'

            row += f' {trend} |'
            lines.append(row)

        lines.append('')

        # 稳定性分析
        always_tier1 = [code for code, info in all_tier1_codes.items()
                        if len(info['scores']) == len(available_slots)]
        new_in_final = [code for code, info in all_tier1_codes.items()
                        if max(info['scores'].keys()) == max(available_slots)
                        and len(info['scores']) == 1]
        dropped = [code for code, info in all_tier1_codes.items()
                   if min(info['scores'].keys()) < max(available_slots)
                   and max(info['scores'].keys()) < max(available_slots)]

        def fmt_list(codes, d):
            return ", ".join([f"{c} {d[c]['name']}" for c in codes]) if codes else "无"

        lines.append('**稳定性分析：**')
        lines.append(f'- 三轮均在一档：{len(always_tier1)}只 — {fmt_list(always_tier1, all_tier1_codes)}')
        lines.append(f'- 最后一轮新增：{len(new_in_final)}只 — {fmt_list(new_in_final, all_tier1_codes)}')
        lines.append(f'- 中途被淘汰：{len(dropped)}只 — {fmt_list(dropped, all_tier1_codes)}')
        lines.append('')

    # ===== 4. 二档关注对比 =====
    lines.append('## 4. 二档关注对比(50-69分)')
    lines.append('')

    all_tier2_codes = OrderedDict()
    for s in available_slots:
        for stock in slot_map[s].get('tier2', []):
            code = stock['code']
            if code not in all_tier2_codes:
                all_tier2_codes[code] = {'name': stock['name'], 'scores': {}}
            all_tier2_codes[code]['scores'][s] = stock['score']

    if not all_tier2_codes:
        lines.append('三轮均无二档关注。')
    else:
        header = '| 代码 | 名称 |'
        separator = '|------|------|'
        for s in available_slots:
            header += f' 第{s}轮分数 |'
            separator += '------|'
        lines.append(header)
        lines.append(separator)

        for code, info in all_tier2_codes.items():
            row = f'| {code} | {info["name"]} |'
            for s in available_slots:
                if s in info['scores']:
                    row += f' {info["scores"][s]} |'
                else:
                    row += ' - |'
            lines.append(row)
        lines.append('')

    # ===== 5. 档位升降 =====
    lines.append('## 5. 档位升降变化')
    lines.append('')

    if len(available_slots) >= 2:
        # 收集所有股票在各轮的档位
        all_codes = set()
        for s in available_slots:
            for stock in slot_map[s].get('tier1', []) + slot_map[s].get('tier2', []):
                all_codes.add(stock['code'])

        tier_changes = []
        for code in all_codes:
            name = None
            tiers = {}
            for s in available_slots:
                t1_codes = [st['code'] for st in slot_map[s].get('tier1', [])]
                t2_codes = [st['code'] for st in slot_map[s].get('tier2', [])]
                if code in t1_codes:
                    tiers[s] = '一档'
                    name = next(st['name'] for st in slot_map[s]['tier1'] if st['code'] == code)
                elif code in t2_codes:
                    tiers[s] = '二档'
                    name = next(st['name'] for st in slot_map[s]['tier2'] if st['code'] == code)

            # 判断升降
            sorted_slots = sorted(tiers.keys())
            if len(sorted_slots) >= 2:
                first_tier = tiers[sorted_slots[0]]
                last_tier = tiers[sorted_slots[-1]]
                if first_tier != last_tier:
                    change = f'{first_tier} → {last_tier}'
                    if first_tier == '二档' and last_tier == '一档':
                        change += ' (升级)'
                    elif first_tier == '一档' and last_tier == '二档':
                        change += ' (降级)'
                    tier_changes.append((code, name or code, change))

        if tier_changes:
            lines.append('| 代码 | 名称 | 变化 |')
            lines.append('|------|------|------|')
            for code, name, change in tier_changes:
                lines.append(f'| {code} | {name} | {change} |')
        else:
            lines.append('无档位升降变化（各轮档位一致）。')
    else:
        lines.append('仅1轮数据，无法对比档位升降。')
    lines.append('')

    # ===== 6. 深度趋势排除 =====
    lines.append('## 6. 深度趋势排除（距60日高点<-30%）')
    lines.append('')

    all_excluded = OrderedDict()
    for s in available_slots:
        for exc in slot_map[s].get('excluded_deep_trend', []):
            code = exc.get('code', '')
            if code not in all_excluded:
                all_excluded[code] = {'name': exc.get('name', ''), 'reasons': {}, 'slots': []}
            all_excluded[code]['reasons'][s] = exc.get('reason', '')
            all_excluded[code]['slots'].append(s)

    if all_excluded:
        header = '| 代码 | 名称 | 排除轮次 | 排除原因 |'
        separator = '|------|------|---------|---------|'
        lines.append(header)
        lines.append(separator)
        for code, info in all_excluded.items():
            slots_str = '/'.join([f'第{s}轮' for s in sorted(info['slots'])])
            reason = list(info['reasons'].values())[0]
            lines.append(f'| {code} | {info["name"]} | {slots_str} | {reason} |')
    else:
        lines.append('无深度趋势排除（所有标的距60日高点均>-30%）。')
    lines.append('')

    # ===== 7. ETF推荐对比 =====
    lines.append('## 7. ETF推荐对比')
    lines.append('')
    all_etf_codes = OrderedDict()
    for s in available_slots:
        for etf in slot_map[s].get('etf_recommendations', []):
            code = etf.get('code', '')
            if code not in all_etf_codes:
                all_etf_codes[code] = {'name': etf.get('name', ''), 'changes': {}}
            all_etf_codes[code]['changes'][s] = etf.get('change_pct', 0)

    if all_etf_codes:
        header = '| 代码 | 名称 |'
        separator = '|------|------|'
        for s in available_slots:
            header += f' 第{s}轮涨幅 |'
            separator += '------|'
        lines.append(header)
        lines.append(separator)
        for code, info in all_etf_codes.items():
            row = f'| {code} | {info["name"]} |'
            for s in available_slots:
                if s in info['changes']:
                    row += f' {info["changes"][s]}% |'
                else:
                    row += ' - |'
            lines.append(row)
    lines.append('')

    # ===== 8. 操作建议 =====
    lines.append('## 8. 操作建议')
    lines.append('')

    if len(available_slots) >= 2:
        final_slot = max(available_slots)
        final_tier1 = slot_map[final_slot].get('tier1', [])
        final_tier2 = slot_map[final_slot].get('tier2', [])

        # 大盘趋势判断
        market_changes = []
        sh_ok_all = True
        for s in available_slots:
            me = slot_map[s].get('market_env', {})
            market_changes.append(me.get('sh_change_pct', 0))
            if not me.get('sh_ok', True):
                sh_ok_all = False

        market_worsening = all(market_changes[i] >= market_changes[i+1]
                               for i in range(len(market_changes)-1)) if len(market_changes) >= 2 else False

        # 2026.7.16大盘弱时脉冲信号风险提示
        # 验证：sh_ok=false时脉冲胜率仅30%(3/10)，sh_ok=true时100%(6/6)
        pulse_codes = all_codes_union - consensus_all if 'all_codes_union' in dir() else set()

        if not sh_ok_all:
            lines.append(f'**\\u26a0 大盘偏弱环境提示**')
            lines.append(f'- 当前大盘sh_ok=false，验证数据显示此时脉冲信号胜率仅30%')
            lines.append(f'- **仅操作持续信号标的（两轮以上入选）**，脉冲信号标注高风险不建议操作')
            lines.append('')

        # === 极端情况：末轮无一档且无二档 ===
        if not final_tier1 and not final_tier2:
            lines.append(f'**末轮个股全部被淘汰，建议空仓观望。**')
            lines.append('')
            lines.append(f'- 最后一轮（{slot_map[final_slot].get("slot_label","")}）一档0只、二档0只，所有个股信号消失')
            if market_worsening:
                lines.append(f'- 大盘逐轮走弱（{" → ".join([f"{c}%" for c in market_changes])}），市场持续恶化')
            lines.append('- 防御机制在尾盘收紧，深度趋势排除/均线降档/K线形态过滤等关卡将不达标标的全部清理')
            lines.append('- **操作建议：今日不进场，空仓等待企稳信号。** 如已持仓，严格执行止损纪律。')
            lines.append('')

            # ETF仍可作为避险参考
            final_etfs = slot_map[final_slot].get('etf_recommendations', [])
            if final_etfs:
                etf_names = [f"{e.get('code')} {e.get('name')}({e.get('change_pct',0)}%)" for e in final_etfs[:3]]
                lines.append(f'**避险ETF参考**（{len(final_etfs)}只）：{", ".join(etf_names)}')
                lines.append('- 个股全军覆没时，逆势上涨的ETF（如银行/能源化工）可关注，但不宜重仓追高')
                lines.append('')
        else:
            # 三轮均在一档的=最稳定
            stable = [code for code, info in all_tier1_codes.items()
                      if len(info['scores']) == len(available_slots)]
            # 最后一轮新增的=尾盘强化
            final_new = [code for code, info in all_tier1_codes.items()
                         if max(info['scores'].keys()) == final_slot and len(info['scores']) == 1]

            if stable:
                stable_names = [f"{c} {all_tier1_codes[c]['name']}(末轮{all_tier1_codes[c]['scores'][final_slot]}分)" for c in stable]
                lines.append(f'**高置信标的**（三轮均一档，{len(stable)}只）：{", ".join(stable_names)}')
                lines.append('- 这些标的从14:00到14:50始终维持一档，信号最稳定，可优先考虑尾盘建仓')
                lines.append('')

            if final_new:
                new_names = [f"{c} {all_tier1_codes[c]['name']}({all_tier1_codes[c]['scores'][final_slot]}分)" for c in final_new]
                lines.append(f'**尾盘强化标的**（末轮才入一档，{len(final_new)}只）：{", ".join(new_names)}')
                lines.append('- 尾盘才达到一档门槛，可能是午后资金逐步流入的结果，需关注次日开盘确认')
                lines.append('')

            # 评分递减的=信号减弱
            declining = []
            for code, info in all_tier1_codes.items():
                if len(info['scores']) == len(available_slots):
                    scores = [info['scores'][s] for s in available_slots]
                    if all(scores[i] >= scores[i+1] for i in range(len(scores)-1)) and scores[0] > scores[-1]:
                        declining.append(f"{code} {info['name']}({scores[0]}→{scores[-1]})")
            if declining:
                lines.append(f'**信号减弱标的**（评分递减）：{", ".join(declining)}')
                lines.append('- 评分逐步下降，说明盘中条件在恶化，谨慎追入')
                lines.append('')

            # 大盘弱势提示
            if market_worsening:
                lines.append(f'**大盘逐轮走弱**（{" → ".join([f"{c}%" for c in market_changes])}），整体偏弱，控制仓位。')
                lines.append('')

            # 末轮仍有标的但数量减少
            if not stable and not final_new and final_tier1:
                t1_names = [f"{r['code']} {r['name']}({r.get('score',0)}分)" for r in final_tier1]
                lines.append(f'**末轮一档标的**（{len(final_tier1)}只）：{", ".join(t1_names)}')
                lines.append('- 无三轮稳定标的，尾盘仍有入选但信号不够强，轻仓试探为主，严格止损')
                lines.append('')
    else:
        lines.append('需至少2轮数据才能生成操作建议。')

    return '\n'.join(lines)


def main():
    today = datetime.now().strftime('%Y-%m-%d')

    print('=' * 60)
    print('  尾盘选股 三轮对比2026.7.16')
    print('=' * 60)
    print(f'  日期: {today}')

    runs = load_runs_for_date(today)
    print(f'  找到 {len(runs)} 轮运行数据')

    if not runs:
        print('\n  无运行数据。请先运行 run_and_save_v4.py')
        return

    for r in runs:
        slot = r.get('run_slot', '?')
        label = r.get('slot_label', '?')
        t1 = r.get('stats', {}).get('tier1_count', 0)
        t2 = r.get('stats', {}).get('tier2_count', 0)
        print(f'    第{slot}轮({label}): 一档{t1}只 / 二档{t2}只')

    report = compare_three_runs(runs)

    # 保存报告
    report_path = os.path.join(BASE_DIR, f'compare_{today}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f'\n  对比报告已保存: {report_path}')
    print('\n' + report)


if __name__ == '__main__':
    main()
