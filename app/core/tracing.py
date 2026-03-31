from contextvars import ContextVar
from typing import Any

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def setup_tracing(app: Any = None, engine: Any = None) -> None:
    pass


def get_tracer(name: str) -> Any:
    class NoOpTracer:
        def __getattr__(self, item):
            return lambda *args, **kwargs: None
    return NoOpTracer()


def generate_trace_id() -> str:
    import uuid
    return str(uuid.uuid4())
