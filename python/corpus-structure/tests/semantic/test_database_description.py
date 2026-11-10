from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from corpus_structure.serve.database_description import (
    DatabaseDescriptionRequest,
    describe_database,
)


def test_description_requires_query_binding():
    with pytest.raises(ValueError, match="together"):
        DatabaseDescriptionRequest(schemas=("kb",), query="SELECT 1")


@pytest.mark.parametrize("configured", [False, True])
def test_description_uses_server_type_resolution_with_configured_driver(
    semantic_db_engine, native_settings, configured, monkeypatch
):
    import adbc_driver_postgresql

    from corpus_structure.serve import database_description

    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA describe_types")
        conn.exec_driver_sql("CREATE TYPE describe_types.color AS ENUM ('red', 'blue')")
        conn.exec_driver_sql("CREATE DOMAIN describe_types.positive AS numeric CHECK (VALUE > 0)")
        conn.exec_driver_sql(
            "CREATE TABLE describe_types.sample (color describe_types.color, amount numeric(12,3), "
            "identity uuid NOT NULL, payload jsonb, opaque point, positive describe_types.positive)"
        )
        conn.exec_driver_sql("GRANT USAGE ON SCHEMA describe_types TO corpus_sem_reader")
        conn.exec_driver_sql("GRANT SELECT ON describe_types.sample TO corpus_sem_reader")
    url = make_url(native_settings.database.url).set(database=semantic_db_engine.url.database)
    settings = native_settings.model_copy(
        update={
            "database": native_settings.database.model_copy(
                update={"url": url.render_as_string(hide_password=False)}
            ),
            "analytics": native_settings.analytics.model_copy(
                update={
                    "adbc_driver_path": adbc_driver_postgresql._driver_path()
                    if configured
                    else None
                }
            ),
        }
    )
    acquire = database_description.open_adbc_connection
    acquired = []

    def observe_acquisition(uri, *, driver_path, resolver_mode):
        acquired.append((driver_path, resolver_mode))
        return acquire(uri, driver_path=driver_path, resolver_mode=resolver_mode)

    monkeypatch.setattr(database_description, "open_adbc_connection", observe_acquisition)
    result = describe_database(
        DatabaseDescriptionRequest(schemas=("describe_types",), relations=("sample",)), settings
    )
    assert acquired == [(settings.analytics.adbc_driver_path, "server")]
    assert result.principal == "corpus_sem_reader"
    shape = next(x for x in result.observations if "arrow_fields" in x)
    assert shape["status"] == "available"
    fields = {field["name"]: field for field in shape["arrow_fields"]}
    assert fields["color"]["arrow_type"] == "string"
    assert fields["amount"]["postgresql_type"] == "numeric"
    assert fields["amount"].get("storage_type", fields["amount"]["arrow_type"]) == "string"
    assert fields["amount"]["typmod"] in (-1, 786439, "unavailable")
    assert fields["identity"]["arrow_nullable"] is True
    assert fields["identity"]["declared_nullability"] == "unavailable"
    assert fields["payload"]["metadata"]
    assert fields["opaque"]["extension_name"] == "arrow.opaque"
    catalog = next(x for x in result.observations if x.get("interface") == "sqlalchemy.Inspector")
    assert (
        next(x for x in catalog["columns"] if x["column_name"] == "identity")["nullable"] is False
    )
    assert catalog["field_sources"]["relation_type"] == {
        "interface": "adbc.GetObjects",
        "session": "adbc",
    }
    assert catalog["field_sources"]["columns"] == {
        "interface": "sqlalchemy.Inspector",
        "session": "catalog",
    }
    assert catalog["field_sources"]["constraints"] == {"status": "not_requested"}
    catalog_fields = {column["column_name"]: column for column in catalog["columns"]}
    assert catalog_fields["color"]["native_type"] == {
        "kind": "enum",
        "name": "color",
        "schema": "describe_types",
    }
    assert catalog_fields["positive"]["native_type"] == {
        "kind": "domain",
        "name": "positive",
        "schema": "describe_types",
    }
    assert result.snapshot == "separate_sessions"


def test_literal_scoped_description(semantic_db_engine, native_settings):
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA describe_scope")
        conn.exec_driver_sql(
            'CREATE TABLE describe_scope."literal_%" (key bigint NOT NULL, value text)',
            execution_options={"no_parameters": True},
        )
        conn.exec_driver_sql("CREATE TABLE describe_scope.literal_collision (other boolean)")
        conn.exec_driver_sql("GRANT USAGE ON SCHEMA describe_scope TO corpus_sem_reader")
        conn.exec_driver_sql(
            "GRANT SELECT ON ALL TABLES IN SCHEMA describe_scope TO corpus_sem_reader"
        )
    base = make_url(native_settings.database.url).set(database=semantic_db_engine.url.database)
    settings = native_settings.model_copy(
        update={
            "database": native_settings.database.model_copy(
                update={"url": base.render_as_string(hide_password=False)}
            )
        }
    )
    result = describe_database(
        DatabaseDescriptionRequest(
            schemas=("describe_scope",), relations=("literal_%", "missing"), estimates=True
        ),
        settings,
    )
    relations_only = describe_database(
        DatabaseDescriptionRequest(
            schemas=("describe_scope",), relations=("literal_%",), depth="relations"
        ),
        settings,
    )
    relation_observation = next(
        x for x in relations_only.observations if x.get("relation") == "literal_%"
    )
    assert relation_observation["interface"] == "adbc.GetObjects"
    assert relation_observation["session"] == "adbc"
    assert relation_observation["columns"] == "not_requested"
    assert result.database == semantic_db_engine.url.database
    assert result.principal == "corpus_sem_reader"
    physical = [x for x in result.observations if x["kind"] == "physical"]
    table = next(x for x in physical if x.get("columns") and isinstance(x["columns"], list))
    assert table["relation"] == "literal_%"
    assert [x["column_name"] for x in table["columns"]] == ["key", "value"]
    assert any(
        x["status"] == "no_visible_match" and x.get("relation") == "missing" for x in physical
    )
    assert all(x.get("relation") in {"literal_%", "missing", None} for x in result.observations)
    assert any(x["kind"] == "estimate" for x in result.observations)
    estimate = next(x for x in result.observations if x["kind"] == "estimate")
    assert all(x["table_name"] == "literal_%" for x in estimate.get("statistics", []))
    assert estimate["status"] == "unavailable"
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql(
            """INSERT INTO describe_scope."literal_%" VALUES (1,'one'),(2,'two')""",
            execution_options={"no_parameters": True},
        )
        conn.exec_driver_sql("INSERT INTO describe_scope.literal_collision VALUES (true)")
        conn.exec_driver_sql(
            'ANALYZE describe_scope."literal_%"', execution_options={"no_parameters": True}
        )
        conn.exec_driver_sql("ANALYZE describe_scope.literal_collision")
    analyzed = describe_database(
        DatabaseDescriptionRequest(
            schemas=("describe_scope",), relations=("literal_%",), estimates=True
        ),
        settings,
    )
    statistics = next(x for x in analyzed.observations if x["kind"] == "estimate")
    assert statistics["status"] == "available"
    assert statistics["statistics"]
    assert all(x["table_name"] == "literal_%" for x in statistics["statistics"])
    with pytest.raises(ValueError, match="bound"):
        describe_database(
            DatabaseDescriptionRequest(schemas=("describe_scope",), max_columns=1), settings
        )


def test_query_schema_uses_actual_reader_and_refuses_effects(
    semantic_db_engine, native_settings, cli
):
    from corpus_structure.semantic import (
        PreparationProfile,
        SourceArtifact,
        SourceBundle,
        prepare_release,
    )
    from corpus_structure.semantic.analytical_profile import analytical_inputs
    from corpus_structure.semantic.authored_sql import SQLAdmissionError
    from corpus_structure.semantic.releases import persist_release

    bundle, dependencies = analytical_inputs(
        SourceBundle(
            "describe",
            (
                SourceArtifact(
                    "describe",
                    b"""id: https://example/describe
name: describe
prefixes: {ex: "https://example/"}
default_prefix: ex
types:
  string: {base: str, uri: "http://www.w3.org/2001/XMLSchema#string"}
classes: {}
""",
                ),
            ),
        )
    )
    prepared = prepare_release(bundle, dependencies)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, PreparationProfile(), prepared)
    url = make_url(native_settings.database.url).set(database=semantic_db_engine.url.database)
    settings = native_settings.model_copy(
        update={
            "database": native_settings.database.model_copy(
                update={"url": url.render_as_string(hide_password=False)}
            )
        }
    )
    result = describe_database(
        DatabaseDescriptionRequest(
            schemas=("kb",), query="SELECT 1::bigint AS answer", release_id=prepared.release_id
        ),
        settings,
    )
    with pytest.raises(ValueError, match="bound"):
        describe_database(
            DatabaseDescriptionRequest(
                schemas=("missing",),
                query="SELECT 1,2",
                release_id=prepared.release_id,
                max_columns=1,
            ),
            settings,
        )
    with pytest.raises(ValueError, match="bound"):
        describe_database(DatabaseDescriptionRequest(schemas=("missing",), max_bytes=1), settings)
    with pytest.raises(ValueError, match="bound"):
        describe_database(DatabaseDescriptionRequest(schemas=("x" * 500,), max_bytes=600), settings)
    with pytest.raises(ValueError, match="object bound"):
        describe_database(
            DatabaseDescriptionRequest(schemas=("kb", "ops"), depth="schemas", max_objects=1),
            settings,
        )
    shape = next(x for x in result.observations if x["kind"] == "query_output")
    assert [(x["name"], x["arrow_type"]) for x in shape["fields"]] == [("answer", "int64")]
    numeric = describe_database(
        DatabaseDescriptionRequest(
            schemas=("missing",),
            query="SELECT 1::numeric(12,3) AS amount",
            release_id=prepared.release_id,
        ),
        settings,
    )
    numeric_field = next(x for x in numeric.observations if x["kind"] == "query_output")["fields"][
        0
    ]
    assert numeric_field["postgresql_type"] == "numeric"
    assert numeric_field["typmod"] == 786439
    assert numeric_field.get("storage_type", numeric_field["arrow_type"]) == "string"
    for sql in ["SELECT $1", "SELECT pg_catalog.pg_sleep(1)", "SELECT 1; SELECT 2"]:
        with pytest.raises(SQLAdmissionError):
            describe_database(
                DatabaseDescriptionRequest(
                    schemas=("kb",), query=sql, release_id=prepared.release_id
                ),
                settings,
            )
    shown = cli(
        "db", "describe", "--schema", "missing_literal", "--json", settings=lambda: settings
    )
    assert shown.exit_code == 0, shown.output
    import json

    payload = json.loads(shown.stdout)
    assert payload["version"] == "database-description-v2"
    assert payload["snapshot"] == "separate_sessions"
    assert payload["observations"][0]["interface"] == "adbc.GetObjects"
    assert payload["principal"] == "corpus_sem_reader"
    assert payload["observations"][0]["status"] == "no_visible_match"


def test_arrow_metadata_is_lossless_attributed_and_bounded():
    import base64

    import pyarrow as pa

    from corpus_structure.serve.database_description import _fields

    raw = {
        b"POSTGRESQL:type": b"numeric",
        b"POSTGRESQL:typmod": b"-1",
        b"ARROW:extension:name": b"opaque",
        b"ARROW:extension:metadata": b'{"vendor":"pg"}',
        b"binary\xff": b"\x00\xfe",
    }
    schema = pa.schema(
        [
            pa.field(
                "nested", pa.struct([pa.field("amount", pa.string(), metadata=raw)]), nullable=False
            )
        ]
    )
    field = _fields(schema)[0]
    assert field["arrow_nullable"] is False
    assert field["declared_nullability"] == "unavailable"
    nested = field["children"][0]
    assert nested["typmod"] == -1
    assert nested["postgresql_type"] == "numeric"
    assert nested["extension_metadata"] == {"vendor": "pg"}
    assert {
        base64.b64decode(x["key_base64"]): base64.b64decode(x["value_base64"])
        for x in nested["metadata"]
    } == raw
    with pytest.raises(ValueError, match="column bound"):
        _fields(schema, columns=[1])
    with pytest.raises(ValueError, match="metadata byte bound"):
        _fields(schema, remaining=[1])


@pytest.mark.parametrize("failure_kind", ["iteration", "consumer_bound"])
def test_description_child_cleanup_preserves_iteration_and_consumer_failure(monkeypatch, failure_kind):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from corpus_structure.serve import database_description as description
    from corpus_structure.settings import Settings
    from corpus_structure.semantic.refusals import SemanticRefusal

    events = []
    primary = RuntimeError("metadata iteration")
    failures = {name: RuntimeError(name) for name in ("reader", "cursor", "rollback", "connection")}

    class Reader:
        def __iter__(self):
            if failure_kind == "iteration":
                raise primary
            yield SimpleNamespace(nbytes=1, to_pylist=lambda: [
                {"catalog_db_schemas": [{"db_schema_name": "public"}, {"db_schema_name": "public"}]}
            ])

        def close(self):
            events.append("reader")
            raise failures["reader"]

    class Cursor:
        adbc_statement = SimpleNamespace(set_options=lambda **kwargs: None)

        def execute(self, sql):
            pass

        def fetchone(self):
            return ("database", "corpus_sem_reader")

        def close(self):
            events.append("cursor")
            raise failures["cursor"]

    class Bulk:
        def cursor(self):
            return Cursor()

        def adbc_get_objects(self, **kwargs):
            return Reader()

        def rollback(self):
            events.append("rollback")
            raise failures["rollback"]

        def close(self):
            events.append("connection")
            raise failures["connection"]

    @contextmanager
    def connect():
        yield SimpleNamespace(exec_driver_sql=lambda sql: None)

    @contextmanager
    def engine(*args, **kwargs):
        yield SimpleNamespace(connect=connect)

    monkeypatch.setattr(description, "open_runtime_engine", engine)
    monkeypatch.setattr(description, "inspect", lambda conn: object())
    monkeypatch.setattr(description, "open_adbc_connection", lambda *args, **kwargs: Bulk())
    with pytest.raises(RuntimeError if failure_kind == "iteration" else SemanticRefusal) as caught:
        describe_database(DatabaseDescriptionRequest(schemas=("public",), depth="schemas", max_objects=1), Settings())
    if failure_kind == "iteration":
        assert caught.value is primary
    else:
        assert "object bound" in str(caught.value)
    assert events == ["reader", "cursor", "rollback", "connection"]
    assert caught.value.__dict__["adbc_cleanup_failures"] == tuple(failures[name] for name in events)


def test_existing_inaccessible_relation_is_distinct_from_missing_in_native_json(
    semantic_db_engine, semantic_reader_engine, semantic_application_settings, cli
):
    import json
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    relation = "public.semantic_alembic_version"
    with semantic_reader_engine.connect() as conn:
        assert conn.scalar(text("SELECT current_user")) == "corpus_sem_reader"
        assert conn.scalar(text("SELECT to_regclass(:relation)::text"), {"relation": relation})
        assert conn.scalar(text("SELECT has_table_privilege(current_user,:relation,'SELECT')"), {"relation": relation}) is False
    with semantic_reader_engine.connect() as conn, pytest.raises(DBAPIError) as caught:
        conn.exec_driver_sql("SELECT * FROM public.semantic_alembic_version")
    assert getattr(caught.value.orig, "sqlstate", None) == "42501"
    request = DatabaseDescriptionRequest(schemas=("public",), relations=("semantic_alembic_version", "ptd_known_missing_relation"))
    direct = describe_database(request, semantic_application_settings)
    shown = cli("db", "describe", "--schema", "public", "--relation", "semantic_alembic_version", "--relation", "ptd_known_missing_relation", "--json", settings=lambda: semantic_application_settings)
    assert shown.exit_code == 0, shown.output
    payload = json.loads(shown.stdout)
    for observations in (direct.observations, payload["observations"]):
        denied = [row for row in observations if row.get("relation") == "semantic_alembic_version"]
        assert any(row["status"] == "available" and isinstance(row.get("columns"), list) for row in denied)
        assert any(row["status"] == "refused" and row["arrow_fields"] == "unavailable" for row in denied)
        assert any(row.get("relation") == "ptd_known_missing_relation" and row["status"] == "no_visible_match" for row in observations)
