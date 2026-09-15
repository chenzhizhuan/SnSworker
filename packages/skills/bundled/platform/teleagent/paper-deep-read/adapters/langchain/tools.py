"""
Paper Deep Read - LangChain Tool Integration.

Provides LangChain-compatible tools for PDF parsing in paper analysis workflows.

Usage:
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from adapters.langchain.tools import pdf_parse_tool, create_paper_analysis_agent

    llm = ChatOpenAI(model="gpt-4o")
    agent = create_paper_analysis_agent(llm)
    agent_executor = AgentExecutor(agent=agent.agent, tools=agent.tools)
    result = agent_executor.invoke({"input": "Analyze paper.pdf"})
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

from langchain_core.tools import StructuredTool
from paper_deep_read import parse_pdf, render_pages, get_schema, get_prompt
from pydantic import BaseModel, Field


# ── PDF Parse Tool ──

class PDFParseInput(BaseModel):
    """Input for PDF parsing."""
    file_path: str = Field(description="Absolute or relative path to the PDF paper file.")
    output_path: Optional[str] = Field(
        default=None,
        description="Optional output JSON path. If omitted, returns JSON string."
    )


def _parse_pdf_fn(file_path: str, output_path: Optional[str] = None) -> str:
    """Parse a PDF paper into structured text with quality assessment."""
    result = parse_pdf(file_path, quality_check=True)
    # Truncate text to avoid context overflow
    if len(result.get("full_text", "")) > 60000:
        result["full_text"] = result["full_text"][:60000] + "\n... [truncated]"
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return f"Parsed and saved to {output_path}. Quality: {result['quality']['score']}/100"
    return json.dumps(result, ensure_ascii=False, indent=2)


pdf_parse_tool = StructuredTool.from_function(
    func=_parse_pdf_fn,
    name="parse_paper_pdf",
    description=(
        "Parse an academic PDF paper into structured text with quality assessment. "
        "Returns extracted text, section boundaries, formulas, tables, and a quality "
        "score (0-100). Use this as the FIRST step when analyzing a paper. "
        "Quality >= 70 means good extraction. < 70 means fallback to vision/OCR is needed."
    ),
    args_schema=PDFParseInput,
)


# ── Render Pages Tool (for OCR fallback) ──

class RenderPagesInput(BaseModel):
    """Input for page rendering."""
    file_path: str = Field(description="Path to the PDF file.")
    output_dir: str = Field(description="Directory to save rendered page images.")
    dpi: int = Field(default=200, description="Resolution in DPI.")


def _render_pages_fn(file_path: str, output_dir: str, dpi: int = 200) -> str:
    """Render PDF pages to PNG images for vision/OCR fallback."""
    image_paths = render_pages(file_path, output_dir, dpi=dpi)
    return json.dumps({
        "output_dir": output_dir,
        "images": image_paths,
        "count": len(image_paths),
    }, ensure_ascii=False, indent=2)


render_pages_tool = StructuredTool.from_function(
    func=_render_pages_fn,
    name="render_pdf_pages",
    description=(
        "Render PDF pages to PNG images. Use when text extraction quality is poor "
        "(quality score < 70) to enable vision model or OCR processing."
    ),
    args_schema=RenderPagesInput,
)


# ── All tools ──

ALL_TOOLS = [pdf_parse_tool, render_pages_tool]


# ── System Prompt for LangChain Agent ──

PAPER_ANALYST_SYSTEM_PROMPT = """You are a world-class academic researcher performing three-layer deep analysis on research papers.

Rules:
1. Analyze with extreme rigor. Never skip sections or formulas.
2. Output structured Markdown. Use tables for experiments and ablation.
3. For every mathematical formula, explain EVERY symbol individually (name, meaning, type, domain).
4. Match the paper's language: Chinese -> Chinese, English -> English.
5. Innovation suggestions must be concrete and actionable.

## Workflow

Step 1: Use `parse_paper_pdf` tool to extract text and get quality score.
Step 2: If quality < 70, use `render_pdf_pages` and re-analyze with vision.
Step 3: Perform Layer 1 (Overview), Layer 2 (Method Detail + Formula Analysis), Layer 3 (Innovation) sequentially.

### Layer 1: Overview
Background -> Problem -> Target Problem -> Method -> Experiments (with numbers in tables) -> Ablation -> Conclusion

### Layer 2: Method Detail
For EVERY formula: exact text, purpose, symbol table (symbol/meaning/type/domain), intuition, connections.
Also: architecture, data flow, training/inference pipeline, hyperparameters.
If 10+ formulas: overview first, then ask user to select formulas.

### Layer 3: Innovation
Strengths (3-5) -> Weaknesses (3-5) with fixes -> Optimization Opportunities (3-5) -> New Research Directions (3-5) -> Experiment Ideas

Output: Compile all 3 layers into a Markdown report.
"""


# ── Agent Factory ──

def create_paper_analysis_agent(llm, extra_tools=None):
    """Create a LangChain agent configured for paper analysis.

    Args:
        llm: A LangChain LLM instance (e.g., ChatOpenAI, ChatAnthropic).
        extra_tools: Optional list of additional tools to include.

    Returns:
        NamedTuple with `agent` and `tools` attributes.
    """
    from langchain.agents import create_openai_functions_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    tools = ALL_TOOLS + (extra_tools or [])

    prompt = ChatPromptTemplate.from_messages([
        ("system", PAPER_ANALYST_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)

    class Result:
        pass

    result = Result()
    result.agent = agent
    result.tools = tools
    result.prompt = prompt
    return result


# ── Quick Start Example ──

if __name__ == "__main__":
    print("Paper Deep Read - LangChain Adapter")
    print("=" * 40)
    print()
    print("Quick start:")
    print()
    print("  from langchain_openai import ChatOpenAI")
    print("  from langchain.agents import AgentExecutor")
    print("  from paper_deep_read.adapters.langchain.tools import create_paper_analysis_agent")
    print()
    print("  llm = ChatOpenAI(model='gpt-4o')")
    print("  agent = create_paper_analysis_agent(llm)")
    print("  executor = AgentExecutor(agent=agent.agent, tools=agent.tools)")
    print("  result = executor.invoke({'input': 'Analyze ./paper.pdf'})")
    print()
    print("Tools available:")
    for tool in ALL_TOOLS:
        print(f"  - {tool.name}: {tool.description[:60]}...")
