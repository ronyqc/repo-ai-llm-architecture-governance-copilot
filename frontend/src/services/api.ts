import { env } from "../config/env";

const API_BASE_URL = env.apiBaseUrl.replace(/\/+$/, "");

export type ApiRequestOptions = {
  accessToken?: string;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export async function apiGet<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const url = buildUrl(path);
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.accessToken) {
    headers.set("Authorization", `Bearer ${options.accessToken}`);
  }

  try {
    const response = await fetch(url, {
      method: "GET",
      headers,
      signal: options.signal,
    });

    if (!response.ok) {
      throw new Error(`GET ${url} failed with status ${response.status}`);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `No se pudo conectar con ${url}. Verifica backend, URL o CORS. ${error.message}`
      );
    }

    if (error instanceof Error) {
      throw error;
    }

    throw new Error(`Error desconocido al conectar con ${url}`);
  }
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  accessToken?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`POST ${path} failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}
