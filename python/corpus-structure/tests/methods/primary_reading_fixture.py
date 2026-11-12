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


def native_execution_for_product(product, profile=None, *, native_profile=None):
    """Authenticate a fixture's carried execution; legacy fixtures remain unprofiled."""
    from dataclasses import replace
    from hashlib import sha256

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.observations import source_python

    retained = {
        canonical_bytes(source_python(row["execution_profile"]))
        for layer in getattr(product, "primary_layers", {}).values()
        for row in layer.payload.get("native_runs", ())
        if row["provider"] == "spacy" and "execution_profile" in row
    }
    if len(retained) > 1:
        raise ValueError("fixture contains competing native execution profiles")
    carried = NativeProfile.from_content(next(iter(retained))) if retained else None
    if native_profile is None:
        native_profile = carried
    elif carried is not None and native_profile != carried:
        raise ValueError("explicit fixture execution differs from retained native profile")
    if profile is None:
        configuration = (
            SentenceConfig.model_validate(native_profile.parameters)
            if native_profile is not None
            else SentenceConfig(
                spacy_version=product.spacy_version,
                model=product.model,
                model_version=product.model_version,
                exclude=("ner",),
            )
        )
        profile = AnnotationProfile(configuration)
    if native_profile is None:
        if profile.execution_profile is not None:
            raise ValueError("explicit fixture execution requires a complete native snapshot")
        if product.profile_digest != sha256(canonical_bytes(profile.identity())).hexdigest():
            raise ValueError(
                "profiled fixture columns require their original complete native snapshot"
            )
        return None
    effective = replace(profile, execution_profile=native_profile.fingerprint)
    if sha256(canonical_bytes(effective.identity())).hexdigest() != product.profile_digest:
        raise ValueError("fixture must carry the exact execution profile of its annotation product")
    return native_profile


def primary_product(
    text,
    product,
    profile,
    *,
    configuration="independent-native-columns",
    rules=(),
    native_profile=None,
):
    execution = native_execution_for_product(product, profile, native_profile=native_profile)
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
    if execution is not None:
        from corpus_structure.semantic.observations import source_value

        run["execution_profile"] = source_value(execution.wire)
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
