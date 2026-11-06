"""Literal syntax controls for authored rules; no trained-provider efficacy claim."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.ingest.annotations import annotate
from corpus_structure.methods.annotation_rules import AnnotationRule, PreparedAnnotationRules
from corpus_structure.methods.definition_applicability import components_from_named_matches
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.structural_products import StructuralPassage

from .test_annotations import controlled as controlled
from .test_annotations import item


def matched(controlled, text, heads, deps, pos, lemmas):
    request = item(controlled, text)
    (product,) = annotate((request,))
    tokens = tuple(
        replace(t, head=h, dependency=d, pos=p, lemma=lemma)
        for t, h, d, p, lemma in zip(product.tokens, heads, deps, pos, lemmas, strict=True)
    )
    view = annotation_view(replace(product, tokens=tokens), text, controlled.vocab)
    recipe = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_text())["configs"][
        "extract.m1_candidates"
    ]["witnessed"]["annotation_rules"]
    matches = (
        PreparedAnnotationRules(
            controlled.vocab, rules=tuple(AnnotationRule.model_validate(r) for r in recipe)
        )
        .match(view)
        .matches
    )
    passage = StructuralPassage(
        passage_id="control",
        source_ref="source",
        start=100,
        end=100 + len(text),
        text=text,
        scope="s",
    )
    return matches, components_from_named_matches(
        passage, matches, term_role="defined_term", content_role="defining_content"
    )


@pytest.mark.parametrize(
    "text,heads,deps,pos,lemmas,variant,interpretation",
    [
        (
            "We define variance to be dispersion .",
            (1, 1, 1, 4, 1, 4, 1),
            ("nsubj", "ROOT", "dobj", "aux", "xcomp", "attr", "punct"),
            ("PRON", "VERB", "NOUN", "PART", "AUX", "NOUN", "PUNCT"),
            ("we", "define", "variance", "to", "be", "dispersion", "."),
            "active_to_be",
            "definition",
        ),
        (
            "Variance is defined to be dispersion .",
            (2, 2, 2, 4, 2, 4, 2),
            ("nsubjpass", "auxpass", "ROOT", "aux", "xcomp", "attr", "punct"),
            ("NOUN", "AUX", "VERB", "PART", "AUX", "NOUN", "PUNCT"),
            ("variance", "be", "define", "to", "be", "dispersion", "."),
            "passive_to_be",
            "definition",
        ),
        (
            "We call dispersion variance .",
            (1, 1, 1, 1, 1),
            ("nsubj", "ROOT", "dobj", "oprd", "punct"),
            ("PRON", "VERB", "NOUN", "NOUN", "PUNCT"),
            ("we", "call", "dispersion", "variance", "."),
            "active_called_term",
            "explanation",
        ),
        (
            "Dispersion is called variance .",
            (2, 2, 2, 2, 2),
            ("nsubjpass", "auxpass", "ROOT", "oprd", "punct"),
            ("NOUN", "AUX", "VERB", "NOUN", "PUNCT"),
            ("dispersion", "be", "call", "variance", "."),
            "passive_called_term",
            "explanation",
        ),
    ],
)
def test_explicit_defining_and_naming_orientation(
    controlled, text, heads, deps, pos, lemmas, variant, interpretation
):
    matches, (found,) = matched(controlled, text, heads, deps, pos, lemmas)
    assert variant in {m.variant for m in matches}
    assert found.term.text.lower() == "variance" and found.content.text.lower() == "dispersion"
    assert found.interpretation == interpretation
    assert text[found.term.start - 100 : found.term.end - 100] == found.term.text


def test_conditional_value_is_not_lowered_to_an_unqualified_constant(controlled):
    matches, components = matched(
        controlled,
        "We define X to be 1 if heads occur .",
        (1, 1, 1, 4, 1, 4, 8, 8, 4, 1),
        ("nsubj", "ROOT", "dobj", "aux", "xcomp", "attr", "mark", "nsubj", "advcl", "punct"),
        ("PRON", "VERB", "NOUN", "PART", "AUX", "NUM", "SCONJ", "NOUN", "VERB", "PUNCT"),
        ("we", "define", "x", "to", "be", "1", "if", "head", "occur", "."),
    )
    assert not components
    (reading,) = [m for m in matches if m.variant == "active_to_be"]
    assert next(r for r in reading.roles if r.role == "definition_scope_guard").status == "partial"


def test_negated_definition_retains_cue_without_positive_attachment(controlled):
    matches, components = matched(
        controlled,
        "Variance is not defined to be dispersion .",
        (3, 3, 3, 3, 5, 3, 5, 3),
        ("nsubjpass", "auxpass", "neg", "ROOT", "aux", "xcomp", "attr", "punct"),
        ("NOUN", "AUX", "PART", "VERB", "PART", "AUX", "NOUN", "PUNCT"),
        ("variance", "be", "not", "define", "to", "be", "dispersion", "."),
    )
    assert not components
    assert any(m.negation_extents == ((112, 115),) for m in matches)


def test_competing_passive_subjects_are_unresolved_without_surface_order_guess(controlled):
    matches, components = matched(
        controlled,
        "Density 3 is called Maxwell .",
        (3, 3, 3, 3, 3, 3),
        ("nsubjpass", "nsubjpass", "auxpass", "ROOT", "oprd", "punct"),
        ("NOUN", "NUM", "AUX", "VERB", "PROPN", "PUNCT"),
        ("density", "3", "be", "call", "Maxwell", "."),
    )
    assert len([m for m in matches if m.variant == "passive_called_term"]) == 2
    assert not components
