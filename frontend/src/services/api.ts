const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = buildUrl(path);

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`GET ${url} failed with status ${response.status}`);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `No se pudo conectar con ${url}. Verifica backend, URL o CORS.`+String(error.message)
      );
    }

    if (error instanceof Error) {
      throw error;
    }

    throw new Error(`Error desconocido al conectar con ${url}`);
  }
}