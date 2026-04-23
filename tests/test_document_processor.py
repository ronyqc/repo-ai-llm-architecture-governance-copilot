from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from apps.document_processor_function.processing.document_processor import (
    chunk_text,
    clean_text,
    process_normalized_document,
    recursive_split,
)


class DocumentProcessorChunkingTests(unittest.TestCase):
    def test_clean_text_normalizes_whitespace_and_control_characters(self) -> None:
        cleaned = clean_text("Line 1\r\n\r\n\x00Line\t\t2\u00a0 ")

        self.assertEqual(cleaned, "Line 1\n\nLine 2")

    def test_recursive_split_falls_back_to_character_boundaries_for_long_tokens(self) -> None:
        fragments = recursive_split("A" * 2200)

        self.assertGreaterEqual(len(fragments), 3)
        self.assertTrue(all(len(fragment) <= 1000 for fragment in fragments))

    def test_chunk_text_rejects_invalid_size_and_overlap_values(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("content", chunk_size=0)
        with self.assertRaises(ValueError):
            chunk_text("content", chunk_size=10, overlap=-1)
        with self.assertRaises(ValueError):
            chunk_text("content", chunk_size=10, overlap=10)

    def test_chunk_text_preserves_overlap_across_fragments(self) -> None:
        text = ("A" * 40) + "\n\n" + ("B" * 40) + "\n\n" + ("C" * 40)

        chunks = chunk_text(text, chunk_size=70, overlap=10)

        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[1].startswith("AAAAAAAAAA"))
        self.assertTrue(chunks[2].startswith("BBBBBBBBBB"))

    def test_process_normalized_document_builds_chunk_records_with_metadata(self) -> None:
        normalized_document = {
            "title": "Architecture Guide",
            "knowledge_domain": "guidelines_patterns",
            "source_type": "markdown_curated",
            "document_name": "guide.md",
            "source_url": "blob://documents/guide.md",
            "metadata": json.dumps({"section": "intro"}),
            "content": "A" * 1200,
        }

        with patch(
            "apps.document_processor_function.processing.document_processor.uuid.uuid4",
            side_effect=["chunk-1", "chunk-2"],
        ):
            records = process_normalized_document(normalized_document)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["id"], "chunk-1")
        self.assertEqual(records[0]["chunk_id"], "guide.md#chunk-1")
        self.assertEqual(records[0]["knowledge_domain"], "guidelines_patterns")
        self.assertEqual(records[0]["metadata"], normalized_document["metadata"])
        self.assertTrue(records[0]["updated_at"].endswith("Z"))

    def test_process_normalized_document_rejects_missing_required_fields(self) -> None:
        with self.assertRaises(ValueError) as context:
            process_normalized_document(
                {
                    "title": "Architecture Guide",
                    "knowledge_domain": "guidelines_patterns",
                    "source_type": "markdown_curated",
                    "content": "body",
                }
            )

        self.assertIn("missing required fields", str(context.exception))


if __name__ == "__main__":
    unittest.main()
