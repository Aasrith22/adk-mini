import { FormEvent, useState } from "react";
import { GenerationData, OutputType, generateArtifact } from "../services/api";

type GenerationStudioProps = {
  hasUploadedDocuments: boolean;
  documentId: string | null;
  onGenerated: (data: GenerationData) => void;
};

type OutputMode = "auto" | OutputType;

const OUTPUT_MODES: { id: OutputMode; icon: string; label: string; desc: string }[] = [
  { id: "quiz", icon: "📝", label: "Quiz", desc: "MCQ assessment" },
  { id: "flashcards", icon: "🗂️", label: "Flashcards", desc: "Memory cards" },
  { id: "study_plan", icon: "📅", label: "Study Plan", desc: "Weekly revision" },
];

export function GenerationStudio({ hasUploadedDocuments, documentId, onGenerated }: GenerationStudioProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<OutputMode>("quiz");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canGenerate = query.trim().length > 0 && !isGenerating;

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setIsGenerating(true);
    setError(null);

    try {
      const response = await generateArtifact({
        query: trimmedQuery,
        outputType: mode === "auto" ? undefined : mode,
        documentId: documentId ?? undefined,
      });
      onGenerated(response);
      setQuery("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  if (!hasUploadedDocuments) {
    return (
      <section className="glass-card">
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <h3>Upload a document first</h3>
          <p>Go to the Upload tab and add your study materials before generating content.</p>
        </div>
      </section>
    );
  }

  if (isGenerating) {
    return (
      <section className="glass-card">
        <div className="loading-state">
          <div className="spinner spinner-lg" />
          <p>Generating your {mode === "auto" ? "content" : mode.replace("_", " ")}...</p>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            Retrieving context, synthesising, and structuring output
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="glass-card" aria-label="AI generation workspace">
      <div className="section-icon">✨</div>
      <h2 className="section-title">Generate Study Content</h2>
      <p className="section-desc">
        Choose an output type and describe what you'd like to generate from your uploaded materials.
      </p>

      <div className="output-type-grid">
        {OUTPUT_MODES.map((item) => (
          <div
            key={item.id}
            className={`output-type-card ${mode === item.id ? "selected" : ""}`}
            onClick={() => setMode(item.id)}
            role="radio"
            aria-checked={mode === item.id}
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setMode(item.id); }}
          >
            <div className="output-type-icon">{item.icon}</div>
            <p className="output-type-label">{item.label}</p>
            <p className="output-type-desc">{item.desc}</p>
          </div>
        ))}
      </div>

      <form onSubmit={onSubmit} style={{ marginTop: "20px" }}>
        <div className="form-group">
          <label className="label" htmlFor="generation-query">
            Your request
          </label>
          <textarea
            id="generation-query"
            className="textarea"
            rows={3}
            placeholder={
              mode === "quiz"
                ? "e.g. Generate a Unit 1 quiz covering key definitions and calculations"
                : mode === "flashcards"
                ? "e.g. Create flashcards for Chapter 3 — cell biology key terms"
                : mode === "study_plan"
                ? "e.g. Build a 4-week revision plan for the midterm exam"
                : "Describe what you want to generate..."
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={!canGenerate}>
            Generate {mode === "auto" ? "" : mode.replace("_", " ")}
          </button>
        </div>
      </form>

      {error && (
        <div className="status-message status-error">{error}</div>
      )}
    </section>
  );
}
