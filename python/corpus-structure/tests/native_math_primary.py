"""Stage actual primary owners over the native math tests' independently authored views."""

from dataclasses import asdict, replace
from functools import cache
from hashlib import sha256

from corpus_structure.core.evidence import MacroDef
from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout
from corpus_structure.methods.native_evidence import native_run
from corpus_structure.methods.native_evidence_layers import (
    SPACY_COLUMNS,
    SPACY_FAMILIES,
    NativeEvidenceBuilder,
)
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.math_scope import FAMILY, populate_math_scope
from corpus_structure.semantic.formal_evidence import build_formal_layer, grammar_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourcePin
from corpus_structure.semantic.types import PreparedRelease


def native_view(view):
    """Complete the authored physical piece contract without rebasing any coordinates."""
    pieces = tuple(
        {"kind": "native_text", "source_field": "text", **piece} for piece in view.pieces
    )
    projection = dict(
        text=view.text,
        pieces=pieces,
        items=[node["self_ref"] for node in view.items],
        ancestors=view.ancestors,
        health=view.health,
    )
    return replace(
        view,
        pieces=pieces,
        ref=replace(view.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )


def primary_layers(view, prepared, *, binders=None, rules=(), macros=None, task_start=100):
    """An explicit upstream whole-view block, with exact native pieces and protected math atoms."""
    base = view.ref.native_product.values()
    selector = (
        dict(projection=view.ref.projection_digest, start=0, end=len(view.text))
        if view.text
        else dict(projection=view.ref.projection_digest, native_pointer=view.ref.section_pointer)
    )
    scope = dict(
        source_view_ids=[view.ref.id],
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=base,
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
        ],
        profile="independent-native-math-fixture",
        selectors=[selector],
    )
    config = dict(
        binders=None if binders is None else binders.model_dump(mode="json"),
        rules=[rule.model_dump(mode="json") for rule in rules],
        macros=macros or {},
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="fixture-local-spacy",
        model="fixture-local-spacy",
        grammar="none",
        configuration=sha256(canonical_bytes(config)).hexdigest(),
        input=view.ref.projection_digest,
        context="whole-view-native-math-fixture",
    )
    native = NativeEvidenceBuilder(
        base, scope, operation, profile="spacy_only", families=SPACY_FAMILIES
    )
    profile = AnnotationProfile()
    nlp = pipeline(profile.configuration)
    if view.text.strip():
        nodes = {node["self_ref"]: node for node in view.items}
        math = tuple(
            (piece["start"], piece["end"])
            for piece in view.pieces
            if nodes[piece["item_ref"]].get("label") == "formula"
        )
        block = Block(view.text, math, (), ())
        request = AnnotationInput(
            NativeSourcePin.from_source(native_source_frame(view, ())),
            view.ref.section_pointer,
            "paragraph",
            block,
            prepare_layout(nlp, block),
            tuple(ProjectedPiece(**piece) for piece in view.pieces),
        )
        (product,) = annotate((request,), profile)
        native.spacy(view, product, "spacy")
        run = native_run(
            "spacy",
            "spacy_only",
            nlp.config.to_str(),
            model=product.model,
            version=product.model_version,
            runtime_version=product.spacy_version,
            layout=[],
            text=[],
            components=[asdict(c) for c in product.components],
        )
        run["configuration_digest"] = product.pipeline_config_digest
        run["availability"] = [
            dict(family=SPACY_COLUMNS[row.attribute], attribute=row.attribute, status=row.status)
            for row in product.availability
        ]
        native.native_runs.append(run)
    else:
        for family in SPACY_FAMILIES:
            native.record(family, [selector])
    native_layer = native.finish(prepared)
    layers = {native_layer.reference(task_start): native_layer}
    formal = build_formal_layer(
        view,
        prepared,
        dict(operation, key="text.formal_evidence", grammar=grammar_identity()),
        macros={name: MacroDef(body=body) for name, body in (macros or {}).items()},
    )
    layers[formal.reference(task_start + 1)] = formal
    construction = ConstructionLayer(
        base, scope, dict(operation, key="text.constructions"), families=(FAMILY,)
    )
    populate_math_scope(construction, view, layers, nlp.vocab, binders=binders, rules=rules)
    if not view.pieces:
        construction.record(FAMILY, selector, "empty")
    layer = construction.finish(prepared, dependencies=layers)
    layers[layer.reference(task_start + 2)] = layer
    return layers


@cache
def pure_source_release() -> PreparedRelease:
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.contracts import trusted_execution_inputs

    inputs = trusted_execution_inputs()
    return prepare_release(
        inputs.schema,
        composed_dependencies(ResolvedDependencies(), inputs),
        PreparationProfile(version="semantic-2"),
    )
