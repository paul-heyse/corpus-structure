"""Authenticate authored/native columns through the ordinary primary model in tests."""

from dataclasses import asdict, fields
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from corpus_structure.methods.annotation_rules import PreparedAnnotationRules
from corpus_structure.methods.native_evidence import native_run
from corpus_structure.methods.native_evidence_layers import (
    SPACY_FAMILIES,
    NativeEvidenceBuilder,
    PrimaryAnnotationProduct,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.constructions.declarations import FAMILIES
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.named import NAMED_FAMILY, populate_named
from corpus_structure.semantic.constructions.retained_rules import _frame_vocabulary, populate


@lru_cache(maxsize=1)
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def primary_product(
    text, product, profile, *, configuration="independent-native-columns", rules=()
):
    pin = product.source
    view = SimpleNamespace(
        ref=SimpleNamespace(
            id=pin.source_view_id,
            key=pin.unit_ref,
            native_product=pin.native_product,
            section_pointer=pin.section_pointer,
            membership=pin.membership,
            projection_digest=pin.projection_digest,
            recipe_digest=pin.recipe_digest,
        ),
        text=text,
        pieces=[piece.to_wire() for piece in product.native_pieces],
        items=[
            dict(self_ref=pointer, label="text")
            for pointer in dict.fromkeys(p.item_ref for p in product.native_pieces if p.item_ref)
        ],
        ancestors=[],
        health={},
        integrated_context=None,
    )
    scope = dict(
        source_view_ids=[pin.source_view_id],
        source_views=[
            dict(
                source_view_id=pin.source_view_id,
                key=pin.unit_ref,
                base_document=pin.native_product.values(),
                section_pointer=pin.section_pointer,
                membership=pin.membership,
                projection_digest=pin.projection_digest,
                recipe_digest=pin.recipe_digest,
            )
        ],
        profile="test-source-readings",
        selectors=[
            dict(projection=pin.projection_digest, start=product.block_start, end=product.block_end)
        ],
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="test-runtime",
        model="test-native",
        grammar="none",
        configuration="test-cfg",
        input="test-input",
        context="exact-authored-columns",
    )
    native = NativeEvidenceBuilder(
        pin.native_product.values(), scope, operation, profile="spacy_only", families=SPACY_FAMILIES
    )
    native.spacy(view, product, "spacy")
    run = native_run(
        "spacy",
        "spacy_only",
        configuration,
        model=product.model,
        version=product.model_version,
        runtime_version=product.spacy_version,
        layout=[],
        text=[],
        components=[asdict(c) for c in product.components],
    )
    run["configuration_digest"] = product.pipeline_config_digest
    from corpus_structure.methods.native_evidence_layers import SPACY_COLUMNS

    run["availability"] = [
        dict(family=SPACY_COLUMNS[row.attribute], attribute=row.attribute, status=row.status)
        for row in product.availability
    ]
    native.native_runs.append(run)
    native_layer = native.finish(prepared())
    native_pin = native_layer.reference(101)
    layer = ConstructionLayer(
        pin.native_product.values(),
        scope,
        dict(operation, key="text.constructions"),
        families=(*FAMILIES, NAMED_FAMILY) if rules else FAMILIES,
    )
    populate(layer, view, native_pin, native_layer)
    if rules:
        populate_named(
            layer,
            view,
            native_pin,
            native_layer,
            PreparedAnnotationRules(_frame_vocabulary(), rules=rules),
        )
    reading = layer.finish(prepared(), dependencies={native_pin: native_layer})
    return PrimaryAnnotationProduct(
        primary_layers={native_pin: native_layer, reading.reference(102): reading},
        **{field.name: getattr(product, field.name) for field in fields(product)},
    )
