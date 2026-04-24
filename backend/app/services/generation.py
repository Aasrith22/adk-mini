from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from flask import current_app
from jsonschema import Draft202012Validator
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.services.adk_runtime import ADKAgentBundle, OutputType
from app.services.vector_store import build_qdrant_vector_store

VALID_OUTPUT_TYPES = ("quiz", "flashcards", "study_plan")

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

QUIZ_GENERATION_PROMPT_TEMPLATE = """
You are {agent_name}.
Role instruction: {agent_instruction}

Produce a rigorous quiz response in STRICT JSON matching the schema below.
Return JSON only. No markdown. No prose outside JSON.

Schema:
{schema_json}

Generation constraints:
- Use only information from the condensed context and source context.
- Generate 5 to 10 high-quality MCQ questions.
- Each question must have exactly 4 options.
- answer_index must be 0-3.
- Include concise explanations.
- Keep difficulty levels balanced.
- output_type must be \"quiz\".

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
            "minItems": 5,
            "maxItems": 10,
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
        "source_context": {
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
        },
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
        "source_context": {
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
        },
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
        "source_context": {
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
        },
    },
}

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


class GenerationService:
    def __init__(
        self,
        qdrant_path: Path,
        collection_name: str,
        google_api_key: str,
        embedding_model: str,
        retrieval_k: int,
        adk_agents: ADKAgentBundle,
    ) -> None:
        self.retrieval_k = retrieval_k
        self.adk_agents = adk_agents

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=embedding_model,
            google_api_key=google_api_key,
        )
        self.vector_store = build_qdrant_vector_store(
            persist_path=qdrant_path,
            collection_name=collection_name,
            embeddings=self.embeddings,
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": retrieval_k})

        self.intent_llm = ChatGoogleGenerativeAI(
            model=self.adk_agents.intent_router.model,
            google_api_key=google_api_key,
            temperature=0,
        )
        self.retrieval_llm = ChatGoogleGenerativeAI(
            model=self.adk_agents.retrieval_strategist.model,
            google_api_key=google_api_key,
            temperature=0.1,
        )
        self.generator_llms: dict[OutputType, ChatGoogleGenerativeAI] = {
            "quiz": ChatGoogleGenerativeAI(
                model=self.adk_agents.quiz_generator.model,
                google_api_key=google_api_key,
                temperature=0.2,
            ),
            "flashcards": ChatGoogleGenerativeAI(
                model=self.adk_agents.flashcard_generator.model,
                google_api_key=google_api_key,
                temperature=0.2,
            ),
            "study_plan": ChatGoogleGenerativeAI(
                model=self.adk_agents.study_plan_generator.model,
                google_api_key=google_api_key,
                temperature=0.2,
            ),
        }

        self.intent_chain = (
            ChatPromptTemplate.from_template(INTENT_ROUTER_PROMPT_TEMPLATE)
            | self.intent_llm
            | StrOutputParser()
        )
        self.retrieval_chain = (
            ChatPromptTemplate.from_template(RETRIEVAL_SYNTHESIS_PROMPT_TEMPLATE)
            | self.retrieval_llm
            | StrOutputParser()
        )

    def generate(self, query: str, output_type: str | None = None) -> dict[str, Any]:
        resolved_output_type = self._resolve_output_type(query=query, output_type=output_type)
        generation_chain = self._build_generation_chain(output_type=resolved_output_type)

        payload = generation_chain.invoke(query)

        return {
            "query": query,
            "output_type": resolved_output_type,
            "supervisor_agent": self.adk_agents.generation_supervisor.name,
            "generator_agent": self.adk_agents.generator_for(resolved_output_type).name,
            "payload": payload,
        }

    def _resolve_output_type(self, query: str, output_type: str | None) -> OutputType:
        if output_type and output_type in VALID_OUTPUT_TYPES:
            return output_type  # type: ignore[return-value]

        raw_router_output = self.intent_chain.invoke(
            {
                "agent_name": self.adk_agents.intent_router.name,
                "agent_instruction": self.adk_agents.intent_router.instruction,
                "query": query,
            }
        )
        router_payload = self._parse_json_object(raw_router_output)

        selected_output_type = router_payload.get("output_type")
        if isinstance(selected_output_type, str) and selected_output_type in VALID_OUTPUT_TYPES:
            return selected_output_type  # type: ignore[return-value]

        return self._fallback_output_type(query)

    def _fallback_output_type(self, query: str) -> OutputType:
        lowered = query.lower()

        if any(token in lowered for token in ("flashcard", "memorize", "recall", "definition")):
            return "flashcards"
        if any(token in lowered for token in ("plan", "schedule", "timeline", "revise", "revision")):
            return "study_plan"
        return "quiz"

    def _build_generation_chain(self, output_type: OutputType):
        prompt = ChatPromptTemplate.from_template(GENERATION_PROMPT_TEMPLATES[output_type])
        schema_json = json.dumps(OUTPUT_SCHEMAS[output_type], indent=2)
        generator_agent = self.adk_agents.generator_for(output_type)

        def prepare_prompt_values(payload: dict[str, Any]) -> dict[str, Any]:
            query = payload["query"]
            retrieved_docs = payload["retrieved_docs"]

            context_text, source_context = self._serialize_docs(retrieved_docs)
            condensed_context = self.retrieval_chain.invoke(
                {
                    "agent_name": self.adk_agents.retrieval_strategist.name,
                    "agent_instruction": self.adk_agents.retrieval_strategist.instruction,
                    "query": query,
                    "retrieved_context": context_text,
                }
            )

            return {
                "agent_name": generator_agent.name,
                "agent_instruction": generator_agent.instruction,
                "query": query,
                "condensed_context": condensed_context,
                "source_context_json": json.dumps(source_context, indent=2, ensure_ascii=False),
                "schema_json": schema_json,
            }

        return (
            {
                "query": RunnablePassthrough(),
                "retrieved_docs": RunnablePassthrough() | self.retriever,
            }
            | RunnableLambda(prepare_prompt_values)
            | prompt
            | self.generator_llms[output_type]
            | StrOutputParser()
            | RunnableLambda(lambda text: self._parse_and_validate_output(text, output_type))
        )

    def _serialize_docs(self, docs: list[Document]) -> tuple[str, list[dict[str, Any]]]:
        if not docs:
            raise ValueError(
                "No retrieval context found. Upload academic materials first via /api/upload."
            )

        context_lines: list[str] = []
        source_context: list[dict[str, Any]] = []

        for index, doc in enumerate(docs, start=1):
            source = str(doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown")
            page = doc.metadata.get("page")
            page_number = page if isinstance(page, int) else None

            snippet = re.sub(r"\s+", " ", doc.page_content).strip()
            snippet = snippet[:450]

            context_lines.append(
                f"[{index}] source={source}; page={page_number if page_number is not None else 'n/a'}\n{snippet}"
            )
            source_context.append(
                {
                    "source": source,
                    "page": page_number,
                    "snippet": snippet,
                }
            )

        return "\n\n".join(context_lines), source_context

    def _parse_and_validate_output(self, raw_text: str, output_type: OutputType) -> dict[str, Any]:
        payload = self._parse_json_object(raw_text)

        validator = Draft202012Validator(OUTPUT_SCHEMAS[output_type])
        validation_errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
        if validation_errors:
            first_error = validation_errors[0]
            error_path = ".".join(str(part) for part in first_error.path) or "<root>"
            raise ValueError(
                f"Generated output failed schema validation at {error_path}: {first_error.message}"
            )

        return payload

    @staticmethod
    def _parse_json_object(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()

        if not text.startswith("{"):
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                text = match.group(0)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Model returned invalid JSON output.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Model output must be a JSON object.")

        return parsed


def get_generation_service() -> GenerationService:
    service = current_app.extensions.get("generation_service")
    if service is not None:
        return service

    adk_agents = current_app.extensions.get("adk_agents")
    if not isinstance(adk_agents, ADKAgentBundle):
        raise RuntimeError("ADK agent bundle is not initialized.")

    service = GenerationService(
        qdrant_path=current_app.config["QDRANT_PATH"],
        collection_name=current_app.config["QDRANT_COLLECTION"],
        google_api_key=current_app.config["GOOGLE_API_KEY"],
        embedding_model=current_app.config["GOOGLE_EMBEDDING_MODEL"],
        retrieval_k=current_app.config["RAG_RETRIEVAL_K"],
        adk_agents=adk_agents,
    )
    current_app.extensions["generation_service"] = service

    return service
