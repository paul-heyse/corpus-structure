"""Pure structural controls for the statement boundary; native tests own semantics."""

from typing import cast

from sqlalchemy import Connection
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic.data_operation_bindings import (
    binding_statement,
    compile_binding,
)
from corpus_structure.semantic.data_operation_model import BindingExpression
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    admitted_data_projection,
)
from semantic.test_data_operation_bindings import model


def test_binding_statement_materializes_role_selections_and_decodes_context_only_at_output(
    monkeypatch,
):
    target = model(BindingExpression("scan", roles=("left", "right")), names=("left", "right"))
    monkeypatch.setattr(
        DataOperationStorage,
        "acquire_data_read_context",
        lambda *_args: dict(
            read_id="read:controlled",
            trust_snapshot={},
            selection={},
            read_snapshot="1:2:",
            frontier_at="now",
        ),
    )
    projections = admitted_data_projection(
        cast(Connection, object()),
        "demand:controlled",
        "urn:op",
        {},
        target,
        read_id="read:controlled",
    )
    compiled = compile_binding(target, "urn:op", projections, subject="doc")
    statement = binding_statement(compiled)
    assert statement is not None
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert sql.count("ops.data_binding_rows(") == 1
    assert sql.count(" AS MATERIALIZED") == 3
    assert sql.count("SELECT DISTINCT") == 2
    assert sql.count("CAST(binding_output.") == 2
    assert "CAST(binding_output.analyzed_scope AS" in sql
    assert "CAST(binding_output.support_evidence AS" in sql
    assert "UNION ALL" in sql and "ORDER BY binding_output.binding_kind" in sql
    # Wide semantic predicate fields remain available to DISTINCT and checks,
    # while the outer transport exposes only decoder-owned member facts.
    assert "body" not in statement.selected_columns
    assert "meaning_body" not in statement.selected_columns
