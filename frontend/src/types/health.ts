export type HealthResponse = {
  status: "healthy" | "degraded" | "unhealthy";
  components: {
    backend?: string;
    azure_openai?: string;
    azure_ai_search?: string;
    blob_storage?: string;
    context_store?: string;
  };
  timestamp: string;
};