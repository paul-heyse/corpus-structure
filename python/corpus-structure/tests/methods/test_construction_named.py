"""Named primary-rule execution and pure consumer projection, no model quality claim."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from semantic.construction_products_test_support import profiles as profiles
from semantic.construction_products_test_support import publication_context
from semantic.source_annotations_test_support import detached as detached
from semantic.source_annotations_test_support import partition_controlled_annotations

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.annotation_rules import (
    AnnotationRule,
    PreparedAnnotationRules,
    RoleBinding,
)
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic.construction_products import ConstructionOptions
from corpus_structure.semantic.constructions.declared_named import DeclaredNamedRules
from corpus_structure.semantic.constructions.named import rule_identity
from corpus_structure.semantic.constructions.named_nominations import naming_nomination
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.sentence_products import retained_source_annotation_products


@pytest.fixture(scope="module")
def acquired(profiles):
    _, construction = profiles
    configuration = SentenceConfig(exclude=("ner",))
    selection = NativeSelection(
        NativeProfile(
            "spacy",
            {"fixture": "controlled-columns"},
            {},
            configuration.model_dump(mode="json"),
            "float32",
            "cupy",
        ),
        Path("."),
    )
    return construction.prepared, construction.model, configuration, selection


@pytest.mark.parametrize("detached", ["X X é."], indirect=True)
def test_named_rules_execute_upstream_once_and_replay_exact_roles_without_nlp(
    profiles, acquired, detached, monkeypatch
):
    formal, construction = profiles
    prepared, model, configuration, _selection = acquired
    source, value = detached
    context = publication_context(source)
    retained = partition_controlled_annotations(
        prepared, model, value, source, configuration=configuration, subject_context=context
    )
    (product,) = retained_source_annotation_products(source, retained)
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
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    produced = construction.run(
        source,
        (primary,),
        ConstructionOptions(annotation_rules=rules),
        sentences=retained,
        subject_context=context,
    )
    monkeypatch.setattr(
        PreparedAnnotationRules, "match", lambda *_: pytest.fail("consumer reran matching")
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.constructions.named.annotation_view",
        lambda *_args, **_kw: pytest.fail("consumer rebuilt native Doc"),
    )
    result, references, _nominations, identities = DeclaredNamedRules((produced,), retained).decode(
        product
    )
    assert set(result.availability) == {
        ("repeat", "two", "available"),
        ("term", "each", "available"),
        ("missing", "zero", "available"),
        ("ner", "unavailable", "unavailable"),
    }
    repeated = next(m for m in result.matches if m.rule == "repeat")
    assert repeated.nodes == (0, 1)
    assert repeated.extents == ((0, 1), (2, 3))
    assert repeated.roles[0].nodes == (0, 1)
    assert repeated.roles[0].extents == ((0, 1), (2, 3))
    assert repeated.sentences == (0, 0)
    assert len([m for m in result.matches if m.rule == "term"]) == 2
    assert not any(m.rule in {"missing", "ner"} for m in result.matches)
    changed = rules[0].model_copy(update={"pattern": [{"TEXT": "Y"}]})
    assert identities[("repeat", "two")] == rule_identity(rules[0])
    assert identities[("repeat", "two")] != rule_identity(changed)
    assert all(ref.product.product_id == produced.semantic_id for ref in references.values())


@pytest.mark.parametrize(
    "article,status,scenario",
    [
        ("the", "resolved", "unique"),
        ("a", "unresolved", "indefinite"),
        ("the", "unresolved", "competing"),
        ("the", "unresolved", "separate_piece"),
    ],
)
def test_primary_naming_nomination_retains_exact_antecedent_and_prior_sentence_context(
    article, status, scenario
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
    if scenario == "competing":
        # The authored dependency columns contain two identical restricted
        # nominal signatures; choosing the first equal wording is invalid.
        words[6:8] = ["function", "f"]
        heads[6:8] = [2, 6]
        deps[6:8] = ["conj", "appos"]
        pos[6:8] = ["NOUN", "NOUN"]
    morphs = [
        "VerbForm=Fin" if p == "VERB" and i in {0, 7} else "Number=Sing" if p == "NOUN" else ""
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
        SimpleNamespace(
            start=t.idx,
            end=t.idx + len(t.text),
            piece_indices=(1 if scenario == "separate_piece" and t.i >= 9 else 0,),
        )
        for t in doc
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
