import os
import requests

BASE_URL = os.getenv(
    "E2E_API_BASE_URL",
    "https://agc-api-mvp.graycoast-cbfe8a60.centralus.azurecontainerapps.io",
)

def test_health_cloud_returns_status():
    response = requests.get(f"{BASE_URL}/api/v1/health", timeout=30)

    assert response.status_code == 200

    data = response.json()
    assert data.get("status") in ["healthy", "degraded"]
    assert "components" in data