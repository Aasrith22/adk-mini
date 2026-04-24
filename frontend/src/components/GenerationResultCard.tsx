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

type SourceContextListProps = {
  context: SourceContextItem[];
};

function SourceContextList({ context }: SourceContextListProps): JSX.Element {
  return (
    <section className="result-section" aria-label="Source context">
      <h4>Source Context</h4>
      <div className="source-context-list">
        {context.map((item, index) => (
          <article key={`${item.source}-${item.page ?? "na"}-${index}`} className="source-context-item">
            <p className="source-context-meta">
              <strong>{item.source}</strong> {item.page !== null ? `- page ${item.page}` : "- page n/a"}
            </p>
            <p>{item.snippet}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function QuizResult({ payload }: { payload: QuizPayload }): JSX.Element {
  return (
    <div className="result-layout">
      <section className="result-section">
        <h3>{payload.title}</h3>
        <p>{payload.instructions}</p>
      </section>

      <section className="result-section" aria-label="Quiz questions">
        <h4>Questions ({payload.questions.length})</h4>
        <div className="quiz-list">
          {payload.questions.map((question, questionIndex) => (
            <article key={question.id} className="quiz-item">
              <p className="quiz-question">
                {questionIndex + 1}. {question.question}
              </p>
              <ol className="quiz-options" type="A">
                {question.options.map((option, optionIndex) => (
                  <li key={`${question.id}-option-${optionIndex}`}>{option}</li>
                ))}
              </ol>
              <p className="quiz-answer">
                Answer: {String.fromCharCode(65 + question.answer_index)} | Difficulty: {question.difficulty}
              </p>
              <p className="quiz-explanation">{question.explanation}</p>
              <p className="quiz-objective">Objective: {question.learning_objective}</p>
            </article>
          ))}
        </div>
      </section>

      <SourceContextList context={payload.source_context} />
    </div>
  );
}

function FlashcardsResult({ payload }: { payload: FlashcardsPayload }): JSX.Element {
  return (
    <div className="result-layout">
      <section className="result-section">
        <h3>{payload.title}</h3>
        <p>{payload.flashcards.length} flashcards generated.</p>
      </section>

      <section className="result-section" aria-label="Flashcards">
        <h4>Flashcards</h4>
        <div className="flashcards-grid">
          {payload.flashcards.map((card) => (
            <article key={card.id} className="flashcard-item">
              <p className="flashcard-front">Q: {card.front}</p>
              <p className="flashcard-back">A: {card.back}</p>
              <p className="flashcard-meta">
                Difficulty: {card.difficulty} | Tags: {card.tags.join(", ")}
              </p>
            </article>
          ))}
        </div>
      </section>

      <SourceContextList context={payload.source_context} />
    </div>
  );
}

function StudyPlanResult({ payload }: { payload: StudyPlanPayload }): JSX.Element {
  return (
    <div className="result-layout">
      <section className="result-section">
        <h3>{payload.title}</h3>
        <p>{payload.total_weeks} week study plan generated.</p>
      </section>

      <section className="result-section" aria-label="Weekly plan">
        <h4>Weekly Plan</h4>
        <div className="plan-list">
          {payload.weekly_plan.map((weekItem) => (
            <article key={weekItem.week} className="plan-item">
              <h5>Week {weekItem.week}</h5>
              <p className="plan-focus">Focus: {weekItem.focus}</p>
              <div>
                <p className="plan-subtitle">Learning Goals</p>
                <ul>
                  {weekItem.learning_goals.map((goal) => (
                    <li key={goal}>{goal}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="plan-subtitle">Revision Tasks</p>
                <ul>
                  {weekItem.revision_tasks.map((task) => (
                    <li key={task}>{task}</li>
                  ))}
                </ul>
              </div>
              <p className="plan-self-test">Self-test: {weekItem.self_test_prompt}</p>
            </article>
          ))}
        </div>
      </section>

      <SourceContextList context={payload.source_context} />
    </div>
  );
}

export function GenerationResultCard({ result }: GenerationResultCardProps): JSX.Element {
  const payload = result.payload;

  return (
    <div className="generation-result-card">
      <div className="generation-result-header">
        <p>
          Mode: <strong>{result.output_type}</strong>
        </p>
        <p>
          Agent: <strong>{result.generator_agent}</strong>
        </p>
      </div>

      {payload.output_type === "quiz" && <QuizResult payload={payload} />}
      {payload.output_type === "flashcards" && <FlashcardsResult payload={payload} />}
      {payload.output_type === "study_plan" && <StudyPlanResult payload={payload} />}
    </div>
  );
}
