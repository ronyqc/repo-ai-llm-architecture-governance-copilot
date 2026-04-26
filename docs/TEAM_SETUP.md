# Guía rápida de trabajo en equipo

## 1. Estrategia de ramas
- `main`: rama estable
- `develop`: rama de integración
- `feat/*`: nuevas funcionalidades
- `fix/*`: correcciones
- `docs/*`: documentación
- `chore/*`: ajustes técnicos o mantenimiento

## 2. Flujo de trabajo
1. Siempre partir desde `develop`
2. Crear una rama propia
3. Trabajar solo en esa rama
4. Hacer push de la rama al repositorio
5. Abrir Pull Request hacia `develop`
6. Pedir revisión antes de mergear
7. Solo pasar a `main` lo que ya esté validado

## 3. Convención de nombres de ramas
Ejemplos:
- `feat/backend-base`
- `feat/frontend-shell`
- `feat/blob-storage-setup`
- `feat/adf-pipeline-base`
- `fix/health-endpoint`
- `docs/readme-setup`
- `chore/ci-adjustments`

## 4. Convención de commits
Usar Conventional Commits:

- `feat(scope): descripción`
- `fix(scope): descripción`
- `docs(scope): descripción`
- `test(scope): descripción`
- `chore(scope): descripción`

Ejemplos:
- `feat(api): add backend base structure`
- `feat(frontend): add initial app shell`
- `feat(storage): add blob setup notes`
- `chore(ci): adjust github actions workflow`
- `docs(readme): add local setup steps`

## 5. Distribución inicial de trabajo

### Rony
- Backend FastAPI
- `src/api`
- `src/core`
- `src/rag`
- `src/security`
- Contrato de `/query`
- Contrato de `/ingest`
- Esquema lógico del índice en Azure AI Search
- Estrategia de chunking y metadata
- Azure AI Search
- Azure OpenAI
- Azure Table Storage o mecanismo de contexto
- Observabilidad mínima
- Azure Function de procesamiento documental
- Retriever y orquestación del backend

### José Luis
- Frontend
- Integración frontend con `/health` y luego `/query`
- Autenticación frontend con Entra ID
- Manejo de token hacia backend
- Formato estándar de documentos fuente
- Curación de fuentes BIAN
- Building blocks iniciales
- Buenas prácticas / lineamientos iniciales
- Azure Blob Storage
- Azure Data Factory
- Validación de calidad de retrieval y respuesta

### Compartido
- `README.md`
- `docs/`
- `docs/api/openapi.yaml`
- contrato visual de fuentes
- pruebas end-to-end
- validación final del MVP

## 6. Reglas básicas
- No hacer push directo a `main`
- No subir secretos ni archivo `.env`
- No cambiar la estructura principal del repo sin avisar
- Mantener commits pequeños y descriptivos
- Abrir PR con una descripción clara de lo cambiado

## 7. Checklist mínimo para un Pull Request
- ¿Qué cambió?
- ¿Por qué se hizo?
- ¿Agrega o cambia variables de entorno?
- ¿Impacta documentación?
- ¿Tiene evidencia o captura si aplica?