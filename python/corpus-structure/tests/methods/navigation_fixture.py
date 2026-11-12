"""Execute the primary navigation owner, then hand retained products to consumers."""

import json
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any

from corpus_structure.methods.native_evidence import native_run
from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES, NativeEvidenceBuilder
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.navigation import FAMILY, populate_navigation
from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_FAMILY, populate
from corpus_structure.semantic.formal_evidence import build_formal_layer

from .primary_reading_fixture import prepared


def primary_navigation(
    view, annotations=None, *, formal=False, task_start=201, native_profile=None
):
    if annotations is None:
        from corpus_structure.ingest.annotations import AnnotationProfile
        from corpus_structure.ingest.sentences import pipeline

        profile = AnnotationProfile()
        nlp: Any = pipeline(profile.configuration)
        native_profile = nlp.selection().native
        annotations = prepare_source(view, profile=profile, annotations_only=True).annotations
    scope = dict(
        source_view_ids=[view.ref.id],
        source_views=[
            dict(
                source_view_id=view.ref.id,
                key=view.ref.key,
                base_document=view.ref.native_product.values(),
                section_pointer=view.ref.section_pointer,
                membership=view.ref.membership,
                projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest,
            )
        ],
        profile="navigation-fixture",
        selectors=[dict(projection=view.ref.projection_digest, start=0, end=len(view.text))],
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="fixture",
        model="fixture",
        grammar="none",
        configuration="fixture",
        input="fixture",
        context="source",
    )
    native = NativeEvidenceBuilder(
        view.ref.native_product.values(),
        scope,
        operation,
        profile="spacy_only",
        families=SPACY_FAMILIES,
    )
    for product in annotations:
        native.spacy(view, product, "spacy")
    if annotations:
        product = annotations[0]
        run = native_run(
            "spacy",
            "spacy_only",
            "fixture",
            model=product.model,
            version=product.model_version,
            runtime_version=product.spacy_version,
            layout=[],
            text=[],
            components=[asdict(c) for c in product.components],
        )
        run["configuration_digest"] = product.pipeline_config_digest
        from corpus_structure.semantic.observations import source_value

        from .primary_reading_fixture import native_execution_for_product

        execution = native_execution_for_product(product, native_profile=native_profile)
        if execution is not None:
            run["execution_profile"] = source_value(execution.wire)
        from corpus_structure.methods.native_evidence_layers import SPACY_COLUMNS

        run["availability"] = [
            dict(family=SPACY_COLUMNS[row.attribute], attribute=row.attribute, status=row.status)
            for row in product.availability
        ]
        native.native_runs.append(run)
    native_layer = native.finish(prepared())
    native_pin = native_layer.reference(task_start)
    layers = {native_pin: native_layer}
    navigation = ConstructionLayer(
        view.ref.native_product.values(),
        scope,
        dict(operation, key="text.constructions"),
        families=(FAMILY, PRIMARY_RULE_FAMILY),
    )
    if annotations:
        populate(navigation, view, native_pin, native_layer)
    populate_navigation(navigation, view, layers)
    report = navigation.finish(prepared(), dependencies=layers)
    layers[report.reference(task_start + 1)] = report
    if formal:
        formal_layer = build_formal_layer(
            view, prepared(), dict(operation, key="text.formal_evidence", model="none")
        )
        layers[formal_layer.reference(task_start + 2)] = formal_layer
    return layers


def view_from_frame(frame):
    context = json.loads(frame.native_context)
    return SimpleNamespace(
        ref=SimpleNamespace(
            id=frame.source_view_id,
            key=frame.unit_ref,
            native_product=frame.native_product,
            section_pointer=frame.section_pointer,
            membership=frame.membership,
            projection_digest=frame.projection_digest,
            recipe_digest=frame.recipe_digest,
        ),
        text=frame.text,
        pieces=context["pieces"],
        items=context["items"],
        ancestors=context["ancestors"],
        health=context["health"],
        integrated_context=None,
    )
