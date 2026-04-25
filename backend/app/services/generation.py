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
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.agents import ADKAgentBundle, OutputType
from app.agents.prompts import (
    GENERATION_PROMPT_TEMPLATES,
    INTENT_ROUTER_PROMPT_TEMPLATE,
    OUTPUT_SCHEMAS,
    RETRIEVAL_SYNTHESIS_PROMPT_TEMPLATE,
)
from app.core.vector_store import build_qdrant_vector_store

VALID_OUTPUT_TYPES = ("quiz", "flashcards", "study_plan")


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

    def generate(self, query: str, output_type: str | None = None, document_id: str | None = None) -> dict[str, Any]:
        resolved_output_type = self._resolve_output_type(query=query, output_type=output_type)
        generation_chain = self._build_generation_chain(
            output_type=resolved_output_type,
            document_id=document_id,
        )

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

    def _build_generation_chain(self, output_type: OutputType, document_id: str | None = None):
        prompt = ChatPromptTemplate.from_template(GENERATION_PROMPT_TEMPLATES[output_type])
        schema_json = json.dumps(OUTPUT_SCHEMAS[output_type], indent=2)
        generator_agent = self.adk_agents.generator_for(output_type)

        # Build a retriever scoped to the specific document if document_id is provided.
        # This prevents chunks from other uploads from polluting results.
        if document_id:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": self.retrieval_k, "filter": qdrant_filter}
            )
        else:
            retriever = self.retriever

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
                "retrieved_docs": RunnablePassthrough() | retriever,
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
