"""Current semantic entry-point resources and explicit project selections."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import Connection, Engine, Text, func, select
from sqlalchemy.engine import URL, make_url

from corpus_structure.settings import Settings

type Purpose = Literal["read", "write", "evaluate", "admit", "maintenance", "fit"]


def connection_settings(settings: Settings, purpose: Purpose = "write") -> Settings:
    """Resolve authentication for one explicit purpose on the declared storage target.

    Purpose URLs may omit endpoint components; an explicitly conflicting component refuses.
    A different principal never implicitly inherits the base principal's password.
    """
    database = settings.database
    source = make_url(database.sqlalchemy_url)
    declared = {
        "read": database.reader_url,
        "evaluate": database.evaluator_url,
        "fit": database.fitter_url,
        "admit": database.admission_url,
        "maintenance": database.maintenance_url,
    }
    if purpose == "write":
        return settings
    role = {
        "read": "corpus_sem_reader",
        "evaluate": "corpus_sem_evaluator",
        "fit": "corpus_sem_fitter",
        "admit": "corpus_sem_admitter",
        "maintenance": None,
    }[purpose]
    credentials = make_url(declared[purpose] or URL.create("postgresql", username=role))
    if credentials.drivername not in {"postgresql", "postgres", "postgresql+psycopg"}:
        raise ValueError(f"database credentials for {purpose} must use a PostgreSQL URL")
    for component in ("host", "port", "database"):
        actual = getattr(credentials, component)
        if actual not in (None, "") and actual != getattr(source, component):
            raise ValueError(f"database credentials for {purpose} contradict target {component}")
    authentication = {"user", "password", "passfile"}
    for key, value in credentials.query.items():
        if key not in authentication and source.query.get(key) != value:
            raise ValueError(f"database credentials for {purpose} contradict target option {key}")
    url = URL.create(
        "postgresql",
        username=credentials.username,
        password=credentials.password,
        host=source.host,
        port=source.port,
        database=source.database,
        query={key: value for key, value in source.query.items() if key not in authentication},
    ).render_as_string(hide_password=False)
    return settings.model_copy(update={"database": database.model_copy(update={"url": url})})


def require_runtime_principal(conn: Connection, *, purpose: Purpose) -> None:
    """Authenticate the current purpose on the actual borrowed connection."""
    if purpose == "maintenance":
        return
    if purpose == "fit":
        conn.execute(select(func.ops.ddo_require_feature_fit_principal())).scalar_one()
    else:
        conn.execute(
            select(func.data.require_runtime_principal(purpose, type_=Text()))
        ).scalar_one()


@contextmanager
def open_runtime_engine(
    settings: Settings,
    application_name: str = "ci",
    *,
    purpose: Purpose,
    timeout: float | None = None,
    max_size: int | None = None,
) -> Generator[Engine]:
    """One psycopg pool; SQLAlchemy uses the store's NullPool adapter."""
    from corpus_structure.core.db.store import open_store

    with open_store(
        connection_settings(settings, purpose), application_name, timeout=timeout, max_size=max_size
    ) as store:
        try:
            if purpose != "maintenance":
                with store.engine.connect() as conn:
                    require_runtime_principal(conn, purpose=purpose)
            yield store.engine
        except BaseException as error:
            from corpus_structure.core.db.store import operation_failure

            error.__dict__["database_diagnostic"] = store.diagnostic(
                operation_failure(error).failure
            )
            raise
