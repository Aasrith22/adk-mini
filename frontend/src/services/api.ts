export type UploadChunking = {
  chunk_size: number;
  chunk_overlap: number;
};

export type OutputType = "quiz" | "flashcards" | "study_plan";

export type SourceContextItem = {
  source: string;
  page: number | null;
  snippet: string;
};

export type DifficultyLevel = "easy" | "medium" | "hard";

export type QuizQuestion = {
  id: string;
  question: string;
  options: [string, string, string, string];
  answer_index: 0 | 1 | 2 | 3;
  explanation: string;
  difficulty: DifficultyLevel;
  learning_objective: string;
};

export type QuizPayload = {
  output_type: "quiz";
  title: string;
  instructions: string;
  questions: QuizQuestion[];
  source_context: SourceContextItem[];
};

export type Flashcard = {
  id: string;
  front: string;
  back: string;
  difficulty: DifficultyLevel;
  tags: string[];
};

export type FlashcardsPayload = {
  output_type: "flashcards";
  title: string;
  flashcards: Flashcard[];
  source_context: SourceContextItem[];
};

export type StudyPlanWeek = {
  week: number;
  focus: string;
  learning_goals: string[];
  revision_tasks: string[];
  self_test_prompt: string;
};

export type StudyPlanPayload = {
  output_type: "study_plan";
  title: string;
  total_weeks: number;
  weekly_plan: StudyPlanWeek[];
  source_context: SourceContextItem[];
};

export type GeneratedPayload = QuizPayload | FlashcardsPayload | StudyPlanPayload;

export type GenerationData = {
  query: string;
  output_type: OutputType;
  supervisor_agent: string;
  generator_agent: string;
  payload: GeneratedPayload;
};

export type GenerateArtifactInput = {
  query: string;
  outputType?: OutputType;
  documentId?: string;
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

type GenerateApiSuccess = {
  status: "success";
  data: GenerationData;
};

type UploadApiError = {
  error?: string;
  details?: string;
};

type GenerateApiError = UploadApiError;

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

export async function generateArtifact(input: GenerateArtifactInput): Promise<GenerationData> {
  const body = {
    query: input.query,
    ...(input.outputType ? { output_type: input.outputType } : {}),
    ...(input.documentId ? { document_id: input.documentId } : {}),
  };

  const response = await fetch(`${API_BASE_URL}/api/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => ({}))) as GenerateApiError;
    const message = errorPayload.error ?? "Generation failed.";
    const details = errorPayload.details ? ` ${errorPayload.details}` : "";
    throw new Error(`${message}${details}`.trim());
  }

  const payload = (await response.json()) as GenerateApiSuccess;
  return payload.data;
}

// API_BASE_URL is intentionally kept private — not exposed to UI components.
