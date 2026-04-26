# REQUIRED_FILES.md

## 4.8 Checklist de entrega final — Verificación de artefactos

Este documento valida que el proyecto cumple con todos los artefactos requeridos según el checklist maestro de entrega final.

---

## 1. Repositorio Git

| Elemento | Estado | Observación |
|----------|--------|------------|
| Repositorio GitHub | ✔ | Proyecto versionado correctamente |
| Rama principal (main) | ✔ | Lista para entrega final |
| Rama develop | ✔ | Integración de cambios |
| Historial de commits | ✔ | Evidencia de evolución del proyecto |
| Pull Requests (PR) | ✔ | Flujo de integración aplicado |
| Tag de versión | ✔ | Se creó en 4.6 (`v1.0.0`) |

---

## 2. Código del sistema

| Elemento | Estado | Observación |
|----------|--------|------------|
| Backend (FastAPI) | ✔ | Endpoints `/health`, `/query`, `/ingest` |
| Orquestador LLM | ✔ | Implementado |
| Integración Azure OpenAI | ✔ | Generación de respuestas |
| Integración Azure AI Search | ✔ | Vector DB funcionando |
| Pipeline de ingesta | ✔ | Azure Function + Blob Trigger |
| Seguridad JWT | ✔ | Validación con Entra ID |
| Frontend | ✔ | Aplicación desplegada |
| Dockerfile | ✔ | Contenedor funcional |
| docker-compose | ✔ | Entorno local disponible |

---

## 3. Pruebas

| Tipo de prueba | Estado | Evidencia |
|---------------|--------|----------|
| Pruebas unitarias | ✔ | `tests/` |
| Pruebas de integración | ✔ | `tests/integration/` |
| Pruebas de carga | ✔ | `tests/load/load_test.js` |
| Cobertura | ✔ | `reports/coverage.xml` (>60%) |
| Evaluación LLM | ✔ | `reports/ragas_report.json` |
| Resultados de carga | ✔ | `reports/load_test_results.json` |

---

## 4. Documentación

| Documento | Estado | Observación |
|----------|--------|------------|
| README.md | ✔ | Instrucciones y descripción del sistema |
| Variables de entorno | ✔ | Documentadas |
| Arquitectura | ✔ | Diagramas incluidos |
| Resultados de pruebas | ✔ | Sección 7.2 y 7.3 |
| Costos | ✔ | Se completó en 4.3 |
| Observabilidad | ✔ | Se completó en sección 9 |
| Conclusiones | ✔ | Se completó en sección 10 |

---

## 5. Automatización

| Elemento | Estado | Observación |
|----------|--------|------------|
| Makefile | ✔ | Comandos documentados (`install`, `test`, `check-files`) |
| GitHub Actions | ✔ | Pipeline CI/CD en verde |
| Docker build | ✔ | Validado en CI |

---

## 6. Archivos requeridos

| Archivo | Estado |
|--------|--------|
| README.md | ✔ |
| .env.example | ✔ |
| .gitignore | ✔ |
| Makefile | ✔ |
| Dockerfile | ✔ |
| docker-compose.yml | ✔ |
| requirements.txt | ✔ |
| workflows CI/CD | ✔ |

---

## 7. Seguridad

| Validación | Estado |
|-----------|--------|
| No hay secretos en repo | ✔ |
| Uso de `.env.example` | ✔ |
| JWT protegido | ✔ |

---

## 8. Entrega final (según checklist del profesor)

| Elemento | Estado | Observación |
|----------|--------|------------|
| Código funcional | ✔ | MVP completo |
| Pruebas ejecutadas | ✔ | Evidencias incluidas |
| Documentación completa | ✔ |
| Video de demo | ✔ |
| Tag de versión | ✔ |
| Validación final | ✔ |

---

## 9. Comandos de validación

Antes de la entrega final se recomienda ejecutar:
make check-files
make test
make pre-delivery

---

## 10. Conclusión

El proyecto cumple con los artefactos requeridos para la entrega final.