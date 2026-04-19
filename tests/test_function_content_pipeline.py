from __future__ import annotations

from pathlib import Path
import sys
import unittest


APP_DIR = Path.cwd() / "apps" / "document_processor_function"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import function_app  # type: ignore  # noqa: E402


class FunctionContentPipelineTests(unittest.TestCase):
    def test_http_source_type_prefers_inferred_pdf_type(self) -> None:
        self.assertEqual(
            function_app._resolve_http_source_type(
                requested_source_type="plain_text",
                inferred_source_type="pdf_document",
            ),
            "pdf_document",
        )

    def test_infers_pdf_source_type_from_blob_name(self) -> None:
        self.assertEqual(
            function_app._infer_source_type_from_blob_name("raw/manuals/guide.pdf"),
            "pdf_document",
        )

    def test_infers_docx_source_type_from_blob_name(self) -> None:
        self.assertEqual(
            function_app._infer_source_type_from_blob_name("raw/manuals/guide.docx"),
            "docx_document",
        )

    def test_resolve_blob_source_metadata_keeps_html_compatibility(self) -> None:
        knowledge_domain, source_type = function_app._resolve_blob_source_metadata(
            blob_name="guidelines/guide.html",
            raw_content="<html><body>Architecture</body></html>",
            inferred_source_type="html_page",
        )

        self.assertEqual(knowledge_domain, "guidelines_patterns")
        self.assertEqual(source_type, "html_page")


if __name__ == "__main__":
    unittest.main()
