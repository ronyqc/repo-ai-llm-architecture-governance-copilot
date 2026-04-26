from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import get_health_service
from src.core.health import SystemHealthService


def _healthy(_: float) -> None:
    return None


def _failing(_: float) -> None:
    raise RuntimeError("dependency failed")


class SystemHealthServiceTests(unittest.TestCase):
    def test_health_is_healthy_when_all_dependencies_respond(self) -> None:
        service = SystemHealthService(
            timeout_seconds=0.05,
            azure_openai_check=_healthy,
            azure_search_check=_healthy,
            confluence_check=_healthy,
        )

        report = service.check()

        self.assertEqual(report.status, "healthy")
        self.assertEqual(report.components["backend"], "healthy")
        self.assertEqual(report.components["azure_openai"], "healthy")
        self.assertEqual(report.components["azure_ai_search"], "healthy")
        self.assertEqual(report.components["confluence"], "healthy")
        self.assertTrue(report.timestamp)

    def test_health_is_degraded_when_azure_openai_fails(self) -> None:
        service = SystemHealthService(
            timeout_seconds=0.05,
            azure_openai_check=_failing,
            azure_search_check=_healthy,
            confluence_check=_healthy,
        )

        report = service.check()

        self.assertEqual(report.status, "degraded")
        self.assertEqual(report.components["azure_openai"], "unhealthy")
        self.assertEqual(report.components["azure_ai_search"], "healthy")
        self.assertEqual(report.components["confluence"], "healthy")

    def test_health_is_degraded_when_azure_search_fails(self) -> None:
        service = SystemHealthService(
            timeout_seconds=0.05,
            azure_openai_check=_healthy,
            azure_search_check=_failing,
            confluence_check=_healthy,
        )

        report = service.check()

        self.assertEqual(report.status, "degraded")
        self.assertEqual(report.components["azure_openai"], "healthy")
        self.assertEqual(report.components["azure_ai_search"], "unhealthy")
        self.assertEqual(report.components["confluence"], "healthy")

    def test_health_is_degraded_when_confluence_fails(self) -> None:
        service = SystemHealthService(
            timeout_seconds=0.05,
            azure_openai_check=_healthy,
            azure_search_check=_healthy,
            confluence_check=_failing,
        )

        report = service.check()

        self.assertEqual(report.status, "degraded")
        self.assertEqual(report.components["azure_openai"], "healthy")
        self.assertEqual(report.components["azure_ai_search"], "healthy")
        self.assertEqual(report.components["confluence"], "unhealthy")


class HealthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_health_endpoint_responds_when_external_dependency_fails(self) -> None:
        health_service = SystemHealthService(
            timeout_seconds=0.05,
            azure_openai_check=_healthy,
            azure_search_check=_failing,
            confluence_check=_healthy,
        )
        app.dependency_overrides[get_health_service] = lambda: health_service

        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "degraded")
        self.assertEqual(body["components"]["backend"], "healthy")
        self.assertEqual(body["components"]["azure_openai"], "healthy")
        self.assertEqual(body["components"]["azure_ai_search"], "unhealthy")
        self.assertEqual(body["components"]["confluence"], "healthy")
        self.assertTrue(body["timestamp"])


if __name__ == "__main__":
    unittest.main()
