import os

import pytest
import requests


BASE_URL = os.getenv(
    "E2E_API_BASE_URL",
    "https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io",
)


@pytest.mark.skipif(
    not os.getenv("TEST_JWT_TOKEN"),
    reason="Requiere TEST_JWT_TOKEN válido para ejecutar prueba RAG cloud.",
)
def test_rag_query_cloud_returns_answer_and_sources():
    """
    E3-3.7: Prueba de integración end-to-end del pipeline RAG.

    Requiere un JWT válido obtenido desde el frontend autenticado con Microsoft Entra ID.
    En CI/CD se omite automáticamente si TEST_JWT_TOKEN no está configurado.
    """

    token = os.getenv("TEST_JWT_TOKEN")

    response = requests.post(
        f"{BASE_URL}/api/v1/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "query": (
                "Según el documento Demo RAG Entregable 3.3, "
                "¿qué building blocks se recomiendan para la apertura digital de tarjeta de crédito?"
            ),
            "stream": False,
        },
        timeout=60,
    )

    assert response.status_code == 200

    data = response.json()

    assert data.get("answer")
    assert isinstance(data.get("sources"), list)
    assert len(data["sources"]) >= 1
    assert data.get("trace_id")