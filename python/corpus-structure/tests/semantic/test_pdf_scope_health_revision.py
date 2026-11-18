"""Published health and byte comparisons use exact physical placement."""

from hashlib import sha256

from pglast import ast

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.pdf_publication_native import publication_sql
from corpus_structure.semantic.pdf_publication_read_native import pdf_reference_bytes_equal_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_scope_health_does_not_read_other_revision_health_or_formula_rows(infrastructure_rollback):
    prepared = prepare_sql(publication_sql(), source="current PDF publication")
    declaration = next(
        prepared.excerpt(index)
        for index, raw in enumerate(prepared.statements)
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
        and tuple(part.sval for part in raw.stmt.funcname or ())
        == ("ops", "pdf_record_scope_health")
    )
    conn = infrastructure_rollback
    tx = conn.begin_nested()
    conn.exec_driver_sql("CREATE SCHEMA ops")
    conn.exec_driver_sql("CREATE SCHEMA kb")
    conn.exec_driver_sql(
        "CREATE TABLE ops.pdf_published_revision("
        "build_id text,task_id bigint,product_key text,logical_digest text)"
    )
    conn.exec_driver_sql(
        "CREATE TABLE kb.pdf_record_companion("
        "product_id text,revision_id text,family text,local_id text,"
        "ordinal bigint,body jsonb)"
    )
    conn.exec_driver_sql(declaration)
    conn.exec_driver_sql(
        "INSERT INTO ops.pdf_published_revision VALUES('build',7,'integrated','digest')"
    )
    conn.exec_driver_sql("""INSERT INTO kb.pdf_record_companion VALUES
 ('build','other','health','health',0,'{"source_scope":"whole","quality":"wrong"}'),
 ('build','build','native_metadata','outcome',1,
 '{"kind":"formula_outcomes","pointer":"#/texts/1","outcome":"unknown"}'),
 ('build','other','native_metadata','other-outcome',2,
 '{"kind":"formula_outcomes","pointer":"#/texts/1","outcome":"success"}')""")
    query = "SELECT ops.pdf_record_scope_health(7,'integrated','digest',ARRAY['#/texts/1'])"
    assert conn.exec_driver_sql(query).scalar_one() is None
    conn.exec_driver_sql("""INSERT INTO kb.pdf_record_companion VALUES
 ('build','build','health','health',0,'{"source_scope":"whole","quality":"current"}')""")
    assert conn.exec_driver_sql(query).scalar_one() == {
        "quality": "current",
        "formula_outcomes": [{"pointer": "#/texts/1", "outcome": "unknown"}],
    }
    tx.rollback()


def test_reference_byte_equality_requires_both_root_and_exact_scoped_length(
    infrastructure_rollback,
):
    conn = infrastructure_rollback
    conn.exec_driver_sql("CREATE SCHEMA ops")
    conn.exec_driver_sql(
        "CREATE FUNCTION ops.pdf_identity_byte_root(bytes bytea) RETURNS bytea "
        "LANGUAGE sql IMMUTABLE RETURN sha256(bytes)"
    )
    conn.exec_driver_sql(
        "CREATE TABLE ops.pdf_artifact_stream(product_id text,revision_id text,"
        "stream_id text,byte_length bigint,byte_root text)"
    )
    root = sha256("β".encode()).hexdigest()
    conn.exec_driver_sql(
        "INSERT INTO ops.pdf_artifact_stream VALUES "
        "('b','b','stored',2,%s),('b','b','wrong-length',3,%s),('b','other','foreign',2,%s)",
        (root, root, root),
    )
    execute_native_sql(conn, pdf_reference_bytes_equal_sql(metadata))
    statement = "SELECT ops.pdf_reference_bytes_equal('b','b','β',NULL,%s,%s)"
    for text, stream, equal in (
        ("β", None, True),
        ("λ", None, False),
        (None, "stored", True),
        (None, "wrong-length", False),
        (None, "foreign", False),
        (None, None, False),
    ):
        assert conn.exec_driver_sql(statement, (text, stream)).scalar_one() is equal


def test_sealed_projection_uses_catalog_row_shape_and_actual_fence(infrastructure_rollback):
    import json

    import pytest
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.pdf_publication_read_native import pdf_publication_projection_sql

    conn = infrastructure_rollback
    conn.exec_driver_sql("""
CREATE SCHEMA ops;
CREATE SCHEMA kb;
CREATE TABLE ops.pdf_published_revision(
 kind text, recipe_digest text, schema_digest text, source_digest text, release_id text,
 frozen_digest text, logical_digest text, product_key text, task_id bigint, build_id text);
CREATE TABLE ops.pdf_stage_build(
 state text, recipe_digest text, schema_digest text, source_digest text, release_id text,
 holder text, attempt bigint, task_id bigint, build_id text);
CREATE TABLE ops.pdf_build_validation(
 build_id text, certification_basis text, lowering_identity text, attested_logical_digest text,
 native_document_digest text, oracle_receipt_id text, frozen_digest text,
 native_callbacks boolean, logical_digest text, native_contract_digest text);
CREATE TABLE ops.pdf_frozen_build(build_id text, kind text, frozen_digest text);
CREATE TABLE kb.pdf_record_companion(product_id text, revision_id text, family text, body jsonb);
CREATE TABLE kb.document(id bigint, key text);
CREATE FUNCTION ops.pdf_task_context(task bigint)
 RETURNS TABLE(document_id bigint, release_id text, source_digest text)
 LANGUAGE sql AS 'SELECT 9::bigint, ''release'', ''source'' WHERE task=7';
CREATE FUNCTION ops.pdf_spool_contributors(build text) RETURNS jsonb
 LANGUAGE sql RETURN '[]'::jsonb;
CREATE FUNCTION ops.pdf_validation_contract(release text) RETURNS text
 LANGUAGE sql RETURN 'contract'::text;
INSERT INTO ops.pdf_published_revision VALUES
 ('native','recipe','schema','source','release','frozen','logical','key',7,'build');
INSERT INTO ops.pdf_stage_build VALUES
 ('published','recipe','schema','source','release','sealed-owner',2,7,'build');
INSERT INTO ops.pdf_build_validation VALUES
 ('build','producer-certified','lowering','logical','document','oracle','frozen',true,'logical','contract');
INSERT INTO ops.pdf_frozen_build VALUES ('build','native','frozen');
INSERT INTO kb.document VALUES (9,'registered-key');
INSERT INTO kb.pdf_record_companion VALUES
 ('build','wrong-revision','health','{"conversion":"wrong"}'),
 ('build','build','health','{"conversion":"success","display_coverage":"complete"}');
""")
    execute_native_sql(conn, pdf_publication_projection_sql(metadata))
    publication = conn.exec_driver_sql(
        "SELECT to_jsonb(p) FROM ops.pdf_published_revision p"
    ).scalar_one()
    receipt = {
        "publication": publication,
        "publisher_attempt": 2,
        "publisher_holder": "sealed-owner",
        "contributors": [],
        "certification": {
            "basis": "producer-certified",
            "lowering_identity": "lowering",
            "attested_logical_digest": "logical",
            "native_document_digest": "document",
            "oracle_receipt_id": "oracle",
        },
    }
    statement = "SELECT ops.pdf_publication_projection(%s::jsonb,7,3,'current-owner')"
    assert conn.exec_driver_sql(statement, (json.dumps(receipt),)).scalar_one() == {
        "document": "registered-key",
        "source_digest": "source",
        "schema_digest": "schema",
        "recipe_digest": "recipe",
        "logical_digest": "logical",
        "kind": "native",
        "health": {
            "conversion": "success",
            "display_coverage": "complete",
            "inline_coverage": None,
            "cell_coverage": None,
        },
    }
    with (
        pytest.raises(DBAPIError, match="differs from actual sealed publisher"),
        conn.begin_nested(),
    ):
        conn.exec_driver_sql(statement, (json.dumps(receipt | {"publisher_attempt": 1}),))
