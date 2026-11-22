"""Independent math-source cues over current controlled native columns/products."""

import pytest
from annotation_support import ControlledPipeline

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, prepare_layout
from corpus_structure.semantic.construction_products import ConstructionOptions
from corpus_structure.semantic.constructions.math_scope import (
    Binders,
    NativeDomainRule,
    retained_math_scope_products,
)
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.native_source_view import thaw_native
from methods.declared_primary_fixture import profiles, retained_products, selected_source


def produce(monkeypatch, text, *, binders, rules=(), math=(), recognized=None):
    nlp = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: nlp)
    profile = AnnotationProfile(execution_profile=nlp.selection().native.fingerprint)
    pieces = [
        dict(
            kind="native_text",
            item_ref="#/texts/0",
            source_field="orig" if recognized is not None else "text",
            start=0,
            end=len(text),
        )
    ]
    source, frame, context = selected_source(
        text,
        pieces=pieces,
        items=[
            dict(
                self_ref="#/texts/0",
                label="formula" if recognized is not None else "text",
                orig=text,
                text=recognized if recognized is not None else text,
            )
        ],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")]
        if recognized is not None
        else (),
    )
    block = Block(text, math, (), ())
    request = AnnotationInput(
        frame.pin,
        "#/texts/0",
        "paragraph",
        block,
        prepare_layout(nlp.language, block, start=0),
        (
            ProjectedPiece(
                "#/texts/0",
                0,
                len(text),
                "native_text",
                source_field="orig" if recognized is not None else "text",
            ),
        ),
    )
    (product,) = annotate((request,), profile)
    native, _ = retained_products(source, frame, context, product, profile)
    formal, construction = profiles()
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    built = construction.run(
        source,
        (primary,),
        ConstructionOptions(math_scope_binders=binders, math_domain_rules=rules),
        sentences=native,
        subject_context=context,
    )
    return source, built


def test_primary_binder_flags_targets_and_read_do_not_match_again(monkeypatch):
    binders = Binders(
        sentence_initial=("Suppose",),
        clause=("where",),
        reopen=("again",),
        section_wide=("throughout this section",),
    )
    text = "Suppose again x throughout this section where y."
    source, product = produce(monkeypatch, text, binders=binders, math=((14, 15), (45, 46)))
    from corpus_structure.semantic.constructions import math_scope

    monkeypatch.setattr(
        math_scope, "Matcher", lambda *_a, **_k: pytest.fail("consumer matched language")
    )
    retained = retained_math_scope_products((product,), source, binders=binders)
    assert retained.complete and retained.sentences == ((0, len(text)),)
    assert retained.flags(14) == {"initial", "reopen", "section_wide"}
    assert retained.flags(45) == {"initial", "reopen", "section_wide", "clause"}
    assert not retained_math_scope_products(
        (product,), source, binders=Binders(sentence_initial=("Let",))
    ).complete


def test_primary_domain_candidates_keep_rule_metadata_and_conflicts(monkeypatch):
    rules = (
        NativeDomainRule(
            rule_id="theorem", pattern=r"^Theorem", statement_kind="theorem", scope_role="statement"
        ),
        NativeDomainRule(
            rule_id="claim", pattern=r"Theorem", statement_kind="claim", scope_role="statement"
        ),
    )
    source, product = produce(monkeypatch, "Theorem 1.", binders=None, rules=rules)
    from corpus_structure.semantic.constructions import math_scope

    monkeypatch.setattr(
        math_scope.re, "compile", lambda *_a, **_k: pytest.fail("consumer reran domain regex")
    )
    retained = retained_math_scope_products((product,), source, binders=None, rules=rules)
    assert retained.complete
    assert [(start, pointer, rule.rule_id) for start, pointer, rule in retained.markers] == [
        (0, "#/texts/0", "claim"),
        (0, "#/texts/0", "theorem"),
    ]
    assert retained.markers[0][2].pattern == "Theorem"
    assert not retained_math_scope_products((product,), source, binders=None, rules=()).complete


def test_native_formula_domain_marker_keeps_represented_coordinates(monkeypatch):
    rules = (
        NativeDomainRule(
            rule_id="t", pattern="^T", statement_kind="theorem", scope_role="statement"
        ),
    )
    source, product = produce(
        monkeypatch, "Original", binders=None, rules=rules, math=((0, 8),), recognized="T"
    )
    retained = retained_math_scope_products((product,), source, binders=None, rules=rules)
    assert retained.complete and retained.markers == ((0, "#/texts/0", rules[0]),)
    inventory = product.inventory()
    marker = next(row for row in inventory["annotations"] if row["kind"] == "math.domain_marker")
    assert marker["external_premises"]
    occurrences = {row["local_id"]: row for row in inventory["occurrences"]}
    assert [
        (e["start"], e["end"], e["text"])
        for oid in marker["occurrences"]
        for e in occurrences[oid]["extents"]
    ] == [(0, 8, "Original")]
    terms = {row["local_id"]: row for row in inventory["terms"]}
    values = {
        m["role"]: terms[m["member"]]["value"]
        for m in inventory["memberships"]
        if m["group"] == marker["local_id"]
    }
    assert (values["coordinate_space"], values["input_start"], values["input_end"]) == (
        "recognized_latex",
        "0",
        "1",
    )


def test_primary_scope_preserves_native_block_trailing_space_and_sentence_bounds(monkeypatch):
    binders = Binders(sentence_initial=("Let",))
    source, product = produce(monkeypatch, "Let x. ", binders=binders, math=((4, 5),))
    retained = retained_math_scope_products((product,), source, binders=binders)
    assert (
        retained.complete and retained.sentences == ((0, 6),) and retained.flags(4) == {"initial"}
    )


@pytest.mark.parametrize("equal_text", [False, True])
def test_primary_math_scope_refuses_foreign_original_even_with_equal_projection(
    monkeypatch, equal_text
):
    from corpus_structure.semantic.original_documents import original_document_subject
    from corpus_structure.semantic.source_products import FrozenNativeSource

    binders = Binders(sentence_initial=("Let", "Suppose"))
    source, product = produce(monkeypatch, "Let x.", binders=binders)
    sibling, sibling_product = produce(
        monkeypatch, "Let x." if equal_text else "Suppose z follows.", binders=binders
    )
    value = thaw_native(sibling.value)
    value["source"] = {
        **value["source"],
        "document": "unadmitted:another-original",
        "document_subject": original_document_subject("unadmitted:another-original"),
    }
    foreign = FrozenNativeSource.acquire(profiles()[0].prepared, value)
    assert (
        foreign.value["source"]["projection"] == source.value["source"]["projection"]
    ) is equal_text
    with pytest.raises(ValueError, match="exact original source/scope"):
        retained_math_scope_products((product,), foreign, binders=binders)
    if not equal_text:
        with pytest.raises(ValueError, match="exact original source/scope"):
            retained_math_scope_products((sibling_product,), source, binders=binders)
