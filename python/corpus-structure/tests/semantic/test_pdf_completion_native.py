"""Completion proof declaration includes independent semantic outcome and producer custody."""

from pglast import ast

from corpus_structure.semantic.pdf_completion_native import pdf_completion_native_sql
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_pdf_completion_proof_is_closed_private_and_preserves_semantic_non_success():
    sql = pdf_completion_native_sql()
    prepared = prepare_sql(sql, source="PDF completion proof")
    function = prepared.statements[0].stmt
    assert isinstance(function, ast.CreateFunctionStmt)
    assert function.funcname is not None
    assert tuple(part.sval for part in function.funcname) == ("ops", "ddo_require_pdf_completion")
    assert len(prepared.statements) == 2
    assert "ops.ddo_completion_state(definition,p_completion->>'outcome')" in sql
    assert "ops.pdf_publication_projection(receipts->0,p_task,p_attempt,p_holder)" in sql
    assert "data.ddo_json(output->'product'->'body') IS DISTINCT FROM expected" in sql
    assert "jsonb_array_length(receipts)<>1" in sql
    assert "output->>'member_id' IS NOT NULL" in sql
    assert "FROM PUBLIC" in sql
    assert "GRANT" not in sql
