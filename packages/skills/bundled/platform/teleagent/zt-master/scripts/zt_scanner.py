#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
涨停大师 - 全A股涨停概率扫描器
基于近3年3820个涨停事件回溯统计权重模型
遍览全A股，按技术面信号评分，选出最可能涨停的TOP N股票
"""
import os, sys, json, time, argparse
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

# ====== 清除代理（东财/新浪接口需直连） ======
for k in ['HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy','ALL_PROXY','all_proxy']:
    os.environ.pop(k, None)

import requests
_orig_init = requests.Session.__init__
def _patched_init(self, *a, **kw):
    _orig_init(self, *a, **kw)
    self.trust_env = False
requests.Session.__init__ = _patched_init

import akshare as ak


# ================================================================
# 评分权重体系（来源：近3年3820个涨停事件回溯统计）
# ================================================================

# 组合指标（优先匹配，命中后子指标不重复计分）
COMBO_INDICATORS = [
    # (名称, 权重, 条件函数键名列表)
    ("站上MA20+布林>0.8+突破20日新高", 10.0, ["above_ma20", "boll_above_08", "breakout_high20"]),
    ("布林>0.8+60日高位>0.7",           9.6, ["boll_above_08", "price_pos_above_07"]),
    ("60日高位>0.7+突破20日新高",        9.2, ["price_pos_above_07", "breakout_high20"]),
    ("站上MA20+DIF>0+20日站上MA20>=10天", 9.0, ["above_ma20", "dif_above_0", "above_ma20_20d_ge10"]),
    ("站上MA20+60日高位+DIF>0",          8.8, ["above_ma20", "price_pos_above_07", "dif_above_0"]),
    ("均线多头+DIF>0",                   8.5, ["ma_bullish", "dif_above_0"]),
    ("站上MA20+布林>0.8+DIF>0",         8.2, ["above_ma20", "boll_above_08", "dif_above_0"]),
    ("均线多头+20日站上MA20>=10天",      7.8, ["ma_bullish", "above_ma20_20d_ge10"]),
    ("站上MA20+突破20日新高+DIF>0",     7.5, ["above_ma20", "breakout_high20", "dif_above_0"]),
    ("站上MA20+DIF>0",                  7.2, ["above_ma20", "dif_above_0"]),
    ("站上MA20+RSI6>70",                6.8, ["above_ma20", "rsi6_above_70"]),
    ("DIF>0+突破20日新高",              6.5, ["dif_above_0", "breakout_high20"]),
    ("布林>0.8+20日站上MA20>=10天",     5.5, ["boll_above_08", "above_ma20_20d_ge10"]),
    ("DIF>0+5日均线多头>=3天",          5.2, ["dif_above_0", "ma_bullish_5d_ge3"]),
]

# 单一指标（未被组合覆盖时单独计分）
SINGLE_INDICATORS = [
    # (名称, 权重, 条件函数键名)
    ("站上MA20",          10.0, "above_ma20"),
    ("MACD金叉(前3日)",   9.5,  "macd_golden_3d"),
    ("均线多头排列",       9.2,  "ma_bullish"),
    ("布林>0.8",          8.8,  "boll_above_08"),
    ("60日高位>0.7",      8.5,  "price_pos_above_07"),
    ("前1日涨>3%",        7.8,  "pct_above_3"),
    ("RSI14>55",          7.2,  "rsi14_above_55"),
    ("突破20日新高(前5日)", 6.8, "breakout_high20"),
    ("DIF>0",             6.5,  "dif_above_0"),
    ("20日站上MA20>=10天", 6.2,  "above_ma20_20d_ge10"),
    ("RSI6>70",           5.8,  "rsi6_above_70"),
    ("5日均线多头>=3天",   5.5,  "ma_bullish_5d_ge3"),
    ("MACD底背离(前20日)", 4.8, "macd_bottom_div_20d"),
    ("60日回撤>30%",      4.5,  "max_drawdown_30"),
    ("MACD金叉(前5日)",   4.2,  "macd_golden_5d"),
    ("量比>1.5(前1日)",   4.0,  "vol_ratio_above_15"),
    ("60日低位<0.3",      3.8,  "price_pos_below_03"),
    ("10日缩量>=3天",     3.5,  "vol_shrink_10d_ge3"),
]


# ================================================================
# 技术指标计算
# ================================================================

def calc_indicators(df):
    """计算全部技术指标，返回DataFrame"""
    df = df.copy()
    c = df['close'].values.astype(float)
    h = df['high'].values.astype(float)
    l = df['low'].values.astype(float)
    v = df['volume'].values.astype(float)
    n = len(c)
    
    # 涨跌幅
    df['pct'] = df['close'].pct_change() * 100
    
    # 均线
    for p in [5, 10, 20, 60]:
        df[f'ma{p}'] = df['close'].rolling(p).mean()
    
    # 均量
    for p in [5, 10, 20]:
        df[f'vma{p}'] = df['volume'].rolling(p).mean()
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['dif'] = ema12 - ema26
    df['dea'] = df['dif'].ewm(span=9, adjust=False).mean()
    df['macd'] = (df['dif'] - df['dea']) * 2
    
    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    for period in [6, 14]:
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df[f'rsi{period}'] = 100 - (100 / (1 + rs))
    
    # 布林带
    df['boll_mid'] = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['boll_up'] = df['boll_mid'] + 2 * std20
    df['boll_down'] = df['boll_mid'] - 2 * std20
    boll_range = df['boll_up'] - df['boll_down']
    df['boll_pct'] = (df['close'] - df['boll_down']) / boll_range.replace(0, np.nan)
    
    # 量比
    df['vol_ratio_ma5'] = v / df['vma5'].replace(0, np.nan)
    
    # 均线排列
    df['ma_bullish'] = (
        (df['ma5'] > df['ma10']) & 
        (df['ma10'] > df['ma20']) & 
        (df['ma20'] > df['ma60'])
    ).astype(int)
    
    df['above_ma20'] = (df['close'] > df['ma20']).astype(int)
    
    # MACD金叉
    df['macd_golden'] = ((df['dif'] > df['dea']) & (df['dif'].shift(1) <= df['dea'].shift(1))).astype(int)
    
    # 20日最高价
    df['high20'] = df['high'].rolling(20).max().shift(1)
    df['breakout_high20'] = (df['close'] > df['high20']).astype(int)
    
    # 60日价格位置
    df['low60'] = df['low'].rolling(60).min()
    df['high60'] = df['high'].rolling(60).max()
    df['price_position_60d'] = (df['close'] - df['low60']) / (df['high60'] - df['low60']).replace(0, np.nan)
    
    # 60日最大回撤
    cummax = df['close'].cummax()
    df['max_drawdown_60d'] = ((cummax - df['close']) / cummax * 100)
    
    # MACD底背离（简化：近20日价格新低但DIF未新低）
    df['macd_bottom_div'] = 0
    for i in range(60, n):
        price_recent_low = min(c[max(0,i-20):i+1])
        price_older_low = min(c[max(0,i-60):max(0,i-20+1)])
        dif_recent_low = min(df['dif'].values[max(0,i-20):i+1])
        dif_older_low = min(df['dif'].values[max(0,i-60):max(0,i-20+1)])
        if price_recent_low < price_older_low and dif_recent_low > dif_older_low:
            df.iloc[i, df.columns.get_loc('macd_bottom_div')] = 1
    
    # 5日均线多头天数
    df['ma_bullish_5d_cnt'] = df['ma_bullish'].rolling(5).sum()
    
    # 20日站上MA20天数
    df['above_ma20_20d_cnt'] = df['above_ma20'].rolling(20).sum()
    
    # 10日缩量天数
    df['vol_shrink_10d'] = (df['vol_ratio_ma5'] < 0.7).rolling(10).sum()
    
    return df


# ================================================================
# 信号判定（对最新一个交易日）
# ================================================================

def evaluate_signals(df, code):
    """评估最新交易日的全部信号，返回 dict {信号键名: bool}"""
    if len(df) < 70:
        return None, 0.0, {}
    
    row = df.iloc[-1]
    prev3 = df.iloc[-4:-1] if len(df) >= 4 else df
    prev5 = df.iloc[-6:-1] if len(df) >= 6 else df
    prev20 = df.iloc[-21:-1] if len(df) >= 21 else df
    
    signals = {}
    
    # --- 站上MA20 ---
    signals['above_ma20'] = bool(row.get('above_ma20', 0) == 1)
    
    # --- MACD金叉(前3日) ---
    signals['macd_golden_3d'] = bool(prev3.get('macd_golden', 0).max() > 0) if 'macd_golden' in prev3.columns else False
    
    # --- 均线多头排列 ---
    signals['ma_bullish'] = bool(row.get('ma_bullish', 0) == 1)
    
    # --- 布林>0.8 ---
    signals['boll_above_08'] = bool(row.get('boll_pct', 0) > 0.8)
    
    # --- 60日高位>0.7 ---
    signals['price_pos_above_07'] = bool(row.get('price_position_60d', 0) > 0.7)
    
    # --- 前1日涨>3% ---
    signals['pct_above_3'] = bool(row.get('pct', 0) > 3)
    
    # --- RSI14>55 ---
    signals['rsi14_above_55'] = bool(row.get('rsi14', 0) > 55)
    
    # --- 突破20日新高(前5日) ---
    signals['breakout_high20'] = bool(prev5.get('breakout_high20', 0).max() > 0) if 'breakout_high20' in prev5.columns else False
    
    # --- DIF>0 ---
    signals['dif_above_0'] = bool(row.get('dif', 0) > 0)
    
    # --- 20日站上MA20>=10天 ---
    signals['above_ma20_20d_ge10'] = bool(row.get('above_ma20_20d_cnt', 0) >= 10)
    
    # --- RSI6>70 ---
    signals['rsi6_above_70'] = bool(row.get('rsi6', 0) > 70)
    
    # --- 5日均线多头>=3天 ---
    signals['ma_bullish_5d_ge3'] = bool(row.get('ma_bullish_5d_cnt', 0) >= 3)
    
    # --- MACD底背离(前20日) ---
    signals['macd_bottom_div_20d'] = bool(prev20.get('macd_bottom_div', 0).max() > 0) if 'macd_bottom_div' in prev20.columns else False
    
    # --- 60日回撤>30% ---
    signals['max_drawdown_30'] = bool(row.get('max_drawdown_60d', 0) > 30)
    
    # --- MACD金叉(前5日) ---
    signals['macd_golden_5d'] = bool(prev5.get('macd_golden', 0).max() > 0) if 'macd_golden' in prev5.columns else False
    
    # --- 量比>1.5(前1日) ---
    signals['vol_ratio_above_15'] = bool(row.get('vol_ratio_ma5', 0) > 1.5)
    
    # --- 60日低位<0.3 ---
    signals['price_pos_below_03'] = bool(row.get('price_position_60d', 1) < 0.3)
    
    # --- 10日缩量>=3天 ---
    signals['vol_shrink_10d_ge3'] = bool(row.get('vol_shrink_10d', 0) >= 3)
    
    # ====== 评分 ======
    score = 0.0
    used_keys = set()
    hit_items = []  # (指标名, 权重)
    
    # 1. 优先匹配组合指标
    for combo_name, weight, keys in COMBO_INDICATORS:
        if all(signals.get(k, False) for k in keys):
            score += weight
            hit_items.append((combo_name, weight))
            used_keys.update(keys)
    
    # 2. 未被组合覆盖的子指标单独计分
    for name, weight, key in SINGLE_INDICATORS:
        if key in used_keys:
            continue
        if signals.get(key, False):
            score += weight
            hit_items.append((name, weight))
    
    return signals, score, hit_items


# ================================================================
# 数据获取
# ================================================================

def get_stock_list():
    """获取全A股列表"""
    print("获取全A股列表...")
    df = ak.stock_zh_a_spot()
    codes = df['代码'].tolist()
    names = df['名称'].tolist()
    code_name = dict(zip(codes, names))
    
    # 过滤北交所和ST
    filtered = {}
    for c in codes:
        if c.startswith('bj'):
            continue
        nm = code_name.get(c, '')
        if 'ST' in nm or '*ST' in nm:
            continue
        filtered[c] = nm
    
    print(f"沪深非ST股票: {len(filtered)}")
    return filtered


def fetch_kline(code, retries=3):
    """获取日K线（新浪源）"""
    for attempt in range(retries):
        try:
            df = ak.stock_zh_a_daily(symbol=code, start_date='20260101', end_date='20991231')
            if df is not None and len(df) > 70:
                return df
        except:
            pass
        time.sleep(0.3)
    return None


# ================================================================
# 主扫描流程
# ================================================================

def main():
    parser = argparse.ArgumentParser(description='涨停大师 - 全A股涨停概率扫描')
    parser.add_argument('--top', type=int, default=5, help='输出TOP N（默认5）')
    parser.add_argument('--max-stocks', type=int, default=0, help='最大扫描股票数（0=全部）')
    args = parser.parse_args()
    
    stock_list = get_stock_list()
    items = list(stock_list.items())
    
    if args.max_stocks > 0:
        items = items[:args.max_stocks]
    
    total = len(items)
    results = []
    success = 0
    fail = 0
    
    print(f"\n开始扫描 {total} 只股票...")
    
    for i, (code, name) in enumerate(items):
        if (i + 1) % 100 == 0:
            print(f"  进度: {i+1}/{total}, 已评分: {success}, 失败: {fail}")
        
        df = fetch_kline(code)
        if df is None:
            fail += 1
            continue
        
        try:
            df = calc_indicators(df)
            signals, score, hit_items = evaluate_signals(df, code)
            
            if signals is None:
                fail += 1
                continue
            
            # 获取最新行情数据
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
            
            result = {
                'code': code,
                'name': name,
                'score': float(score),
                'latest_close': float(latest['close']),
                'latest_pct': float(latest.get('pct', 0)),
                'rsi6': float(latest.get('rsi6', 0)),
                'rsi14': float(latest.get('rsi14', 0)),
                'dif': float(latest.get('dif', 0)),
                'boll_pct': float(latest.get('boll_pct', 0)),
                'price_position_60d': float(latest.get('price_position_60d', 0)),
                'vol_ratio': float(latest.get('vol_ratio_ma5', 0)),
                'hit_items': hit_items,
            }
            results.append(result)
            success += 1
        except Exception as e:
            fail += 1
        
        time.sleep(0.15)
    
    # 排序输出
    results.sort(key=lambda x: -x['score'])
    top_n = results[:args.top]
    
    # 统计
    stats = {
        'total_scanned': total,
        'success': success,
        'fail': fail,
        'combo_hit_counts': {},
    }
    
    # 统计各组合指标命中数
    for combo_name, weight, keys in COMBO_INDICATORS:
        cnt = 0
        for r in results:
            signals = {}
            # 简化：从hit_items中检查
            for item_name, _ in r['hit_items']:
                if item_name == combo_name:
                    cnt += 1
                    break
        stats['combo_hit_counts'][combo_name] = cnt
    
    # 零分股票数
    stats['zero_score_count'] = sum(1 for r in results if r['score'] <= 0)
    
    # 输出JSON
    output = {
        'scan_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'top_n': top_n,
        'stats': stats,
    }
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'scan_result.json')
    output_path = os.path.abspath(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 控制台摘要
    print(f"\n{'='*60}")
    print(f"涨停大师扫描完成")
    print(f"{'='*60}")
    print(f"扫描: {total} | 成功: {success} | 失败: {fail}")
    print(f"零分股票: {stats['zero_score_count']}")
    print(f"\nTOP {args.top} 涨停概率排名：")
    
    for i, r in enumerate(top_n):
        print(f"\n  #{i+1} {r['name']}({r['code']}) — 评分 {r['score']:.1f}")
        print(f"       收盘: {r['latest_close']:.2f}  涨跌: {r['latest_pct']:.2f}%")
        print(f"       命中: {' + '.join([f'{n}({w})' for n,w in r['hit_items'][:5]])}")
        if len(r['hit_items']) > 5:
            print(f"       ...等{len(r['hit_items'])}项")
    
    print(f"\n详细结果: {output_path}")


if __name__ == '__main__':
    main()
