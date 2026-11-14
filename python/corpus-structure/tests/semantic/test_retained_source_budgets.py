"""Retained report admission must not cap the independently owned source closure."""

from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from methods.m1_producer_support import view

from corpus_structure.semantic import releases, source_views
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import BoundReader, OperationConflict
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import ReadLimit
from corpus_structure.semantic.source_contexts import NativeSourcePin
from corpus_structure.semantic.types import PreparedRelease


@pytest.mark.parametrize("narrow", [False, True])
def test_normal_upstream_result_uses_same_large_fallback_and_explicit_refusal(monkeypatch, narrow):
    source = view()
    caller_budget = PublishedReadBudget(16, 1024**2) if narrow else None
    body = dict(
        release_id="current-release",
        method="extract.m1_candidates",
        input_hash="upstream-input",
        configuration_hash="upstream-config",
        unit_key=source.ref.key,
        source=source.ref.key,
        payload="x" * 28_070_287,
        parse_detail=source_value(dict(marker="retained")),
    )
    size = len(canonical_bytes(body))
    summary = Mock()
    summary.one.return_value = SimpleNamespace(rows=1, bytes=size, largest=size)
    payload = Mock()
    payload.mappings.return_value = (
        dict(
            body=body,
            release_id="current-release",
            input_hash="upstream-input",
            unit_key=source.ref.key,
            config_hash="upstream-config",
        ),
    )
    conn = Mock()
    conn.execute.side_effect = (summary, payload)
    source_budgets = []

    def source_view(reader, identity):
        source_budgets.append(reader.read_budget)
        return source

    monkeypatch.setattr(BoundReader, "source_view", source_view)
    reader = BoundReader(
        conn,
        99,
        Mock(spec=PreparedRelease, release_id="current-release"),
        read_budget=caller_budget,
    )
    if narrow:
        with pytest.raises(ReadLimit, match="byte budget"):
            reader.source_result(source.ref.id, "extract.m1_candidates")
        assert conn.execute.call_count == 1  # Only scalar length/count preflight crossed.
    else:
        result = reader.source_result(source.ref.id, "extract.m1_candidates")
        assert result is not None
        assert result["payload"] == body["payload"]
        assert result["parse_detail"] == dict(marker="retained")
    assert source_budgets == [caller_budget]


@pytest.mark.parametrize("explicit_budget", [False, True, "narrow"])
def test_retained_report_and_native_source_keep_their_budget_scope(monkeypatch, explicit_budget):
    original_view = view()
    current_view = replace(original_view, ref=replace(original_view.ref, id=90, key="current-view"))
    caller_budget = (
        PublishedReadBudget(64, (1 if explicit_budget == "narrow" else 32) * 1024**2)
        if explicit_budget
        else None
    )
    body = dict(
        release_id="old-release",
        method="extract.m1_candidates",
        input_hash="retained-input",
        configuration_hash="retained-config",
        unit_key=original_view.ref.key,
        source=original_view.ref.key,
        retained_payload="x" * (28_070_287 if explicit_budget is False else 2 * 1024**2),
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
    body_bytes = len(canonical_bytes(body))
    summary.one.return_value = SimpleNamespace(rows=1, bytes=body_bytes, largest=body_bytes)
    project = Mock()
    project.scalar_one.return_value = "project"
    conn = Mock()
    conn.execute.side_effect = [
        mapped(dict(id=37, reused_task_id=None, run_id=14)),
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
            )
        ),
        project,
        project,
        summary,
        mapped(dict(body=body, producer_configuration={})),
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
    monkeypatch.setattr(
        BoundReader,
        "source_view_ref",
        lambda reader, identity: original_view.ref if reader.run_id == 14 else current_view.ref,
    )
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
    if explicit_budget == "narrow":
        with pytest.raises(ReadLimit, match="byte budget"):
            reader.retained_source_result(current_view.ref.id, 37, "extract.m1_candidates")
        assert conn.execute.call_count == 5  # Refused by preflight before body transfer.
    else:
        result = reader.retained_source_result(current_view.ref.id, 37, "extract.m1_candidates")
        assert result.result["input_hash"] == "retained-input"
    assert source_budgets and all(budget is caller_budget for budget in source_budgets)
    assert selection_budgets == ([] if explicit_budget == "narrow" else [caller_budget])
    assert observed_report_limits == [
        (caller_budget.max_rows, caller_budget.max_bytes) if caller_budget else (16, 64 * 1024**2)
    ]


@pytest.mark.parametrize(
    "mismatch", ["project", "requested_project", "method", "unit", "physical", "projection"]
)
def test_unrelated_metadata_refuses_before_report_budget_or_body(monkeypatch, mismatch):
    original = view()
    current = replace(original, ref=replace(original.ref, id=90, key="current-view"))
    if mismatch == "physical":
        current = replace(current, ref=replace(current.ref, section_pointer="#/different"))
    if mismatch == "projection":
        current = replace(current, text="different retained projection")
    metadata = dict(
        run_id=14,
        release_id="old-release",
        origin_project="project",
        method_name="extract.m1_candidates",
        unit_type="source_view",
        unit_id=original.ref.id,
    )
    if mismatch in {"project", "method", "unit"}:
        metadata[
            dict(project="origin_project", method="method_name", unit="unit_type")[mismatch]
        ] = "different"

    def mapped(value):
        result = Mock()
        result.mappings.return_value.one_or_none.return_value = value
        return result

    def scalar(value):
        result = Mock()
        result.scalar_one.return_value = value
        return result

    conn = Mock()
    conn.execute.side_effect = [
        mapped(dict(reused_task_id=None, run_id=14)),
        mapped(metadata),
        scalar("project"),
        scalar("different" if mismatch == "requested_project" else "project"),
    ]
    monkeypatch.setattr(
        BoundReader,
        "source_view_ref",
        lambda reader, identity: original.ref if reader.run_id == 14 else current.ref,
    )
    monkeypatch.setattr(
        BoundReader,
        "source_view",
        lambda reader, identity: original if reader.run_id == 14 else current,
    )
    monkeypatch.setattr(
        releases, "open_release", lambda *_: Mock(spec=PreparedRelease, release_id="old-release")
    )
    preflight = Mock(side_effect=AssertionError("unrelated report reached byte preflight"))
    monkeypatch.setattr(PublishedReadBudget, "preflight", preflight)
    with pytest.raises(OperationConflict):
        BoundReader(conn, 99, Mock(spec=PreparedRelease)).retained_source_result(
            90, 37, "extract.m1_candidates"
        )
    preflight.assert_not_called()
    # Only compact task/config/source metadata was selected, never the JSON result.
    for call in conn.execute.call_args_list:
        assert all(column.name != "body" for column in call.args[0].selected_columns)
