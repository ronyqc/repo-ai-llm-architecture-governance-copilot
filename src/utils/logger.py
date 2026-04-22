import json
import logging
from collections.abc import Mapping
from typing import Any

from src.core.config import settings


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
STRUCTURED_LOG_ATTR = "event_data"


class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        event_data = getattr(record, STRUCTURED_LOG_ATTR, None)
        if not isinstance(event_data, Mapping) or not event_data:
            return message
        serialized = json.dumps(
            event_data,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return f"{message} | {serialized}"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter(LOG_FORMAT))
        logger.addHandler(handler)
    else:
        for handler in logger.handlers:
            handler.setFormatter(StructuredLogFormatter(LOG_FORMAT))

    logger.setLevel(settings.LOG_LEVEL.upper())
    logger.propagate = False

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    event_data = {
        key: value
        for key, value in fields.items()
        if value is not None and value != ""
    }
    logger.log(
        level,
        event,
        extra={STRUCTURED_LOG_ATTR: event_data},
        exc_info=exc_info,
    )
