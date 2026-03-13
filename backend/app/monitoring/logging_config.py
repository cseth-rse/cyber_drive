# app/monitoring/logging_config.py
"""
Structured JSON logging for production.
In development (APP_ENV != production), falls back to readable colored output.

Usage (in main.py):
    from app.monitoring.logging_config import configure_logging
    configure_logging(settings)
"""
import logging
import sys


class _JSONFormatter(logging.Formatter):
    """Minimal JSON log formatter — no external dependency."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Include extra fields attached via logger.info("msg", extra={...})
        for key in ("request_id", "user_id", "doc_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging(settings) -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.app_env == "development" else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if settings.app_env == "production":
        handler.setFormatter(_JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
                              datefmt="%H:%M:%S")
        )

    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
