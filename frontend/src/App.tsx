import { DocumentUploader } from "./components/DocumentUploader";

export default function App(): JSX.Element {
  return (
    <main className="app-shell">
      <header className="app-header">
        <p className="eyebrow">AI Learning System</p>
        <h1>Academic Material Ingestion</h1>
        <p>
          Upload syllabus PDFs, textbooks, and notes to prepare your RAG vector index for quiz, flashcard, and study plan generation.
        </p>
      </header>

      <DocumentUploader />
    </main>
  );
}
