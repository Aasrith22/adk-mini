import { FormEvent, useMemo, useState } from "react";

import { API_BASE_URL, UploadData, uploadDocument } from "../services/api";

type UploadState = "idle" | "uploading" | "success" | "error";

export function DocumentUploader(): JSX.Element {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [message, setMessage] = useState<string>("Select a PDF and upload it to build your vector store.");
  const [result, setResult] = useState<UploadData | null>(null);

  const canUpload = useMemo(() => selectedFile !== null && uploadState !== "uploading", [selectedFile, uploadState]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();

    if (!selectedFile) {
      setUploadState("error");
      setMessage("Please choose a PDF file first.");
      return;
    }

    setUploadState("uploading");
    setMessage("Uploading and processing document...");

    try {
      const data = await uploadDocument(selectedFile);
      setResult(data);
      setUploadState("success");
      setMessage("Document uploaded and indexed successfully.");
      setSelectedFile(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed due to an unknown error.";
      setUploadState("error");
      setMessage(errorMessage);
      setResult(null);
    }
  };

  return (
    <section className="uploader-card" aria-label="Document uploader">
      <h2 className="uploader-title">Document Upload</h2>
      <p className="uploader-subtitle">
        Backend endpoint: <span>{API_BASE_URL}/api/upload</span>
      </p>

      <form className="upload-form" onSubmit={onSubmit}>
        <label className="file-label" htmlFor="pdf-file-input">
          PDF file
        </label>
        <input
          id="pdf-file-input"
          className="file-input"
          type="file"
          accept="application/pdf"
          onChange={(event) => {
            const nextFile = event.target.files?.[0] ?? null;
            setSelectedFile(nextFile);
            setUploadState("idle");
            setResult(null);
            setMessage(nextFile ? `Ready to upload ${nextFile.name}` : "Select a PDF and upload it to build your vector store.");
          }}
        />

        <button className="upload-button" type="submit" disabled={!canUpload}>
          {uploadState === "uploading" ? "Uploading..." : "Upload PDF"}
        </button>
      </form>

      <p className={`upload-message upload-message-${uploadState}`}>{message}</p>

      {result && (
        <div className="upload-result" aria-live="polite">
          <h3>Ingestion Summary</h3>
          <dl>
            <div>
              <dt>Document ID</dt>
              <dd>{result.document_id}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>{result.source_file}</dd>
            </div>
            <div>
              <dt>Pages</dt>
              <dd>{result.pages_loaded}</dd>
            </div>
            <div>
              <dt>Base Chunks</dt>
              <dd>{result.base_chunks}</dd>
            </div>
            <div>
              <dt>Enrichment Chunks</dt>
              <dd>{result.enrichment_chunks}</dd>
            </div>
            <div>
              <dt>Total Stored Chunks</dt>
              <dd>{result.stored_chunks}</dd>
            </div>
            <div>
              <dt>Embedding Model</dt>
              <dd>{result.embedding_model}</dd>
            </div>
            <div>
              <dt>Chunking</dt>
              <dd>
                {result.chunking.chunk_size}/{result.chunking.chunk_overlap}
              </dd>
            </div>
            <div>
              <dt>Enrichment Applied</dt>
              <dd>{result.enrichment_applied ? "Yes" : "No"}</dd>
            </div>
          </dl>
        </div>
      )}
    </section>
  );
}
