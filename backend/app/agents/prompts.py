"""Prompt templates and JSON output schemas for generation agents.

Centralises all LLM prompt engineering in one file, keeping services lean.
"""

from __future__ import annotations

from typing import Any

from app.agents.agent_bundle import OutputType

# ---------------------------------------------------------------------------
# Intent Router
# ---------------------------------------------------------------------------

INTENT_ROUTER_PROMPT_TEMPLATE = """
You are {agent_name}.
Role instruction: {agent_instruction}

Classify the user query into exactly one output type.
Allowed output types:
- quiz
- flashcards
- study_plan

Return ONLY a valid JSON object with this schema:
{{
  "output_type": "quiz|flashcards|study_plan",
  "reason": "short reason"
}}

User query:
{query}
""".strip()

# ---------------------------------------------------------------------------
# Retrieval Synthesis
# ---------------------------------------------------------------------------

RETRIEVAL_SYNTHESIS_PROMPT_TEMPLATE = """
You are {agent_name}.
Role instruction: {agent_instruction}

Given the retrieval context, extract the most relevant facts for generation.
Rules:
- Do not invent facts.
- Preserve definitions, key points, formulas, and dependencies.
- Keep the summary under 2200 characters.
- Keep academic precision.

User query:
{query}

Retrieved context:
{retrieved_context}
""".strip()

# ---------------------------------------------------------------------------
# Generation Prompts (one per output type)
# ---------------------------------------------------------------------------

QUIZ_GENERATION_PROMPT_TEMPLATE = """
You are {agent_name}.
Role instruction: {agent_instruction}

Produce a rigorous quiz response in STRICT JSON matching the schema below.
Return JSON only. No markdown. No prose outside JSON.

Schema:
{schema_json}

### How many questions to generate
Look at the **User query** below. If the user explicitly states a number of questions
(e.g. "give me 3 questions", "5 MCQs", "only 2"), generate EXACTLY that many.
If no count is specified, default to 5.
Never generate more or fewer than the resolved count.

### Question-quality rules (MANDATORY)
1. Every question MUST read like a real university exam or certification question.
   Write each question as a direct, standalone academic question.
2. NEVER begin or include phrases such as:
   - "According to the provided context"
   - "Based on the provided text"
   - "From the context in unit X"
   - "The context mentions"
   - "As stated in the passage"
   - Any similar meta-reference to "context", "passage", "text", or "provided material".
3. Questions must test conceptual understanding, application, or analysis — not mere recall of context wording.
4. Distractors (wrong options) must be plausible and clearly distinct from the correct answer.
5. Each question must have exactly 4 options.
6. answer_index must be 0-3.
7. Include concise but informative explanations.
8. Vary difficulty across easy, medium, and hard.
9. output_type must be \"quiz\".
10. Use only information from the condensed context and source context — do NOT hallucinate facts.

User query:
{query}

Condensed context:
{condensed_context}

Source context snippets:
{source_context_json}
""".strip()

FLASHCARD_GENERATION_PROMPT_TEMPLATE = """
You are {agent_name}.
Role instruction: {agent_instruction}

Produce flashcards in STRICT JSON matching the schema below.
Return JSON only. No markdown. No prose outside JSON.

Schema:
{schema_json}

Generation constraints:
- Use only retrieved academic context.
- Generate 8 to 16 flashcards.
- Front should be short and testable.
- Back should be precise and concise.
- output_type must be \"flashcards\".

User query:
{query}

Condensed context:
{condensed_context}

Source context snippets:
{source_context_json}
""".strip()

STUDY_PLAN_GENERATION_PROMPT_TEMPLATE = """
You are {agent_name}.
Role instruction: {agent_instruction}

Produce a revision plan in STRICT JSON matching the schema below.
Return JSON only. No markdown. No prose outside JSON.

Schema:
{schema_json}

Generation constraints:
- Use only retrieved context.
- Build a realistic weekly structure.
- Include focused learning goals and revision tasks.
- Add one self_test_prompt for each week.
- output_type must be \"study_plan\".

User query:
{query}

Condensed context:
{condensed_context}

Source context snippets:
{source_context_json}
""".strip()

# ---------------------------------------------------------------------------
# JSON Schemas (used for validation + injected into prompts)
# ---------------------------------------------------------------------------

_SOURCE_CONTEXT_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["source", "page", "snippet"],
        "properties": {
            "source": {"type": "string", "minLength": 1},
            "page": {"type": ["integer", "null"]},
            "snippet": {"type": "string", "minLength": 1},
        },
    },
}

QUIZ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["output_type", "title", "instructions", "questions", "source_context"],
    "properties": {
        "output_type": {"const": "quiz"},
        "title": {"type": "string", "minLength": 3},
        "instructions": {"type": "string", "minLength": 5},
        "questions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "question",
                    "options",
                    "answer_index",
                    "explanation",
                    "difficulty",
                    "learning_objective",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "question": {"type": "string", "minLength": 10},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "answer_index": {"type": "integer", "minimum": 0, "maximum": 3},
                    "explanation": {"type": "string", "minLength": 5},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    "learning_objective": {"type": "string", "minLength": 4},
                },
            },
        },
        "source_context": _SOURCE_CONTEXT_SCHEMA,
    },
}

FLASHCARDS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["output_type", "title", "flashcards", "source_context"],
    "properties": {
        "output_type": {"const": "flashcards"},
        "title": {"type": "string", "minLength": 3},
        "flashcards": {
            "type": "array",
            "minItems": 8,
            "maxItems": 16,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "front", "back", "difficulty", "tags"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "front": {"type": "string", "minLength": 3},
                    "back": {"type": "string", "minLength": 5},
                    "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                    "tags": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
        "source_context": _SOURCE_CONTEXT_SCHEMA,
    },
}

STUDY_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["output_type", "title", "total_weeks", "weekly_plan", "source_context"],
    "properties": {
        "output_type": {"const": "study_plan"},
        "title": {"type": "string", "minLength": 3},
        "total_weeks": {"type": "integer", "minimum": 1, "maximum": 20},
        "weekly_plan": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["week", "focus", "learning_goals", "revision_tasks", "self_test_prompt"],
                "properties": {
                    "week": {"type": "integer", "minimum": 1},
                    "focus": {"type": "string", "minLength": 3},
                    "learning_goals": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 3},
                    },
                    "revision_tasks": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "minLength": 3},
                    },
                    "self_test_prompt": {"type": "string", "minLength": 5},
                },
            },
        },
        "source_context": _SOURCE_CONTEXT_SCHEMA,
    },
}

# ---------------------------------------------------------------------------
# Lookup dicts used by GenerationService
# ---------------------------------------------------------------------------

OUTPUT_SCHEMAS: dict[OutputType, dict[str, Any]] = {
    "quiz": QUIZ_SCHEMA,
    "flashcards": FLASHCARDS_SCHEMA,
    "study_plan": STUDY_PLAN_SCHEMA,
}

GENERATION_PROMPT_TEMPLATES: dict[OutputType, str] = {
    "quiz": QUIZ_GENERATION_PROMPT_TEMPLATE,
    "flashcards": FLASHCARD_GENERATION_PROMPT_TEMPLATE,
    "study_plan": STUDY_PLAN_GENERATION_PROMPT_TEMPLATE,
}
