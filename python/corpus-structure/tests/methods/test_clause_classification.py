from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.methods.clause_classification import (
    clause_focus,
    model_concordance,
)
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import ClauseFocusSelection, StructuralPassage
from corpus_structure.serve.model_observation_replay import clause_context, clause_labels


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


def test_primary_functions_preserve_overlaps_scores_and_exact_focal_scope():
    from dataclasses import asdict
    from pathlib import Path

    from semantic.model_characterization_support import (
        builder,
        gliner_profile,
        gliner_report,
        mark_other_families_complete,
        scope,
    )

    from corpus_structure.methods.clause_classification import primary_clause_functions
    from corpus_structure.methods.gliner import GlinerInput, GlinerPack
    from corpus_structure.methods.model_observation import installed_policy
    from corpus_structure.methods.pm2_gliner_classification import (
        classification_product,
        classification_request,
    )
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release

    # Primary declaration custody is the same archived release input as production.
    from corpus_structure.semantic.characterization import characterization_inputs
    from corpus_structure.semantic.interpretation_questions import (
        CHARACTERIZATION_FAMILIES,
        characterization_question_dependencies,
        declared_families,
    )
    from corpus_structure.semantic.types import ResolvedDependencies

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))),
        characterization_question_dependencies(ResolvedDependencies()),
    )
    family = declared_families(release.registry_rows)[CHARACTERIZATION_FAMILIES[-1]]
    selected, profile = scope("They define it."), gliner_profile()
    request = classification_request(
        release.release_id,
        family,
        "functions",
        selected.mapping,
        profile,
        installed_policy()[0]["inference"],
        characterization_family=family.family,
    )
    pack, item = GlinerPack(**request["pack"]), GlinerInput(**request["item"])
    native = gliner_report(
        pack,
        item,
        profile.profile,
        dict(
            functions=[
                dict(label="definition", confidence=0.92),
                dict(label="example", confidence=0.8),
                dict(label="description", confidence=0.4),
            ]
        ),
        overlap="flat",
    )
    output = builder(selected)
    output.classification(
        family, selected, request, classification_product(request, asdict(native), profile), native
    )
    mark_other_families_complete(output, selected)
    report = output.finish(release)
    pin = report.reference(12)
    focus = StructuralPassage(
        passage_id="focus",
        source_ref="source",
        start=0,
        end=len(selected.view.text),
        text=selected.view.text,
        scope="focus",
    )
    labels, refs, digest, disposition, _reason = primary_clause_functions(
        {pin: report},
        release,
        selected.mapping.context.primary,
        focus,
        (0, len(selected.view.text)),
    )
    assert [(label.label, label.score, label.accepted) for label in labels] == [
        ("definition", 0.92, True),
        ("example", 0.8, True),
        ("description", 0.4, False),
    ]
    assert (
        disposition == "observed"
        and len(refs) == 1
        and digest
        == next(
            a["model_answer"]["request_digest"]
            for a in report.payload["annotations"]
            if a["kind"] == "model.question"
        )
    )
    from semantic.structural_release_fixture import released_report

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.clause_classification import (
        ClauseClassificationConfig,
        ClauseClassificationMethod,
    )
    from corpus_structure.semantic.structural_products import (
        ExternalSourceRef,
        StructuralInput,
        StructuralProductReport,
    )

    view = selected.view
    source = ExternalSourceRef(
        project_id="fixture",
        run_id=1,
        cut_id=1,
        release_id=release.release_id,
        result_revision=0,
        source_view_id=view.ref.id,
        native_task_id=view.ref.native_product.task_id,
        native_product_key=view.ref.native_product.product_key,
        native_content_digest=view.ref.native_product.content_digest,
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        coordinate_version=3,
    )
    frame_id = "source-contribution:" + "a" * 64
    selection = ClauseFocusSelection(
        passage_id=focus.passage_id,
        frame=RetainedContributionRef(
            contribution_id=frame_id,
            project_id="fixture",
            run_id=1,
            cut_id=1,
            release_id=release.release_id,
            result_revision=0,
            selected_task_id=1,
            origin_task_id=1,
            runtime_fingerprint="fixture",
        ),
    )
    inputs = StructuralInput(
        question="clause functions",
        scope=focus.scope,
        inventory_id="fixture",
        policy_id="retained-functions",
        sources=(source,),
        passages=(focus.model_copy(update=dict(source_ref=source.identity)),),
        dependencies=(frame_id,),
    )
    cfg = ClauseClassificationConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        focuses=(selection,),
        characterization_layers=(pin.values(),),
    )
    retained = dict(
        contributions=[
            dict(
                contribution_id=frame_id,
                pin=dict(source_view_id=view.ref.id, projection_digest=view.ref.projection_digest),
                component=dict(
                    kind="predicate_frame",
                    focus_state="exact",
                    scope=focus.passage_id,
                    frame_members=[
                        dict(role="focus", extents=[dict(start=focus.start, end=focus.end)])
                    ],
                ),
            )
        ]
    )
    reader = SimpleNamespace(
        prepared=release,
        validate_structural_inputs=lambda _inputs: None,
        primary_characterization=lambda *_args, **_kwargs: {pin: report},
        structural_source_frame=lambda *_args: selected.mapping.context.primary,
        retained_source_contribution=lambda _reference: retained,
    )
    method = ClauseClassificationMethod()
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key="function-fixture")),),
        cfg,
        SimpleNamespace(reader=reader, check_active=lambda: None),
    )
    structural = StructuralProductReport.model_validate(result.structural_product)
    wire = released_report(structural, method=method.name, version=method.version)
    (reading,) = wire["clause_classification"]["readings"]
    assert [(label["label"], label["accepted"]) for label in reading["function"]] == [
        ("definition", True),
        ("example", True),
        ("description", False),
    ]
    assert reading["primary_functions"] == list(refs)
    from corpus_structure.semantic.identity import canonical_bytes

    changed = deepcopy(wire)
    question_ref = changed["clause_classification"]["readings"][0]["primary_functions"][0]
    question_ref["layer"]["task_id"] = True
    with pytest.raises(ValueError, match="task_id"):
        release.property_adapter("SourceObservationBatch", "structural_product").validate_json(
            canonical_bytes(changed), strict=True, context={"validation_purpose": "structural"}
        )
    clipped = focus.model_copy(update=dict(start=5, end=11, text="define"))
    assert (
        primary_clause_functions(
            {pin: report}, release, selected.mapping.context.primary, clipped, (5, 11)
        )[3]
        == "failed"
    )
    assert (
        primary_clause_functions(
            {pin: report},
            release,
            selected.mapping.context.primary,
            focus,
            (0, len(selected.view.text) - 1),
        )[3]
        == "failed"
    )
    assert (
        primary_clause_functions(
            {pin: report, report.reference(13): report},
            release,
            selected.mapping.context.primary,
            focus,
            (0, len(selected.view.text)),
        )[3]
        == "failed"
    )
