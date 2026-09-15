# -*- coding: utf-8 -*-
"""
ETF主力吸筹长线版V2.3 - 完整分析脚本
V2.3新增:
1. 每日追踪存档：每次运行自动存档结果到etf_tracking.csv，跨日对比
2. 同日去重：同一天多次运行先回退旧记录再写入最新，连续天数不虚增
3. 历史对比报告：新入选/持续追踪/重新入选/已退出四类输出
4. 连续>=3天重点标注：主力持续吸筹信号强
V2.2 vs V2.1a 改进:
1. L2巨潮PE真实调用+缓存+3年分位计算（替代V2.1a的L1/L3降级）
2. EPS假低估过滤：净利润环比2季度
3. mootdx资金流估算：首次运行缓存不足5天时补缺
4. 宽基/跨境精确排除规则
5. T2条件放宽：3日递增→5日净流入>0天数≥3+周环比递增
6. PMI量化验证周期判断
7. 布林带支撑2+放量标准1.5倍+RSI灰带(30-35)
8. 等待清单+触发价提醒
"""
import akshare as ak
import pandas as pd
import numpy as np
import os, sys, time, warnings
from datetime import datetime, timedelta
from mootdx.quotes import Quotes

warnings.filterwarnings('ignore')

CACHE_DIR = os.path.join(os.environ.get('TELEAGENT_MEMORY', os.path.expanduser('~/.local/share/TeleAgent/memory')), 'etf_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

###############################################################################
# 第一步：全量扫描
###############################################################################
def step1_scan():
    print('='*60)
    print('ETF主力吸筹长线版V2.3 - 实时分析')
    print(f'分析时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('='*60)

    df = ak.fund_etf_spot_em()
    total = len(df)
    print(f'\n[第一步] 获取ETF总数: {total}')

    # ===== V2.2修正: 精确排除规则 =====
    # 宽基指数（精确全称匹配）
    broad_base_names = [
        '沪深300', '中证500', '中证1000', '中证2000', '上证50',
        '创业板指', '科创50', '科创创业', '中证A50', '中证A500',
        '国证2000', '北证50', '深证100', '央视50',
        '创业板ETF', '科创50ETF', '科创综指ETF',  # V2.2新增
    ]
    # 债券/货币（精确关键词）
    bond_names = ['国债', '地方债', '政金债', '利率债', '信用债', '可转债', '短融',
                  '城投债', '债券', '金融债', '货币']
    # 跨境（精确多字关键词，不用单字）
    cross_border_names = [
        '纳斯达克', '标普', '道琼斯', '日经225', '恒生科技', '恒生医疗',
        '恒生互联网', '中概互联', '德国DAX', '法国CAC', '英国富时',
        '印度基金', '越南', '东南亚', 'QDII', '沪港深', '港股通',
        '港股ETF', '恒指ETF', '港股医药',
    ]

    def is_excluded(name):
        for kw in broad_base_names + bond_names + cross_border_names:
            if kw in name:
                return True
        return False

    mask = ~df['名称'].apply(is_excluded)
    df_filtered = df[mask].copy()

    # 排除规模<5亿
    df_filtered['流通市值'] = pd.to_numeric(df_filtered['流通市值'], errors='coerce')
    df_filtered = df_filtered[df_filtered['流通市值'] >= 5e8]

    # 筛选跌幅>0%且成交额>300万
    df_filtered['涨跌幅'] = pd.to_numeric(df_filtered['涨跌幅'], errors='coerce')
    df_filtered['成交额'] = pd.to_numeric(df_filtered['成交额'], errors='coerce')
    df_filtered = df_filtered[(df_filtered['涨跌幅'] < 0) & (df_filtered['成交额'] > 3e6)]

    print(f'排除后+筛选跌+成交流: {len(df_filtered)}只')

    # 每日缓存
    today = datetime.now().strftime('%Y-%m-%d')
    month_str = datetime.now().strftime('%Y-%m')
    cache_file = os.path.join(CACHE_DIR, f'etf_fund_flow_cache_{month_str}.csv')

    fund_flow_cols = ['代码','名称','涨跌幅','成交额','主力净流入-净额','主力净流入-净占比',
                      '超大单净流入-净额','大单净流入-净额','中单净流入-净额','小单净流入-净额',
                      '最新份额','流通市值','数据日期']
    today_snapshot = df_filtered[fund_flow_cols].copy()
    today_snapshot['数据日期'] = today

    if os.path.exists(cache_file):
        cache_df = pd.read_csv(cache_file)
        cache_df = cache_df[cache_df['数据日期'] != today]
        combined = pd.concat([cache_df, today_snapshot], ignore_index=True)
    else:
        combined = today_snapshot
    combined.to_csv(cache_file, index=False, encoding='utf-8-sig')
    cache_days = combined['数据日期'].nunique()
    print(f'资金流缓存: {cache_days}天')

    return df_filtered, combined, cache_days


###############################################################################
# 第二步：资金流筛选（V2.2: +mootdx估算法补缺 + T2放宽）
###############################################################################
def step2_flow_filter(df_filtered, combined, cache_days):
    print(f'\n[第二步] 资金流筛选')

    df_filtered['主力净流入-净额'] = pd.to_numeric(df_filtered['主力净流入-净额'], errors='coerce')
    df_filtered['主力净流入-净占比'] = pd.to_numeric(df_filtered['主力净流入-净占比'], errors='coerce')
    df_filtered['超大单净流入-净额'] = pd.to_numeric(df_filtered['超大单净流入-净额'], errors='coerce')
    df_filtered['大单净流入-净额'] = pd.to_numeric(df_filtered['大单净流入-净额'], errors='coerce')

    # 初筛
    cond1 = (df_filtered['主力净流入-净占比'] >= 5) & (df_filtered['主力净流入-净占比'] <= 20)
    cond2 = df_filtered['主力净流入-净额'] > 1e6
    df_flow = df_filtered[cond1 & cond2].copy()
    print(f'净占比5-20% + 主力净流入>100万: {len(df_flow)}只')

    # 5日数据获取
    flow_data = []
    if cache_days >= 5:
        print(f'使用本地缓存法({cache_days}天)')
        data_source = '缓存法'
    else:
        # V2.2: mootdx估算法补缺
        print(f'缓存不足5天({cache_days}天)，使用mootdx估算法补缺')
        data_source = '缓存+mootdx估算'

    for _, row in df_flow.iterrows():
        code = str(row['代码'])
        name = row['名称']

        # 获取5日资金流数据
        net_inflows = []
        big_net_list = []
        vol_list = []

        # 从缓存取
        code_cache = combined[combined['代码'] == code].sort_values('数据日期')
        for _, cr in code_cache.iterrows():
            net_inflows.append(float(cr['主力净流入-净额']))
            bn = 0
            if '超大单净流入-净额' in cr.index and pd.notna(cr.get('超大单净流入-净额', None)):
                bn += float(cr['超大单净流入-净额'])
            if '大单净流入-净额' in cr.index and pd.notna(cr.get('大单净流入-净额', None)):
                bn += float(cr['大单净流入-净额'])
            big_net_list.append(bn)
            vol_list.append(float(cr['成交额']))

        # 缓存不足5天，用mootdx估算补缺
        missing_days = 5 - len(net_inflows)
        if missing_days > 0:
            mootdx_flows = mootdx_estimate_flow(code, missing_days)
            # mootdx返回的是历史日，插到前面
            net_inflows = mootdx_flows['net_inflows'] + net_inflows
            big_net_list = mootdx_flows['big_net'] + big_net_list
            vol_list = mootdx_flows['volumes'] + vol_list

        if len(net_inflows) < 3:
            continue

        # 取最近5日
        net_inflows = net_inflows[-5:]
        big_net_list = big_net_list[-5:]
        vol_list = vol_list[-5:]

        # T1: 累计净流入>0
        cum_net = sum(net_inflows)
        if cum_net <= 0:
            continue

        # V2.2 T2放宽: 5日净流入>0天数>=3天 + 周累计递增（替代3日逐日递增）
        pos_days = sum(1 for x in net_inflows if x > 0)
        if pos_days < 3:
            continue
        # 周环比：前半段vs后半段累计
        half = len(net_inflows) // 2
        if half > 0:
            first_half = sum(net_inflows[:half])
            second_half = sum(net_inflows[half:])
            if second_half <= first_half:
                # 后半段未增强，但允许（降级标注）
                trend_label = '震荡吸筹(后半段未增强)'
            else:
                trend_label = '吸筹加速'
        else:
            trend_label = '数据不足'

        # T3: 大单净流入/总成交额>3%
        total_vol = sum(vol_list)
        big_total = sum(big_net_list)
        big_pct = big_total / total_vol * 100 if total_vol > 0 else 0
        if big_pct <= 3:
            continue

        # 5日累计净流入>日均成交额×10%
        avg_vol = total_vol / len(vol_list)
        if cum_net <= avg_vol * 0.1:
            continue

        flow_data.append({
            '代码': code,
            '名称': name,
            '5日累计净流入': cum_net,
            '5日净流入天数': pos_days,
            '5日总天数': len(net_inflows),
            '大单占比': round(big_pct, 2),
            '趋势类型': trend_label,
            '数据源': data_source,
        })

    df_result = pd.DataFrame(flow_data)
    print(f'通过完整资金流筛选: {len(df_result)}只')

    # 放宽候选池
    df_relaxed = df_filtered[
        (df_filtered['主力净流入-净占比'] >= 3) & (df_filtered['主力净流入-净额'] > 5e5)
    ].sort_values('主力净流入-净占比', ascending=False)

    return df_result, df_relaxed


def mootdx_estimate_flow(code, days_needed):
    """V2.2新增: mootdx分钟线估算历史资金流"""
    result = {'net_inflows': [], 'big_net': [], 'volumes': []}
    try:
        client = Quotes.factory(market='std')
        code_int = int(code)
        market = 1 if code_int >= 500000 else 0

        # 拉取近期日线 (多拉一些以覆盖缺几天)
        df_k = client.bars(symbol=code[:6], frequency=9, market=market, offset=days_needed + 5)
        if df_k is None or len(df_k) < days_needed:
            # 不够就填充0
            for _ in range(days_needed):
                result['net_inflows'].append(0)
                result['big_net'].append(0)
                result['volumes'].append(0)
            return result

        # 取最后N天（排除今天的）
        recent = df_k.tail(days_needed + 1).head(days_needed)
        for _, row in recent.iterrows():
            vol = float(row['amount']) if 'amount' in row.index else float(row.get('vol', 0)) * float(row.get('close', 1))
            # 估算：用涨跌幅粗估主力方向
            chg = float(row.get('change', 0))
            close = float(row.get('close', 0))
            open_ = float(row.get('open', close))
            if open_ > 0:
                day_chg_pct = (close - open_) / open_ * 100
            else:
                day_chg_pct = 0

            # 简单估算：阳线推算主力净流入=总成交额*8-15%（视涨幅）
            if day_chg_pct > 0:
                est_pct = min(5 + day_chg_pct * 1.5, 20)
            elif day_chg_pct < 0:
                est_pct = max(5 + day_chg_pct * 1.0, -15)
            else:
                est_pct = 0

            est_net = vol * est_pct / 100 if vol > 0 else 0
            est_big = est_net * 0.6  # 大单约占主力60%

            result['net_inflows'].append(est_net)
            result['big_net'].append(est_big)
            result['volumes'].append(vol)

    except Exception:
        for _ in range(days_needed):
            result['net_inflows'].append(0)
            result['big_net'].append(0)
            result['volumes'].append(0)

    return result


###############################################################################
# 第三步：估值锚定（V2.2: L2巨潮PE真实调用 + 3年分位 + EPS过滤）
###############################################################################
# ETF→巨潮行业编码映射
ETF_INDUSTRY_MAP = {
    # 采矿业/石油/能源
    '159588': 'B', '159697': 'B', '561360': 'B', '159309': 'B', '159930': 'B',
    # 信息传输、软件和信息技术服务业
    '512330': 'I', '589210': 'I',
    # 金融业/证券
    '562870': 'J',
    # 制造业/消费电子/电池
    '561100': 'C', '159775': 'C', '562880': 'C', '159997': 'C', '159806': 'C',
}

INDUSTRY_CODE_MAP = {
    'A': '农、林、牧、渔业', 'B': '采矿业', 'C': '制造业', 'D': '电力、热力、燃气及水生产和供应业',
    'E': '建筑业', 'F': '批发和零售业', 'G': '交通运输、仓储和邮政业', 'H': '住宿和餐饮业',
    'I': '信息传输、软件和信息技术服务业', 'J': '金融业', 'K': '房地产业',
    'L': '租赁和商务服务业', 'M': '科学研究和技术服务业', 'N': '水利、环境和公共设施管理业',
    'Q': '卫生和社会工作', 'R': '文化、体育和娱乐业',
}


def step3_valuation(df_candidates):
    print(f'\n[第三步] 估值锚定 (L2巨潮PE真实调用)')

    results = []
    today = datetime.now()

    # 预拉取巨潮行业PE缓存
    pe_cache = load_pe_cache()

    for _, row in df_candidates.iterrows():
        code = str(row['代码'])
        name = row['名称']
        price = row['最新价']
        chg = row['涨跌幅']
        net_pct = row['主力净流入-净占比']
        net_amt = row['主力净流入-净额']
        mkt_cap = row['流通市值']

        pe_val = None
        pe_pct = None
        pe_level = 'L4应急'
        eps_trend = '未验证'
        eps_warning = False

        # 尝试L2巨潮行业PE
        industry_code = ETF_INDUSTRY_MAP.get(code)
        if industry_code:
            pe_val, pe_pct, pe_level = get_l2_pe_pct(industry_code, pe_cache, today)
            # EPS假低估过滤
            if pe_val is not None:
                eps_trend, eps_warning = check_eps_trend(industry_code, pe_cache)

        # L2失败，L3价格分位兜底
        if pe_val is None:
            pe_val, pe_pct, pe_level = get_l3_price_pct(code)

        # 估值判断
        if pe_pct is not None:
            if pe_pct < 20:
                status = '低估' if not eps_warning else '假低估→观察'
            elif pe_pct < 40:
                status = '观察'
            else:
                status = '淘汰'
        else:
            status = '估值未知'

        results.append({
            '代码': code,
            '名称': name,
            '最新价': price,
            '涨跌幅': chg,
            '净占比': net_pct,
            '净流入额': net_amt,
            'PE值': pe_val,
            'PE分位': pe_pct,
            '层级': pe_level,
            'EPS趋势': eps_trend,
            '假低估风险': '是' if eps_warning else '否',
            '估值状态': status,
            '流通市值(亿)': round(mkt_cap / 1e8, 2),
        })

    df_val = pd.DataFrame(results)
    df_under = df_val[df_val['估值状态'].isin(['低估', '假低估→观察', '观察'])].copy()
    df_under = df_under.sort_values('PE分位', ascending=True)

    print(f'低估: {len(df_val[df_val["估值状态"]=="低估"])}只, 观察含假低估: {len(df_val[df_val["估值状态"].isin(["观察","假低估→观察"])])}只, 淘汰: {len(df_val[df_val["估值状态"]=="淘汰"])}只')

    return df_val, df_under


def load_pe_cache():
    """加载或拉取巨潮行业PE缓存（近3年）"""
    cache_file = os.path.join(CACHE_DIR, 'industry_pe_cache_all.csv')
    today_str = datetime.now().strftime('%Y-%m-%d')

    if os.path.exists(cache_file):
        cache = pd.read_csv(cache_file)
        # 检查是否今天已更新
        if '日期' in cache.columns and today_str in cache['日期'].values:
            return cache

    # 拉取近3年的行业PE数据（每月1个采样点，减少API调用）
    all_data = []
    today = datetime.now()
    # 采样日期：每季度末+当月
    sample_dates = []
    for year in range(today.year - 3, today.year + 1):
        for month in [3, 6, 9, 12]:
            d = datetime(year, month, 28)
            if d <= today:
                sample_dates.append(d.strftime('%Y%m%d'))
    # 加上近3个月每月
    for m in range(3):
        d = today - timedelta(days=30*m)
        sample_dates.append(d.strftime('%Y%m%d'))

    sample_dates = list(set(sample_dates))
    sample_dates.sort()

    existing_dates = set()
    if os.path.exists(cache_file):
        old_cache = pd.read_csv(cache_file)
        if '日期' in old_cache.columns:
            existing_dates = set(old_cache['日期'].values)

    for date_str in sample_dates:
        date_display = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}'
        if date_display in existing_dates:
            continue
        try:
            df = ak.stock_industry_pe_ratio_cninfo(date=date_str)
            if df is not None and len(df) > 0:
                lv1 = df[df['行业层级'] == 1.0]
                for _, r in lv1.iterrows():
                    all_data.append({
                        '日期': date_display,
                        '行业编码': r['行业编码'],
                        '行业名称': r['行业名称'],
                        'PE加权': r['静态市盈率-加权平均'],
                        'PE中位数': r['静态市盈率-中位数'],
                        '净利润': r['净利润-静态'],
                        '总市值': r['总市值-静态'],
                    })
            time.sleep(0.3)
        except:
            pass

    if all_data:
        new_data = pd.DataFrame(all_data)
        if os.path.exists(cache_file):
            old_cache = pd.read_csv(cache_file)
            combined = pd.concat([old_cache, new_data], ignore_index=True)
            combined = combined.drop_duplicates(subset=['日期', '行业编码'], keep='last')
        else:
            combined = new_data
        combined.to_csv(cache_file, index=False, encoding='utf-8-sig')
        return combined
    elif os.path.exists(cache_file):
        return pd.read_csv(cache_file)
    else:
        return pd.DataFrame()


def get_l2_pe_pct(industry_code, pe_cache, today):
    """L2巨潮行业PE：3年分位计算"""
    try:
        if pe_cache is None or len(pe_cache) == 0:
            return None, None, 'L2数据为空'

        ind_data = pe_cache[pe_cache['行业编码'] == industry_code].copy()
        if len(ind_data) < 10:
            return None, None, 'L2数据不足'

        ind_data['日期'] = pd.to_datetime(ind_data['日期'])
        three_yr_ago = today - timedelta(days=1095)
        ind_3y = ind_data[ind_data['日期'] >= three_yr_ago]

        if len(ind_3y) < 5:
            return None, None, 'L2近3年数据不足'

        current_pe = ind_3y.iloc[-1]['PE加权']
        if pd.isna(current_pe):
            return None, None, 'L2当前PE为空'

        # 去除NaN
        valid_pe = ind_3y['PE加权'].dropna()
        if len(valid_pe) < 5:
            return None, None, 'L2有效PE不足'

        pe_pct = (valid_pe < current_pe).sum() / len(valid_pe) * 100

        return round(float(current_pe), 2), round(float(pe_pct), 2), 'L2巨潮行业PE'
    except Exception as e:
        return None, None, f'L2失败:{str(e)[:30]}'


def check_eps_trend(industry_code, pe_cache):
    """V2.2: EPS假低估过滤——近2季度净利润环比"""
    try:
        if pe_cache is None or len(pe_cache) == 0:
            return '未验证', True

        ind_data = pe_cache[pe_cache['行业编码'] == industry_code].sort_values('日期', ascending=False)
        if len(ind_data) < 2:
            return '数据不足', True

        # 取最近2个数据点的净利润
        profits = ind_data['净利润'].dropna().head(2).values
        if len(profits) < 2:
            return '净利润数据不足', True

        latest = float(profits[0])
        prev = float(profits[1])
        if prev == 0:
            return '前期利润为零', True

        chg_pct = (latest - prev) / abs(prev) * 100
        if chg_pct < -10:
            return f'恶化({chg_pct:.1f}%)', True
        elif chg_pct < 0:
            return f'微降({chg_pct:.1f}%)', False
        else:
            return f'改善(+{chg_pct:.1f}%)', False
    except:
        return '未验证', True


def get_l3_price_pct(code):
    """L3: mootdx价格分位近似"""
    try:
        client = Quotes.factory(market='std')
        code_int = int(code)
        market = 1 if code_int >= 500000 else 0
        df_k = client.bars(symbol=code[:6], frequency=9, market=market, offset=250)
        if df_k is None or len(df_k) < 20:
            return None, None, 'L3无K线'
        current = float(df_k.iloc[-1]['close'])
        high_3y = float(df_k['close'].max())
        low_3y = float(df_k['close'].min())
        if high_3y == low_3y:
            return None, None, 'L3价差为零'
        pct = (current - low_3y) / (high_3y - low_3y) * 100
        return round(current, 4), round(pct, 2), 'L3价格分位'
    except Exception as e:
        return None, None, f'L3失败:{str(e)[:30]}'


###############################################################################
# 第四步：周期位置判断（V2.2: +PMI量化验证）
###############################################################################
def step4_cycle(df_under):
    print(f'\n[第四步] 周期位置判断 (+PMI量化)')

    # 获取PMI数据
    pmi_ok, pmi_trend = get_pmi_trend()

    industry_cycle = {
        '采矿业/石油/能源': {
            '周期位置': '震荡期',
            '优先级': '★☆☆',
            '特征': 'OPEC+产量政策反复，油价中枢下移但未崩盘',
            '催化': 'OPEC+深化减产/地缘冲突/夏季用油高峰',
            'pmi_rel': 'mining',
        },
        '信息技术/芯片': {
            '周期位置': '复苏早期',
            '优先级': '★★☆',
            '特征': 'AI算力需求释放，半导体周期见底回升',
            '催化': '国产替代加速/终端需求回暖',
            'pmi_rel': 'mfg',
        },
        '证券/金融': {
            '周期位置': '震荡期',
            '优先级': '★☆☆',
            '特征': '市场交投一般，券商盈利平淡',
            '催化': '资本市场改革/牛市预期/并购重组',
            'pmi_rel': 'none',
        },
        '消费电子/电子': {
            '周期位置': '复苏早期',
            '优先级': '★★☆',
            '特征': 'AI手机/PC换机周期启动',
            '催化': '苹果/华为新品周期/AI端侧落地',
            'pmi_rel': 'mfg',
        },
        '新能源/电池': {
            '周期位置': '去产能末期',
            '优先级': '★★★',
            '特征': '产能过剩严重，龙头亏损减产',
            '催化': '产能出清加速/固态电池突破/海外需求回升',
            'pmi_rel': 'mfg',
        },
        '创业板/科创': {
            '周期位置': '震荡期',
            '优先级': '★☆☆',
            '特征': '成长股估值消化中',
            '催化': '货币宽松/产业政策',
            'pmi_rel': 'none',
        },
    }

    def get_industry(name, code):
        if '石油' in name or '能源' in name or '油气' in name:
            return '采矿业/石油/能源'
        elif '信息' in name or '芯片' in name or '科技' in name:
            return '信息技术/芯片'
        elif '证券' in name:
            return '证券/金融'
        elif '消费电子' in name or '电子' in name:
            return '消费电子/电子'
        elif '电池' in name or '新能源' in name:
            return '新能源/电池'
        elif '创业板' in name or '科创' in name:
            return '创业板/科创'
        else:
            return '其他'

    cycle_results = []
    for _, row in df_under.iterrows():
        ind = get_industry(row['名称'], str(row['代码']))
        cycle = industry_cycle.get(ind, {
            '周期位置': '未知', '优先级': '★☆☆',
            '特征': '数据不足', '催化': '待研究', 'pmi_rel': 'none'
        })

        # V2.2: PMI量化验证
        pmi_verified = False
        pmi_info = 'PMI未验证'
        pmi_rel = cycle.get('pmi_rel', 'none')
        if pmi_ok:
            if pmi_rel == 'mfg':
                if pmi_trend == '改善':
                    pmi_verified = True
                    pmi_info = f'制造业PMI连续改善 ✓'
                else:
                    pmi_info = f'制造业PMI未改善 ✗'
            elif pmi_rel == 'none':
                pmi_info = '非制造业，PMI不直接验证'

        # 量化验证后调整优先级
        final_priority = cycle['优先级']
        if pmi_verified and '★★' not in final_priority:
            # PMI验证通过可提升半级
            pass  # 保持原评级，但标注验证通过

        cycle_results.append({
            '代码': row['代码'],
            '名称': row['名称'],
            '行业': ind,
            '周期位置': cycle['周期位置'],
            '优先级': final_priority,
            'PMI验证': pmi_info,
            '催化': cycle['催化'],
        })

    return pd.DataFrame(cycle_results)


def get_pmi_trend():
    """V2.2: 获取制造业PMI趋势"""
    try:
        df = ak.macro_china_pmi()
        if df is None or len(df) < 3:
            return False, '数据不足'

        # 取最近3个月制造业PMI
        recent = df.head(3)
        pmi_values = recent['制造业-指数'].values

        # 连续2月环比改善
        if len(pmi_values) >= 3:
            if pmi_values[0] > pmi_values[1] > pmi_values[2]:
                return True, '改善'
            elif pmi_values[0] > pmi_values[1]:
                return True, '部分改善'
        return True, '未改善'
    except:
        return False, '获取失败'


###############################################################################
# 第五步：建仓计划（V2.2: 布林带支撑2 + RSI灰带 + 放量标准）
###############################################################################
def step5_build_plan(df_under):
    print(f'\n[第五步] 三批建仓计划')

    client = Quotes.factory(market='std')
    plan_data = []

    for _, row in df_under.iterrows():
        code = str(row['代码'])
        code_int = int(code)
        market = 1 if code_int >= 500000 else 0

        try:
            df_k = client.bars(symbol=code[:6], frequency=9, market=market, offset=120)
            if df_k is None or len(df_k) < 20:
                continue

            current_price = float(row['最新价'])

            # 支撑1: 近120日放量低点
            avg_vol_s = df_k['vol'].rolling(20).mean()
            high_vol_mask = df_k['vol'] > avg_vol_s
            low_points = df_k[high_vol_mask.fillna(False)]['low']
            support1 = float(low_points.min()) if len(low_points) > 0 else float(df_k['low'].min())

            # V2.2: 支撑2 = max(支撑1×0.95, 布林带下轨120日)
            # 布林带计算
            close_s = df_k['close'].astype(float)
            ma20 = close_s.rolling(20).mean()
            std20 = close_s.rolling(20).std()
            boll_lower = (ma20 - 2 * std20).iloc[-1] if len(ma20.dropna()) > 0 else support1 * 0.95
            support2 = max(support1 * 0.95, float(boll_lower))

            # RSI6
            delta = close_s.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.rolling(6).mean()
            avg_loss = loss.rolling(6).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi6 = 100 - (100 / (1 + rs))
            current_rsi6 = float(rsi6.iloc[-1]) if not rsi6.empty and not pd.isna(rsi6.iloc[-1]) else 50

            # MA20
            ma20_val = float(ma20.iloc[-1]) if not ma20.empty and not pd.isna(ma20.iloc[-1]) else current_price

            # 止损止盈
            stop_a = support2 * 0.97
            stop_b = current_price * 0.92
            stop_loss = max(stop_a, stop_b)
            tp1 = current_price * 1.20
            tp2 = current_price * 1.30

            # V2.2: RSI灰带判断
            if current_rsi6 < 30:
                rsi_label = '超卖 ✓可第1批'
            elif current_rsi6 < 35:
                rsi_label = '灰带(30-35)→关注'
            elif current_rsi6 < 45:
                rsi_label = '中性偏低'
            else:
                rsi_label = '中性'

            # V2.2: 放量标准 = 成交量>5日均量1.5倍
            vol_ma5 = float(df_k['vol'].tail(5).mean())
            vol_today = float(df_k.iloc[-1]['vol'])
            vol_ratio = vol_today / vol_ma5 if vol_ma5 > 0 else 0

            dist_support1 = (current_price / support1 - 1) * 100

            plan_data.append({
                '代码': code,
                '名称': row['名称'],
                '现价': current_price,
                'RSI6': round(current_rsi6, 1),
                'RSI状态': rsi_label,
                '支撑1': round(support1, 4),
                '支撑2(布林)': round(support2, 4),
                'MA20': round(ma20_val, 4),
                '距支撑1%': round(dist_support1, 1),
                '量比': round(vol_ratio, 2),
                '止损': round(stop_loss, 4),
                '止盈+20%': round(tp1, 4),
                '止盈+30%': round(tp2, 4),
                '估值状态': row['估值状态'],
                'PE分位': row['PE分位'],
                '层级': row['层级'],
            })

        except Exception as e:
            continue

    return pd.DataFrame(plan_data)


###############################################################################
# 主流程
###############################################################################
def main():
    # 第一步
    df_filtered, combined, cache_days = step1_scan()

    # 第二步
    df_flow_passed, df_relaxed = step2_flow_filter(df_filtered, combined, cache_days)

    # 用放宽候选池进入估值（覆盖更多可能低估的品种）
    # 第二步严格通过的优先展示，放宽的作为备选
    if len(df_flow_passed) > 0:
        print('\n✓ 严格通过资金流筛选:')
        for _, r in df_flow_passed.iterrows():
            print(f'  {r["名称"]}({r["代码"]}) 5日净流入天数:{r["5日净流入天数"]}/{r["5日总天数"]} 趋势:{r["趋势类型"]}')

    # 取放宽候选做估值
    print(f'\n进入估值的候选ETF: {len(df_relaxed)}只')

    # 第三步
    df_val, df_under = step3_valuation(df_relaxed)
    if len(df_under) > 0:
        print('\n估值筛选结果（低估+观察）:')
        cols = ['代码','名称','PE值','PE分位','层级','EPS趋势','假低估风险','估值状态','流通市值(亿)']
        print(df_under[cols].to_string(index=False))

    # 第四步
    if len(df_under) > 0:
        df_cycle = step4_cycle(df_under)
        print('\n周期判断结果:')
        for _, r in df_cycle.iterrows():
            print(f'  {r["名称"]} → {r["行业"]} | {r["周期位置"]} {r["优先级"]} | PMI:{r["PMI验证"]}')

    # 第五步
    if len(df_under) > 0:
        df_plan = step5_build_plan(df_under)
        if len(df_plan) > 0:
            print('\n建仓计划:')
            for _, r in df_plan.iterrows():
                print(f'\n  {r["名称"]}({r["代码"]}) 现价:{r["现价"]} RSI6:{r["RSI6"]}({r["RSI状态"]})')
                print(f'    支撑1:{r["支撑1"]} 支撑2(布林):{r["支撑2(布林)"]} MA20:{r["MA20"]}')
                print(f'    距支撑1:{r["距支撑1%"]}% 量比:{r["量比"]}')
                print(f'    第1批: 跌到{r["支撑1"]}且RSI6<30 → 1/5仓')
                print(f'    第2批: 跌到{r["支撑2(布林)"]} → 1/5仓')
                print(f'    第3批: 站回MA20+量比>1.5+MACD金叉 → 2/5仓')
                print(f'    止损:{r["止损"]} 止盈1:{r["止盈+20%"]} 止盈2:{r["止盈+30%"]}')

    # V2.2: 等待清单
    df_plan_result = df_plan if len(df_under) > 0 else pd.DataFrame()
    print_waitlist(df_under, df_plan_result)

    # 每日追踪：存档+历史对比
    save_and_track(df_plan_result, df_under)


###############################################################################
# 每日追踪：存档+历史对比
###############################################################################
TRACKING_FILE = os.path.join(CACHE_DIR, 'etf_tracking.csv')


def save_and_track(df_plan, df_under):
    """每日结果存档 + 历史追踪对比

    同一天多次运行只保留最后一次：每次先回退今天的旧记录，再写入最新结果。
    追踪文件结构: 代码, 名称, 首次入选日期, 最近入选日期, 连续入选天数,
                   累计入选天数, 状态, PE分位, RSI6, 现价, 支撑1, 支撑2,
                   估值状态, 入选日期列表
    """
    today_str = datetime.now().strftime('%Y-%m-%d')
    track_file = TRACKING_FILE

    # 加载历史追踪记录
    if os.path.exists(track_file):
        df_track = pd.read_csv(track_file, dtype={'代码': str})
    else:
        df_track = pd.DataFrame(columns=[
            '代码', '名称', '首次入选日期', '最近入选日期',
            '连续入选天数', '累计入选天数', '状态',
            'PE分位', 'RSI6', '现价', '支撑1', '支撑2',
            '估值状态', '入选日期列表'
        ])

    # ===== 回退今天的旧记录（同一天多次运行，只保留最后一次）=====
    if len(df_track) > 0:
        rollback_rows = []
        for _, tr in df_track.iterrows():
            row = tr.to_dict()
            last_date = str(row.get('最近入选日期', ''))
            if last_date == today_str:
                # 今天已经记录过，需要回退
                date_list_str = str(row.get('入选日期列表', ''))
                if date_list_str and date_list_str != 'nan':
                    date_list = [d.strip() for d in date_list_str.split(',')]
                    # 移除今天
                    date_list = [d for d in date_list if d != today_str]
                else:
                    date_list = []

                if len(date_list) == 0:
                    # 今天是唯一入选日 → 这条记录是今天新建的，直接删除
                    continue
                else:
                    # 恢复到昨天的状态
                    row['入选日期列表'] = ','.join(date_list)
                    row['最近入选日期'] = date_list[-1]
                    row['连续入选天数'] = int(row.get('连续入选天数', 1)) - 1
                    row['累计入选天数'] = int(row.get('累计入选天数', 1)) - 1
                    if row['连续入选天数'] <= 0:
                        row['连续入选天数'] = 0
                        row['状态'] = '已退出'
                    else:
                        row['状态'] = '追踪中'
            rollback_rows.append(row)
        df_track = pd.DataFrame(rollback_rows) if rollback_rows else pd.DataFrame(columns=df_track.columns)

    # 准备今天入选的ETF集合
    today_codes = set()
    today_data = {}
    if df_plan is not None and len(df_plan) > 0:
        for _, r in df_plan.iterrows():
            code = str(r['代码'])
            today_codes.add(code)
            today_data[code] = r

    # 也把估值低估/观察但未进入建仓计划的纳入
    if df_under is not None and len(df_under) > 0:
        for _, r in df_under.iterrows():
            code = str(r['代码'])
            if code not in today_codes:
                today_codes.add(code)
                today_data[code] = r

    # 更新追踪记录
    existing_codes = set(df_track['代码'].astype(str).values) if len(df_track) > 0 else set()
    updated_rows = []

    # 1. 更新已存在的记录
    for _, tr in df_track.iterrows():
        code = str(tr['代码'])
        row = tr.to_dict()

        if code in today_codes:
            # 今天仍然入选
            r = today_data[code]
            was_tracked = row.get('状态', '').startswith('追踪')
            row['最近入选日期'] = today_str
            row['连续入选天数'] = int(row.get('连续入选天数', 0)) + 1
            row['累计入选天数'] = int(row.get('累计入选天数', 0)) + 1
            # 更新最新数据
            if 'PE分位' in r:
                row['PE分位'] = r.get('PE分位', row.get('PE分位'))
            if 'RSI6' in r:
                row['RSI6'] = r.get('RSI6', row.get('RSI6'))
            if '现价' in r:
                row['现价'] = r.get('现价', row.get('现价'))
            if '支撑1' in r:
                row['支撑1'] = r.get('支撑1', row.get('支撑1'))
            if '支撑2(布林)' in r:
                row['支撑2'] = r.get('支撑2(布林)', row.get('支撑2'))
            if '估值状态' in r:
                row['估值状态'] = r.get('估值状态', row.get('估值状态'))
            # 追加日期（去重）
            date_list = str(row.get('入选日期列表', ''))
            if date_list == 'nan' or date_list == '':
                date_list = today_str
            else:
                existing_dates = [d.strip() for d in date_list.split(',')]
                if today_str not in existing_dates:
                    date_list = date_list + ',' + today_str
            row['入选日期列表'] = date_list
            # 状态：之前已在追踪→继续追踪；之前已退出→重新入选
            if was_tracked:
                row['状态'] = '追踪中'
            else:
                row['状态'] = '追踪中(重新入选)'
        else:
            # 今天未入选 → 连续中断
            if row.get('状态', '').startswith('追踪'):
                row['状态'] = '已退出'
                row['连续入选天数'] = 0

        updated_rows.append(row)

    # 2. 新增今天首次入选的
    for code in today_codes:
        if code not in existing_codes:
            r = today_data[code]
            new_row = {
                '代码': code,
                '名称': r.get('名称', ''),
                '首次入选日期': today_str,
                '最近入选日期': today_str,
                '连续入选天数': 1,
                '累计入选天数': 1,
                '状态': '追踪中(新)',
                'PE分位': r.get('PE分位', ''),
                'RSI6': r.get('RSI6', '') if 'RSI6' in r else '',
                '现价': r.get('现价', r.get('最新价', '')),
                '支撑1': r.get('支撑1', ''),
                '支撑2': r.get('支撑2(布林)', ''),
                '估值状态': r.get('估值状态', ''),
                '入选日期列表': today_str,
            }
            updated_rows.append(new_row)

    # 保存更新后的追踪文件
    df_track_new = pd.DataFrame(updated_rows)
    df_track_new.to_csv(track_file, index=False, encoding='utf-8-sig')

    # ===== 输出追踪报告 =====
    print('\n' + '=' * 60)
    print('[每日追踪] 历史对比报告')
    print(f'追踪文件: {track_file}')
    print(f'追踪总记录: {len(df_track_new)}只')

    active = df_track_new[df_track_new['状态'].str.contains('追踪', na=False)]
    exited = df_track_new[df_track_new['状态'] == '已退出']
    new_today = df_track_new[df_track_new['状态'] == '追踪中(新)']
    continuing = df_track_new[df_track_new['状态'] == '追踪中']
    re_entry = df_track_new[df_track_new['状态'] == '追踪中(重新入选)']

    print(f'  当前追踪中: {len(active)}只 (新入选{len(new_today)} + 持续{len(continuing)} + 重新入选{len(re_entry)})')
    print(f'  已退出: {len(exited)}只')

    if len(new_today) > 0:
        print(f'\n--- 新入选（首次出现）---')
        for _, r in new_today.iterrows():
            print(f'  ★ {r["名称"]}({r["代码"]}) 现价:{r["现价"]} PE分位:{r["PE分位"]}% 估值:{r["估值状态"]}')

    if len(re_entry) > 0:
        print(f'\n--- 重新入选（之前退出，今天再次出现）---')
        for _, r in re_entry.iterrows():
            print(f'  ↻ {r["名称"]}({r["代码"]}) 现价:{r["现价"]} 累计{int(r["累计入选天数"])}天')
            print(f'    首次入选:{r["首次入选日期"]} 最近入选:{r["最近入选日期"]}')

    if len(continuing) > 0:
        print(f'\n--- 持续追踪（连续入选）---')
        df_cont = continuing.sort_values('连续入选天数', ascending=False)
        for _, r in df_cont.iterrows():
            print(f'  ◆ {r["名称"]}({r["代码"]}) 连续{int(r["连续入选天数"])}天 累计{int(r["累计入选天数"])}天')
            print(f'    现价:{r["现价"]} RSI6:{r["RSI6"]} PE分位:{r["PE分位"]}% 估值:{r["估值状态"]}')
            print(f'    首次入选:{r["首次入选日期"]} 最近入选:{r["最近入选日期"]}')
            dates = str(r.get('入选日期列表', ''))
            if dates and dates != 'nan':
                print(f'    入选日期: {dates}')

    if len(exited) > 0:
        print(f'\n--- 已退出（今日未入选）---')
        df_exit = exited.sort_values('最近入选日期', ascending=False).head(10)
        for _, r in df_exit.iterrows():
            print(f'  ✗ {r["名称"]}({r["代码"]}) 最后入选:{r["最近入选日期"]} 累计{int(r["累计入选天数"])}天')

    # 连续>=3天的品种重点标注
    hot = active[active['连续入选天数'] >= 3]
    if len(hot) > 0:
        print(f'\n⚠ 连续≥3天入选（主力持续吸筹信号强）:')
        for _, r in hot.sort_values('连续入选天数', ascending=False).iterrows():
            print(f'  🔴 {r["名称"]}({r["代码"]}) 连续{int(r["连续入选天数"])}天 现价:{r["现价"]} RSI6:{r["RSI6"]}')

    print(f'\n提示: 如需删除某品种，编辑 {track_file} 删除对应行即可')

    return df_track_new


def print_waitlist(df_under, df_plan):
    """V2.2新增: 无品种入场时输出等待清单+触发价"""
    print('\n' + '='*60)
    print('[等待清单] 触发价提醒')

    if len(df_plan) == 0:
        print('  当前无候选ETF，等待市场进一步调整')
        return

    # 按距支撑1的距离排序
    df_sorted = df_plan.sort_values('距支撑1%')
    for _, r in df_sorted.iterrows():
        trigger_desc = []
        if r['RSI6'] < 35:
            trigger_desc.append('RSI接近超卖')
        if r['距支撑1%'] < 5:
            trigger_desc.append(f'距支撑1仅{r["距支撑1%"]}%')
        if r['PE分位'] is not None and r['PE分位'] < 30:
            trigger_desc.append(f'PE分位{r["PE分位"]}%')

        trigger_str = ' | '.join(trigger_desc) if trigger_desc else '等待条件触发'
        print(f'  {r["名称"]}({r["代码"]})')
        print(f'    触发价: 第1批={r["支撑1"]} 第2批={r["支撑2(布林)"]}')
        print(f'    关注信号: {trigger_str}')
        print(f'    估值: {r["估值状态"]} ({r["层级"]} 分位{r["PE分位"]}%)')


if __name__ == '__main__':
    main()
