"""Current semantic entry-point resources and explicit project selections."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import Connection, Engine, select
from sqlalchemy.engine import URL, make_url

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.settings import Settings

from ._operation_ids import NativeAdmissionParametersPurpose

type Purpose = NativeAdmissionParametersPurpose | Literal["maintenance", "fit"]


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
                from ._operation_calls import require_runtime_principal

                with store.engine.connect() as conn:
                    if purpose == "fit":
                        from sqlalchemy import text

                        conn.execute(text("SELECT eval.require_record_fitting_principal()"))
                    else:
                        require_runtime_principal(conn, purpose=purpose)
            yield store.engine
        except BaseException as error:
            from corpus_structure.core.db.store import operation_failure

            error.__dict__["database_diagnostic"] = store.diagnostic(
                operation_failure(error).failure
            )
            raise


def resolve_source_binding(
    conn: Connection,
    project_id: str,
    *,
    release_id: str | None = None,
    realization_id: str | None = None,
) -> tuple[str, str]:
    """Use the project's admitted interpretation; refuse an ambiguous source realization."""
    projects, realizations = table("data.project"), table("data.realization")
    project = (
        conn.execute(select(projects).where(projects.c.project_id == project_id))
        .mappings()
        .one_or_none()
    )
    if project is None:
        raise OperationConflict(f"unknown semantic project {project_id!r}; initialize it first")
    release_id = release_id or project["active_release_id"]
    if release_id is None:
        raise OperationConflict("project has no active admitted release")
    if realization_id is None and project.get("selected_result_run_id") is not None:
        completed = table("ops.completed_result")
        realization_id = conn.execute(
            select(completed.c.output_realization_id).where(
                completed.c.run_id == project["selected_result_run_id"],
                completed.c.release_id == release_id,
            )
        ).scalar_one_or_none()
    if realization_id is None:
        candidates = (
            conn.execute(
                select(realizations.c.realization_id).where(
                    realizations.c.project_id == project_id,
                    realizations.c.release_id == release_id,
                    realizations.c.state == "active",
                )
            )
            .scalars()
            .all()
        )
        if len(candidates) != 1:
            raise OperationConflict(
                "select --realization explicitly: project has zero or multiple active inputs"
            )
        realization_id = candidates[0]
    return release_id, realization_id


def select_completed_result(
    conn: Connection,
    project_id: str,
    run_id: int,
    expected_generation: int,
) -> int:
    """Atomically select an immutable completed output under the project generation CAS."""
    from ._operation_calls import select_completed_result as invoke
    from ._operation_ids import ProjectId, RunId

    return invoke(
        conn,
        project_id=ProjectId(project_id),
        run_id=RunId(run_id),
        expected_generation=expected_generation,
    )
