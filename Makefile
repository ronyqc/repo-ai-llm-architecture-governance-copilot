# ==============================================================
# Makefile — Architecture Governance Copilot
# ==============================================================

PYTHON := python
PIP := pip
TEST_DIR := tests
REPORTS_DIR := reports
COV_MINIMUM := 60
IMAGE_NAME := agc-api
IMAGE_TAG := latest

.PHONY: help install dev stop test test-unit test-integration test-load evaluate build clean check-files ci-check pre-delivery

help: ## Muestra los comandos disponibles
	@echo ""
	@echo "Architecture Governance Copilot — comandos disponibles"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'
	@echo ""

install: ## Instala dependencias Python y prepara carpetas mínimas
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt
	@mkdir -p $(REPORTS_DIR)
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env creado desde .env.example"; else echo ".env ya existe"; fi

dev: ## Levanta el backend local con Docker Compose
	docker compose up --build

stop: ## Detiene el entorno local
	docker compose down

test: ## Ejecuta pruebas con coverage mínimo del 60%
	@mkdir -p $(REPORTS_DIR)
	pytest $(TEST_DIR) \
		--ignore=tests/scripts \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=xml:$(REPORTS_DIR)/coverage.xml \
		--cov-fail-under=$(COV_MINIMUM)

test-unit: ## Ejecuta solo pruebas unitarias
	pytest tests/unit -v

test-integration: ## Ejecuta pruebas de integración
	pytest tests/integration -v

test-load: ## Ejecuta prueba de carga k6 de /query
	k6 run --out json=$(REPORTS_DIR)/load_test_results.json tests/load/load_test.js

evaluate: ## Ejecuta evaluación estructurada LLM/RAG y genera ragas_report.json
	$(PYTHON) scripts/evaluate_llm_quality.py

build: ## Construye la imagen Docker del backend
	@command -v docker >/dev/null 2>&1 || (echo "Docker no está disponible en esta terminal. Abre Docker Desktop o ejecuta este comando desde PowerShell/Git Bash con Docker en PATH." && exit 1)
	docker build --target runtime -t $(IMAGE_NAME):$(IMAGE_TAG) .

clean: ## Limpia cachés y archivos temporales locales
	@rm -rf .pytest_cache htmlcov __pycache__ .coverage
	@echo "Limpieza completada"

check-files: ## Verifica archivos mínimos esperados para la entrega final
	@test -f README.md || (echo "Falta README.md" && exit 1)
	@test -f REQUIRED_FILES.md || (echo "Falta REQUIRED_FILES.md" && exit 1)
	@test -f .env.example || (echo "Falta .env.example" && exit 1)
	@test -f .gitignore || (echo "Falta .gitignore" && exit 1)
	@test -f Makefile || (echo "Falta Makefile" && exit 1)
	@test -f Dockerfile || (echo "Falta Dockerfile" && exit 1)
	@test -f docker-compose.yml || (echo "Falta docker-compose.yml" && exit 1)
	@test -f requirements.txt || (echo "Falta requirements.txt" && exit 1)
	@test -f .github/workflows/ci.yml || (echo "Falta .github/workflows/ci.yml" && exit 1)
	@test -f src/api/main.py || (echo "Falta src/api/main.py" && exit 1)
	@test -f src/api/routes.py || (echo "Falta src/api/routes.py" && exit 1)
	@test -d src/core || (echo "Falta src/core" && exit 1)
	@test -d src/rag || (echo "Falta src/rag" && exit 1)
	@test -d src/security || (echo "Falta src/security" && exit 1)
	@test -d apps/document_processor_function || (echo "Falta Azure Function de ingesta" && exit 1)
	@test -d frontend || (echo "Falta frontend" && exit 1)
	@test -d tests || (echo "Falta carpeta tests" && exit 1)
	@test -d tests/integration || (echo "Falta tests/integration" && exit 1)
	@test -d tests/load || (echo "Falta tests/load" && exit 1)
	@test -f reports/coverage.xml || (echo "Falta reports/coverage.xml" && exit 1)
	@test -f reports/ragas_report.json || (echo "Falta reports/ragas_report.json" && exit 1)
	@test -f reports/load_test_results.json || (echo "Falta reports/load_test_results.json" && exit 1)
	@test -f reports/load_test_summary.md || (echo "Falta reports/load_test_summary.md" && exit 1)
	@echo "Archivos mínimos de entrega final presentes"

ci-check: ## Verifica archivos de CI/CD esperados
	@test -f .github/workflows/ci.yml || (echo "Falta workflow CI principal" && exit 1)
	@echo "Workflow CI/CD presente. Verificar estado verde en GitHub Actions antes de la entrega."

pre-delivery: check-files test ci-check ## Ejecuta validaciones principales antes de la entrega final
	@echo "Nota: ejecutar 'make build' o 'docker build --target runtime -t agc-api:latest .' en una terminal con Docker disponible."
	@echo "✓ Proyecto listo para entrega final"