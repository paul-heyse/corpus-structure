"""Independent controlled columns, nominal primary products and source projections."""

from dataclasses import replace

import pytest
from annotation_support import controlled as controlled
from annotation_support import item

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.predicate_frames import predicate_frames
from methods.declared_primary_fixture import selected_source
from methods.navigation_fixture import source_primary_products


def primary_fixture(controlled, monkeypatch, *, heading=None, missing=None):
    body = "Ada must check valves." if heading else "Ada checks valves."
    start = len(heading) + 1 if heading else 0
    text = (heading + "\n" if heading else "") + body
    pieces = (
        [
            dict(
                kind="native_text",
                start=0,
                end=len(heading),
                item_ref="#/texts/0",
                source_field="text",
            ),
            dict(kind="synthetic_separator", start=len(heading), end=start),
        ]
        if heading
        else []
    )
    pieces.append(
        dict(
            kind="native_text",
            start=start,
            end=len(text),
            item_ref="#/texts/1",
            source_field="text",
        )
    )
    from pydantic import JsonValue

    items: list[dict[str, JsonValue]] = [dict(self_ref="#/groups/1", label="section")]
    if heading:
        items.append(
            dict(
                self_ref="#/texts/0",
                label="section_header",
                text=heading,
                orig=heading,
                parent={"$ref": "#/groups/1"},
            )
        )
    items.append(
        dict(
            self_ref="#/texts/1", label="text", text=body, orig=body, parent={"$ref": "#/groups/1"}
        )
    )
    _source, frame, _context = selected_source(text, pieces=pieces, items=items)
    profile = AnnotationProfile()
    request = replace(item(controlled, body, start=start, block_id="#/texts/1"), source=frame.pin)
    (product,) = annotations.annotate((request,), profile)
    rows = (
        (
            ("ada", "PROPN", "NNP", "nsubj", 2),
            ("must", "AUX", "MD", "aux", 2),
            ("check", "VERB", "VB", "ROOT", 2),
            ("valve", "NOUN", "NN", "dobj", 2),
            (".", "PUNCT", ".", "punct", 2),
        )
        if heading
        else (
            ("ada", "PROPN", "NNP", "nsubj", 1),
            ("check", "VERB", "VBZ", "ROOT", 1),
            ("valve", "NOUN", "NN", "dobj", 1),
            (".", "PUNCT", ".", "punct", 1),
        )
    )
    product = replace(
        product,
        tokens=tuple(
            replace(token, lemma=lemma, pos=pos, tag=tag, dependency=dep, head=head)
            for token, (lemma, pos, tag, dep, head) in zip(product.tokens, rows, strict=True)
        ),
    )
    products = [product]
    if heading:
        from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece

        request = replace(
            item(
                controlled,
                heading,
                start=0,
                block_id="#/texts/0",
                pieces=(
                    ProjectedPiece(
                        "#/texts/0", 0, len(heading), "native_text", source_field="text"
                    ),
                ),
            ),
            source=frame.pin,
        )
        (header,) = annotations.annotate((request,), profile)
        header = replace(
            header,
            tokens=tuple(
                replace(
                    token, pos="NOUN", tag="NN", lemma=heading[token.start : token.end].casefold()
                )
                for token in header.tokens
            ),
        )
        products.insert(0, header)
    if missing is not None:
        products = [
            replace(
                current,
                availability=tuple(
                    replace(column, status="absent") if column.attribute == missing else column
                    for column in current.availability
                ),
            )
            for current in products
        ]
    primary = source_primary_products(
        frame, products, profile=profile, native_profile=controlled.selection().native
    )
    monkeypatch.setattr(
        annotations, "pipeline", lambda *_: pytest.fail("consumer reran native NLP")
    )
    return frame, product, primary


def test_actual_native_heading_determines_policy_and_retains_examined_context(
    controlled, monkeypatch
):
    view, product, primary = primary_fixture(controlled, monkeypatch, heading="Requirements")
    (frame,) = predicate_frames(
        view.text, (product,), primary_products=(primary.construction,)
    ).frames
    assert frame.interpretation == "prescribed_action"
    body = primary.construction.inventory()
    term = next(row for row in body["terms"] if row["local_id"] == frame.primary_ref.local_id)
    construction = next(row for row in body["annotations"] if row["local_id"] in term["premises"])
    assert construction["context"]["examined"] == (
        dict(projection=view.projection_digest, native_pointer="#/texts/0", start=0, end=12),
        dict(projection=view.projection_digest, start=13, end=len(view.text)),
    )
    assert construction["context"]["focal"] == (
        dict(projection=view.projection_digest, start=13, end=len(view.text)),
    )


def test_common_native_to_primary_graph_to_domain_projection_runs_no_model(controlled, monkeypatch):
    view, product, primary = primary_fixture(controlled, monkeypatch)
    result = predicate_frames(view.text, (product,), primary_products=(primary.construction,))
    assert not result.issues
    (frame,) = result.frames
    assert view.text[slice(*frame.predicate.extents[0])] == "checks"
    assert [
        (role.name, tuple(view.text[a:b] for a, b in role.span.extents)) for role in frame.roles
    ] == [("actor", ("Ada",)), ("object", ("valves",))]
    assert frame.primary_ref is not None
    assert all(role.primary_ref is not None for role in frame.roles)
    assert frame.primary_ref.product.product_id == primary.construction.semantic_id
    # Native columns alone cannot trigger private role recognition.
    assert predicate_frames(view.text, (product,)).issues


def test_annotation_restoration_requires_exact_frozen_source_and_preserves_columns(
    controlled, monkeypatch
):
    from corpus_structure.semantic.sentence_products import retained_source_annotation_products

    _view, product, primary = primary_fixture(controlled, monkeypatch)
    (restored,) = retained_source_annotation_products(primary.source, primary.native)
    assert restored == product
    changed, _frame, _context = selected_source("Different source text.")
    with pytest.raises(ValueError, match="exact original source/scope"):
        retained_source_annotation_products(changed, primary.native)


def test_version6_contribution_projection_cites_actual_primary_nodes(controlled, monkeypatch):
    from corpus_structure.methods.predicate_contributions import declared_predicate_evidence
    from corpus_structure.semantic.source_contexts import NativeSourceContext, source_slice

    view, product, primary = primary_fixture(controlled, monkeypatch)
    context = NativeSourceContext(
        view,
        (),
        (source_slice(view, 0, len(view.text)),),
        "exact read",
        "test-layout",
        "selected",
        preparation=primary.prepared,
    )
    assert primary.native is not None
    evidence = declared_predicate_evidence(
        view,
        context,
        (product,),
        dependency=primary.native.semantic_id,
        primary_products=(primary.construction,),
        formal_products=(primary.formal,),
    )
    assert evidence.contributions and all(
        operation["operation_version"] == "6" for operation in evidence.operations
    )
    components = [row["component"] for row in evidence.contributions if "component" in row]
    frames = [row for row in components if row["kind"] == "predicate_frame"]
    assert len(frames) == 1
    assert frames[0]["primary_node"]["product_id"] == primary.construction.semantic_id
    assert all(member["primary_node"]["member_id"] for member in frames[0]["frame_members"])
    (frame_contribution,) = [
        row
        for row in evidence.contributions
        if row.get("component", {}).get("kind") == "predicate_frame"
    ]
    assert (
        frame_contribution["contribution_id"],
        "component/primary_node",
        0,
        frames[0]["primary_node"],
    ) in evidence.primary_evidence
    assert all(
        reference["product_id"] == primary.construction.semantic_id
        for _owner, _field, _position, reference in evidence.primary_evidence
    )


def test_numeric_condition_uses_exact_retained_formal_parts():

    from corpus_structure.methods.predicate_contributions import _condition

    text = "unless -2.50 < 3"
    _source, view, _context = selected_source(text)
    primary = source_primary_products(view, annotations=())
    layer = primary.formal
    condition, parts = _condition(
        "condition",
        "not_compare",
        text,
        marker_extents=((0, 6),),
        contiguous=True,
        formal_products=(layer,),
        projection=view.projection_digest,
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
    nodes = {row["local_id"]: row for row in layer.inventory()["annotations"]}
    assert [nodes[part["member_id"]]["formal"]["normalized"]["kind"] for part in parts] == [
        "decimal",
        "comparator",
        "decimal",
    ]
    assert all(part["product_id"] == layer.semantic_id for part in parts)
    # The same spelling at a different source address grants no lowering.
    refused, refs = _condition(
        "condition",
        "not_compare",
        text,
        marker_extents=((0, 6),),
        contiguous=True,
        formal_products=(layer,),
        projection="f" * 64,
        extents=((0, len(text)),),
    )
    assert refused is not None
    assert refused["kind"] == "escape" and refs == []


def test_formula_symbols_consume_canonical_inventory_and_preserve_coordinate_space():

    from corpus_structure.methods.structural_roles import captured_formula_symbols
    from corpus_structure.semantic.declared_formal_readings import declared_formal_layers

    text = r"\sigma_{X_1} + \mu_i"
    _source, view, _context = selected_source(
        "original",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/0", source_field="orig", start=0, end=8)
        ],
        items=[dict(self_ref="#/texts/0", label="formula", orig="original", text=text)],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
    )
    primary = source_primary_products(view, annotations=())
    layer = primary.formal
    formal_layers = declared_formal_layers((layer,), primary.source)
    rows, outcome = captured_formula_symbols(
        text,
        primary_layers=formal_layers,
        projection=view.projection_digest,
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
        and row["primary_node"]["product_id"] == layer.semantic_id
        for row in rows
    )
    assert captured_formula_symbols(
        text,
        primary_layers=formal_layers,
        projection=view.projection_digest,
        source_start=1,
        representation="recognized_latex",
    ) == ((), "unsupported")
    assert captured_formula_symbols(text) == ((), "unsupported")


@pytest.mark.parametrize(
    "missing,polarity", [("TAG", "positive"), ("MORPH", "unresolved"), ("SENT_START", None)]
)
def test_optional_native_columns_do_not_taint_independent_source_reading_coverage(
    controlled, monkeypatch, missing, polarity
):
    import json

    _view, _annotation, primary = primary_fixture(controlled, monkeypatch, missing=missing)
    assert primary.native is not None
    native = json.loads(primary.native.content)
    assert native["outcome"] == "partial"
    coverage = {row["family"]: row for row in json.loads(primary.construction.content)["coverage"]}
    source_readings = coverage["construction.source_readings"]
    if polarity is None:
        assert source_readings["outcome"] == "partial"
        assert all(
            row["outcome"] not in {"complete", "empty"}
            for name, row in coverage.items()
            if name in {"construction.predication", "construction.embedding"}
        )
        return
    assert source_readings["outcome"] == "complete" and not source_readings["unexamined"]
    inventory = primary.construction.inventory()
    terms = {row["local_id"]: row for row in inventory["terms"]}
    source_frames = [
        row
        for row in inventory["terms"]
        if row["kind"] == "predicate" and row["vocabulary"] == "source-linguistic-rules-1"
    ]
    assert source_frames
    assert {
        terms[edge["target"]]["value"]
        for frame in source_frames
        for edge in frame["children"]
        if edge["role"] == "polarity"
    } == {polarity}
