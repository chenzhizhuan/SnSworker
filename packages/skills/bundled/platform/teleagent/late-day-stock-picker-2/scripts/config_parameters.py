#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 参数集中配置（2026.9.9 新增）

将所有可调阈值集中于此，与 screener_v4.py 解耦，便于 audit_overfit.py 做网格敏感性扫描。
调参纪律：修改前先备份 + 跑 audit_overfit 审计；禁止凭几天行情频繁微调（避免过拟合）。

用法：
    from config_parameters import PARAMS, SCAN_RANGES
"""

# ============ 1. 大盘环境 ============
MARKET = {
    'sh_drop_limit': -1.5,        # 上证当日涨跌幅低于该值视为偏弱
    'ratio_ok_min': 0.8,          # 涨跌家数比 >= 该值视为正常
    'consecutive_decline_days': 2,  # 近3完成交易日连续N日下跌 → 判定大盘弱
    'sh_kline_datalen': 5,        # 获取上证K线长度（用于检测连续下跌）
}

# ============ 2. 情绪维度（2026.9.9新增） ============
SENTIMENT = {
    'limit_up_pct': 9.8,          # 收盘涨幅 >= 该值视为涨停（主板10%近似）
    'limit_down_pct': -9.8,       # 收盘涨幅 <= 该值视为跌停
    'boom_touch_pct': 9.8,        # 盘中最高涨幅 >= 该值视为曾触及涨停（炸板判定）
}

# ============ 3. 本地硬性过滤（STAGE 2） ============
HARD_FILTER = {
    'price_min': 3.0,             # 最低价
    'price_max': 105.0,           # 最高价
    'amplitude_max': 15.0,        # 振幅上限%
    'drop_min': -7.0,             # 跌幅下限%（低于该跌幅剔除）
    'init_gain_min': 1.0,         # 初筛涨幅下限 %
    'init_gain_max': 6.0,         # 初筛涨幅上限 %
    'yiziban_min_gain': 9.0,      # 一字板判定涨幅（open==price 且 high==low 且 |chg|>=9）
}

# ============ 4. 稳健版筛选 + 强制避雷（STAGE 4） ============
PROFILE = {
    'gain_min': 1.8,              # 涨幅下限 %
    'gain_max': 5.2,              # 涨幅上限 %
    'volume_ratio_min': 1.9,      # 量比下限
    'volume_ratio_max': 4.2,      # 量比上限
    'turnover_min': 4.2,          # 换手下限 %
    'turnover_max': 10.5,         # 换手上限 %
    'amplitude_max': 13.0,        # 振幅上限 %
    'price_ge_avg': True,         # 现价 >= 均价
}

RISK_EXCLUDE = {
    'volume_ratio_max': 6.8,      # 量比 > 6.8 剔除（强制避雷）
    'turnover_max': 17.5,         # 换手 > 17.5% 剔除
}

LIQUIDITY = {
    'amount_min': 2.0e8,          # 【2026.9.9新增】流动性下限：成交额≥2亿(元)，防小票滑点/操纵
    'skip_if_missing': True,      # 缺成交额数据时不误伤
}

# ============ 5. K线形态过滤（STAGE 4.5） ============
FORM = {
    'shadow_ratio': 0.8,          # 上影线 <= 实体 × 0.8（2026.7.10收严）
    'close_high_ratio': 0.95,     # 收盘 >= 最高价 × 95%
    'body_ratio_min': 0.4,        # 实体占比 >= 40%
    'pass_min': 2,                # 3项满足2项即通过
}

# ============ 6. K线深度验证（STAGE 5） ============
DEEP = {
    'kline_datalen': 65,          # 深度K线天数（2026.9.9起优先腾讯前复权）
    'vol_mult_pass': 1.28,        # 5日均量倍数达标线
    'dist_high_exclude': -30.0,   # 距60日高点 < -30% 直接排除（深度下降趋势）
    'pulse_gain_ratio': 0.60,     # 脉冲双因子：收益率 < 0.60
    'pulse_shadow_body': 0.50,    # 脉冲双因子：影体比 > 0.50 → 直接排除
    'atr_period': 14,             # 【2026.9.9新增】ATR周期
}

# ============ 7. 评分体系 ============
SCORING = {
    'tier1_min': 70,              # 一档
    'tier2_min': 50,              # 二档
    'ma_pass_cap': 69,            # 均线未多头时锁定二档上限（不得进一档）

    # 加分项
    'score_ma_pass': 20,          # 均线多头
    'score_vol_high': 20,         # 量倍 >= 1.28
    'score_vol_mid': 10,          # 量倍 >= 1.0
    'score_consec_1': 15,         # 连涨 <=1天
    'score_consec_2': 10,         # 连涨 <=2天
    'score_consec_3': 5,          # 连涨 <=3天
    'score_cum_8': 15,            # 5日累计 <=8%
    'score_cum_12': 10,           # 5日累计 <=12%
    'score_cum_15': 5,            # 5日累计 <=15%
    'score_dist_low_15': 10,      # 距20日低点 <=15%
    'score_dist_low_25': 5,       # 距20日低点 <=25%
    'score_dist_high': 5,         # 距60日高点 <= -5%
    'score_form_3': 10,           # K线形态3/3
    'score_form_2': 5,            # K线形态2/3
    'score_market_ok': 5,         # 大盘OK(涨跌幅+涨跌比)
    'score_market_mid': 3,        # 大盘一般(仅涨跌幅OK)
    'score_ma20_slope': 5,        # MA20上翘（额外）
}

# ============ 8. 扣分项 ============
PENALTY = {
    'prev_gain_7': 7.0,           # 前日涨幅 > 7% 扣10分
    'prev_gain_7_score': 10,
    'prev_gain_5': 5.0,           # 前日涨幅 > 5% 扣5分
    'prev_gain_5_score': 5,
    'ma_dev_2': 2.0,              # MA5/MA10偏离度 <2% 不扣（粘合）
    'ma_dev_5': 5.0,              # 偏离度 2-5% 扣5分
    'ma_dev_5_score': 5,
    'ma_dev_gt5_score': 10,       # 偏离度 >5% 扣10分
    'vol_mult_penalty': 1.0,      # 5日均量倍数 <1.0 扣5分
    'vol_mult_penalty_score': 5,
    'stagnant_volume_ratio': 2.0, # 放量滞涨：量比 >= 2.0
    'stagnant_gain_ratio': 0.6,   # 收盘涨幅 < 盘中最大涨幅×60% 扣5分
    'stagnant_gain_score': 5,
    'stagnant_shadow_ratio': 0.5, # 上影线/实体 > 0.5 扣5分
    'stagnant_shadow_score': 5,
}

# ============ 9. 情绪维度阈值（2026.9.9） ============
EMOTION = {
    'limit_up_pct': 9.8,
    'limit_down_pct': -9.8,
    'boom_touch_pct': 9.8,
    'boom_rate_warn': 0.5,        # 炸板率 >= 50% 提示情绪偏弱
}

# ============ 10. ETF筛选 ============
ETF = {
    'gain_min': 0.5,              # 涨幅 > 0.5%
    'volume_ratio_min': 1.0,      # 量比 > 1.0
    'top_n': 8,                   # 输出前N只
}

# ============ 11. 交易成本口径（与 trading_cost.py 保持一致） ============
COST = {
    'commission_rate': 2.5e-4,    # 佣金 万2.5（单边）
    'stamp_tax': 5e-4,            # 印花税 0.05%（卖出单边，2023.8后）
    'slippage': 1e-3,             # 滑点 0.1%（单边）
    'round_trip_total': 0.003,    # 往返总成本约 0.30%
}

# ============ 12. 敏感性扫描范围（网格，供 audit_overfit.py） ============
SCAN_RANGES = {
    'gain_min': [1.5, 1.8, 2.1, 2.4],
    'gain_max': [4.5, 5.2, 5.8],
    'volume_ratio_min': [1.2, 1.5, 1.9, 2.3],
    'volume_ratio_max': [3.2, 3.8, 4.2, 5.0],
    'turnover_min': [3.0, 3.6, 4.2, 5.0],
    'turnover_max': [8.5, 9.5, 10.5, 12.0],
    'amplitude_max': [11.0, 13.0, 15.0],
    'score_thresholds': [60, 65, 68, 70, 73, 76, 80],
    'vol_mult_pass': [1.1, 1.28, 1.4],
    'dist_high_exclude': [-25.0, -30.0, -35.0],
}

# 汇总视图（便于脚本统一引用）
PARAMS = {
    'MARKET': MARKET,
    'SENTIMENT': SENTIMENT,
    'HARD_FILTER': HARD_FILTER,
    'PROFILE': PROFILE,
    'RISK_EXCLUDE': RISK_EXCLUDE,
    'LIQUIDITY': LIQUIDITY,
    'FORM': FORM,
    'DEEP': DEEP,
    'SCORING': SCORING,
    'PENALTY': PENALTY,
    'EMOTION': EMOTION,
    'ETF': ETF,
    'COST': COST,
}


def dump_params():
    """打印全部参数（便于调参前留档）"""
    import json
    print(json.dumps(PARAMS, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    dump_params()