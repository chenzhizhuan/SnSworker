# -*- coding: utf-8 -*-
"""
从JSON数据生成Mermaid关系图代码
用法: python generate_mermaid.py <input.json> [output.md]
input.json 格式同 generate_graph_html.py
输出 Mermaid graph LR 代码块，可选写入 .md 文件
"""

import json
import sys
import re


def sanitize_id(id_str):
    """Sanitize ID for Mermaid (no spaces, special chars)."""
    return re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', str(id_str))


def node_shape(type_str):
    """Return Mermaid node shape markers based on type."""
    shapes = {
        "person": ("(", ")"),       # rounded rect
        "company":("[", "]"),       # square
        "organization":("{", "}"),  # diamond
        "event":("([", "]))"),      # stadium
        "project":("[[", "]]"),     # subroutine
        "location":("((", "))"),    # circle
    }
    return shapes.get(type_str, ("[", "]"))


def generate_mermaid(data):
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    title = data.get("title", "关系图谱")

    lines = [f"---", f"title: {title}", f"---", f"graph LR"]

    # Group nodes by type for visual clarity
    for n in nodes:
        nid = sanitize_id(n["id"])
        label = n["label"].replace('"', "'")
        shape = node_shape(n.get("type", ""))
        lines.append(f"    {nid}{shape[0]}\"{label}\"{shape[1]}")

    lines.append("")

    for e in edges:
        src = sanitize_id(e["source"])
        tgt = sanitize_id(e["target"])
        label = e.get("label", "")
        if label:
            label = label.replace('"', "'")
            lines.append(f"    {src} -->|{label}| {tgt}")
        else:
            lines.append(f"    {src} --> {tgt}")

    # Add styling by type
    type_colors = {
        "person": "#e74c3c",
        "company": "#3498db",
        "organization": "#2ecc71",
        "event": "#f39c12",
        "project": "#9b59b6",
        "location": "#1abc9c",
    }

    for type_name, color in type_colors.items():
        type_nodes = [sanitize_id(n["id"]) for n in nodes if n.get("type") == type_name]
        if type_nodes:
            ids = " ".join(type_nodes)
            lines.append(f"    style {ids} fill:{color},color:#fff,stroke:{color}")

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_mermaid.py <input.json> [output.md]")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    mermaid_code = generate_mermaid(data)

    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
        content = f"# {data.get('title', '关系图谱')}\n\n```mermaid\n{mermaid_code}\n```\n"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Mermaid关系图已生成: {output_path}")
    else:
        print(mermaid_code)
