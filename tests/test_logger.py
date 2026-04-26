from __future__ import annotations

import io
import logging
import unittest

from src.utils.logger import STRUCTURED_LOG_ATTR, StructuredLogFormatter, get_logger, log_event


class StructuredLoggerTests(unittest.TestCase):
    def test_formatter_appends_sorted_json_event_data(self) -> None:
        formatter = StructuredLogFormatter("%(levelname)s | %(message)s")
        record = logging.LogRecord(
            name="agc.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="query.request.completed",
            args=(),
            exc_info=None,
        )
        setattr(record, STRUCTURED_LOG_ATTR, {"zeta": 2, "alpha": "one"})

        formatted = formatter.format(record)

        self.assertIn("INFO | query.request.completed", formatted)
        self.assertIn('{"alpha": "one", "zeta": 2}', formatted)

    def test_get_logger_reuses_handler_without_duplication(self) -> None:
        logger_name = "tests.logger.reuse"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()

        first = get_logger(logger_name)
        second = get_logger(logger_name)

        self.assertIs(first, second)
        self.assertEqual(len(second.handlers), 1)
        self.assertFalse(second.propagate)

    def test_log_event_omits_empty_fields_and_writes_structured_payload(self) -> None:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredLogFormatter("%(message)s"))
        logger = logging.getLogger("tests.logger.event")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        log_event(
            logger,
            logging.INFO,
            "upload_url.sas.generated",
            user_id="admin-user",
            blob_name="guide.pdf",
            empty_value="",
            none_value=None,
        )

        output = stream.getvalue()
        self.assertIn("upload_url.sas.generated", output)
        self.assertIn('"user_id": "admin-user"', output)
        self.assertIn('"blob_name": "guide.pdf"', output)
        self.assertNotIn("empty_value", output)
        self.assertNotIn("none_value", output)


if __name__ == "__main__":
    unittest.main()
