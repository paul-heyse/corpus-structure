"""Analytical replay consumes the captured primary selection without recognizing source again."""

from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.serve import primary_characterization_replay, review_bundle


def captured_report(method, cfg, report):
    from corpus_structure.orchestrate.registry import canonical_numbers

    config = canonical_numbers(cfg.model_dump(mode="json"))
    digest = config_key(method.name, method.version, config)
    return dict(
        origin_task_id=91,
        project_id="capture",
        origin_run_id=31,
        runtime_fingerprint="runtime",
        configuration=config,
        config_hash=digest,
        input_hash="captured-input",
        body=dict(
            method=method.name,
            operation_version=method.version,
            release_id="capture-release",
            outcome="produced",
            configuration_hash=digest,
            input_hash="captured-input",
            structural_product=report.model_dump(mode="json"),
        ),
    )


def install_capture(monkeypatch, raw, layers, sources=(), payloads=None):
    monkeypatch.setattr(
        review_bundle,
        "_detached_relation",
        lambda _root, _manifest, name: iter(
            [raw] if name == "reports" else sources if name == "sources" else ()
        ),
    )
    # These adapter controls start after the shared archive/pin/source authentication boundary.
    # Layers are actual primary producer results; the adapter must preserve their exact selection.
    monkeypatch.setattr(
        primary_characterization_replay, "retained_primary_layers", lambda *_: (layers, {})
    )
    if payloads is not None:
        monkeypatch.setattr(
            review_bundle,
            "_retained_contribution_payloads",
            lambda _root, _manifest, requested, *_args, **_kwargs: (
                payloads[ref.contribution_id] for _report, ref in requested
            ),
        )


def verify_artifact(raw, report):
    review_bundle._verify_artifact_nomination_closure(
        None,
        {},
        [(0, 0, 91, 31, "capture", "runtime", report)],
        {0: {"release_id": "capture-release"}},
        {},
        {},
    )


def artifact_fixture():
    from methods.m1_source_preparation_support import source
    from methods.navigation_fixture import primary_navigation
    from methods.scoped_relations_support import complete_native_fields, original_inputs

    from corpus_structure.methods.artifact_identity import (
        ArtifactIdentityConfig,
        ArtifactIdentityMethod,
    )
    from corpus_structure.methods.scoped_relations import SourceWorkBinding
    from corpus_structure.semantic.artifact_identity import ArtifactScoringPolicy
    from corpus_structure.semantic.proposals import native_source_frame

    view = complete_native_fields(
        source("Table 5.1 (numbering namespace: Main)", labels=("caption",))
    )
    layers = primary_navigation(view, annotations=(), formal=True)
    inputs = original_inputs(view)
    cfg = ArtifactIdentityConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        characterization_layers=tuple(pin.values() for pin in layers),
        work_bindings=(
            SourceWorkBinding(
                native_content_digest=view.ref.native_product.content_digest,
                source_work="book",
                provenance="explicit fixture",
            ),
        ),
        policy=ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05),
    )
    method = ArtifactIdentityMethod()
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key=inputs.identity)),),
        cfg,
        SimpleNamespace(
            check_active=lambda: None,
            reader=SimpleNamespace(
                structural_source_frame=lambda *_: native_source_frame(view, ()),
                characterization_layers=lambda _: layers,
            ),
        ),
    )
    report = StructuralProductReport.model_validate(result.structural_product)
    source_row = dict(
        source_view_id=view.ref.id,
        text=view.text,
        ref=asdict(view.ref),
        context=dict(
            items=view.items, pieces=view.pieces, ancestors=view.ancestors, health=view.health
        ),
    )
    return captured_report(method, cfg, report), report, layers, source_row


@pytest.mark.parametrize(
    "mutation", (None, "missing_primary", "obsolete", "invented_title", "wrong_source")
)
def test_artifact_replay_preserves_current_primary_source_fields(monkeypatch, mutation):
    from corpus_structure.semantic.constructions import navigation

    raw, report, layers, source = artifact_fixture()
    if mutation == "missing_primary":
        layers = {}
    elif mutation == "obsolete":
        raw["body"]["operation_version"] = "4"
    elif mutation == "invented_title":
        product = report.artifact_identity
        assert product is not None
        (record,) = product.records
        artifact = record.artifact.model_copy(update={"title": "Invented caption"})
        forged = record.model_copy(update={"artifact": artifact})
        report = report.model_copy(
            update={"artifact_identity": product.model_copy(update={"records": (forged,)})}
        )
        raw["body"]["structural_product"] = report.model_dump(mode="json")
    elif mutation == "wrong_source":
        source = deepcopy(source)
        source["ref"]["projection_digest"] = "f" * 64
    install_capture(monkeypatch, raw, layers, [source])
    monkeypatch.setattr(
        navigation,
        "source_alias_fields",
        lambda *_: pytest.fail("artifact replay recognized aliases"),
    )
    monkeypatch.setattr(navigation, "_ARTIFACT", None)
    if mutation is None:
        verify_artifact(raw, report)
        assert report.artifact_identity is not None
        assert report.artifact_identity.records[0].numbering.value == "Main"
    else:
        with pytest.raises(ValueError, match=r"primary|producer|source|artifact cohort"):
            verify_artifact(raw, report)


def comparison_fixture():
    from corpus_structure.methods.structural_products import (
        StructuralComparisonConfig,
        StructuralComparisonMethod,
    )
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from semantic.primary_formal_fixture import formal_layers
    from semantic.typed_structural_composition_support import threshold_inputs

    inputs = threshold_inputs(
        "revenue ≥ 100 USD\nComparison basis: annual revenue.",
        "revenue ≥ 200 USD\nComparison basis: annual revenue.",
    )
    inputs = inputs.model_copy(
        update={
            "passages": tuple(
                p.model_copy(update={"effective_version": "R1"}) for p in inputs.passages
            )
        }
    )
    layers = formal_layers(inputs)
    references, payloads = [], {}
    for source, passage, digit in zip(inputs.sources, inputs.passages, "ab", strict=True):
        key = "source-contribution:" + digit * 64
        reference = RetainedContributionRef(
            contribution_id=key,
            project_id=source.project_id,
            run_id=source.run_id,
            cut_id=source.cut_id,
            release_id=source.release_id,
            result_revision=source.result_revision,
            selected_task_id=source.native_task_id + 1,
            origin_task_id=source.native_task_id + 1,
            runtime_fingerprint="runtime",
        )
        references.append(reference)
        pin = dict(
            source_view_id=source.source_view_id,
            native_product_task_id=source.native_task_id,
            product_digest=source.native_content_digest,
            projection_digest=source.projection_digest,
            recipe_digest=source.recipe_digest,
        )
        extents = [dict(start=passage.start, end=passage.end)]
        payloads[key] = dict(
            contributions=[
                dict(
                    contribution_id=key,
                    pin=pin,
                    component=dict(
                        kind="predicate_reading",
                        question_version="6",
                        frame="frame",
                        scope=passage.passage_id,
                        effective_version="R1",
                    ),
                ),
                dict(
                    contribution_id="frame",
                    pin=pin,
                    component=dict(
                        kind="predicate_frame",
                        scope=passage.passage_id,
                        effective_version="R1",
                        frame_members=[
                            dict(
                                role="predicate",
                                contribution="action",
                                outcome="complete",
                                extents=extents,
                            ),
                            dict(
                                role="focus",
                                contribution="action",
                                outcome="complete",
                                extents=extents,
                            ),
                        ],
                    ),
                ),
            ]
        )
    inputs = inputs.model_copy(update={"dependencies": (*inputs.dependencies, *payloads)})
    cfg = StructuralComparisonConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        left_id="a",
        right_id="b",
        left_reading=references[0],
        right_reading=references[1],
        characterization_layers=tuple(pin.values() for pin in layers),
    )
    method = StructuralComparisonMethod()
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key=inputs.identity)),),
        cfg,
        SimpleNamespace(
            check_active=lambda: None,
            reader=SimpleNamespace(
                validate_structural_inputs=lambda _: None,
                primary_characterization=lambda *_args, **_kwargs: layers,
                retained_source_contribution=lambda reference: payloads[reference.contribution_id],
            ),
        ),
    )
    report = StructuralProductReport.model_validate(result.structural_product)
    return captured_report(method, cfg, report), report, layers, payloads


@pytest.mark.parametrize(
    "mutation", (None, "missing_primary", "obsolete", "predicate_version", "unselected_layer")
)
def test_comparison_replay_preserves_primary_thresholds_and_selection(monkeypatch, mutation):
    from corpus_structure.semantic import formal_evidence, structural_parsing

    raw, report, layers, payloads = comparison_fixture()
    if mutation == "missing_primary":
        layers = {}
    elif mutation == "obsolete":
        raw["body"]["operation_version"] = "5"
    elif mutation == "predicate_version":
        next(iter(payloads.values()))["contributions"][0]["component"]["question_version"] = "5"
    elif mutation == "unselected_layer":
        raw["configuration"]["characterization_layers"][0]["content_digest"] = "f" * 64
        digest = config_key("structure.compare", "6", raw["configuration"])
        raw["config_hash"] = raw["body"]["configuration_hash"] = digest
    install_capture(monkeypatch, raw, layers, payloads=payloads)
    monkeypatch.setattr(
        formal_evidence,
        "nominate_fields",
        lambda *_args, **_kwargs: pytest.fail("replay recognized formal fields"),
    )
    monkeypatch.setattr(
        structural_parsing,
        "parse_threshold",
        lambda *_args, **_kwargs: pytest.fail("replay parsed threshold"),
    )

    def verify():
        review_bundle._verify_comparison_closure(
            None,
            {},
            [(0, 0, 91, 31, "capture", "runtime", report)],
            {0: {"release_id": "capture-release"}},
            {},
            {},
        )

    if mutation is None:
        verify()
        assert report.comparison is not None
        threshold = next(d for d in report.comparison.dimensions if d.dimension == "threshold_unit")
        assert threshold.left_group is not None and threshold.right_group is not None
        left, right = threshold.left_group.members[0].typed, threshold.right_group.members[0].typed
        assert left is not None and right is not None
        assert (left.value, right.value) == ("100", "200")
        assert left.primary_formal is not None
    else:
        with pytest.raises(ValueError, match=r"primary|producer|retained predicate"):
            verify()
