"""Named primary-rule execution and pure consumer projection, no model quality claim."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from annotation_support import ControlledPipeline, item

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import annotate
from corpus_structure.methods.annotation_rules import (
    AnnotationRule,
    PreparedAnnotationRules,
    RoleBinding,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.named import (
    NAMED_FAMILY,
    RetainedNamedRules,
    populate_named,
)
from corpus_structure.semantic.constructions.named_nominations import naming_nomination
from corpus_structure.semantic.source_contexts import NativeSourcePin


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )


def test_named_rules_execute_upstream_once_and_replay_exact_roles_without_nlp(
    prepared, monkeypatch
):
    controlled = ControlledPipeline()
    monkeypatch.setattr(annotations, "pipeline", lambda _: controlled)
    request = item(controlled, "X X é.", start=0)
    (product,) = annotate([request])
    pin = product.source
    assert isinstance(pin, NativeSourcePin)
    view = SimpleNamespace(
        ref=SimpleNamespace(
            id=pin.source_view_id,
            key=pin.unit_ref,
            native_product=pin.native_product,
            projection_digest=pin.projection_digest,
            recipe_digest=pin.recipe_digest,
            section_pointer=pin.section_pointer,
            membership=pin.membership,
        ),
        text=request.block.text,
        pieces=[p.to_wire() for p in request.native_pieces],
        items=[dict(self_ref="#/texts/1", label="text")],
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
        profile="named-rules",
        selectors=[dict(projection=pin.projection_digest, start=0, end=len(view.text))],
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

    retained, npin = primary_native_layer(
        pin.native_product.values(),
        scope,
        operation,
        prepared,
        ((view, product),),
        configuration=controlled.config.to_str(),
        digest="derived",
        reference=101,
        execution=controlled.selection().native,
    )
    rules = (
        AnnotationRule(
            rule="repeat",
            variant="two",
            mechanism="token",
            pattern=[{"TEXT": "X"}, {"TEXT": "X"}],
            bindings={"members": RoleBinding(node="match")},
        ),
        AnnotationRule(
            rule="term",
            variant="each",
            mechanism="phrase",
            pattern=["X"],
            bindings={"mention": RoleBinding(node="match")},
        ),
        AnnotationRule(
            rule="missing",
            variant="zero",
            mechanism="phrase",
            pattern=["absent"],
            bindings={"mention": RoleBinding(node="match")},
        ),
        AnnotationRule(
            rule="ner",
            variant="unavailable",
            mechanism="token",
            pattern=[{"ENT_TYPE": "PERSON"}],
            bindings={"person": RoleBinding(node="match")},
        ),
    )
    layer = ConstructionLayer(
        pin.native_product.values(),
        scope,
        dict(operation, key="text.constructions"),
        families=(NAMED_FAMILY,),
    )
    populate_named(
        layer, view, npin, retained, PreparedAnnotationRules(controlled.vocab, rules=rules)
    )
    produced = layer.finish(prepared, dependencies={npin: retained})
    cpin = produced.reference(102)
    monkeypatch.setattr(
        PreparedAnnotationRules, "match", lambda *_: pytest.fail("consumer reran matching")
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.constructions.named.annotation_view",
        lambda *_args, **_kw: pytest.fail("consumer rebuilt native Doc"),
    )
    result = RetainedNamedRules({npin: retained, cpin: produced}).match(product, rules=rules)
    assert result.availability == (
        ("repeat", "two", "available"),
        ("term", "each", "available"),
        ("missing", "zero", "available"),
        ("ner", "unavailable", "unavailable"),
    )
    repeated = next(m for m in result.matches if m.rule == "repeat")
    assert repeated.nodes == (0, 1)
    assert repeated.extents == ((0, 1), (2, 3))
    assert repeated.roles[0].nodes == (0, 1)
    assert repeated.roles[0].extents == ((0, 1), (2, 3))
    assert repeated.sentences == (0, 0)
    assert len([m for m in result.matches if m.rule == "term"]) == 2
    assert not any(m.rule in {"missing", "ner"} for m in result.matches)
    changed = rules[0].model_copy(update={"pattern": [{"TEXT": "Y"}]})
    with pytest.raises(ValueError, match="not produced"):
        RetainedNamedRules({npin: retained, cpin: produced}).match(product, rules=(changed,))


@pytest.mark.parametrize("article,status", [("the", "resolved"), ("a", "unresolved")])
def test_primary_naming_nomination_retains_exact_antecedent_and_prior_sentence_context(
    article, status
):
    from spacy.lang.en import English
    from spacy.tokens import Doc

    from corpus_structure.methods.annotation_rules import AnnotationRuleMatch, LocatedRole

    words = [
        "Consider",
        article,
        "function",
        "f",
        "such",
        "that",
        "x",
        "varies",
        ".",
        "This",
        "function",
        "f",
        "is",
        "called",
        "law",
        ".",
    ]
    heads = [0, 2, 0, 2, 5, 7, 7, 2, 0, 10, 13, 10, 13, 13, 13, 13]
    deps = [
        "ROOT",
        "det",
        "dobj",
        "appos",
        "advmod",
        "mark",
        "nsubj",
        "acl",
        "punct",
        "det",
        "nsubjpass",
        "appos",
        "auxpass",
        "ROOT",
        "oprd",
        "punct",
    ]
    pos = [
        "VERB",
        "DET",
        "NOUN",
        "NOUN",
        "ADJ",
        "SCONJ",
        "NOUN",
        "VERB",
        "PUNCT",
        "DET",
        "NOUN",
        "NOUN",
        "AUX",
        "VERB",
        "NOUN",
        "PUNCT",
    ]
    morphs = [
        "VerbForm=Fin" if i in {0, 7} else "Number=Sing" if p == "NOUN" else ""
        for i, p in enumerate(pos)
    ]
    doc = Doc(
        English().vocab,
        words=words,
        spaces=[i not in {7, 14, 15} for i in range(len(words))],
        heads=heads,
        deps=deps,
        pos=pos,
        lemmas=[w.lower() for w in words],
        morphs=morphs,
    )
    tokens = tuple(
        SimpleNamespace(start=t.idx, end=t.idx + len(t.text), piece_indices=(0,)) for t in doc
    )
    product = SimpleNamespace(
        tokens=tokens,
        availability=[
            SimpleNamespace(attribute=column, status="complete")
            for column in ("LEMMA", "POS", "MORPH", "DEP", "SENT_START")
        ],
    )
    role = LocatedRole(
        "defining_content",
        "content",
        10,
        "noun_chunk",
        (9, 10, 11),
        tuple((tokens[i].start, tokens[i].end) for i in (9, 10, 11)),
        "complete",
    )
    match = AnnotationRuleMatch(
        "naming",
        "passive_called_term",
        "dependency",
        (13, 10, 14),
        (),
        (0,),
        (1, 1, 1),
        "d" * 64,
        (role,),
    )
    nomination = naming_nomination(SimpleNamespace(product=product, doc=doc), match, role)
    assert nomination is not None
    assert nomination.demonstrative is True
    assert nomination.status == status
    if status == "resolved":
        assert nomination.antecedent_nodes == tuple(range(1, 9))
        assert nomination.context_start == 0
        assert nomination.antecedent_extents[0][0] > nomination.context_start
        assert (
            doc.text[nomination.antecedent_extents[0][0] : nomination.antecedent_extents[-1][1]]
            == "the function f such that x varies."
        )
