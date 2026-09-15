"""
Dify Tool: PDF Parser for Paper Deep Read.

This is a Dify custom tool that wraps the paper_deep_read Python package.
Install it in Dify as a "Custom Tool" under the Tools section.

Setup in Dify:
1. Go to Settings -> Tools -> Add Custom Tool
2. Upload this file or paste its content
3. Configure the Python environment with: pip install paper-deep-read pdfplumber pymupdf

Identity:
  Name: pdf_parser
  Label: PDF Paper Parser
  Description: Parse academic PDF papers into structured text with quality assessment.
"""

import json
import os
import tempfile
from paper_deep_read import parse_pdf, render_pages


class PDFParserTool:
    """Dify custom tool for parsing academic PDFs."""

    name = "pdf_parser"
    description = (
        "Parse an academic PDF paper into structured text content with quality assessment. "
        "Returns extracted text, section boundaries, formulas, and a quality score (0-100). "
        "Use this as the first step before analyzing a paper."
    )
    parameters = [
        {
            "name": "pdf_file",
            "type": "file",
            "required": True,
            "description": "The PDF paper file to parse.",
        }
    ]

    def _run(self, pdf_file) -> str:
        """Execute PDF parsing.

        Args:
            pdf_file: Dify File object (has .path attribute for temporary file path).

        Returns:
            JSON string with parsed content and quality assessment.
        """
        # Dify stores uploaded files temporarily; pdf_file might be a path string
        if isinstance(pdf_file, str):
            file_path = pdf_file
        elif hasattr(pdf_file, "path"):
            file_path = pdf_file.path
        else:
            # Fallback: write bytes to temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.write(pdf_file.read() if hasattr(pdf_file, "read") else pdf_file)
            tmp.close()
            file_path = tmp.name

        try:
            result = parse_pdf(file_path, quality_check=True)
            # Trim full_text to avoid context overflow (keep first 50000 chars)
            if len(result.get("full_text", "")) > 50000:
                result["full_text"] = result["full_text"][:50000] + "\n... [truncated]"
            return json.dumps(result, ensure_ascii=False, indent=2)
        finally:
            # Clean up temp file
            if file_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(file_path)
                except OSError:
                    pass


class PageRendererTool:
    """Dify custom tool for rendering PDF pages to images (for OCR fallback)."""

    name = "page_renderer"
    description = (
        "Render PDF pages to PNG images. Use this when PDF text extraction quality is poor "
        "(quality score < 70). The rendered images can then be processed by a vision model or OCR."
    )
    parameters = [
        {
            "name": "pdf_file",
            "type": "file",
            "required": True,
            "description": "The PDF paper file.",
        },
        {
            "name": "dpi",
            "type": "number",
            "required": False,
            "default": 200,
            "description": "Resolution in DPI (default 200).",
        },
    ]

    def _run(self, pdf_file, dpi=200) -> str:
        """Render PDF pages to images.

        Returns:
            JSON string with list of rendered image file paths.
        """
        if isinstance(pdf_file, str):
            file_path = pdf_file
        elif hasattr(pdf_file, "path"):
            file_path = pdf_file.path
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp.write(pdf_file.read() if hasattr(pdf_file, "read") else pdf_file)
            tmp.close()
            file_path = tmp.name

        output_dir = tempfile.mkdtemp(prefix="paper_pages_")
        try:
            image_paths = render_pages(file_path, output_dir, dpi=int(dpi))
            return json.dumps({
                "output_dir": output_dir,
                "images": image_paths,
                "count": len(image_paths),
            }, ensure_ascii=False, indent=2)
        finally:
            if file_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
