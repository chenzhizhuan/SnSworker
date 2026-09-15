#!/usr/bin/env python3
"""数据可视化脚本 - 生成各类统计图表"""

import argparse
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# 尝试设置中文字体
_CHINESE_FONTS = [
    "SimHei", "Microsoft YaHei", "STHeiti", "WenQuanYi Micro Hei",
    "Noto Sans CJK SC", "PingFang SC", "Source Han Sans SC",
]
_FONT_SET = False

def setup_chinese_font():
    global _FONT_SET
    if _FONT_SET:
        return
    for name in _CHINESE_FONTS:
        if any(name.lower() in f.name.lower() for f in fm.fontManager.ttflist):
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["axes.unicode_minus"] = False
            _FONT_SET = True
            return
    # fallback
    plt.rcParams["axes.unicode_minus"] = False


def plot_histogram(df, column, output_path, bins=30, title=None, color="#4C72B0"):
    """绘制直方图"""
    setup_chinese_font()
    fig, ax = plt.subplots(figsize=(10, 6))
    data = df[column].dropna()
    ax.hist(data, bins=bins, color=color, edgecolor="white", alpha=0.85)
    ax.axvline(data.mean(), color="red", linestyle="--", linewidth=1.5, label=f"均值: {data.mean():.2f}")
    ax.axvline(data.median(), color="orange", linestyle="--", linewidth=1.5, label=f"中位数: {data.median():.2f}")
    ax.set_xlabel(column, fontsize=12)
    ax.set_ylabel("频数", fontsize=12)
    ax.set_title(title or f"{column} 分布直方图", fontsize=14)
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_bar(df, x_col, y_col=None, output_path="bar.png", top_n=None, title=None, color="#4C72B0"):
    """绘制柱状图"""
    setup_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 6))
    if y_col is None:
        # 统计分类变量频次
        counts = df[x_col].value_counts()
        if top_n:
            counts = counts.head(top_n)
        counts.plot(kind="bar", ax=ax, color=color, edgecolor="white")
        ax.set_ylabel("频数", fontsize=12)
        ax.set_title(title or f"{x_col} 频次分布", fontsize=14)
    else:
        ax.bar(df[x_col].astype(str), df[y_col], color=color, edgecolor="white")
        ax.set_ylabel(y_col, fontsize=12)
        ax.set_title(title or f"{x_col} vs {y_col}", fontsize=14)
    ax.set_xlabel(x_col, fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_line(df, x_col, y_col, output_path="line.png", title=None, color="#4C72B0", marker=True):
    """绘制折线图"""
    setup_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df[x_col], df[y_col], color=color, linewidth=2, marker="o" if marker else None, markersize=4)
    ax.set_xlabel(x_col, fontsize=12)
    ax.set_ylabel(y_col, fontsize=12)
    ax.set_title(title or f"{y_col} 趋势图", fontsize=14)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_scatter(df, x_col, y_col, output_path="scatter.png", title=None, color="#4C72B0", trend_line=False):
    """绘制散点图"""
    setup_chinese_font()
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(df[x_col], df[y_col], alpha=0.5, s=30, color=color, edgecolors="white", linewidth=0.5)
    if trend_line:
        mask = df[x_col].notna() & df[y_col].notna()
        if mask.sum() > 1:
            z = np.polyfit(df.loc[mask, x_col], df.loc[mask, y_col], 1)
            p = np.poly1d(z)
            x_sorted = np.sort(df.loc[mask, x_col])
            ax.plot(x_sorted, p(x_sorted), "r--", linewidth=2, label=f"趋势线: y={z[0]:.4f}x+{z[1]:.4f}")
            # 计算 R^2
            corr = df.loc[mask, [x_col, y_col]].corr().iloc[0, 1]
            ax.legend(fontsize=10, title=f"r={corr:.4f}")
    ax.set_xlabel(x_col, fontsize=12)
    ax.set_ylabel(y_col, fontsize=12)
    ax.set_title(title or f"{x_col} vs {y_col} 散点图", fontsize=14)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_boxplot(df, columns, output_path="boxplot.png", title=None):
    """绘制箱线图"""
    setup_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 6))
    data = [df[col].dropna().values for col in columns if df[col].notna().sum() > 0]
    valid_cols = [col for col in columns if df[col].notna().sum() > 0]
    bp = ax.boxplot(data, labels=valid_cols, patch_artist=True)
    colors = plt.cm.Set3(np.linspace(0, 1, len(valid_cols)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
    ax.set_ylabel("数值", fontsize=12)
    ax.set_title(title or "多列箱线图", fontsize=14)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_heatmap(df, output_path="heatmap.png", title=None, numeric_only=True):
    """绘制相关性热力图"""
    setup_chinese_font()
    if numeric_only:
        df = df.select_dtypes(include=[np.number])
    corr = df.corr()
    fig, ax = plt.subplots(figsize=(max(10, len(corr.columns) * 0.8), max(8, len(corr.index) * 0.8)))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(corr.index, fontsize=9)
    # 标注数值
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            val = corr.iloc[i, j]
            text_color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8, color=text_color)
    plt.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title or "相关性热力图", fontsize=14)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_pie(df, column, output_path="pie.png", top_n=10, title=None):
    """绘制饼图"""
    setup_chinese_font()
    fig, ax = plt.subplots(figsize=(10, 8))
    counts = df[column].value_counts().head(top_n)
    if len(counts) < df[column].nunique():
        others = df[column].value_counts().iloc[top_n:].sum()
        counts["其他"] = others
    colors = plt.cm.Set3(np.linspace(0, 1, len(counts)))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index, autopct="%1.1f%%",
        colors=colors, startangle=90, pctdistance=0.85,
    )
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(8)
    ax.set_title(title or f"{column} 占比分布", fontsize=14)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="数据可视化工具")
    parser.add_argument("input", help="输入文件路径 (CSV/Excel)")
    parser.add_argument("--type", choices=["histogram", "bar", "line", "scatter", "boxplot", "heatmap", "pie"],
                        required=True, help="图表类型")
    parser.add_argument("--x", help="X轴列名")
    parser.add_argument("--y", help="Y轴列名")
    parser.add_argument("--columns", nargs="+", help="多列 (箱线图/热力图)")
    parser.add_argument("--output", default=None, help="输出图片路径")
    parser.add_argument("--title", default=None, help="图表标题")
    parser.add_argument("--bins", type=int, default=30, help="直方图分箱数")
    parser.add_argument("--top-n", type=int, default=None, help="显示前N个类别")
    parser.add_argument("--trend-line", action="store_true", help="散点图添加趋势线")
    parser.add_argument("--encoding", default="utf-8", help="文件编码")
    args = parser.parse_args()

    # 读取数据
    if args.input.endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.input)
    else:
        df = pd.read_csv(args.input, encoding=args.encoding)

    # 确定输出路径
    suffix = f"_{args.type}.png"
    output_path = args.output or suffix

    # 绘图
    if args.type == "histogram":
        plot_histogram(df, args.x, output_path, bins=args.bins, title=args.title)
    elif args.type == "bar":
        plot_bar(df, args.x, y_col=args.y, output_path=output_path, top_n=args.top_n, title=args.title)
    elif args.type == "line":
        plot_line(df, args.x, args.y, output_path, title=args.title)
    elif args.type == "scatter":
        plot_scatter(df, args.x, args.y, output_path, title=args.title, trend_line=args.trend_line)
    elif args.type == "boxplot":
        cols = args.columns or df.select_dtypes(include=[np.number]).columns.tolist()[:6]
        plot_boxplot(df, cols, output_path, title=args.title)
    elif args.type == "heatmap":
        cols = args.columns or None
        sub_df = df[cols] if cols else df
        plot_heatmap(sub_df, output_path, title=args.title)
    elif args.type == "pie":
        plot_pie(df, args.x, output_path, top_n=args.top_n or 10, title=args.title)

    print(f"Chart saved to: {output_path}")


if __name__ == "__main__":
    main()
