import { useState } from "react";
import {
  FlashcardsPayload,
  GenerationData,
  QuizPayload,
  SourceContextItem,
  StudyPlanPayload,
} from "../services/api";

type GenerationResultCardProps = {
  result: GenerationData;
};

/* ------------------------------------------------------------------ */
/* Source Context (collapsible)                                        */
/* ------------------------------------------------------------------ */

function SourceContext({ context }: { context: SourceContextItem[] }): JSX.Element {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button className="source-toggle" onClick={() => setOpen(!open)} type="button">
        {open ? "▾" : "▸"} Sources ({context.length})
      </button>
      {open && (
        <div className="source-list">
          {context.map((item, i) => (
            <div key={`${item.source}-${item.page ?? "na"}-${i}`} className="source-item">
              <div className="source-item-header">
                <span>{item.source}</span>
                <span>{item.page !== null ? `Page ${item.page}` : ""}</span>
              </div>
              <p className="source-item-snippet">{item.snippet}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Quiz Result                                                         */
/* ------------------------------------------------------------------ */

function QuizResult({ payload }: { payload: QuizPayload }): JSX.Element {
  const [revealedQuestions, setRevealedQuestions] = useState<Set<string>>(new Set());

  const toggleReveal = (id: string) => {
    setRevealedQuestions((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", margin: "0 0 16px" }}>
        {payload.instructions}
      </p>

      {payload.questions.map((q, idx) => {
        const revealed = revealedQuestions.has(q.id);
        return (
          <div key={q.id} className="quiz-item">
            <p className="quiz-question-text">
              {idx + 1}. {q.question}
            </p>
            <ul className="quiz-options">
              {q.options.map((opt, oi) => (
                <li
                  key={`${q.id}-opt-${oi}`}
                  className={`quiz-option ${revealed && oi === q.answer_index ? "correct" : ""}`}
                >
                  {String.fromCharCode(65 + oi)}. {opt}
                </li>
              ))}
            </ul>

            {!revealed ? (
              <button className="quiz-reveal-btn" onClick={() => toggleReveal(q.id)} type="button">
                👁️ Show Answer
              </button>
            ) : (
              <div className="quiz-answer-section">
                <p className="quiz-answer-label">
                  ✓ Answer: {String.fromCharCode(65 + q.answer_index)}
                </p>
                <p className="quiz-explanation">{q.explanation}</p>
                <div className="quiz-meta">
                  <span>Difficulty: {q.difficulty}</span>
                  <span>Objective: {q.learning_objective}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}

      <SourceContext context={payload.source_context} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Flashcards Result (flip animation)                                  */
/* ------------------------------------------------------------------ */

function FlashcardsResult({ payload }: { payload: FlashcardsPayload }): JSX.Element {
  const [flippedCards, setFlippedCards] = useState<Set<string>>(new Set());

  const toggleFlip = (id: string) => {
    setFlippedCards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div>
      <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", margin: "0 0 14px" }}>
        Click a card to flip it
      </p>

      <div className="flashcards-grid">
        {payload.flashcards.map((card) => (
          <div
            key={card.id}
            className={`flashcard ${flippedCards.has(card.id) ? "flipped" : ""}`}
            onClick={() => toggleFlip(card.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") toggleFlip(card.id); }}
          >
            <div className="flashcard-inner">
              <div className="flashcard-face flashcard-front">
                <p className="flashcard-label">Question</p>
                <p className="flashcard-content">{card.front}</p>
                <span className="flashcard-flip-hint">tap to flip</span>
              </div>
              <div className="flashcard-face flashcard-back">
                <p className="flashcard-label">Answer</p>
                <p className="flashcard-content">{card.back}</p>
                <div className="flashcard-tags">
                  {card.tags.map((tag) => (
                    <span key={tag} className="flashcard-tag">{tag}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <SourceContext context={payload.source_context} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Study Plan Result (timeline)                                        */
/* ------------------------------------------------------------------ */

function StudyPlanResult({ payload }: { payload: StudyPlanPayload }): JSX.Element {
  return (
    <div>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", margin: "0 0 16px" }}>
        {payload.total_weeks}-week revision plan
      </p>

      <div className="plan-timeline">
        {payload.weekly_plan.map((week) => (
          <div key={week.week} className="plan-week">
            <div className="plan-week-header">
              <span className="plan-week-number">Week {week.week}</span>
              <span className="plan-week-focus">— {week.focus}</span>
            </div>

            <p className="plan-sub-title">Learning Goals</p>
            <ul className="plan-list">
              {week.learning_goals.map((goal, i) => (
                <li key={`goal-${i}`}>{goal}</li>
              ))}
            </ul>

            <p className="plan-sub-title">Revision Tasks</p>
            <ul className="plan-list">
              {week.revision_tasks.map((task, i) => (
                <li key={`task-${i}`}>{task}</li>
              ))}
            </ul>

            <p className="plan-self-test">💡 {week.self_test_prompt}</p>
          </div>
        ))}
      </div>

      <SourceContext context={payload.source_context} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Result Card                                                    */
/* ------------------------------------------------------------------ */

const BADGE_MAP: Record<string, { cls: string; icon: string }> = {
  quiz: { cls: "badge-quiz", icon: "📝" },
  flashcards: { cls: "badge-flashcards", icon: "🗂️" },
  study_plan: { cls: "badge-study-plan", icon: "📅" },
};

export function GenerationResultCard({ result }: GenerationResultCardProps): JSX.Element {
  const { payload } = result;
  const badge = BADGE_MAP[result.output_type] ?? BADGE_MAP.quiz;

  return (
    <article className="result-card">
      <div className="result-query-banner">
        <p className="result-query-label">Your request</p>
        <p className="result-query-text">{result.query}</p>
      </div>

      <div className="result-card-header">
        <span className="result-card-icon">{badge.icon}</span>
        <h3 className="result-card-title">{payload.title ?? "Generated Content"}</h3>
        <span className={`result-card-badge ${badge.cls}`}>
          {result.output_type.replace("_", " ")}
        </span>
      </div>

      {payload.output_type === "quiz" && <QuizResult payload={payload} />}
      {payload.output_type === "flashcards" && <FlashcardsResult payload={payload} />}
      {payload.output_type === "study_plan" && <StudyPlanResult payload={payload} />}
    </article>
  );
}
