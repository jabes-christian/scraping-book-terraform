import json
import logging
import sys
from collections.abc import Iterable
from datetime import UTC, datetime

MASK = "***"


def redact(text: str, secrets: Iterable[str]) -> str:
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            text = text.replace(secret, MASK)
    return text


class _JsonFormatter(logging.Formatter):
    def __init__(self, secrets: Iterable[str]):
        super().__init__()
        self._secrets = list(secrets)

    def format(self, record: logging.LogRecord) -> str:
        event = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "message": redact(record.getMessage(), self._secrets),
        }
        if record.exc_info:
            event["exception"] = redact(self.formatException(record.exc_info), self._secrets)
        return json.dumps(event, ensure_ascii=False)


def configure(level: str, secrets: Iterable[str]) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter(secrets))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
