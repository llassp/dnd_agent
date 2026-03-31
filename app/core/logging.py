import structlog
import logging
import sys
from contextvars import ContextVar
from typing import Any

from app.core.config import get_settings

settings = get_settings()

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def add_trace_id(_, __: Any, event_dict: Any) -> Any:
    trace_id = trace_id_var.get()
    if trace_id:
        event_dict["trace_id"] = trace_id
    return event_dict


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_trace_id,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
