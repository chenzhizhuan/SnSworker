---
name: paper-deep-read
description: |
  Academic paper deep reading and structured analysis skill. Three-layer progressive analysis (overview, method detail, innovation) with symbol-level formula explanation and quality-aware PDF parsing. Trigger words: "精读论文", "论文精读", "论文分析", "read paper", "analyze paper", "paper review", "解读论文", "帮我读这篇论文", "论文创新点", "理解论文方法", "explain paper".
---

# Paper Deep Read

Three-layer academic paper analysis: **Overview -> Method Detail -> Innovation**.

All analysis is performed by the agent itself. The Python package handles PDF parsing and quality assessment only.

## Pipeline

```
PDF -> parse_pdf(quality_check=True) -> Assess quality
  -> score >= 70: use extracted text
  -> score < 70 + multimodal: Read tool on PDF (VLM)
  -> score < 70 + text-only: OCR fallback
-> Layer 1 Overview -> Layer 2 Method Detail -> Layer 3 Innovation -> Markdown Report
```

## Step 1: Parse PDF & Assess Quality

```bash
pip install pdfplumber pymupdf
python -m paper_deep_read <paper.pdf> -o parsed.json
```

The script always runs quality assessment (5 checks: garbled text, formula quality, text misalignment, empty sections, missing tables). Output includes `quality.score` (0-100).

**Quality thresholds:**
- `>= 70`: Good. Use extracted content.
- `40-69`: Degraded. Switch to fallback.
- `< 40`: Critical. Must use fallback.

### Fallback Chain

```
score < 70 AND model is multimodal -> Read PDF directly with Read tool (VLM understands formulas/tables natively)
score < 70 AND model is text-only  -> render pages + OCR (tencentcloud-ocr or similar)
both fail                         -> ask user
```

**Do NOT ask user which fallback.** Auto-detect model capability and proceed.

## Step 2: Layer 1 - Overview

Extract in this exact order:
1. **Background** - Research context, motivation
2. **Problem** - General problem -> specific gap -> why it matters
3. **Target Problem** - Formal statement, input/output, constraints
4. **Method** - Name, category, core idea, architecture, key components
5. **Experiments** - Datasets, baselines, main results (with **numbers**)
6. **Ablation** - What each component contributes
7. **Conclusion** - Contributions, limitations, future work

**Output format:** Structured Markdown with tables for experiments/ablation.

**Decision points:**
- Language ambiguity -> match paper's primary language, ask if truly uncertain
- 10+ formulas in paper -> offer overview-first, then user-selected deep-dive

## Step 3: Layer 2 - Method Detail

For **every** mathematical formula:

| Field | Content |
|-------|---------|
| Formula text | Exact as it appears |
| Purpose | What it computes |
| Symbol table | Each symbol: name, meaning, type, domain, shape |
| Intuition | Plain-language explanation |
| Connection | How it relates to other formulas |
| Complexity | O(...) if applicable |

Also describe: overall architecture, data flow, training/inference pipeline, hyperparameters.

**Formula template:**
```
#### Formula [id]: [brief name]
**Formula:** [exact text]
**Purpose:** ...
**Symbols:**
| Symbol | Meaning | Type | Domain |
|--------|---------|------|--------|
| ... | ... | scalar/vector/matrix/function | R^d, ... |
**Intuition:** ...
**Connection:** links to formula [x]
```

## Step 4: Layer 3 - Innovation & Optimization

1. **Strengths** (3-5) with evidence from paper
2. **Weaknesses** (3-5) with suggested fixes
3. **Optimization Opportunities** (3-5) - concrete, implementable
4. **New Research Directions** (3-5) - each with: title, motivation, connection, expected contribution, methodology sketch, target venues
5. **Experiment Ideas** - additional experiments to validate extensions

**Ask user** about their research direction to tailor suggestions.

## Step 5: Output

1. Generate Markdown report (all 3 layers) -> save to workspace
2. Use `deliver_attachments` to deliver
3. Present Layer 1 inline, offer deep-dive on Layers 2/3

## MCP Integration (Optional)

When available, use MCP tools for:
- Knowledge base search (related papers)
- Any tool that provides complementary analysis

Discover tools via ToolSearch with queries like ["knowledge", "search", "paper"].

## Decision Points

| # | Situation | Auto-behavior | Ask user only when |
|---|-----------|---------------|-------------------|
| 1 | Language ambiguity | Match paper language | Truly mixed CN/EN |
| 2 | 10+ formulas | Overview first, offer drill-down | After overview |
| 3 | Section boundary unclear | Merge and analyze | — |
| 7 | Research domain unknown | Paper-specific suggestions | Always offer to customize |
| 9 | PDF quality < 70 | Auto-fallback chain | Both fallbacks fail |

Full decision definitions: `paper_deep_read/schemas.py` + `paper_deep_read/prompts.py`
