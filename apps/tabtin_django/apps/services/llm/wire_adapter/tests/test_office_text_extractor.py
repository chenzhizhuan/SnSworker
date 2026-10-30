"""office_text_extractor 单测：docx/xlsx/pptx/纯文本本地提取。

fixture 全部用 ``zipfile`` 在内存构造最小合法 OOXML，零外部依赖；
断言覆盖中文文本、表格行、共享字符串、多工作表/多幻灯片、编码
（UTF-8 / GB18030 / BOM）与非 office 内容的负向判定。
"""

from __future__ import annotations

import io
import zipfile

from django.test import SimpleTestCase

from apps.services.llm.wire_adapter.office_text_extractor import (
    extract_office_text_for_model,
    extract_text_document_for_model,
)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _build_docx(paragraph_xml: str) -> bytes:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}"><w:body>{paragraph_xml}</w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
        archive.writestr("[Content_Types].xml", "<Types/>")
    return buffer.getvalue()


def _build_xlsx(parts: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheets>"
            '<sheet name="Sheet1" sheetId="1"/>'
            "</sheets></workbook>",
        )
        for name, xml in parts.items():
            archive.writestr(name, xml)
    return buffer.getvalue()


def _build_pptx(parts: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "ppt/presentation.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<presentation xmlns="http://schemas.openxmlformats.org/presentationml/2006/main"/>',
        )
        for name, xml in parts.items():
            archive.writestr(name, xml)
    return buffer.getvalue()


class ExtractDocxTextTests(SimpleTestCase):
    def test_paragraphs_table_and_tab(self):
        content = _build_docx(
            "<w:p><w:r><w:t>第一章 招标公告</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>项目名称：</w:t></w:r>"
            "<w:r><w:tab/></w:r>"
            "<w:r><w:t>某某大厦安防系统</w:t></w:r></w:p>"
            "<w:tbl><w:tr>"
            "<w:tc><w:p><w:r><w:t>序号</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>货物名称</w:t></w:r></w:p></w:tc>"
            "</w:tr><w:tr>"
            "<w:tc><w:p><w:r><w:t>1</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>高清摄像机</w:t></w:r></w:p></w:tc>"
            "</w:tr></w:tbl>"
        )

        text = extract_office_text_for_model(content, filename="招标文件.docx")

        self.assertIsNotNone(text)
        self.assertIn("[文档附件 · Word 文档] 文件名：招标文件.docx", text)
        self.assertIn("第一章 招标公告", text)
        self.assertIn("项目名称：\t某某大厦安防系统", text)
        self.assertIn("序号 | 货物名称", text)
        self.assertIn("1 | 高清摄像机", text)

    def test_empty_docx_raises_value_error(self):
        content = _build_docx("<w:p><w:r><w:t>   </w:t></w:r></w:p>")

        with self.assertRaises(ValueError):
            extract_office_text_for_model(content, filename="empty.docx")

    def test_extension_fallback_on_broken_zip(self):
        # zip 头损坏但扩展名明确 → 仍按 docx 解析 → 抛错由调用方回退
        content = b"PK\x03\x04 broken-not-a-zip"

        with self.assertRaises(Exception):
            extract_office_text_for_model(content, filename="broken.docx")


class ExtractXlsxTextTests(SimpleTestCase):
    def test_shared_strings_inline_and_numbers(self):
        shared = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<si><t>货物名称</t></si>"
            "<si><t>高清摄像机</t></si>"
            "</sst>"
        )
        sheet1 = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
            '<row r="2"><c r="A2"><v>1</v></c><c r="B2"><v>128</v></c></row>'
            "</sheetData></worksheet>"
        )
        sheet2 = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            "<sheetData>"
            '<row r="1"><c r="A1" t="inlineStr"><is><t>第二工作表</t></is></c></row>'
            "</sheetData></worksheet>"
        )
        content = _build_xlsx(
            {
                "xl/sharedStrings.xml": shared,
                "xl/worksheets/sheet1.xml": sheet1,
                "xl/worksheets/sheet2.xml": sheet2,
            }
        )

        text = extract_office_text_for_model(content, filename="清单.xlsx")

        self.assertIsNotNone(text)
        self.assertIn("[文档附件 · Excel 工作簿] 文件名：清单.xlsx", text)
        self.assertIn("--- 工作表 1 ---", text)
        self.assertIn("--- 工作表 2 ---", text)
        self.assertIn("货物名称\t高清摄像机", text)
        self.assertIn("1\t128", text)
        self.assertIn("第二工作表", text)

    def test_xlsx_without_sheets_raises(self):
        content = _build_xlsx({})

        with self.assertRaises(ValueError):
            extract_office_text_for_model(content, filename="empty.xlsx")


class ExtractPptxTextTests(SimpleTestCase):
    def test_slides_in_numeric_order(self):
        slide_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<p:cSld><p:spTree><p:sp><p:txBody>"
            "<a:p><a:r><a:t>{text}</a:t></a:r></a:p>"
            "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>"
        )
        content = _build_pptx(
            {
                "ppt/slides/slide1.xml": slide_xml.format(text="投标单位资质要求"),
                "ppt/slides/slide10.xml": slide_xml.format(text="第十页：评分办法"),
                "ppt/slides/slide2.xml": slide_xml.format(text="项目概况"),
            }
        )

        text = extract_office_text_for_model(content, filename="汇报.pptx")

        self.assertIsNotNone(text)
        self.assertIn("[文档附件 · PowerPoint 演示文稿] 文件名：汇报.pptx", text)
        # slide10 必须排在 slide2 之后（数值序而非字典序）
        self.assertLess(text.index("投标单位资质要求"), text.index("项目概况"))
        self.assertLess(text.index("项目概况"), text.index("第十页：评分办法"))
        self.assertIn("--- 幻灯片 1 ---", text)
        self.assertIn("--- 幻灯片 3 ---", text)


class ExtractTextDocumentTests(SimpleTestCase):
    def test_utf8_txt(self):
        content = "第一行：招标编号 ABC-2026\n第二行：截止时间 2026-11-05".encode(
            "utf-8"
        )

        text = extract_text_document_for_model(content, filename="公告.txt")

        self.assertIsNotNone(text)
        self.assertIn("招标编号 ABC-2026", text)

    def test_gb18030_txt(self):
        content = "中文内容：货物需求一览表".encode("gb18030")

        text = extract_text_document_for_model(
            content, filename="需求.txt", mime_type="text/plain"
        )

        self.assertIsNotNone(text)
        self.assertIn("货物需求一览表", text)

    def test_utf8_bom_csv(self):
        content = "列A,列B\n1,2".encode("utf-8-sig")

        text = extract_text_document_for_model(content, filename="data.csv")

        self.assertIsNotNone(text)
        self.assertTrue(text.startswith("列A"), text[:10])

    def test_binary_content_returns_none(self):
        self.assertIsNone(
            extract_text_document_for_model(b"\x00\x01\x02\xff", filename="x.bin")
        )
        self.assertIsNone(
            extract_text_document_for_model(b"%PDF-1.7 fake", filename="x.pdf")
        )

    def test_unknown_mime_binary_sniff_returns_none(self):
        # octet-stream + 高比例不可打印 → 不当文本处理
        content = bytes(range(256)) * 4

        self.assertIsNone(
            extract_text_document_for_model(
                content, filename="noext", mime_type="application/octet-stream"
            )
        )


class OfficeKindDetectionTests(SimpleTestCase):
    def test_non_office_content_returns_none(self):
        # PDF 走 pdf_text_extractor，不进 office 分支
        self.assertIsNone(
            extract_office_text_for_model(b"%PDF-1.7 fixture", filename="x.pdf")
        )
        # 普通文本
        self.assertIsNone(
            extract_office_text_for_model("纯文本".encode("utf-8"), filename="x.txt")
        )
        # 无 office part 的 zip
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("readme.txt", "not office")
        self.assertIsNone(
            extract_office_text_for_model(buffer.getvalue(), filename="x.zip")
        )

    def test_zip_bomb_guard_truncates(self):
        # 巨量段落触发 5M 字符护栏：不抛 MemoryError，打截断标记
        paragraph = "<w:p><w:r><w:t>{filler}</w:t></w:r></w:p>".format(
            filler="字" * 500
        )
        content = _build_docx(paragraph * 20000)

        text = extract_office_text_for_model(content, filename="big.docx")

        self.assertIsNotNone(text)
        self.assertLessEqual(len(text), 6_000_000)
        self.assertIn("已截断", text)
