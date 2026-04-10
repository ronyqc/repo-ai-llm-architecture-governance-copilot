const ACCESS_TOKEN_KEY = "auth.accessToken";

export function setStoredAccessToken(token: string | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (token && token.trim().length > 0) {
    window.sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
    return;
  }

  window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const token = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
  return token && token.trim().length > 0 ? token : null;
}
