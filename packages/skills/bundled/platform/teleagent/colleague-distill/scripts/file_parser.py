#!/usr/bin/env python3
"""
多格式文件解析器
支持从 Word、PPT、PDF、TXT、MD、CSV、JSON、EML、HTML 等格式提取纯文本
专门适配"同事蒸馏器"的数据采集场景
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Optional

# ============================================================
# 文本提取函数
# ============================================================

def extract_docx(file_path: str) -> str:
    """从 .docx 文件提取文本"""
    try:
        from docx import Document
    except ImportError:
        return "[ERROR] python-docx 未安装，请运行: pip install python-docx"

    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())

    # 提取表格内容
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    return "\n".join(paragraphs)


def extract_pptx(file_path: str) -> str:
    """从 .pptx 文件提取文本"""
    try:
        from pptx import Presentation
    except ImportError:
        return "[ERROR] python-pptx 未安装，请运行: pip install python-pptx"

    prs = Presentation(file_path)
    slides_text = []

    for i, slide in enumerate(prs.slides, 1):
        slide_parts = [f"--- 幻灯片 {i} ---"]
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        slide_parts.append(text)
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        slide_parts.append(" | ".join(cells))

        if len(slide_parts) > 1:
            slides_text.append("\n".join(slide_parts))

    return "\n\n".join(slides_text)


def extract_pdf(file_path: str) -> str:
    """从 .pdf 文件提取文本"""
    try:
        import pdfplumber
    except ImportError:
        return "[ERROR] pdfplumber 未安装，请运行: pip install pdfplumber"

    pages_text = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"--- 页 {i} ---\n{text.strip()}")

    return "\n\n".join(pages_text)


def extract_txt(file_path: str) -> str:
    """从 .txt/.md 文件提取文本，自动检测编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-16']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "[ERROR] 无法解码文件，尝试过的编码: " + ", ".join(encodings)


def extract_csv(file_path: str) -> str:
    """从 .csv 文件提取文本"""
    import csv
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, newline='') as f:
                reader = csv.reader(f)
                rows = []
                for row in reader:
                    if any(cell.strip() for cell in row):
                        rows.append(" | ".join(cell.strip() for cell in row))
                return "\n".join(rows)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "[ERROR] 无法解码 CSV 文件"


def extract_json(file_path: str) -> str:
    """从 .json 文件提取文本（支持聊天记录导出格式）"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 尝试识别常见聊天记录格式
    if isinstance(data, list):
        messages = []
        for item in data:
            if isinstance(item, dict):
                # 微信/钉钉/飞书导出格式
                speaker = item.get('speaker') or item.get('sender') or item.get('from') or item.get('name') or ''
                content = item.get('content') or item.get('text') or item.get('message') or item.get('body') or ''
                time = item.get('time') or item.get('timestamp') or item.get('date') or ''
                if content:
                    prefix = f"[{time}] " if time else ""
                    name_prefix = f"{speaker}: " if speaker else ""
                    messages.append(f"{prefix}{name_prefix}{content}")
        if messages:
            return "\n".join(messages)
        # 非聊天格式，直接格式化
        return json.dumps(data, ensure_ascii=False, indent=2)

    return json.dumps(data, ensure_ascii=False, indent=2)


def extract_eml(file_path: str) -> str:
    """从 .eml 邮件文件提取文本"""
    import email
    from email.header import decode_header

    def decode_mime_str(s):
        if not s:
            return ""
        parts = decode_header(s)
        decoded = []
        for content, charset in parts:
            if isinstance(content, bytes):
                decoded.append(content.decode(charset or 'utf-8', errors='replace'))
            else:
                decoded.append(content)
        return "".join(decoded)

    with open(file_path, 'rb') as f:
        msg = email.message_from_bytes(f.read())

    subject = decode_mime_str(msg.get('Subject', ''))
    from_addr = decode_mime_str(msg.get('From', ''))
    to_addr = decode_mime_str(msg.get('To', ''))
    date = msg.get('Date', '')

    # 提取正文
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
                break
            elif content_type == 'text/html' and not body:
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
    else:
        charset = msg.get_content_charset() or 'utf-8'
        body = msg.get_payload(decode=True).decode(charset, errors='replace')

    return f"主题: {subject}\n发件人: {from_addr}\n收件人: {to_addr}\n日期: {date}\n\n{body}"


def extract_html(file_path: str) -> str:
    """从 .html 文件提取文本"""
    try:
        from html.parser import HTMLParser

        class HTMLTextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.result = []
                self._skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in ('script', 'style'):
                    self._skip = False
                if tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr'):
                    self.result.append('\n')

            def handle_data(self, data):
                if not self._skip and data.strip():
                    self.result.append(data.strip())

        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            html_content = f.read()

        extractor = HTMLTextExtractor()
        extractor.feed(html_content)
        return "\n".join(extractor.result)
    except Exception as e:
        return f"[ERROR] HTML 解析失败: {e}"


def extract_xlsx(file_path: str) -> str:
    """从 .xlsx 文件提取文本"""
    try:
        from openpyxl import load_workbook
    except ImportError:
        return "[ERROR] openpyxl 未安装，请运行: pip install openpyxl"

    wb = load_workbook(file_path, read_only=True, data_only=True)
    sheets_text = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_parts = [f"--- 工作表: {sheet_name} ---"]
        for row in ws.iter_rows(values_only=True):
            cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if cells:
                sheet_parts.append(" | ".join(cells))
        if len(sheet_parts) > 1:
            sheets_text.append("\n".join(sheet_parts))

    wb.close()
    return "\n\n".join(sheets_text)


# ============================================================
# 格式路由
# ============================================================

EXTRACTORS = {
    '.docx': extract_docx,
    '.pptx': extract_pptx,
    '.pdf': extract_pdf,
    '.txt': extract_txt,
    '.md': extract_txt,
    '.csv': extract_csv,
    '.json': extract_json,
    '.eml': extract_eml,
    '.html': extract_html,
    '.htm': extract_html,
    '.xlsx': extract_xlsx,
    '.xlsm': extract_xlsx,
}


def extract_file(file_path: str) -> str:
    """根据文件扩展名自动选择提取器"""
    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] 文件不存在: {file_path}"

    ext = path.suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if not extractor:
        # 未知格式，尝试作为纯文本读取
        return extract_txt(file_path)

    return extractor(file_path)


def extract_directory(dir_path: str, target_name: Optional[str] = None) -> str:
    """递归提取目录下所有支持的文件"""
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        return f"[ERROR] 目录不存在: {dir_path}"

    all_text = []
    supported_exts = set(EXTRACTORS.keys())

    for file_path in sorted(dir_path.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in supported_exts:
            print(f"  提取: {file_path}", file=sys.stderr)
            text = extract_file(str(file_path))
            if text and not text.startswith("[ERROR]"):
                header = f"========== {file_path.name} =========="
                all_text.append(f"{header}\n{text}")

    if not all_text:
        return "[WARNING] 未找到可提取的文件"

    return "\n\n".join(all_text)


def save_raw_text(text: str, output_path: str):
    """保存提取的原始文本"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="多格式文件解析器 - 同事蒸馏器数据采集工具")
    parser.add_argument("input", help="输入文件或目录路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("-n", "--name", help="目标同事姓名（用于筛选相关内容）")
    parser.add_argument("--stats", action="store_true", help="仅输出文件统计信息")

    args = parser.parse_args()

    input_path = Path(args.input)

    # 统计模式
    if args.stats:
        if input_path.is_dir():
            files = list(input_path.rglob("*"))
            supported = [f for f in files if f.is_file() and f.suffix.lower() in EXTRACTORS]
            ext_stats = {}
            for f in supported:
                ext = f.suffix.lower()
                ext_stats[ext] = ext_stats.get(ext, 0) + 1
            print(f"目录: {input_path}")
            print(f"支持的文件数: {len(supported)}")
            for ext, count in sorted(ext_stats.items()):
                print(f"  {ext}: {count} 个")
        else:
            print(f"文件: {input_path}")
            print(f"格式: {input_path.suffix.lower()}")
            print(f"大小: {input_path.stat().st_size} 字节")
        return

    # 提取模式
    if input_path.is_dir():
        text = extract_directory(str(input_path), args.name)
    else:
        text = extract_file(str(input_path))

    if args.output:
        save_raw_text(text, args.output)
        print(f"已保存到: {args.output}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
