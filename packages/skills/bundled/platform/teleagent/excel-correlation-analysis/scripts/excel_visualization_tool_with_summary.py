from __future__ import annotations

import html
import io
import json
import math
import os
import socket
import threading
import webbrowser
from collections import OrderedDict
from typing import Any

try:
    import numpy as np
    import pandas as pd
    from flask import Flask, request, render_template_string
except ImportError as exc:
    raise SystemExit(
        "缺少运行依赖。请在终端中执行：\n"
        "pip install flask pandas numpy openpyxl\n\n"
        f"原始错误：{exc}"
    ) from exc

import argparse


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--dictionary", "-d",
        type=str,
        default="",
        help="预加载数据字典文件路径（.xlsx/.xls），设置后浏览器端无需再上传字典",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=0,
        help=f"端口号（默认 {PORT}）",
    )
    return parser.parse_args()


APP_TITLE = "Excel 字段可视化分析工具"
HOST = "127.0.0.1"
PORT = int(os.getenv("EXCEL_VIS_PORT", "5000"))
AUTO_OPEN_BROWSER = os.getenv("EXCEL_VIS_AUTO_OPEN", "1") != "0"
MAX_CATEGORICAL_VALUES = 30
PIE_TOP_N = 10
HISTOGRAM_BINS = 10
MIN_HISTOGRAM_BINS = 1
MAX_HISTOGRAM_BINS = 100
LONG_LABEL_WEIGHT = 20
NULL_LABEL = "NULL"

REQUIRED_DICTIONARY_COLUMNS = {
    "字段分类",
    "类别个数",
    "关联度",
    "数值标签",
    "字段名",
    "字段说明",
}

COLORS = [
    "#2563eb",
    "#0891b2",
    "#0d9488",
    "#65a30d",
    "#ca8a04",
    "#ea580c",
    "#dc2626",
    "#db2777",
    "#9333ea",
    "#4f46e5",
    "#64748b",
]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024


def read_first_sheet(uploaded_file: Any) -> pd.DataFrame:
    """读取上传工作簿的第一个工作表。"""
    raw = uploaded_file.read()
    if not raw:
        raise ValueError(f"文件“{uploaded_file.filename}”为空。")
    return pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=object)


def json_for_script(value: Any) -> str:
    """生成可安全嵌入 script 标签的 JSON。"""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def scalar_to_text(value: Any) -> str:
    if pd.isna(value):
        return NULL_LABEL
    if isinstance(value, pd.Timestamp):
        return value.isoformat(sep=" ")
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        number = float(value)
        if math.isfinite(number) and number.is_integer():
            return str(int(number))
        return f"{number:g}"
    return str(value).strip()


def weighted_length(text: str) -> int:
    """ASCII 按1个字符、非ASCII（如中文）按2个字符计算。"""
    return sum(1 if ord(char) < 128 else 2 for char in text)


def make_label_map(labels: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    serial = 1
    for label in labels:
        if label != NULL_LABEL and weighted_length(label) > LONG_LABEL_WEIGHT:
            result[label] = f"编号{serial}"
            serial += 1
    return result


def category_counts(series: pd.Series, include_null: bool) -> list[tuple[str, int]]:
    texts = series.map(scalar_to_text)
    if not include_null:
        texts = texts[texts != NULL_LABEL]
    counts = texts.value_counts(dropna=False, sort=True)
    return [(str(label), int(count)) for label, count in counts.items()]


def table_rows(
    counts: list[tuple[str, int]],
    denominator: int,
    label_map: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "code": label_map.get(label, ""),
            "label": label,
            "count": count,
            "percent": (count / denominator * 100) if denominator else 0,
        }
        for label, count in counts
    ]


def pie_trace_and_layout(
    counts: list[tuple[str, int]],
    denominator: int,
    label_map: dict[str, str],
    title: str,
) -> dict[str, Any] | None:
    if not counts or denominator <= 0:
        return None

    top = counts[:PIE_TOP_N]
    other_count = sum(count for _, count in counts[PIE_TOP_N:])
    if other_count:
        top = [*top, ("其他", other_count)]

    display_labels = [
        label_map.get(label, label)
        if label not in {NULL_LABEL, "其他"}
        else label
        for label, _ in top
    ]
    original_labels = [label for label, _ in top]
    values = [count for _, count in top]

    return {
        "data": [
            {
                "type": "pie",
                "labels": display_labels,
                "values": values,
                "customdata": original_labels,
                "sort": False,
                "textinfo": "label+percent",
                "textposition": "auto",
                "marker": {"colors": COLORS},
                "hovertemplate": (
                    "类别：%{customdata}<br>"
                    "数量：%{value:,}<br>"
                    "占比：%{percent}<extra></extra>"
                ),
            }
        ],
        "layout": {
            "title": {"text": title, "x": 0.02, "xanchor": "left", "font": {"size": 15}},
            "height": 285,
            "margin": {"l": 20, "r": 20, "t": 48, "b": 20},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"family": "Microsoft YaHei, Arial, sans-serif", "size": 11},
            "showlegend": False,
        },
        "config": {
            "responsive": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    }


def nice_number(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 10000 or (0 < abs_value < 0.001):
        return f"{value:.3e}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def numeric_histogram_payload(
    series: pd.Series,
    title: str,
    histogram_bins: int,
) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce")
    values = numeric.dropna().astype(float).to_numpy()
    total_count = int(len(series))
    valid_count = int(len(values))
    null_count = total_count - valid_count

    if valid_count == 0:
        included_rows = (
            [{"code": "", "label": NULL_LABEL, "count": null_count, "percent": 100.0}]
            if null_count
            else []
        )
        return {
            "with_null": None,
            "without_null": None,
            "table_with_null": included_rows,
            "table_without_null": [],
            "null_count": null_count,
        }

    minimum = float(np.min(values))
    maximum = float(np.max(values))

    if math.isclose(minimum, maximum):
        bin_labels = [nice_number(minimum)]
        bin_counts = [valid_count]
    else:
        edges = np.linspace(minimum, maximum, histogram_bins + 1)
        histogram_counts, _ = np.histogram(values, bins=edges)
        bin_counts = [int(item) for item in histogram_counts]
        bin_labels = []
        for index in range(histogram_bins):
            left_bracket = "[" if index == 0 else "("
            bin_labels.append(
                f"{left_bracket}{nice_number(edges[index])}, "
                f"{nice_number(edges[index + 1])}]"
            )

    def build(include_null: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        labels = list(bin_labels)
        counts = list(bin_counts)
        colors = ["#2563eb"] * len(labels)
        denominator = total_count if include_null else valid_count
        if include_null and null_count:
            labels.append(NULL_LABEL)
            counts.append(null_count)
            colors.append("#94a3b8")
        percentages = [
            (count / denominator * 100) if denominator else 0 for count in counts
        ]
        rows = [
            {
                "code": "",
                "label": label,
                "count": count,
                "percent": percentage,
            }
            for label, count, percentage in zip(labels, counts, percentages)
        ]
        spec = {
            "data": [
                {
                    "type": "bar",
                    "x": labels,
                    "y": percentages,
                    "customdata": counts,
                    "marker": {"color": colors},
                    "hovertemplate": (
                        "区间：%{x}<br>"
                        "数量：%{customdata:,}<br>"
                        "占比：%{y:.2f}%<extra></extra>"
                    ),
                }
            ],
            "layout": {
                "title": {
                    "text": title,
                    "x": 0.02,
                    "xanchor": "left",
                    "font": {"size": 15},
                },
                "height": 285,
                "margin": {"l": 55, "r": 20, "t": 48, "b": 85},
                "paper_bgcolor": "rgba(0,0,0,0)",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "font": {"family": "Microsoft YaHei, Arial, sans-serif", "size": 10},
                "showlegend": False,
                "xaxis": {"tickangle": -35, "automargin": True},
                "yaxis": {"title": "占比", "ticksuffix": "%", "rangemode": "tozero"},
            },
            "config": {
                "responsive": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            },
        }
        return spec, rows

    with_null, table_with_null = build(True)
    without_null, table_without_null = build(False)
    return {
        "with_null": with_null,
        "without_null": without_null,
        "table_with_null": table_with_null,
        "table_without_null": table_without_null,
        "null_count": null_count,
    }


def categorical_payload(
    series: pd.Series,
    title: str,
    create_chart: bool,
) -> dict[str, Any]:
    counts_with_null = category_counts(series, True)
    counts_without_null = category_counts(series, False)
    all_labels = [label for label, _ in counts_with_null]
    label_map = make_label_map(all_labels)
    total = int(len(series))
    non_null_total = sum(count for _, count in counts_without_null)
    null_count = total - non_null_total

    with_null_chart = (
        pie_trace_and_layout(counts_with_null, total, label_map, title)
        if create_chart
        else None
    )
    without_null_chart = (
        pie_trace_and_layout(
            counts_without_null,
            non_null_total,
            label_map,
            f"{title}（排除NULL）",
        )
        if create_chart
        else None
    )
    mapping = [
        {"code": code, "label": label}
        for label, code in label_map.items()
    ]
    return {
        "with_null": with_null_chart,
        "without_null": without_null_chart,
        "table_with_null": table_rows(counts_with_null, total, label_map),
        "table_without_null": table_rows(
            counts_without_null, non_null_total, label_map
        ),
        "mapping": mapping,
        "null_count": null_count,
    }


def normalize_small_integer(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def parse_histogram_bins(value: Any) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("数值字段均分份数必须是整数。") from exc
    if not MIN_HISTOGRAM_BINS <= parsed <= MAX_HISTOGRAM_BINS:
        raise ValueError(
            f"数值字段均分份数必须在 "
            f"{MIN_HISTOGRAM_BINS}–{MAX_HISTOGRAM_BINS} 之间。"
        )
    return parsed


def build_report(
    data: pd.DataFrame,
    dictionary: pd.DataFrame,
    histogram_bins: int = HISTOGRAM_BINS,
) -> dict[str, Any]:
    histogram_bins = parse_histogram_bins(histogram_bins)
    missing_columns = REQUIRED_DICTIONARY_COLUMNS - set(dictionary.columns)
    if missing_columns:
        missing = "、".join(sorted(missing_columns))
        raise ValueError(f"数据字典缺少必要列：{missing}")

    total_rows = int(len(data))
    if total_rows == 0:
        raise ValueError("数据文件没有数据行。")

    groups: OrderedDict[str, OrderedDict[int, list[dict[str, Any]]]] = OrderedDict()
    skipped_high_cardinality: list[dict[str, Any]] = []
    missing_fields: list[str] = []
    drawn_field_count = 0

    for _, dictionary_row in dictionary.iterrows():
        field_name = scalar_to_text(dictionary_row["字段名"])
        field_group = scalar_to_text(dictionary_row["字段分类"])
        description = scalar_to_text(dictionary_row["字段说明"])
        category_type = scalar_to_text(dictionary_row["类别个数"]).lower()
        relevance = normalize_small_integer(dictionary_row["关联度"], 0)
        numeric_label = normalize_small_integer(dictionary_row["数值标签"], 0)

        if relevance == 0:
            continue
        if field_name not in data.columns:
            missing_fields.append(field_name)
            continue

        series = data[field_name]
        actual_non_null_categories = int(series.nunique(dropna=True))

        # 类别数上限只约束非数值标签。
        if numeric_label == 0 and actual_non_null_categories > MAX_CATEGORICAL_VALUES:
            skipped_high_cardinality.append(
                {
                    "field": field_name,
                    "description": description,
                    "categories": actual_non_null_categories,
                }
            )
            continue

        is_small_table = category_type in {"1", "2", "3"}
        if numeric_label == 1 and category_type == "n":
            payload = numeric_histogram_payload(
                series,
                description,
                histogram_bins,
            )
            view_type = "histogram"
        else:
            payload = categorical_payload(
                series,
                description,
                create_chart=not is_small_table,
            )
            view_type = "table" if is_small_table else "pie"

        card_id = f"field-{drawn_field_count}"
        card = {
            "id": card_id,
            "field": field_name,
            "description": description,
            "category_type": category_type,
            "numeric_label": numeric_label,
            "actual_categories": actual_non_null_categories,
            "view_type": view_type,
            **payload,
        }
        groups.setdefault(field_group, OrderedDict()).setdefault(relevance, []).append(card)
        drawn_field_count += 1

    serializable_groups = []
    for group_name, relevance_groups in groups.items():
        sections = []
        for relevance in (3, 2, 1):
            cards = relevance_groups.get(relevance, [])
            if cards:
                sections.append(
                    {
                        "relevance": relevance,
                        "cards": cards,
                    }
                )
        if sections:
            serializable_groups.append(
                {
                    "name": group_name,
                    "field_count": sum(len(section["cards"]) for section in sections),
                    "sections": sections,
                }
            )

    return {
        "total_rows": total_rows,
        "total_columns": int(len(data.columns)),
        "dictionary_fields": int(len(dictionary)),
        "rendered_fields": drawn_field_count,
        "histogram_bins": histogram_bins,
        "skipped_high_cardinality": skipped_high_cardinality,
        "missing_fields": missing_fields,
        "groups": serializable_groups,
    }


BASE_STYLES = """
:root {
  --blue: #2563eb;
  --navy: #0f172a;
  --slate: #475569;
  --line: #dbe4f0;
  --soft: #f5f8fc;
  --white: #ffffff;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #edf2f8;
  color: var(--navy);
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}
.page { width: min(1480px, calc(100% - 32px)); margin: 24px auto 60px; }
.hero {
  padding: 26px 30px;
  border-radius: 18px;
  color: white;
  background: linear-gradient(135deg, #172554, #1d4ed8 65%, #0891b2);
  box-shadow: 0 16px 38px rgba(30, 64, 175, .18);
}
.hero h1 { margin: 0 0 8px; font-size: 26px; }
.hero p { margin: 0; color: #dbeafe; line-height: 1.7; }
.panel {
  margin-top: 18px;
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--white);
  box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
}
.upload-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.file-box {
  padding: 18px;
  border: 1px dashed #94a3b8;
  border-radius: 12px;
  background: #f8fafc;
}
.file-box label { display: block; margin-bottom: 10px; font-weight: 700; }
input[type=file] { width: 100%; }
input[type=number] {
  width: min(220px, 100%);
  padding: 9px 11px;
  border: 1px solid #94a3b8;
  border-radius: 8px;
  background: white;
  color: #0f172a;
  font: inherit;
}
.config-box { grid-column: 1 / -1; }
.actions { display: flex; gap: 12px; align-items: center; margin-top: 20px; }
button, .button {
  border: 0;
  border-radius: 9px;
  padding: 9px 14px;
  background: var(--blue);
  color: white;
  cursor: pointer;
  font: inherit;
}
button:hover, .button:hover { filter: brightness(.95); }
.secondary { background: #e2e8f0; color: #1e293b; }
.muted { color: #64748b; font-size: 13px; line-height: 1.6; }
.error {
  margin-top: 18px;
  padding: 14px 16px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fef2f2;
  color: #b91c1c;
}
.loading {
  display: none;
  align-items: center;
  gap: 9px;
  color: #1d4ed8;
  font-weight: 700;
}
.spinner {
  width: 18px; height: 18px; border: 3px solid #bfdbfe;
  border-top-color: #2563eb; border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 18px; }
.stat {
  padding: 16px 18px; border: 1px solid var(--line); border-radius: 12px;
  background: white;
}
.stat strong { display: block; font-size: 23px; color: #1d4ed8; }
.stat span { color: #64748b; font-size: 13px; }
details.chapter, details.relevance {
  overflow: hidden;
  margin-top: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: white;
}
details.relevance { margin: 14px; border-radius: 10px; background: #f8fafc; }
summary {
  cursor: pointer;
  list-style: none;
  user-select: none;
}
summary::-webkit-details-marker { display: none; }
.chapter > summary {
  padding: 17px 20px;
  color: white;
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(90deg, #1e3a8a, #2563eb);
}
.relevance > summary {
  padding: 13px 16px;
  color: #1e3a8a;
  font-weight: 700;
  background: #eaf2ff;
}
.summary-row { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
.summary-row::after { content: "＋"; font-size: 20px; }
details[open] > summary .summary-row::after { content: "－"; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(430px, 1fr));
  align-items: start;
  gap: 14px;
  padding: 14px;
}
.field-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dbe4f0;
  border-radius: 12px;
  background: white;
  box-shadow: 0 4px 14px rgba(15, 23, 42, .05);
}
.field-head {
  display: flex; justify-content: space-between; gap: 12px; align-items: flex-start;
  padding: 14px 15px 10px;
}
.field-title { margin: 0; font-size: 16px; }
.field-name { margin-top: 4px; color: #64748b; font: 12px Consolas, monospace; word-break: break-all; }
.badges { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
.badge {
  white-space: nowrap; padding: 4px 7px; border-radius: 99px;
  background: #eff6ff; color: #1d4ed8; font-size: 11px;
}
.toolbar { display: flex; gap: 8px; padding: 0 15px 8px; }
.toolbar button { padding: 6px 10px; font-size: 12px; }
.chart { width: 100%; min-height: 285px; }
.chart svg { display: block; width: 100%; height: 285px; }
.chart-legend {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px 12px; padding: 0 15px 12px; font-size: 11px;
}
.legend-item { display: flex; min-width: 0; gap: 6px; align-items: center; }
.legend-dot { flex: 0 0 9px; width: 9px; height: 9px; border-radius: 50%; }
.legend-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chart.empty {
  display: grid; place-items: center; min-height: 120px; color: #94a3b8;
}
.mapping-note {
  margin: 0 15px 10px; padding: 9px 11px; border-radius: 8px;
  background: #fff7ed; color: #9a3412; font-size: 12px;
}
.table-wrap {
  max-height: 280px;
  overflow: auto;
  border-top: 1px solid var(--line);
}
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th {
  position: sticky; top: 0; z-index: 1;
  padding: 9px 10px; background: #f1f5f9; color: #334155; text-align: left;
}
td { padding: 8px 10px; border-top: 1px solid #edf2f7; vertical-align: top; word-break: break-word; }
td.number, th.number { text-align: right; white-space: nowrap; }
.notice { margin-top: 16px; padding: 14px 16px; border-radius: 10px; background: #fff7ed; color: #9a3412; }
.notice details { margin-top: 7px; }
.summary-panel {
  display: none;
  margin-top: 16px;
  padding: 20px;
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 8px 24px rgba(30, 64, 175, .08);
}
.summary-panel.visible { display: block; }
.summary-panel h2 { margin: 0 0 6px; font-size: 20px; color: #1e3a8a; }
.summary-output, .json-output {
  max-height: 520px;
  overflow: auto;
  margin: 14px 0 0;
  padding: 16px;
  border: 1px solid #dbe4f0;
  border-radius: 10px;
  background: #f8fafc;
  color: #1e293b;
  font: 13px/1.85 "Microsoft YaHei", "PingFang SC", sans-serif;
  white-space: pre-wrap;
  word-break: break-word;
}
.json-output {
  display: none;
  font-family: Consolas, "Microsoft YaHei", monospace;
  line-height: 1.6;
}
.summary-status { min-height: 20px; color: #0f766e; font-size: 12px; }
.modal {
  display: none; position: fixed; inset: 0; z-index: 1000;
  padding: 26px; background: rgba(15, 23, 42, .82);
}
.modal.open { display: grid; grid-template-columns: minmax(0, 1fr) minmax(240px, 340px); gap: 14px; }
.modal-main, .modal-side {
  min-height: 0; border-radius: 14px; background: white; overflow: hidden;
}
.modal-main { position: relative; }
.modal-chart { width: 100%; height: calc(100vh - 52px); }
.modal-chart svg { display: block; width: 100%; height: calc(100vh - 52px); }
.modal-chart .chart-legend {
  position: absolute; left: 12px; right: 12px; bottom: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 10px; border-radius: 9px; background: rgba(255,255,255,.92);
}
.modal-close {
  position: absolute; top: 12px; right: 12px; z-index: 4;
  width: 36px; height: 36px; padding: 0; border-radius: 50%;
  background: #0f172a; font-size: 20px;
}
.modal-side { padding: 18px; overflow: auto; }
.modal-side h3 { margin: 0 0 12px; }
.mapping-list { margin: 0; padding: 0; list-style: none; font-size: 13px; }
.mapping-list li { padding: 7px 0; border-bottom: 1px solid #e2e8f0; word-break: break-word; }
@media (max-width: 820px) {
  .upload-grid, .stats, .cards { grid-template-columns: 1fr; }
  .page { width: min(100% - 18px, 1480px); margin-top: 9px; }
  .modal.open { grid-template-columns: 1fr; overflow: auto; }
  .modal-chart { height: 65vh; }
}
"""


UPLOAD_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>{{ styles|safe }}</style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>{{ title }}</h1>
      <p>上传数据文件{{ '（数据字典已预加载）' if preloaded_dictionary else '' }}，系统将在本机完成统计并生成交互式可视化页面。</p>
    </section>
    <section class="panel">
      <form method="post" action="/analyze" enctype="multipart/form-data" id="upload-form">
        <div class="upload-grid">
          <div class="file-box">
            <label for="data_file">① 数据文件</label>
            <input id="data_file" name="data_file" type="file" accept=".xlsx,.xls" required>
            <p class="muted">选择实际数据文件；默认读取第一个工作表。</p>
          </div>
          <div class="file-box" id="dict-box">
            <label for="dictionary_file">② 数据字典</label>
            {% if preloaded_dictionary %}
            <p class="muted" style="margin:0 0 6px">已默认加载：<strong>{{ preloaded_dictionary_filename }}</strong></p>
            <input id="dictionary_file" name="dictionary_file" type="file" accept=".xlsx,.xls">
            <p class="muted">如需更换字典，请选择新文件；不选则使用默认加载的字典。</p>
            <input type="hidden" name="use_preloaded_dictionary" id="use_preloaded_flag" value="1">
            {% else %}
            <input id="dictionary_file" name="dictionary_file" type="file" accept=".xlsx,.xls" required>
            <p class="muted">需包含字段分类、类别个数、关联度、数值标签等列。</p>
            {% endif %}
          </div>
          <div class="file-box config-box">
            <label for="histogram_bins">③ 数值字段均分份数</label>
            <input
              id="histogram_bins"
              name="histogram_bins"
              type="number"
              min="{{ min_histogram_bins }}"
              max="{{ max_histogram_bins }}"
              step="1"
              value="{{ histogram_bins }}"
              required
            >
            <p class="muted">
              默认10份，可输入 {{ min_histogram_bins }}–{{ max_histogram_bins }} 之间的整数。
              数值完全相同时只生成一个有效区间。
            </p>
          </div>
        </div>
        <div class="actions">
          <button type="submit" id="submit-button">生成可视化</button>
          <div class="loading" id="loading">
            <span class="spinner"></span>
            正在读取和统计，请稍候……
          </div>
        </div>
      </form>
      {% if error %}<div class="error">{{ error }}</div>{% endif %}
      <p class="muted">
        规则：关联度0不展示；非数值字段的实际非空类别数超过
        {{ max_categories }} 时跳过；NULL默认计入占比，可在结果中切换排除。
      </p>
    </section>
  </main>
  <script>
    var dictInput = document.getElementById("dictionary_file");
    var preloadedFlag = document.getElementById("use_preloaded_flag");
    if (dictInput && preloadedFlag) {
      dictInput.addEventListener("change", function() {
        preloadedFlag.value = this.files && this.files.length > 0 ? "0" : "1";
      });
    }
    document.getElementById("upload-form").addEventListener("submit", function () {
      document.getElementById("submit-button").disabled = true;
      document.getElementById("loading").style.display = "flex";
    });
  </script>
</body>
</html>
"""


REPORT_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} - 分析结果</title>
  <style>{{ styles|safe }}</style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>字段可视化分析结果</h1>
      <p>点击章节标题可展开或折叠；双击图表或点击“查看大图”可放大。</p>
    </section>

    <section class="stats">
      <div class="stat"><strong>{{ report.total_rows }}</strong><span>数据行数</span></div>
      <div class="stat"><strong>{{ report.total_columns }}</strong><span>数据字段数</span></div>
      <div class="stat"><strong>{{ report.rendered_fields }}</strong><span>本次展示字段</span></div>
      <div class="stat"><strong>{{ report.skipped_high_cardinality|length }}</strong><span>高类别字段已跳过</span></div>
    </section>

    <div class="actions">
      <a class="button secondary" href="/">重新选择文件</a>
      <button type="button" class="secondary" onclick="setAllDetails(true)">全部展开</button>
      <button type="button" class="secondary" onclick="setAllDetails(false)">全部折叠</button>
      <button type="button" id="generate-summary">生成文字总结 / JSON</button>
      <span class="badge">数值字段均分：{{ report.histogram_bins }} 份</span>
    </div>

    <section class="summary-panel" id="summary-panel">
      <h2>字段分布总结</h2>
      <p class="muted">根据当前页面的NULL设置生成；关联度0及超过30类的非数值字段不会进入总结。</p>
      <div class="actions">
        <button type="button" class="secondary" id="show-summary-text">查看文字总结</button>
        <button type="button" class="secondary" id="show-summary-json">查看 JSON</button>
        <button type="button" class="secondary" id="copy-summary">复制当前内容</button>
        <button type="button" class="secondary" id="download-summary-json">下载 JSON</button>
      </div>
      <div class="summary-status" id="summary-status"></div>
      <div class="summary-output" id="summary-output"></div>
      <pre class="json-output" id="json-output"></pre>
    </section>

    {% if report.skipped_high_cardinality %}
    <div class="notice">
      已跳过 {{ report.skipped_high_cardinality|length }} 个实际非空类别数超过
      {{ max_categories }} 的非数值字段。
      <details>
        <summary>查看跳过明细</summary>
        <ul>
        {% for item in report.skipped_high_cardinality %}
          <li>{{ item.description }}（{{ item.field }}）：{{ item.categories }} 类</li>
        {% endfor %}
        </ul>
      </details>
    </div>
    {% endif %}

    {% if report.missing_fields %}
    <div class="notice">
      数据文件中缺少 {{ report.missing_fields|length }} 个字典字段，已自动跳过。
      <details>
        <summary>查看缺失字段</summary>
        <p>{{ report.missing_fields|join("、") }}</p>
      </details>
    </div>
    {% endif %}

    {% for group in report.groups %}
    <details class="chapter">
      <summary><span class="summary-row"><span>{{ group.name }}</span><small>{{ group.field_count }} 个字段</small></span></summary>
      {% for section in group.sections %}
      <details class="relevance">
        <summary><span class="summary-row"><span>关联度 {{ section.relevance }}</span><small>{{ section.cards|length }} 个字段</small></span></summary>
        <div class="cards">
          {% for card in section.cards %}
          <article class="field-card" id="{{ card.id }}">
            <header class="field-head">
              <div>
                <h3 class="field-title">{{ card.description }}</h3>
                <div class="field-name">{{ card.field }}</div>
              </div>
              <div class="badges">
                <span class="badge">字典类别：{{ card.category_type }}</span>
                <span class="badge">实际类别：{{ card.actual_categories }}</span>
                <span class="badge">
                  {% if card.view_type == "histogram" %}等宽柱状图
                  {% elif card.view_type == "pie" %}饼图
                  {% else %}百分比表{% endif %}
                </span>
              </div>
            </header>
            <div class="toolbar">
              {% if card.null_count > 0 %}
              <button type="button" class="secondary null-toggle" data-card="{{ card.id }}">排除 NULL</button>
              {% endif %}
              {% if card.with_null or card.without_null %}
              <button type="button" class="secondary expand-chart" data-card="{{ card.id }}">查看大图</button>
              {% endif %}
            </div>
            {% if card.mapping %}
            <div class="mapping-note">图中长类别已用编号代替；表格及大图右侧可查看完整对照。</div>
            {% endif %}
            {% if card.with_null or card.without_null %}
            <div class="chart" id="chart-{{ card.id }}" data-card="{{ card.id }}" title="双击查看大图"></div>
            {% elif card.view_type == "histogram" %}
            <div class="chart empty">没有可用于数值统计的数据</div>
            {% endif %}
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th style="width:78px">编号</th>
                    <th>{% if card.view_type == "histogram" %}数值区间{% else %}类别{% endif %}</th>
                    <th class="number">数量</th>
                    <th class="number">百分比</th>
                  </tr>
                </thead>
                <tbody id="table-{{ card.id }}"></tbody>
              </table>
            </div>
          </article>
          {% endfor %}
        </div>
      </details>
      {% endfor %}
    </details>
    {% endfor %}

    {% if not report.groups %}
    <section class="panel">
      <p>没有符合展示规则的字段。请检查数据文件与数据字典是否匹配。</p>
    </section>
    {% endif %}
  </main>

  <div class="modal" id="chart-modal">
    <div class="modal-main">
      <button type="button" class="modal-close" aria-label="关闭">×</button>
      <div class="modal-chart" id="modal-chart"></div>
    </div>
    <aside class="modal-side">
      <h3 id="modal-title">类别对照</h3>
      <ul class="mapping-list" id="modal-mapping"></ul>
    </aside>
  </div>

  <script id="report-data" type="application/json">{{ report_json|safe }}</script>
  <script>
    const report = JSON.parse(document.getElementById("report-data").textContent);
    const cards = {};
    report.groups.forEach(group => {
      group.sections.forEach(section => {
        section.cards.forEach(card => {
          cards[card.id] = card;
          card.excludeNull = false;
        });
      });
    });

    function escapeText(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function activeSpec(card) {
      return card.excludeNull ? card.without_null : card.with_null;
    }

    function activeRows(card) {
      return card.excludeNull ? card.table_without_null : card.table_with_null;
    }

    const chartColors = [
      "#2563eb", "#0891b2", "#0d9488", "#65a30d", "#ca8a04", "#ea580c",
      "#dc2626", "#db2777", "#9333ea", "#4f46e5", "#64748b"
    ];

    function polarPoint(cx, cy, radius, angle) {
      const radians = (angle - 90) * Math.PI / 180;
      return [cx + radius * Math.cos(radians), cy + radius * Math.sin(radians)];
    }

    function piePath(cx, cy, radius, startAngle, endAngle) {
      const start = polarPoint(cx, cy, radius, endAngle);
      const end = polarPoint(cx, cy, radius, startAngle);
      const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
      return `M ${cx} ${cy} L ${start[0]} ${start[1]} A ${radius} ${radius} 0 ${largeArc} 0 ${end[0]} ${end[1]} Z`;
    }

    function drawPie(target, spec, large) {
      const trace = spec.data[0];
      const total = trace.values.reduce((sum, value) => sum + Number(value), 0);
      const width = large ? 900 : 500;
      const height = large ? 620 : 285;
      const cx = large ? 360 : 190;
      const cy = large ? 280 : 145;
      const radius = large ? 205 : 100;
      let angle = 0;
      const slices = trace.values.map((rawValue, index) => {
        const value = Number(rawValue);
        const sweep = total ? value / total * 360 : 0;
        const color = chartColors[index % chartColors.length];
        const label = trace.customdata[index];
        const percent = total ? value / total * 100 : 0;
        let shape;
        if (sweep >= 359.999) {
          shape = `<circle cx="${cx}" cy="${cy}" r="${radius}" fill="${color}">`;
        } else {
          shape = `<path d="${piePath(cx, cy, radius, angle, angle + sweep)}" fill="${color}" stroke="#fff" stroke-width="2">`;
        }
        angle += sweep;
        return `${shape}<title>${escapeText(label)}：${value.toLocaleString("zh-CN")}（${percent.toFixed(2)}%）</title>${sweep >= 359.999 ? "</circle>" : "</path>"}`;
      }).join("");
      const legend = trace.labels.map((label, index) => {
        const value = Number(trace.values[index]);
        const percent = total ? value / total * 100 : 0;
        return `<div class="legend-item" title="${escapeText(trace.customdata[index])}">
          <span class="legend-dot" style="background:${chartColors[index % chartColors.length]}"></span>
          <span class="legend-text">${escapeText(label)} ${percent.toFixed(1)}%</span>
        </div>`;
      }).join("");
      target.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="饼图">
          <text x="18" y="24" font-size="${large ? 20 : 13}" font-weight="700" fill="#0f172a">${escapeText(spec.layout.title.text)}</text>
          ${slices}
          <text x="${cx}" y="${cy - 3}" text-anchor="middle" font-size="${large ? 24 : 15}" font-weight="700" fill="#0f172a">${total.toLocaleString("zh-CN")}</text>
          <text x="${cx}" y="${cy + (large ? 25 : 17)}" text-anchor="middle" font-size="${large ? 15 : 11}" fill="#64748b">总数</text>
        </svg>
        <div class="chart-legend">${legend}</div>`;
    }

    function drawBar(target, spec, large) {
      const trace = spec.data[0];
      const width = large ? 1000 : 620;
      const height = large ? 650 : 300;
      const margin = {left: 62, right: 20, top: large ? 62 : 42, bottom: large ? 125 : 105};
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      const maxValue = Math.max(1, ...trace.y.map(Number));
      const axisMax = Math.ceil(maxValue / 10) * 10 || 10;
      const slot = plotWidth / Math.max(trace.x.length, 1);
      const barWidth = Math.max(8, slot * 0.68);
      let grid = "";
      for (let tick = 0; tick <= 4; tick++) {
        const percent = axisMax * tick / 4;
        const y = margin.top + plotHeight - plotHeight * tick / 4;
        grid += `<line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="#e2e8f0"/>
          <text x="${margin.left - 8}" y="${y + 4}" text-anchor="end" font-size="${large ? 13 : 10}" fill="#64748b">${percent.toFixed(0)}%</text>`;
      }
      const bars = trace.x.map((label, index) => {
        const value = Number(trace.y[index]);
        const count = Number(trace.customdata[index]);
        const x = margin.left + slot * index + (slot - barWidth) / 2;
        const barHeight = value / axisMax * plotHeight;
        const y = margin.top + plotHeight - barHeight;
        const markerColors = Array.isArray(trace.marker.color)
          ? trace.marker.color
          : (trace.marker.colors || []);
        const color = markerColors[index] || "#2563eb";
        const labelX = margin.left + slot * index + slot / 2;
        const labelY = margin.top + plotHeight + 12;
        return `<rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="2" fill="${color}">
            <title>${escapeText(label)}：${count.toLocaleString("zh-CN")}（${value.toFixed(2)}%）</title>
          </rect>
          <text x="${labelX}" y="${labelY}" transform="rotate(-38 ${labelX} ${labelY})"
            text-anchor="end" font-size="${large ? 12 : 9}" fill="#475569">${escapeText(label)}</text>`;
      }).join("");
      target.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="柱状图">
          <text x="18" y="${large ? 30 : 22}" font-size="${large ? 20 : 13}" font-weight="700" fill="#0f172a">${escapeText(spec.layout.title.text)}</text>
          ${grid}
          <line x1="${margin.left}" y1="${margin.top + plotHeight}" x2="${width - margin.right}" y2="${margin.top + plotHeight}" stroke="#94a3b8"/>
          ${bars}
        </svg>`;
    }

    function drawChart(target, spec, large=false) {
      if (spec.data[0].type === "pie") drawPie(target, spec, large);
      else drawBar(target, spec, large);
    }

    function renderTable(card) {
      const body = document.getElementById("table-" + card.id);
      const rows = activeRows(card);
      if (!rows.length) {
        body.innerHTML = '<tr><td colspan="4" class="muted">排除NULL后没有数据</td></tr>';
        return;
      }
      body.innerHTML = rows.map(row => `
        <tr>
          <td>${escapeText(row.code || "")}</td>
          <td title="${escapeText(row.label)}">${escapeText(row.label)}</td>
          <td class="number">${Number(row.count).toLocaleString("zh-CN")}</td>
          <td class="number">${Number(row.percent).toFixed(2)}%</td>
        </tr>
      `).join("");
    }

    function renderChart(card) {
      const target = document.getElementById("chart-" + card.id);
      if (!target) return;
      const spec = activeSpec(card);
      if (!spec) {
        target.innerHTML = "";
        target.classList.add("empty");
        target.textContent = "排除NULL后没有可展示的数据";
        return;
      }
      target.classList.remove("empty");
      drawChart(target, spec, false);
    }

    function renderCard(card) {
      renderChart(card);
      renderTable(card);
    }

    Object.values(cards).forEach(renderCard);

    let generatedSummaryText = "";
    let generatedSummaryJson = null;
    let summaryView = "text";

    function statisticTypeText(card) {
      if (card.view_type === "histogram") return "等宽区间柱状分布";
      if (card.view_type === "pie") return "分类占比分布";
      return "分类百分比表";
    }

    function buildSummaryData() {
      const fields = [];
      const textLines = [
        `数据分布总结（共 ${report.total_rows.toLocaleString("zh-CN")} 条数据）`,
        ""
      ];

      report.groups.forEach(group => {
        textLines.push(`【${group.name}】`);
        group.sections.forEach(section => {
          textLines.push(`关联度 ${section.relevance}：`);
          section.cards.forEach(card => {
            const rows = activeRows(card);
            const total = rows.reduce((sum, row) => sum + Number(row.count), 0);
            const distribution = rows.map(row => ({
              "编号": row.code || "",
              "类别或区间": row.label,
              "数量": Number(row.count),
              "占比": `${Number(row.percent).toFixed(2)}%`,
              "占比数值": Number(Number(row.percent).toFixed(6))
            }));
            fields.push({
              "字段分类": group.name,
              "关联度": section.relevance,
              "字段中文名": card.description,
              "字段名": card.field,
              "统计方式": statisticTypeText(card),
              "NULL处理": card.excludeNull ? "已排除NULL并重新计算占比" : "NULL计入总数",
              "统计总数": total,
              "实际非空类别数": card.actual_categories,
              "分布": distribution
            });

            if (!rows.length || total === 0) {
              textLines.push(`  · ${card.description}：当前没有可统计的数据。`);
              return;
            }
            const leadingRows = [...rows]
              .sort((left, right) => Number(right.percent) - Number(left.percent))
              .slice(0, 3);
            const descriptions = leadingRows.map(row =>
              `${row.label}占${Number(row.percent).toFixed(2)}%（${Number(row.count).toLocaleString("zh-CN")}条）`
            );
            const prefix = card.view_type === "histogram" ? "数值主要分布为" : "占比较高的类别为";
            const nullNote = card.excludeNull ? "，统计时已排除NULL" : "";
            textLines.push(`  · ${card.description}：${prefix}${descriptions.join("、")}${nullNote}。`);
          });
        });
        textLines.push("");
      });

      return {
        text: textLines.join("\\n").trim(),
        json: {
          "报告名称": "Excel字段分布总结",
          "数据行数": report.total_rows,
          "数据字段数": report.total_columns,
          "输出字段数": fields.length,
          "规则说明": {
            "关联度0": "不输出",
            "高类别非数值字段": `实际非空类别数超过 {{ max_categories }} 时不输出`,
            "饼图": `展示前 {{ pie_top_n }} 类，其余合并为其他；JSON保留完整分布`,
            "数值字段": `按 {{ histogram_bins }} 个等宽区间统计`
          },
          "字段统计": fields
        }
      };
    }

    function setSummaryView(view) {
      summaryView = view;
      document.getElementById("summary-output").style.display = view === "text" ? "block" : "none";
      document.getElementById("json-output").style.display = view === "json" ? "block" : "none";
    }

    function generateSummary() {
      const generated = buildSummaryData();
      generatedSummaryText = generated.text;
      generatedSummaryJson = generated.json;
      document.getElementById("summary-output").textContent = generatedSummaryText;
      document.getElementById("json-output").textContent = JSON.stringify(generatedSummaryJson, null, 2);
      document.getElementById("summary-panel").classList.add("visible");
      document.getElementById("summary-status").textContent =
        `已生成 ${generatedSummaryJson["输出字段数"]} 个字段的总结。`;
      setSummaryView("text");
      document.getElementById("summary-panel").scrollIntoView({behavior: "smooth", block: "start"});
    }

    async function copyCurrentSummary() {
      if (!generatedSummaryJson) generateSummary();
      const content = summaryView === "json"
        ? JSON.stringify(generatedSummaryJson, null, 2)
        : generatedSummaryText;
      try {
        await navigator.clipboard.writeText(content);
        document.getElementById("summary-status").textContent = "当前内容已复制到剪贴板。";
      } catch (_) {
        const helper = document.createElement("textarea");
        helper.value = content;
        helper.style.position = "fixed";
        helper.style.opacity = "0";
        document.body.appendChild(helper);
        helper.select();
        document.execCommand("copy");
        helper.remove();
        document.getElementById("summary-status").textContent = "当前内容已复制到剪贴板。";
      }
    }

    function downloadSummaryJson() {
      if (!generatedSummaryJson) generateSummary();
      const blob = new Blob(
        [JSON.stringify(generatedSummaryJson, null, 2)],
        {type: "application/json;charset=utf-8"}
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const now = new Date();
      const stamp = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0"),
        "_",
        String(now.getHours()).padStart(2, "0"),
        String(now.getMinutes()).padStart(2, "0"),
        String(now.getSeconds()).padStart(2, "0")
      ].join("");
      link.href = url;
      link.download = `字段占比总结_${stamp}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      document.getElementById("summary-status").textContent = "JSON文件已生成并开始下载。";
    }

    document.getElementById("generate-summary").addEventListener("click", generateSummary);
    document.getElementById("show-summary-text").addEventListener("click", () => setSummaryView("text"));
    document.getElementById("show-summary-json").addEventListener("click", () => setSummaryView("json"));
    document.getElementById("copy-summary").addEventListener("click", copyCurrentSummary);
    document.getElementById("download-summary-json").addEventListener("click", downloadSummaryJson);

    document.querySelectorAll(".null-toggle").forEach(button => {
      button.addEventListener("click", () => {
        const card = cards[button.dataset.card];
        card.excludeNull = !card.excludeNull;
        button.textContent = card.excludeNull ? "计入 NULL" : "排除 NULL";
        renderCard(card);
        if (document.getElementById("summary-panel").classList.contains("visible")) {
          generatedSummaryText = "";
          generatedSummaryJson = null;
          document.getElementById("summary-status").textContent =
            "NULL设置已改变，请重新点击“生成文字总结 / JSON”。";
        }
      });
    });

    const modal = document.getElementById("chart-modal");
    const modalChart = document.getElementById("modal-chart");
    const modalMapping = document.getElementById("modal-mapping");
    const modalTitle = document.getElementById("modal-title");

    function openModal(cardId) {
      const card = cards[cardId];
      const spec = activeSpec(card);
      if (!spec) return;
      modal.classList.add("open");
      document.body.style.overflow = "hidden";
      const largeSpec = JSON.parse(JSON.stringify(spec));
      largeSpec.layout.title.text = card.description + (card.excludeNull ? "（排除NULL）" : "");
      drawChart(modalChart, largeSpec, true);
      modalTitle.textContent = card.mapping && card.mapping.length ? "编号—完整类别对照" : "字段信息";
      if (card.mapping && card.mapping.length) {
        modalMapping.innerHTML = card.mapping.map(item =>
          `<li><strong>${escapeText(item.code)}</strong>：${escapeText(item.label)}</li>`
        ).join("");
      } else {
        modalMapping.innerHTML = `
          <li><strong>字段说明：</strong>${escapeText(card.description)}</li>
          <li><strong>字段名：</strong>${escapeText(card.field)}</li>
          <li><strong>实际非空类别数：</strong>${card.actual_categories}</li>
          <li><strong>NULL数量：</strong>${card.null_count}</li>
        `;
      }
    }

    function closeModal() {
      modal.classList.remove("open");
      document.body.style.overflow = "";
      modalChart.innerHTML = "";
    }

    document.querySelectorAll(".expand-chart").forEach(button => {
      button.addEventListener("click", () => openModal(button.dataset.card));
    });
    document.querySelectorAll(".chart[data-card]").forEach(chart => {
      chart.addEventListener("dblclick", event => {
        event.preventDefault();
        openModal(chart.dataset.card);
      });
    });
    document.querySelector(".modal-close").addEventListener("click", closeModal);
    modal.addEventListener("dblclick", event => {
      if (event.target === modal || event.target.closest(".modal-main")) closeModal();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") closeModal();
    });

    function setAllDetails(open) {
      document.querySelectorAll("details.chapter, details.relevance").forEach(item => {
        item.open = open;
      });
      if (open) {
        Object.values(cards).forEach(renderChart);
      }
    }

    document.querySelectorAll("details").forEach(item => {
      item.addEventListener("toggle", () => {
        if (item.open) {
          item.querySelectorAll(".chart[data-card]").forEach(chart => {
            renderChart(cards[chart.dataset.card]);
          });
        }
      });
    });
  </script>
</body>
</html>
"""


PRELOADED_DICTIONARY_PATH: str = ""


@app.get("/")
def upload_page() -> str:
    has_preloaded_dict = bool(PRELOADED_DICTIONARY_PATH)
    dict_filename = os.path.basename(PRELOADED_DICTIONARY_PATH) if has_preloaded_dict else ""
    return render_template_string(
        UPLOAD_TEMPLATE,
        title=APP_TITLE,
        styles=BASE_STYLES,
        error=None,
        max_categories=MAX_CATEGORICAL_VALUES,
        histogram_bins=HISTOGRAM_BINS,
        min_histogram_bins=MIN_HISTOGRAM_BINS,
        max_histogram_bins=MAX_HISTOGRAM_BINS,
        preloaded_dictionary=has_preloaded_dict,
        preloaded_dictionary_filename=dict_filename,
    )


def _load_preloaded_file(path: str, label: str) -> pd.DataFrame:
    if not path:
        raise ValueError(f"预加载的{label}文件路径为空。")
    if not os.path.isfile(path):
        raise ValueError(f"预加载的{label}文件不存在：{path}")
    return pd.read_excel(path, sheet_name=0, dtype=object)


@app.post("/analyze")
def analyze_page() -> tuple[str, int] | str:
    data_file = request.files.get("data_file")
    dictionary_file = request.files.get("dictionary_file")
    use_preloaded_dictionary = request.form.get("use_preloaded_dictionary") == "1"
    submitted_histogram_bins = request.form.get(
        "histogram_bins",
        str(HISTOGRAM_BINS),
    )
    try:
        selected_histogram_bins = parse_histogram_bins(
            submitted_histogram_bins
        )
    except ValueError as exc:
        return (
            render_template_string(
                UPLOAD_TEMPLATE,
                title=APP_TITLE,
                styles=BASE_STYLES,
                error=str(exc),
                max_categories=MAX_CATEGORICAL_VALUES,
                histogram_bins=submitted_histogram_bins,
                min_histogram_bins=MIN_HISTOGRAM_BINS,
                max_histogram_bins=MAX_HISTOGRAM_BINS,
                preloaded_dictionary=bool(PRELOADED_DICTIONARY_PATH),
                preloaded_dictionary_filename=os.path.basename(PRELOADED_DICTIONARY_PATH) if PRELOADED_DICTIONARY_PATH else "",
            ),
            400,
        )

    # 数据文件必须手动上传
    if not data_file or not data_file.filename:
        return (
            render_template_string(
                UPLOAD_TEMPLATE,
                title=APP_TITLE,
                styles=BASE_STYLES,
                error="请选择数据文件。",
                max_categories=MAX_CATEGORICAL_VALUES,
                histogram_bins=selected_histogram_bins,
                min_histogram_bins=MIN_HISTOGRAM_BINS,
                max_histogram_bins=MAX_HISTOGRAM_BINS,
                preloaded_dictionary=bool(PRELOADED_DICTIONARY_PATH),
                preloaded_dictionary_filename=os.path.basename(PRELOADED_DICTIONARY_PATH) if PRELOADED_DICTIONARY_PATH else "",
            ),
            400,
        )

    # 数据字典：优先用上传的，其次用预加载的
    if dictionary_file and dictionary_file.filename:
        pass  # 使用用户上传的文件
    elif use_preloaded_dictionary and PRELOADED_DICTIONARY_PATH:
        pass  # 使用预加载的数据字典
    elif not PRELOADED_DICTIONARY_PATH:
        return (
            render_template_string(
                UPLOAD_TEMPLATE,
                title=APP_TITLE,
                styles=BASE_STYLES,
                error="请选择数据字典。",
                max_categories=MAX_CATEGORICAL_VALUES,
                histogram_bins=selected_histogram_bins,
                min_histogram_bins=MIN_HISTOGRAM_BINS,
                max_histogram_bins=MAX_HISTOGRAM_BINS,
                preloaded_dictionary=bool(PRELOADED_DICTIONARY_PATH),
                preloaded_dictionary_filename=os.path.basename(PRELOADED_DICTIONARY_PATH) if PRELOADED_DICTIONARY_PATH else "",
            ),
            400,
        )

    try:
        # 读取数据文件（始终手动上传）
        raw_data = data_file.read()
        if not raw_data:
            raise ValueError(f"文件\"{data_file.filename}\"为空。")
        data = pd.read_excel(io.BytesIO(raw_data), sheet_name=0, dtype=object)

        # 读取数据字典
        if dictionary_file and dictionary_file.filename:
            raw_dict = dictionary_file.read()
            if not raw_dict:
                raise ValueError(f"文件\"{dictionary_file.filename}\"为空。")
            dictionary = pd.read_excel(io.BytesIO(raw_dict), sheet_name=0, dtype=object)
        else:
            dictionary = _load_preloaded_file(PRELOADED_DICTIONARY_PATH, "数据字典")

        report = build_report(
            data,
            dictionary,
            histogram_bins=selected_histogram_bins,
        )
    except Exception as exc:
        return (
            render_template_string(
                UPLOAD_TEMPLATE,
                title=APP_TITLE,
                styles=BASE_STYLES,
                error=html.escape(str(exc)),
                max_categories=MAX_CATEGORICAL_VALUES,
                histogram_bins=selected_histogram_bins,
                min_histogram_bins=MIN_HISTOGRAM_BINS,
                max_histogram_bins=MAX_HISTOGRAM_BINS,
                preloaded_dictionary=bool(PRELOADED_DICTIONARY_PATH),
                preloaded_dictionary_filename=os.path.basename(PRELOADED_DICTIONARY_PATH) if PRELOADED_DICTIONARY_PATH else "",
            ),
            400,
        )

    return render_template_string(
        REPORT_TEMPLATE,
        title=APP_TITLE,
        styles=BASE_STYLES,
        report=report,
        report_json=json_for_script(report),
        max_categories=MAX_CATEGORICAL_VALUES,
        pie_top_n=PIE_TOP_N,
        histogram_bins=report["histogram_bins"],
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def open_browser() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    cli_args = parse_cli_args()
    if cli_args.port:
        PORT = cli_args.port
    if cli_args.dictionary:
        PRELOADED_DICTIONARY_PATH = os.path.abspath(cli_args.dictionary)
    if not port_is_available(HOST, PORT):
        raise SystemExit(
            f"端口 {PORT} 已被占用。请关闭旧程序，或修改脚本顶部的 PORT 后重试。"
        )
    if AUTO_OPEN_BROWSER:
        threading.Timer(1.0, open_browser).start()
    preload_info = ""
    if PRELOADED_DICTIONARY_PATH:
        preload_info += f"\n  预加载数据字典：{PRELOADED_DICTIONARY_PATH}"
    print(f"{APP_TITLE} 已启动：http://{HOST}:{PORT}")
    if preload_info:
        print(preload_info)
    print("关闭工具时，请回到此窗口按 Ctrl+C。")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
