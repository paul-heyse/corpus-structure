"""Independent cut and pre-hydration budget checks for structural inspection."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve import structural_products as reader


def bind(monkeypatch):
    monkeypatch.setattr(
        reader,
        "bind_completed_result",
        lambda *_: SimpleNamespace(
            completed_cut_id=9, prepared=SimpleNamespace(release_id="release")
        ),
    )


def test_foreign_cut_refuses_before_query(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    with pytest.raises(SemanticRefusal, match="exact completed cut"):
        reader.serve_structural_products(conn, reader.StructuralRequest(run_id=1, cut_id=8))
    conn.execute.assert_not_called()


def test_large_report_refuses_before_payload_hydration(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value = [{"id": 12, "origin_id": 3, "bytes": 2000}]
    with pytest.raises(SemanticRefusal, match="byte budget"):
        reader.serve_structural_products(conn, reader.StructuralRequest(run_id=1, max_bytes=1000))
    conn.scalar.assert_not_called()
    sql = str(conn.execute.call_args.args[0])
    assert "cut_task.cut_id" in sql and "origin.release_id" in sql


def test_empty_selected_population_is_not_source_completeness(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value = []
    result = reader.serve_structural_products(conn, reader.StructuralRequest(run_id=1))
    assert result.reports == () and result.next_after_task_id is None
    assert result.source_coverage == "declared_report_inputs_only"
    assert result.standing == "private_proposals"
