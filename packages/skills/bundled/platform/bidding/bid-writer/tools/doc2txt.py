#!/usr/bin/env python3
"""
万能文档转换器 — doc2txt v1.0
支持 .doc / .docx / .xlsx / .pdf → TXT/Markdown
标书写作配套工具
"""
import os, sys, re, struct, argparse
from pathlib import Path

# ============================================================
# .doc 提取器（olefile + UTF-16LE 文本块扫描）
# ============================================================
def extract_doc(filepath: str) -> str:
    """从 .doc (OLE2) 文件中提取文本"""
    import olefile

    ole = olefile.OleFileIO(filepath)
    word_bytes = bytearray(ole.openstream('WordDocument').read())

    blocks = _scan_utf16le_blocks(word_bytes, min_chars=20)
    ole.close()

    if not blocks:
        return ""

    text = '\n'.join(blocks)
    text = text.replace('\x00', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _scan_utf16le_blocks(data: bytearray, min_chars: int = 20) -> list:
    """扫描 UTF-16LE 编码的中文文本块"""
    blocks = []
    i = 0
    block_start = -1

    while i < len(data) - 1:
        cp = struct.unpack_from('<H', data, i)[0]
        is_valid = _is_valid_utf16le_char(cp)

        if is_valid:
            if block_start < 0:
                block_start = i
        else:
            if block_start >= 0:
                block_len = i - block_start
                if block_len >= min_chars * 2:
                    raw = data[block_start:i]
                    try:
                        text = raw.decode('utf-16-le', errors='replace')
                        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
                        if chinese_chars >= 5:
                            blocks.append(text)
                    except:
                        pass
                block_start = -1
        i += 2

    # 处理末尾块
    if block_start >= 0 and len(data) - block_start >= min_chars * 2:
        raw = data[block_start:]
        try:
            text = raw.decode('utf-16-le', errors='replace')
            if sum(1 for c in text if '\u4e00' <= c <= '\u9fff') >= 5:
                blocks.append(text)
        except:
            pass

    return blocks


def _is_valid_utf16le_char(cp: int) -> bool:
    """判断是否为有效的 UTF-16LE 可打印字符"""
    return (
        (0x0020 <= cp <= 0x007E) or      # ASCII 可打印
        (0x3000 <= cp <= 0x303F) or      # CJK 标点
        (0x4E00 <= cp <= 0x9FFF) or      # 中日韩统一汉字
        (0xFF00 <= cp <= 0xFFEF) or      # 全角字符
        (0x2000 <= cp <= 0x206F) or      # 通用标点
        cp in (0x000D, 0x000A, 0x0009, 0x003A,
               0x003B, 0x002C, 0x002E, 0x000B)
    )


# ============================================================
# .docx 提取器
# ============================================================
def extract_docx(filepath: str) -> str:
    """从 .docx 文件提取全部段落文本"""
    import docx

    doc = docx.Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return '\n\n'.join(paragraphs)


# ============================================================
# .xlsx 提取器（输出 Markdown 表格）
# ============================================================
def extract_xlsx(filepath: str, as_markdown: bool = True) -> str:
    """从 .xlsx 文件提取所有 Sheet 内容

    Args:
        filepath: xlsx 文件路径
        as_markdown: True 输出 Markdown 表格，False 输出纯文本
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    output_parts = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows or all(all(c is None for c in row) for row in rows):
            continue

        output_parts.append(f"\n## {sheet_name}\n")
        output_parts.append(_rows_to_table(rows, as_markdown))

    wb.close()
    return '\n'.join(output_parts).strip()


def _rows_to_table(rows: list, as_markdown: bool) -> str:
    """将二维列表转为表格"""
    if not rows:
        return ""

    # 统一转字符串，None 转空
    str_rows = [[str(c) if c is not None else '' for c in row] for row in rows]

    # 确定列数（取最大）
    max_cols = max(len(r) for r in str_rows)
    for r in str_rows:
        while len(r) < max_cols:
            r.append('')

    # 清理单元格内容
    clean_rows = [[c.replace('\n', ' ').replace('|', r'\|').strip()
                   for c in row] for row in str_rows]

    if as_markdown:
        return _to_markdown_table(clean_rows)
    else:
        return _to_tsv(clean_rows)


def _to_markdown_table(rows: list) -> str:
    """转为 Markdown 表格"""
    lines = []
    # 表头
    lines.append('| ' + ' | '.join(rows[0]) + ' |')
    # 分隔线
    lines.append('| ' + ' | '.join(['---'] * len(rows[0])) + ' |')
    # 数据行
    for row in rows[1:]:
        lines.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(lines)


def _to_tsv(rows: list) -> str:
    """转为 TSV"""
    return '\n'.join('\t'.join(row) for row in rows)


# ============================================================
# .pdf 提取器（文字层）
# ============================================================
def extract_pdf(filepath: str) -> str:
    """从 PDF 提取文字层文本

    若疑似扫描件（文字量极少），返回提示信息。
    """
    import fitz  # pymupdf

    doc = fitz.open(filepath)
    total_pages = len(doc)
    pages_text = []

    for page in doc:
        text = page.get_text()
        if text.strip():
            pages_text.append(text.strip())

    doc.close()

    full_text = '\n\n'.join(pages_text)

    if len(full_text) < 50:
        return (
            "[提示] 此 PDF 疑似纯扫描件（文字层 < 50 字符），"
            f"请用视觉模型或 OCR 工具另行处理。共 {total_pages} 页。"
        )

    return full_text.strip()


# ============================================================
# 主入口
# ============================================================
SUPPORTED_EXT = {
    '.doc':  extract_doc,
    '.docx': extract_docx,
    '.xlsx': extract_xlsx,
    '.xlsm': extract_xlsx,
    '.pdf':  extract_pdf,
}


def convert(filepath: str, output: str = None) -> str:
    """转换单个文件

    Returns:
        输出文件路径
    """
    ext = Path(filepath).suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise ValueError(f"不支持的文件格式: {ext}（支持: {', '.join(SUPPORTED_EXT)}）")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    print(f"[转换] {os.path.basename(filepath)} ({ext})... ", end='', flush=True)

    func = SUPPORTED_EXT[ext]
    text = func(filepath)

    if not text:
        print("WARN: no content extracted")
        return ""

    # 确定输出路径
    if output is None:
        stem = Path(filepath).stem
        parent = Path(filepath).parent
        out_ext = '.md' if ext in ('.xlsx', '.xlsm') else '.txt'
        output = str(parent / f"{stem}_doc2txt{out_ext}")

    with open(output, 'w', encoding='utf-8') as f:
        f.write(text)

    size = len(text)
    print(f"OK {size:,} chars -> {os.path.basename(output)}")
    return output


def convert_batch(filepaths: list, output_dir: str = None) -> list:
    """批量转换

    Returns:
        成功转换的输出文件路径列表
    """
    results = []
    for fp in filepaths:
        try:
            out = convert(fp, output_dir=output_dir)
            if out:
                results.append(out)
        except Exception as e:
            print(f"[错误] {os.path.basename(fp)}: {e}")
    return results


def main():
    parser = argparse.ArgumentParser(
        description='万能文档转换器 — .doc/.docx/.xlsx/.pdf → TXT/Markdown',
        epilog='标书写作配套工具 v1.0'
    )
    parser.add_argument('files', nargs='+', help='要转换的文件路径（支持多个）')
    parser.add_argument('-o', '--output', help='输出文件路径（单文件模式）')
    parser.add_argument('-d', '--output-dir', help='输出目录（批量模式）')
    parser.add_argument('--no-md', action='store_true', help='xlsx 输出纯文本而非 Markdown')

    args = parser.parse_args()

    if len(args.files) == 1 and not args.output_dir:
        # 单文件模式
        try:
            convert(args.files[0], args.output)
        except Exception as e:
            print(f"[错误] {e}")
            sys.exit(1)
    else:
        # 批量模式
        results = convert_batch(args.files, args.output_dir)
        print(f"\n完成：成功 {len(results)}/{len(args.files)} 个文件")


if __name__ == '__main__':
    main()
