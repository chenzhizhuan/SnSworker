"""
Paper Deep Read - CrewAI Agent Integration.

Provides a CrewAI-compatible Agent and Task for paper deep reading.

Usage:
    from crewai import Agent, Task, Crew, Process
    from paper_deep_read.adapters.crewai.agent import PaperAnalystAgent, create_paper_crew

    crew = create_paper_crew(llm="gpt-4o")
    result = crew.kickoff(inputs={"pdf_path": "paper.pdf"})
    print(result)
"""

from __future__ import annotations

import json
from crewai import Agent, Task, Crew, Process
from paper_deep_read import parse_pdf, get_schema, get_prompt


def _parse_pdf_tool(pdf_path: str) -> str:
    """Tool function for CrewAI agent to parse PDFs."""
    result = parse_pdf(pdf_path, quality_check=True)
    if len(result.get("full_text", "")) > 50000:
        result["full_text"] = result["full_text"][:50000] + "\n... [truncated]"
    return json.dumps(result, ensure_ascii=False, indent=2)


PAPER_ANALYST_ROLE = "Senior Academic Research Analyst"
PAPER_ANALYST_GOAL = (
    "Perform comprehensive three-layer deep reading of academic papers, "
    "extracting structured insights from background through methodology to innovation opportunities."
)
PAPER_ANALYST_BACKSTORY = (
    "You are a distinguished researcher with expertise across AI, ML, NLP, and computer science. "
    "You have published at top venues (NeurIPS, ICML, ACL, EMNLP) and have extensive experience "
    "in peer review. You excel at breaking down complex mathematical formulations into intuitive "
    "explanations, identifying both strengths and weaknesses in research, and proposing novel "
    "research directions that build on existing work."
)


def create_paper_analyst_agent(llm=None, verbose=True):
    """Create a CrewAI Agent configured for paper analysis.

    Args:
        llm: A CrewAI-compatible LLM instance. If None, uses default.
        verbose: Enable verbose output.

    Returns:
        CrewAI Agent instance.
    """
    agent = Agent(
        role=PAPER_ANALYST_ROLE,
        goal=PAPER_ANALYST_GOAL,
        backstory=PAPER_ANALYST_BACKSTORY,
        verbose=verbose,
        allow_delegation=False,
        tools=[],  # Agent uses code execution for PDF parsing
        llm=llm,
    )
    return agent


def create_analysis_task(agent, pdf_path: str):
    """Create a CrewAI Task for paper analysis.

    Args:
        agent: The paper analyst agent.
        pdf_path: Path to the PDF paper.

    Returns:
        CrewAI Task instance.
    """
    task = Task(
        description=f"""Analyze the academic paper at: {pdf_path}

Step 1: Parse the PDF using Python:
```python
from paper_deep_read import parse_pdf
result = parse_pdf("{pdf_path}")
print(result["quality"]["score"])
print(result["full_text"][:8000])
```

Step 2: Perform Layer 1 Overview - Background, Problem, Target Problem, Method, Experiments (with number tables), Ablation, Conclusion

Step 3: Perform Layer 2 Method Detail - Every formula with symbol table (symbol/meaning/type/domain), architecture, data flow, training/inference

Step 4: Perform Layer 3 Innovation - Strengths, Weaknesses, Optimization Opportunities, New Research Directions, Experiment Ideas

Step 5: Compile all layers into a comprehensive Markdown report and save to a file.""",
        expected_output="A comprehensive Markdown report with three layers of paper analysis, saved as a .md file.",
        agent=agent,
    )
    return task


def create_paper_crew(llm=None, verbose=True):
    """Create a complete CrewAI Crew for paper analysis.

    Args:
        llm: Optional LLM instance.
        verbose: Enable verbose output.

    Returns:
        CrewAI Crew instance ready for kickoff.
    """
    agent = create_paper_analyst_agent(llm=llm, verbose=verbose)

    crew = Crew(
        agents=[agent],
        tasks=[],  # Tasks are added dynamically with pdf_path
        process=Process.sequential,
        verbose=verbose,
    )

    # Attach task creation method
    crew.add_paper_task = lambda pdf_path: (
        setattr(crew, 'tasks', [create_analysis_task(agent, pdf_path)]),
        crew
    )[-1]

    return crew


if __name__ == "__main__":
    print("Paper Deep Read - CrewAI Adapter")
    print("=" * 35)
    print()
    print("Quick start:")
    print()
    print("  from paper_deep_read.adapters.crewai.agent import create_paper_crew")
    print()
    print("  crew = create_paper_crew()")
    print("  crew.add_paper_task('paper.pdf')")
    print("  result = crew.kickoff()")
    print()
