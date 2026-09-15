"""
Paper Deep Read - OpenAI Assistants API Integration.

Provides a ready-to-use OpenAI Assistant configuration for paper analysis.

Usage:
    from adapters.openai_assistants.assistant import create_paper_assistant

    assistant = create_paper_assistant(client)
    thread = client.beta.threads.create()
    # Upload PDF, create message, run assistant
"""

from __future__ import annotations

import json
from typing import Optional

from paper_deep_read import get_prompt, get_schema, SYSTEM_PROMPT


ASSISTANT_INSTRUCTIONS = """You are an expert academic paper analyst performing three-layer progressive deep reading.

## Core Rules

1. Analyze with extreme rigor. Never skip sections or formulas.
2. Output structured Markdown with tables for experiments and ablation.
3. For EVERY formula, explain EVERY symbol (name, meaning, type, domain).
4. Match paper language: Chinese -> Chinese, English -> English.
5. Innovation suggestions must be concrete and actionable.

## Workflow

When the user provides a PDF paper:

1. **Parse PDF**: Use the `parse_pdf` code interpreter tool to extract text.
   - The tool returns extracted text, sections, formulas, and quality score (0-100).
   - Quality >= 70: use extracted text
   - Quality < 70: inform user extraction was degraded, but proceed with available text

2. **Layer 1 - Overview**: Background -> Problem -> Target Problem -> Method -> Experiments -> Ablation -> Conclusion
   - Experiments and ablation must include tables with exact numbers

3. **Layer 2 - Method Detail**: For EVERY formula:
   - Exact text, purpose, symbol table (symbol/meaning/type/domain), intuition, connections
   - Also: architecture, data flow, training/inference, hyperparameters
   - If 10+ formulas: overview first, ask user to select for deep-dive

4. **Layer 3 - Innovation**: Strengths (3-5) -> Weaknesses (3-5) -> Optimization (3-5) -> New Directions (3-5) -> Experiments

5. **Output**: Compile all layers into a single Markdown report. Use file_search to save it if available.

## Code Interpreter Tool

Use the code interpreter to run this Python code:

```python
from paper_deep_read import parse_pdf
result = parse_pdf("/mnt/data/paper.pdf")
print(result["quality"]["score"])
print(result["full_text"][:10000])
```

If `paper_deep_read` is not installed:
```python
import subprocess
subprocess.run(["pip", "install", "paper-deep-read", "pdfplumber", "pymupdf"])
from paper_deep_read import parse_pdf
result = parse_pdf("/mnt/data/paper.pdf")
```
"""


def create_paper_assistant(
    client,
    model: str = "gpt-4o",
    name: str = "Paper Deep Read",
    code_interpreter: bool = True,
    file_search: bool = False,
    extra_instructions: Optional[str] = None,
):
    """Create an OpenAI Assistant for paper deep reading.

    Args:
        client: OpenAI client instance.
        model: Model to use (default gpt-4o).
        name: Assistant name.
        code_interpreter: Enable code interpreter for PDF parsing.
        file_search: Enable file search for knowledge base.
        extra_instructions: Additional instructions to append.

    Returns:
        Assistant object.
    """
    tools = []
    if code_interpreter:
        tools.append({"type": "code_interpreter"})
    if file_search:
        tools.append({"type": "file_search"})

    instructions = ASSISTANT_INSTRUCTIONS
    if extra_instructions:
        instructions += f"\n\n## Additional Instructions\n\n{extra_instructions}"

    assistant = client.beta.assistants.create(
        name=name,
        instructions=instructions,
        model=model,
        tools=tools,
    )

    return assistant


def create_thread_with_pdf(client, assistant_id: str, pdf_path: str):
    """Create a thread, upload a PDF, and send the initial message.

    Args:
        client: OpenAI client instance.
        assistant_id: The assistant's ID.
        pdf_path: Path to the PDF file to analyze.

    Returns:
        Tuple of (thread, message).
    """
    # Upload file
    with open(pdf_path, "rb") as f:
        file = client.files.create(file=f, purpose="assistants")

    # Create thread
    thread = client.beta.threads.create()

    # Add message with file attachment
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Please perform a deep three-layer analysis of this paper.",
        attachments=[{"file_id": file.id, "tools": [{"type": "code_interpreter"}]}],
    )

    return thread, message


def run_analysis(client, thread_id: str, assistant_id: str):
    """Run the assistant on the thread and stream results.

    Args:
        client: OpenAI client instance.
        thread_id: Thread ID.
        assistant_id: Assistant ID.

    Returns:
        Run object.
    """
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        return messages
    else:
        raise RuntimeError(f"Run failed with status: {run.status}")


if __name__ == "__main__":
    print("Paper Deep Read - OpenAI Assistants API Adapter")
    print("=" * 45)
    print()
    print("Quick start:")
    print()
    print("  from openai import OpenAI")
    print("  from paper_deep_read.adapters.openai_assistants.assistant import (")
    print("      create_paper_assistant,")
    print("      create_thread_with_pdf,")
    print("      run_analysis")
    print("  )")
    print()
    print("  client = OpenAI()")
    print("  assistant = create_paper_assistant(client)")
    print("  thread, msg = create_thread_with_pdf(client, assistant.id, 'paper.pdf')")
    print("  messages = run_analysis(client, thread.id, assistant.id)")
    print()
