"""Shared controlled inputs and builders for evaluation characterization assessment support."""

import json
from dataclasses import asdict, replace
from typing import Any

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    CharacterizationSourceOpportunity,
    OperationCase,
    OperationEvaluationFrameV3,
    encode_frame,
)

PIN = {"task_id": 7, "product_key": "layer", "content_digest": "a" * 64}


VIEW = {"task_id": 8, "product_key": "view", "content_digest": "b" * 64}


EXTENT = dict(source_view_id=23, projection="c" * 64, native_pointer="#/texts/0", start=0, end=20)


def frame(direction="source_first", **changes) -> OperationEvaluationFrameV3:
    common: dict[str, Any] = dict(
        unit="chapter5",
        release_id="release-1",
        guideline_version="independent-1",
        rubric_version="scope-1",
        context_policy="source-only-1",
        operation_question="predicate_scope",
        operation_version="1",
        domain="statistics",
        direction=direction,
        pin={"source_view_id": 23},
        source_group="book",
        partition="development",
        inspected_scope="original clause",
        opportunities=(
            CharacterizationSourceOpportunity("opportunity", (EXTENT,), "scope", "stated"),
        ),
    )
    if direction == "output_first":
        common.update(characterization_view=VIEW, selected_layers=(PIN,), outputs=())
    return OperationEvaluationFrameV3(**dict(common, **changes))


def case(**changes) -> OperationCase:
    common: dict[str, Any] = dict(
        case_id="scope-case",
        facet="scope",
        anchor_ids=(),
        inspected_scope="original clause",
        source_state="stated",
        judgment="supported",
        alternatives=({"value": {"kind": "operator", "value": "not"}},),
        explanation="Independently read not taking scope over every.",
        assessor_provenance={"actor": "independent-A"},
        opportunity_id="opportunity",
        required_family="prose.scope",
        candidate_selector={"collection": "terms", "value": {"family": "prose.scope"}},
    )
    return OperationCase(**dict(common, **changes))


def coverage(**changes):
    return dict(
        family="prose.scope",
        availability="available",
        outcome="complete",
        examined=[dict(projection=EXTENT["projection"], start=0, end=20)],
        **changes,
    )


def payload(frozen, cases):
    return dict(
        protocol=PROTOCOL,
        release_id=frozen.release_id,
        unit_ref=frozen.unit,
        guideline=frozen.guideline_version,
        rubric_version=frozen.rubric_version,
        context_policy=frozen.context_policy,
        operation_question=frozen.operation_question,
        operation_version=frozen.operation_version,
        domain=frozen.domain,
        direction=frozen.direction,
        reason="independent source-only judgment",
        cases=[asdict(c) for c in cases],
    )


def captured_assessment(monkeypatch, *, extents, expected_case, coverage_row=None):
    """Exercise production capture and scoring; only retained ports/custody are doubled."""
    from types import SimpleNamespace

    from corpus_structure.evaluate import operation_assessment as assessment
    from corpus_structure.evaluate.characterization_assessment import evaluate_characterization
    from corpus_structure.semantic import characterization_store as store

    selected_coverage = coverage_row or dict(
        coverage(), eligible=[dict(projection=EXTENT["projection"], start=0, end=20)]
    )
    body = dict(
        source_scope={"source_view_ids": [23]},
        occurrences=[dict(local_id="location", extents=extents)],
        terms=[
            dict(
                local_id="term",
                kind="operator",
                value="not",
                family="prose.scope",
                occurrences=["location"],
                children=[],
            )
        ],
        annotations=[],
        memberships=[],
        roles=[],
        choices=[],
        coverage=[selected_coverage],
    )
    if expected_case.candidate_selector.get("collection") == "coverage":
        body["terms"] = []
    monkeypatch.setattr(
        store,
        "read_view",
        lambda *a, **k: SimpleNamespace(payload={"layers": [PIN], "active_layers": [PIN]}),
    )
    monkeypatch.setattr(store, "read_layer", lambda *a, **k: SimpleNamespace(payload=body))
    monkeypatch.setattr(
        store,
        "read_layer_manifest",
        lambda *a, **k: SimpleNamespace(payload={"source_scope": body["source_scope"]}),
    )
    opportunity = replace(frame().opportunities[0], source_state=expected_case.source_state)
    frozen = frame(opportunities=(opportunity,))
    snapshot = [{"unit_id": 2, "pass_id": 3, "frame_id": 4}]
    retained = []

    def call(_conn, statement, **values):
        if "native_reference_snapshot" in statement:
            return SimpleNamespace(scalar_one=lambda: snapshot)
        retained.append(json.loads(values["v"]))
        return SimpleNamespace(scalar_one=lambda: 99)

    monkeypatch.setattr(assessment, "_call", call)
    monkeypatch.setattr(assessment, "source_units", lambda *a: [{"source_view_id": 23}])
    monkeypatch.setattr(
        assessment, "read_pass", lambda *a, **k: {"payload": {"cases": [expected_case]}}
    )
    report = evaluate_characterization(
        None,
        project_id="book",
        run_id=5,
        set_id=6,
        completed={"cut_id": 1},
        prepared=SimpleNamespace(release_id="release-1"),
        definition={"sampling": {"partition": "development"}},
        units=[
            {
                "id": 2,
                "unit_key": "chapter5",
                "source_view_id": 23,
                "context": [encode_frame(frozen)],
            }
        ],
        frames={"chapter5": frozen},
        characterization_view=VIEW,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    assert canonical_bytes(retained[0]) == canonical_bytes(report.result)
    return report.result["units"][0]
