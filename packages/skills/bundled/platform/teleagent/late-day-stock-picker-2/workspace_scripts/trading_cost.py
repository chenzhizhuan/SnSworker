#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
尾盘选股 交易成本模型（2026.9.9 新增）

A股交易往返成本模型：
  佣金    万2.5（单边，双向收取）
  印花税  0.05%（卖出单边，2023年8月28日起下调）
  滑点    0.1%（单边，估算：买入价+卖出回撤）
  往返总成本 ≈ 0.30%

用途：
   - 将名义收益换算为净收益（verify_v4 净收益列、review_v4 成本提示）
   - 评估策略在真实成本下的盈亏平衡点

用法：
    python trading_cost.py            # 打印明细模型
    from trading_cost import net_return, round_trip_cost, breakeven_gain
"""

# ============ 成本参数（与 config_parameters.py 的 COST 一致） ============
COMMISSION_RATE = 2.5e-4   # 佣金 万2.5，单边
STAMP_TAX = 5e-4           # 印花税 0.05%，卖出单边
SLIPPAGE = 1e-3            # 滑点 0.1%，单边


def _fmt_pct(v):
    """小数 → 百分比字符串（保留3位）"""
    return f'{v * 100:.3f}%'


def buy_cost_rate():
    """买入单边成本率（佣金+滑点）"""
    return COMMISSION_RATE + SLIPPAGE


def sell_cost_rate():
    """卖出单边成本率（佣金+印花税+滑点）"""
    return COMMISSION_RATE + STAMP_TAX + SLIPPAGE


def round_trip_cost():
    """往返总成本率"""
    return buy_cost_rate() + sell_cost_rate()


def net_return(nominal_pct):
    """
    名义收益率 → 净收益率（扣往返成本）
    :param nominal_pct: 名义收益率（%，如 +2.0 表示 +2%）
    :return: 净收益率（%）
    """
    return nominal_pct - round_trip_cost() * 100


def breakeven_gain():
    """净收益为零所需的名义涨幅（%）"""
    return round_trip_cost() * 100


def main():
    print('=' * 60)
    print('  尾盘选股 交易成本模型（2026.9.9）')
    print('=' * 60)
    print('\n【参数】')
    print(f'  佣金     : {_fmt_pct(COMMISSION_RATE)}（单边双向）')
    print(f'  印花税   : {_fmt_pct(STAMP_TAX)}（卖出单边）')
    print(f'  滑点     : {_fmt_pct(SLIPPAGE)}（单边双向）')
    print('\n【单边成本】')
    print(f'  买入单边 : {_fmt_pct(buy_cost_rate())}（佣金+滑点）')
    print(f'  卖出单边 : {_fmt_pct(sell_cost_rate())}（佣金+印花税+滑点）')
    print(f'  往返总成本: {_fmt_pct(round_trip_cost())}')
    print(f'  盈亏平衡点: 名义涨幅需 >= {breakeven_gain():.3f}%')
    print('\n【名义 vs 净收益对照】')
    print(f'  {"名义":>8}  {"净收益":>8}')
    for nominal in (-3, -2, -1, 0, 1, 2, 3, 4, 5, 8):
        net = net_return(nominal)
        print(f'  {nominal:+6.1f}%  {net:+7.2f}%')
    print('\n【结论】')
    print('  平均盈利 +1% 量级时，扣除往返成本 0.30% 后净值显著低于名义，')
    print('  策略评估必须使用净收益口径（verify_v4 净收益列 / review_v4 成本提示）。')


if __name__ == '__main__':
    main()