"""Identity of an acquired PostgreSQL endpoint and its authorized purpose."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic._operation_ids import NativeAdmissionParametersPurpose
from corpus_structure.semantic.refusals import SemanticRefusal

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from corpus_structure.settings import Settings

type StoragePurpose = NativeAdmissionParametersPurpose | Literal["maintenance", "fit"]


class StorageTargetError(SemanticRefusal):
    """The current connection cannot establish or match its storage binding."""


class StorageTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    database: str
    database_oid: int
    system_identifier: str
    host: str
    port: int
    purpose: StoragePurpose


def assert_explicit_route(settings: Settings) -> dict[str, str]:
    """Require one fully named libpq endpoint for a separately selected target."""
    from psycopg import ProgrammingError
    from psycopg.conninfo import conninfo_to_dict

    from corpus_structure.settings import ambient_postgresql_routing

    try:
        route = {
            key: str(value)
            for key, value in conninfo_to_dict(settings.database.url).items()
            if value is not None
        }
        port = int(route.get("port", "0"))
    except (ValueError, ProgrammingError) as error:
        raise StorageTargetError("invalid configured PostgreSQL route") from error
    if (
        not route.get("dbname")
        or not (route.get("host") or route.get("hostaddr"))
        or any("," in route.get(field, "") for field in ("host", "hostaddr"))
        or not 0 < port <= 65535
        or route.get("service")
    ):
        raise StorageTargetError("target requires an explicit PostgreSQL database, host and port")
    ambient = ambient_postgresql_routing()
    if "PGSERVICE" in ambient or ("PGHOSTADDR" in ambient and not route.get("hostaddr")):
        raise StorageTargetError("ambient libpq routing conflicts with the explicit target")
    return {key: route[key] for key in ("dbname", "host", "hostaddr", "port") if key in route}


def verify_declared_route(conn: Connection, settings: Settings) -> None:
    """Check the actual libpq route before relying on the configured selection."""
    import psycopg

    route = assert_explicit_route(settings)
    driver = conn.connection.driver_connection
    if not isinstance(driver, psycopg.Connection):
        raise StorageTargetError("storage identity requires an acquired psycopg connection")
    info = driver.info
    if (
        info.dbname != route["dbname"]
        or info.port != int(route["port"])
        or (route.get("host") and info.host != route["host"])
        or (route.get("hostaddr") and info.hostaddr != route["hostaddr"])
    ):
        raise StorageTargetError("acquired PostgreSQL route differs from the configured route")


def acquired_target(conn: Connection, *, purpose: StoragePurpose) -> StorageTarget:
    """Read libpq routing and catalog identity on the exact borrowed connection."""
    import psycopg
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic._operation_calls import require_runtime_principal

    driver = conn.connection.driver_connection
    if not isinstance(driver, psycopg.Connection):
        raise StorageTargetError("storage identity requires an acquired psycopg connection")
    try:
        if purpose == "fit":
            conn.exec_driver_sql("SELECT eval.require_record_fitting_principal()")
        elif purpose != "maintenance":
            require_runtime_principal(conn, purpose=purpose)
        row = conn.exec_driver_sql(
            "SELECT d.datname, d.oid, c.system_identifier "
            "FROM pg_catalog.pg_database d CROSS JOIN pg_catalog.pg_control_system() c "
            "WHERE d.datname = pg_catalog.current_database()"
        ).one()
    except DBAPIError as error:
        raise StorageTargetError(
            f"cannot establish the acquired PostgreSQL target for {purpose}"
        ) from error
    info = driver.info
    return StorageTarget(
        database=row.datname,
        database_oid=row.oid,
        system_identifier=str(row.system_identifier),
        host=info.hostaddr or info.host,
        port=info.port,
        purpose=purpose,
    )


def verify_target(
    conn: Connection, expected: StorageTarget, *, purpose: StoragePurpose
) -> StorageTarget:
    actual = acquired_target(conn, purpose=purpose)
    if actual != expected.model_copy(update={"purpose": purpose}):
        raise StorageTargetError("acquired PostgreSQL target differs from the approved target")
    return actual
