# Paper Deep Read

<p align="center">
<b>Three-layer progressive academic paper analysis toolkit</b>
</p>

Cross-platform Python package for parsing academic PDFs and performing structured deep analysis. Works with any LLM/Agent platform.

## Features

- **PDF Parsing** — Text extraction, table extraction, formula detection, section boundary identification
- **Quality Assessment** — 5 automated checks (garbled text, formula quality, text misalignment, empty sections, missing tables) with 0-100 scoring
- **Intelligent Fallback** — VLM (vision model) or OCR when extraction quality is poor
- **Three-Layer Analysis** — Progressive depth: Overview -> Method Detail -> Innovation
- **Symbol-Level Formula Explanation** — Every symbol in every formula gets name, meaning, type, domain, intuition
- **Structured Output** — JSON schemas + prompt templates for reproducible analysis
- **Platform Adapters** — One core package, multiple platform wrappers

## Install

```bash
pip install paper-deep-read
# or from source
pip install -e .
```

## Quick Start

### 1. Parse a PDF

```python
from paper_deep_read import parse_pdf, assess_quality

result = parse_pdf("paper.pdf", output_path="parsed.json")
print(f"Quality: {result['quality']['score']}/100")
print(f"Sections: {result['stats']['sections_found']}")
print(f"Formulas: {result['stats']['total_formulas']}")
```

### 2. CLI Usage

```bash
# Parse with quality assessment (default)
paper-deep-read paper.pdf -o parsed.json

# Render pages to images (for VLM/OCR fallback)
paper-deep-read paper.pdf --render-pages ./pages/
```

### 3. Quality Assessment

```python
from paper_deep_read import assess_quality, render_pages

quality = assess_quality(result)

if quality["score"] < 70:
    # Fallback: render pages for VLM/OCR
    pages = render_pages("paper.pdf", "./pages/")
```

Quality checks:
| Check | Severity | What it detects |
|-------|----------|----------------|
| Garbled text | CRITICAL/HIGH | Replacement characters (U+FFFD) |
| Formula quality | MEDIUM/HIGH | Missing formulas or extraction artifacts |
| Text misalignment | HIGH | Multi-column content merged into single stream |
| Empty sections | MEDIUM | Key sections with < 50 chars |
| Missing tables | MEDIUM | Experiments section with 0 tables |

### 4. Get Analysis Schemas & Prompts

```python
from paper_deep_read.schemas import get_schema
from paper_deep_read.prompts import get_prompt

# Layer 1: Overview
schema = get_schema(1)          # JSON schema for structured output
prompt = get_prompt(1, paper_text)  # Ready-to-use prompt for LLM

# Layer 2: Method Detail (includes formula symbol tables)
schema = get_schema(2)
prompt = get_prompt(2, method_text)

# Layer 3: Innovation & Optimization
schema = get_schema(3)
prompt = get_prompt(3, full_text)
```

## Three-Layer Analysis Framework

```
Layer 1: Overview
  Background -> Problem -> Target Problem -> Method -> Experiments -> Ablation -> Conclusion

Layer 2: Method Detail
  Architecture -> Data Flow -> Every Formula (symbol-by-symbol) -> Algorithm -> Hyperparameters

Layer 3: Innovation
  Strengths -> Weaknesses -> Optimization Opportunities -> New Research Directions -> Experiment Ideas
```

## Architecture

```
paper-deep-read/
├── paper_deep_read/              # Core Python package (platform-independent)
│   ├── __init__.py               # Public API + version
│   ├── __main__.py               # python -m paper_deep_read entry point
│   ├── parser.py                 # PDF parsing + quality assessment + page rendering
│   ├── schemas.py                # JSON schemas for 3-layer output
│   └── prompts.py                 # Prompt templates for 3-layer analysis
├── adapters/                     # Platform-specific adapters (copy & use)
│   ├── workbuddy/                # WorkBuddy agent platform
│   │   └── SKILL.md
│   ├── openai_custom_gpt/        # ChatGPT Custom GPT
│   │   └── instructions.md
│   ├── openai_assistants/        # OpenAI Assistants API
│   │   └── assistant.py
│   ├── claude/                   # Claude Project (Anthropic)
│   │   └── CLAUDE.md
│   ├── dify/                     # Dify (open-source AI app platform)
│   │   ├── instructions.md
│   │   ├── tools/parse_pdf.py
│   │   └── README.md
│   ├── coze/                     # Coze (ByteDance agent platform)
│   │   └── prompt.md
│   ├── langchain/                # LangChain/LangGraph
│   │   └── tools.py
│   ├── autogen/                  # Microsoft AutoGen
│   │   └── tools.py
│   ├── crewai/                   # CrewAI
│   │   └── agent.py
│   └── cursor/                   # Cursor IDE
│       └── .cursorrules
├── templates/                    # Output format templates
│   ├── layer1_overview.md
│   ├── layer2_method.md
│   └── layer3_innovation.md
├── pyproject.toml                # pip install -e .
├── requirements.txt
└── README.md
```

## Platform Adapters

> **Design principle:** The `paper_deep_read/` core package handles PDF parsing only. All analysis is done by the platform's LLM. Adapters are pure instruction/config files — no platform lock-in.

### WorkBuddy

Copy `adapters/workbuddy/SKILL.md` to `~/.workbuddy/skills/paper-deep-read/SKILL.md`.

### ChatGPT Custom GPT

Copy the content of `adapters/openai_custom_gpt/instructions.md` into **GPTs > Configure > Instructions**.

### OpenAI Assistants API

```python
from openai import OpenAI
from adapters.openai_assistants.assistant import create_paper_assistant

client = OpenAI()
assistant = create_paper_assistant(client)
# Create thread, upload PDF, run analysis
```

### Claude Project (Anthropic)

Place `adapters/claude/CLAUDE.md` as the project instructions file, or paste into Claude's Project settings.

### Dify

1. Copy `adapters/dify/instructions.md` as the system prompt
2. Register `adapters/dify/tools/parse_pdf.py` as a custom tool
3. See `adapters/dify/README.md` for workflow configuration

### Coze (ByteDance)

Copy `adapters/coze/prompt.md` into your Bot's "Personality & Prompt" settings.

### LangChain

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from adapters.langchain.tools import create_paper_analysis_agent

llm = ChatOpenAI(model="gpt-4o")
agent = create_paper_analysis_agent(llm)
executor = AgentExecutor(agent=agent.agent, tools=agent.tools)
result = executor.invoke({"input": "Analyze paper.pdf"})
```

### Microsoft AutoGen

```python
import autogen
from adapters.autogen.tools import PAPER_ANALYST_PROMPT, FUNCTION_MAP

assistant = autogen.AssistantAgent("analyst", system_message=PAPER_ANALYST_PROMPT, llm_config=...)
```

### CrewAI

```python
from adapters.crewai.agent import create_paper_crew

crew = create_paper_crew()
crew.add_paper_task("paper.pdf")
result = crew.kickoff()
```

### Cursor IDE

Place `adapters/cursor/.cursorrules` in your project root.

### Custom Agent

```python
from paper_deep_read import parse_pdf, get_schema, get_prompt

# 1. Parse PDF
result = parse_pdf("paper.pdf")

# 2. If quality is poor, use VLM/OCR
if result["quality"]["score"] < 70:
    pages = render_pages("paper.pdf", "./pages/")
    # Feed pages to your vision model or OCR engine

# 3. Generate analysis prompts for your LLM
for layer in [1, 2, 3]:
    schema = get_schema(layer)
    prompt = get_prompt(layer, result["full_text"])
    response = your_llm_call(prompt)
```

## Dependencies

| Package | Required | Purpose |
|---------|----------|---------|
| pdfplumber | Yes (or pymupdf) | Text & table extraction |
| pymupdf | Yes (or pdfplumber) | Metadata, formula detection, page rendering |

At least one PDF backend is required. Both recommended for best results.

## License

MIT
