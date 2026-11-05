"""Independent automatic-selector controls; mocked models do not qualify providers."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.methods.definition_applicability import (
    DefinitionApplicabilityConfig,
    DefinitionApplicabilityMethod,
    decode_applicability,
    pair_input,
)
from corpus_structure.methods.gliner import GlinerPack, GlinerProfile, GlinerRefused
from corpus_structure.methods.structural_retrieval import source_definition_inventory
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)


def inputs():
    source = ExternalSourceRef(
        project_id="book",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        source_view_id=1,
        native_task_id=1,
        native_product_key="native",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    passages = (
        StructuralPassage(
            passage_id="usage", source_ref=source.identity, start=0, end=4, text="mean", scope="s"
        ),
        StructuralPassage(
            passage_id="target",
            source_ref=source.identity,
            start=10,
            end=17,
            text="average",
            scope="s",
        ),
    )
    base = StructuralInput(
        question="What defines mean?",
        scope="s",
        inventory_id="pending",
        policy_id="p",
        sources=(source,),
        passages=passages,
        dependencies=("source",),
    )
    inventory = source_definition_inventory(base, target_ids=("target",))
    return base.model_copy(update={"inventory_id": inventory.inventory_id})


def profile():
    return GlinerProfile(
        Path("/model"),
        "checkpoint",
        "revision",
        tuple(
            (name, "a" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
    )


def test_default_is_unrequested_and_cannot_smuggle_partial_inputs():
    method = DefinitionApplicabilityMethod()
    assert method.select(None, DefinitionApplicabilityConfig()) == ()
    with pytest.raises(ValueError, match="partial inputs"):
        DefinitionApplicabilityConfig(usage_id="usage")


def test_source_inventory_is_frozen_before_any_model_work():
    value = inputs()
    kwargs = dict(
        inputs=value,
        structural_input_digest=value.identity,
        usage_id="usage",
        target_ids=("target",),
        profile=profile(),
    )
    DefinitionApplicabilityConfig(**kwargs)
    selected_units = DefinitionApplicabilityMethod().select(
        None, DefinitionApplicabilityConfig(**kwargs)
    )
    assert len(selected_units) == 1
    assert next(iter(selected_units)).unit_key == "definition:" + value.identity + ":usage"
    with pytest.raises(ValueError, match="digest"):
        DefinitionApplicabilityConfig(**{**kwargs, "structural_input_digest": "foreign"})
    with pytest.raises(ValueError, match="frozen"):
        changed = value.model_copy(update={"inventory_id": "foreign"})
        DefinitionApplicabilityConfig(
            **{**kwargs, "inputs": changed, "structural_input_digest": changed.identity}
        )


def test_pair_classification_has_distinct_virtual_context_and_no_fabricated_native_offsets():
    pack = GlinerPack("release", "{}", version="native-combined-v2")
    value = inputs()
    pair = pair_input(value, "usage", "target", pack)
    assert pair.text.index("mean") < pair.text.index("average")
    assert pair.context_id.startswith("definition-pair:") and len(pair.context_digest) == 64
    changed = pair_input(
        value.model_copy(update={"question": "different question"}), "usage", "target", pack
    )
    assert changed.context_digest != pair.context_digest


def test_raw_confidence_is_not_public_authority_or_literal_evidence():
    reading = decode_applicability(
        {"applicability": {"label": "mention", "confidence": 0.999}},
        usage_id="usage",
        target_id="target",
        allowed=frozenset({"mention"}),
    )
    assert reading.outcome == "mention" and reading.evidence == ("usage", "target")
    assert "confidence" not in reading.model_dump()
    for bad in ({}, {"applicability": []}, {"applicability": {"label": "invented"}}):
        with pytest.raises(GlinerRefused):
            decode_applicability(
                bad, usage_id="usage", target_id="target", allowed=frozenset({"mention"})
            )


def test_classifier_failure_retains_successful_nomination_and_truthful_stage(monkeypatch):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
    from corpus_structure.methods import definition_applicability as operation
    from corpus_structure.methods.gliner_worker import GlinerWorker, GlinerWorkerError

    value = inputs()
    cfg = DefinitionApplicabilityConfig(
        inputs=value,
        structural_input_digest=value.identity,
        usage_id="usage",
        target_ids=("target",),
        profile=profile(),
    )
    order = []

    class Reader:
        prepared = SimpleNamespace(enum_members=lambda *_: frozenset({"mention"}))

        def validate_structural_inputs(self, actual):
            assert actual == value
            order.append("validated")

        def contextual_candidates(self, **kwargs):
            order.append("nominated")
            return SimpleNamespace(
                list_id="list", candidates=(SimpleNamespace(target_id="target"),)
            )

    def encode(*args, **kwargs):
        order.append("encoded")
        return SimpleNamespace(
            vectors=(SimpleNamespace(object_id="usage"), SimpleNamespace(object_id="target")),
            implementation={"test": "not_provider"},
            inputs=(),
        )

    class FailedWorker(GlinerWorker):
        def __init__(self):
            super().__init__(profile())

        @property
        def closed(self):
            return True

        def extract(self, *args, **kwargs):
            raise GlinerWorkerError("controlled model failure")

    monkeypatch.setattr(GlinerProfile, "verify_artifacts", lambda *_: None)
    monkeypatch.setattr(operation, "encode_contexts", encode)
    monkeypatch.setattr(operation, "enrichment_report", lambda **_: {"retained_nomination": True})
    monkeypatch.setattr(
        operation,
        "applicability_pack",
        lambda _: GlinerPack("release", "{}", version="native-combined-v2"),
    )
    method = DefinitionApplicabilityMethod()
    method._worker = FailedWorker()
    (result,) = method.run(
        (SimpleNamespace(ref=UnitRef(TaskUnitType.RUN)),),
        cfg,
        SimpleNamespace(reader=Reader(), check_active=lambda: None),
    )
    assert order == ["validated", "encoded", "nominated"]
    assert result.outcome is ObservationOutcome.PRODUCED
    assert result.structural_product is not None and result.parse_detail is not None
    assert result.structural_product["definition"]["readings"] == []
    assert result.structural_product["retrieval_report"] == {"retained_nomination": True}
    stages = result.parse_detail["classification_stages"]
    assert isinstance(stages, list) and stages
    first = stages[0]
    assert isinstance(first, dict) and first["outcome"] == "failed"
    assert result.parse_detail["raw_reports"] == []
