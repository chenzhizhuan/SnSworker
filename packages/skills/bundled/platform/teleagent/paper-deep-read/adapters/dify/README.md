# Paper Deep Read - Dify Adapter

Dify is an open-source LLM app development platform (https://dify.ai).
This adapter provides a complete Dify workflow configuration.

## Quick Setup

1. Create a new "Chatbot" type app in Dify
2. Copy `instructions.md` content into the system prompt
3. Create the tool functions from `tools/parse_pdf.py`
4. Configure the workflow nodes as described below

---

## Option A: Simple Chatbot (Single Prompt)

Use `instructions.md` as the system prompt. Add the PDF parse tool as a function tool.

## Option B: Workflow Mode (Recommended)

Create a 5-node workflow:

```
[Start Node] -> [PDF Parse Node] -> [Quality Check Node] -> [LLM Analysis Node] -> [End Node]
```

### Node 1: Start
- Input variables:
  - `pdf_file` (File type) - the uploaded PDF
  - `user_language` (String, optional) - preferred output language

### Node 2: PDF Parse (HTTP Request / Function)
- Calls the `parse_pdf` tool
- Input: PDF file path/bytes
- Output: `{text, quality_score, sections, formulas}`

### Node 3: Quality Check (Conditional Router)
- If `quality_score >= 70`: route to Node 4A (Text Analysis)
- If `quality_score < 70`: route to Node 4B (Vision Analysis, if model supports vision)
- If model is text-only and score < 70: route to Node 4C (OCR Analysis)

### Node 4A/B/C: LLM Analysis (3 sequential LLM calls)
- **Call 1 (Layer 1)**: Overview analysis prompt
- **Call 2 (Layer 2)**: Method detail + formula analysis prompt
- **Call 3 (Layer 3)**: Innovation + optimization prompt
- Each call passes the previous layer's output as context

### Node 5: End
- Merge all layer outputs into final Markdown report
- Output as file download

## Required Environment

In Dify's tool configuration, set up:
- Python environment with `pdfplumber` and `pymupdf` installed
- Or use HTTP request to an external API that runs `paper_deep_read`
