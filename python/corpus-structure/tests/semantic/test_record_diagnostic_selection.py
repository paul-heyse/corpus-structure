"""Bounded diagnostic selection controls; no live database/provider qualification."""

from dataclasses import replace
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection
from sqlalchemy.dialects import postgresql

from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import ReadLimit
from corpus_structure.semantic.record_queries import RecordReadLimit, _read_producer_coverage
from corpus_structure.semantic.refusals import WrongBinding
from corpus_structure.serve.record_export import write_record_relations
from corpus_structure.serve.record_results import RecordRequest, present_record_projection
from semantic.record_consumers_support import prepared as prepared
from semantic.record_consumers_support import projection as projection


def producer_row(diagnostics):
    return dict(
        selected_task_id=25,
        origin_task_id=25,
        cut_member=True,
        source_view_id=7,
        task_status="done",
        task_error=None,
        reason=None,
        unit_key="u",
        input_hash="input",
        config_hash="config",
        method="extract.m1_annotations",
        method_version="1",
        report_release_id="r",
        body_release_id="r",
        body_method="extract.m1_annotations",
        body_config_hash="config",
        body_input_hash="input",
        body_unit_key="u",
        source="u",
        outcome="produced",
        records_present=False,
        coverage=[],
        diagnostics=diagnostics,
        diagnostics_available=True,
        error=None,
    )


class Rows:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def mappings(self):
        return iter([self.row])


def test_default_record_page_omits_large_annotation_tokens_at_sql_boundary(projection, monkeypatch):
    encoded = source_value(dict(tokens="x" * (5 * 1024**2)))
    observed = []

    def expression(statement):
        return str(
            statement.selected_columns["diagnostics"].compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )

    def preflight(budget, conn, statement, **kwargs):
        sql = expression(statement)
        observed.append(sql)
        if "parse_detail" in sql:
            raise ReadLimit("complete actual diagnostic body exceeds budget", reason="work_limit")

    def execute(statement):
        assert "parse_detail" not in expression(statement)
        return Rows(producer_row(None))

    monkeypatch.setattr(PublishedReadBudget, "preflight", preflight)
    mock = MagicMock(spec=Connection)
    mock.execute.side_effect = execute
    conn = cast(Connection, mock)
    coverage = _read_producer_coverage(
        conn,
        run_id=41,
        release_id="r",
        cut_id=9,
        source_view_ids=None,
        max_rows=100,
        max_bytes=64 * 1024,
        include_diagnostics=False,
    )
    page = present_record_projection(
        replace(projection, coverage=coverage), RecordRequest(run_id=41)
    )
    assert page.coverage[0].diagnostics is None
    assert page.coverage[0].diagnostics_available and not page.coverage[0].diagnostics_included
    assert page.coverage[0].selected_task_id == 25
    assert len(page.model_dump_json().encode()) < 1024**2
    with pytest.raises(RecordReadLimit, match="coverage exceeds"):
        _read_producer_coverage(
            conn,
            run_id=41,
            release_id="r",
            cut_id=9,
            source_view_ids=None,
            max_rows=100,
            max_bytes=64 * 1024,
            include_diagnostics=True,
        )
    assert "parse_detail" in observed[-1]
    # Explicit presentation of an already detached full body remains bounded too.
    full = replace(
        coverage[0], diagnostics={"tokens": "x" * (5 * 1024**2)}, diagnostics_included=True
    )
    with pytest.raises(RecordReadLimit, match="response byte budget"):
        present_record_projection(
            replace(projection, coverage=(full,)),
            RecordRequest(run_id=41, include_diagnostics=True),
        )
    assert encoded["kind"] == "object"  # actual SourceValue shape, not a token-count surrogate


def test_diagnostic_choice_is_part_of_record_cursor_identity(projection):
    first = present_record_projection(projection, RecordRequest(run_id=41, limit=1))
    with pytest.raises(WrongBinding):
        present_record_projection(
            projection,
            RecordRequest(run_id=41, limit=1, cursor=first.next_cursor, include_diagnostics=True),
        )
    assert RecordRequest(run_id=41).include_diagnostics is False


def test_relation_export_uses_explicit_diagnostic_selection_without_losing_available_locator(
    projection, monkeypatch, tmp_path
):
    monkeypatch.setattr(PublishedReadBudget, "preflight", lambda *args, **kwargs: None)
    encoded = source_value(dict(tokens="actual controlled token body"))
    mock = MagicMock(spec=Connection)
    mock.execute.side_effect = lambda statement: Rows(producer_row(encoded))
    coverage = _read_producer_coverage(
        cast(Connection, mock),
        run_id=41,
        release_id="r",
        cut_id=9,
        source_view_ids=None,
        max_rows=100,
        max_bytes=64 * 1024,
    )
    detached = replace(projection, coverage=coverage)
    ordinary = tmp_path / "ordinary"
    detailed = tmp_path / "detailed"
    ordinary.mkdir()
    detailed.mkdir()
    before, _ = write_record_relations(detached, ordinary, projection.binding, format="jsonl")
    after, _ = write_record_relations(
        detached, detailed, projection.binding, format="jsonl", include_diagnostics=True
    )
    assert before["coverage"][0]["diagnostics"] is None
    assert before["coverage"][0]["diagnostics_available"]
    assert not before["coverage"][0]["diagnostics_included"]
    assert after["coverage"][0]["diagnostics"]["tokens"] == "actual controlled token body"
    assert after["coverage"][0]["diagnostics_included"]
    assert before["logical_digest"] != after["logical_digest"]
