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


def test_file_export_budget_preserves_interactive_cap_and_exact_selection(monkeypatch):
    from pydantic import ValidationError

    from semantic.test_structural_admission import definition

    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value = [
        {"id": 12, "origin_id": 3, "bytes": 9_000_000}
    ]
    with pytest.raises(ValidationError):
        reader.StructuralRequest(run_id=1, max_bytes=16_000_000)
    with pytest.raises(SemanticRefusal, match="byte budget"):
        reader.serve_structural_products(
            conn, reader.StructuralRequest(run_id=1, cut_id=9, max_bytes=8_000_000)
        )
    conn.scalar.assert_not_called()
    expected = definition()
    conn.scalar.return_value = expected.model_dump(mode="json")
    exported = reader.read_structural_export_page(
        conn, reader.StructuralExportRequest(run_id=1, cut_id=9, max_bytes=16_000_000)
    )
    assert exported.task_ids == (12,) and exported.cut_id == 9
    assert exported.reports == (expected,)
    assert exported.standing == "private_proposals"


def test_empty_selected_population_is_not_source_completeness(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value = []
    result = reader.serve_structural_products(conn, reader.StructuralRequest(run_id=1))
    assert result.reports == () and result.next_after_task_id is None
    assert result.source_coverage == "declared_report_inputs_only"
    assert result.standing == "private_proposals"


def dossier_metadata():
    return dict(
        origin_id=3,
        product_id="structural:exact",
        policy="supported-facet-greedy-1",
        membership_digest="a" * 64,
        facet_digest="b" * 64,
        mandatory_overflow=True,
        selected_count=3,
        full_member_count=5,
        omitted_member_count=2,
        missing_facet_count=1,
    )


def test_dossier_page_budget_checks_selected_projection_before_hydration(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value.one_or_none.return_value = dossier_metadata()
    conn.scalar.return_value = 2000
    with pytest.raises(SemanticRefusal, match="byte budget"):
        reader.serve_dossier_representation(
            conn, reader.DossierRepresentationRequest(run_id=1, task_id=12, max_bytes=1000)
        )
    assert conn.scalar.call_count == 1
    sql = str(conn.scalar.call_args.args[0])
    assert "octet_length(body::text)" in sql
    assert "ord>:offset" in sql and "ord<=:end_offset" in sql


def test_dossier_page_continuation_is_bound_before_selected_payload_read(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value.one_or_none.return_value = dossier_metadata()
    cursor = reader.DossierContinuation(
        product_id="another",
        membership_digest="a" * 64,
        facet_digest="b" * 64,
        policy="supported-facet-greedy-1",
        offset=2,
    )
    with pytest.raises(SemanticRefusal, match="continuation differs"):
        reader.serve_dossier_representation(
            conn, reader.DossierRepresentationRequest(run_id=1, task_id=12, continuation=cursor)
        )
    conn.scalar.assert_not_called()


def test_dossier_page_returns_selected_members_and_exact_citations(monkeypatch):
    bind(monkeypatch)
    conn = MagicMock(spec=Connection)
    conn.execute.return_value.mappings.return_value.one_or_none.return_value = dossier_metadata()
    conn.scalar.side_effect = (
        100,
        dict(
            members=[dict(member_id="m")],
            citations=[dict(member_id="m", citation=dict(text="source"))],
            supported_facets=[],
        ),
    )
    page = reader.serve_dossier_representation(
        conn, reader.DossierRepresentationRequest(run_id=1, task_id=12, limit=1)
    )
    assert page.continuation is not None and page.continuation.offset == 1
    assert page.full_member_count == 5 and page.omitted_member_count == 2
    assert page.members[0]["member_id"] == "m" and page.citations[0]["citation"] == dict(
        text="source"
    )
    assert page.mandatory_overflow is True
