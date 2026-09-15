#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_docx.py - 将结构化文章渲染为规范的 Word(.docx) 文档

输入：JSON 字符串（或通过 --input 指定 JSON 文件）
输出：生成的 .docx 文件路径（--output 指定，默认当前目录输出）

JSON 结构示例：
{
  "title": "文章标题",
  "meta": {
    "author": "小陈",
    "course": "课程名称（可选）",
    "teacher": "老师（可选）",
    "date": "2026-08-07（可选）"
  },
  "abstract": "摘要内容（可选）",
  "keywords": ["关键词1", "关键词2"]（可选）,
  "sections": [
    {"type": "h1", "text": "一级标题"},
    {"type": "h2", "text": "二级标题"},
    {"type": "p", "text": "正文段落"},
    {"type": "bullet", "items": ["要点一", "要点二"]},
    {"type": "numbered", "items": ["第一点", "第二点"]}
  ],
  "references": [
    "[1] 作者. 题名[J]. 刊名, 年, 卷(期): 页.",
    "[2] 机构. 题名[EB/OL]. (2026-08-01)[2026-08-07]. 链接."
  ]
}

section.type 支持：h1 / h2 / h3 / p / bullet / numbered / quote
"""

import argparse
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


DEFAULT_FONT = "宋体"
HEADING_FONT = "黑体"
TITLE_FONT = "黑体"


def _set_run_font(run, font_name=DEFAULT_FONT, size=None, bold=False, color=None):
    run.font.name = font_name
    run._element.rPr.rFonts.set(
        __import__("docx").oxml.ns.qn("w:eastAsia"), font_name
    )
    if size is not None:
        run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def build_docx(data: dict, output_path: str):
    doc = Document()

    # 默认正文字体（中文）
    style = doc.styles["Normal"]
    style.font.name = DEFAULT_FONT
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(__import__("docx").oxml.ns.qn("w:eastAsia"), DEFAULT_FONT)

    # 标题
    title = data.get("title", "未命名文章")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title)
    _set_run_font(run, TITLE_FONT, size=18, bold=True)

    # 元信息
    meta = data.get("meta") or {}
    if any(meta.get(k) for k in ("author", "course", "teacher", "date")):
        mp = doc.add_paragraph()
        mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        parts = []
        if meta.get("author"):
            parts.append(f"作者：{meta['author']}")
        if meta.get("course"):
            parts.append(f"课程：{meta['course']}")
        if meta.get("teacher"):
            parts.append(f"指导老师：{meta['teacher']}")
        if meta.get("date"):
            parts.append(meta["date"])
        mrun = mp.add_run("    ".join(parts))
        _set_run_font(mrun, DEFAULT_FONT, size=10.5, color=RGBColor(0x55, 0x55, 0x55))

    # 摘要与关键词
    if data.get("abstract"):
        ap = doc.add_paragraph()
        r = ap.add_run("摘要：")
        _set_run_font(r, HEADING_FONT, size=11, bold=True)
        r2 = ap.add_run(data["abstract"])
        _set_run_font(r2, DEFAULT_FONT, size=11)
    if data.get("keywords"):
        kp = doc.add_paragraph()
        r = kp.add_run("关键词：")
        _set_run_font(r, HEADING_FONT, size=11, bold=True)
        r2 = kp.add_run("；".join(data["keywords"]))
        _set_run_font(r2, DEFAULT_FONT, size=11)

    # 正文区块
    for sec in data.get("sections", []):
        stype = sec.get("type", "p")
        text = sec.get("text", "")
        if stype == "h1":
            h = doc.add_heading(level=1)
            run = h.add_run(text)
            _set_run_font(run, HEADING_FONT, size=15, bold=True)
        elif stype == "h2":
            h = doc.add_heading(level=2)
            run = h.add_run(text)
            _set_run_font(run, HEADING_FONT, size=13, bold=True)
        elif stype == "h3":
            h = doc.add_heading(level=3)
            run = h.add_run(text)
            _set_run_font(run, HEADING_FONT, size=12, bold=True)
        elif stype == "p":
            p = doc.add_paragraph()
            run = p.add_run(text)
            _set_run_font(run, DEFAULT_FONT, size=12)
        elif stype == "quote":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(21)
            run = p.add_run(text)
            _set_run_font(run, DEFAULT_FONT, size=12, color=RGBColor(0x33, 0x33, 0x33))
        elif stype in ("bullet", "numbered"):
            items = sec.get("items", [])
            for it in items:
                style_name = "List Bullet" if stype == "bullet" else "List Number"
                p = doc.add_paragraph(style=style_name)
                run = p.add_run(it)
                _set_run_font(run, DEFAULT_FONT, size=12)

    # 参考文献
    refs = data.get("references") or []
    if refs:
        h = doc.add_heading(level=1)
        run = h.add_run("参考文献")
        _set_run_font(run, HEADING_FONT, size=13, bold=True)
        for ref in refs:
            p = doc.add_paragraph()
            run = p.add_run(ref)
            _set_run_font(run, DEFAULT_FONT, size=10.5)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return str(out)


def main():
    parser = argparse.ArgumentParser(description="将结构化 JSON 渲染为 Word 文档")
    parser.add_argument("--input", help="输入 JSON 文件路径")
    parser.add_argument("--output", required=True, help="输出 .docx 路径")
    parser.add_argument("--json", help="直接传入 JSON 字符串")
    args = parser.parse_args()

    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    elif args.json:
        data = json.loads(args.json)
    else:
        data = json.loads(sys.stdin.read())

    path = build_docx(data, args.output)
    print(f"✅ 文档已生成: {path}")


if __name__ == "__main__":
    main()
