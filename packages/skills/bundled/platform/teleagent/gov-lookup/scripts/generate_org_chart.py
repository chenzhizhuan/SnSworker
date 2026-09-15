#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政府部门组织架构可视化生成器

根据结构化的组织数据生成HTML格式的可视化组织架构图。

输入: JSON 格式的组织架构数据文件
输出: HTML 文件，包含可交互的组织架构树形图

用法:
    python generate_org_chart.py <input.json> [--output output.html] [--title "标题"]
"""

import json
import sys
import os
import argparse
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f5f7fa; color: #2c3e50; padding: 20px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ text-align: center; margin-bottom: 8px; font-size: 24px; color: #1a1a2e; }}
.subtitle {{ text-align: center; color: #7f8c8d; font-size: 13px; margin-bottom: 30px; }}
.org-chart {{ display: flex; flex-direction: column; align-items: center; gap: 0; }}
.level {{ display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; margin-bottom: 0; position: relative; }}
.level-row {{ display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; padding: 20px 0; }}
.node {{ background: white; border-radius: 10px; padding: 16px 20px; min-width: 160px; max-width: 260px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); text-align: center; position: relative; transition: all 0.3s; border-left: 4px solid #3498db; }}
.node:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }}
.node.level-0 {{ border-left-color: #e74c3c; background: linear-gradient(135deg, #fff 0%, #fef0f0 100%); }}
.node.level-1 {{ border-left-color: #e67e22; background: linear-gradient(135deg, #fff 0%, #fef7f0 100%); }}
.node.level-2 {{ border-left-color: #3498db; background: linear-gradient(135deg, #fff 0%, #f0f7fe 100%); }}
.node.level-3 {{ border-left-color: #2ecc71; background: linear-gradient(135deg, #fff 0%, #f0fef5 100%); }}
.node.level-4 {{ border-left-color: #9b59b6; background: linear-gradient(135deg, #fff 0%, #f7f0fe 100%); }}
.node-title {{ font-weight: 700; font-size: 15px; margin-bottom: 6px; color: #2c3e50; }}
.node-person {{ font-size: 13px; color: #e74c3c; font-weight: 600; margin-bottom: 4px; }}
.node-title-only .node-person {{ display: none; }}
.node-extra {{ font-size: 12px; color: #95a5a6; }}
.connector-group {{ display: flex; justify-content: center; align-items: flex-start; height: 30px; position: relative; }}
.connector-line {{ width: 2px; height: 30px; background: #bdc3c7; }}
.connector-h {{ height: 2px; background: #bdc3c7; position: absolute; top: 0; }}
.legend {{ margin-top: 30px; padding: 16px; background: white; border-radius: 8px; box-shadow: 0 1px 6px rgba(0,0,0,0.06); }}
.legend h3 {{ font-size: 14px; margin-bottom: 10px; color: #2c3e50; }}
.legend-item {{ display: inline-block; margin-right: 16px; font-size: 12px; }}
.legend-dot {{ display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 4px; vertical-align: middle; }}
@media (max-width: 768px) {{
    .node {{ min-width: 120px; padding: 10px 14px; }}
    .level-row {{ gap: 8px; }}
    h1 {{ font-size: 18px; }}
}}
</style>
</head>
<body>
<div class="container">
<h1>{title}</h1>
<p class="subtitle">生成时间：{timestamp} | 数据来源：互联网公开信息，仅供参考</p>
{chart_content}
{legend}
</div>
</body>
</html>"""

LEGEND_HTML = """
<div class="legend">
<h3>层级说明</h3>
<span class="legend-item"><span class="legend-dot" style="background:#e74c3c"></span>一级机构</span>
<span class="legend-item"><span class="legend-dot" style="background:#e67e22"></span>二级机构</span>
<span class="legend-item"><span class="legend-dot" style="background:#3498db"></span>三级机构</span>
<span class="legend-item"><span class="legend-dot" style="background:#2ecc71"></span>四级机构</span>
<span class="legend-item"><span class="legend-dot" style="background:#9b59b6"></span>五级机构</span>
</div>"""


def render_node(node, level):
    """渲染单个节点"""
    name = node.get("name", "")
    person = node.get("person", "")
    title_extra = node.get("title", "")
    css_class = f"level-{level}" if level <= 4 else f"level-4"

    parts = [f'<div class="node {css_class}">']
    parts.append(f'<div class="node-title">{name}</div>')
    if person:
        parts.append(f'<div class="node-person">{person}</div>')
    if title_extra:
        parts.append(f'<div class="node-extra">{title_extra}</div>')
    parts.append('</div>')
    return "".join(parts)


def render_tree(nodes, level=0):
    """递归渲染组织架构树"""
    if not nodes:
        return ""
    html_parts = []
    # 当前层所有节点
    node_htmls = [render_node(n, level) for n in nodes]
    html_parts.append(f'<div class="level-row">')
    html_parts.append("".join(node_htmls))
    html_parts.append('</div>')

    # 收集所有子节点
    all_children = []
    for n in nodes:
        children = n.get("children", [])
        if children:
            all_children.extend(children)

    if all_children:
        html_parts.append('<div class="connector-group"><div class="connector-line"></div></div>')
        html_parts.append(render_tree(all_children, level + 1))

    return "\n".join(html_parts)


def generate_chart(data, title, output_path):
    """生成完整HTML文件"""
    nodes = data if isinstance(data, list) else data.get("org", [])

    chart_content = f'<div class="org-chart">{render_tree(nodes)}</div>'
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = HTML_TEMPLATE.format(
        title=title,
        timestamp=timestamp,
        chart_content=chart_content,
        legend=LEGEND_HTML
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK: {os.path.abspath(output_path)}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="政府部门组织架构可视化生成器")
    parser.add_argument("input", help="JSON格式的组织架构数据文件路径")
    parser.add_argument("--output", "-o", help="输出HTML文件路径", default=None)
    parser.add_argument("--title", "-t", help="图表标题", default="政府部门组织架构图")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: 输入文件不存在: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    output = args.output or os.path.splitext(args.input)[0] + "_chart.html"
    generate_chart(data, args.title, output)


if __name__ == "__main__":
    main()
