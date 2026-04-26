import json
import os
import time
from datetime import datetime, timezone

import requests


API_BASE_URL = os.getenv(
    "EVAL_API_BASE_URL",
    "https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io",
)

TOKEN = os.getenv("TEST_JWT_TOKEN")

QUESTIONS = [
    {
        "id": "q1",
        "question": "Según el documento Demo RAG Entregable 3.3, ¿qué building blocks se recomiendan para la apertura digital de tarjeta de crédito?",
        "expected_keywords": ["autenticación", "elegibilidad", "riesgo", "emisión", "notificaciones"],
    },
    {
        "id": "q2",
        "question": "¿Qué dominios BIAN podrían alinearse con una apertura digital de tarjeta de crédito?",
        "expected_keywords": ["Party Authentication", "Customer", "Credit", "Card"],
    },
    {
        "id": "q3",
        "question": "¿Qué fuentes utiliza el copiloto para sustentar sus recomendaciones?",
        "expected_keywords": ["fuentes", "documento", "contexto"],
    },
    {
        "id": "q4",
        "question": "¿Qué recomendaciones arquitectónicas aplican para un caso de onboarding digital?",
        "expected_keywords": ["recomendaciones", "arquitectónicas", "building blocks"],
    },
    {
        "id": "q5",
        "question": "¿Qué lineamientos debería considerar una solución de arquitectura para reutilizar capacidades existentes?",
        "expected_keywords": ["reutilizar", "capacidades", "arquitectura"],
    },
]


def score_answer_relevancy(answer: str, expected_keywords: list[str]) -> float:
    answer_lower = answer.lower()
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in answer_lower)
    return round(hits / len(expected_keywords), 2)


def score_context_precision(sources: list[dict]) -> float:
    if not sources:
        return 0.0

    valid_sources = [
        source
        for source in sources
        if source.get("title") or source.get("source_id") or source.get("document_id")
    ]
    return round(len(valid_sources) / len(sources), 2)


def score_faithfulness(answer: str, sources: list[dict]) -> float:
    if not answer or not sources:
        return 0.0

    answer_lower = answer.lower()
    weak_phrases = [
        "no cuento con suficiente contexto",
        "no tengo información",
        "no se encontraron fuentes",
    ]

    if any(phrase in answer_lower for phrase in weak_phrases):
        return 0.5

    return 1.0


def post_with_retries(item: dict) -> requests.Response:
    last_error = None

    for attempt in range(1, 4):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/query",
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": item["question"],
                    "stream": False,
                },
                timeout=90,
            )

            if response.status_code in (429, 500, 502, 503, 504):
                print(
                    f"Intento {attempt}/3 para {item['id']} devolvió "
                    f"HTTP {response.status_code}. Reintentando..."
                )
                time.sleep(5 * attempt)
                continue

            return response

        except requests.exceptions.RequestException as exc:
            last_error = exc
            print(f"Intento {attempt}/3 para {item['id']} falló por conexión: {exc}")
            time.sleep(5 * attempt)

    raise RuntimeError(
        f"No se pudo evaluar {item['id']} después de 3 intentos."
    ) from last_error


def evaluate_question(item: dict) -> dict:
    started_at = time.perf_counter()
    response = post_with_retries(item)
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    response.raise_for_status()
    data = response.json()

    answer = data.get("answer", "")
    sources = data.get("sources", [])

    return {
        "id": item["id"],
        "question": item["question"],
        "answer_preview": answer[:300],
        "sources_count": len(sources),
        "latency_ms": latency_ms,
        "trace_id": data.get("trace_id"),
        "scores": {
            "faithfulness": score_faithfulness(answer, sources),
            "answer_relevancy": score_answer_relevancy(answer, item["expected_keywords"]),
            "context_precision": score_context_precision(sources),
        },
    }


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def main() -> None:
    if not TOKEN:
        raise RuntimeError(
            "Falta TEST_JWT_TOKEN. Obtén un JWT válido desde el frontend autenticado."
        )

    results = []

    for item in QUESTIONS:
        print(f"Evaluando {item['id']}...")
        result = evaluate_question(item)
        results.append(result)

        # Pausa para evitar saturar el backend/LLM y reducir cortes transitorios.
        time.sleep(3)

    faithfulness = average([r["scores"]["faithfulness"] for r in results])
    answer_relevancy = average([r["scores"]["answer_relevancy"] for r in results])
    context_precision = average([r["scores"]["context_precision"] for r in results])

    report = {
        "evaluation_type": "manual_structured_rag_evaluation",
        "note": (
            "Evaluación estructurada del pipeline RAG ejecutada contra el backend cloud. "
            "Las métricas se calculan con criterios determinísticos basados en presencia de fuentes, "
            "relevancia por keywords esperadas y consistencia básica de respuesta."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base_url": API_BASE_URL,
        "dataset_size": len(results),
        "metrics": {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
        },
        "thresholds": {
            "faithfulness": 0.75,
            "answer_relevancy": 0.70,
            "context_precision": 0.70,
        },
        "passed": {
            "faithfulness": faithfulness >= 0.75,
            "answer_relevancy": answer_relevancy >= 0.70,
            "context_precision": context_precision >= 0.70,
        },
        "results": results,
    }

    os.makedirs("reports", exist_ok=True)

    with open("reports/ragas_report.json", "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print("Reporte generado en reports/ragas_report.json")


if __name__ == "__main__":
    main()