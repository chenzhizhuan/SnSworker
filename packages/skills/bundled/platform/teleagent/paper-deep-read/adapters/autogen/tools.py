"""
Paper Deep Read - AutoGen Tool Integration.

Provides AutoGen-compatible functions for PDF paper parsing in multi-agent workflows.

Usage:
    import autogen
    from paper_deep_read.adapters.autogen.tools import pdf_parse_func, PAPER_ANALYST_PROMPT

    assistant = autogen.AssistantAgent(
        "analyst",
        system_message=PAPER_ANALYST_PROMPT,
        llm_config=llm_config,
    )
    user_proxy = autogen.UserProxyAgent(
        "user",
        human_input_mode="NEVER",
        code_execution_config={"work_dir": "paper_analysis"},
    )
    user_proxy.initiate_chat(assistant, message="Analyze paper.pdf")
"""

from __future__ import annotations

import json
import os
from paper_deep_read import parse_pdf, render_pages


PAPER_ANALYST_PROMPT = """You are a world-class academic researcher performing three-layer deep analysis on research papers.

Rules:
1. Analyze with extreme rigor. Never skip sections or formulas.
2. Output structured Markdown with tables for experiments and ablation.
3. For EVERY formula, explain EVERY symbol (name, meaning, type, domain).
4. Match paper language: Chinese -> Chinese, English -> English.
5. Innovation suggestions must be concrete and actionable.

## Workflow

When asked to analyze a paper:

Step 1: Write and execute Python code to parse the PDF:
```python
from paper_deep_read import parse_pdf
result = parse_pdf("paper.pdf")
score = result["quality"]["score"]
print(f"Quality: {score}/100")
print(result["full_text"][:5000])
```

Step 2: Based on the parsed content, perform three-layer analysis:
- Layer 1: Overview (Background -> Problem -> Method -> Experiments -> Ablation -> Conclusion)
- Layer 2: Method Detail (every formula with symbol table, architecture, data flow)
- Layer 3: Innovation (Strengths -> Weaknesses -> Optimization -> New Directions -> Experiments)

Step 3: Compile all layers into a Markdown file and save it.
"""

# Functions that can be registered with AutoGen's function calling
PDF_PARSE_FUNCTIONS = [
    {
        "name": "parse_paper_pdf",
        "description": (
            "Parse an academic PDF paper into structured text with quality assessment. "
            "Returns text, sections, formulas, and quality score (0-100)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the PDF file.",
                },
                "output_json": {
                    "type": "string",
                    "description": "Optional path to save the parsed JSON result.",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "render_pdf_pages",
        "description": (
            "Render PDF pages to PNG images for vision/OCR fallback when text extraction fails."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the PDF."},
                "output_dir": {"type": "string", "description": "Directory for page images."},
                "dpi": {"type": "integer", "description": "Resolution (default 200)."},
            },
            "required": ["file_path", "output_dir"],
        },
    },
]


def pdf_parse_func(file_path: str, output_json: str = None) -> str:
    """AutoGen function: Parse a PDF paper."""
    result = parse_pdf(file_path, quality_check=True)
    if len(result.get("full_text", "")) > 50000:
        result["full_text"] = result["full_text"][:50000] + "\n... [truncated]"
    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return f"Saved to {output_json}. Quality: {result['quality']['score']}/100"
    return json.dumps(result, ensure_ascii=False, indent=2)


def render_pages_func(file_path: str, output_dir: str, dpi: int = 200) -> str:
    """AutoGen function: Render PDF pages to images."""
    image_paths = render_pages(file_path, output_dir, dpi=dpi)
    return json.dumps({"images": image_paths, "count": len(image_paths)}, ensure_ascii=False)


# Function map for AutoGen
FUNCTION_MAP = {
    "parse_paper_pdf": pdf_parse_func,
    "render_pdf_pages": render_pages_func,
}
