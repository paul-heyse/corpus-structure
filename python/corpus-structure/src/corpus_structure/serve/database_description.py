"""Bounded, principal-scoped physical and query-output observations."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, cast

import adbc_driver_manager
import adbc_driver_postgresql.dbapi as adbc
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
from corpus_structure.settings import Settings


class DescriptionDepth(StrEnum):
    SCHEMAS = "schemas"
    RELATIONS = "relations"
    COLUMNS = "columns"
    CONSTRAINTS = "constraints"


class DatabaseDescriptionRequest(BaseModel):
    schemas: tuple[str, ...] = Field(min_length=1)
    relations: tuple[str, ...] = ()
    depth: DescriptionDepth = DescriptionDepth.COLUMNS
    estimates: bool = False
    query: str | None = None
    release_id: str | None = None
    max_objects: int = Field(default=1000, gt=0)
    max_columns: int = Field(default=10000, gt=0)
    max_bytes: int = Field(default=4 * 1024 * 1024, gt=0)

    @model_validator(mode="after")
    def query_binding(self):
        if bool(self.query) != bool(self.release_id):
            raise ValueError("query and release_id must be supplied together")
        if any(not value for value in (*self.schemas, *self.relations)):
            raise ValueError("selectors must be nonempty literal names")
        return self


class DatabaseDescription(BaseModel):
    database: str
    principal: str
    observed_at: datetime
    schemas: tuple[str, ...]
    relations: tuple[str, ...]
    depth: str
    observations: list[dict[str, Any]]


def _pattern(value: str) -> str:
    # PostgreSQL metadata accepts literal selectors. Exact returned-name checks
    # below retain literal public semantics independently of backend matching.
    return value


def _rows(reader, remaining: list[int]):
    try:
        for batch in reader:
            remaining[0] -= batch.nbytes
            if remaining[0] < 0:
                raise SemanticRefusal("database description exceeds output byte bound")
            yield from batch.to_pylist()
    finally:
        reader.close()


def _fields(schema):
    return [
        {
            "name": f.name,
            "arrow_type": str(f.type),
            "domain": "unavailable",
            "typmod": "unavailable",
            "declared_nullability": "unavailable",
        }
        for f in schema
    ]


def describe_database(
    request: DatabaseDescriptionRequest, settings: Settings
) -> DatabaseDescription:
    """Describe only selected visible objects; never execute a submitted data query."""
    from corpus_structure.semantic.authored_sql import admit_sql
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID, metadata
    from corpus_structure.semantic.releases import open_release

    if request.query is not None:
        if request.release_id is None:
            raise SemanticRefusal("query release binding is missing")
        with (
            open_runtime_engine(settings, "describe-release", purpose="read") as engine,
            engine.connect() as conn,
        ):
            try:
                open_release(conn, request.release_id)
            except KeyError as error:
                raise SemanticRefusal("unknown description release") from error
        with (
            open_runtime_engine(settings, "describe-admission", purpose="read") as engine,
            engine.connect() as conn,
        ):
            admit_sql(
                conn,
                request.query,
                release_id=request.release_id,
                metadata=metadata,
                physical_id=PHYSICAL_MODEL_ID,
            )
    read = connection_settings(settings, "read")
    uri = make_url(read.database.url).render_as_string(hide_password=False)
    observations: list[dict[str, Any]] = []
    remaining = [request.max_bytes]
    object_count = column_count = 0
    with (
        open_runtime_engine(settings, "description-catalog", purpose="read") as catalog_engine,
        catalog_engine.connect() as catalog_conn,
        adbc.connect(uri) as conn,
    ):
        catalog_conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        catalog_conn.exec_driver_sql("SET LOCAL search_path=pg_catalog")
        catalog_inspector = inspect(catalog_conn)
        try:
            with conn.cursor() as cur:
                cur.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET LOCAL search_path=pg_catalog")
                cur.execute("SELECT current_database(), current_user")
                identity = cur.fetchone()
                if identity is None:
                    raise RuntimeError("database identity unavailable")
                database, principal = identity
                depth = {
                    "schemas": "db_schemas",
                    "relations": "tables",
                    "columns": "tables",
                    "constraints": "tables",
                }[request.depth]
                for selected_schema in dict.fromkeys(request.schemas):
                    found = False
                    for catalog in _rows(
                        conn.adbc_get_objects(
                            depth=cast(
                                Literal["all", "catalogs", "columns", "db_schemas", "tables"], depth
                            ),
                            catalog_filter=database,
                            db_schema_filter=_pattern(selected_schema),
                        ),
                        remaining,
                    ):
                        for schema in catalog.get("catalog_db_schemas") or []:
                            if schema["db_schema_name"] != selected_schema:
                                continue
                            found = True
                            object_count += 1
                            if object_count > request.max_objects:
                                raise SemanticRefusal("database description exceeds object bound")
                            if request.depth == "schemas":
                                observations.append(
                                    {
                                        "kind": "physical",
                                        "status": "available",
                                        "schema": selected_schema,
                                        "children": "not_requested",
                                    }
                                )
                                continue
                            matched = set()
                            for table in schema.get("db_schema_tables") or []:
                                name = table["table_name"]
                                if request.relations and name not in request.relations:
                                    continue
                                matched.add(name)
                                object_count += 1
                                columns = None
                                if request.depth in {"columns", "constraints"}:
                                    columns = [
                                        {
                                            "column_name": item["name"],
                                            "ordinal_position": index + 1,
                                            "physical_type": str(item["type"]),
                                            "nullable": item["nullable"],
                                            "default": item.get("default"),
                                        }
                                        for index, item in enumerate(
                                            catalog_inspector.get_columns(
                                                name, schema=selected_schema
                                            )
                                        )
                                    ]
                                column_count += len(columns or [])
                                if (
                                    object_count > request.max_objects
                                    or column_count > request.max_columns
                                ):
                                    raise SemanticRefusal(
                                        "database description exceeds object/column bound"
                                    )
                                item = {
                                    "kind": "physical",
                                    "status": "available",
                                    "schema": selected_schema,
                                    "relation": name,
                                    "relation_type": table["table_type"],
                                    "columns": columns if columns is not None else "not_requested",
                                    "constraints": {
                                        "primary_key": catalog_inspector.get_pk_constraint(
                                            name, schema=selected_schema
                                        ),
                                        "foreign_keys": catalog_inspector.get_foreign_keys(
                                            name, schema=selected_schema
                                        ),
                                        "unique": catalog_inspector.get_unique_constraints(
                                            name, schema=selected_schema
                                        ),
                                        "check": catalog_inspector.get_check_constraints(
                                            name, schema=selected_schema
                                        ),
                                        "exclusions": "unavailable",
                                    }
                                    if request.depth == "constraints"
                                    else "not_requested",
                                }
                                observations.append(item)
                                if request.depth in {"columns", "constraints"}:
                                    permitted = catalog_conn.scalar(
                                        text(
                                            "SELECT pg_catalog.has_table_privilege("
                                            "pg_catalog.format('%I.%I',CAST(:schema AS text),"
                                            "CAST(:relation AS text)),'SELECT')"
                                        ),
                                        dict(schema=selected_schema, relation=name),
                                    )
                                    if permitted:
                                        try:
                                            shape = conn.adbc_get_table_schema(
                                                name, db_schema_filter=selected_schema
                                            )
                                            shape_item = {
                                                "status": "available",
                                                "arrow_fields": _fields(shape),
                                            }
                                        except adbc_driver_manager.NotSupportedError:
                                            shape_item = {
                                                "status": "unsupported",
                                                "arrow_fields": "unavailable",
                                            }
                                    else:
                                        shape_item = {
                                            "status": "refused",
                                            "arrow_fields": "unavailable",
                                        }
                                    observations.append(
                                        {
                                            "kind": "physical",
                                            "schema": selected_schema,
                                            "relation": name,
                                            **shape_item,
                                        }
                                    )
                                if request.estimates:
                                    try:
                                        stats = list(
                                            _rows(
                                                conn.adbc_get_statistics(
                                                    catalog_filter=database,
                                                    db_schema_filter=selected_schema,
                                                    table_name_filter=_pattern(name),
                                                    approximate=True,
                                                ),
                                                remaining,
                                            )
                                        )
                                        stats = [
                                            entry
                                            for root in stats
                                            if root.get("catalog_name") == database
                                            for schema_row in root.get("catalog_db_schemas") or []
                                            if schema_row.get("db_schema_name") == selected_schema
                                            for entry in schema_row.get("db_schema_statistics")
                                            or []
                                            if entry.get("table_name") == name
                                        ]
                                        observations.append(
                                            {
                                                "kind": "estimate",
                                                "schema": selected_schema,
                                                "relation": name,
                                                "status": "available" if stats else "unavailable",
                                                "approximate_requested": True,
                                                "statistics": stats,
                                                "freshness": "unavailable",
                                            }
                                        )
                                    except adbc_driver_manager.NotSupportedError:
                                        observations.append(
                                            {
                                                "kind": "estimate",
                                                "schema": selected_schema,
                                                "relation": name,
                                                "status": "unsupported",
                                            }
                                        )
                            for name in set(request.relations) - matched:
                                observations.append(
                                    {
                                        "kind": "physical",
                                        "status": "no_visible_match",
                                        "schema": selected_schema,
                                        "relation": name,
                                    }
                                )
                    if not found:
                        observations.append(
                            {
                                "kind": "physical",
                                "status": "no_visible_match",
                                "schema": selected_schema,
                            }
                        )
                if request.query is not None:
                    shape = cur.adbc_execute_schema(request.query)
                    column_count += len(shape)
                    if column_count > request.max_columns:
                        raise SemanticRefusal("query schema exceeds column bound")
                    observations.append(
                        {
                            "kind": "query_output",
                            "status": "available",
                            "release_id": request.release_id,
                            "physical_id": PHYSICAL_MODEL_ID,
                            "fields": _fields(shape),
                        }
                    )
        finally:
            conn.rollback()
    result = DatabaseDescription(
        database=database,
        principal=principal,
        observed_at=datetime.now(UTC),
        schemas=request.schemas,
        relations=request.relations,
        depth=request.depth,
        observations=observations,
    )

    if len(result.model_dump_json().encode("utf8")) > request.max_bytes:
        raise SemanticRefusal("database description exceeds returned JSON byte bound")
    return result
