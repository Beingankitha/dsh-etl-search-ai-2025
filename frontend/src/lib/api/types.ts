export interface Dataset {
  file_identifier: string;
  title: string;
  abstract: string;

  topic_category: string[];
  keywords: string[];

  lineage?: string | null;
  supplemental_info?: string | null;
}

export interface SearchResult {
  dataset: Dataset;
  score: number; // expected 0..1
}

export interface SearchRequest {
  query: string;
  top_k?: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export type ChatRole = "system" | "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  top_k?: number;
}

export interface ChatResponse {
  message: ChatMessage;
  sources: SearchResult[];
}