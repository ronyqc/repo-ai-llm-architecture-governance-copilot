import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/useAuth";
import { getHealthStatus } from "../services/healthService";
import type { HealthResponse } from "../types/health";

export function HealthStatus() {
  const { accessToken, refreshAccessToken, isAuthenticated } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const tokenToUse = isAuthenticated
        ? accessToken ?? (await refreshAccessToken())
        : undefined;
      const result = await getHealthStatus(tokenToUse ?? undefined);
      setHealth(result);

    } catch (err) {
      setError("No se pudo conectar con el backend "+ String(err));
    } finally {
      setLoading(false);
    }
  }, [accessToken, isAuthenticated, refreshAccessToken]);

  useEffect(() => {
    void loadHealth();
  }, [loadHealth]);

  if (loading) {
    return <span>Verificando backend...</span>;
  }

  if (error) {
    return (
      <div>
        <span>{error}</span>{" "}
        <button onClick={() => void loadHealth()}>Reintentar</button>
      </div>
    );
  }

  return (
    <div>
      <strong>Backend:</strong> {health?.status}
    </div>
  );
}
