"""Office Open XML（docx/xlsx/pptx）与纯文本附件的本地零依赖提取。

背景（ 方案1 的本地化扩展）：
- ``DocumentCaps.upload_mode=file_extract`` 的官方路径依赖上游 Files API
  （Moonshot 风格 ``POST /files`` + ``GET /files/{id}/content``）。
- 自建 vLLM / OpenAI 兼容网关没有 Files API，docx 等办公附件会在提取阶段
  失败（``document_upload_failed``），文档能力门控也因此长期只敢给
  Moonshot/Kimi 预置（0048）。
- 与 ``pdf_text_extractor`` 同思路：能在服务端本地把字节稳定转成纯文本的
  格式（docx/xlsx/pptx 均为 zip+XML 的 OOXML；txt/md/csv/json 为纯文本）
  优先本地提取，提取文本注入 system 消息——该路径与上游模型能力无关，
  任何 OpenAI 兼容 chat 端点都能消费。
- 本地提取失败（损坏 / 无文本层）时由调用方回退上游 Files API，行为与
  PDF 分支一致。

零第三方依赖：``zipfile`` + ``xml.etree``（均为标准库），模块不 import
Django / httpx，可独立单测。
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import Any, List, Optional
from xml.etree import ElementTree as ET

__all__ = [
    "extract_office_text_for_model",
    "extract_text_document_for_model",
]


# OOXML zip 内部特征 part → 文档类型
_OFFICE_PART_HINTS = {
    "word/document.xml": "docx",
    "xl/workbook.xml": "xlsx",
    "ppt/presentation.xml": "pptx",
}

# zip 结构嗅探失败但扩展名明确时，仍按扩展名走对应解析器
# （读到坏结构会抛错，由调用方回退上游 Files API）
_OFFICE_EXTENSIONS = {
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
}

_TEXT_EXTENSIONS = (".txt", ".md", ".csv", ".json", ".log", ".xml")
_TEXT_MIME_EXACT = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/yaml",
    "application/x-yaml",
}

# 明确的非文本扩展名：即使 MIME 缺省也不进入文本嗅探，
# 避免把二进制头部（如 ``%PDF``）误当纯文本注入模型。
_NON_TEXT_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".docm", ".dot",
    ".xls", ".xlsx", ".xlsm", ".xlt",
    ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svgz", ".heic",
    ".zip", ".rar", ".7z", ".gz", ".tar", ".bz2",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".otf",
    ".mp3", ".mp4", ".wav", ".flac", ".avi", ".mov", ".mkv",
)

# 已知二进制魔数：内容层防护（无扩展名/无 MIME 时也不误判）
_BINARY_MAGIC_PREFIXES = (
    b"%PDF-",
    b"PK\x03\x04",
    b"PK\x05\x06",
    b"PK\x07\x08",
    b"\xd0\xcf\x11\xe0",  # OLE2（doc/xls/ppt 旧二进制格式）
    b"\x89PNG",
    b"\xff\xd8\xff",  # JPEG
    b"GIF8",
    b"\x1f\x8b",  # gzip
    b"7z\xbc\xaf\x27\x1c",
    b"Rar!",
)

_KIND_LABELS = {
    "docx": "Word 文档",
    "xlsx": "Excel 工作簿",
    "pptx": "PowerPoint 演示文稿",
    "text": "纯文本",
}

# 本地提取的内存护栏：正文累积到该长度后停止收集并打截断标记
# （调用方还会按 DocumentCaps.max_extract_chars 二次截断注入模型）。
_MAX_BODY_CHARS = 5_000_000
_TRUNCATED_MARK = "\n\n…[本地提取已达上限，原文更长已截断]"


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------


def extract_office_text_for_model(
    content: bytes,
    *,
    filename: str = "",
    mime_type: str = "",
) -> Optional[str]:
    """docx/xlsx/pptx → 纯文本（带元数据头）。非 OOXML 内容返回 ``None``。

    返回 ``None`` 表示"不是本地可识别的办公文档"，调用方继续走原路径
    （纯文本判定 / 上游 Files API）。

    Raises:
        ValueError: 判定为 OOXML 但无可读文本（空文档 / 纯图片幻灯片等）。
        ET.ParseError / zipfile.BadZipFile: 内容损坏。
        以上异常均由调用方捕获后回退上游 Files API。
    """
    kind = _detect_office_kind(content, filename=filename)
    if kind is None:
        return None
    if kind == "docx":
        body = _extract_docx(content)
    elif kind == "xlsx":
        body = _extract_xlsx(content)
    else:
        body = _extract_pptx(content)
    return _render_with_header(body, filename=filename, kind=kind)


def extract_text_document_for_model(
    content: bytes,
    *,
    filename: str = "",
    mime_type: str = "",
) -> Optional[str]:
    """txt/md/csv/json 等纯文本附件 → 解码文本。非文本内容返回 ``None``。

    解码顺序：UTF-8（含 BOM）→ GB18030（兼容 GBK/GB2312 的中文 txt）→
    UTF-8 宽松模式兜底。是否"文本"由扩展名 / MIME 判定；MIME 缺省或
    ``application/octet-stream`` 时做内容嗅探（无 NUL + 可解码 + 可打印率）。
    """
    if not content:
        return None
    if not _looks_like_text(filename=filename, mime_type=mime_type, content=content):
        return None

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
        if text.strip():
            return text
        return None

    text = content.decode("utf-8", errors="replace")
    return text if text.strip() else None


# ---------------------------------------------------------------------------
# 类型判定
# ---------------------------------------------------------------------------


def _detect_office_kind(content: bytes, *, filename: str = "") -> Optional[str]:
    """zip 内容嗅探 + 扩展名兜底 → docx/xlsx/pptx；非 office 返回 ``None``。"""
    if not content or not content.startswith(b"PK"):
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
    except (zipfile.BadZipFile, OSError, ValueError):
        # zip 头存在但结构损坏：交由扩展名兜底（解析器会抛错回退）
        names = set()

    for part, kind in _OFFICE_PART_HINTS.items():
        if part in names:
            return kind

    lower = (filename or "").lower()
    for ext, kind in _OFFICE_EXTENSIONS.items():
        if lower.endswith(ext):
            return kind
    return None


def _looks_like_text(
    *,
    filename: str,
    mime_type: str,
    content: bytes,
) -> bool:
    lower = (filename or "").lower()
    if any(lower.endswith(ext) for ext in _TEXT_EXTENSIONS):
        return True
    if any(lower.endswith(ext) for ext in _NON_TEXT_EXTENSIONS):
        return False
    if content.startswith(_BINARY_MAGIC_PREFIXES):
        return False

    mime = (mime_type or "").split(";", 1)[0].strip().lower()
    if mime.startswith("text/") or mime in _TEXT_MIME_EXACT:
        return True
    if mime and mime != "application/octet-stream":
        # 明确的非文本 MIME（pdf / zip / 二进制办公格式等）不误判
        return False

    # MIME 缺省 / octet-stream：内容嗅探（无 NUL + 可解码 + 可打印率高）
    return _sniff_decodable_text(content)


def _sniff_decodable_text(content: bytes) -> bool:
    if b"\x00" in content:
        return False
    text: Optional[str] = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        return False
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\t\n\r\f")
    return printable / len(text) > 0.85


def _render_with_header(body: str, *, filename: str, kind: str) -> str:
    safe_filename = " ".join((filename or "document").split()) or "document"
    label = _KIND_LABELS.get(kind, kind)
    return f"[文档附件 · {label}] 文件名：{safe_filename}\n\n{body}"


# ---------------------------------------------------------------------------
# XML 辅助
# ---------------------------------------------------------------------------


def _local_name(tag: Any) -> str:
    """``{namespace}p`` → ``p``；非字符串 tag（注释/PI）返回空串。"""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


class _LineAccumulator:
    """行累积器：超过 ``_MAX_BODY_CHARS`` 后停止收集并打截断标记。"""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.total = 0
        self.truncated = False

    def add(self, line: str) -> None:
        if self.truncated:
            return
        if self.total + len(line) > _MAX_BODY_CHARS:
            self.truncated = True
            return
        self.lines.append(line)
        self.total += len(line)

    def text(self) -> str:
        body = "\n".join(self.lines)
        if self.truncated:
            body += _TRUNCATED_MARK
        return body


# ---------------------------------------------------------------------------
# docx（word/document.xml）
# ---------------------------------------------------------------------------


def _extract_docx(content: bytes) -> str:
    """Word 正文 → 段落文本；表格按"单元格 | 单元格"逐行输出。

    只收集段落直属 run 的文本；嵌套段落（文本框等）由外层遍历单独成行，
    避免重复计数。
    """
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)

    accumulator = _LineAccumulator()
    _walk_docx_blocks(root, accumulator)
    body = accumulator.text()
    if not body.strip():
        raise ValueError("docx has no readable text")
    return body


def _walk_docx_blocks(element: Any, accumulator: _LineAccumulator) -> None:
    for child in element:
        name = _local_name(child.tag)
        if name == "tbl":
            _walk_docx_table(child, accumulator)
        elif name == "p":
            text = _collect_docx_paragraph_text(child)
            if text.strip():
                accumulator.add(text.rstrip())
            # 段内嵌套段（文本框）：单独成行继续收集
            _walk_docx_blocks(child, accumulator)
        else:
            _walk_docx_blocks(child, accumulator)


def _collect_docx_paragraph_text(paragraph: Any) -> str:
    """段落直属文本（w:t / w:tab / w:br），跳过嵌套段落子树。"""
    parts: List[str] = []

    def visit(node: Any) -> None:
        name = _local_name(node.tag)
        if name == "p":
            return  # 嵌套段落由外层单独处理
        if name == "t":
            parts.append(node.text or "")
        elif name == "tab":
            parts.append("\t")
        elif name in ("br", "cr"):
            parts.append("\n")
        for grandchild in node:
            visit(grandchild)

    for child in paragraph:
        visit(child)
    return "".join(parts)


def _walk_docx_table(table: Any, accumulator: _LineAccumulator) -> None:
    for row in table:
        if _local_name(row.tag) != "tr":
            continue
        cells: List[str] = []
        for cell in row:
            if _local_name(cell.tag) != "tc":
                continue
            cell_accumulator = _LineAccumulator()
            _walk_docx_blocks(cell, cell_accumulator)
            cell_text = " ".join(
                line.strip() for line in cell_accumulator.lines if line.strip()
            )
            cells.append(cell_text)
        row_text = " | ".join(cells).strip(" |")
        if row_text:
            accumulator.add(row_text)


# ---------------------------------------------------------------------------
# xlsx（xl/sharedStrings.xml + xl/worksheets/sheet*.xml）
# ---------------------------------------------------------------------------

_SHEET_NAME_RE = re.compile(r"^xl/worksheets/sheet(\d+)\.xml$")
_SLIDE_NAME_RE = re.compile(r"^ppt/slides/slide(\d+)\.xml$")


def _extract_xlsx(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        shared = _read_xlsx_shared_strings(archive)
        sheet_names = sorted(
            (name for name in names if _SHEET_NAME_RE.match(name)),
            key=lambda name: int(_SHEET_NAME_RE.match(name).group(1)),
        )
        if not sheet_names:
            raise ValueError("xlsx has no worksheets")

        accumulator = _LineAccumulator()
        for index, sheet_path in enumerate(sheet_names, 1):
            sheet_accumulator = _LineAccumulator()
            _extract_xlsx_sheet(archive.read(sheet_path), shared, sheet_accumulator)
            if not sheet_accumulator.lines:
                continue
            accumulator.add(f"--- 工作表 {index} ---")
            for line in sheet_accumulator.lines:
                accumulator.add(line)

    body = accumulator.text()
    if not body.strip():
        raise ValueError("xlsx has no readable text")
    return body


def _read_xlsx_shared_strings(archive: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: List[str] = []
    for node in root.iter():
        if _local_name(node.tag) != "si":
            continue
        parts = [
            child.text or ""
            for child in node.iter()
            if _local_name(child.tag) == "t"
        ]
        values.append("".join(parts))
    return values


def _extract_xlsx_sheet(
    xml_bytes: bytes,
    shared: List[str],
    accumulator: _LineAccumulator,
) -> None:
    root = ET.fromstring(xml_bytes)
    for row in root.iter():
        if _local_name(row.tag) != "row":
            continue
        cells: List[str] = []
        for cell in row.iter():
            if _local_name(cell.tag) != "c":
                continue
            cells.append(_xlsx_cell_value(cell, shared))
        row_text = "\t".join(cells).rstrip("\t")
        if row_text.strip():
            accumulator.add(row_text)


def _xlsx_cell_value(cell: Any, shared: List[str]) -> str:
    cell_type = (cell.get("t") or "").strip()
    if cell_type == "inlineStr":
        parts = [
            node.text or ""
            for node in cell.iter()
            if _local_name(node.tag) == "t"
        ]
        return "".join(parts)

    value: Optional[str] = None
    for node in cell.iter():
        if _local_name(node.tag) == "v":
            value = node.text or ""
            break
    if value is None:
        return ""
    if cell_type == "s":
        try:
            return shared[int(value)]
        except (ValueError, IndexError):
            return value
    return value


# ---------------------------------------------------------------------------
# pptx（ppt/slides/slide*.xml）
# ---------------------------------------------------------------------------


def _extract_pptx(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        slide_names = sorted(
            (name for name in archive.namelist() if _SLIDE_NAME_RE.match(name)),
            key=lambda name: int(_SLIDE_NAME_RE.match(name).group(1)),
        )
        if not slide_names:
            raise ValueError("pptx has no slides")

        accumulator = _LineAccumulator()
        for index, slide_path in enumerate(slide_names, 1):
            slide_accumulator = _LineAccumulator()
            root = ET.fromstring(archive.read(slide_path))
            for node in root.iter():
                if _local_name(node.tag) != "t":
                    continue
                text = (node.text or "").strip()
                if text:
                    slide_accumulator.add(text)
            if slide_accumulator.lines:
                accumulator.add(f"--- 幻灯片 {index} ---")
                for line in slide_accumulator.lines:
                    accumulator.add(line)

    body = accumulator.text()
    if not body.strip():
        raise ValueError("pptx has no readable text")
    return body
