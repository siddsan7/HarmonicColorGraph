import time
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core import telemetry
from app.core.config import get_settings
from app.core.metrics import emit_metric


def _instrument_engine(engine: Engine) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def before(_conn, _cursor, statement, _parameters, context, _executemany):
        # Record the SQL verb only. SQL text, parameters and connection URLs can be sensitive.
        verb = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "UNKNOWN"
        operation = verb if verb in {"SELECT", "INSERT", "UPDATE", "DELETE"} else "OTHER"
        scope = telemetry.safe_span("db.query")
        span = scope.__enter__()
        span.set_attribute("db.system.name", engine.dialect.name)
        span.set_attribute("db.operation.name", operation)
        context._hcg_span = (scope, time.perf_counter(), operation)

    def finish(context, *, error: bool = False):
        active = getattr(context, "_hcg_span", None)
        if active is None:
            return
        context._hcg_span = None
        scope, started, operation = active
        elapsed_ms = (time.perf_counter() - started) * 1000
        emit_metric("db_query_latency_ms", elapsed_ms, operation=operation)
        if elapsed_ms >= 100:
            emit_metric("db_slow_query_count", 1, operation=operation)
        if error:
            emit_metric("db_query_error_count", 1, operation=operation)
        scope.__exit__(None, None, None)

    @event.listens_for(engine, "after_cursor_execute")
    def after(_conn, _cursor, _statement, _parameters, context, _executemany):
        finish(context)

    @event.listens_for(engine, "handle_error")
    def failed(exception_context):
        finish(exception_context.execution_context, error=True)


def get_database_url() -> str:
    return get_settings().database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
    engine_kwargs: dict = {}
    if url.startswith("postgresql"):
        # Serverless-safe: no pool to keep warm across invocations, no
        # server-side prepared statements (the transaction pooler doesn't
        # support them across pooled connections), hcg first on the search
        # path so unqualified table names resolve there, and a statement
        # timeout so one runaway query can't hang a request indefinitely.
        engine_kwargs["poolclass"] = NullPool
        engine_kwargs["connect_args"] = {
            "prepare_threshold": None,
            "options": "-c search_path=hcg,extensions,public -c statement_timeout=5000",
        }
    elif url.startswith("sqlite"):
        # The default DATABASE_URL is a file-based sqlite db under
        # backend/.tmp/, which is gitignored and so doesn't exist in a
        # fresh checkout (e.g. CI) - sqlite refuses to create the file if
        # its parent directory is missing.
        db_path = make_url(url).database
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **engine_kwargs)
    _instrument_engine(engine)
    return engine


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = create_database_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@lru_cache
def _default_session_factory() -> sessionmaker[Session]:
    """The process-wide session factory, built on first use rather than at
    import time. Importing app.db.session (e.g. transitively, by importing
    app.main) must not open a database connection or even construct an
    Engine before anything actually needs one - see F05."""
    return create_session_factory()


def get_session() -> Generator[Session, None, None]:
    with _default_session_factory()() as session:
        yield session
