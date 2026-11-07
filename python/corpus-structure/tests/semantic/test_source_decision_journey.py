"""Independent source capture and exact side-to-display journey controls."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    ExternalSourceRef,
    StructuralProductReport,
)
from corpus_structure.serve.source_decision_journey import (
    JourneyTask,
    Opportunity,
    SourceDecisionJourneyParams,
    source_decision_journey,
)


@pytest.fixture
def original():
    return ExternalSourceRef(
        project_id="statistics",
        run_id=1,
        cut_id=2,
        release_id="release",
        result_revision=3,
        source_view_id=4,
        native_task_id=5,
        native_product_key="organized",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=2,
    )


def _source(ref, *, projected=True):
    return {
        "ref": {
            "id": ref.source_view_id,
            "native_product": {
                "task_id": ref.native_task_id,
                "product_key": ref.native_product_key,
                "content_digest": ref.native_content_digest,
            },
            "projection_digest": ref.projection_digest,
            "recipe_digest": ref.recipe_digest,
        },
        "context": {
            "items": [{"self_ref": "#/texts/0", "text": "Table 5.8 proves nothing."}],
            "pieces": (
                [
                    {
                        "item_ref": "#/texts/0",
                        "kind": "native_text",
                        "start": 0,
                        "end": 25,
                    }
                ]
                if projected
                else []
            ),
        },
        "text": "Table 5.8 proves nothing." if projected else "",
    }


def _pin(task, cut):
    return dict(
        cut_member=True,
        task_status="done",
        run_id=7,
        cut_id=cut,
        selected_task_id=task,
        origin_task_id=task + 100,
        release_id="release",
        project_id="statistics",
        result_revision=3,
        runtime_fingerprint="runtime",
    )


def test_journey_distinguishes_native_caption_omission_from_task_availability(original):
    request = SourceDecisionJourneyParams(
        opportunity=Opportunity(source=original, pointer="#/texts/0", start=0, end=9),
        layers=(JourneyTask(layer="artifact", run_id=7, cut_id=8, task_id=9),),
    )
    capture = _source(original, projected=False)
    tasks = {
        "artifact": (
            _pin(9, 8),
            {
                "structural_product": {
                    "artifact_identity": {"records": [], "pairs": [], "route_counts": []}
                }
            },
        ),
    }
    answer = source_decision_journey(request, capture, tasks)
    assert answer.source_capture == "omitted_from_projection"
    assert answer.layers[0].status == "inspected_empty"
    assert answer.layers[1].status == "unrequested"
    assert (
        source_decision_journey(request, capture, {"artifact": (_pin(9, 8), None)}).layers[0].status
        == "unavailable"
    )
    assert (
        source_decision_journey(
            request, capture, {"artifact": ({**_pin(9, 8), "cut_member": False}, None)}
        )
        .layers[0]
        .status
        == "outside_selection"
    )
    capture["context"]["items"] = []
    assert source_decision_journey(request, capture, tasks).source_capture == "outside_selection"


def test_journey_joins_only_exact_comparison_side_and_display(original):
    comparison_task, dossier_task = 9, 10
    reading_id = "source-contribution:" + "d" * 64
    request = SourceDecisionJourneyParams(
        opportunity=Opportunity(source=original, pointer="#/texts/0", start=0, end=9),
        layers=(
            JourneyTask(
                layer="comparison", run_id=7, cut_id=8, task_id=comparison_task, case_id=reading_id
            ),
            JourneyTask(layer="dossier", run_id=7, cut_id=8, task_id=dossier_task),
        ),
    )
    capture = _source(original)
    reading = {
        "contribution_id": reading_id,
        "project_id": "statistics",
        "run_id": 7,
        "cut_id": 8,
        "selected_task_id": 90,
        "origin_task_id": 90,
        "release_id": "release",
        "result_revision": 3,
        "runtime_fingerprint": "runtime",
    }
    comparison = {
        "kind": "qualified_comparison",
        "inputs": {
            "question": "exact comparison",
            "scope": "chapter",
            "inventory_id": "items",
            "policy_id": "p",
            "sources": [original.model_dump()],
            "passages": [
                {
                    "passage_id": "left",
                    "source_ref": original.identity,
                    "text": "Table 5.8 proves nothing.",
                    "start": 0,
                    "end": 25,
                    "scope": "chapter",
                },
                {
                    "passage_id": "right",
                    "source_ref": original.identity,
                    "text": "Table 5.8 proves nothing.",
                    "start": 0,
                    "end": 25,
                    "scope": "chapter",
                },
            ],
            "dependencies": ["source"],
        },
        "comparison": {
            "left_id": "left",
            "right_id": "right",
            "left_reading": reading,
            "right_reading": {**reading, "contribution_id": "source-contribution:" + "e" * 64},
            "left_focus": {"passage_id": "left", "text": "Table 5.8", "start": 0, "end": 9},
            "applicability": "co_applicable",
            "applicability_reason": "same independently bound applicability",
            "dimensions": [
                {
                    "dimension": name,
                    "outcome": "unknown",
                    "left_group": {"state": "absent"},
                    "right_group": {"state": "absent"},
                }
                for name in DIMENSIONS
            ],
        },
    }
    pin = _pin(comparison_task, 8)
    citation = dict(
        comparison_ref={
            **pin,
            "product_id": StructuralProductReport.model_validate(comparison).product_id,
        },
        side="left",
    )
    dossier = {
        "dossier": {
            "predecessors": [citation["comparison_ref"]],
            "members": [
                {"member_id": "same-side", "comparison_binding": citation},
                {"member_id": "opposite", "comparison_binding": {**citation, "side": "right"}},
                {
                    "member_id": "other-cut",
                    "comparison_binding": {
                        **citation,
                        "comparison_ref": {**citation["comparison_ref"], "cut_id": 14},
                    },
                },
            ],
            "representation": {"selected": ["same-side", "opposite", "other-cut"]},
        }
    }
    tasks = {
        "comparison": (pin, {"structural_product": comparison}),
        "dossier": (_pin(dossier_task, 8), {"structural_product": dossier}),
    }
    answer = source_decision_journey(request, capture, tasks)
    assert answer.source_capture == "represented"
    assert answer.layers[2].status == "observed"
    assert answer.layers[3].status == "observed"
    assert answer.layers[3].evidence["display"] == ["same-side"]
    altered = deepcopy(tasks)
    altered["comparison"][1]["structural_product"]["comparison"]["left_focus"] = {
        "passage_id": "left",
        "text": "prove",
        "start": 10,
        "end": 15,
    }
    answer = source_decision_journey(request, capture, altered)
    assert answer.layers[2].status == "inspected_empty"
    assert answer.layers[3].status == "unavailable"
    dossier["dossier"]["predecessors"] = []
    assert source_decision_journey(request, capture, tasks).layers[3].status == "unavailable"
