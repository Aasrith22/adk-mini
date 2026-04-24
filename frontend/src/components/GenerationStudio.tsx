import { FormEvent, useMemo, useState } from "react";

import { API_BASE_URL, GenerationData, OutputType, generateArtifact } from "../services/api";
import { GenerationResultCard } from "./GenerationResultCard";

type GenerationMode = "auto" | OutputType;
type ExchangeStatus = "loading" | "success" | "error";

type GenerationExchange = {
  id: string;
  query: string;
  requestedMode: GenerationMode;
  status: ExchangeStatus;
  response: GenerationData | null;
  errorMessage: string | null;
};

const OUTPUT_MODE_LABELS: Record<GenerationMode, string> = {
  auto: "Auto",
  quiz: "Quiz",
  flashcards: "Flashcards",
  study_plan: "Study Plan",
};

export function GenerationStudio(): JSX.Element {
  const [query, setQuery] = useState<string>("");
  const [mode, setMode] = useState<GenerationMode>("auto");
  const [statusMessage, setStatusMessage] = useState<string>(
    "Ask for a quiz, flashcards, or a revision plan based on uploaded materials.",
  );
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [history, setHistory] = useState<GenerationExchange[]>([]);

  const canGenerate = useMemo(() => query.trim().length > 0 && !isGenerating, [query, isGenerating]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setStatusMessage("Please enter a generation request first.");
      return;
    }

    const exchangeId = crypto.randomUUID();
    const pendingExchange: GenerationExchange = {
      id: exchangeId,
      query: trimmedQuery,
      requestedMode: mode,
      status: "loading",
      response: null,
      errorMessage: null,
    };

    setHistory((previous) => [pendingExchange, ...previous]);
    setQuery("");
    setIsGenerating(true);
    setStatusMessage("Generating structured output from your indexed context...");

    try {
      const response = await generateArtifact({
        query: trimmedQuery,
        outputType: mode === "auto" ? undefined : mode,
      });

      setHistory((previous) =>
        previous.map((item) =>
          item.id === exchangeId ? { ...item, status: "success", response, errorMessage: null } : item,
        ),
      );
      setStatusMessage("Generation completed successfully.");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Generation failed due to an unknown error.";

      setHistory((previous) =>
        previous.map((item) =>
          item.id === exchangeId ? { ...item, status: "error", response: null, errorMessage } : item,
        ),
      );
      setStatusMessage(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <section className="generator-card" aria-label="AI generation workspace">
      <h2 className="generator-title">AI Generation Workspace</h2>
      <p className="generator-subtitle">
        Backend endpoint: <span>{API_BASE_URL}/api/generate</span>
      </p>

      <form className="generator-form" onSubmit={onSubmit}>
        <label className="generator-label" htmlFor="generation-query">
          Request
        </label>
        <textarea
          id="generation-query"
          className="generator-input"
          rows={4}
          placeholder="Example: Generate a Unit 1 quiz with conceptual and calculation questions"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={isGenerating}
        />

        <div className="generator-controls">
          <label className="generator-label" htmlFor="generation-mode">
            Output type
          </label>
          <select
            id="generation-mode"
            className="generator-select"
            value={mode}
            onChange={(event) => setMode(event.target.value as GenerationMode)}
            disabled={isGenerating}
          >
            <option value="auto">Auto</option>
            <option value="quiz">Quiz</option>
            <option value="flashcards">Flashcards</option>
            <option value="study_plan">Study Plan</option>
          </select>

          <button className="generate-button" type="submit" disabled={!canGenerate}>
            {isGenerating ? "Generating..." : "Generate"}
          </button>
        </div>
      </form>

      <p className={`generation-message generation-message-${isGenerating ? "running" : "idle"}`}>{statusMessage}</p>

      <div className="generation-thread" aria-live="polite">
        {history.length === 0 && (
          <p className="thread-empty">No generations yet. Upload a PDF, then submit your first request.</p>
        )}

        {history.map((exchange) => (
          <article key={exchange.id} className="thread-item">
            <section className="thread-message thread-message-user" aria-label="User request">
              <p className="thread-role">You</p>
              <p className="thread-query">{exchange.query}</p>
              <p className="thread-meta">Requested mode: {OUTPUT_MODE_LABELS[exchange.requestedMode]}</p>
            </section>

            <section className="thread-message thread-message-assistant" aria-label="Model response">
              <p className="thread-role">EduSynapse AI</p>

              {exchange.status === "loading" && <p className="thread-loading">Generating response...</p>}

              {exchange.status === "error" && exchange.errorMessage && (
                <p className="thread-error">{exchange.errorMessage}</p>
              )}

              {exchange.status === "success" && exchange.response && (
                <GenerationResultCard result={exchange.response} />
              )}
            </section>
          </article>
        ))}
      </div>
    </section>
  );
}
