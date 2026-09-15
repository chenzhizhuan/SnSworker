#!/usr/bin/env python3
"""相关性分析脚本 - 分析变量间的相关关系"""

import argparse
import json
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from itertools import combinations


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


def correlation_analysis(df, columns=None, method="pearson", output_dir="."):
    """执行相关性分析"""
    setup_chinese_font()

    if columns:
        df = df[columns]
    df_numeric = df.select_dtypes(include=[np.number])

    corr_matrix = df_numeric.corr(method=method)

    # 找出强相关对
    strong_pairs = []
    for col1, col2 in combinations(corr_matrix.columns, 2):
        r = corr_matrix.loc[col1, col2]
        if abs(r) >= 0.5:
            strong_pairs.append({
                "var1": col1, "var2": col2,
                "correlation": round(float(r), 4),
                "strength": "强正相关" if r > 0.7 else "中等正相关" if r > 0.5
                           else "强负相关" if r < -0.7 else "中等负相关",
            })
    strong_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    # 绘制热力图
    fig, ax = plt.subplots(figsize=(max(10, len(corr_matrix.columns) * 0.8),
                                   max(8, len(corr_matrix.index) * 0.8)))
    im = ax.imshow(corr_matrix.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr_matrix.columns)))
    ax.set_yticks(range(len(corr_matrix.index)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="right", fontsize=10)
    ax.set_yticklabels(corr_matrix.index, fontsize=10)

    for i in range(len(corr_matrix.index)):
        for j in range(len(corr_matrix.columns)):
            val = corr_matrix.iloc[i, j]
            text_color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=9, color=text_color)

    plt.colorbar(im, ax=ax, shrink=0.8)
    method_label = {"pearson": "Pearson", "spearman": "Spearman", "kendall": "Kendall"}.get(method, method)
    ax.set_title(f"相关性热力图 ({method_label})", fontsize=14)
    plt.tight_layout()
    heatmap_path = str(Path(output_dir) / "correlation_heatmap.png")
    fig.savefig(heatmap_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 对强相关对绘制散点图
    scatter_paths = []
    for pair in strong_pairs[:6]:  # 最多6对
        col1, col2 = pair["var1"], pair["var2"]
        mask = df[col1].notna() & df[col2].notna()
        if mask.sum() < 3:
            continue

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(df.loc[mask, col1], df.loc[mask, col2], alpha=0.4, s=20, color="#4C72B0",
                   edgecolors="white", linewidth=0.3)

        # 趋势线
        z = np.polyfit(df.loc[mask, col1], df.loc[mask, col2], 1)
        p = np.poly1d(z)
        x_sorted = np.sort(df.loc[mask, col1])
        ax.plot(x_sorted, p(x_sorted), "r--", linewidth=2)

        r = pair["correlation"]
        ax.set_xlabel(col1, fontsize=12)
        ax.set_ylabel(col2, fontsize=12)
        ax.set_title(f"{col1} vs {col2}\nr = {r:.4f}", fontsize=13)
        ax.grid(True, alpha=0.3)

        fname = f"scatter_{col1}_{col2}.png".replace(" ", "_")
        fpath = str(Path(output_dir) / fname)
        plt.tight_layout()
        fig.savefig(fpath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        scatter_paths.append(fpath)

    result = {
        "method": method,
        "variables_analyzed": corr_matrix.columns.tolist(),
        "correlation_matrix": {col: {col2: round(float(v), 4) for col2, v in row.items()}
                               for col, row in corr_matrix.iterrows()},
        "strong_correlations": strong_pairs,
        "heatmap_path": heatmap_path,
        "scatter_paths": scatter_paths,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="相关性分析")
    parser.add_argument("input", help="输入文件路径 (CSV/Excel)")
    parser.add_argument("--columns", nargs="+", default=None, help="指定分析的列名")
    parser.add_argument("--method", choices=["pearson", "spearman", "kendall"], default="pearson",
                        help="相关系数方法")
    parser.add_argument("--output-dir", default=".", help="输出目录")
    parser.add_argument("--encoding", default="utf-8", help="文件编码")
    args = parser.parse_args()

    if args.input.endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input, encoding=args.encoding)

    result = correlation_analysis(df, args.columns, args.method, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
