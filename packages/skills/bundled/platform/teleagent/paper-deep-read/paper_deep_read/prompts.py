"""
Paper Deep Read - Prompt Templates for Three-Layer Analysis.

Provides reusable prompt templates that any LLM/Agent can use.
Prompts are pure text — no platform-specific markup.

Usage:
    from paper_deep_read.prompts import get_prompt, SYSTEM_PROMPT
    prompt = get_prompt(1, paper_content="...", schema_json="{...}")
"""

SYSTEM_PROMPT = """You are a world-class academic researcher with deep expertise in the paper's domain.
Your task is to analyze research papers with extreme rigor and precision.

Rules:
1. Always respond with valid JSON matching the provided schema.
2. Be thorough - do not skip any section or formula.
3. For mathematical formulas, explain EVERY symbol, not just the main ones.
4. Use precise language. Avoid vague statements like "significantly improves".
5. If the paper is in Chinese, respond in Chinese. If in English, respond in English.
6. When uncertain about a formula's meaning, state your interpretation and flag it.
7. For innovation suggestions, be concrete and actionable, not generic."""

LAYER1_PROMPT = """Analyze the following paper and produce a Layer 1 overview analysis.

The paper content is divided into sections. Analyze each section and extract:

1. From Introduction/Background: Research context, motivation, problem statement.
2. From Method section: Proposed method name, core idea, architecture.
3. From Experiments: Datasets used, baselines compared, main results (with numbers).
4. From Ablation Studies: What components were tested, what each contributes.
5. From Conclusion: Main contributions, limitations, future work.

Follow this JSON schema exactly:
{schema}

Paper content:
{paper_content}"""

LAYER2_PROMPT = """Perform a Layer 2 deep-dive analysis of the method section.

For every mathematical formula in the paper:
1. Quote the formula exactly as it appears
2. State the purpose: what does this formula compute?
3. List EVERY symbol with full explanation:
   - Symbol name and notation
   - Meaning in plain language
   - Mathematical type (scalar, vector, matrix, set, function)
   - Domain/range
4. Provide intuition: what's the "story" behind this equation?
5. Explain connections: how does this formula relate to others in the method?
6. Note any assumptions or approximations

Also describe:
- Overall architecture and how components connect
- Data flow through the method
- Training and inference procedures
- Key hyperparameters and their sensitivity

Follow this JSON schema exactly:
{schema}

Method section content:
{paper_content}"""

LAYER3_PROMPT = """Perform a Layer 3 innovation and optimization analysis.

Based on the paper's background, method, and results:

1. Identify Strengths (3-5): What does the paper excel at? Be specific.
2. Identify Weaknesses (3-5): Limitations and gaps. Be constructive.
3. Optimization Opportunities (3-5): Concrete improvements to the method.
4. New Research Directions (3-5): Potential new papers building on this work.
   For each direction:
   - Proposed title/topic
   - Why it's promising
   - How it connects to this paper
   - Expected contribution
   - Rough methodology
5. New Experiments: Experiments to validate or extend this work.

Follow this JSON schema exactly:
{schema}

Full paper content:
{paper_content}"""


def get_prompt(layer: int, paper_content: str, schema_json: str = "") -> str:
    """
    Get a formatted prompt for a specific analysis layer.

    Args:
        layer: Analysis layer (1, 2, or 3).
        paper_content: The paper text content.
        schema_json: JSON string of the expected output schema.
                     If empty, uses the built-in schema.

    Returns:
        Formatted prompt string.
    """
    from .schemas import get_schema, schema_to_json

    templates = {1: LAYER1_PROMPT, 2: LAYER2_PROMPT, 3: LAYER3_PROMPT}
    if layer not in templates:
        raise ValueError(f"Invalid layer {layer}. Must be 1, 2, or 3.")

    if not schema_json:
        schema_json = schema_to_json(get_schema(layer))

    return templates[layer].format(schema=schema_json, paper_content=paper_content)
