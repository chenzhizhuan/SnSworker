#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 2026.7.16 - 突破确认策略 + 趋势强化过滤
2026.7.8改进点：
  1. 大盘环境过滤（上证涨跌 + 涨跌家数比）
  2. 连涨天数 + 累计涨幅限制（避免追末期）
  3. 位置判断（距20日低点 / 60日高点）
  4. K线形态过滤（上影线 / 收盘位置 / 实体占比）
  5. MA20斜率判断（中线趋势辅助）
  6. 综合评分制（非单一硬过滤，多维度量化打分）
2026.7.9改进：
  7. 前日涨幅独立扣分（>7%扣10分，>5%扣5分）
  8. 均线修复程度评估（MA5/MA10偏离度<2%不扣，2-5%扣5分，>5%扣10分）
2026.7.10改进：
  9. 上影线阈值收严：实体×0.8（原1.5倍太宽松，世龙实业上影线1.46倍仍通过）
  10. 连涨天数改为按日涨幅>0计算（原按收盘价>前日收盘，高开低收时有误差）
  11. 放量滞涨扣分：量比>=2且收盘涨幅<盘中最高涨幅60%扣5分+上影线/实体>0.5扣5分
2026.7.13改进（基于验证数据回测优化）：
  12. 均线不达标降档：ma_pass=False的股票锁定二档上限（最高69分），不得进入一档
  13. 大盘连续下跌检测：近3个完成交易日中连续2日下跌则判定大盘偏弱不出票
  14. 距60日高点<-30%直接排除：深度下降趋势中的反弹不参与
  15. 5日均量倍数<1.0额外扣5分：量能萎缩中的脉冲放量风险大
2026.7.14改进（三轮对比+验证驱动迭代）：
  16. 三轮对比选股机制(14:00/14:30/14:50)，次日10:00验证
  17. 次日验证驱动模型迭代（3日22只验证标的）
2026.7.16改进（基于7/13-7/15三天验证数据）：
  18. 脉冲双因子硬过滤：gain_ratio<0.60且shadow_body>0.50直接排除
      → 验证：7/13+7/15共5只满足此条件的标的全部亏损(100%亏损率)，0只盈利
  19. 大盘弱时脉冲标注高风险：sh_ok=false时仅持续信号(两轮以上入选)推荐操作
      → 验证：sh_ok=false时脉冲胜率仅30%(3/10)，sh_ok=true时100%(6/6)
流程: mootdx全量 → 硬性过滤 → 大盘检查(含3日趋势) → 腾讯补字段(含开盘价) → 稳健版筛选
      → K线形态过滤(收紧) → K线深度验证(65日) → 深度趋势排除(距高点<-30%)
      → 脉冲双因子排除(gain_ratio+shadow_body) → 综合评分(含扣分+均线降档) → 输出
2026.9.9改进：
  20. K线前复权(腾讯qfq优先+新浪降级)、市场情绪(涨停/跌停/炸板率)、流动性下限(成交额≥2亿)
  21. 板块联动提示(名称关键词聚类v1)、ATR14波动率(供predict动态止盈止损)
  22. 修复脉冲双因子判断顺序bug(gain_ratio在判断前未定义会NameError)
"""

import time
import json
import re
import pandas as pd
import numpy as np
import requests

T_START = time.time()
STAGE_TIMES = {}

def stage(name):
    t0 = time.time()
    print(f'\n{"="*60}')
    print(f'  {name}')
    print(f'{"="*60}')
    return t0

def stage_end(name, t0, count=None):
    elapsed = round((time.time() - t0) * 1000)
    STAGE_TIMES[name] = elapsed
    extra = f', {count}只' if count is not None else ''
    print(f'  >> {name}: {elapsed}ms{extra}')


# ============================================================
# STAGE 0: 大盘环境检查（2026.7.13: 新增近3日连续下跌检测）
# ============================================================
t0 = stage('STAGE 0: 大盘环境检查(2026.7.13含3日趋势)')

market_env = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

try:
    url = 'https://qt.gtimg.cn/q=sh000001'
    r = requests.get(url, headers=headers, timeout=10)
    parts = r.text.split('="')
    if len(parts) >= 2:
        fields = parts[1].rstrip('"').split('~')
        sh_price = float(fields[3]) if fields[3] else 0
        sh_pre_close = float(fields[4]) if fields[4] else 0
        sh_change_pct = float(fields[32]) if fields[32] else 0
        sh_high = float(fields[33]) if fields[33] else 0
        sh_low = float(fields[34]) if fields[34] else 0
        market_env['sh_change_pct'] = sh_change_pct
        market_env['sh_price'] = sh_price
        market_env['sh_amplitude'] = round((sh_high - sh_low) / sh_pre_close * 100, 2) if sh_pre_close > 0 else 0
except Exception as e:
    print(f'  大盘数据获取失败: {e}')

market_env['sh_ok'] = market_env.get('sh_change_pct', 0) > -1.5
print(f'  上证指数: {market_env.get("sh_price","N/A")} 涨跌幅={market_env.get("sh_change_pct","N/A")}%')

# 2026.7.13新增: 获取近5日上证K线，检测连续下跌趋势
market_env['sh_3d_trend'] = '未知'
market_env['sh_consecutive_decline'] = False
try:
    url_sh_kline = 'https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_shkline5/CN_MarketDataService.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=5'
    headers_sh = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                  'Referer': 'https://finance.sina.com.cn'}
    r_sh = requests.get(url_sh_kline, headers=headers_sh, timeout=10)
    match_sh = re.search(r'\((.*)\)', r_sh.text, re.DOTALL)
    if match_sh:
        sh_kdata = json.loads(match_sh.group(1))
        sh_closes = [float(d['close']) for d in sh_kdata]
        if len(sh_closes) >= 4:
            # 最近3个已完成交易日（不含今日进行中的）
            recent_3 = sh_closes[-4:-1]  # [3天前, 2天前, 昨天]
            d1 = (recent_3[-1] - recent_3[-2]) / recent_3[-2] * 100  # 昨天 vs 前天
            d2 = (recent_3[-2] - recent_3[-3]) / recent_3[-3] * 100  # 前天 vs 大前天
            decline_count = sum(1 for d in [d1, d2] if d < 0)
            consec_2d = d1 < 0 and d2 < 0  # 连续2天下跌

            market_env['sh_3d_decline_count'] = decline_count
            market_env['sh_consecutive_decline'] = consec_2d
            market_env['sh_d1'] = round(d1, 2)
            market_env['sh_d2'] = round(d2, 2)

            if consec_2d:
                market_env['sh_3d_trend'] = f'连续2日下跌(前日{d2:+.2f}% 昨日{d1:+.2f}%)'
                market_env['sh_ok'] = False
                print(f'  [2026.7.16] 近3日趋势: {market_env["sh_3d_trend"]} → 判定大盘偏弱，不出票')
            elif decline_count >= 2 and market_env.get('sh_change_pct', 0) < 0:
                market_env['sh_3d_trend'] = f'3日中{decline_count}天下跌且今日仍跌'
                market_env['sh_ok'] = False
                print(f'  [2026.7.16] 近3日趋势: {market_env["sh_3d_trend"]} → 判定大盘偏弱，不出票')
            else:
                market_env['sh_3d_trend'] = f'前日{d2:+.2f}% 昨日{d1:+.2f}% 趋势正常'
                print(f'  [2026.7.16] 近3日趋势: {market_env["sh_3d_trend"]}')
except Exception as e:
    print(f'  [2026.7.16] 上证K线趋势获取失败: {e}')

print(f'  大盘环境: {"正常" if market_env.get("sh_ok") else "偏弱"}')

stage_end('大盘环境检查', t0)


# ============================================================
# STAGE 1: mootdx 全量扫描
# ============================================================
t0 = stage('STAGE 1: mootdx全量扫描')

from mootdx.quotes import Quotes
client = Quotes.factory(market='std')

sz_df = client.stocks(market=0)
sh_df = client.stocks(market=1)

def filter_a_stock(df, market_val):
    result = []
    for _, row in df.iterrows():
        code = str(row.get('code', '')).zfill(6)
        name = str(row.get('name', ''))
        pre_close = row.get('pre_close', 0)
        if market_val == 0:
            is_a = code.startswith('00') or code.startswith('30')
        else:
            is_a = code.startswith('60') or code.startswith('68')
        if is_a and pre_close > 0:
            result.append({'market': market_val, 'code': code, 'name': name, 'pre_close': pre_close})
    return result

sz_a = filter_a_stock(sz_df, 0)
sh_a = filter_a_stock(sh_df, 1)
all_a = sz_a + sh_a

all_quotes = []
codes_only = [item['code'] for item in all_a]
batch_size = 80
for i in range(0, len(codes_only), batch_size):
    batch = codes_only[i:i + batch_size]
    try:
        df = client.quots(symbol=batch) if hasattr(client, 'quots') else client.quotes(symbol=batch)
        if df is not None and len(df) > 0:
            all_quotes.append(df)
    except:
        pass

df_all = pd.concat(all_quotes) if all_quotes else pd.DataFrame()
total_scanned = len(df_all)

# 统计涨跌家数
up_count = 0
down_count = 0
for _, row in df_all.iterrows():
    if row.get('price', 0) > 0 and row.get('last_close', 0) > 0:
        chg = (row['price'] - row['last_close']) / row['last_close']
        if chg > 0.001:
            up_count += 1
        elif chg < -0.001:
            down_count += 1
market_env['up_count'] = up_count
market_env['down_count'] = down_count
ratio = up_count / down_count if down_count > 0 else 999
market_env['ratio_ok'] = ratio >= 0.8
print(f'  涨:{up_count} 跌:{down_count} 比值={round(ratio, 2)} {"OK" if market_env["ratio_ok"] else "偏弱"}')

# 2026.9.9 情绪维度：涨停/跌停/炸板家数与炸板率
limit_up_count = 0
limit_down_count = 0
boom_count = 0
for _, row in df_all.iterrows():
    pc = row.get('last_close', 0)
    if pc <= 0 or row.get('price', 0) <= 0:
        continue
    chg = (row['price'] - pc) / pc * 100
    hi = row.get('high', 0)
    hi_chg = (hi - pc) / pc * 100 if hi > 0 else chg
    if chg >= 9.8:
        limit_up_count += 1
    elif chg <= -9.8:
        limit_down_count += 1
    if hi_chg >= 9.8 and chg < 9.8:
        boom_count += 1
boom_total = limit_up_count + boom_count
boom_rate = round(boom_count / boom_total, 2) if boom_total > 0 else 0.0
market_env['limit_up'] = limit_up_count
market_env['limit_down'] = limit_down_count
market_env['boom'] = boom_count
market_env['boom_rate'] = boom_rate
market_env['sentiment_hot'] = limit_up_count >= 50
print(f'  情绪: 涨停{limit_up_count} 跌停{limit_down_count} 炸板{boom_count} 炸板率={boom_rate*100:.0f}%')

stage_end('mootdx全量扫描', t0, total_scanned)


# ============================================================
# STAGE 2: 本地硬性过滤
# ============================================================
t0 = stage('STAGE 2: 本地硬性过滤')

valid = df_all[df_all['price'] > 0].copy()
valid['change_pct'] = (valid['price'] - valid['last_close']) / valid['last_close'] * 100
valid['amplitude'] = (valid['high'] - valid['low']) / valid['last_close'] * 100

count_before = len(valid)

mask_one = (valid['open'] == valid['price']) & (valid['high'] == valid['low']) & (abs(valid['change_pct']) >= 9.0)
valid = valid[~mask_one]
valid = valid[(valid['price'] >= 3.0) & (valid['price'] <= 105.0)]
valid = valid[valid['amplitude'] <= 15.0]
valid = valid[valid['change_pct'] > -7.0]
valid = valid[(valid['change_pct'] >= 1.0) & (valid['change_pct'] <= 6.0)]

count_after = len(valid)
stage_end('本地硬性过滤', t0, count_after)
print(f'  过滤: {count_before} -> {count_after} (剔除{count_before - count_after})')


# ============================================================
# STAGE 3: 腾讯API补字段
# ============================================================
t0 = stage('STAGE 3: 腾讯API补字段')

candidate_codes = valid['code'].tolist()
tencent_data = {}

for i in range(0, len(candidate_codes), 40):
    batch = candidate_codes[i:i + 40]
    codes_str = ','.join([('sh' + c if c.startswith('6') else 'sz' + c) for c in batch])
    url = f'https://qt.gtimg.cn/q={codes_str}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
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
            change_pct = float(fields[32]) if fields[32] else 0
            volume_ratio = float(fields[49]) if len(fields) > 49 and fields[49] else 0
            turnover = float(fields[38]) if len(fields) > 38 and fields[38] else 0
            amplitude = float(fields[43]) if len(fields) > 43 and fields[43] else 0
            amount = float(fields[37]) if len(fields) > 37 and fields[37] else 0
            high = float(fields[33]) if fields[33] else 0
            low = float(fields[34]) if fields[34] else 0
            avg_price = float(fields[51]) if len(fields) > 51 and fields[51] else 0
            pe = float(fields[39]) if fields[39] else 0

            tencent_data[code] = {
                'code': code, 'name': name, 'price': price,
                'pre_close': pre_close, 'open': open_price,
                'change_pct': round(change_pct, 2),
                'volume_ratio': round(volume_ratio, 2), 'turnover': round(turnover, 2),
                'amplitude': round(amplitude, 2), 'amount': round(amount, 0),
                'high': high, 'low': low, 'avg_price': avg_price,
                'pe': round(pe, 2) if pe else 0,
            }
    except Exception as e:
        print(f'  batch error: {e}')
    time.sleep(0.2)

stage_end('腾讯API补字段', t0, len(tencent_data))


# ============================================================
# STAGE 4: 稳健版筛选 + 强制避雷
# ============================================================
t0 = stage('STAGE 4: 稳健版筛选+避雷')

df_candidates = pd.DataFrame(tencent_data.values())

mask_st = df_candidates['name'].str.contains('ST|\\*ST|^S|退', case=False, na=False)
df_candidates = df_candidates[~mask_st]
df_candidates = df_candidates[~df_candidates['code'].str.startswith('92')]

count_before_profile = len(df_candidates)

df_candidates = df_candidates[
    (df_candidates['change_pct'] >= 1.8) &
    (df_candidates['change_pct'] <= 5.2) &
    (df_candidates['volume_ratio'] >= 1.9) &
    (df_candidates['volume_ratio'] <= 4.2) &
    (df_candidates['turnover'] >= 4.2) &
    (df_candidates['turnover'] <= 10.5) &
    (df_candidates['amplitude'] <= 13.0)
]

df_candidates = df_candidates[
    (df_candidates['avg_price'] > 0) &
    (df_candidates['price'] >= df_candidates['avg_price'])
]

count_after_profile = len(df_candidates)

df_candidates = df_candidates[
    (df_candidates['volume_ratio'] <= 6.8) &
    (df_candidates['turnover'] <= 17.5)
]

count_after_risk = len(df_candidates)

# 2026.9.9 流动性下限：成交额≥2亿(元)，小票滑点/操纵风险；成交额<=0或缺数据不误伤
count_before_liq = len(df_candidates)
df_candidates = df_candidates[(df_candidates['amount'] <= 0) | (df_candidates['amount'] >= 2.0e8)]
count_after_liq = len(df_candidates)

stage_end('STAGE 4: 稳健版筛选+避雷', t0, count_after_liq)
print(f'  筛选链: {len(tencent_data)} -> {count_before_profile} -> {count_after_profile} -> {count_after_risk} -> 流动性{count_after_liq}(剔除{count_before_liq - count_after_liq})')


# ============================================================
# STAGE 4.5: K线形态过滤（2026.7.10: 上影线阈值收严为实体×0.8）
# ============================================================
t0 = stage('STAGE 4.5: K线形态过滤(2026.7.10收紧)')

form_pass = []
form_fail = []
form_pass_map = {}

for _, row in df_candidates.iterrows():
    code = row['code']
    name = row['name']
    open_p = row['open']
    close_p = row['price']
    high = row['high']
    low = row['low']

    if open_p <= 0 or high <= 0 or low <= 0:
        form_fail.append((code, name, '数据缺失'))
        continue

    upper_shadow = high - max(open_p, close_p)
    body = abs(close_p - open_p)
    total_range = high - low + 0.001

    form_score = 0
    form_details = []

    # 2026.7.10: 上影线 <= 实体 × 0.8（原1.5太宽松）
    if upper_shadow <= body * 0.8:
        form_score += 1
        form_details.append('上影线OK')
    else:
        form_details.append(f'上影线长({round(upper_shadow,2)}>{round(body*0.8,2)})')

    if close_p >= high * 0.95:
        form_score += 1
        form_details.append('收盘高位OK')
    else:
        form_details.append(f'收盘偏低({round(close_p/high*100,1)}%)')

    body_ratio = body / total_range
    if body_ratio >= 0.4:
        form_score += 1
        form_details.append(f'实体{round(body_ratio*100,0)}%OK')
    else:
        form_details.append(f'实体低{round(body_ratio*100,0)}%')

    if form_score >= 2:
        form_pass.append(code)
        form_pass_map[code] = (form_score, form_details)
    else:
        form_fail.append((code, name, ' | '.join(form_details)))

print(f'  形态通过: {len(form_pass)}只, 不达标: {len(form_fail)}只')
for code, name, reason in form_fail:
    print(f'    剔除 {code} {name}: {reason}')

stage_end('K线形态过滤', t0, len(form_pass))


# ============================================================
# STAGE 5: K线深度验证（65日K线）+ 2026.7.14评分
# 2026.7.14改进：
#   - 距60日高点<-30%直接排除（深度下降趋势不抢反弹）
#   - 5日均量倍数<1.0额外扣5分（量能萎缩脉冲放量风险）
#   - 均线不达标锁定二档上限69分（不得进入一档）
# ============================================================
t0 = stage('STAGE 5: K线深度验证(65日) + 2026.7.14评分')

final_results = []
excluded_deep_trend = []  # 2026.7.13: 记录被深度趋势排除的股票

for _, row in df_candidates.iterrows():
    code = row['code']
    if code not in form_pass:
        continue

    name = row['name']

    deep_info = {}
    try:
        prefix = 'sh' if code.startswith('6') else 'sz'
        # 2026.9.9 复权修正：优先腾讯前复权(qfqday)，避免除权导致MA/距高点/连涨失真
        closes = opens = highs = lows = volumes = None
        try:
            url_qfq = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,65,qfq'
            r_qfq = requests.get(url_qfq, headers=headers, timeout=10)
            j = r_qfq.json()
            node = (j.get('data') or {}).get(f'{prefix}{code}')
            kdata = (node or {}).get('qfqday') or (node or {}).get('day')
            if kdata:
                closes = [float(d[2]) for d in kdata]      # close
                opens = [float(d[1]) for d in kdata]       # open
                highs = [float(d[3]) for d in kdata]       # high
                lows = [float(d[4]) for d in kdata]        # low
                volumes = [float(d[5]) for d in kdata]     # volume
        except Exception:
            pass
        if not closes:
            # 降级：新浪原逻辑
            url = f'https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_{code}_65/CN_MarketDataService.getKLineData?symbol={prefix}{code}&scale=240&ma=no&datalen=65'
            r = requests.get(url, headers=headers, timeout=10)
            match = re.search(r'\((.*)\)', r.text, re.DOTALL)
            if match:
                kdata = json.loads(match.group(1))
                closes = [float(d['close']) for d in kdata]
                opens = [float(d['open']) for d in kdata]
                highs = [float(d['high']) for d in kdata]
                lows = [float(d['low']) for d in kdata]
                volumes = [float(d['volume']) for d in kdata]
        if closes:

            if len(closes) >= 10:
                ma5 = sum(closes[-5:]) / 5
                ma10 = sum(closes[-10:]) / 10
                ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)

                avg5_vol = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else 0
                today_vol = volumes[-1]
                vol_mult = today_vol / avg5_vol if avg5_vol > 0 else 0

                ma_pass = ma5 > ma10 and row['price'] > ma5
                vol_pass = vol_mult >= 1.28

                # 2026.7.10改进: 连涨天数按日涨幅>0计算（而非收盘价>前日收盘）
                consec_up = 0
                for i in range(len(closes) - 1, 0, -1):
                    daily_chg = (closes[i] - closes[i-1]) / closes[i-1] * 100
                    if daily_chg > 0:
                        consec_up += 1
                    else:
                        break

                # 前5日累计涨幅
                cum_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0

                # 前1日涨幅
                prev_1d = (closes[-2] - closes[-3]) / closes[-3] * 100 if len(closes) >= 3 else 0

                # 距20日低点
                low_20 = min(closes[-20:]) if len(closes) >= 20 else min(closes)
                dist_from_low = (closes[-1] - low_20) / low_20 * 100

                # 距60日高点
                high_60 = max(closes[-60:]) if len(closes) >= 60 else max(closes)
                dist_from_high = (closes[-1] - high_60) / high_60 * 100

                # 2026.7.13: 距60日高点<-30%直接排除（深度下降趋势不抢反弹）
                if dist_from_high < -30:
                    excluded_deep_trend.append((code, name, f'距高点{dist_from_high:.1f}%<-30%'))
                    print(f'  [2026.7.13] 排除 {code} {name}: 距高点{dist_from_high:.1f}%<-30% 深度下降趋势')
                    continue

                # 2026.9.10: gain_ratio/shadow_body_ratio 提前计算（修复旧代码顺序bug：先使用后定义会NameError）
                intraday_max_gain = (row['high'] - row['open']) / row['open'] * 100 if row['open'] > 0 else 0
                close_gain = row['change_pct']
                gain_ratio = close_gain / intraday_max_gain if intraday_max_gain > 0 else 1.0

                upper_shadow_val = row['high'] - max(row['open'], row['price'])
                body_val = abs(row['price'] - row['open'])
                shadow_body_ratio = upper_shadow_val / body_val if body_val > 0 else 0

                # 2026.7.16脉冲双因子硬过滤：gain_ratio<0.60且shadow_body>0.50直接排除
                # 验证：7/13+7/15共5只满足此条件的标的全部亏损，0只盈利，100%亏损率
                if gain_ratio < 0.60 and shadow_body_ratio > 0.50:
                    excluded_deep_trend.append((code, name, f'脉冲双因子(收益率{gain_ratio:.2f}<0.60+影体比{shadow_body_ratio:.2f}>0.50)'))
                    print(f'  [2026.7.16] 排除 {code} {name}: 收益率{gain_ratio:.2f}<0.60且影体比{shadow_body_ratio:.2f}>0.50 放量冲高回落')
                    continue

                # MA20斜率
                if len(closes) >= 25:
                    ma20_5d_ago = sum(closes[-25:-5]) / 20
                    ma20_slope_up = ma20 > ma20_5d_ago
                else:
                    ma20_slope_up = True

                # MA5/MA10偏离度
                ma_deviation = abs(ma5 - ma10) / ma10 * 100 if ma10 > 0 else 0

                # 2026.9.9 ATR(14) 波动率，供次日动态止盈止损（predict_v4）
                atr = 0.0
                if highs and lows and len(closes) >= 15:
                    trs = []
                    for i in range(1, len(closes)):
                        tr = max(highs[i] - lows[i],
                                 abs(highs[i] - closes[i - 1]),
                                 abs(lows[i] - closes[i - 1]))
                        trs.append(tr)
                    atr = sum(trs[-14:]) / 14
                atr_pct = round(atr / closes[-1] * 100, 2) if closes and closes[-1] > 0 and atr > 0 else 0.0

                deep_info = {
                    'ma5': round(ma5, 2), 'ma10': round(ma10, 2), 'ma20': round(ma20, 2),
                    'ma_pass': ma_pass, 'vol_pass': vol_pass,
                    'vol_mult_5d': round(vol_mult, 2),
                    'consec_up': consec_up,
                    'cum_5d': round(cum_5d, 2),
                    'prev_1d': round(prev_1d, 2),
                    'dist_from_low': round(dist_from_low, 2),
                    'dist_from_high': round(dist_from_high, 2),
                    'ma20_slope_up': ma20_slope_up,
                    'ma_deviation': round(ma_deviation, 2),
                    'gain_ratio': round(gain_ratio, 2),
                    'shadow_body_ratio': round(shadow_body_ratio, 2),
                    'atr': round(atr, 3),          # 2026.9.9 ATR14(元)
                    'atr_pct': atr_pct,            # 2026.9.9 ATR/收盘价(%)
                }
    except Exception as e:
        deep_info = {'error': str(e)[:60]}

    time.sleep(0.15)

    # === 综合评分（2026.7.14：含全部扣分项 + 均线降档）===
    score = 0
    score_details = []
    penalty_details = []
    di = deep_info

    # 1. 均线多头排列 (20分)
    if di.get('ma_pass'):
        score += 20
        score_details.append('均线多头 +20')
    else:
        score_details.append('均线不达标 +0')
        ma_dev = di.get('ma_deviation', 0)
        if ma_dev < 2:
            penalty_details.append(f'MA偏离{ma_dev}%<2% 不扣分(即将修复)')
        elif ma_dev <= 5:
            score -= 5
            penalty_details.append(f'MA偏离{ma_dev}%2-5% 扣5分')
        else:
            score -= 10
            penalty_details.append(f'MA偏离{ma_dev}%>5% 扣10分(均线压制重)')

    # 2. 5日均量倍数 (20分)
    vm = di.get('vol_mult_5d', 0)
    if vm >= 1.28:
        score += 20
        score_details.append(f'量能{vm} +20')
    elif vm >= 1.0:
        score += 10
        score_details.append(f'量能{vm} +10')
    else:
        score_details.append(f'量能{vm} +0')

    # 2026.7.13新增: 5日均量倍数<1.0额外扣5分（量能萎缩中的脉冲放量风险大）
    if vm < 1.0:
        score -= 5
        penalty_details.append(f'5日均量倍数{vm}<1.0 量能萎缩 扣5分')

    # 3. 连涨天数 (15分)
    cu = di.get('consec_up', 0)
    if cu <= 1:
        score += 15
        score_details.append(f'连涨{cu}天 +15')
    elif cu <= 2:
        score += 10
        score_details.append(f'连涨{cu}天 +10')
    elif cu <= 3:
        score += 5
        score_details.append(f'连涨{cu}天 +5')
    else:
        score_details.append(f'连涨{cu}天 +0(末期)')

    # 4. 前5日累计涨幅 (15分)
    c5 = di.get('cum_5d', 0)
    if c5 <= 8:
        score += 15
        score_details.append(f'5日累计{c5}% +15')
    elif c5 <= 12:
        score += 10
        score_details.append(f'5日累计{c5}% +10')
    elif c5 <= 15:
        score += 5
        score_details.append(f'5日累计{c5}% +5')
    else:
        score_details.append(f'5日累计{c5}% +0(过高)')

    # 5. 位置判断 (15分)
    dfl = di.get('dist_from_low', 0)
    dfh = di.get('dist_from_high', 0)
    if dfl <= 15:
        score += 10
        score_details.append(f'距低点{dfl}% +10')
    elif dfl <= 25:
        score += 5
        score_details.append(f'距低点{dfl}% +5')
    else:
        score_details.append(f'距低点{dfl}% +0(偏高)')

    if dfh <= -5:
        score += 5
        score_details.append(f'距高点{dfh}% +5')
    else:
        score_details.append(f'距高点{dfh}% +0')

    # 6. K线形态 (10分)
    fs = form_pass_map.get(code, (0, []))[0]
    if fs == 3:
        score += 10
        score_details.append('形态满分 +10')
    elif fs == 2:
        score += 5
        score_details.append('形态及格 +5')

    # 7. 大盘环境 (5分)
    if market_env.get('sh_ok') and market_env.get('ratio_ok'):
        score += 5
        score_details.append('大盘OK +5')
    elif market_env.get('sh_ok'):
        score += 3
        score_details.append('大盘一般 +3')

    # 8. MA20斜率额外加分 (5分)
    if di.get('ma20_slope_up'):
        score += 5
        score_details.append('MA20上翘 +5')

    # === 扣分项 ===

    # 2026.7.9: 前日涨幅独立扣分
    p1 = di.get('prev_1d', 0)
    if p1 > 7:
        score -= 10
        penalty_details.append(f'前日涨{p1}%>7% 扣10分(昨天已大涨)')
    elif p1 > 5:
        score -= 5
        penalty_details.append(f'前日涨{p1}%>5% 扣5分(昨天涨幅较大)')
    else:
        penalty_details.append(f'前日涨{p1}% 无扣分')

    # 2026.7.10新增: 放量滞涨扣分
    # 规则1: 量比>=2.0 且 收盘涨幅 < 盘中最大涨幅×60%
    gr = di.get('gain_ratio', 1.0)
    vr_tencent = row['volume_ratio']
    if vr_tencent >= 2.0 and gr < 0.6:
        score -= 5
        penalty_details.append(f'放量滞涨(量比{vr_tencent} 收益率{round(gr*100,0)}%<60%) 扣5分')

    # 规则2: 量比>=2.0 且 上影线/实体>0.5
    sbr = di.get('shadow_body_ratio', 0)
    if vr_tencent >= 2.0 and sbr > 0.5:
        score -= 5
        penalty_details.append(f'放量长上影(量比{vr_tencent} 影/体={sbr}>0.5) 扣5分')

    # 2026.7.13新增: 均线不达标锁定二档上限（不得进入一档）
    # 回测验证：7/10一档2只全部ma_pass=False，平均亏损-3.33%
    if not di.get('ma_pass'):
        if score >= 70:
            original_score = score
            score = 69
            penalty_details.append(f'[2026.7.16] 均线未多头排列 原分{original_score}→锁定{score}分(二档上限)')

    result = {
        'code': code, 'name': name, 'price': row['price'],
        'change_pct': row['change_pct'], 'volume_ratio': row['volume_ratio'],
        'turnover': row['turnover'], 'amplitude': row['amplitude'],
        'amount': row['amount'], 'avg_price': row['avg_price'],
        'price_vs_avg': round(row['price'] / row['avg_price'], 4) if row['avg_price'] > 0 else 0,
        'deep_info': deep_info,
        'score': score,
        'score_details': score_details,
        'penalty_details': penalty_details,
        # 2026.7.16标注大盘弱时脉冲高风险
        'market_weak': not market_env.get('sh_ok', True),
    }
    final_results.append(result)

    di_s = deep_info
    print(f'\n  {code} {name} | 总分={score}')
    print(f'    价格={row["price"]} 涨幅={row["change_pct"]}% 量比={row["volume_ratio"]} 换手={row["turnover"]}%')
    print(f'    MA5={di_s.get("ma5","N/A")} MA10={di_s.get("ma10","N/A")} MA20={di_s.get("ma20","N/A")} | {"多头" if di_s.get("ma_pass") else "非多头"} MA偏离={di_s.get("ma_deviation","N/A")}%')
    print(f'    连涨={di_s.get("consec_up","N/A")}天 5日累计={di_s.get("cum_5d","N/A")}% 前日={di_s.get("prev_1d","N/A")}%')
    print(f'    距20日低={di_s.get("dist_from_low","N/A")}% 距60日高={di_s.get("dist_from_high","N/A")}% 量倍={di_s.get("vol_mult_5d","N/A")}')
    print(f'    收益率={di_s.get("gain_ratio","N/A")} 影/体比={di_s.get("shadow_body_ratio","N/A")}')
    print(f'    --- 加分明细 ---')
    for d in score_details:
        print(f'      {d}')
    print(f'    --- 扣分明细 ---')
    for d in penalty_details:
        print(f'      {d}')

# 2026.7.14: 输出被深度趋势排除的股票
if excluded_deep_trend:
    print(f'\n  [2026.7.16] 深度趋势排除({len(excluded_deep_trend)}只):')
    for code, name, reason in excluded_deep_trend:
        print(f'    {code} {name}: {reason}')

stage_end('K线深度验证', t0, len(final_results))

# ============================================================
# STAGE 5.5: 板块联动提示（2026.9.9 v1 简版，基于名称关键词聚类）
# ============================================================
SECTOR_KEYWORDS = {
    '半导体': ['半导体', '芯片', '集成电路', '晶圆', '封测', '中芯', '长电', '存储', '光刻'],
    'AI算力': ['AI', '算力', '机器人', '云计算', '大模型', '人工智能', '软件', '数据'],
    '医药': ['医药', '制药', '生物', '医疗', '疫苗', '创新药', '药业', '健康'],
    '白酒消费': ['白酒', '酒业', '食品', '消费', '零售', '饮料', '乳业'],
    '汽车': ['汽车', '汽配', '零部件', '整车', '新能源车', '智能车'],
    '新能源': ['新能源', '光伏', '储能', '锂电', '风电', '硅'],
    '军工': ['军工', '航天', '航空', '兵器', '国防', '雷达', '船舶'],
    '通信电子': ['通信', '光模块', 'CPO', '5G', '电路', '电源', '电子'],
    '化工材料': ['化工', '化学', '材料', '树脂', '钢铁', '有色', '稀土', '金属'],
    '金融地产': ['银行', '证券', '保险', '地产', '置业'],
}


def sector_of(name):
    for sector, kws in SECTOR_KEYWORDS.items():
        for kw in kws:
            if kw and kw.lower() in name.lower():
                return sector
    return '其他'


sector_counts = {}
for r in final_results:
    s = sector_of(r['name'])
    sector_counts[s] = sector_counts.get(s, 0) + 1
if final_results:
    top_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    print('\n  [2026.9.9] 板块联动: ' + ', '.join(f'{s}×{c}' for s, c in top_sectors) + '（名称聚类简版）')


# ============================================================
# STAGE 6: ETF筛选
# ============================================================
t0 = stage('STAGE 6: ETF筛选')

etf_codes = [
    '159915','510300','510500','159919','512100','159922','510050',
    '159949','512660','512480','159992','512010','512170','159881',
    '588000','159869','560250','159667','562500','159995',
    '515790','516160','515050','512690','512800','159766',
    '515170','512680','515710','159825','512980','515030',
    '562000','159605','513100','513500','159941',
    '510880','512880','515180','159989','513050',
    '159865','159790','159967','512580','159806',
    '515080','159998','512120','516950','159855',
    '159632','512220','516110','159840','159611',
    '512610','560150','159885','159732','515950',
    '512760','512970','159801','159996','515060',
    '159871','512670','512640','512400',
    '159966','512070','512200','159981','512710',
    '515220','515230','515880','516150',
    '159858','159969','512960','512770','512360',
]

etf_results = []
seen_codes = set()
for i in range(0, len(etf_codes), 40):
    batch = etf_codes[i:i + 40]
    codes_str = ','.join([('sh' + c if c.startswith('5') else 'sz' + c) for c in batch])
    url = f'https://qt.gtimg.cn/q={codes_str}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
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
            if code in seen_codes:
                continue
            seen_codes.add(code)
            name = fields[1]
            price = float(fields[3]) if fields[3] else 0
            change_pct = float(fields[32]) if fields[32] else 0
            volume_ratio = float(fields[49]) if len(fields) > 49 and fields[49] else 0
            turnover = float(fields[38]) if len(fields) > 38 and fields[38] else 0
            amount = float(fields[37]) if len(fields) > 37 and fields[37] else 0
            if price > 0 and change_pct >= 0.5 and volume_ratio >= 1.0:
                etf_results.append({
                    'code': code, 'name': name, 'price': price,
                    'change_pct': round(change_pct, 2),
                    'volume_ratio': round(volume_ratio, 2),
                    'turnover': round(turnover, 2),
                    'amount': round(amount, 0),
                })
    except:
        pass
    time.sleep(0.2)

etf_results.sort(key=lambda x: x['change_pct'], reverse=True)
stage_end('ETF筛选', t0, len(etf_results))


# ============================================================
# 最终输出
# ============================================================
total_elapsed = round((time.time() - T_START) * 1000)

print('\n' + '=' * 70)
print('  尾盘选股 最终结果 2026.7.16')
print('=' * 70)

final_results.sort(key=lambda x: x['score'], reverse=True)

tier1 = [r for r in final_results if r['score'] >= 70]
tier2 = [r for r in final_results if 50 <= r['score'] < 70]
tier3 = [r for r in final_results if r['score'] < 50]

print(f'\n  全量扫描: {total_scanned}只')
print(f'  硬性过滤后: {count_after}只')
print(f'  稳健版筛选后: {count_after_risk}只')
print(f'  形态过滤后: {len(form_pass)}只')
print(f'  深度趋势排除: {len(excluded_deep_trend)}只')
print(f'  深度验证后: {len(final_results)}只')
print(f'  一档(>=70分): {len(tier1)}只')
print(f'  二档(50-69分): {len(tier2)}只')
print(f'  三档(<50分): {len(tier3)}只')

print(f'\n  大盘: 上证{market_env.get("sh_change_pct","N/A")}% 涨跌比={market_env.get("up_count",0)}:{market_env.get("down_count",0)}')
print(f'  3日趋势: {market_env.get("sh_3d_trend","N/A")}')

print('\n----- 一档推荐(>=70分) -----')
for r in tier1:
    di = r['deep_info']
    print(f'\n  {r["code"]} {r["name"]} | 总分={r["score"]}')
    print(f'    价格={r["price"]} 涨幅={r["change_pct"]}% 量比={r["volume_ratio"]} 换手={r["turnover"]}% 振幅={r["amplitude"]}%')
    print(f'    连涨{di.get("consec_up","?")}天 5日累计={di.get("cum_5d","?")}% 前日={di.get("prev_1d","?")}% 距低点={di.get("dist_from_low","?")}% 距高点={di.get("dist_from_high","?")}%')
    print(f'    MA5={di.get("ma5","?")} MA10={di.get("ma10","?")} MA20={di.get("ma20","?")} MA偏离={di.get("ma_deviation","?")}% 量倍={di.get("vol_mult_5d","?")}')
    print(f'    收益率={di.get("gain_ratio","?")} 影/体比={di.get("shadow_body_ratio","?")}')
    print(f'    扣分: {" | ".join(r["penalty_details"])}')

print('\n----- 二档关注(50-69分) -----')
for r in tier2:
    di = r['deep_info']
    print(f'  {r["code"]} {r["name"]} | 总分={r["score"]} | 连涨{di.get("consec_up","?")}天 5日累计={di.get("cum_5d","?")}% 前日={di.get("prev_1d","?")}% 距低点={di.get("dist_from_low","?")}%')
    print(f'    收益率={di.get("gain_ratio","?")} 影/体比={di.get("shadow_body_ratio","?")}')
    print(f'    扣分: {" | ".join(r["penalty_details"])}')

print('\n----- 三档(剔除, <50分) -----')
for r in tier3:
    di = r['deep_info']
    print(f'  {r["code"]} {r["name"]} | 总分={r["score"]} | 连涨{di.get("consec_up","?")}天 5日累计={di.get("cum_5d","?")}% 前日={di.get("prev_1d","?")}%')
    print(f'    扣分: {" | ".join(r["penalty_details"])}')

print('\n----- ETF推荐 -----')
for r in etf_results[:8]:
    print(f'  {r["code"]} {r["name"]}: 涨幅={r["change_pct"]}% 量比={r["volume_ratio"]} 换手={r["turnover"]}% 成交额={round(r["amount"]/10000,1)}亿')

print(f'\n===== 总耗时: {round(total_elapsed/1000, 1)}秒 =====')
for k, v in STAGE_TIMES.items():
    print(f'    {k}: {round(v/1000, 1)}秒')
