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


def test_literal_scoped_description(semantic_db_engine, native_settings):
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA describe_scope")
        conn.exec_driver_sql(
            'CREATE TABLE describe_scope."literal_%" (key bigint NOT NULL, value text)',
            execution_options={"no_parameters": True},
        )
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
    shape = next(x for x in result.observations if x["kind"] == "query_output")
    assert [(x["name"], x["arrow_type"]) for x in shape["fields"]] == [("answer", "int64")]
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
    assert payload["principal"] == "corpus_sem_reader"
    assert payload["observations"][0]["status"] == "no_visible_match"
