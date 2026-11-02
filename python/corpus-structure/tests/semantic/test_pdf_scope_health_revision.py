"""Published scope health uses both physical placement coordinates independently."""

from pglast import ast

from corpus_structure.semantic.pdf_publication_native import publication_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_scope_health_does_not_read_other_revision_health_or_formula_rows(semantic_bare_engine):
    prepared = prepare_sql(publication_sql(), source="current PDF publication")
    declaration = next(
        prepared.excerpt(index)
        for index, raw in enumerate(prepared.statements)
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
        and tuple(part.sval for part in raw.stmt.funcname or ())
        == ("ops", "pdf_record_scope_health")
    )
    with semantic_bare_engine.connect() as conn:
        tx = conn.begin()
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
