type JwtPayload = {
  roles?: string[] | string;
  scp?: string;
};

export type AccessTokenClaims = {
  roles: string[];
  scopes: string[];
  isAdmin: boolean;
};

export function getAccessTokenClaims(token: string | null): AccessTokenClaims {
  if (!token || token.trim().length === 0) {
    return {
      roles: [],
      scopes: [],
      isAdmin: false,
    };
  }

  try {
    const [, payloadSegment] = token.split(".");
    if (!payloadSegment) {
      return {
        roles: [],
        scopes: [],
        isAdmin: false,
      };
    }

    const normalized = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      "="
    );
    const decoded = window.atob(padded);
    const payload = JSON.parse(decoded) as JwtPayload;

    const roles = Array.isArray(payload.roles)
      ? payload.roles.map((role) => String(role))
      : typeof payload.roles === "string" && payload.roles.trim().length > 0
        ? [payload.roles.trim()]
        : [];

    const scopes =
      typeof payload.scp === "string" && payload.scp.trim().length > 0
        ? payload.scp.trim().split(/\s+/)
        : [];

    const isAdmin =
      roles.some((role) => role.toLowerCase() === "admin") ||
      scopes.some((scope) => scope.toLowerCase() === "admin");

    return {
      roles,
      scopes,
      isAdmin,
    };
  } catch {
    return {
      roles: [],
      scopes: [],
      isAdmin: false,
    };
  }
}
