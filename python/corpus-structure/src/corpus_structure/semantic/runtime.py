"""Current semantic entry-point resources and explicit project selections."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import Connection, Engine, select, text
from sqlalchemy.engine import URL, make_url

from corpus_structure.settings import Settings
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict

Purpose = Literal["write", "read", "evaluate", "maintenance"]


def connection_settings(settings: Settings, purpose: Purpose = "write") -> Settings:
    """Bind every credential purpose to the application's one declared storage target.

    Maintenance and evaluator URLs contribute credentials only. Their database, network
    coordinates and query options cannot redirect a phase of an otherwise bound operation.
    """
    database = settings.database
    source = make_url(database.sqlalchemy_url)
    credentials = source
    if purpose == "maintenance":
        credentials = make_url(database.maintenance_url)
    elif purpose == "evaluate":
        credentials = (make_url(database.evaluator_url) if database.evaluator_url else
                       source.set(username="corpus_sem_evaluator"))
    elif purpose == "read" and source.username == "corpus_sem_writer":
        credentials = source.set(username="corpus_sem_reader")
    if purpose == "write":
        return settings
    if credentials.drivername not in {"postgresql", "postgres", "postgresql+psycopg"}:
        raise ValueError(f"database credentials for {purpose} must use a PostgreSQL URL")
    # URL.set ignores None, so create a new public URL to remove the writer username and
    # password when the maintenance credentials intentionally use local peer authentication.
    url = URL.create(
        "postgresql", username=credentials.username, password=credentials.password,
        host=source.host, port=source.port, database=source.database,
        query={key: value for key, value in source.query.items()
               if key not in {"user", "password", "passfile"}},
    ).render_as_string(hide_password=False)
    return settings.model_copy(update={"database": database.model_copy(update={"url": url})})


@contextmanager
def open_runtime_engine(
    settings: Settings,
    application_name: str = "ci",
    *,
    purpose: Purpose = "write",
    timeout: float = 30.0,
    max_size: int = 4,
) -> Iterator[Engine]:
    """One psycopg pool; SQLAlchemy uses the store's NullPool adapter."""
    from corpus_structure.core.db.store import open_store

    with open_store(connection_settings(settings, purpose), application_name,
                    timeout=timeout, max_size=max_size) as store:
        yield store.engine


def resolve_source_binding(
    conn: Connection, project_id: str, *, release_id: str | None = None,
    realization_id: str | None = None,
) -> tuple[str, str]:
    """Use the project's admitted interpretation; refuse an ambiguous source realization."""
    projects, realizations = table("data.project"), table("data.realization")
    project = conn.execute(select(projects).where(projects.c.project_id == project_id)).mappings().one_or_none()
    if project is None:
        raise OperationConflict(f"unknown semantic project {project_id!r}; initialize it first")
    release_id = release_id or project["active_release_id"]
    if release_id is None:
        raise OperationConflict("project has no active admitted release")
    if realization_id is None and project.get("selected_result_run_id") is not None:
        completed = table("ops.completed_result")
        realization_id = conn.execute(select(completed.c.output_realization_id).where(
            completed.c.run_id == project["selected_result_run_id"],
            completed.c.release_id == release_id,
        )).scalar_one_or_none()
    if realization_id is None:
        candidates = conn.execute(select(realizations.c.realization_id).where(
            realizations.c.project_id == project_id, realizations.c.release_id == release_id,
            realizations.c.state == "active",
        )).scalars().all()
        if len(candidates) != 1:
            raise OperationConflict("select --realization explicitly: project has zero or multiple active inputs")
        realization_id = candidates[0]
    return release_id, realization_id


def select_completed_result(
    conn: Connection, project_id: str, run_id: int, expected_generation: int,
) -> int:
    """Atomically select an immutable completed output under the project generation CAS."""
    return conn.execute(text("SELECT data.select_project_result(:p,:r,:g)"),
                        {"p": project_id, "r": run_id, "g": expected_generation}).scalar_one()
