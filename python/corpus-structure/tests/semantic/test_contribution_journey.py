"""Independent population/cursor controls for the contribution serving boundary."""

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic.contribution_queries import ContributionInventory
from corpus_structure.semantic.query import SnapshotBinding
from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal
from corpus_structure.serve import contributions as journey


@dataclass
class Session:
    completed_cut_id: int = 4
    binding: SnapshotBinding = field(
        default_factory=lambda: SnapshotBinding("release", "realization", 2, "capture")
    )
    prepared: object = None


@pytest.fixture
def inventory(monkeypatch):
    monkeypatch.setattr(journey, "bind_completed_result", lambda *_: Session())
    # Deliberately independent fields: an empty operation still exists with no product.
    data = ContributionInventory(
        ({"selected_task_id": 1, "cut_member": True},),
        ({"operation_key": "empty", "emitted_count": 0},),
        ({"contribution_id": "located", "source_piece": "12"},),
        False,
    )
    calls = []

    def read(*args, **kwargs):
        calls.append(kwargs)
        return data

    monkeypatch.setattr(journey, "read_source_contributions", read)
    return calls


def test_pages_preserve_distinct_populations_and_empty_operation(inventory):
    first = journey.serve_contributions(
        MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, limit=1)
    )
    assert first.items == (
        {"population": "report", "row": {"selected_task_id": 1, "cut_member": True}},
    )
    second = journey.serve_contributions(
        MagicMock(spec=Connection),
        journey.ContributionRequest(run_id=7, limit=1, cursor=first.next_cursor),
    )
    assert second.items[0]["row"] == {"operation_key": "empty", "emitted_count": 0}
    last = journey.serve_contributions(
        MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, cursor=second.next_cursor)
    )
    assert last.items[0]["row"] == {"contribution_id": "located", "source_piece": "12"}
    assert last.population_paging_complete and last.next_cursor is None
    assert last.standing == "retained_private"
    assert last.scientific_support == "unmodeled"
    assert last.assessment == "not_included"
    assert inventory[0]["cut_id"] == 4


def test_changed_selection_refuses_before_inventory_hydration(inventory):
    first = journey.serve_contributions(
        MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, limit=1)
    )
    with pytest.raises(SemanticRefusal):
        journey.serve_contributions(
            MagicMock(spec=Connection),
            journey.ContributionRequest(run_id=7, method="changed", cursor=first.next_cursor),
        )
    assert len(inventory) == 1


def test_publication_facet_change_invalidates_private_cursor_before_hydration(inventory):
    first = journey.serve_contributions(
        MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, limit=1)
    )
    with pytest.raises(SemanticRefusal):
        journey.serve_contributions(
            MagicMock(spec=Connection),
            journey.ContributionRequest(
                run_id=7, cursor=first.next_cursor, include_publication=True
            ),
        )
    assert len(inventory) == 1
    with pytest.raises(ValueError, match="publication facet"):
        journey.ContributionRequest(run_id=7, include_support=True)


def test_population_limit_and_response_budget_refuse(inventory, monkeypatch):
    with pytest.raises(SemanticRefusal, match="page byte"):
        journey.serve_contributions(
            MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, page_bytes=1)
        )
    monkeypatch.setattr(
        journey,
        "read_source_contributions",
        lambda *a, **k: ContributionInventory((), (), (), True),
    )
    with pytest.raises(SemanticRefusal, match="10000"):
        journey.serve_contributions(
            MagicMock(spec=Connection), journey.ContributionRequest(run_id=7)
        )


def test_malformed_cursor(inventory):
    with pytest.raises(InvalidContinuation):
        journey.serve_contributions(
            MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, cursor="bad")
        )


def test_unknown_facets_cannot_request_admitted_or_assessed_standing():
    with pytest.raises(ValueError):
        journey.ContributionRequest.model_validate(dict(run_id=7, standing="accepted"))


@pytest.mark.parametrize(
    "change",
    [
        dict(operation_version="2"),
        dict(contribution_id="other"),
        dict(occurrence_id="other"),
        dict(include_interpretation=True),
        dict(include_assessment=True),
    ],
)
def test_v3_selection_is_bound_before_hydration(inventory, change):
    first = journey.serve_contributions(
        MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, limit=1)
    )
    with pytest.raises(SemanticRefusal):
        journey.serve_contributions(
            MagicMock(spec=Connection),
            journey.ContributionRequest(run_id=7, cursor=first.next_cursor, **change),
        )
    assert len(inventory) == 1


def test_old_release_interpretation_and_absent_public_assessment_do_not_read_private_grades(
    monkeypatch,
):
    session = Session(prepared=SimpleNamespace(index=SimpleNamespace(definitions={})))
    monkeypatch.setattr(journey, "bind_completed_result", lambda *_: session)
    contribution = dict(
        contribution_id="cid",
        selected_task_id=1,
        origin_task_id=1,
        operation_key="op",
        semantic_type="number",
        disposition="proposed",
        value={"kind": "integer", "integer": 12},
        members=("source",),
        endpoints=(),
        computation_dependencies=("derivation",),
    )
    monkeypatch.setattr(
        journey,
        "read_source_contributions",
        lambda *a, **k: ContributionInventory((), (), (contribution,), False, (contribution,)),
    )
    conn = MagicMock(spec=Connection)
    page = journey.serve_contributions(
        conn,
        journey.ContributionRequest(run_id=7, include_interpretation=True, include_assessment=True),
    )
    assessment = next(
        item["row"]
        for item in page.model_dump(mode="json")["items"]
        if item["population"] == "assessment"
    )
    assert assessment["outcome"] == "no_public_assessment" and assessment["witnesses"] == []
    meaning = next(
        item["row"]
        for item in page.model_dump(mode="json")["items"]
        if item["population"] == "interpretation"
    )
    assert meaning["value"] == contribution["value"] and meaning["members"] == ["source"]
    assert (
        page.publication == "not_included"
        and page.assessment_scope == "published_admission_witnesses_only"
    )
    conn.execute.assert_not_called()


def test_selected_export_is_atomic_bounded_and_not_a_review_bundle(inventory, tmp_path):
    destination = tmp_path / "selection"
    manifest = journey.export_contribution_selection(
        MagicMock(spec=Connection), journey.ContributionRequest(run_id=7), destination
    )
    assert len((destination / "items.jsonl").read_text().splitlines()) == 3
    assert json.loads((destination / "manifest.json").read_bytes())["sha256"] == manifest["sha256"]
    assert "not a self-contained" in manifest["scope"]
    with pytest.raises(FileExistsError):
        journey.export_contribution_selection(
            MagicMock(spec=Connection), journey.ContributionRequest(run_id=7), destination
        )
    refused = tmp_path / "refused"
    with pytest.raises(SemanticRefusal):
        journey.export_contribution_selection(
            MagicMock(spec=Connection), journey.ContributionRequest(run_id=7, max_bytes=1), refused
        )
    assert not refused.exists()
