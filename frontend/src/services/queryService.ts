import { apiPost } from "./api";
import type { QueryRequest, QueryResponse } from "../types/query";

export async function queryCopilot(
  payload: QueryRequest,
  accessToken: string
): Promise<QueryResponse> {
  return apiPost<QueryResponse>("/api/v1/query", payload, accessToken);
}
