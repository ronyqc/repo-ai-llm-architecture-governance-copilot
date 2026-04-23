from __future__ import annotations

import unittest

from src.core.llm_client import (
    AzureOpenAILLMConfigurationError,
    _ensure_https_url as ensure_openai_https_url,
)
from src.rag.vector_store import (
    AzureSearchConfigurationError,
    _ensure_https_url as ensure_search_https_url,
)


class SecurityReviewTests(unittest.TestCase):
    def test_openai_health_check_requires_https_url(self) -> None:
        with self.assertRaises(AzureOpenAILLMConfigurationError):
            ensure_openai_https_url("http://example.test/openai/deployments/x")

    def test_search_health_check_requires_https_url(self) -> None:
        with self.assertRaises(AzureSearchConfigurationError):
            ensure_search_https_url("file:///tmp/index")


if __name__ == "__main__":
    unittest.main()
