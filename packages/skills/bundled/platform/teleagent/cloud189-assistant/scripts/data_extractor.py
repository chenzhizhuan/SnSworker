#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天翼云盘报表整理 - 数据提取脚本
支持格式：.xlsx, .xls, .csv, .tsv, .docx, .txt, .md, .pdf

功能：
  extract  — 提取文件内容为JSON（表格数据保留行列结构，文本数据保留段落）
  extract-multi — 批量提取多个文件，合并输出

使用方式：
  python scripts/data_extractor.py extract --input <文件路径>
  python scripts/data_extractor.py extract-multi --inputs <文件1> <文件2> ...
"""
import argparse
import json
import os
import sys
import csv

def extract_xlsx(filepath):
    """提取Excel文件，保留表格结构"""
    try:
        import openpyxl
    except ImportError:
        return {"error": "需要安装 openpyxl: pip install openpyxl"}

    wb = openpyxl.load_workbook(filepath, data_only=True)
    sheets = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            # 将None转为空字符串，其他值转str
            rows.append([str(cell) if cell is not None else "" for cell in row])
        # 去掉全空行
        rows = [r for r in rows if any(c.strip() for c in r)]
        sheets.append({
            "sheet_name": sheet_name,
            "row_count": len(rows),
            "col_count": max((len(r) for r in rows), default=0),
            "rows": rows
        })
    wb.close()
    return {"format": "xlsx", "sheet_count": len(sheets), "sheets": sheets}


def extract_csv(filepath, delimiter=","):
    """提取CSV/TSV文件"""
    rows = []
    encoding = _detect_encoding(filepath)
    with open(filepath, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            rows.append([cell.strip() for cell in row])
    # 去掉全空行
    rows = [r for r in rows if any(c.strip() for c in r)]
    return {
        "format": "csv",
        "row_count": len(rows),
        "col_count": max((len(r) for r in rows), default=0),
        "rows": rows
    }


def extract_docx(filepath):
    """提取Word文档文本"""
    try:
        from docx import Document
    except ImportError:
        return {"error": "需要安装 python-docx: pip install python-docx"}

    doc = Document(filepath)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # 提取表格
    tables = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        if rows:
            tables.append({"row_count": len(rows), "rows": rows})

    result = {"format": "docx", "paragraphs": paragraphs}
    if tables:
        result["tables"] = tables
    return result


def extract_txt(filepath):
    """提取纯文本文件"""
    encoding = _detect_encoding(filepath)
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        content = f.read()
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        # 按行分割
        paragraphs = [line.strip() for line in content.split("\n") if line.strip()]
    return {"format": "txt", "paragraphs": paragraphs}


def extract_md(filepath):
    """提取Markdown文件"""
    return extract_txt(filepath)  # Markdown本质上也是文本


def extract_pdf(filepath):
    """提取PDF文本"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"error": "需要安装 pypdf: pip install pypdf"}

    reader = PdfReader(filepath)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append({"page": i + 1, "content": text})
    return {"format": "pdf", "page_count": len(pages), "pages": pages}


def _detect_encoding(filepath):
    """简单编码检测：尝试utf-8，失败则用gbk"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            f.read(4096)
        return "utf-8"
    except UnicodeDecodeError:
        return "gbk"


def extract_file(filepath):
    """根据文件扩展名自动选择提取方法"""
    ext = os.path.splitext(filepath)[1].lower()
    extractors = {
        ".xlsx": extract_xlsx,
        ".xls": extract_xlsx,
        ".csv": lambda f: extract_csv(f, ","),
        ".tsv": lambda f: extract_csv(f, "\t"),
        ".docx": extract_docx,
        ".txt": extract_txt,
        ".md": extract_md,
        ".pdf": extract_pdf,
    }
    extractor = extractors.get(ext)
    if not extractor:
        return {"error": f"不支持的文件格式: {ext}", "supported": list(extractors.keys())}
    try:
        return extractor(filepath)
    except Exception as e:
        return {"error": f"提取失败: {str(e)}"}


def cmd_extract(args):
    """提取单个文件"""
    result = extract_file(args.input)
    # 附加文件元信息
    result["file"] = os.path.basename(args.input)
    result["file_path"] = args.input
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_extract_multi(args):
    """批量提取多个文件"""
    results = []
    for fpath in args.inputs:
        r = extract_file(fpath)
        r["file"] = os.path.basename(fpath)
        r["file_path"] = fpath
        results.append(r)
    print(json.dumps({
        "file_count": len(results),
        "files": results
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="天翼云盘报表整理 - 数据提取")
    subparsers = parser.add_subparsers(dest="command")

    # extract
    ext_p = subparsers.add_parser("extract", help="提取单个文件内容")
    ext_p.add_argument("--input", required=True, help="输入文件路径")

    # extract-multi
    multi_p = subparsers.add_parser("extract-multi", help="批量提取多个文件")
    multi_p.add_argument("--inputs", nargs="+", required=True, help="多个输入文件路径")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "extract": cmd_extract,
        "extract-multi": cmd_extract_multi,
    }
    if args.command in commands:
        commands[args.command](args)
    else:
        print(json.dumps({"error": f"未知命令: {args.command}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
