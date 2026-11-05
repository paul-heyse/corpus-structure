"""Independent local-event expectations; exact quotes do not establish roles."""

from dataclasses import replace

import pytest
from methods.test_record_assembly import context, release, report, span

from corpus_structure.methods.contribution_adapter import adapt_report
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.semantic.local_admission import (
    exact_source_event,
    local_assertion_support,
    project_local_assertions,
)


def source_report():
    prepared = release()
    ctx = context("term")
    pack = family_pack(prepared, contract="DefinitionRecordFields", anchor_role="term")
    batch = adapt_report(
        report(ctx, pack, "definition", [{"term": span(0, 4, "term")}]),
        ctx,
        pack=pack,
        item_key="actual",
    )
    return prepared, dict(
        selected_task_id=10,
        origin_task_id=9,
        cut_id=7,
        source="source",
        contributions=batch.contributions,
        contribution_operations=batch.operations,
    )


def test_exact_local_claims_preserve_quote_grain_and_do_not_claim_definition_role():
    prepared, report = source_report()
    rows = project_local_assertions(prepared, (report,))
    assert {row.event for row in rows} == {"source_occurrence", "source_literal_quote"}
    assert len(rows) == 2
    for row in rows:
        support = local_assertion_support(row)
        assert support["literal_pieces"] == ["term"]
        assert support["standing"] == "admitted_local_source_claim"
        assert support["interpretation"] == "not_established_by_local_publication"
        assert support["scientific_support"] == "unmodeled"
        assert "semantic_type" not in support and "score" not in support
    other = project_local_assertions(
        prepared, (dict(report, selected_task_id=11, origin_task_id=12),)
    )
    assert {row.claim_id for row in rows} == {row.claim_id for row in other}
    assert {row.assertion_id for row in rows}.isdisjoint(row.assertion_id for row in other)


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "relation"},
        {"anchor_role": "inspection_subject"},
        {"occurrence_id": None},
        {"anchors": ()},
    ],
)
def test_unlocated_or_stronger_events_cannot_consume_coordinate_proof(change):
    _, report = source_report()
    occurrence = next(row for row in report["contributions"] if row["kind"] == "occurrence")
    assert exact_source_event(dict(occurrence, **change)) is None


def test_item_level_or_captured_mapping_is_not_exact_native_proof():
    _, report = source_report()
    occurrence = next(row for row in report["contributions"] if row["kind"] == "occurrence")
    (anchor,) = occurrence["anchors"]
    for change in (
        {"precision": "item"},
        {"space": "selected_projection"},
        {"source_piece": "wrong"},
    ):
        assert exact_source_event(dict(occurrence, anchors=(dict(anchor, **change),))) is None


def test_contribution_only_cut_publishes_local_quote_without_record_projection(monkeypatch):
    from corpus_structure.semantic import record_assertions
    from corpus_structure.semantic.domain_operations import _project_cut

    from .test_semantic_reason_producers import release as composed_release

    _, report = source_report()
    prepared = composed_release()
    prepared = replace(
        prepared,
        artifacts=tuple(
            artifact for artifact in prepared.artifacts if artifact.kind != "record_projection.json"
        ),
    )
    assert not any(artifact.kind == "record_projection.json" for artifact in prepared.artifacts)
    monkeypatch.setattr(
        record_assertions,
        "lower_record_assertions",
        lambda *_: pytest.fail("local source claim required whole-record lowering"),
    )
    job = dict(
        id=1,
        project_id="local-only",
        release_id=prepared.release_id,
        input_realization_id="input",
        input_revision=0,
    )
    projected = _project_cut(
        prepared,
        job,
        {"id": 7},
        [],
        {},
        [],
        [],
        "local-only-output",
        {},
        {},
        record_reports=(report,),
    )
    assert not projected.batch.source_record and not projected.batch.record_assertion
    assert {row.event for row in projected.batch.local_assertion} == {
        "source_occurrence",
        "source_literal_quote",
    }
    assert {row.literal_pieces_json for row in projected.batch.local_assertion} == {'["term"]'}
