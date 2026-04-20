export type KnowledgeDomain =
  | "bian"
  | "building_blocks"
  | "guidelines_patterns";

export type UploadUrlRequest = {
  file_name: string;
};

export type UploadUrlResponse = {
  upload_url: string;
  blob_url: string;
  blob_name: string;
  expires_in_seconds: number;
};

export type IngestRequest = {
  file_name: string;
  file_url: string;
  knowledge_domain: KnowledgeDomain;
  metadata: Record<string, string>;
};

export type IngestResponse = {
  status: "accepted";
  message: string;
  trace_id: string;
};

export type AdminUploadPhase =
  | "idle"
  | "subiendo"
  | "subido"
  | "procesando"
  | "procesado"
  | "error";
