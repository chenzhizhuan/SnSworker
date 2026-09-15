# -*- coding: utf-8 -*-
"""
同花顺数据获取脚本 (基于 akshare 1.18+)
支持：实时行情、历史K线、板块数据、技术选股、资金流向、龙虎榜、个股详情
"""

import sys
import json
import argparse
import pandas as pd

try:
    import akshare as ak
except ImportError:
    print("ERROR: akshare 未安装，请执行 pip install akshare", file=sys.stderr)
    sys.exit(1)


def df_to_json(df: pd.DataFrame) -> str:
    """DataFrame 转紧凑 JSON"""
    if df is None or df.empty:
        return json.dumps({"count": 0, "data": []}, ensure_ascii=False)
    return json.dumps(
        {"count": len(df), "data": df.to_dict(orient="records")},
        ensure_ascii=False,
        default=str,
    )


# ──────────────────────────────────────────────
# 1. 实时行情
# ──────────────────────────────────────────────

def stock_zh_a_spot():
    """A股全部实时行情"""
    return ak.stock_zh_a_spot_em()


def stock_sh_a_spot():
    """沪A实时行情"""
    return ak.stock_sh_a_spot_em()


def stock_sz_a_spot():
    """深A实时行情"""
    return ak.stock_sz_a_spot_em()


# ──────────────────────────────────────────────
# 2. 历史K线
# ──────────────────────────────────────────────

def stock_zh_a_hist(symbol: str, period: str = "daily",
                    start_date: str = "", end_date: str = "", adjust: str = "qfq"):
    """
    个股历史K线
    period: daily / weekly / monthly
    adjust: qfq(前复权) / hfq(后复权) / ""(不复权)
    """
    return ak.stock_zh_a_hist(
        symbol=symbol, period=period,
        start_date=start_date, end_date=end_date, adjust=adjust
    )


# ──────────────────────────────────────────────
# 3. 同花顺板块
# ──────────────────────────────────────────────

def stock_board_industry_name():
    """同花顺-行业板块列表"""
    return ak.stock_board_industry_name_ths()


def stock_board_industry_info(symbol: str):
    """同花顺-行业板块成分股及详情"""
    return ak.stock_board_industry_info_ths(symbol=symbol)


def stock_board_industry_summary():
    """同花顺-行业板块汇总"""
    return ak.stock_board_industry_summary_ths()


def stock_board_industry_index(symbol: str, start_date: str = "", end_date: str = ""):
    """同花顺-行业板块指数历史"""
    return ak.stock_board_industry_index_ths(
        symbol=symbol, start_date=start_date, end_date=end_date
    )


def stock_board_concept_name():
    """同花顺-概念板块列表"""
    return ak.stock_board_concept_name_ths()


def stock_board_concept_info(symbol: str):
    """同花顺-概念板块成分股及详情"""
    return ak.stock_board_concept_info_ths(symbol=symbol)


def stock_board_concept_summary():
    """同花顺-概念板块汇总"""
    return ak.stock_board_concept_summary_ths()


def stock_board_concept_index(symbol: str, start_date: str = "", end_date: str = ""):
    """同花顺-概念板块指数历史"""
    return ak.stock_board_concept_index_ths(
        symbol=symbol, start_date=start_date, end_date=end_date
    )


# ──────────────────────────────────────────────
# 4. 同花顺技术选股排名
# ──────────────────────────────────────────────

def stock_rank_cxg(symbol: str = "创月新高"):
    """同花顺-技术选股-创新高 (symbol: 创月新高/创季新高/创半年新高/创年新高)"""
    return ak.stock_rank_cxg_ths(symbol=symbol)


def stock_rank_cxd(symbol: str = "创月新低"):
    """同花顺-技术选股-创新低 (symbol: 创月新低/创季新低/创半年新低/创年新低)"""
    return ak.stock_rank_cxd_ths(symbol=symbol)


def stock_rank_ljqs():
    """同花顺-技术选股-连涨"""
    return ak.stock_rank_ljqs_ths()


def stock_rank_ljqd():
    """同花顺-技术选股-连跌"""
    return ak.stock_rank_ljqd_ths()


def stock_rank_lxsz():
    """同花顺-技术选股-连续缩量"""
    return ak.stock_rank_lxsz_ths()


def stock_rank_cxfl():
    """同花顺-技术选股-创周新高"""
    return ak.stock_rank_cxfl_ths()


# ──────────────────────────────────────────────
# 5. 资金流向
# ──────────────────────────────────────────────

def stock_individual_fund_flow(stock: str, market: str = "sh"):
    """个股资金流向 (stock: 股票代码, market: sh/sz)"""
    return ak.stock_individual_fund_flow(stock=stock, market=market)


def stock_market_fund_flow():
    """大盘资金流向"""
    return ak.stock_market_fund_flow()


def stock_sector_fund_flow_rank(indicator: str = "今日", sector_type: str = "行业资金流"):
    """板块资金流向排名 (indicator: 今日/3日/5日/10日, sector_type: 行业资金流/概念资金流)"""
    return ak.stock_sector_fund_flow_rank(indicator=indicator, sector_type=sector_type)


def stock_individual_fund_flow_rank(indicator: str = "5日"):
    """个股资金流向排名 (indicator: 今日/3日/5日/10日)"""
    return ak.stock_individual_fund_flow_rank(indicator=indicator)


# ──────────────────────────────────────────────
# 6. 龙虎榜
# ──────────────────────────────────────────────

def stock_lhb_detail(start_date: str, end_date: str = ""):
    """龙虎榜明细 (start_date/end_date: YYYYMMDD)"""
    return ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)


def stock_lhb_statistic(symbol: str = "近一月"):
    """龙虎榜个股上榜统计 (symbol: 近一月/近三月/近六月/近一年)"""
    return ak.stock_lhb_stock_statistic_em(symbol=symbol)


# ──────────────────────────────────────────────
# 7. 个股信息与财务
# ──────────────────────────────────────────────

def stock_individual_info(symbol: str):
    """个股基本信息"""
    return ak.stock_individual_info_em(symbol=symbol)


def stock_financial_abstract(symbol: str, indicator: str = "按报告期"):
    """同花顺-个股主要财务指标 (indicator: 按报告期/按年度)"""
    return ak.stock_financial_abstract_ths(symbol=symbol, indicator=indicator)


def stock_financial_indicator(symbol: str, start_year: str = "1900"):
    """个股财务分析指标"""
    return ak.stock_financial_analysis_indicator(symbol=symbol, start_year=start_year)


# ──────────────────────────────────────────────
# 8. 热门排名
# ──────────────────────────────────────────────

def stock_hot_rank():
    """东方财富-人气排名"""
    return ak.stock_hot_rank_em()


# ──────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────

# 每个条目: (函数, 参数名列表, 默认值字典)
FUNC_MAP = {
    # 实时行情
    "a_spot":        (stock_zh_a_spot, [], {}),
    "sh_spot":       (stock_sh_a_spot, [], {}),
    "sz_spot":       (stock_sz_a_spot, [], {}),
    # 历史K线
    "hist":          (stock_zh_a_hist, ["symbol", "period", "start_date", "end_date", "adjust"],
                      {"period": "daily", "adjust": "qfq"}),
    # 行业板块
    "industry_name":     (stock_board_industry_name, [], {}),
    "industry_info":     (stock_board_industry_info, ["symbol"], {}),
    "industry_summary":  (stock_board_industry_summary, [], {}),
    "industry_index":    (stock_board_industry_index, ["symbol", "start_date", "end_date"], {}),
    # 概念板块
    "concept_name":      (stock_board_concept_name, [], {}),
    "concept_info":      (stock_board_concept_info, ["symbol"], {}),
    "concept_summary":   (stock_board_concept_summary, [], {}),
    "concept_index":     (stock_board_concept_index, ["symbol", "start_date", "end_date"], {}),
    # 技术选股
    "rank_cxg":  (stock_rank_cxg, ["symbol"], {"symbol": "创月新高"}),
    "rank_cxd":  (stock_rank_cxd, ["symbol"], {"symbol": "创月新低"}),
    "rank_ljqs": (stock_rank_ljqs, [], {}),
    "rank_ljqd": (stock_rank_ljqd, [], {}),
    "rank_lxsz": (stock_rank_lxsz, [], {}),
    "rank_cxfl": (stock_rank_cxfl, [], {}),
    # 资金流向
    "fund_flow":           (stock_individual_fund_flow, ["stock", "market"], {"market": "sh"}),
    "market_fund_flow":    (stock_market_fund_flow, [], {}),
    "sector_fund_rank":    (stock_sector_fund_flow_rank, ["indicator", "sector_type"],
                            {"indicator": "今日", "sector_type": "行业资金流"}),
    "individual_fund_rank": (stock_individual_fund_flow_rank, ["indicator"], {"indicator": "5日"}),
    # 龙虎榜
    "lhb_detail":    (stock_lhb_detail, ["start_date", "end_date"], {}),
    "lhb_statistic": (stock_lhb_statistic, ["symbol"], {"symbol": "近一月"}),
    # 个股信息
    "stock_info":           (stock_individual_info, ["symbol"], {}),
    "financial_abstract":   (stock_financial_abstract, ["symbol", "indicator"], {"indicator": "按报告期"}),
    "financial_indicator":  (stock_financial_indicator, ["symbol", "start_year"], {"start_year": "1900"}),
    # 热门排名
    "hot_rank": (stock_hot_rank, [], {}),
}


def main():
    parser = argparse.ArgumentParser(description="同花顺数据获取工具 (基于akshare)")
    parser.add_argument("func", choices=FUNC_MAP.keys(), help="功能名称")
    parser.add_argument("--symbol", default="", help="股票代码/板块名称/选股类型")
    parser.add_argument("--stock", default="", help="股票代码(资金流)")
    parser.add_argument("--market", default="", help="市场 sh/sz")
    parser.add_argument("--period", default="", help="K线周期 daily/weekly/monthly")
    parser.add_argument("--start_date", default="", help="开始日期 YYYYMMDD")
    parser.add_argument("--end_date", default="", help="结束日期 YYYYMMDD")
    parser.add_argument("--adjust", default="", help="复权 qfq/hfq/空")
    parser.add_argument("--indicator", default="", help="指标(今日/3日/5日/10日/按报告期等)")
    parser.add_argument("--sector_type", default="", help="板块类型(行业资金流/概念资金流)")
    parser.add_argument("--start_year", default="", help="起始年份(财务指标)")
    parser.add_argument("--limit", type=int, default=0, help="限制返回行数(0=全部)")

    args = parser.parse_args()
    fn, param_names, defaults = FUNC_MAP[args.func]

    # 构建参数，空值时使用默认值
    kwargs = {}
    for p in param_names:
        val = getattr(args, p)
        if val == "" or val is None:
            val = defaults.get(p, "")
        kwargs[p] = val

    # 过滤掉空字符串参数（避免传入无效空值）
    kwargs = {k: v for k, v in kwargs.items() if v != ""}

    try:
        df = fn(**kwargs)
        if args.limit > 0:
            df = df.head(args.limit)
        print(df_to_json(df))
    except Exception as e:
        error_msg = {"error": str(e), "func": args.func, "params": kwargs}
        print(json.dumps(error_msg, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
