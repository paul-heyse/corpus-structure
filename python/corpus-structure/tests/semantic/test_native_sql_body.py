"""Server-bound SQL-standard body custody and explicit mixed-profile evolution."""

import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, Table, Text, literal, literal_column, select, text

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    admit_native,
    definition_from_sql,
    execute_native_sql,
    observe_native,
    prepare_native_authoring,
)
from corpus_structure.semantic.native_sql_body import (
    SQL_STANDARD_PROFILE,
    admission_body_comparison,
    sql_standard_definition,
)


def test_sql_standard_bound_profile_frozen_transition_and_native_results(semantic_bare_engine):
    md = MetaData()
    items = Table("items", md, Column("n", Integer, primary_key=True), schema="native test")
    with semantic_bare_engine.connect() as conn:
        transaction = conn.begin()
        conn.exec_driver_sql("CREATE SCHEMA sem")
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        md.create_all(conn)
        conn.execute(items.insert(), [{"n": 1}, {"n": 2}, {"n": 3}])
        owner = conn.scalar(text("SELECT current_user"))
        old = definition_from_sql(
            conn,
            """CREATE OR REPLACE FUNCTION "native test".selected(p_min integer)
RETURNS TABLE(n integer,label text) LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $$ SELECT n,'stable'::text
FROM "native test".items WHERE n>=p_min $$""",
            source="selected:AS-v1",
            owner=owner,
            grants=(("corpus_sem_reader", "EXECUTE", False),),
        )
        original = prepare_native_authoring(conn, (old,), owned_authoring=True).desired[0]
        operations = Operations(MigrationContext.configure(conn))
        NativeTransitionOp.native_transition(
            operations, NativeTransitionOp(None, original).payload()
        )
        conn.exec_driver_sql("""CREATE FUNCTION "native test".selected(text) RETURNS text
LANGUAGE sql AS $$ SELECT 'unrelated overload'::text $$""")
        selected = sql_standard_definition(
            replace(
                old,
                role_bindings=(("$migration_owner", "sem_namespace_owner"),),
                bind_owner=True,
            ),
            select(items.c.n, literal("stable", type_=Text).label("label")).where(
                items.c.n >= literal_column("p_min", type_=Integer)
            ),
        )
        assert selected.catalog_version == 2
        authoring = prepare_native_authoring(
            conn, (selected,), predecessor=(original,), owned_authoring=True
        )
        target = authoring.desired[0]
        assert target.binding_version == 2 and target.catalog["owner"] == "$migration_owner"
        assert target.expected_catalog(conn)["owner"] == owner
        assert not any(" OWNER TO " in statement for statement in target.statements)
        assert target.catalog["body_kind"] == "sql_standard"
        assert target.catalog["body_profile"] == SQL_STANDARD_PROFILE
        assert target.catalog["server_major"] == 18
        assert any(
            d["type"] == "table column" and d["identity"] == '"native test".items.n'
            for d in target.catalog["dependencies"]
        )
        assert all("oid" not in d for d in target.catalog["dependencies"])
        assert (
            target.catalog["language"],
            target.catalog["security"],
            target.catalog["volatility"],
        ) == ("sql", True, "s")
        payload = NativeTransitionOp(original, target).payload()
        assert payload["version"] == 2
        NativeTransitionOp.native_transition(operations, payload)
        admit_native(conn, (target,))
        descriptor = {
            key: target.catalog[key]
            for key in ("body_kind", "body_profile", "server_major", "dependencies")
        }
        descriptor["body_sha256"] = sha256(target.catalog["body"].encode()).hexdigest()
        comparison = text(
            "SELECT "
            + admission_body_comparison()
            + " FROM pg_proc p CROSS JOIN (SELECT CAST(:spec AS jsonb) value) item"
            + " WHERE p.oid=CAST(:signature AS regprocedure)"
        )

        def body_differs(spec):
            return conn.scalar(
                comparison, {"spec": json.dumps(spec), "signature": target.identity.qualified}
            )

        assert body_differs(descriptor) is False
        assert body_differs({**descriptor, "dependencies": []}) is True
        assert body_differs({**descriptor, "body_profile": "unknown"}) is True
        assert body_differs({"body_sha256": sha256(b"").hexdigest()}) is True
        assert conn.exec_driver_sql('SELECT * FROM "native test".selected(2) ORDER BY n').all() == [
            (2, "stable"),
            (3, "stable"),
        ]
        assert (
            conn.exec_driver_sql("SELECT \"native test\".selected('x'::text)").scalar_one()
            == "unrelated overload"
        )
        with pytest.raises(NativeAuthoringError, match="unsupported"):
            observe_native(conn, target.identity)  # The v1 reader remains an AS-only reader.
        previous = conn.scalar(text("SHOW search_path"))
        conn.exec_driver_sql('SET LOCAL search_path="native test",public')
        assert observe_native(conn, target.identity, catalog_version=2) == target.expected_catalog(
            conn
        )
        assert conn.scalar(text("SHOW search_path")) == '"native test", public'
        conn.execute(text("SELECT set_config('search_path',:p,true)"), {"p": previous})
        for change, expected in (
            ('ALTER FUNCTION "native test".selected(integer) SET search_path=public', "body"),
            (
                'GRANT EXECUTE ON FUNCTION "native test".selected(integer) TO corpus_sem_writer',
                "acl",
            ),
        ):
            with pytest.raises(NativeAuthoringError, match=expected), conn.begin_nested():
                conn.exec_driver_sql(change)
                admit_native(conn, (target,))
        with conn.begin_nested() as savepoint:
            changed = target.statements[0].replace("'stable'", "'changed'")
            assert changed != target.statements[0]
            execute_native_sql(conn, changed)
            assert conn.exec_driver_sql('SELECT * FROM "native test".selected(3)').all() == [
                (3, "changed")
            ]
            assert body_differs(descriptor) is True
            with pytest.raises(NativeAuthoringError, match="body"):
                admit_native(conn, (target,))
            savepoint.rollback()
        forged = deepcopy(payload)
        forged["version"] = 1
        with pytest.raises(NativeAuthoringError, match="v1 frozen"):
            NativeTransitionOp.from_payload(forged)
        forged = deepcopy(payload)
        assert forged["after"] is not None
        forged["after"]["catalog"]["body_profile"] = "unsupported-profile"
        with pytest.raises(NativeAuthoringError, match="unsupported frozen"):
            NativeTransitionOp.from_payload(forged)
        # OIDs are different after recreation, but the declared symbolic profile
        # compares the same bound function/table-column meaning.
        with conn.begin_nested() as savepoint:
            conn.exec_driver_sql('DROP FUNCTION "native test".selected(integer)')
            conn.exec_driver_sql('DROP TABLE "native test".items')
            md.create_all(conn)
            conn.execute(items.insert(), [{"n": 1}, {"n": 2}, {"n": 3}])
            NativeTransitionOp.native_transition(
                operations, NativeTransitionOp(None, target).payload()
            )
            admit_native(conn, (target,))
            assert conn.exec_driver_sql('SELECT * FROM "native test".selected(3)').all() == [
                (3, "stable")
            ]
            savepoint.rollback()
        transaction.rollback()
    with semantic_bare_engine.connect() as conn:
        assert conn.scalar(text("""SELECT to_regnamespace('"native test"')""")) is None


def test_unbound_sql_standard_body_cannot_author_native_admission():
    from corpus_structure.semantic.migrations import ALEMBIC_DIR
    from corpus_structure.semantic.source_view_native import native_admission_sql

    source = """CREATE OR REPLACE FUNCTION ops.unbound_preview() RETURNS integer
LANGUAGE sql BEGIN ATOMIC SELECT 1; END;"""
    frozen = ALEMBIC_DIR.joinpath("versions/semantic_0065_admission.sql").read_text()
    with pytest.raises(ValueError, match="server-bound normalized native object"):
        native_admission_sql(source, base_admission=frozen)


def test_current_release_guards_refuse_historical_archive_and_projection_compilers():
    from pathlib import Path

    from corpus_structure.semantic.native_products import function_bodies

    source = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    archive = function_bodies((source / "closure.sql").read_text())["sem.require_archive_bytes"]
    projection = function_bodies((source / "execution_projection_check.sql").read_text())[
        "sem.require_execution_projection"
    ]
    assert "document->>'format' IS DISTINCT FROM 'semantic-release-archive-3'" in archive
    assert "manifest->'profile'->>'compiler_version' IS DISTINCT FROM '14'" in archive
    assert "IS DISTINCT FROM '14' THEN RAISE EXCEPTION" in projection
    assert "THEN RETURN;" not in projection


def test_current_native_sources_own_release_guards_and_record_only_views(semantic_bare_engine):
    from corpus_structure.semantic.native_candidate import (
        series_native_definitions,
        series_predecessor_definitions,
    )

    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA sem")
        desired = series_native_definitions(conn)
        predecessor = series_predecessor_definitions(conn)
    wanted = {(item.identity.schema, item.identity.name): item for item in desired}
    previous = {(item.identity.schema, item.identity.name): item for item in predecessor}
    for name in ("require_archive_bytes", "require_execution_projection"):
        assert wanted["sem", name].sql != previous["sem", name].sql
        assert wanted["sem", name].owner == "corpus_sem_publisher"
        assert wanted["sem", name].grants == ()
    for name in (
        "pdf_selected_product",
        "pdf_published_item",
        "pdf_published_region",
        "pdf_published_coverage",
    ):
        assert "UNION" not in wanted["ops", name].sql
        assert "UNION" in previous["ops", name].sql
    assert ("ops", "legacy_integrated_source_context") not in wanted
