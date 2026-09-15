"""
Paper Deep Read - PDF Parser Module.

Extracts structured content from academic PDF papers with quality assessment.
Supports pdfplumber and PyMuPDF (fitz) as parsing backends.

Functions:
- parse_pdf(pdf_path, output_path, quality_check): Main entry point
- assess_quality(result): Evaluate extraction quality (0-100 score)
- render_pages(pdf_path, output_dir, dpi): Render pages to PNG images
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ── Section detection patterns ──────────────────────────────────────────────
SECTION_PATTERNS = [
    r"(?i)^[\d\s]*abstract\b",
    r"(?i)^[\d\s]*introduction\b",
    r"(?i)^[\d\s]*(?:related\s+work|background|preliminaries?)\b",
    r"(?i)^[\d\s]*(?:method(?:ology|s)?|approach|proposed\s+method|our\s+approach|framework)\b",
    r"(?i)^[\d\s]*(?:experiment|evaluation|results?|empirical)\b",
    r"(?i)^[\d\s]*(?:ablation|analysis|discussion)\b",
    r"(?i)^[\d\s]*(?:conclusion|summary|future\s+work)\b",
    r"(?i)^[\d\s]*references?\b",
    r"(?i)^[\d\s]*appendix\b",
]


def _check_dependencies():
    """Check that at least one PDF backend is available."""
    if pdfplumber is None and fitz is None:
        raise ImportError(
            "No PDF backend available. Install at least one:\n"
            "  pip install pdfplumber pymupdf"
        )


def detect_sections(text_blocks: List[Dict]) -> List[Dict]:
    """
    Scan text blocks to identify section boundaries.
    Returns list of {page, block_idx, section_name, raw_text}.
    """
    sections = []
    for block in text_blocks:
        text = block.get("text", "").strip()
        if not text or len(text) > 200:
            continue
        for pattern in SECTION_PATTERNS:
            if re.match(pattern, text):
                name = re.sub(r"^[\d\s.]+", "", text).strip()
                sections.append({
                    "page": block["page"],
                    "block_idx": block["block_idx"],
                    "section_name": name,
                    "raw_text": text,
                })
                break
    return sections


def extract_text_with_layout(pdf_path: str) -> List[Dict]:
    """Extract text blocks with layout info using pdfplumber."""
    if pdfplumber is None:
        raise ImportError("pdfplumber is required for layout extraction. pip install pdfplumber")
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text(layout=True) or ""
            if text.strip():
                blocks.append({
                    "page": page_num + 1,
                    "block_idx": len(blocks),
                    "text": text,
                    "type": "text_block",
                })
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                if table and len(table) > 1:
                    blocks.append({
                        "page": page_num + 1,
                        "block_idx": len(blocks),
                        "text": json.dumps(table, ensure_ascii=False),
                        "type": "table",
                        "table_idx": t_idx,
                    })
    return blocks


def extract_text_with_fitz(pdf_path: str) -> str:
    """Extract full text using PyMuPDF as fallback/enhancement."""
    if fitz is None:
        raise ImportError("pymupdf is required for fitz extraction. pip install pymupdf")
    doc = fitz.open(pdf_path)
    full_text = ""
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
    doc.close()
    return full_text


def extract_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract PDF metadata (title, authors, etc.)."""
    if fitz is None:
        return {"title": "", "author": "", "page_count": 0, "source": pdf_path}
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    info = {
        "title": meta.get("title", "") or "",
        "author": meta.get("author", "") or "",
        "subject": meta.get("subject", "") or "",
        "keywords": meta.get("keywords", "") or "",
        "page_count": len(doc),
    }
    doc.close()
    return info


def extract_formulas_from_text(text: str) -> List[Dict]:
    """
    Identify formula-like regions in extracted text.
    Detects: $...$ inline math, $$...$$ display math, and heuristic math-symbol-dense lines.
    """
    formulas = []

    # $...$ inline math
    for m in re.finditer(r'\$([^$]{3,200}?)\$', text):
        formulas.append({
            "type": "inline",
            "formula": m.group(1).strip(),
            "context": text[max(0, m.start()-100):m.end()+100],
        })

    # $$...$$ display math
    for m in re.finditer(r'\$\$([^$]{10,1000}?)\$\$', text, re.DOTALL):
        formulas.append({
            "type": "display",
            "formula": m.group(1).strip(),
            "context": "",
        })

    # Heuristic: lines dominated by math symbols
    math_pat = re.compile(
        r'[\w\s]*[∑∏∫∂∇√±≤≥≠≈∈∉⊂⊃∪∩∧∨∀∃¬→↔⇒⇐'
        r'αβγδεζηθλμνπρστωφχψωΔΩΓΛΣΦΨ'
        r'|\\frac|\\mathbb|\\mathcal|\\sum|\\prod|\\int|\\lim'
        r'|\\frac\{.*?\}\{.*?\}|\\sqrt\{.*?\}]',
        re.IGNORECASE,
    )
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and len(stripped) > 5:
            matches = math_pat.findall(stripped)
            if len(matches) >= 3 and len(matches) / max(len(stripped), 1) > 0.15:
                formulas.append({
                    "type": "heuristic_line",
                    "formula": stripped,
                    "context": "\n".join(lines[max(0, i-2):i+3]),
                })

    return formulas


def render_pages(pdf_path: str, output_dir: str, dpi: int = 200) -> List[str]:
    """
    Render PDF pages to PNG images for VLM/OCR fallback.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save page images.
        dpi: Resolution in DPI (default 200).

    Returns:
        List of saved image file paths.
    """
    if fitz is None:
        raise ImportError("pymupdf is required for page rendering. pip install pymupdf")
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img_path = os.path.join(output_dir, f"page_{page_num + 1:04d}.png")
        pix.save(img_path)
        image_paths.append(img_path)
    doc.close()
    return image_paths


def assess_quality(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess PDF extraction quality with a 0-100 score and detailed report.

    Checks:
    1. Garbled text (replacement char ratio)
    2. Formula extraction quality
    3. Text misalignment (column merging)
    4. Empty key sections
    5. Missing tables in experiments

    Returns:
        dict with: score (int), level (str), issues (list), recommendation (str)
    """
    issues = []
    score = 100

    full_text = result.get("full_text", "")
    sections = result.get("sections", [])
    stats = result.get("stats", {})
    formulas = result.get("formulas", [])

    # Check 1: Garbled text
    repl_count = full_text.count("\ufffd")
    repl_ratio = repl_count / max(len(full_text), 1)
    if repl_ratio > 0.01:
        severity = "CRITICAL" if repl_ratio > 0.05 else "HIGH"
        deduction = 30 if repl_ratio > 0.05 else 15
        score -= deduction
        issues.append({
            "check": "garbled_text",
            "severity": severity,
            "detail": f"{repl_count} replacement chars ({repl_ratio:.2%})",
            "deduction": deduction,
        })

    # Check 2: Formula quality
    section_names = [s["section_name"].lower() for s in sections]
    has_method = any(kw in n for kw in ["method", "approach", "framework", "model"] for n in section_names)
    formula_count = stats.get("total_formulas", 0)
    if has_method and formula_count == 0:
        score -= 10
        issues.append({
            "check": "no_formulas_in_method",
            "severity": "MEDIUM",
            "detail": "Method section found but 0 formulas (may be image-based)",
            "deduction": 10,
        })
    alpha_pat = re.compile(r'[a-zA-Z]')
    bad_formulas = sum(1 for f in formulas if len(f.get("formula", "")) > 3 and not alpha_pat.search(f["formula"]))
    if bad_formulas > 0:
        deduction = min(10, bad_formulas * 3)
        score -= deduction
        issues.append({
            "check": "formula_quality",
            "severity": "HIGH" if bad_formulas > 3 else "MEDIUM",
            "detail": f"{bad_formulas}/{len(formulas)} formulas are extraction artifacts",
            "deduction": deduction,
        })

    # Check 3: Text misalignment
    lines = [l for l in full_text.split("\n") if l.strip()]
    if lines:
        lengths = [len(l.strip()) for l in lines]
        avg = sum(lengths) / len(lengths)
        outliers = sum(1 for l in lengths if l > avg * 3) + sum(1 for l in lengths if avg * 0.2 < l < avg * 0.5)
        outlier_count = outliers  # already an int
        if outlier_count / len(lengths) > 0.3:
            score -= 15
            issues.append({
                "check": "text_misalignment",
                "severity": "HIGH",
                "detail": f"{outliers/len(lengths):.1%} outlier lines (possible column merge)",
                "deduction": 15,
            })

    # Check 4: No sections detected
    if len(sections) == 0 and len(full_text) > 500:
        score -= 20
        issues.append({
            "check": "no_sections_detected",
            "severity": "HIGH",
            "detail": "0 sections detected (headers may be non-standard)",
            "deduction": 20,
        })

    # Check 5: Missing tables
    table_count = stats.get("total_tables", 0)
    has_exp = any(kw in n for kw in ["experiment", "result", "evaluation"] for n in section_names)
    if has_exp and table_count == 0:
        score -= 5
        issues.append({
            "check": "missing_tables",
            "severity": "MEDIUM",
            "detail": "Experiments section but 0 tables extracted",
            "deduction": 5,
        })

    score = max(0, min(100, score))
    if score >= 70:
        level, rec = "good", "Extraction quality is acceptable."
    elif score >= 40:
        level, rec = "degraded", "Quality degraded. Use VLM or OCR fallback."
    else:
        level, rec = "critical", "Critically low quality. Must use VLM or OCR."

    return {"score": score, "level": level, "issues": issues, "recommendation": rec}


def parse_pdf(pdf_path: str, output_path: Optional[str] = None, quality_check: bool = True) -> Dict[str, Any]:
    """
    Parse a PDF paper into structured data.

    Args:
        pdf_path: Path to the PDF file.
        output_path: Optional path to save JSON output.
        quality_check: Whether to run quality assessment (default True).

    Returns:
        Structured dictionary with paper content and optional quality report.
    """
    _check_dependencies()

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Metadata
    metadata = extract_metadata(pdf_path)

    # Text extraction
    text_blocks = []
    if pdfplumber:
        text_blocks = extract_text_with_layout(pdf_path)

    full_text = ""
    if fitz:
        full_text = extract_text_with_fitz(pdf_path)
    elif text_blocks:
        full_text = "\n".join(b.get("text", "") for b in text_blocks)

    # Sections
    sections = detect_sections(text_blocks) if text_blocks else []

    # Formulas
    formulas = extract_formulas_from_text(full_text)

    # Build result
    result = {
        "metadata": metadata,
        "sections": sections,
        "content_blocks": text_blocks,
        "full_text": full_text,
        "formulas": formulas,
        "stats": {
            "total_pages": metadata.get("page_count", 0),
            "total_text_blocks": sum(1 for b in text_blocks if b["type"] == "text_block"),
            "total_tables": sum(1 for b in text_blocks if b["type"] == "table"),
            "total_formulas": len(formulas),
            "sections_found": [s["section_name"] for s in sections],
        },
    }

    # Quality assessment
    if quality_check:
        result["quality"] = assess_quality(result)

    # Output
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Paper Deep Read - Parse academic PDFs into structured data.",
    )
    parser.add_argument("pdf_path", help="Path to the PDF paper file.")
    parser.add_argument("-o", "--output", help="Output JSON file path.")
    parser.add_argument("--no-quality-check", action="store_true",
                        help="Skip quality assessment (enabled by default).")
    parser.add_argument("--render-pages", metavar="DIR",
                        help="Render PDF pages to PNG images in DIR.")
    args = parser.parse_args()

    if args.render_pages:
        pages = render_pages(args.pdf_path, args.render_pages)
        print(f"Rendered {len(pages)} pages to {args.render_pages}")
        return

    result = parse_pdf(args.pdf_path, args.output, quality_check=not args.no_quality_check)

    if args.output:
        print(f"Output saved to: {args.output}")
        if "quality" in result:
            q = result["quality"]
            print(f"Quality: {q['score']}/100 ({q['level']})")
    else:
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
        sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()
