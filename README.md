# Architecture Governance Copilot

Copiloto de arquitectura basado en AI/LLM y RAG para apoyar la revisión conceptual de soluciones en una organización financiera. El sistema permite consultar conocimiento arquitectónico indexado, recuperar fuentes relevantes y generar recomendaciones sobre building blocks, lineamientos y posibles alineamientos BIAN.

## Arquitectura

La solución se compone de un frontend en Azure Static Web Apps, un backend FastAPI desplegado en Azure Container Apps, autenticación con Microsoft Entra ID mediante JWT, Azure OpenAI para generación de respuestas y embeddings, Azure AI Search como vector store, Azure Blob Storage para documentos fuente y Azure Functions para el procesamiento de ingesta documental.

## URLs de despliegue

### Frontend

https://icy-pond-021121e0f.7.azurestaticapps.net

### Backend API

https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io

### Swagger / OpenAPI

https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io/docs

## Endpoints principales

| Método | Endpoint | Descripción | Seguridad |
|---|---|---|---|
| GET | `/api/v1/health` | Estado del backend y dependencias | Público |
| POST | `/api/v1/query` | Ejecuta consulta RAG y retorna respuesta con fuentes | JWT |
| POST | `/api/v1/ingest` | Registra o dispara ingesta de documentos | JWT admin |
| POST | `/api/v1/upload-url` | Genera URL SAS para carga de archivo a Blob Storage | JWT admin |

## Validación rápida en cloud

### Health

```bash
curl https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io/api/v1/health
Respuesta esperada:

{
  "status": "healthy",
  "components": {
    "backend": "healthy",
    "azure_openai": "healthy",
    "azure_ai_search": "healthy",
    "confluence": "healthy"
  }
}

Flujo funcional validado

El sistema desplegado permite ejecutar el siguiente flujo end-to-end:

Acceso al frontend publicado en Azure Static Web Apps.
Autenticación del usuario mediante Microsoft Entra ID.
Generación de URL SAS mediante /api/v1/upload-url.
Carga de documento al contenedor raw-corpus en Azure Blob Storage.
Registro de ingesta mediante /api/v1/ingest.
Procesamiento del documento mediante Azure Functions.
Generación de chunks, embeddings e indexación en Azure AI Search.
Consulta mediante /api/v1/query.
Recuperación de respuesta generada con fuentes del documento indexado.


Requisitos para ejecución local
Python 3.11+
Docker y Docker Compose
Node.js 20+ para frontend local
Cuenta de Azure con acceso a:
Azure OpenAI
Azure AI Search
Azure Storage Account
Azure Functions
Azure Container Apps
Azure Static Web Apps
Microsoft Entra ID
Archivo .env creado a partir de .env.example con las variables reales del entorno.


Instalación local
git clone https://github.com/ronyqc/repo-ai-llm-architecture-governance-copilot.git
cd repo-ai-llm-architecture-governance-copilot
cp .env.example .env

Editar .env con los valores reales de Azure OpenAI, Azure AI Search, Azure Storage, Confluence y Microsoft Entra ID.

Ejecución local del backend
docker compose build
docker compose up

Validar health local:
curl http://localhost:8000/api/v1/health

Ejecución local del frontend
cd frontend
npm install
npm run dev

Abrir:
http://localhost:5173

Pruebas
make test

Verificación de archivos obligatorios
make check-files

Video demo
Pendiente de incorporar en E4.

Participantes
Rony Lexter Quiroz Castillo
José Luis Rodríguez Prieto

Curso
Proyecto Final — AI/LLM Solution Architect