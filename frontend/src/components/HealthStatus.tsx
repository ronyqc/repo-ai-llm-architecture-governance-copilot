import { useEffect, useState } from "react";
import { getHealthStatus } from "../services/healthService";
import type { HealthResponse } from "../types/health";

export function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getHealthStatus();
      setHealth(result);
    } catch (err) {
      setError("No se pudo conectar con el backend "+ String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadHealth();
  }, []);

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