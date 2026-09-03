export type DocumentStatus = "UPLOADING" | "PROCESSING" | "READY" | "FAILED";

export interface DocChatDocument {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  page_count: number | null;
  chunk_count: number | null;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocChatDocument[];
  total: number;
}

export interface Conversation {
  id: string;
  title: string;
  document_ids: string[];
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
}

export type MessageRole = "user" | "assistant";

export interface SourceCitation {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  similarity_score: number;
}

export interface DebugRetrievedChunk {
  filename: string;
  page_number: number;
  score: number;
  used: boolean;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  sources: SourceCitation[];
  debug_retrieved_chunks?: DebugRetrievedChunk[] | null;
  created_at: string;
}

export interface MessageListResponse {
  messages: Message[];
}

export type StreamEvent =
  | { type: "delta"; text: string }
  | { type: "done"; message: Message }
  | { type: "error"; message: string; code: string };

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
  vector_search: "ok" | "not_configured" | "unavailable" | "unknown";
  llm: "ok" | "unavailable";
}
