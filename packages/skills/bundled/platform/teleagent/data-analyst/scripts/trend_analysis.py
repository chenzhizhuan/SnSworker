#!/usr/bin/env python3
"""趋势预测分析脚本 - 时间序列趋势分析与简单预测"""

import argparse
import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


def setup_chinese_font():
    _CHINESE_FONTS = [
        "SimHei", "Microsoft YaHei", "STHeiti", "WenQuanYi Micro Hei",
        "Noto Sans CJK SC", "PingFang SC", "Source Han Sans SC",
    ]
    for name in _CHINESE_FONTS:
        if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            return
    plt.rcParams["axes.unicode_minus"] = False


def moving_average(series, window=7):
    """计算移动平均"""
    return series.rolling(window=window, min_periods=1).mean()


def linear_trend(series):
    """线性趋势拟合，返回斜率和截距"""
    x = np.arange(len(series))
    mask = series.notna()
    if mask.sum() < 2:
        return None, None
    z = np.polyfit(x[mask], series[mask], 1)
    return z[0], z[1]


def simple_forecast(series, periods=5, method="linear"):
    """简单预测"""
    series = series.dropna()
    if len(series) < 3:
        return None

    if method == "linear":
        slope, intercept = linear_trend(series)
        if slope is None:
            return None
        future_x = np.arange(len(series), len(series) + periods)
        forecast = slope * future_x + intercept
        return forecast.tolist()

    elif method == "mean":
        avg = series.mean()
        return [avg] * periods

    return None


def analyze_trend(df, date_col, value_col, output_dir=".", periods=5, title=None):
    """完整趋势分析"""
    setup_chinese_font()

    # 确保日期列是 datetime
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, value_col]).sort_values(date_col)

    series = df.set_index(date_col)[value_col]

    # 计算指标
    slope, intercept = linear_trend(series)
    ma7 = moving_average(series, 7)
    ma30 = moving_average(series, 30)

    # 增长率计算
    if len(series) >= 2:
        first_val = series.iloc[0]
        last_val = series.iloc[-1]
        total_growth = (last_val - first_val) / abs(first_val) * 100 if first_val != 0 else 0
        period_count = len(series) - 1
        cagr = ((last_val / abs(first_val)) ** (1 / period_count) - 1) * 100 if first_val > 0 else None
    else:
        total_growth = 0
        cagr = None

    # 预测
    forecast = simple_forecast(series, periods, "linear")

    # 绘制趋势图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [3, 1]})

    # 主图：趋势 + 移动平均
    ax1.plot(series.index, series.values, label="原始数据", alpha=0.5, color="#4C72B0", linewidth=1)
    if ma7.dropna().any():
        ax1.plot(ma7.index, ma7.values, label="7日移动平均", color="#DD8452", linewidth=1.5)
    if len(series) > 30 and ma30.dropna().any():
        ax1.plot(ma30.index, ma30.values, label="30日移动平均", color="#55A868", linewidth=1.5)
    if slope is not None:
        x_range = pd.date_range(series.index.min(), series.index.max(), freq="D")
        trend_vals = slope * np.arange(len(x_range)) + intercept
        ax1.plot(x_range, trend_vals, "r--", linewidth=1.5, label=f"线性趋势 (斜率: {slope:.4f})")

    # 绘制预测部分
    if forecast is not None and slope is not None:
        future_dates = pd.date_range(start=series.index.max(), periods=periods + 1, freq="D")[1:]
        ax1.plot(future_dates, forecast, "r*-", linewidth=2, markersize=8, label="预测值", alpha=0.7)
        ax1.axvline(series.index.max(), color="gray", linestyle=":", alpha=0.5)

    ax1.set_title(title or f"{value_col} 趋势分析", fontsize=14)
    ax1.set_ylabel(value_col, fontsize=12)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 副图：日环比变化
    daily_change = series.pct_change() * 100
    colors = ["#d9534f" if v < 0 else "#5cb85c" for v in daily_change.values]
    ax2.bar(daily_change.index, daily_change.values, color=colors, alpha=0.7, width=1)
    ax2.set_ylabel("日环比变化 (%)", fontsize=12)
    ax2.set_xlabel("日期", fontsize=12)
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = str(Path(output_dir) / "trend_analysis.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 结果摘要
    result = {
        "trend_direction": "上升" if slope and slope > 0 else "下降" if slope and slope < 0 else "平稳",
        "slope_per_day": round(float(slope), 6) if slope is not None else None,
        "total_growth_pct": round(float(total_growth), 2),
        "cagr_pct": round(float(cagr), 4) if cagr is not None else None,
        "mean_value": round(float(series.mean()), 4),
        "std_value": round(float(series.std()), 4),
        "max_value": round(float(series.max()), 4),
        "min_value": round(float(series.min()), 4),
        "data_points": len(series),
        "date_range": f"{series.index.min().strftime('%Y-%m-%d')} ~ {series.index.max().strftime('%Y-%m-%d')}",
        "forecast_next_n": forecast,
        "chart_path": output_path,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="趋势预测分析")
    parser.add_argument("input", help="输入文件路径 (CSV/Excel)")
    parser.add_argument("--date", required=True, help="日期列名")
    parser.add_argument("--value", required=True, help="数值列名")
    parser.add_argument("--periods", type=int, default=5, help="预测期数")
    parser.add_argument("--output-dir", default=".", help="输出目录")
    parser.add_argument("--title", default=None, help="图表标题")
    parser.add_argument("--encoding", default="utf-8", help="文件编码")
    args = parser.parse_args()

    if args.input.endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input, encoding=args.encoding)

    result = analyze_trend(df, args.date, args.value, args.output_dir, args.periods, args.title)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
