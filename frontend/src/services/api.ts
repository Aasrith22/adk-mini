export type UploadChunking = {
  chunk_size: number;
  chunk_overlap: number;
};

export type UploadData = {
  document_id: string;
  source_file: string;
  pages_loaded: number;
  base_chunks: number;
  enrichment_chunks: number;
  stored_chunks: number;
  enrichment_applied: boolean;
  embedding_model: string;
  chunking: UploadChunking;
};

type UploadApiSuccess = {
  status: "success";
  data: UploadData;
};

type UploadApiError = {
  error?: string;
  details?: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";

export async function uploadDocument(file: File): Promise<UploadData> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => ({}))) as UploadApiError;
    const message = errorPayload.error ?? "Upload failed.";
    const details = errorPayload.details ? ` ${errorPayload.details}` : "";
    throw new Error(`${message}${details}`.trim());
  }

  const payload = (await response.json()) as UploadApiSuccess;
  return payload.data;
}

export { API_BASE_URL };
