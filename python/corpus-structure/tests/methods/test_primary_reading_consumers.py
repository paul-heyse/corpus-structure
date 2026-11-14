"""Shared producer and domain projections agree on independent native role fixtures."""

from dataclasses import fields, replace
from types import SimpleNamespace

import pytest

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationProduct, AnnotationProfile
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.native_evidence_layers import (
    PrimaryAnnotationProduct,
)
from corpus_structure.methods.predicate_frames import predicate_frames
from corpus_structure.semantic.characterization import select_primary_layers
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_FAMILY, populate
from corpus_structure.semantic.proposals import NativeFrameSource
from methods.native_evidence_support import native_source as native_source
from methods.native_evidence_support import prepared as prepared


def primary_fixture(source, prepared, monkeypatch, *, heading=None):
    controlled, _, _, original, base, scope, operation = source
    from annotation_support import item

    body = "Ada must check valves." if heading is not None else "Ada checks valves."
    request = item(controlled, body, start=0 if heading is None else len(heading) + 1)
    (product,) = annotations.annotate([request])
    data = (
        list(
            zip(
                ("ada", "check", "valve", "."),
                ("PROPN", "VERB", "NOUN", "PUNCT"),
                ("NNP", "VBZ", "NN", "."),
                ("nsubj", "ROOT", "dobj", "punct"),
                (1, 1, 1, 1),
                strict=True,
            )
        )
        if heading is None
        else list(
            zip(
                ("ada", "must", "check", "valve", "."),
                ("PROPN", "AUX", "VERB", "NOUN", "PUNCT"),
                ("NNP", "MD", "VB", "NN", "."),
                ("nsubj", "aux", "ROOT", "dobj", "punct"),
                (2, 2, 2, 2, 2),
                strict=True,
            )
        )
    )
    tokens = tuple(
        replace(token, lemma=lemma, pos=pos, tag=tag, dependency=dependency, head=head)
        for token, (lemma, pos, tag, dependency, head) in zip(product.tokens, data, strict=True)
    )
    product = replace(product, tokens=tokens)
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourcePin
    from methods.pm2_source_support import source_context

    source_fields = [("#/texts/1", "text", request.block.text, request.block.text)]
    if heading is not None:
        source_fields = [
            ("#/texts/0", "text", heading, heading),
            (None, None, "\n", "\n"),
            *source_fields,
        ]
    context = source_context(source_fields, identity=7)
    native = context.primary
    assert isinstance(native, NativeFrameSource)
    ref = SimpleNamespace(
        **{
            **vars(original.ref),
            "key": native.unit_ref,
            "native_product": native.native_product,
            "projection_digest": native.projection_digest,
            "recipe_digest": native.recipe_digest,
        }
    )
    import json

    source_context_body = json.loads(native.native_context)
    view = SimpleNamespace(
        ref=ref,
        text=context.primary.text,
        pieces=source_context_body["pieces"],
        items=[
            dict(
                node,
                label="section_header" if node["self_ref"] == "#/texts/0" else "text",
                parent="#/groups/1",
            )
            for node in source_context_body["items"]
        ],
        ancestors=[],
        health={},
        integrated_context=None,
    )
    product = replace(product, source=NativeSourcePin.from_source(native_source_frame(view, ())))
    base = ref.native_product.values()
    scope = {
        **scope,
        "source_views": [
            dict(
                scope["source_views"][0],
                key=ref.key,
                base_document=base,
                projection_digest=ref.projection_digest,
                recipe_digest=ref.recipe_digest,
            )
        ],
        "selectors": [dict(projection=view.ref.projection_digest, start=0, end=len(view.text))],
    }
    native_products = []
    if heading is not None:
        from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece

        header_request = item(
            controlled,
            heading,
            start=0,
            block_id="paragraph:0",
            pieces=(ProjectedPiece("#/texts/0", 0, len(heading), "native_text"),),
        )
        (header,) = annotations.annotate([header_request])
        header = replace(
            header,
            source=product.source,
            tokens=tuple(
                replace(
                    token, pos="NOUN", tag="NN", lemma=heading[token.start : token.end].casefold()
                )
                for token in header.tokens
            ),
        )
        native_products.append((view, header))
    native_products.append((view, product))
    from methods.primary_native_fixture import primary_native_layer

    native_layer, native_pin = primary_native_layer(
        base,
        scope,
        operation,
        prepared,
        native_products,
        configuration=controlled.config.to_str(),
        digest="derived",
        reference=100,
        execution=controlled.selection().native,
        model="en_core_web_sm",
        version="3.8.0",
        runtime_version="3.8.18",
        components=(),
    )
    monkeypatch.setattr(
        annotations,
        "pipeline",
        lambda _: pytest.fail("primary recognition/replay reran native NLP"),
    )
    layer = ConstructionLayer(base, scope, {**operation, "key": "text.constructions"})
    populate(layer, view, native_pin, native_layer)
    report = layer.finish(prepared, dependencies={native_pin: native_layer})
    pin = report.reference(101)
    layers = {native_pin: native_layer, pin: report}
    wrapped = PrimaryAnnotationProduct(
        primary_layers=layers,
        **{field.name: getattr(product, field.name) for field in fields(product)},
    )
    return view, wrapped, layers, scope


def test_actual_native_heading_determines_policy_and_retains_examined_context(
    native_source, prepared, monkeypatch
):
    view, product, layers, _ = primary_fixture(
        native_source, prepared, monkeypatch, heading="Requirements"
    )
    (frame,) = predicate_frames(view.text, (product,)).frames
    assert frame.interpretation == "prescribed_action"
    body = layers[frame.primary_ref.layer].payload
    term = next(row for row in body["terms"] if row["local_id"] == frame.primary_ref.local_id)
    construction = next(row for row in body["annotations"] if row["local_id"] in term["premises"])
    assert construction["context"]["examined"] == [
        dict(projection=view.ref.projection_digest, native_pointer="#/texts/0", start=0, end=12),
        dict(projection=view.ref.projection_digest, start=13, end=len(view.text)),
    ]
    assert construction["context"]["focal"] == [
        dict(projection=view.ref.projection_digest, start=13, end=len(view.text))
    ]


def test_common_native_to_primary_graph_to_domain_projection_runs_no_model(
    native_source, prepared, monkeypatch
):
    view, product, layers, _ = primary_fixture(native_source, prepared, monkeypatch)
    result = predicate_frames(view.text, (product,))
    assert not result.issues
    (frame,) = result.frames
    assert view.text[slice(*frame.predicate.extents[0])] == "checks"
    assert [
        (role.name, tuple(view.text[a:b] for a, b in role.span.extents)) for role in frame.roles
    ] == [("actor", ("Ada",)), ("object", ("valves",))]
    assert frame.primary_ref is not None
    assert all(role.primary_ref is not None for role in frame.roles)
    assert frame.primary_ref.layer in layers
    plain = AnnotationProduct(
        **{field.name: getattr(product, field.name) for field in fields(product)}
    )
    # A detached native Doc alone cannot silently trigger private role recognition.
    assert predicate_frames(view.text, (plain,)).issues


def test_m1_annotation_consumer_requires_complete_frozen_primary_inputs(
    native_source, prepared, monkeypatch
):
    view, _, layers, _ = primary_fixture(native_source, prepared, monkeypatch)
    requested = []

    def primary(source_view_id, *, families):
        requested.append((source_view_id, tuple(families)))
        return select_primary_layers(layers, view, families=families)

    reader = SimpleNamespace(primary_characterization=primary)
    products, errors, result = consume_annotations(reader, view, AnnotationProfile())
    assert not errors and len(products) == 1
    assert PRIMARY_RULE_FAMILY in requested[0][1]
    assert len(result["primary_layers"]) == 2
    assert all(product.primary_layers for product in products)
    assert result["method"] == "retained.primary_characterization"
    with pytest.raises(ValueError, match="missing or incomplete"):
        select_primary_layers(
            {
                pin: layer
                for pin, layer in layers.items()
                if PRIMARY_RULE_FAMILY not in layer.payload["operation"]["produced_families"]
            },
            view,
            families=(PRIMARY_RULE_FAMILY,),
        )


def test_version6_contribution_projection_cites_actual_primary_nodes(
    native_source, prepared, monkeypatch
):
    from corpus_structure.methods.predicate_contributions import (
        predicate_results,
        publish_predicate_evidence,
    )
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        SourceSlice,
        record_source_pin,
    )

    view, product, layers, _ = primary_fixture(native_source, prepared, monkeypatch)
    frame = native_source_frame(view, ())
    context = NativeSourceContext(
        frame,
        (),
        (SourceSlice(view.ref.id, 0, len(view.text)),),
        "exact read",
        "test-layout",
        "selected",
    )
    rows, coordinates = [], {}
    results = predicate_results(
        frame, (product,), view.pieces, {node["self_ref"]: node for node in view.items}
    )
    operations = publish_predicate_evidence(
        frame,
        context,
        record_source_pin(frame),
        context.dependency_digest,
        results,
        (),
        None,
        None,
        rows,
        coordinates,
        version="6",
    )
    assert rows and all(operation["operation_version"] == "6" for operation in operations)
    components = [row["component"] for row in rows if "component" in row]
    frames = [row for row in components if row["kind"] == "predicate_frame"]
    assert len(frames) == 1 and frames[0]["primary_node"]["layer"] in [
        pin.values() for pin in layers
    ]
    assert all(member["primary_node"]["local_id"] for member in frames[0]["frame_members"])
    assert all(operation["primary_layers"] for operation in operations)
    for component in components:
        from corpus_structure.semantic.identity import canonical_bytes

        prepared.validate_json(
            {
                "predicate_frame": "PredicateFrameComponent",
                "predicate_cue": "PredicateCueComponent",
                "predicate_reading": "PredicateReadingComponent",
                "predicate_qualifier": "PredicateQualifierComponent",
            }[component["kind"]],
            canonical_bytes(component),
        )


def test_numeric_condition_uses_exact_retained_formal_parts(prepared):
    from semantic.primary_formal_fixture import operation, source

    from corpus_structure.methods.predicate_contributions import _condition
    from corpus_structure.semantic.formal_evidence import build_formal_layer

    text = "unless -2.50 < 3"
    view = source((text, "text", "", ""))
    layer = build_formal_layer(view, prepared, operation())
    pin = layer.reference(110)
    condition, parts = _condition(
        "condition",
        "not_compare",
        text,
        marker_extents=((0, 6),),
        contiguous=True,
        layers={pin: layer},
        projection=view.ref.projection_digest,
        extents=((0, len(text)),),
    )
    assert condition == dict(
        kind="not",
        term=dict(
            kind="compare",
            relation="<",
            lhs=dict(kind="expression", language="text", expression="-2.5", form="formula"),
            rhs=dict(kind="expression", language="text", expression="3", form="formula"),
        ),
    )
    nodes = {row["local_id"]: row for row in layer.payload["annotations"]}
    assert [nodes[part["local_id"]]["formal"]["normalized"]["kind"] for part in parts] == [
        "decimal",
        "comparator",
        "decimal",
    ]
    assert all(part["layer"] == pin.values() for part in parts)
    # The same spelling at a different source address grants no lowering.
    refused, refs = _condition(
        "condition",
        "not_compare",
        text,
        marker_extents=((0, 6),),
        contiguous=True,
        layers={pin: layer},
        projection="f" * 64,
        extents=((0, len(text)),),
    )
    assert refused is not None
    assert refused["kind"] == "escape" and refs == []


def test_formula_symbols_consume_canonical_inventory_and_preserve_coordinate_space(prepared):
    from semantic.primary_formal_fixture import operation, source

    from corpus_structure.methods.structural_roles import captured_formula_symbols
    from corpus_structure.semantic.formal_evidence import build_formal_layer

    text = r"\sigma_{X_1} + \mu_i"
    view = source(("original", "formula", text, "succeeded"))
    layer = build_formal_layer(view, prepared, operation(), math_start="formula")
    pin = layer.reference(111)
    rows, outcome = captured_formula_symbols(
        text,
        primary_layers={pin: layer},
        projection=view.ref.projection_digest,
        source_start=0,
        native_pointer="#/texts/0",
        representation="recognized_latex",
    )
    assert outcome == "parsed"
    assert [(row["name"], row["syntax_parent"]) for row in rows] == [
        (r"\sigma_{X_1}", None),
        ("X_1", r"\sigma_{X_1}"),
        (r"\mu_i", None),
        ("i", r"\mu_i"),
    ]
    assert all(
        row["coordinate_space"] == "recognized_latex"
        and row["primary_node"]["layer"] == pin.values()
        for row in rows
    )
    assert captured_formula_symbols(
        text,
        primary_layers={pin: layer},
        projection=view.ref.projection_digest,
        source_start=1,
        representation="recognized_latex",
    ) == ((), "unsupported")
    assert captured_formula_symbols(text) == ((), "unsupported")
