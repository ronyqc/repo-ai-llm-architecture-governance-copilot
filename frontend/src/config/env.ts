function getRequiredEnv(name: keyof ImportMetaEnv): string {
  const value = import.meta.env[name];

  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(
      `Missing required environment variable: ${name}. Check frontend/.env before starting the app.`
    );
  }

  return value.trim();
}

function getOptionalEnv(name: keyof ImportMetaEnv): string | undefined {
  const value = import.meta.env[name];

  if (typeof value !== "string") {
    return undefined;
  }

  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : undefined;
}

export const env = {
  apiBaseUrl: getOptionalEnv("VITE_API_BASE_URL") ?? "http://localhost:8000",
  entraClientId: getRequiredEnv("VITE_ENTRA_CLIENT_ID"),
  entraTenantId: getRequiredEnv("VITE_ENTRA_TENANT_ID"),
  entraRedirectUri: getRequiredEnv("VITE_ENTRA_REDIRECT_URI"),
  entraPopupRedirectUri:
    getOptionalEnv("VITE_ENTRA_POPUP_REDIRECT_URI") ??
    new URL("/redirect.html", getRequiredEnv("VITE_ENTRA_REDIRECT_URI")).toString(),
  apiScope: getRequiredEnv("VITE_API_SCOPE"),
};
