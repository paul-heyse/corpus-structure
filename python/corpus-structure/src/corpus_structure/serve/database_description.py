"""Bounded, principal-scoped physical and query-output observations."""

from __future__ import annotations

import base64
import json
from contextlib import suppress
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from corpus_structure.core.db.adbc_lifetime import open_adbc_connection, owned_adbc_read
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
    version: Literal["database-description-v2"] = "database-description-v2"
    observation_sessions: tuple[str, ...] = ("catalog", "adbc")
    snapshot: Literal["separate_sessions"] = "separate_sessions"
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


def _metadata(metadata, remaining):
    """Preserve bytes; interpreted conveniences never replace the observed metadata."""
    encoded = []
    for key, value in sorted((metadata or {}).items()):
        remaining[0] -= 4 * ((len(key) + 2) // 3 + (len(value) + 2) // 3)
        if remaining[0] < 0:
            raise SemanticRefusal("database description exceeds metadata byte bound")
        encoded.append(
            {
                "key_base64": base64.b64encode(key).decode("ascii"),
                "value_base64": base64.b64encode(value).decode("ascii"),
            }
        )
    return encoded


def _fields(schema, *, remaining=None, columns=None):
    import pyarrow as pa

    remaining = remaining if remaining is not None else [4 * 1024 * 1024]
    columns = columns if columns is not None else [10000]

    def field(f):
        columns[0] -= 1
        if columns[0] < 0:
            raise SemanticRefusal("database description exceeds column bound")
        metadata = f.metadata or {}
        result: dict[str, Any] = {
            "name": f.name,
            "arrow_type": str(f.type),
            "arrow_nullable": f.nullable,
            "domain": "unavailable",
            "typmod": "unavailable",
            "declared_nullability": "unavailable",
            "metadata": _metadata(metadata, remaining),
            "children": [],
        }
        for key, label in (
            (b"POSTGRESQL:type", "postgresql_type"),
            (b"ARROW:extension:name", "extension_name"),
        ):
            if key in metadata:
                with suppress(UnicodeDecodeError):
                    result[label] = metadata[key].decode("utf8")
        if b"POSTGRESQL:typmod" in metadata:
            with suppress(ValueError):
                result["typmod"] = int(metadata[b"POSTGRESQL:typmod"].decode("ascii"))
        if b"ARROW:extension:metadata" in metadata:
            with suppress(ValueError):
                result["extension_metadata"] = json.loads(metadata[b"ARROW:extension:metadata"])
        typ = f.type
        if isinstance(typ, pa.BaseExtensionType):
            result["extension_name"] = typ.extension_name
            result["storage_type"] = str(typ.storage_type)
            if isinstance(typ, pa.OpaqueType):
                result["extension_metadata"] = {
                    "type_name": typ.type_name,
                    "vendor_name": typ.vendor_name,
                }
            typ = typ.storage_type
        result["children"] = [field(typ.field(i)) for i in range(typ.num_fields)]
        return result

    return [field(f) for f in schema]


def _native_type(typ):
    """Qualified identity only when reflected by a public native type object."""
    from sqlalchemy.dialects.postgresql import DOMAIN, ENUM

    if isinstance(typ, (DOMAIN, ENUM)):
        return {
            "kind": "domain" if isinstance(typ, DOMAIN) else "enum",
            "name": typ.name,
            "schema": typ.schema,
        }
    return "unavailable"


def describe_database(
    request: DatabaseDescriptionRequest, settings: Settings
) -> DatabaseDescription:
    """Describe only selected visible objects; never execute a submitted data query."""
    import adbc_driver_manager

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
    object_count = 0
    columns_remaining = [request.max_columns]

    def observe(item):
        if item["kind"] == "query_output":
            interface = "adbc.ExecuteSchema"
        elif item["kind"] == "estimate":
            interface = "adbc.GetStatistics"
        elif "arrow_fields" in item:
            interface = "adbc.GetTableSchema"
        elif isinstance(item.get("columns"), list):
            interface = "sqlalchemy.Inspector"
            item["relation_interface"] = "adbc.GetObjects"
            item["field_sources"] = {
                **{
                    field: {"interface": "adbc.GetObjects", "session": "adbc"}
                    for field in ("schema", "relation", "relation_type")
                },
                "columns": {"interface": "sqlalchemy.Inspector", "session": "catalog"},
                "constraints": {"interface": "sqlalchemy.Inspector", "session": "catalog"}
                if isinstance(item.get("constraints"), dict)
                else {"status": "not_requested"},
            }
        else:
            interface = "adbc.GetObjects"
        item["interface"] = interface
        item["session"] = "catalog" if interface == "sqlalchemy.Inspector" else "adbc"
        observations.append(item)

    with (
        open_runtime_engine(settings, "description-catalog", purpose="read") as catalog_engine,
        catalog_engine.connect() as catalog_conn,
        owned_adbc_read(
            open_adbc_connection(
                uri, driver_path=settings.analytics.adbc_driver_path, resolver_mode="server"
            )
        ) as conn,
    ):
        catalog_conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        catalog_conn.exec_driver_sql("SET LOCAL search_path=pg_catalog")
        catalog_inspector = inspect(catalog_conn)
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
                            observe(
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
                                        "native_type": _native_type(item["type"]),
                                        "nullable": item["nullable"],
                                        "default": item.get("default"),
                                    }
                                    for index, item in enumerate(
                                        catalog_inspector.get_columns(name, schema=selected_schema)
                                    )
                                ]
                            columns_remaining[0] -= len(columns or [])
                            if object_count > request.max_objects or columns_remaining[0] < 0:
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
                            observe(item)
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
                                            "arrow_fields": _fields(
                                                shape,
                                                remaining=remaining,
                                                columns=columns_remaining,
                                            ),
                                            "schema_metadata": _metadata(shape.metadata, remaining),
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
                                observe(
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
                                        for entry in schema_row.get("db_schema_statistics") or []
                                        if entry.get("table_name") == name
                                    ]
                                    observe(
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
                                    observe(
                                        {
                                            "kind": "estimate",
                                            "schema": selected_schema,
                                            "relation": name,
                                            "status": "unsupported",
                                        }
                                    )
                        for name in set(request.relations) - matched:
                            observe(
                                {
                                    "kind": "physical",
                                    "status": "no_visible_match",
                                    "schema": selected_schema,
                                    "relation": name,
                                }
                            )
                if not found:
                    observe(
                        {
                            "kind": "physical",
                            "status": "no_visible_match",
                            "schema": selected_schema,
                        }
                    )
            if request.query is not None:
                shape = cur.adbc_execute_schema(request.query)
                observe(
                    {
                        "kind": "query_output",
                        "status": "available",
                        "release_id": request.release_id,
                        "physical_id": PHYSICAL_MODEL_ID,
                        "fields": _fields(shape, remaining=remaining, columns=columns_remaining),
                        "schema_metadata": _metadata(shape.metadata, remaining),
                    }
                )
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
