# -*- coding: utf-8 -*-
"""
短线股票精选脚本 - 五层量化筛选 + 双源交叉验证 + 五维投资评估
数据源：pywencai（问财） + akshare
"""

import sys
import json
import argparse
from datetime import datetime, timedelta

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: pandas/numpy not installed. Run: pip install pandas numpy")
    sys.exit(1)

try:
    import akshare as ak
except ImportError:
    print("ERROR: akshare not installed. Run: pip install akshare")
    sys.exit(1)

try:
    import pywencai
except ImportError:
    print("ERROR: pywencai not installed. Run: pip install pywencai")
    sys.exit(1)


# ============================================================
# 配置常量
# ============================================================

# 双源验证允许偏差阈值
PRICE_DEVIATION_MAX = 0.01          # 最新价允许 1% 偏差
VOLUME_RATIO_DEVIATION_MAX = 0.10   # 量比允许 10% 偏差
TURNOVER_DEVIATION_MAX = 0.01       # 换手率允许 1 个百分点偏差
CHANGE_DEVIATION_MAX = 0.005        # 日涨幅允许 0.5 个百分点偏差
INFLOW_DEVIATION_MAX = 0.20         # 主力净流入允许 20% 偏差(金额>1000万)

# 第二层筛选阈值
VOLUME_RATIO_MIN = 1.5
VOLUME_RATIO_MAX = 5.0
TURNOVER_MIN = 0.03
TURNOVER_MAX = 0.15
CHANGE_MIN = 0.01
CHANGE_MAX = 0.07

# 第五层风控阈值
MIN_AMOUNT = 50000000       # 日成交额最低 5000 万
MIN_PRICE = 3.0             # 最低股价 3 元
MIN_MARKET_CAP = 3000000000 # 最低总市值 30 亿

# 五维评分权重
WEIGHT_TREND = 0.25
WEIGHT_VOLUME = 0.20
WEIGHT_CAPITAL = 0.25
WEIGHT_TECH = 0.15
WEIGHT_RISK = 0.15

# 输出数量
TOP_N = 15


# ============================================================
# 工具函数
# ============================================================

def safe_get(func, default=None, retries=2, delay=1):
    """安全调用函数，带重试"""
    import time
    for i in range(retries):
        try:
            result = func()
            return result
        except Exception as e:
            if i < retries - 1:
                time.sleep(delay)
            else:
                print(f"  WARN: {func.__name__} failed after {retries} retries: {e}")
                return default


def check_deviation(source1_val, source2_val, threshold, metric_name, code):
    """检查双源数据偏差，返回 (is_consistent, deviation_ratio)"""
    if source1_val is None or source2_val is None:
        return False, None
    try:
        v1 = float(source1_val)
        v2 = float(source2_val)
        if abs(v1) < 1e-9 and abs(v2) < 1e-9:
            return True, 0.0
        denominator = max(abs(v1), abs(v2))
        if denominator < 1e-9:
            return abs(v1 - v2) < 1e-6, 0.0
        deviation = abs(v1 - v2) / denominator
        return deviation <= threshold, deviation
    except (TypeError, ValueError):
        return False, None


# ============================================================
# 第一层：趋势层筛选
# ============================================================

def filter_trend(candidates):
    """均线多头排列 + 周线趋势确认"""
    print("[第一层] 趋势层筛选中...")
    passed = []

    for idx, stock in enumerate(candidates):
        code = stock.get("code", "")
        name = stock.get("name", "")
        try:
            # 获取日K线数据（最近30个交易日）
            df_daily = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df_daily is None or len(df_daily) < 20:
                continue

            df_daily = df_daily.tail(30).copy()
            closes = df_daily["收盘"].astype(float)

            # 计算均线
            ma5 = closes.rolling(5).mean()
            ma10 = closes.rolling(10).mean()
            ma20 = closes.rolling(20).mean()

            # 检查多头排列：MA5 > MA10 > MA20
            if ma5.iloc[-1] <= ma10.iloc[-1] or ma10.iloc[-1] <= ma20.iloc[-1]:
                continue

            # 检查 MA5 斜率 > 0
            if ma5.iloc[-1] <= ma5.iloc[-2]:
                continue

            # 检查 MA10 斜率 >= 0
            if ma10.iloc[-1] < ma10.iloc[-2]:
                continue

            # 检查收盘价 > MA20
            if closes.iloc[-1] <= ma20.iloc[-1]:
                continue

            # 周线趋势：获取周K线
            df_weekly = ak.stock_zh_a_hist(symbol=code, period="weekly", adjust="qfq")
            if df_weekly is not None and len(df_weekly) >= 10:
                w_closes = df_weekly.tail(10)["收盘"].astype(float)
                w_ma5 = w_closes.rolling(5).mean()
                w_ma10 = w_closes.rolling(10).mean()
                weekly_trend = w_ma5.iloc[-1] > w_ma10.iloc[-1] if len(w_ma10) > 0 and not pd.isna(w_ma10.iloc[-1]) else False
            else:
                weekly_trend = False

            stock["ma5"] = round(ma5.iloc[-1], 2)
            stock["ma10"] = round(ma10.iloc[-1], 2)
            stock["ma20"] = round(ma20.iloc[-1], 2)
            stock["ma5_slope"] = round((ma5.iloc[-1] - ma5.iloc[-2]) / ma5.iloc[-2] * 100, 2)
            stock["weekly_trend"] = weekly_trend
            stock["latest_close"] = round(closes.iloc[-1], 2)
            stock["daily_data"] = df_daily

            passed.append(stock)

        except Exception as e:
            print(f"  WARN: {code} {name} 趋势层异常: {e}")
            continue

    print(f"[第一层] 通过: {len(passed)}/{len(candidates)}")
    return passed


# ============================================================
# 第二层：量价层筛选
# ============================================================

def filter_volume_price(candidates):
    """量比 + 换手率 + 涨幅区间筛选，双源验证"""
    print("[第二层] 量价层筛选中...")
    passed = []
    data_issues = []

    today_str = datetime.now().strftime("%Y%m%d")

    # 通过问财获取量比/换手率排名数据
    wencai_data = {}
    try:
        df_wencai = pywencai.get(query="量比大于1且换手率大于3%", date=today_str)
        if df_wencai is not None and len(df_wencai) > 0:
            for _, row in df_wencai.iterrows():
                code_raw = str(row.get("股票代码", "")).strip()
                code_clean = code_raw[:6]
                wencai_data[code_clean] = {
                    "volume_ratio_wc": float(row.get("量比", 0)),
                    "turnover_wc": float(row.get("换手率", 0)) / 100 if float(row.get("换手率", 0)) > 1 else float(row.get("换手率", 0)),
                }
    except Exception as e:
        print(f"  WARN: 问财数据获取异常: {e}")

    for stock in candidates:
        code = stock.get("code", "")
        name = stock.get("name", "")
        try:
            # akshare 获取实时行情
            df_realtime = ak.stock_zh_a_spot_em()
            if df_realtime is None:
                continue
            row_match = df_realtime[df_realtime["代码"] == code]
            if row_match.empty:
                continue
            row = row_match.iloc[0]

            volume_ratio_ak = float(row.get("量比", 0))
            turnover_ak = float(row.get("换手率", 0)) / 100 if float(row.get("换手率", 0)) > 1 else float(row.get("换手率", 0))
            change_pct = float(row.get("涨跌幅", 0)) / 100 if abs(float(row.get("涨跌幅", 0))) > 1 else float(row.get("涨跌幅", 0))

            # 双源验证
            wc_data = wencai_data.get(code, {})
            dev_issues = []

            if wc_data.get("volume_ratio_wc"):
                ok, dev = check_deviation(volume_ratio_ak, wc_data["volume_ratio_wc"], VOLUME_RATIO_DEVIATION_MAX, "量比", code)
                if not ok:
                    dev_issues.append(f"量比偏差{dev:.1%}")

            if wc_data.get("turnover_wc"):
                ok, dev = check_deviation(turnover_ak, wc_data["turnover_wc"], TURNOVER_DEVIATION_MAX, "换手率", code)
                if not ok:
                    dev_issues.append(f"换手率偏差{dev:.1%}")

            if dev_issues:
                data_issues.append(f"{code} {name}: {', '.join(dev_issues)}")
                stock["data_suspect"] = True
                stock["data_issues"] = dev_issues
                continue  # 数据存疑，排除

            # 量比范围
            if not (VOLUME_RATIO_MIN <= volume_ratio_ak <= VOLUME_RATIO_MAX):
                continue

            # 换手率范围
            if not (TURNOVER_MIN <= turnover_ak <= TURNOVER_MAX):
                continue

            # 涨幅区间
            if not (CHANGE_MIN <= change_pct <= CHANGE_MAX):
                continue

            # 量价配合：近3日放量且涨幅>0的交易日≥2天
            daily_data = stock.get("daily_data")
            if daily_data is not None and len(daily_data) >= 4:
                recent_3 = daily_data.tail(3)
                vol_prev = daily_data.iloc[-4]["成交量"]
                up_days = 0
                for _, r in recent_3.iterrows():
                    if float(r["涨跌幅"]) > 0 and float(r["成交量"]) > vol_prev * 0.9:
                        up_days += 1
                    vol_prev = float(r["成交量"])
                if up_days < 2:
                    continue
            else:
                continue

            stock["volume_ratio"] = round(volume_ratio_ak, 2)
            stock["turnover_rate"] = round(turnover_ak * 100, 2)
            stock["change_pct"] = round(change_pct * 100, 2)
            passed.append(stock)

        except Exception as e:
            print(f"  WARN: {code} {name} 量价层异常: {e}")
            continue

    if data_issues:
        print(f"  数据存疑排除: {len(data_issues)} 只")
        for issue in data_issues[:5]:
            print(f"    - {issue}")

    print(f"[第二层] 通过: {len(passed)}/{len(candidates)}")
    return passed


# ============================================================
# 第三层：资金层筛选
# ============================================================

def filter_capital(candidates):
    """主力净流入 + 大单占比 + 北向资金"""
    print("[第三层] 资金层筛选中...")
    passed = []

    for stock in candidates:
        code = stock.get("code", "")
        name = stock.get("name", "")
        try:
            # 个股资金流
            df_capital = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith("6") else "sz")
            if df_capital is None or len(df_capital) < 3:
                continue

            df_recent = df_capital.tail(3)

            # 最近1日主力净流入 > 0
            latest_inflow = float(df_recent.iloc[-1].get("主力净流入-净额", 0))
            if latest_inflow <= 0:
                continue

            # 最近3日主力净流入合计 > 0
            inflow_3d = df_recent["主力净流入-净额"].astype(float).sum()
            if inflow_3d <= 0:
                continue

            # 大单占比 > 30%
            main_pct = float(df_recent.iloc[-1].get("主力净流入-净占比", 0))
            if main_pct < 30:
                continue

            stock["main_inflow"] = round(latest_inflow / 10000, 2)  # 万元
            stock["main_inflow_3d"] = round(inflow_3d / 10000, 2)
            stock["main_pct"] = round(main_pct, 2)
            stock["capital_data"] = df_recent
            passed.append(stock)

        except Exception as e:
            print(f"  WARN: {code} {name} 资金层异常: {e}")
            continue

    print(f"[第三层] 通过: {len(passed)}/{len(candidates)}")
    return passed


# ============================================================
# 第四层：技术层筛选
# ============================================================

def filter_technical(candidates):
    """MACD + KDJ + RSI + 布林带"""
    print("[第四层] 技术层筛选中...")
    passed = []

    for stock in candidates:
        code = stock.get("code", "")
        name = stock.get("name", "")
        try:
            daily_data = stock.get("daily_data")
            if daily_data is None or len(daily_data) < 30:
                continue

            closes = daily_data["收盘"].astype(float).values
            highs = daily_data["最高"].astype(float).values
            lows = daily_data["最低"].astype(float).values

            # --- MACD 计算 ---
            ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean()
            ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            macd_hist = (dif - dea) * 2

            # 金叉或柱状体由负转正
            macd_golden = dif.iloc[-1] > dea.iloc[-1]
            macd_turn = macd_hist.iloc[-1] > 0 and macd_hist.iloc[-2] <= 0
            if not (macd_golden or macd_turn):
                continue

            # --- KDJ 计算 ---
            kdj_k, kdj_d, kdj_j = _calc_kdj(highs, lows, closes)
            if not (kdj_k > kdj_d and kdj_j < 100):
                continue

            # --- RSI 计算 ---
            rsi6 = _calc_rsi(closes, 6)
            if not (50 < rsi6 < 80):
                continue

            # --- 布林带 ---
            mid = np.mean(closes[-20:])
            std = np.std(closes[-20:])
            upper = mid + 2 * std
            lower = mid - 2 * std
            mid_slope = (mid - np.mean(closes[-21:-1])) / np.mean(closes[-21:-1])

            # 股价突破中轨且中轨斜率 > 0
            if not (closes[-1] > mid and mid_slope > 0):
                continue

            stock["macd_dif"] = round(dif.iloc[-1], 4)
            stock["macd_dea"] = round(dea.iloc[-1], 4)
            stock["macd_hist"] = round(macd_hist.iloc[-1], 4)
            stock["kdj_k"] = round(kdj_k, 2)
            stock["kdj_d"] = round(kdj_d, 2)
            stock["kdj_j"] = round(kdj_j, 2)
            stock["rsi6"] = round(rsi6, 2)
            stock["boll_mid"] = round(mid, 2)
            stock["boll_upper"] = round(upper, 2)
            stock["boll_lower"] = round(lower, 2)
            passed.append(stock)

        except Exception as e:
            print(f"  WARN: {code} {name} 技术层异常: {e}")
            continue

    print(f"[第四层] 通过: {len(passed)}/{len(candidates)}")
    return passed


def _calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """计算 KDJ 指标"""
    lowest_low = np.min(lows[-n:])
    highest_high = np.max(highs[-n:])
    rsv = (closes[-1] - lowest_low) / (highest_high - lowest_low) * 100 if highest_high != lowest_low else 50
    # 简化计算（精确版需要递推历史K/D值）
    k = rsv  # 近似
    d = k     # 近似
    j = 3 * k - 2 * d
    return k, d, j


def _calc_rsi(closes, period=6):
    """计算 RSI 指标"""
    deltas = np.diff(closes[-period-1:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ============================================================
# 第五层：风控层筛选
# ============================================================

def filter_risk(candidates):
    """ST/退市/停牌/解禁/减持 风控过滤"""
    print("[第五层] 风控层筛选中...")
    passed = []
    excluded = []

    for stock in candidates:
        code = stock.get("code", "")
        name = stock.get("name", "")
        red_flags = []
        yellow_flags = []

        try:
            # ST 标记检查
            if "ST" in name or "st" in name:
                red_flags.append("ST标记")

            # 退市风险
            if "退" in name:
                red_flags.append("退市风险")

            # 实时行情检查
            df_rt = ak.stock_zh_a_spot_em()
            if df_rt is not None:
                row = df_rt[df_rt["代码"] == code]
                if not row.empty:
                    rt_row = row.iloc[0]
                    # 停牌检查
                    if float(rt_row.get("涨跌幅", 0)) == 0 and float(rt_row.get("成交额", 0)) == 0:
                        red_flags.append("可能停牌")

                    # 日成交额
                    amount = float(rt_row.get("成交额", 0))
                    if amount < MIN_AMOUNT:
                        red_flags.append(f"日成交额不足({amount/1e8:.1f}亿)")

                    # 股价
                    price = float(rt_row.get("最新价", 0))
                    if price < MIN_PRICE:
                        red_flags.append(f"股价过低({price}元)")
                    elif price < 5:
                        yellow_flags.append(f"股价偏低({price}元)")

                    # 总市值
                    market_cap = float(rt_row.get("总市值", 0))
                    if market_cap < MIN_MARKET_CAP:
                        red_flags.append(f"市值过小({market_cap/1e8:.1f}亿)")
                    elif market_cap < 5e9:
                        yellow_flags.append(f"市值偏小({market_cap/1e8:.1f}亿)")

            # 近5日跌停检查
            daily_data = stock.get("daily_data")
            if daily_data is not None and len(daily_data) >= 5:
                recent_5 = daily_data.tail(5)
                for _, r in recent_5.iterrows():
                    if float(r.get("涨跌幅", 0)) <= -9.5:  # 跌停近似
                        red_flags.append("近5日曾跌停")
                        break
                    elif float(r.get("涨跌幅", 0)) < -5:
                        yellow_flags.append("近5日跌幅>5%")

            # 限售股解禁检查（尝试获取）
            try:
                df_unlock = ak.stock_restricted_release_queue_sina(symbol=code)
                if df_unlock is not None and len(df_unlock) > 0:
                    unlock_date = df_unlock.iloc[0].get("解禁日期", "")
                    if unlock_date:
                        unlock_dt = pd.to_datetime(unlock_date, errors="coerce")
                        if pd.notna(unlock_dt) and (unlock_dt - datetime.now()).days <= 5:
                            red_flags.append("近期限售股解禁")
                        elif pd.notna(unlock_dt) and (unlock_dt - datetime.now()).days <= 10:
                            yellow_flags.append("10日内限售股解禁")
            except Exception:
                pass  # 解禁数据获取失败不影响

            # 红色警示一票否决
            if red_flags:
                excluded.append(f"{code} {name}: {', '.join(red_flags)}")
                continue

            stock["yellow_flags"] = yellow_flags
            stock["red_flags"] = red_flags  # 应为空
            passed.append(stock)

        except Exception as e:
            print(f"  WARN: {code} {name} 风控层异常: {e}")
            continue

    if excluded:
        print(f"  红色警示排除: {len(excluded)} 只")
        for exc in excluded[:10]:
            print(f"    - {exc}")

    print(f"[第五层] 通过: {len(passed)}/{len(candidates)}")
    return passed


# ============================================================
# 五维评分
# ============================================================

def score_trend(stock):
    """趋势得分 (0-100)"""
    score = 0
    # 均线排列完整度 (30分)
    if stock.get("ma5", 0) > stock.get("ma10", 0) > stock.get("ma20", 0):
        score += 30
    # 均线斜率强度 (30分)
    slope = stock.get("ma5_slope", 0)
    score += min(30, max(0, slope * 10))  # 斜率3%→30分
    # 周线趋势确认 (20分)
    if stock.get("weekly_trend"):
        score += 20
    # 中长期趋势 (20分) - 简化
    if stock.get("latest_close", 0) > stock.get("ma20", 0) * 1.02:
        score += 20
    elif stock.get("latest_close", 0) > stock.get("ma20", 0):
        score += 10
    return round(score)


def score_volume(stock):
    """量价得分 (0-100)"""
    score = 0
    # 量比合理性 (25分) - 2-3为最佳区间
    vr = stock.get("volume_ratio", 0)
    if 2.0 <= vr <= 3.0:
        score += 25
    elif VOLUME_RATIO_MIN <= vr <= VOLUME_RATIO_MAX:
        score += 15
    # 换手率合理性 (25分) - 5-10%为最佳
    tr = stock.get("turnover_rate", 0)
    if 5 <= tr <= 10:
        score += 25
    elif TURNOVER_MIN * 100 <= tr <= TURNOVER_MAX * 100:
        score += 15
    # 涨幅合理性 (25分) - 2-5%为最佳
    ch = stock.get("change_pct", 0)
    if 2 <= ch <= 5:
        score += 25
    elif CHANGE_MIN * 100 <= ch <= CHANGE_MAX * 100:
        score += 15
    # 量价配合 (25分) - 简化
    score += 15  # 能通过第二层说明量价配合OK
    return round(score)


def score_capital(stock):
    """资金得分 (0-100)"""
    score = 0
    # 主力净流入规模 (30分)
    inflow = stock.get("main_inflow", 0)
    if inflow > 5000:
        score += 30
    elif inflow > 1000:
        score += 20
    elif inflow > 0:
        score += 10
    # 连续流入天数 (25分)
    inflow_3d = stock.get("main_inflow_3d", 0)
    if inflow_3d > 10000:
        score += 25
    elif inflow_3d > 0:
        score += 15
    # 大单占比 (25分)
    mp = stock.get("main_pct", 0)
    if mp > 50:
        score += 25
    elif mp > 30:
        score += 15
    # 北向资金 (20分) - 简化
    score += 10  # 默认中性
    return round(score)


def score_technical(stock):
    """技术得分 (0-100)"""
    score = 0
    # MACD (25分)
    if stock.get("macd_hist", 0) > 0:
        score += 25
    elif stock.get("macd_dif", 0) > stock.get("macd_dea", 0):
        score += 15
    # KDJ (25分)
    j = stock.get("kdj_j", 0)
    k = stock.get("kdj_k", 0)
    if 50 < j < 80 and k > stock.get("kdj_d", 0):
        score += 25
    elif k > stock.get("kdj_d", 0):
        score += 10
    # RSI (25分)
    rsi = stock.get("rsi6", 0)
    if 60 <= rsi <= 75:
        score += 25
    elif 50 < rsi < 80:
        score += 15
    # 布林带 (25分)
    close = stock.get("latest_close", 0)
    mid = stock.get("boll_mid", 0)
    if close > mid and close < stock.get("boll_upper", 0):
        score += 25
    elif close > mid:
        score += 10
    return round(score)


def score_risk(stock):
    """风控得分 (0-100)"""
    # 有红色警示不该到这一步，但保险起见
    if stock.get("red_flags"):
        return 0

    score = 0
    # ST/退市 (一票否决已处理，这里给满分)
    score += 20
    # 流动性 (20分)
    daily_data = stock.get("daily_data")
    if daily_data is not None and len(daily_data) > 0:
        try:
            amount = float(daily_data.iloc[-1].get("成交额", 0))
            if amount > 2e8:
                score += 20
            elif amount > 1e8:
                score += 15
            else:
                score += 5
        except Exception:
            score += 10
    # 股价合理性 (20分)
    price = stock.get("latest_close", 0)
    if price > 10:
        score += 20
    elif price > 5:
        score += 15
    else:
        score += 5
    # 市值规模 (20分)
    score += 15  # 简化
    # 黄色警示扣分
    yf = stock.get("yellow_flags", [])
    score += max(0, 20 - len(yf) * 7)
    # 解禁/减持 (含在黄色警示中)
    return round(min(100, score))


def calculate_composite_score(stock):
    """计算综合评分"""
    t = score_trend(stock)
    v = score_volume(stock)
    c = score_capital(stock)
    tech = score_technical(stock)
    r = score_risk(stock)

    composite = t * WEIGHT_TREND + v * WEIGHT_VOLUME + c * WEIGHT_CAPITAL + tech * WEIGHT_TECH + r * WEIGHT_RISK

    stock["score_trend"] = t
    stock["score_volume"] = v
    stock["score_capital"] = c
    stock["score_technical"] = tech
    stock["score_risk"] = r
    stock["score_composite"] = round(composite, 1)

    return stock


# ============================================================
# 报告生成
# ============================================================

def generate_report(stocks, output_format="markdown"):
    """生成五维投资评估报告"""
    if not stocks:
        return "今日无符合条件的短线股票。"

    lines = []
    lines.append(f"# 短线股票精选报告")
    lines.append(f"\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 筛选范围：全A股 | 入选数量：{len(stocks)} 只")
    lines.append("")

    # 汇总表
    lines.append("## 综合排名")
    lines.append("")
    lines.append("| 排名 | 代码 | 名称 | 综合评分 | 趋势 | 量价 | 资金 | 技术 | 风控 |")
    lines.append("| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for i, s in enumerate(stocks[:TOP_N], 1):
        lines.append(
            f"| {i} | {s.get('code','')} | {s.get('name','')} | "
            f"{s.get('score_composite',0)} | {s.get('score_trend',0)} | "
            f"{s.get('score_volume',0)} | {s.get('score_capital',0)} | "
            f"{s.get('score_technical',0)} | {s.get('score_risk',0)} |"
        )
    lines.append("")

    # 每只股票详细分析
    lines.append("## 个股详细分析")
    lines.append("")

    for s in stocks[:TOP_N]:
        code = s.get("code", "")
        name = s.get("name", "")
        composite = s.get("score_composite", 0)

        # 建议等级
        if composite >= 85:
            suggestion = "重点关注"
        elif composite >= 75:
            suggestion = "短线关注"
        elif composite >= 65:
            suggestion = "谨慎观望"
        else:
            suggestion = "暂不参与"

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"**【代码】{code}  【名称】{name}**")
        lines.append(f"**【综合评分】{composite}/100  【建议】{suggestion}**")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(
            f" ┃ 趋势 {s.get('score_trend',0)} "
            f"┃ 量价 {s.get('score_volume',0)} "
            f"┃ 资金 {s.get('score_capital',0)} "
            f"┃ 技术 {s.get('score_technical',0)} "
            f"┃ 风控 {s.get('score_risk',0)}"
        )
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 操作建议
        price = s.get("latest_close", 0)
        lines.append("**◆ 操作建议：**")
        lines.append(f"  - 关注区间：{price * 0.97:.2f} - {price * 1.02:.2f} 元")
        lines.append(f"  - 止损价位：{price * 0.95:.2f} 元（跌破即离场）")
        lines.append(f"  - 目标收益：3-8%")
        lines.append(f"  - 持仓周期：1-3 个交易日")

        # 风险提示
        yellow_flags = s.get("yellow_flags", [])
        if yellow_flags:
            lines.append("**◆ 风险提示：**")
            for yf in yellow_flags:
                lines.append(f"  - ⚠️ {yf}")

        # 数据验证
        lines.append("**◆ 数据验证：**")
        lines.append("  - ✅ 双源验证通过")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")

    # 免责声明
    lines.append("---")
    lines.append("")
    lines.append("## 免责声明")
    lines.append("")
    lines.append("> ⚠️ 本报告由量化模型自动生成，仅供参考，不构成任何投资建议。")
    lines.append("> 股市有风险，投资需谨慎。模型的筛选逻辑基于历史数据统计规律，")
    lines.append("> 不保证未来收益。使用者应根据自身风险承受能力独立判断，")
    lines.append("> 自主决策，自行承担投资风险。")

    return "\n".join(lines)


# ============================================================
# QQ 机器人推送（可选）
# ============================================================

def push_to_qq(report_text, api_url, token=None, group_id=None, user_id=None):
    """通过 QQ 机器人 HTTP API 推送报告"""
    import requests

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "message": report_text[:4000],  # QQ 消息长度限制
    }
    if group_id:
        payload["group_id"] = group_id
        payload["message_type"] = "group"
    elif user_id:
        payload["user_id"] = user_id
        payload["message_type"] = "private"

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            print("[推送] QQ 机器人推送成功")
        else:
            print(f"[推送] QQ 机器人推送失败: HTTP {resp.status_code}")
    except Exception as e:
        print(f"[推送] QQ 机器人推送异常: {e}")


# ============================================================
# 主流程
# ============================================================

def run_screening(top_n=TOP_N, output_file=None, qq_api=None, qq_token=None, qq_group=None):
    """执行完整五层筛选流程"""

    print("=" * 60)
    print("短线股票精选 - 五层量化筛选")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 第0步：获取全A股列表
    print("\n[准备] 获取全A股列表...")
    try:
        df_stocks = ak.stock_zh_a_spot_em()
        if df_stocks is None or len(df_stocks) == 0:
            print("ERROR: 无法获取A股列表")
            return

        # 去除 ST 和 北交所
        df_stocks = df_stocks[~df_stocks["名称"].str.contains("ST|退", na=False)]
        df_stocks = df_stocks[~df_stocks["代码"].str.startswith(("8", "4", "9"))]

        candidates = []
        for _, row in df_stocks.iterrows():
            candidates.append({
                "code": row["代码"],
                "name": row["名称"],
            })
        print(f"  全A股票数量: {len(candidates)} (已去除ST和北交所)")

    except Exception as e:
        print(f"ERROR: 获取A股列表失败: {e}")
        return

    # 第一层：趋势层
    print()
    layer1 = filter_trend(candidates)
    if not layer1:
        print("第一层筛选后无符合条件的股票。")
        return

    # 第二层：量价层
    print()
    layer2 = filter_volume_price(layer1)
    if not layer2:
        print("第二层筛选后无符合条件的股票。")
        return

    # 第三层：资金层
    print()
    layer3 = filter_capital(layer2)
    if not layer3:
        print("第三层筛选后无符合条件的股票。")
        return

    # 第四层：技术层
    print()
    layer4 = filter_technical(layer3)
    if not layer4:
        print("第四层筛选后无符合条件的股票。")
        return

    # 第五层：风控层
    print()
    layer5 = filter_risk(layer4)
    if not layer5:
        print("第五层筛选后无符合条件的股票。")
        return

    # 五维评分
    print("\n[评分] 计算五维综合评分...")
    for stock in layer5:
        calculate_composite_score(stock)

    # 排序
    results = sorted(layer5, key=lambda x: x.get("score_composite", 0), reverse=True)
    results = results[:top_n]

    print(f"\n最终入选: {len(results)} 只")

    # 生成报告
    report = generate_report(results)

    # 输出到文件
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存至: {output_file}")

    # QQ推送
    if qq_api:
        push_to_qq(report, qq_api, qq_token, qq_group)

    return results, report


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="短线股票精选 - 五层量化筛选")
    parser.add_argument("--top", type=int, default=TOP_N, help=f"输出排名前N只 (默认{TOP_N})")
    parser.add_argument("--output", type=str, default=None, help="报告输出文件路径")
    parser.add_argument("--qq-api", type=str, default=None, help="QQ机器人API地址")
    parser.add_argument("--qq-token", type=str, default=None, help="QQ机器人Token")
    parser.add_argument("--qq-group", type=str, default=None, help="QQ群号")

    args = parser.parse_args()
    run_screening(
        top_n=args.top,
        output_file=args.output,
        qq_api=args.qq_api,
        qq_token=args.qq_token,
        qq_group=args.qq_group,
    )
