"""Current-format linguistic inputs retain original task custody across run boundaries."""

from types import SimpleNamespace

import pytest

from corpus_structure.methods.definition_applicability import (
    DefinitionComponentsConfig,
    retained_annotation_components,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeProposalFrame
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)
from corpus_structure.semantic.structural_sources import (
    PreparedStructuralAnnotations,
    load_structural_annotations,
)


def manifest():
    source = ExternalSourceRef(
        project_id="original",
        run_id=113,
        cut_id=141,
        release_id="original-release",
        result_revision=1,
        source_view_id=53,
        native_task_id=260,
        native_product_key="organized",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    passage = StructuralPassage(
        passage_id="target", source_ref=source.identity, start=0, end=1, text="X", scope="s"
    )
    inputs = StructuralInput(
        question="Locate components",
        scope="s",
        inventory_id="i",
        policy_id="p",
        sources=(source,),
        passages=(passage,),
        dependencies=("annotation:285",),
    )
    return inputs, source, passage


def retained_named_product(monkeypatch, states):
    """Run the primary producer over independently missing dependency columns."""
    from dataclasses import replace

    from annotation_support import ControlledPipeline, item
    from methods.primary_reading_fixture import primary_product

    from corpus_structure.ingest import annotations
    from corpus_structure.ingest.annotations import AnnotationProfile, annotate
    from corpus_structure.methods.annotation_rules import AnnotationRule
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    nlp = ControlledPipeline()
    nlp.omit = "dependency"
    monkeypatch.setattr(annotations, "pipeline", lambda _: nlp)
    rules = tuple(
        AnnotationRule(
            rule="defining",
            variant=str(index),
            mechanism="dependency" if state == "unavailable" else "phrase",
            pattern=(
                [{"RIGHT_ID": "cue", "RIGHT_ATTRS": {"DEP": "ROOT"}}]
                if state == "unavailable"
                else ["absent"]
            ),
            bindings={"defined_term": {"node": "cue" if state == "unavailable" else "match"}},
        )
        for index, state in enumerate(states)
    )
    request = replace(
        item(nlp, "X", start=0, identity=53),
        source=NativeSourcePin(
            53,
            "source:53",
            ProductReference(260, "organized", "a" * 64),
            "#/groups/0",
            "descendants",
            "b" * 64,
            "c" * 64,
            3,
        ),
    )
    (native,) = annotate((request,), require_complete=False)
    return primary_product(
        "X", native, AnnotationProfile(), rules=rules, native_profile=nlp.selection().native
    ), rules


def test_definition_consumer_uses_owned_original_source_read_not_current_run_view(monkeypatch):
    inputs, source, passage = manifest()
    calls = []
    product, rules = retained_named_product(monkeypatch, ("unavailable",))

    class Reader:
        def structural_source_annotations(self, actual, ref, profile):
            calls.append((actual, ref, profile))
            return PreparedStructuralAnnotations(
                NativeProposalFrame(
                    "source:53",
                    "X",
                    (),
                    53,
                    ProductReference(260, "organized", "a" * 64),
                    "#/groups/0",
                    "descendants",
                    "b" * 64,
                    "c" * 64,
                    canonical_bytes(dict(items=[], pieces=[], ancestors=[], health={})).decode(),
                ),
                (product,),
                (),
                285,
                "original-input",
            )

        def source_view(self, *args):
            raise AssertionError("must not select original source through current run")

        def source_result(self, *args):
            raise AssertionError("must not search current-run annotations")

    result = retained_annotation_components(
        Reader(),
        inputs,
        passage,
        DefinitionComponentsConfig(annotation_rules=rules),
        witness_policy={},
    )
    assert result.components == () and not result.available
    assert "no source absence" in result.reason
    assert len(calls) == 1 and calls[0][0] == inputs and calls[0][1] == source.identity


def test_original_source_reference_must_be_inside_authenticated_manifest():
    inputs, _, _ = manifest()
    with pytest.raises(ValueError, match="outside authenticated"):
        load_structural_annotations(None, inputs, "unselected-source", None)


@pytest.mark.parametrize(
    "corruption",
    ("input_hash", "configuration_hash", "method", "operation_version", "source", "release_id"),
)
def test_original_annotation_envelope_cannot_relabel_source_or_task(monkeypatch, corruption):
    from corpus_structure.semantic import proposals
    from corpus_structure.semantic import structural_sources as owner

    inputs, source, _ = manifest()
    frame = SimpleNamespace(unit_ref="source:53")
    body = dict(
        release_id=source.release_id,
        source="source:53",
        method="extract.m1_annotations",
        operation_version="2",
        unit_key="source:53",
        input_hash="input",
        configuration_hash="config",
    )
    body[corruption] = "forged"
    row = dict(
        origin_task_id=285,
        release_id=source.release_id,
        unit_key="source:53",
        input_hash="input",
        config_hash="config",
        version="2",
        body=body,
    )
    monkeypatch.setattr(owner, "load_source_view", lambda *args, **kwargs: object())
    monkeypatch.setattr(proposals, "native_source_frame", lambda *args: frame)

    class Budget:
        def preflight(self, *args):
            pass

        def value(self, *args):
            pass

    class Conn:
        def execute(self, *args):
            return SimpleNamespace(mappings=lambda: (row,))

    with pytest.raises(ValueError, match="native task custody"):
        load_structural_annotations(Conn(), inputs, source.identity, None, read_budget=Budget())


def test_missing_annotation_error_is_unavailable_without_reason_word_matching():
    inputs, _, passage = manifest()
    retained = SimpleNamespace(
        source=object(),
        annotations=(),
        errors=("original cut has no retained linguistic annotation product",),
    )
    result = retained_annotation_components(
        object(),
        inputs,
        passage,
        DefinitionComponentsConfig(),
        retained=retained,
        witness_policy={},
    )
    assert not result.available and not result.components


@pytest.mark.parametrize(
    "states,available", [(("unavailable",), False), (("unavailable", "available"), True)]
)
def test_named_rule_availability_is_preserved_per_variant(monkeypatch, states, available):
    inputs, _, passage = manifest()
    product, rules = retained_named_product(monkeypatch, states)
    retained = SimpleNamespace(
        source=SimpleNamespace(text="X"),
        annotations=(product,),
        errors=(),
        annotation_task_id=285,
    )
    cfg = DefinitionComponentsConfig(annotation_rules=rules)
    result = retained_annotation_components(
        object(), inputs, passage, cfg, retained=retained, witness_policy={}
    )
    assert result.available is available and result.components == ()
    assert tuple(operation["availability"] for operation in result.operations) == states


def test_authentic_unsupported_annotation_version_is_unavailable_without_decoding(monkeypatch):
    from corpus_structure.semantic import proposals
    from corpus_structure.semantic import structural_sources as owner

    inputs, source, _ = manifest()
    body = dict(
        release_id=source.release_id,
        source="source:53",
        method="extract.m1_annotations",
        operation_version="1",
        unit_key="source:53",
        input_hash="input",
        configuration_hash="config",
        parse_detail={"do_not_decode": "unsupportedformat"},
    )
    row = dict(
        origin_task_id=285,
        release_id=source.release_id,
        unit_key="source:53",
        input_hash="input",
        config_hash="config",
        version="1",
        body=body,
    )
    monkeypatch.setattr(owner, "load_source_view", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        proposals, "native_source_frame", lambda *args: SimpleNamespace(unit_ref="source:53")
    )

    class Budget:
        def preflight(self, *args):
            pass

        def value(self, *args):
            pass

    class Conn:
        def execute(self, *args):
            return SimpleNamespace(mappings=lambda: (row,))

    result = load_structural_annotations(
        Conn(), inputs, source.identity, None, read_budget=Budget()
    )
    assert result.annotations == () and result.annotation_task_id == 285
    assert "version 1 is unsupported" in result.errors[0]
