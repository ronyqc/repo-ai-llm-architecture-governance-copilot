export type SourceReference = {
  source_id: string;
  source_type: string;
  title: string;
  score: number;
};

export type QueryRequest = {
  query: string;
  session_id?: string;
  stream?: boolean;
};

export type QueryResponse = {
  answer: string;
  sources: SourceReference[];
  tokens_used: number;
  latency_ms: number;
  trace_id: string;
  session_id: string;
};
