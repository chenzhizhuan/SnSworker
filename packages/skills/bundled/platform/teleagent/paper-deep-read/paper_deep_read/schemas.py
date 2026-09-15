"""
Paper Deep Read - JSON Schemas for Three-Layer Analysis.

Provides structured output schemas for each analysis layer.
Use these to validate agent output or guide LLM prompting.

Usage:
    from paper_deep_read.schemas import get_schema, LAYER1_SCHEMA
    schema = get_schema(1)  # Layer 1 overview schema
"""

LAYER1_SCHEMA = {
    "paper_title": "string",
    "analysis_layer": 1,
    "background": {
        "summary": "Research background and context (2-3 paragraphs)",
        "key_concepts": ["concept1", "concept2"],
        "related_fields": ["field1", "field2"],
    },
    "problem": {
        "general_problem": "What problem exists in the field",
        "specific_gap": "What specific gap the paper addresses",
        "why_important": "Why solving this matters",
    },
    "target_problem": {
        "formal_statement": "Formal problem definition",
        "input": "What the method takes as input",
        "output": "What the method produces",
        "constraints": "Any constraints or assumptions",
    },
    "method": {
        "name": "Method name",
        "category": "Type (retrieval-augmented, diffusion, transformer, etc.)",
        "core_idea": "One-sentence summary of the approach",
        "architecture_overview": "High-level architecture description",
        "key_components": [
            {"component_name": "string", "purpose": "string", "how_it_works": "string"}
        ],
    },
    "experiments": {
        "datasets": ["dataset1", "dataset2"],
        "baselines": ["baseline1", "baseline2"],
        "main_results": [
            {"metric": "string", "proposed": "number", "best_baseline": "number", "improvement": "string"}
        ],
        "table_summary": "Description of main result tables",
    },
    "ablation": {
        "variants_tested": ["variant1", "variant2"],
        "key_findings": [
            {"what_was_removed": "string", "performance_change": "string", "insight": "string"}
        ],
    },
    "conclusion": {
        "main_contributions": ["contribution1", "contribution2"],
        "limitations": ["limitation1", "limitation2"],
        "future_work": ["direction1", "direction2"],
    },
}

LAYER2_SCHEMA = {
    "paper_title": "string",
    "analysis_layer": 2,
    "overall_architecture": {
        "description": "Complete architecture walkthrough",
        "data_flow": ["step1 -> step2", "step2 -> step3"],
        "training_pipeline": "How the model is trained",
        "inference_pipeline": "How the model performs inference",
    },
    "formulas": [
        {
            "id": "formula_1",
            "raw_text": "LaTeX or plain text of the formula",
            "section": "Where in the paper this formula appears",
            "purpose": "What this formula computes",
            "intuition": "Intuitive explanation in plain language",
            "symbols": [
                {
                    "symbol": "e.g., L_ret",
                    "meaning": "e.g., retrieval-enhanced loss",
                    "type": "scalar | vector | matrix | set | function",
                    "domain": "e.g., R^d, {0,1}^n, natural numbers",
                    "shape": "e.g., (batch_size, hidden_dim) if applicable",
                    "notes": "Any additional context",
                }
            ],
            "derivation_or_motivation": "Why this formula is designed this way",
            "connection_to_other": "How this connects to formula_2, formula_3, etc.",
            "complexity": "O(...) time/space complexity if relevant",
        }
    ],
    "algorithm": {
        "pseudocode": "Step-by-step algorithm description",
        "input_output": "Formal input/output specification",
        "key_implementation_details": ["detail1", "detail2"],
        "hyperparameters": [
            {"name": "string", "value_or_range": "string", "sensitivity": "how sensitive"}
        ],
    },
}

LAYER3_SCHEMA = {
    "paper_title": "string",
    "analysis_layer": 3,
    "strengths": [
        {"aspect": "string", "detail": "Why this is a strength", "evidence": "Supporting evidence"}
    ],
    "weaknesses": [
        {"aspect": "string", "detail": "Why this is a weakness", "potential_fix": "Suggested improvement"}
    ],
    "optimization_opportunities": [
        {
            "current_approach": "How the paper currently handles this",
            "proposed_improvement": "Specific improvement suggestion",
            "expected_benefit": "What improvement this would bring",
            "difficulty": "easy | medium | hard",
            "implementation_sketch": "Brief idea of how to implement",
        }
    ],
    "new_research_directions": [
        {
            "title": "Proposed paper title or topic",
            "motivation": "Why this direction is promising",
            "connection_to_paper": "How this builds on the original paper",
            "expected_contribution": "What new value this would provide",
            "methodology_sketch": "Rough approach outline",
            "target_venues": ["ACL", "NeurIPS", "EMNLP"],
        }
    ],
    "experiment_ideas": [
        {"experiment": "Description", "purpose": "What this validates", "setup": "How to set it up"}
    ],
}


def get_schema(layer: int) -> dict:
    """Get the JSON schema for a specific analysis layer (1, 2, or 3)."""
    schemas = {1: LAYER1_SCHEMA, 2: LAYER2_SCHEMA, 3: LAYER3_SCHEMA}
    if layer not in schemas:
        raise ValueError(f"Invalid layer {layer}. Must be 1, 2, or 3.")
    return schemas[layer]


def schema_to_json(schema: dict) -> str:
    """Pretty-print a schema as JSON string."""
    return json.dumps(schema, ensure_ascii=False, indent=2, default=str)


# Need json import
import json
