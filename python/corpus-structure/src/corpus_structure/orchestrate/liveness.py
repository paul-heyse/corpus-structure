"""PostgreSQL session custody for a run's active supervisor."""

from collections.abc import Generator
from contextlib import contextmanager
from math import ceil

from sqlalchemy import Connection, Engine, text

from corpus_structure.semantic.operations import OperationConflict

_KEY = "corpus_runtime.run_supervisor_key(:run_id)"


@contextmanager
def supervisor_connection(engine: Engine) -> Generator[Connection]:
    """Keep the lease outside the writer pool, bound to its acquired PostgreSQL route."""
    database = getattr(engine, "_corpus_database_settings", None)
    if database is None:
        # An injected SQLAlchemy engine owns its connection setup and test role.
        with engine.connect() as conn:
            yield conn
        return

    import psycopg
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    from corpus_structure.core.db.store import configure

    def identity(conn: Connection):
        return conn.exec_driver_sql(
            "SELECT current_database(), current_user, oid FROM pg_catalog.pg_database "
            "WHERE datname = current_database()"
        ).one()

    with engine.connect() as source:
        expected = identity(source)
        physical = source.connection.driver_connection
        if not isinstance(physical, psycopg.Connection):
            raise OperationConflict("run supervisor requires an acquired PostgreSQL connection")
        info = physical.info
        route = {"host": info.host, "hostaddr": info.hostaddr or "", "port": info.port}

    def open_session():
        physical = psycopg.connect(
            database.url,
            **route,
            application_name="ci-run-supervisor",
            connect_timeout=max(1, ceil(database.checkout_timeout_seconds)),
        )
        try:
            configure(physical)
        except BaseException:
            physical.close()
            raise
        return physical

    dedicated = create_engine("postgresql+psycopg://", creator=open_session, poolclass=NullPool)
    try:
        with dedicated.connect() as conn:
            if identity(conn) != expected:
                raise OperationConflict("run supervisor acquired a different database or role")
            conn.rollback()
            yield conn
    finally:
        dedicated.dispose()


@contextmanager
def run_supervisor(conn: Connection, run_id: int) -> Generator[None]:
    """Hold the dedicated physical connection for the active run effect."""
    parameters = {"run_id": run_id}
    if not conn.scalar(text(f"SELECT pg_try_advisory_lock({_KEY})"), parameters):
        raise OperationConflict(f"run {run_id} already has an active supervisor")
    try:
        yield
    finally:
        try:
            if not conn.invalidated:
                if conn.in_transaction():
                    conn.rollback()
                conn.execute(text(f"SELECT pg_advisory_unlock({_KEY})"), parameters)
        except Exception:
            # A reused physical session must never carry the previous borrower's lease.
            conn.invalidate()


def record_supervisor(conn: Connection, run_id: int, *, waiting: bool) -> None:
    conn.execute(
        text("SELECT corpus_runtime.record_run_supervisor(:run_id, :waiting)"),
        {"run_id": run_id, "waiting": waiting},
    )


@contextmanager
def supervise_run(engine: Engine, run_id: int) -> Generator[None]:
    with supervisor_connection(engine) as conn, run_supervisor(conn, run_id):
        record_supervisor(conn, run_id, waiting=False)
        conn.commit()
        yield
        # A clean handoff retains the source cut; terminal results own their state.
        with conn.begin():
            record_supervisor(conn, run_id, waiting=True)


def observe_supervisor(conn: Connection, run_id: int) -> tuple[bool, bool | None]:
    """Read the live lease and the last durable handoff using reader authority."""
    row = conn.execute(
        text(
            "SELECT corpus_runtime.run_supervisor_held(:run_id, false), "
            "(SELECT waiting FROM corpus_runtime.run_supervisor WHERE run_id = :run_id)"
        ),
        {"run_id": run_id},
    ).one()
    return row[0], row[1]
