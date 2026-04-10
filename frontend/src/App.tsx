import { useState } from "react";
import { HealthStatus } from "./components/HealthStatus";
import { LoginButton } from "./components/LoginButton";
import { QueryBox } from "./components/QueryBox";
import { queryCopilot } from "./services/queryService";
import type { QueryResponse } from "./types/query";
import { useAuth } from "./auth/useAuth";

function App() {
  const { accessToken, isAuthenticated, isLoadingAuth, refreshAccessToken } =
    useAuth();
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const trimmedQuery = query.trim();
  const isQueryEmpty = trimmedQuery.length === 0;
  const isQueryButtonDisabled =
    isSubmitting || isLoadingAuth || isQueryEmpty || !isAuthenticated;

  let queryStatusMessage: string | null = null;

  if (isSubmitting) {
    queryStatusMessage = "Se esta enviando la consulta al backend.";
  } else if (isLoadingAuth) {
    queryStatusMessage = "Cargando sesion...";
  } else if (!isAuthenticated) {
    queryStatusMessage = "Inicia sesion para consultar el backend.";
  } else if (isQueryEmpty) {
    queryStatusMessage = "Escribe una consulta para habilitar el boton.";
  }

  const handleQuery = async () => {
    if (!trimmedQuery) {
      setQueryError("Debes ingresar una consulta antes de continuar.");
      setResponse(null);
      return;
    }

    if (!isAuthenticated) {
      setQueryError("Debes iniciar sesion para consultar el backend.");
      setResponse(null);
      return;
    }

    try {
      setIsSubmitting(true);
      setQueryError(null);

      const tokenToUse = accessToken ?? (await refreshAccessToken());
      if (!tokenToUse) {
        setQueryError("No se pudo obtener el token de acceso para consultar.");
        setResponse(null);
        return;
      }

      const result = await queryCopilot({
        query: trimmedQuery,
        stream: false,
      }, tokenToUse);

      setResponse(result);
    } catch (error) {
      setQueryError(
        error instanceof Error
          ? error.message
          : "No se pudo procesar la consulta."
      );
      setResponse(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Architecture Governance Copilot</h1>
          <p>MVP Frontend Base</p>
        </div>

        <div className="header-actions">
          <HealthStatus />
          <LoginButton />
        </div>
      </header>

      <main className="app-main">
        <section className="panel">
          <h2>Consulta</h2>
          <QueryBox query={query} setQuery={setQuery} />
          <div style={{ marginTop: "12px" }}>
            <button
              disabled={isQueryButtonDisabled}
              onClick={() => void handleQuery()}
            >
              {isSubmitting ? "Consultando..." : "Consultar"}
            </button>
          </div>
          {queryStatusMessage && (
            <div style={{ marginTop: "12px", color: "#475569" }}>
              {queryStatusMessage}
            </div>
          )}
          {queryError && (
            <div style={{ marginTop: "12px", color: "#b91c1c" }}>
              {queryError}
            </div>
          )}
        </section>

        <section className="panel">
          <h2>Respuesta</h2>
          <div className="response-placeholder">
            {response ? (
              <div>
                <p>{response.answer}</p>
                <small>
                  Session: {response.session_id} | Trace: {response.trace_id} |
                  Tokens: {response.tokens_used} | Latencia:{" "}
                  {response.latency_ms.toFixed(2)} ms
                </small>
              </div>
            ) : (
              "Aqui se mostrara la respuesta del copiloto."
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
