#!/usr/bin/env python3
"""
Excel 数据可视化分析脚本
功能：读取 Excel/CSV 文件，自动分析数据特征，智能选择图表类型并生成可视化图片。

用法：
  python analyze_visualize.py <excel_file> [options]

选项：
  --output-dir DIR      输出图片目录（默认: ./viz_output）
  --sheet NAME          指定工作表名（默认: 第一个工作表）
  --sheet-index INT     指定工作表索引（默认: 0）
  --no-auto             禁用自动分析，仅输出数据摘要
  --charts LIST         指定图表类型列表，逗号分隔
                        可选: line,bar,pie,donut,heatmap,area,scatter,histogram,box
  --max-categories INT  分类列最大类别数（默认: 10）
  --dpi INT             图片分辨率DPI（默认: 150）
  --style STYLE         matplotlib样式（默认: seaborn-v0_8-whitegrid）
  --title STR           自定义总标题
  --font-family STR     字体（默认: sans-serif）
  --cmap STR            热力图色系（默认: YlOrRd）

示例：
  python analyze_visualize.py sales.xlsx
  python analyze_visualize.py data.xlsx --charts bar,pie --output-dir ./charts
  python analyze_visualize.py multi.xlsx --sheet "Q1数据" --dpi 200
"""

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")


# ── 中文字体自动配置 ──────────────────────────────────────────────
# 已知的中文字体文件路径（按优先级排列）
_CN_FONT_PATHS = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/3419f2a427639ad8c8e139149a287865a90fa17e.asset/AssetData/PingFang.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "C:\\Windows\\Fonts\\msyh.ttc",
    "C:\\Windows\\Fonts\\simhei.ttf",
]

_CN_FONT_NAMES = [
    "PingFang SC", "Heiti SC", "STHeiti", "Hiragino Sans GB",
    "Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei",
    "Noto Sans CJK SC", "Source Han Sans CN", "Arial Unicode MS",
]


def _configure_chinese_fonts(font_family=None):
    """配置中文字体，确保图表中文标签正常显示。"""
    plt.rcParams["axes.unicode_minus"] = False

    if font_family and font_family != "sans-serif":
        plt.rcParams["font.family"] = font_family
        return

    # 优先通过字体文件直接注册（最可靠）
    import os
    for fpath in _CN_FONT_PATHS:
        if os.path.exists(fpath):
            try:
                fm.fontManager.addfont(fpath)
                prop = fm.FontProperties(fname=fpath)
                fname = prop.get_name()
                plt.rcParams["font.sans-serif"] = [fname, "DejaVu Sans"]
                plt.rcParams["font.family"] = "sans-serif"
                return
            except Exception:
                continue

    # 回退：通过字体名称匹配
    available = {f.name for f in fm.fontManager.ttflist}
    for cn in _CN_FONT_NAMES:
        if cn in available:
            plt.rcParams["font.sans-serif"] = [cn, "DejaVu Sans"]
            plt.rcParams["font.family"] = "sans-serif"
            return

    # 最终回退
    plt.rcParams["font.family"] = "sans-serif"


# ── 数据读取 ──────────────────────────────────────────────────────
def read_data(filepath, sheet=None, sheet_index=0):
    """读取 Excel / CSV 文件，返回 DataFrame。"""
    ext = Path(filepath).suffix.lower()
    if ext in (".xls", ".xlsx"):
        if sheet:
            df = pd.read_excel(filepath, sheet_name=sheet)
        else:
            df = pd.read_excel(filepath, sheet_name=sheet_index)
    elif ext in (".csv", ".tsv"):
        df = pd.read_csv(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
    return df


def list_sheets(filepath):
    """列出 Excel 文件中所有工作表名。"""
    ext = Path(filepath).suffix.lower()
    if ext in (".xls", ".xlsx"):
        return pd.ExcelFile(filepath).sheet_names
    return ["(CSV 单表)"]


# ── 列类型分析 ────────────────────────────────────────────────────
def analyze_columns(df):
    """分析每列的类型特征，返回列元信息列表。"""
    cols = []
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            col_type = "empty"
        elif pd.api.types.is_numeric_dtype(s):
            col_type = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            col_type = "datetime"
        else:
            col_type = "unknown"
            # 尝试转换为数值（处理 Excel 读取后 dtype=object 的数值列）
            try:
                converted = pd.to_numeric(s, errors="raise")
                s = converted
                df[col] = converted
                col_type = "numeric"
            except Exception:
                pass

            if col_type != "numeric":
                # 尝试解析日期
                try:
                    pd.to_datetime(s, infer_datetime_format=True)
                    col_type = "datetime"
                except Exception:
                    n_unique = s.nunique()
                    # 判断为 categorical 的条件：唯一值较少 且 占比低于 50%
                    # 如果唯一值占比较高（>50%），即使绝对数量少也视为 text
                    if n_unique <= 20 and (n_unique / len(s)) < 0.5:
                        col_type = "categorical"
                    elif n_unique <= 20:
                        col_type = "categorical"
                    else:
                        col_type = "text"
        cols.append({
            "name": col,
            "type": col_type,
            "non_null": int(s.shape[0]),
            "null_count": int(df[col].isna().sum()),
        })
        if col_type == "numeric":
            cols[-1]["min"] = float(s.min()) if len(s) else None
            cols[-1]["max"] = float(s.max()) if len(s) else None
            cols[-1]["mean"] = float(s.mean()) if len(s) else None
            cols[-1]["median"] = float(s.median()) if len(s) else None
            cols[-1]["std"] = float(s.std()) if len(s) else None
        if col_type == "categorical":
            cols[-1]["n_unique"] = int(s.nunique())
            cols[-1]["top_values"] = s.value_counts().head(10).to_dict()
    return cols


# ── 数据摘要（JSON） ──────────────────────────────────────────────
def build_summary(df, col_infos):
    """生成数据摘要供 LLM 使用。"""
    summary = {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": col_infos,
    }
    # 相关系数矩阵（数值列）
    numeric_cols = [c["name"] for c in col_infos if c["type"] == "numeric"]
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr().round(3)
        summary["correlation"] = corr.to_dict()
    return summary


# ── 智能图表选择 ──────────────────────────────────────────────────
def recommend_charts(col_infos, max_categories=10):
    """根据列特征智能推荐图表类型和对应的列组合。"""
    numeric_cols = [c["name"] for c in col_infos if c["type"] == "numeric"]
    categorical_cols = [c["name"] for c in col_infos if c["type"] == "categorical"]
    datetime_cols = [c["name"] for c in col_infos if c["type"] == "datetime"]

    charts = []

    # 1. 折线图：日期列 + 数值列
    if datetime_cols and numeric_cols:
        for dt in datetime_cols[:1]:
            for nc in numeric_cols[:6]:
                charts.append({"type": "line", "x": dt, "y": nc, "reason": "时间趋势"})

    # 2. 柱状图：分类列 + 数值列
    if categorical_cols and numeric_cols:
        for cc in categorical_cols[:2]:
            cat_unique = 0
            for c in col_infos:
                if c["name"] == cc:
                    cat_unique = c.get("n_unique", 0)
                    break
            if cat_unique <= max_categories:
                for nc in numeric_cols[:4]:
                    charts.append({"type": "bar", "x": cc, "y": nc, "reason": "分类对比"})

    # 3. 饼图 / 环形图：分类列分布
    if categorical_cols:
        for cc in categorical_cols[:2]:
            for c in col_infos:
                if c["name"] == cc:
                    cat_unique = c.get("n_unique", 0)
                    break
            else:
                cat_unique = 0
            if 2 <= cat_unique <= 8:
                charts.append({"type": "pie", "x": cc, "reason": "分类占比"})
                charts.append({"type": "donut", "x": cc, "reason": "分类占比(环形)"})

    # 4. 热力图：数值列相关性
    if len(numeric_cols) >= 2:
        charts.append({"type": "heatmap", "reason": "数值相关性"})

    # 5. 散点图：两个数值列
    if len(numeric_cols) >= 2:
        charts.append({"type": "scatter", "x": numeric_cols[0], "y": numeric_cols[1], "reason": "数值分布关系"})

    # 6. 直方图：单个数值列分布
    for nc in numeric_cols[:3]:
        charts.append({"type": "histogram", "y": nc, "reason": "数值分布"})

    # 7. 箱线图：分类 + 数值
    if categorical_cols and numeric_cols:
        for cc in categorical_cols[:1]:
            for nc in numeric_cols[:2]:
                charts.append({"type": "box", "x": cc, "y": nc, "reason": "分组分布"})

    # 8. 面积图：日期 + 数值
    if datetime_cols and numeric_cols:
        for nc in numeric_cols[:2]:
            charts.append({"type": "area", "x": datetime_cols[0], "y": nc, "reason": "趋势面积"})

    return charts


# ── 绘图函数 ──────────────────────────────────────────────────────
def _save_fig(fig, output_dir, filename):
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=fig.dpi or 150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_line(df, x_col, y_col, title="", output_dir=".", dpi=150):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df[x_col], df[y_col], marker="o", markersize=3, linewidth=1.5)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{y_col} 趋势图")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"line_{x_col}_{y_col}.png")


def plot_bar(df, x_col, y_col, title="", output_dir=".", dpi=150):
    fig, ax = plt.subplots(figsize=(10, 5))
    agg = df.groupby(x_col)[y_col].sum().sort_values(ascending=False)
    ax.bar(agg.index.astype(str), agg.values, color=sns.color_palette("muted", len(agg)))
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{y_col} 按类别汇总")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"bar_{x_col}_{y_col}.png")


def plot_pie(df, col, title="", output_dir=".", dpi=150, donut=False):
    fig, ax = plt.subplots(figsize=(8, 8))
    counts = df[col].value_counts()
    colors = sns.color_palette("Set2", len(counts))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index.astype(str),
        autopct="%1.1f%%", colors=colors,
        pctdistance=0.85 if donut else 0.6,
        startangle=90,
    )
    if donut:
        centre_circle = plt.Circle((0, 0), 0.55, fc="white")
        ax.add_artist(centre_circle)
    kind = "环形" if donut else "饼"
    ax.set_title(title or f"{col} {kind}图")
    fig.tight_layout()
    suffix = "donut" if donut else "pie"
    return _save_fig(fig, output_dir, f"{suffix}_{col}.png")


def plot_heatmap(df, numeric_cols, title="", output_dir=".", dpi=150, cmap="YlOrRd"):
    if len(numeric_cols) < 2:
        return None
    corr = df[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=(max(8, len(numeric_cols)), max(6, len(numeric_cols) * 0.8)))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap=cmap, ax=ax,
                linewidths=0.5, vmin=-1, vmax=1)
    ax.set_title(title or "数值列相关性热力图")
    fig.tight_layout()
    return _save_fig(fig, output_dir, "heatmap_correlation.png")


def plot_scatter(df, x_col, y_col, title="", output_dir=".", dpi=150):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df[x_col], df[y_col], alpha=0.6, edgecolors="k", linewidths=0.3)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{x_col} vs {y_col}")
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"scatter_{x_col}_{y_col}.png")


def plot_histogram(df, col, title="", output_dir=".", dpi=150):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df[col].dropna(), bins=30, color="steelblue", edgecolor="white", alpha=0.85)
    ax.set_xlabel(col)
    ax.set_ylabel("频次")
    ax.set_title(title or f"{col} 分布直方图")
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"histogram_{col}.png")


def plot_box(df, x_col, y_col, title="", output_dir=".", dpi=150):
    fig, ax = plt.subplots(figsize=(10, 5))
    order = df[x_col].value_counts().index.tolist()[:15]
    sns.boxplot(data=df, x=x_col, y=y_col, order=order, ax=ax)
    ax.set_title(title or f"{y_col} 按 {x_col} 箱线图")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"box_{x_col}_{y_col}.png")


def plot_area(df, x_col, y_col, title="", output_dir=".", dpi=150):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(df[x_col], df[y_col], alpha=0.4, color="steelblue")
    ax.plot(df[x_col], df[y_col], color="steelblue", linewidth=1.5)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(title or f"{y_col} 面积图")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return _save_fig(fig, output_dir, f"area_{x_col}_{y_col}.png")


# ── 主流程 ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Excel 数据可视化分析")
    parser.add_argument("filepath", help="Excel/CSV 文件路径")
    parser.add_argument("--output-dir", default="./viz_output", help="输出目录")
    parser.add_argument("--sheet", default=None, help="工作表名")
    parser.add_argument("--sheet-index", type=int, default=0, help="工作表索引")
    parser.add_argument("--no-auto", action="store_true", help="仅输出数据摘要，不生成图表")
    parser.add_argument("--charts", default=None, help="指定图表类型，逗号分隔")
    parser.add_argument("--max-categories", type=int, default=10, help="分类列最大类别数")
    parser.add_argument("--dpi", type=int, default=150, help="图片DPI")
    parser.add_argument("--style", default="seaborn-v0_8-whitegrid", help="matplotlib样式")
    parser.add_argument("--title", default=None, help="自定义总标题")
    parser.add_argument("--font-family", default=None, help="字体")
    parser.add_argument("--cmap", default="YlOrRd", help="热力图色系")
    args = parser.parse_args()

    # 配置样式（先设置样式，再覆盖字体，避免 style.use 覆盖中文字体配置）
    try:
        plt.style.use(args.style)
    except Exception:
        pass
    _configure_chinese_fonts(args.font_family)

    # 读取数据
    filepath = args.filepath
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在 - {filepath}", file=sys.stderr)
        sys.exit(1)

    sheets = list_sheets(filepath)
    if len(sheets) > 1:
        print(f"工作表列表: {sheets}")

    df = read_data(filepath, sheet=args.sheet, sheet_index=args.sheet_index)
    print(f"已读取: {filepath} ({df.shape[0]} 行 × {df.shape[1]} 列)")

    # 列分析
    col_infos = analyze_columns(df)

    # 输出摘要 JSON
    summary = build_summary(df, col_infos)
    os.makedirs(args.output_dir, exist_ok=True)
    summary_path = os.path.join(args.output_dir, "data_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    print(f"数据摘要已保存: {summary_path}")

    if args.no_auto:
        print("仅输出摘要模式，跳过图表生成。")
        return

    # 智能推荐图表
    recommended = recommend_charts(col_infos, args.max_categories)

    # 如果用户指定了图表类型，进行过滤
    if args.charts:
        allowed = set(args.charts.split(","))
        recommended = [r for r in recommended if r["type"] in allowed]

    if not recommended:
        print("未找到适合的可视化组合，请检查数据内容。")
        return

    print(f"计划生成 {len(recommended)} 张图表...")

    # 生成图表
    generated = []
    numeric_cols = [c["name"] for c in col_infos if c["type"] == "numeric"]

    for i, chart in enumerate(recommended):
        ct = chart["type"]
        try:
            if ct == "line":
                path = plot_line(df, chart["x"], chart["y"], output_dir=args.output_dir, dpi=args.dpi)
            elif ct == "bar":
                path = plot_bar(df, chart["x"], chart["y"], output_dir=args.output_dir, dpi=args.dpi)
            elif ct == "pie":
                path = plot_pie(df, chart["x"], output_dir=args.output_dir, dpi=args.dpi, donut=False)
            elif ct == "donut":
                path = plot_pie(df, chart["x"], output_dir=args.output_dir, dpi=args.dpi, donut=True)
            elif ct == "heatmap":
                path = plot_heatmap(df, numeric_cols, output_dir=args.output_dir, dpi=args.dpi, cmap=args.cmap)
            elif ct == "scatter":
                path = plot_scatter(df, chart["x"], chart["y"], output_dir=args.output_dir, dpi=args.dpi)
            elif ct == "histogram":
                path = plot_histogram(df, chart["y"], output_dir=args.output_dir, dpi=args.dpi)
            elif ct == "box":
                path = plot_box(df, chart["x"], chart["y"], output_dir=args.output_dir, dpi=args.dpi)
            elif ct == "area":
                path = plot_area(df, chart["x"], chart["y"], output_dir=args.output_dir, dpi=args.dpi)
            else:
                continue
            if path:
                generated.append({"chart": ct, "reason": chart.get("reason", ""), "path": path})
                print(f"  [{i+1}/{len(recommended)}] {ct}: {path}")
        except Exception as e:
            print(f"  [{i+1}/{len(recommended)}] {ct}: 生成失败 - {e}", file=sys.stderr)

    # 输出生成结果汇总
    result = {
        "source_file": filepath,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "generated_charts": generated,
        "summary_file": summary_path,
    }
    result_path = os.path.join(args.output_dir, "viz_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完成! 共生成 {len(generated)} 张图表。结果: {result_path}")


if __name__ == "__main__":
    main()
