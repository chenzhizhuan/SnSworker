#!/usr/bin/env python3
"""描述性统计分析脚本 - 计算数据集的关键统计指标"""

import argparse
import json
import sys
import pandas as pd
import numpy as np


def compute_stats(df: pd.DataFrame, columns: list = None) -> dict:
    """计算指定列的描述性统计指标"""
    if columns:
        df = df[columns]

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    results = {}

    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        results[col] = {
            "count": int(series.count()),
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "min": round(float(series.min()), 4),
            "q1": round(float(series.quantile(0.25)), 4),
            "median": round(float(series.median()), 4),
            "q3": round(float(series.quantile(0.75)), 4),
            "max": round(float(series.max()), 4),
            "iqr": round(float(series.quantile(0.75) - series.quantile(0.25)), 4),
            "skewness": round(float(series.skew()), 4),
            "kurtosis": round(float(series.kurtosis()), 4),
            "missing": int(df[col].isna().sum()),
            "missing_pct": round(float(df[col].isna().mean() * 100), 2),
        }

    # 整体概览
    overview = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": df.select_dtypes(exclude=[np.number]).columns.tolist(),
        "total_missing": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
    }

    return {"overview": overview, "column_stats": results}


def main():
    parser = argparse.ArgumentParser(description="描述性统计分析")
    parser.add_argument("input", help="输入文件路径 (CSV/Excel)")
    parser.add_argument("--columns", nargs="+", default=None, help="指定分析的列名")
    parser.add_argument("--output", default=None, help="输出JSON路径")
    parser.add_argument("--encoding", default="utf-8", help="文件编码")
    args = parser.parse_args()

    # 读取数据
    if args.input.endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input, encoding=args.encoding)

    result = compute_stats(df, args.columns)
    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
