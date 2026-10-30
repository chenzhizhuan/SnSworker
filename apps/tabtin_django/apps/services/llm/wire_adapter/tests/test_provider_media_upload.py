"""通用 Files API / base64 媒体上传辅助单测。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.services.llm.wire_adapter.provider_media_upload import (
    extract_document_text_via_files_api,
    fetch_file_extract_content,
    to_data_video_url,
    to_provider_file_url,
    upload_media_bytes,
)


class ProviderMediaUploadHelpersTests(SimpleTestCase):

    def test_to_provider_file_url(self):
        self.assertEqual(to_provider_file_url("file-1", "ms://"), "ms://file-1")
        self.assertEqual(to_provider_file_url("ms://file-1", "ms://"), "ms://file-1")
        self.assertEqual(to_provider_file_url("file-1", "ms"), "ms://file-1")

    def test_to_data_video_url(self):
        url = to_data_video_url(b"abc", "video/mp4")
        self.assertTrue(url.startswith("data:video/mp4;base64,"))
        self.assertIn("YWJj", url)

    def test_upload_media_bytes_posts_multipart(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "file-xyz"}
        mock_resp.text = ""

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload.httpx.Client",
            return_value=mock_client,
        ):
            file_id = upload_media_bytes(
                api_base="https://api.moonshot.cn/v1",
                api_key="sk-test",
                content=b"video-bytes",
                filename="clip.mov",
                purpose="video",
                endpoint="/files",
                id_field="id",
            )

        self.assertEqual(file_id, "file-xyz")
        kwargs = mock_client.post.call_args.kwargs
        self.assertEqual(kwargs["data"]["purpose"], "video")
        self.assertEqual(kwargs["files"]["file"][0], "clip.mov")
        self.assertEqual(kwargs["files"]["file"][1], b"video-bytes")
        self.assertEqual(
            mock_client.post.call_args.args[0],
            "https://api.moonshot.cn/v1/files",
        )

    def test_fetch_file_extract_content(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "extracted body"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload.httpx.Client",
            return_value=mock_client,
        ):
            text = fetch_file_extract_content(
                api_base="https://api.moonshot.cn/v1",
                api_key="sk-test",
                file_id="file-abc",
            )

        self.assertEqual(text, "extracted body")
        self.assertEqual(
            mock_client.get.call_args.args[0],
            "https://api.moonshot.cn/v1/files/file-abc/content",
        )

    def test_extract_document_text_via_files_api_upload_get_delete(self):
        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload.upload_media_bytes",
            return_value="file-doc-1",
        ) as upload_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.fetch_file_extract_content",
            return_value="hello from pdf",
        ) as content_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.delete_uploaded_file",
        ) as delete_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_get",
            return_value=None,
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_put",
        ):
            text = extract_document_text_via_files_api(
                api_base="https://api.moonshot.cn/v1",
                api_key="sk-test",
                content=b"%PDF",
                filename="x.pdf",
                purpose="file-extract",
                use_cache=True,
                cleanup_remote=True,
            )

        self.assertEqual(text, "hello from pdf")
        upload_mock.assert_called_once()
        content_mock.assert_called_once()
        delete_mock.assert_called_once()
        self.assertEqual(upload_mock.call_args.kwargs["purpose"], "file-extract")

    def test_pdf_uses_local_docparse_instead_of_stale_provider_extract(self):
        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_get",
            return_value=None,
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_put",
        ) as cache_put_mock, patch(
            "apps.services.llm.wire_adapter.pdf_text_extractor.extract_pdf_text_for_model",
            return_value='[PDF 文档元数据] {"total_pages": 23}\n\n--- Page 23 ---\nLegal',
        ) as local_extract_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.upload_media_bytes",
        ) as upload_mock:
            text = extract_document_text_via_files_api(
                api_base="https://api.moonshot.cn/v1",
                api_key="sk-test",
                content=b"%PDF-1.7 fixture",
                filename="How-Anthropic.pdf",
            )

        self.assertIn('"total_pages": 23', text)
        self.assertIn("Legal", text)
        local_extract_mock.assert_called_once()
        upload_mock.assert_not_called()
        self.assertEqual(
            cache_put_mock.call_args.kwargs["prefix"],
            "llm:pdf_local_extract:v2:",
        )

    # ------------------------------------------------------------------
    #  本地 OOXML / 纯文本提取（自建 OpenAI 兼容端点无 Files API）
    # ------------------------------------------------------------------

    @staticmethod
    def _build_minimal_docx() -> bytes:
        import io
        import zipfile

        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            "<w:p><w:r><w:t>第一章 招标公告：本项目为某某大厦安防系统采购。</w:t></w:r></w:p>"
            "</w:body></w:document>"
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", document)
        return buffer.getvalue()

    def test_docx_uses_local_office_extract_instead_of_files_api(self):
        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_get",
            return_value=None,
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_put",
        ) as cache_put_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.upload_media_bytes",
        ) as upload_mock:
            text = extract_document_text_via_files_api(
                api_base="http://172.23.0.1:13477/v1",
                api_key="vllm-test",
                content=self._build_minimal_docx(),
                filename="招标文件.docx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
                use_cache=True,
                cleanup_remote=True,
            )

        self.assertIn("招标公告", text)
        self.assertIn("招标文件.docx", text)
        upload_mock.assert_not_called()
        self.assertEqual(
            cache_put_mock.call_args.kwargs["prefix"],
            "llm:office_local_extract:v1:",
        )

    def test_txt_attachment_uses_local_extract(self):
        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_get",
            return_value=None,
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_put",
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload.upload_media_bytes",
        ) as upload_mock:
            text = extract_document_text_via_files_api(
                api_base="http://172.23.0.1:13477/v1",
                api_key="vllm-test",
                content="招标编号：ABC-2026-001".encode("utf-8"),
                filename="公告.txt",
                mime_type="text/plain",
            )

        self.assertIn("ABC-2026-001", text)
        upload_mock.assert_not_called()

    def test_corrupt_docx_falls_back_to_files_api(self):
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "<w:document>not-valid-xml")
        corrupt_docx = buffer.getvalue()

        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_get",
            return_value=None,
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_put",
        ), patch(
            "apps.services.llm.wire_adapter.provider_media_upload.upload_media_bytes",
            return_value="file-doc-9",
        ) as upload_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.fetch_file_extract_content",
            return_value="upstream extracted text",
        ) as content_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.delete_uploaded_file",
        ):
            text = extract_document_text_via_files_api(
                api_base="https://api.moonshot.cn/v1",
                api_key="sk-test",
                content=corrupt_docx,
                filename="broken.docx",
                use_cache=True,
                cleanup_remote=True,
            )

        self.assertEqual(text, "upstream extracted text")
        upload_mock.assert_called_once()
        content_mock.assert_called_once()

    def test_office_cache_hit_short_circuits_extraction(self):
        with patch(
            "apps.services.llm.wire_adapter.provider_media_upload._file_extract_cache_get",
            return_value="缓存的 office 提取文本",
        ) as cache_get_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.extract_office_text_for_model",
        ) as office_mock, patch(
            "apps.services.llm.wire_adapter.provider_media_upload.upload_media_bytes",
        ) as upload_mock:
            text = extract_document_text_via_files_api(
                api_base="http://172.23.0.1:13477/v1",
                api_key="vllm-test",
                content=self._build_minimal_docx(),
                filename="招标文件.docx",
            )

        self.assertEqual(text, "缓存的 office 提取文本")
        office_mock.assert_not_called()
        upload_mock.assert_not_called()
        self.assertEqual(
            cache_get_mock.call_args.kwargs["prefix"],
            "llm:office_local_extract:v1:",
        )
