import { useState } from "react";
import { HealthStatus } from "./components/HealthStatus";
import { LoginButton } from "./components/LoginButton";
import { QueryBox } from "./components/QueryBox";

function App() {
  const [query, setQuery] = useState("");

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
        </section>

        <section className="panel">
          <h2>Respuesta</h2>
          <div className="response-placeholder">
            Aqui se mostrara la respuesta del copiloto.
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
