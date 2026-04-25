import { FormEvent, useCallback, useRef, useState } from "react";
import { UploadData, uploadDocument } from "../services/api";

type UploadState = "idle" | "uploading" | "success" | "error";

type DocumentUploaderProps = {
  onUploadSuccess: (data: UploadData) => void;
  onProceed: () => void;
  uploadData: UploadData | null;
};

export function DocumentUploader({ onUploadSuccess, onProceed, uploadData }: DocumentUploaderProps): JSX.Element {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>(uploadData ? "success" : "idle");
  const [message, setMessage] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleFile = (file: File | null) => {
    if (file && file.type !== "application/pdf") {
      setMessage("Only PDF files are supported.");
      setUploadState("error");
      return;
    }
    setSelectedFile(file);
    setUploadState("idle");
    setMessage("");
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0] ?? null;
    handleFile(file);
  }, []);

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!selectedFile) {
      setUploadState("error");
      setMessage("Please choose a PDF file first.");
      return;
    }

    setUploadState("uploading");
    setMessage("Processing your document...");

    try {
      const data = await uploadDocument(selectedFile);
      onUploadSuccess(data);
      setUploadState("success");
      setMessage("Document uploaded and indexed successfully!");
      setSelectedFile(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed.";
      setUploadState("error");
      setMessage(errorMessage);
    }
  };

  const currentData = uploadData;

  return (
    <section className="glass-card" aria-label="Document uploader">
      <div className="section-icon">📄</div>
      <h2 className="section-title">Upload Study Material</h2>
      <p className="section-desc">
        Drop a PDF file — your textbook, syllabus, or notes — and we'll chunk, embed, and index it for AI generation.
      </p>

      <form onSubmit={onSubmit}>
        <div
          className={`drop-zone ${dragOver ? "drag-over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click(); }}
        >
          <div className="drop-zone-icon">⬆️</div>
          <p className="drop-zone-text">
            Drag &amp; drop a PDF here, or <strong>click to browse</strong>
          </p>
          <p className="drop-zone-hint">Supports PDF files up to 25 MB</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            style={{ display: "none" }}
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {selectedFile && (
          <div className="file-preview">
            <span className="file-preview-icon">📎</span>
            <div className="file-preview-info">
              <p className="file-preview-name">{selectedFile.name}</p>
              <p className="file-preview-size">{formatFileSize(selectedFile.size)}</p>
            </div>
            <button
              type="button"
              className="file-remove"
              onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
              aria-label="Remove file"
            >
              ✕
            </button>
          </div>
        )}

        <div className="form-actions">
          <button
            className="btn btn-primary"
            type="submit"
            disabled={!selectedFile || uploadState === "uploading"}
          >
            {uploadState === "uploading" ? (
              <>
                <span className="spinner" />
                Processing...
              </>
            ) : (
              "Upload & Index"
            )}
          </button>

          {currentData && (
            <button type="button" className="btn btn-secondary" onClick={onProceed}>
              Proceed to Generate →
            </button>
          )}
        </div>
      </form>

      {message && uploadState !== "idle" && (
        <div className={`status-message ${
          uploadState === "success" ? "status-success" :
          uploadState === "error" ? "status-error" : "status-info"
        }`}>
          {message}
        </div>
      )}

      {currentData && (
        <div className="upload-summary">
          <div className="summary-stat">
            <span className="summary-stat-value">{currentData.pages_loaded}</span>
            <span className="summary-stat-label">Pages</span>
          </div>
          <div className="summary-stat">
            <span className="summary-stat-value">{currentData.stored_chunks}</span>
            <span className="summary-stat-label">Chunks Indexed</span>
          </div>
          <div className="summary-stat">
            <span className="summary-stat-value">{currentData.enrichment_applied ? "Yes" : "No"}</span>
            <span className="summary-stat-label">Web Enriched</span>
          </div>
        </div>
      )}
    </section>
  );
}
