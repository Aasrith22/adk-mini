from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from google.adk.agents import Agent


OutputType = Literal["quiz", "flashcards", "study_plan"]


@dataclass(frozen=True)
class ADKAgentBundle:
    ingestion_orchestrator: Agent
    intent_router: Agent
    retrieval_strategist: Agent
    quiz_generator: Agent
    flashcard_generator: Agent
    study_plan_generator: Agent
    generation_supervisor: Agent

    def generator_for(self, output_type: OutputType) -> Agent:
        if output_type == "quiz":
            return self.quiz_generator
        if output_type == "flashcards":
            return self.flashcard_generator
        return self.study_plan_generator


def build_ingestion_orchestrator(model: str) -> Agent:
    return Agent(
        name="ingestion_orchestrator",
        model=model,
        instruction=(
            "Coordinate ingestion of academic documents with emphasis on context preservation, "
            "metadata completeness, and retrieval quality for downstream RAG generation."
        ),
        description="ADK orchestration agent used for backend ingestion workflow context.",
    )


def build_agent_bundle(router_model: str, generator_model: str) -> ADKAgentBundle:
    ingestion_orchestrator = build_ingestion_orchestrator(model=router_model)

    intent_router = Agent(
        name="intent_router_agent",
        model=router_model,
        instruction=(
            "Classify user requests into one of three output intents: quiz, flashcards, or study_plan. "
            "Prefer quiz for assessment requests, flashcards for memory-focused requests, and study_plan "
            "for planning or revision timeline requests."
        ),
        description="Routes generation requests to the correct downstream specialist agent.",
    )

    retrieval_strategist = Agent(
        name="retrieval_strategist_agent",
        model=router_model,
        instruction=(
            "Condense retrieved academic passages into concise, faithful context notes without inventing facts. "
            "Preserve definitions, formulas, and key conceptual dependencies."
        ),
        description="Synthesizes retrieved chunks into compact context for generation agents.",
    )

    quiz_generator = Agent(
        name="quiz_generator_agent",
        model=generator_model,
        instruction=(
            "You are a university-level assessment designer. "
            "Generate exam-quality multiple-choice questions that test conceptual understanding, "
            "application, and analytical reasoning — not surface-level recall. "
            "Every question must read as a standalone academic question; NEVER reference "
            "'the context', 'the passage', 'the provided text', or any similar meta-phrase. "
            "If the user specifies how many questions they want, generate exactly that number. "
            "Distractors must be plausible. Vary difficulty across easy, medium, and hard."
        ),
        description="Specialist agent for quiz JSON generation.",
    )

    flashcard_generator = Agent(
        name="flashcard_generator_agent",
        model=generator_model,
        instruction=(
            "Generate high-retention flashcards that capture definitions, mechanisms, and conceptual contrasts."
            "You are a flashcard generation agent that creates concise flashcards for studying. "
            "Focus on clarity and retention. "
            "Keep each flashcard focused on a single concept."
            "The front should be a clear term or question."
            "The back should be a concise explanation, definition, or answer."
            "Do not repeat the same information across multiple cards."
        ),
        description="Specialist agent for flashcard JSON generation.",
    )

    study_plan_generator = Agent(
        name="study_plan_generator_agent",
        model=generator_model,
        instruction=(
            "Generate realistic, structured revision plans with weekly goals, tasks, and self-check prompts."
            "You are an expert academic coach and curriculum designer. "
            "Create structured study plans that are realistic and effective. "
            "Organize the plan into manageable study sessions or days. "
            "Assign a mix of learning activities: reading, practice problems, review. "
            "Balance depth and breadth in the topics covered. "
            "Include checkpoints or self-assessment opportunities. "
            "Suggest a sustainable pace that avoids burnout. "
            "Use the retrieved context to tailor the plan to the specific material. "
            "Focus on building understanding, not just memorization.Take the user intent in mind and divide the study plan specific to the days , weeks or months asked by the user"
        ),
        description="Specialist agent for study plan JSON generation.",
    )

    generation_supervisor = Agent(
        name="generation_supervisor_agent",
        model=router_model,
        instruction=(
            "Coordinate the intent router, retrieval strategist, and specialist generator agents so each request "
            "is served by the best-suited workflow."
        ),
        description="Supervisor over generation sub-agents.",
        sub_agents=[
            intent_router,
            retrieval_strategist,
            quiz_generator,
            flashcard_generator,
            study_plan_generator,
        ],
    )

    return ADKAgentBundle(
        ingestion_orchestrator=ingestion_orchestrator,
        intent_router=intent_router,
        retrieval_strategist=retrieval_strategist,
        quiz_generator=quiz_generator,
        flashcard_generator=flashcard_generator,
        study_plan_generator=study_plan_generator,
        generation_supervisor=generation_supervisor,
    )
