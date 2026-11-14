"""Math language cues are retained before domain binding; controlled native columns."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from annotation_support import ControlledPipeline, item

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import annotate
from corpus_structure.ingest.sentences import Block
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.math_scope import (
    FAMILY,
    Binders,
    NativeDomainRule,
    populate_math_scope,
    retained_math_scope,
)
from methods.primary_reading_fixture import prepared


def produce(
    monkeypatch, text, *, binders, rules=(), math=(), recognized=None, identity=7, projection=None
):
    nlp = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: nlp)
    request = item(nlp, text, start=0, block=Block(text, math, (), ()), identity=identity)
    if projection is not None:
        request = replace(request, source=replace(request.source, projection_digest=projection))
    (product,) = annotate([request])
    source = product.source
    view = SimpleNamespace(
        ref=SimpleNamespace(
            id=source.source_view_id,
            key=source.unit_ref,
            native_product=source.native_product,
            projection_digest=source.projection_digest,
            recipe_digest=source.recipe_digest,
            document_id=3,
            section_pointer=source.section_pointer,
            membership=source.membership,
        ),
        text=text,
        pieces=[p.to_wire() for p in request.native_pieces],
        items=[dict(self_ref="#/texts/1", text=text, label="text")],
        ancestors=[],
    )
    scope = dict(
        source_view_ids=[source.source_view_id],
        source_views=[
            dict(
                source_view_id=source.source_view_id,
                key=source.unit_ref,
                base_document=source.native_product.values(),
                section_pointer=source.section_pointer,
                membership=source.membership,
                projection_digest=source.projection_digest,
                recipe_digest=source.recipe_digest,
            )
        ],
        profile="math-source",
        selectors=[dict(projection=source.projection_digest, start=0, end=len(text))],
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="fixture",
        model="native",
        grammar="none",
        configuration="cfg",
        input="input",
        context="source",
    )
    from methods.primary_native_fixture import primary_native_layer

    raw, pin = primary_native_layer(
        source.native_product.values(),
        scope,
        operation,
        prepared(),
        ((view, product),),
        configuration=nlp.config.to_str(),
        digest="derived",
        reference=101,
        execution=nlp.selection().native,
    )
    builder = ConstructionLayer(
        source.native_product.values(),
        scope,
        dict(operation, key="text.constructions"),
        families=(FAMILY,),
    )
    dependencies = {pin: raw}
    if recognized is not None:
        from corpus_structure.semantic.formal_evidence import build_formal_layer

        view.items[0].update(label="formula", text=recognized, orig=text)
        view.pieces[0]["source_field"] = "orig"
        view.health = dict(formula_outcomes=[dict(pointer="#/texts/1", outcome="succeeded")])
        from corpus_structure.core.method import SourceViewRef
        from corpus_structure.semantic.source_views import PreparedSourceView

        assert source.membership in {"direct", "descendants"}
        formal_view = PreparedSourceView(
            SourceViewRef(
                source.source_view_id,
                source.unit_ref,
                3,
                source.native_product,
                source.section_pointer,
                source.membership,
                source.projection_digest,
                source.recipe_digest,
            ),
            text,
            tuple(view.pieces),
            tuple(view.items),
            (),
            view.health,
        )
        formal = build_formal_layer(
            formal_view, prepared(), dict(operation, key="text.formal_evidence")
        )
        dependencies[formal.reference(103)] = formal
    populate_math_scope(builder, view, dependencies, nlp.vocab, binders=binders, rules=rules)
    result = builder.finish(prepared(), dependencies=dependencies)
    return view, {**dependencies, result.reference(102): result}


def test_primary_binder_flags_targets_and_read_do_not_match_again(monkeypatch):
    binders = Binders(
        sentence_initial=("Suppose",),
        clause=("where",),
        reopen=("again",),
        section_wide=("throughout this section",),
    )
    text = "Suppose again x throughout this section where y."
    view, layers = produce(monkeypatch, text, binders=binders, math=((14, 15), (45, 46)))
    from corpus_structure.semantic.constructions import math_scope

    monkeypatch.setattr(
        math_scope, "Matcher", lambda *_a, **_k: pytest.fail("consumer matched language")
    )
    retained = retained_math_scope(layers, view, binders=binders)
    assert retained.complete
    assert retained.sentences == ((0, len(text)),)
    assert retained.flags(14) == frozenset({"initial", "reopen", "section_wide"})
    assert retained.flags(45) == frozenset({"initial", "reopen", "section_wide", "clause"})
    changed = Binders(sentence_initial=("Let",))
    assert not retained_math_scope(layers, view, binders=changed).complete


def test_primary_domain_candidates_keep_rule_metadata_and_conflicts(monkeypatch):
    rules = (
        NativeDomainRule(
            rule_id="theorem", pattern=r"^Theorem", statement_kind="theorem", scope_role="statement"
        ),
        NativeDomainRule(
            rule_id="claim", pattern=r"Theorem", statement_kind="claim", scope_role="statement"
        ),
    )
    view, layers = produce(monkeypatch, "Theorem 1.", binders=None, rules=rules)
    from corpus_structure.semantic.constructions import math_scope

    monkeypatch.setattr(
        math_scope.re, "compile", lambda *_a, **_k: pytest.fail("consumer reran domain regex")
    )
    retained = retained_math_scope(layers, view, binders=None, rules=rules)
    assert retained.complete
    assert [(start, pointer, rule.rule_id) for start, pointer, rule in retained.markers] == [
        (0, "#/texts/1", "claim"),
        (0, "#/texts/1", "theorem"),
    ]
    assert retained.markers[0][2].pattern == "Theorem"
    assert not retained_math_scope(layers, view, binders=None, rules=()).complete


def test_native_formula_domain_marker_keeps_represented_coordinates(monkeypatch):
    rules = (
        NativeDomainRule(
            rule_id="t", pattern="^T", statement_kind="theorem", scope_role="statement"
        ),
    )
    view, layers = produce(
        monkeypatch, "Original", binders=None, rules=rules, math=((0, 8),), recognized="T"
    )
    retained = retained_math_scope(layers, view, binders=None, rules=rules)
    assert retained.complete and retained.markers == ((0, "#/texts/1", rules[0]),)
    body = next(
        layer.payload
        for layer in layers.values()
        if FAMILY in layer.payload["operation"]["produced_families"]
    )
    marker = next(row for row in body["annotations"] if row["kind"] == "math.domain_marker")
    assert marker["external_premises"]
    occurrences = {row["local_id"]: row for row in body["occurrences"]}
    assert [
        (e["start"], e["end"], e["text"])
        for oid in marker["occurrences"]
        for e in occurrences[oid]["extents"]
    ] == [(0, 8, "Original")]
    terms = {row["local_id"]: row for row in body["terms"]}
    values = {
        m["role"]: terms[m["member"]]["value"]
        for m in body["memberships"]
        if m["group"] == marker["local_id"]
    }
    assert (values["coordinate_space"], values["input_start"], values["input_end"]) == (
        "recognized_latex",
        "0",
        "1",
    )


def test_primary_scope_preserves_native_block_trailing_space_and_sentence_bounds(monkeypatch):
    binders = Binders(sentence_initial=("Let",))
    view, layers = produce(monkeypatch, "Let x. ", binders=binders, math=((4, 5),))
    retained = retained_math_scope(layers, view, binders=binders)
    assert retained.complete
    assert retained.sentences == ((0, 6),)
    assert retained.flags(4) == frozenset({"initial"})


@pytest.mark.parametrize("duplicate_projection", [False, True])
def test_primary_math_scope_filters_exact_views_before_projecting_mixed_layer(
    monkeypatch, duplicate_projection
):
    from copy import deepcopy

    from corpus_structure.semantic.characterization import validate_layer
    from corpus_structure.semantic.identity import canonical_bytes

    binders = Binders(sentence_initial=("Let", "Suppose"))
    selected_view, selected_layers = produce(monkeypatch, "Let x.", binders=binders)
    sibling_view, sibling_layers = produce(
        monkeypatch,
        "Let x." if duplicate_projection else "Suppose z follows.",
        binders=binders,
        identity=8,
        projection=None if duplicate_projection else "d" * 64,
    )
    assert selected_view.ref.id != sibling_view.ref.id
    assert (
        selected_view.ref.projection_digest == sibling_view.ref.projection_digest
    ) is duplicate_projection
    reports = [
        next(
            report
            for report in layers.values()
            if FAMILY in report.payload["operation"]["produced_families"]
        )
        for layers in (selected_layers, sibling_layers)
    ]
    dependencies = {
        pin: report
        for layers in (selected_layers, sibling_layers)
        for pin, report in layers.items()
        if FAMILY not in report.payload["operation"]["produced_families"]
    }

    def unique(rows):
        return list({canonical_bytes(row): row for row in rows}.values())

    body = deepcopy(reports[0].payload)
    body["source_scope"] = dict(
        body["source_scope"],
        source_view_ids=[selected_view.ref.id, sibling_view.ref.id],
        source_views=[
            source
            for report in reports
            for source in report.payload["source_scope"]["source_views"]
        ],
        selectors=unique(
            [
                selector
                for report in reports
                for selector in report.payload["source_scope"]["selectors"]
            ]
        ),
    )
    body["dependencies"] = [pin.values() for pin in dependencies]
    body["operation"]["required_layers"] = body["dependencies"]
    # Portable occurrence IDs deliberately ignore database view placement. An
    # identical-projection report therefore retains one original view's custody;
    # it must not be relabelled as evidence for the other declared view.
    inventories = reports[1:] if duplicate_projection else reports
    for inventory in ("annotations", "occurrences", "memberships", "terms", "roles", "choices"):
        body[inventory] = unique(
            [row for report in inventories for row in report.payload[inventory]]
        )
    for field in ("eligible", "examined", "unexamined"):
        body["coverage"][0][field] = unique(
            [
                selector
                for report in reports
                for selector in report.payload["coverage"][0].get(field, ())
            ]
        )
    combined = validate_layer(prepared(), body, dependencies=dependencies)
    pin = combined.reference(104)
    from corpus_structure.semantic.constructions import math_scope

    monkeypatch.setattr(
        math_scope, "Matcher", lambda *_a, **_k: pytest.fail("reader matched language")
    )
    selected = retained_math_scope({**dependencies, pin: combined}, selected_view, binders=binders)
    sibling = retained_math_scope({**dependencies, pin: combined}, sibling_view, binders=binders)
    if duplicate_projection:
        assert not selected.complete and selected.sentences == ()
        assert selected.flags(4) == frozenset()
    else:
        assert selected.complete and selected.sentences == ((0, 6),)
        assert selected.flags(4) == frozenset({"initial"})
    assert sibling.complete and sibling.sentences == ((0, len(sibling_view.text)),)

    # A valid layer can declare both views while retaining evidence for only one.
    # Shared projection coverage cannot substitute a sibling's policy or cues.
    foreign = deepcopy(reports[1].payload)
    foreign["source_scope"] = body["source_scope"]
    foreign_layer = validate_layer(prepared(), foreign, dependencies=dependencies)
    absent = retained_math_scope(
        {**dependencies, foreign_layer.reference(105): foreign_layer},
        selected_view,
        binders=binders,
    )
    assert not absent.complete and absent.sentences == () and absent.flags(4) == frozenset()

    if duplicate_projection:
        return

    # Keep strict support checks after filtering: a selected cue cannot borrow a
    # valid sibling sentence even when that sentence has the same projection.
    crossed = deepcopy(body)
    selected_initial = next(
        row for row in reports[0].payload["annotations"] if row["kind"] == "math.scope_initial"
    )
    foreign_sentence = next(
        row for row in reports[1].payload["annotations"] if row["kind"] == "math.scope_sentence"
    )
    membership = next(
        row
        for row in crossed["memberships"]
        if row["group"] == selected_initial["local_id"] and row["role"] == "sentence"
    )
    membership["member"] = foreign_sentence["local_id"]
    crossed_layer = validate_layer(prepared(), crossed, dependencies=dependencies)
    with pytest.raises(ValueError, match="no exact literal support"):
        retained_math_scope(
            {**dependencies, crossed_layer.reference(106): crossed_layer},
            selected_view,
            binders=binders,
        )
