import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from app.config import settings

request_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_id", default=None
)

_RESERVED_LOG_RECORD_FIELDS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        record.user_id = user_id_ctx_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    @staticmethod
    def _to_jsonable(value: Any):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): _JsonFormatter._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_JsonFormatter._to_jsonable(item) for item in value]
        return str(value)

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.request_id:
            payload["request_id"] = record.request_id
        if record.user_id:
            payload["user_id"] = record.user_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Keep custom extra fields (request, audit, domain context).
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS:
                continue
            if key.startswith("_"):
                continue
            if key in payload:
                continue
            payload[key] = self._to_jsonable(value)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    if root.handlers:
        root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    if settings.log_json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s user_id=%(user_id)s] %(message)s"
            )
        )
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)


def init_sentry() -> None:
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except Exception:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN is configured but sentry-sdk is not installed"
        )
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        environment=settings.app_env,
        release=os.getenv("APP_RELEASE"),
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    )
    logging.getLogger(__name__).info("Sentry initialized")
