# Architecture Governance Copilot

Copiloto de arquitectura basado en AI/LLM y RAG para apoyar la revisión conceptual de soluciones en una organización financiera. El sistema permite consultar conocimiento arquitectónico indexado, recuperar fuentes relevantes y generar recomendaciones sobre building blocks, lineamientos y posibles alineamientos BIAN.

---

## Arquitectura

La solución se compone de:

- Frontend: Azure Static Web Apps  
- Backend: FastAPI desplegado en Azure Container Apps  
- Autenticación: Microsoft Entra ID (JWT)  
- LLM: Azure OpenAI  
- Vector Store: Azure AI Search  
- Ingesta: Azure Blob Storage + Azure Functions  

---

## URLs de despliegue

### Frontend
https://icy-pond-021121e0f.7.azurestaticapps.net  

### Backend API
https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io  

### Swagger / OpenAPI
https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io/docs  

---

## Validación rápida (menos de 5 minutos)

### Verificar estado del sistema

```bash
curl https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io/api/v1/health
```

Respuesta esperada:

```json
{
  "status": "healthy",
  "components": {
    "backend": "healthy",
    "azure_openai": "healthy",
    "azure_ai_search": "healthy"
  }
}
```

### Probar desde el frontend

1. Acceder al frontend  
2. Autenticarse con Microsoft Entra ID  
3. Ejecutar una consulta  
4. Ver respuesta con fuentes  

---

## Flujo funcional validado

- Autenticación del usuario  
- Generación de URL SAS  
- Carga de documento a Blob Storage  
- Ingesta mediante endpoint `/ingest`  
- Procesamiento con Azure Functions  
- Generación de embeddings  
- Indexación en Azure AI Search  
- Consulta mediante `/query`  
- Respuesta con fuentes  

---

## Resultados reales del sistema

### Calidad del LLM (RAG)

| Métrica | Resultado |
|--------|----------|
| Faithfulness | 0.80 |
| Answer Relevancy | 0.80 |
| Context Precision | 0.80 |

### Pruebas de carga

| Métrica | Resultado |
|--------|----------|
| Latencia p95 | 6.3 s |
| Tasa de error | 86% |
| Error principal | HTTP 429 |

### Cobertura de pruebas

- Coverage: 83.18%  
- Tests: 119 passed / 1 skipped  

---

## Ejecución local

### Requisitos

- Python 3.11+  
- Docker  
- Node.js 20+  
- Cuenta Azure  

### Backend

```bash
git clone https://github.com/ronyqc/repo-ai-llm-architecture-governance-copilot.git
cd repo-ai-llm-architecture-governance-copilot
cp .env.example .env
docker compose up --build
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir:

http://localhost:5173

---

## Pruebas

```bash
make test
```

---

## Validación final

```bash
make pre-delivery
```

---

## Consideraciones de seguridad

- No se incluyen credenciales reales en el repositorio  
- Uso de `.env.example` como plantilla  
- Autenticación mediante JWT (Microsoft Entra ID)  

---

## Modo recomendado de evaluación

Se recomienda utilizar el entorno cloud desplegado, ya que la ejecución local completa requiere credenciales y recursos Azure previamente configurados.

---

## Video demo

Pendiente de incorporación en Entregable 4.

---

## Equipo

- Rony Lexter Quiroz Castillo  
- José Luis Rodríguez Prieto  

---

## Curso

Proyecto Final — AI/LLM Solution Architect