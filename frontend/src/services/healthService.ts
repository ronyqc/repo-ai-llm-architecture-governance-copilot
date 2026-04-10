import { apiGet } from "./api";
import type { HealthResponse } from "../types/health";

export async function getHealthStatus(
  accessToken?: string
): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/api/v1/health", { accessToken });
}
