import { useState, useCallback } from "react";
import { DocumentUploader } from "./components/DocumentUploader";
import { GenerationStudio } from "./components/GenerationStudio";
import { GenerationResultCard } from "./components/GenerationResultCard";
import type { GenerationData, UploadData } from "./services/api";

type TabId = "upload" | "generate" | "results";

const TABS: { id: TabId; label: string; number: string }[] = [
  { id: "upload", label: "Upload", number: "1" },
  { id: "generate", label: "Generate", number: "2" },
  { id: "results", label: "Results", number: "3" },
];

export default function App(): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>("upload");
  const [uploadData, setUploadData] = useState<UploadData | null>(null);
  const [results, setResults] = useState<GenerationData[]>([]);

  const handleUploadSuccess = useCallback((data: UploadData) => {
    setUploadData(data);
  }, []);

  const handleGenerated = useCallback((data: GenerationData) => {
    setResults((prev) => [data, ...prev]);
    setActiveTab("results");
  }, []);

  const goToGenerate = useCallback(() => setActiveTab("generate"), []);

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="app-logo">🧠</div>
        <h1>EduSynapse</h1>
        <p className="app-tagline">
          Upload study materials, generate quizzes, flashcards &amp; study plans with AI
        </p>
      </header>

      <nav className="tab-nav" role="tablist" aria-label="Main navigation">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            className={`tab-button ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-number">{tab.number}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "upload" && (
        <div role="tabpanel" id="panel-upload" aria-labelledby="tab-upload">
          <DocumentUploader
            onUploadSuccess={handleUploadSuccess}
            onProceed={goToGenerate}
            uploadData={uploadData}
          />
        </div>
      )}

      {activeTab === "generate" && (
        <div role="tabpanel" id="panel-generate" aria-labelledby="tab-generate">
          <GenerationStudio
            hasUploadedDocuments={uploadData !== null}
            documentId={uploadData?.document_id ?? null}
            onGenerated={handleGenerated}
          />
        </div>
      )}

      {activeTab === "results" && (
        <div role="tabpanel" id="panel-results" aria-labelledby="tab-results">
          {results.length === 0 ? (
            <div className="glass-card">
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <h3>No results yet</h3>
                <p>Generate a quiz, flashcard set, or study plan to see your results here.</p>
              </div>
            </div>
          ) : (
            <div className="results-list">
              {results.map((result, index) => (
                <GenerationResultCard key={`result-${index}`} result={result} />
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
