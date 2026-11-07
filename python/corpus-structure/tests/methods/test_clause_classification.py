from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.methods.clause_classification import (
    clause_context,
    clause_focus,
    clause_labels,
    model_concordance,
)
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import ClauseFocusSelection, StructuralPassage


def test_native_fallback_preserves_score_without_accepting_presentation():
    function, presentation, state = clause_labels(
        {
            "clause_function": {"label": "definition", "confidence": 0.9},
            "presentation_context": [{"label": "historical", "confidence": 0.3}],
        }
    )
    assert function[0].accepted and state == "observed"
    assert (presentation[0].label, presentation[0].score, presentation[0].accepted) == (
        "historical",
        0.3,
        False,
    )
    _, _, withheld = clause_labels(
        {
            "clause_function": {"label": "unresolved", "confidence": 0.9},
            "presentation_context": [{"label": "example", "confidence": 0.3}],
        }
    )
    assert withheld == "withheld"


def test_concordance_matches_retained_and_current_focus_extents():
    retained: dict[str, Any] = {
        "contribution_id": "old-frame",
        "pin": {"source_view_id": 1},
        "component": {
            "kind": "predicate_frame",
            "focus_state": "exact",
            "frame_members": [{"role": "focus", "extents": [{"start": 3, "end": 8}]}],
        },
    }
    current = deepcopy(retained)
    current["contribution_id"] = "current-frame"
    current["component"]["frame_members"][0]["extents"] = ({"start": 3, "end": 8},)
    reading = {
        "component": {
            "kind": "predicate_reading",
            "frame": "current-frame",
            "reading": "explanation",
        }
    }
    reference = SimpleNamespace(product_id="observation", model_dump=lambda **_: {})
    report = SimpleNamespace(
        product_id="observation",
        inputs=SimpleNamespace(
            sources=[SimpleNamespace(identity="view", source_view_id=1)],
            passages=[SimpleNamespace(passage_id="passage", source_ref="view")],
        ),
        clause_classification=SimpleNamespace(
            readings=[
                SimpleNamespace(
                    selection=SimpleNamespace(passage_id="passage", frame="old-frame"),
                    function=[SimpleNamespace(accepted=True, label="definition")],
                    model_dump=lambda **_: {},
                )
            ]
        ),
    )
    (match,) = model_concordance(reference, report, 1, (current, reading), lambda _: retained)
    assert (match["deterministic_reading"], match["comparison"]) == ("explanation", "disagrees")

    current["component"]["frame_members"][0]["extents"] = ({"start": 4, "end": 8},)
    with pytest.raises(ValueError):
        model_concordance(reference, report, 1, (current, reading), lambda _: retained)


def test_context_contains_only_exact_focus_and_source_owned_adjacent_sentences():
    passage = StructuralPassage(
        passage_id="sample",
        source_ref="source",
        start=20,
        end=40,
        text="Before. Focus. Next.",
        scope="sample",
    )
    contribution_id = "source-contribution:" + "a" * 64
    selection = ClauseFocusSelection(
        passage_id="sample",
        frame=RetainedContributionRef(
            contribution_id=contribution_id,
            project_id="test",
            run_id=1,
            cut_id=1,
            release_id="release",
            result_revision=0,
            selected_task_id=1,
            origin_task_id=1,
            runtime_fingerprint="runtime",
        ),
    )
    retained = {
        "contributions": [
            {
                "contribution_id": contribution_id,
                "pin": {"source_view_id": 1, "projection_digest": "projection"},
                "component": {
                    "kind": "predicate_frame",
                    "focus_state": "exact",
                    "scope": "sample",
                    "frame_members": [{"role": "focus", "extents": [{"start": 28, "end": 33}]}],
                    "annotation": "annotation:retained",
                    "block": "native-block",
                },
            }
        ],
    }
    source = SimpleNamespace(source_view_id=1, projection_digest="projection")
    block = SimpleNamespace(
        block_id="native-block",
        dependency_digest="retained",
        sentences=tuple(
            SimpleNamespace(start=lo, end=hi) for lo, hi in ((20, 27), (28, 34), (35, 40))
        ),
    )
    spans = clause_focus(selection, passage, source, retained, (block,))
    focus, preceding, following = spans
    assert preceding is not None and following is not None
    assert (focus.text, preceding.text, following.text) == ("Focus", "Before.", "Next.")
    context = clause_context(selection, "adjacent_sentences", *spans)
    exact = clause_context(
        selection, "exact_focus", *clause_focus(selection, passage, source, retained)
    )
    assert context.text == "Before.\n<focus>Focus</focus>\nNext."
    assert exact.text == "Focus" and exact.context_digest != context.context_digest
    retained["contributions"][0]["component"]["focus_state"] = "partial"
    with pytest.raises(ValueError, match="exact retained focus"):
        clause_focus(selection, passage, source, retained)
