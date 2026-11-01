"""Independent SQL scalar/key vectors for the publication record cursor."""

import json
import struct

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication_native import pdf_record_logical_identity_sql
from corpus_structure.semantic.pdf_record_identity import canonical_scalar

from .test_pdf_staging import private_build as private_build


def test_publication_inline_and_key_spelling(semantic_db_engine):
    sql = pdf_record_logical_identity_sql()
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})
        for value in ('quoted"\\\n', "\u03b1😀\x7f", "", "a/b~c"):
            actual = conn.execute(
                text("SELECT ops.pdf_identity_ascii_string(:v)"), {"v": value}
            ).scalar_one()
            assert actual == json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        for value in (None, True, False, 1729, -23, "unicode \u03b1"):
            actual = conn.execute(
                text("SELECT ops.pdf_identity_inline(CAST(:v AS jsonb))"), {"v": json.dumps(value)}
            ).scalar_one()
            assert actual == canonical_scalar(value)
        actual = conn.execute(
            text("SELECT ops.pdf_identity_inline(CAST(:v AS jsonb))"),
            {"v": json.dumps({"native_float64": struct.pack(">d", -0.0).hex()})},
        ).scalar_one()
        assert actual == canonical_scalar(-0.0)


def test_publication_inline_refuses_non_scalar(semantic_db_engine):
    sql = pdf_record_logical_identity_sql()
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})
        for value in (
            [],
            {},
            {"native_float64": "bad"},
            {"native_float64": "0" * 16, "extra": 1},
            1.2,
        ):
            with conn.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match=r"scalar|binary64"):
                    conn.execute(
                        text("SELECT ops.pdf_identity_inline(CAST(:v AS jsonb))"),
                        {"v": json.dumps(value)},
                    )
                savepoint.rollback()


def test_actual_record_cursor_matches_independent_logical_fields(semantic_db_engine, private_build):
    from corpus_structure.semantic.pdf_record_identity import LogicalIdentity

    binding = dict(release_id=private_build.release_id, source_digest=private_build.source_digest)
    schema = "f" * 64
    expected = LogicalIdentity(schema, binding["release_id"], binding["source_digest"])
    expected.add_record("companion/health", "health", (("body", '{"ready":true}'), ("ordinal", 0)))
    expected.add_record(
        "document",
        "root",
        (
            ("mapping_profile", "pdf-native-records-v1"),
            ("contract_version", "pdf-native-records-v1"),
            ("native_schema_digest", schema),
            ("root_id", "n"),
        ),
    )
    expected.add_record(
        "membership",
        '["n","children",0]',
        (("parent_id", "n"), ("field_name", "children"), ("ordinal", 0), ("value", None)),
    )
    expected.add_record(
        "native",
        "n",
        (
            ("native_type", "TextItem"),
            ("family", "node"),
            ("children/kind", "array"),
            ("children/length", 1),
            ("note/value", -0.0),
            ("text/value", "hello"),
        ),
    )
    expected.add_record(
        "publication", "root", (("kind", "native"), ("recipe_digest", private_build.recipe_digest))
    )
    sql = pdf_record_logical_identity_sql()
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        # Before publication migration these two relations are not yet in the foundation.
        # Minimal identity-only tables let this independent protocol vector run against0064.
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS kb.pdf_record_companion(product_id text,"
            "revision_id text,family text,local_id text,body jsonb,ordinal bigint)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS kb.pdf_record_endpoint(product_id text,"
            "revision_id text,relation_id text,ordinal bigint,target_task_id bigint,"
            "target_product_key text,target_content_digest text,occurrence_id text,"
            "role text)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS ops.pdf_frozen_build(build_id text,"
            "frozen_digest text,kind text)"
        )
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})

        def execute(statement, parameters=None):
            query = statement.replace("'p'", "%(product)s").replace("'r'", "%(revision)s")
            for name in ("release", "source", "schema", "frozen"):
                query = query.replace(":" + name, "%(" + name + ")s")
            return conn.exec_driver_sql(
                query,
                {
                    "product": private_build.build_id,
                    "revision": private_build.build_id,
                    **(parameters or {}),
                },
            )

        execute(
            "INSERT INTO ops.pdf_frozen_build(build_id,frozen_digest,kind) "
            "VALUES ('p',:frozen,'native')",
            {"frozen": "0" * 64},
        )
        execute(
            "INSERT INTO ops.pdf_record_document VALUES ('p','r',:release,:source,"
            "'pdf-native-records-v1','pdf-native-records-v1',:schema,'n')",
            dict(release=binding["release_id"], source=binding["source_digest"], schema=schema),
        )
        execute(
            "INSERT INTO kb.pdf_record_native(product_id,revision_id,record_id,"
            "native_type,family,native_address,scalars_json,structure_json) VALUES "
            "('p','r','n','TextItem','node','#','{\"text\":\"hello\","
            '"note":{"native_float64":"8000000000000000"}}\','
            '\'{"fields":{"children":{"kind":"array","length":1}}}\')'
        )
        execute(
            "INSERT INTO kb.pdf_record_membership(product_id,revision_id,parent_id,"
            "field_name,ordinal,value_kind,scalar_json) VALUES ('p','r','n',"
            "'children',0,'scalar','null')"
        )
        execute(
            "INSERT INTO kb.pdf_record_companion(product_id,revision_id,family,"
            "local_id,body,ordinal) VALUES ('p','r','health','health',"
            "'{\"ready\":true}',0)"
        )
        actual = execute("SELECT ops.pdf_record_logical_identity('p','r')").scalar_one()
        assert actual == expected.pin().logical_digest
        # Operational allocations are not identity-bearing.
        assert execute("SELECT ops.pdf_record_logical_identity('p','r')").scalar_one() == actual
