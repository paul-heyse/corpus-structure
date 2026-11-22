"""Explicit current source/primary inputs for scoped relation controls."""

from corpus_structure.methods.scoped_relations import discover_relations as _discover_relations
from corpus_structure.semantic.declared_formal_readings import declared_formal_layers
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    source_slice,
)
from corpus_structure.semantic.structural_products import DeclaredStructuralInput, StructuralPassage
from methods.navigation_fixture import source_primary_products


def discover_relations(frame, **kwargs):
    from corpus_structure.methods.predicate_contributions import declared_predicate_evidence
    from corpus_structure.semantic.sentence_products import retained_source_annotation_products

    annotations = kwargs.pop("annotations", None)
    profile = kwargs.pop("annotation_profile", None)
    errors = kwargs.pop("annotation_errors", ())
    preflight = kwargs.pop("qualifier_preflight", None)
    native_profile = kwargs.pop("annotation_native_profile", None)
    primary = kwargs.pop("primary", None)
    if primary is None:
        primary = source_primary_products(
            frame,
            annotations,
            profile=profile,
            native_profile=native_profile,
            max_formula_chars=kwargs.get("max_formula_chars", 2048),
        )
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, len(frame.text)),),
        "scoped scientific control",
        "explicit-current-products",
        "selected original",
        preparation=PreparedNativeSources((frame,)),
        max_chars=max(1, len(frame.text)),
        max_pieces=max(1, len(frame.pieces)),
    )
    evidence = declared_predicate_evidence(
        frame,
        context,
        retained_source_annotation_products(primary.source, primary.native)
        if primary.native is not None
        else (),
        dependency=primary.native.semantic_id
        if primary.native is not None
        else primary.construction.semantic_id,
        primary_products=(primary.construction,),
        formal_products=(primary.formal,),
        passages=kwargs.get("passages"),
        annotation_errors=errors,
        qualifier_preflight=preflight,
    )
    return _discover_relations(
        frame,
        navigation=primary.navigation,
        annotation_errors=errors,
        formal_layers=declared_formal_layers((primary.formal,), primary.source),
        retained_predicates=evidence.contributions,
        retained_predicate_operations=evidence.operations,
        retained_coordinate_texts=evidence.coordinate_texts,
        **kwargs,
    )


def original_inputs(frame):
    source = DeclaredStructuralSource.model_validate(frame.pin.values())
    return DeclaredStructuralInput(
        question="Retain original annotations",
        scope="s",
        inventory_id="i",
        policy_id="p",
        sources=(source,),
        passages=(
            StructuralPassage(
                passage_id="original",
                source_ref=source.identity,
                start=0,
                end=len(frame.text),
                text=frame.text,
                scope="s",
            ),
        ),
        dependencies=(source.source_product,),
    )
