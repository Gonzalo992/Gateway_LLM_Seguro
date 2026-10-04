import json
import logging
import re
from datetime import datetime, timezone


SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(api[_-]?key[\"'=:\s]+)[^\s,}\"]+"),
    re.compile(r"(?i)(x-gateway-key[\"'=:\s]+)[^\s,}\"]+"),
]


def redact_text(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r"\1[REDACTED]", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }

        fields = [
            "request_id",
            "endpoint",
            "method",
            "status_code",
            "latency_ms",
            "client_id",
            "provider",
            "model",
            "security_event",
        ]

        for field in fields:
            if hasattr(record, field):
                data[field] = getattr(record, field)

        return redact_text(json.dumps(data, ensure_ascii=False, default=str))


def configure_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("llm_gateway")
    logger.setLevel(level.upper())
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger
