"""Retained report admission must not cap the independently owned source closure."""

from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from methods.test_m1_producer import view

from corpus_structure.semantic import releases, source_views
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourcePin
from corpus_structure.semantic.types import PreparedRelease


@pytest.mark.parametrize("explicit_budget", [False, True])
def test_retained_report_and_native_source_keep_their_budget_scope(monkeypatch, explicit_budget):
    original_view = view()
    current_view = replace(original_view, ref=replace(original_view.ref, id=90, key="current-view"))
    caller_budget = PublishedReadBudget(64, 32 * 1024**2) if explicit_budget else None
    body = dict(
        release_id="old-release",
        method="extract.m1_candidates",
        input_hash="retained-input",
        configuration_hash="retained-config",
        unit_key=original_view.ref.key,
        source=original_view.ref.key,
        parse_detail=source_value(
            dict(
                source_pin=asdict(
                    NativeSourcePin.from_source(native_source_frame(original_view, ()))
                ),
                contexts=[],
            )
        ),
    )

    def mapped(value):
        result = Mock()
        result.mappings.return_value.one_or_none.return_value = value
        return result

    summary = Mock()
    summary.one.return_value = SimpleNamespace(rows=1, bytes=1000, largest=1000)
    project = Mock()
    project.scalar_one.return_value = "project"
    conn = Mock()
    conn.execute.side_effect = [
        mapped(dict(id=37, reused_task_id=None, run_id=14)),
        summary,
        mapped(
            dict(
                run_id=14,
                release_id="old-release",
                origin_project="project",
                method_name="extract.m1_candidates",
                unit_type="source_view",
                unit_id=original_view.ref.id,
                unit_key=original_view.ref.key,
                input_hash="retained-input",
                config_hash="retained-config",
                producer_configuration={},
                body=body,
            )
        ),
        project,
        project,
    ]
    source_budgets = []

    def source_view(reader, identity):
        if reader.run_id == 14:
            source_budgets.append(reader.read_budget)
            # A source companion needing 32 rows is valid under source defaults
            # or the explicit caller budget, and refuses the report-local 16 cap.
            if reader.read_budget is not None and reader.read_budget.max_rows < 32:
                raise ValueError("source companion exceeds requested row budget")
            return original_view
        return current_view

    selection_budgets = []

    def selected(conn, run_id, *, read_budget):
        selection_budgets.append(read_budget)
        return (current_view.ref,)

    monkeypatch.setattr(BoundReader, "source_view", source_view)
    monkeypatch.setattr(source_views, "selected_source_views", selected)
    monkeypatch.setattr(
        releases, "open_release", lambda *_: Mock(spec=PreparedRelease, release_id="old-release")
    )
    observed_report_limits = []
    preflight = PublishedReadBudget.preflight

    def admit(budget, connection, query, **kwargs):
        observed_report_limits.append((budget.max_rows, budget.max_bytes))
        return preflight(budget, connection, query, **kwargs)

    monkeypatch.setattr(PublishedReadBudget, "preflight", admit)
    reader = BoundReader(
        conn,
        99,
        Mock(spec=PreparedRelease, release_id="current-release"),
        read_budget=caller_budget,
    )
    result = reader.retained_source_result(current_view.ref.id, 37, "extract.m1_candidates")
    assert result.result["input_hash"] == "retained-input"
    assert source_budgets and all(budget is caller_budget for budget in source_budgets)
    assert selection_budgets == [caller_budget]
    assert observed_report_limits == [
        (caller_budget.max_rows, caller_budget.max_bytes) if caller_budget else (16, 16_777_216)
    ]
