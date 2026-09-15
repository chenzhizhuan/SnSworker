"""
Paper Deep Read - Academic Paper Analysis Toolkit.

A cross-platform Python package for parsing academic PDFs and providing
structured schemas/prompts for three-layer progressive paper analysis.

Core modules:
- parser: PDF parsing with quality assessment and page rendering
- schemas: JSON schemas for three-layer analysis output
- prompts: Prompt templates for three-layer analysis

Usage:
    from paper_deep_read import parse_pdf, assess_quality, render_pages
    result = parse_pdf("paper.pdf", quality_check=True)
    quality = assess_quality(result)
"""

__version__ = "1.0.0"
__all__ = [
    "parse_pdf",
    "assess_quality",
    "render_pages",
    "get_schema",
    "get_prompt",
    "LAYER1_SCHEMA",
    "LAYER2_SCHEMA",
    "LAYER3_SCHEMA",
]

from .parser import parse_pdf, assess_quality, render_pages
from .schemas import LAYER1_SCHEMA, LAYER2_SCHEMA, LAYER3_SCHEMA, get_schema
from .prompts import SYSTEM_PROMPT, get_prompt
