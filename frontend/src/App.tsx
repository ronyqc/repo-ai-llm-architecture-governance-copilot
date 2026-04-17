import { useState } from "react";
import { HealthStatus } from "./components/HealthStatus";
import { LoginButton } from "./components/LoginButton";
import { QueryBox } from "./components/QueryBox";
import { queryCopilot } from "./services/queryService";
import type { QueryResponse } from "./types/query";
import { useAuth } from "./auth/useAuth";

function formatAnswer(answer: string) {
  return answer
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter((block) => block.length > 0)
    .map((block) => {
      const lines = block
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

      const heading = lines.length === 1 && /^##\s+/.test(lines[0]);
      if (heading) {
        return {
          type: "heading" as const,
          content: lines[0].replace(/^##\s+/, ""),
        };
      }

      const isBulletBlock = lines.every((line) => /^[-*]\s+/.test(line));
      if (isBulletBlock) {
        return {
          type: "list" as const,
          items: lines.map((line) => line.replace(/^[-*]\s+/, "")),
        };
      }

      return {
        type: "paragraph" as const,
        content: block,
      };
    });
}

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
  const formattedAnswer = response ? formatAnswer(response.answer) : [];

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
              <div className="response-card">
                <div className="response-body">
                  {formattedAnswer.map((block, index) =>
                    block.type === "heading" ? (
                      <h3 className="answer-heading" key={`heading-${index}`}>
                        {block.content}
                      </h3>
                    ) : block.type === "list" ? (
                      <ul className="answer-list" key={`list-${index}`}>
                        {block.items.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="answer-paragraph" key={`paragraph-${index}`}>
                        {block.content}
                      </p>
                    )
                  )}
                </div>

                {response.sources.length > 0 && (
                  <div className="sources-section">
                    <h3>Fuentes utilizadas</h3>
                    <div className="sources-list">
                      {response.sources.map((source) => (
                        <article
                          className="source-card"
                          key={`${source.source_id}-${source.title}`}
                        >
                          <div className="source-card-header">
                            <strong>{source.title || "Sin titulo"}</strong>
                            <span className="source-score">
                              Score {source.score.toFixed(3)}
                            </span>
                          </div>
                          <div className="source-card-meta">
                            <span>ID: {source.source_id}</span>
                            <span>Tipo: {source.source_type || "n/a"}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                )}

                <div className="response-metadata">
                  <span>Session: {response.session_id}</span>
                  <span>Trace: {response.trace_id}</span>
                  <span>Tokens: {response.tokens_used}</span>
                  <span>Latencia: {response.latency_ms.toFixed(2)} ms</span>
                </div>
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
