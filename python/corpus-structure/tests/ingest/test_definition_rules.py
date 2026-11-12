"""Literal syntax controls for authored rules; no trained-provider efficacy claim."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.ingest.annotations import annotate
from corpus_structure.methods.annotation_rules import AnnotationRule, PreparedAnnotationRules
from corpus_structure.methods.definition_applicability import (
    components_from_following_display,
    components_from_named_matches,
    definition_scopes,
)
from corpus_structure.methods.predicate_frames import predicate_frame_result
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.structural_products import StructuralPassage

from .test_annotations import controlled as controlled
from .test_annotations import item, primary_product


def matched(controlled, text, heads, deps, pos, lemmas, *, display=None):
    request = item(controlled, text)
    (product,) = annotate((request,))
    tokens = tuple(
        replace(t, head=h, dependency=d, pos=p, lemma=lemma)
        for t, h, d, p, lemma in zip(product.tokens, heads, deps, pos, lemmas, strict=True)
    )
    view = annotation_view(
        primary_product(
            text, replace(product, tokens=tokens), native_profile=controlled.selection().native
        ),
        text,
        controlled.vocab,
    )
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
    scopes = definition_scopes(
        matches, predicate_frame_result(view), content_role="defining_content"
    )
    if display is not None:
        start = text.index(display) + 100
        components = components_from_following_display(
            passage,
            matches,
            ((start, start + len(display)),),
            scopes=scopes,
            term_role="defined_term",
        )
    else:
        components = components_from_named_matches(
            passage,
            matches,
            scopes=scopes,
            term_role="defined_term",
            content_role="defining_content",
        )
    return matches, scopes, components


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
    matches, _, (found,) = matched(controlled, text, heads, deps, pos, lemmas)
    assert variant in {m.variant for m in matches}
    assert found.term.text.lower() == "variance" and found.content.text.lower() == "dispersion"
    assert found.interpretation == interpretation
    assert text[found.term.start - 100 : found.term.end - 100] == found.term.text


def test_conditional_value_is_not_lowered_to_an_unqualified_constant(controlled):
    matches, scopes, components = matched(
        controlled,
        "We define X to be 1 if heads occur .",
        (1, 1, 1, 4, 1, 4, 8, 8, 4, 1),
        ("nsubj", "ROOT", "dobj", "aux", "xcomp", "attr", "mark", "nsubj", "advcl", "punct"),
        ("PRON", "VERB", "NOUN", "PART", "AUX", "NUM", "SCONJ", "NOUN", "VERB", "PUNCT"),
        ("we", "define", "x", "to", "be", "1", "if", "head", "occur", "."),
    )
    assert not components
    (reading,) = [m for m in matches if m.variant == "active_to_be"]
    scope = scopes[reading]
    assert scope.disposition == "qualified"
    assert scope.act_polarity == "positive"
    (condition,) = scope.content_cues
    assert (condition.kind, condition.status, condition.hosts) == ("condition", "located", (4,))
    assert tuple(text_span(condition, "We define X to be 1 if heads occur .")) == (
        "if heads occur",
    )


def test_negated_definition_retains_cue_without_positive_attachment(controlled):
    matches, scopes, components = matched(
        controlled,
        "Variance is not defined to be dispersion .",
        (3, 3, 3, 3, 5, 3, 5, 3),
        ("nsubjpass", "auxpass", "neg", "ROOT", "aux", "xcomp", "attr", "punct"),
        ("NOUN", "AUX", "PART", "VERB", "PART", "AUX", "NOUN", "PUNCT"),
        ("variance", "be", "not", "define", "to", "be", "dispersion", "."),
    )
    assert not components
    (reading,) = [m for m in matches if m.variant == "passive_to_be"]
    scope = scopes[reading]
    assert (scope.act_host, scope.act_polarity, scope.disposition) == (3, "negative", "negated")
    (negation,) = scope.act_cues
    assert (negation.kind, negation.hosts, negation.span.extents) == (
        "negation",
        (3,),
        ((112, 115),),
    )
    assert not scope.content_cues


def test_competing_passive_subjects_are_unresolved_without_surface_order_guess(controlled):
    matches, _, components = matched(
        controlled,
        "Density 3 is called Maxwell .",
        (3, 3, 3, 3, 3, 3),
        ("nsubjpass", "nsubjpass", "auxpass", "ROOT", "oprd", "punct"),
        ("NOUN", "NUM", "AUX", "VERB", "PROPN", "PUNCT"),
        ("density", "3", "be", "call", "Maxwell", "."),
    )
    assert len([m for m in matches if m.variant == "passive_called_term"]) == 2
    assert not components


def text_span(cue, text):
    return (text[start - 100 : end - 100] for start, end in cue.span.extents)


def test_embedded_content_negation_remains_inside_a_positive_definition(controlled):
    text = "We define X as a value that does not change ."
    matches, scopes, (found,) = matched(
        controlled,
        text,
        (1, 1, 1, 1, 5, 3, 9, 9, 9, 5, 1),
        ("nsubj", "ROOT", "dobj", "prep", "det", "pobj", "nsubj", "aux", "neg", "relcl", "punct"),
        ("PRON", "VERB", "NOUN", "ADP", "DET", "NOUN", "PRON", "AUX", "PART", "VERB", "PUNCT"),
        ("we", "define", "x", "as", "a", "value", "that", "do", "not", "change", "."),
    )
    (reading,) = [m for m in matches if m.variant == "active_as"]
    scope = scopes[reading]
    assert (scope.act_host, scope.act_polarity, scope.disposition) == (1, "positive", "supported")
    assert not scope.act_cues
    (negation,) = scope.content_cues
    assert (negation.kind, negation.hosts, tuple(text_span(negation, text))) == (
        "negation",
        (9,),
        ("not",),
    )
    assert found.content.text == "a value that does not change"


def test_naming_keeps_its_permitted_nominal_complement(controlled):
    _, _, (found,) = matched(
        controlled,
        "This set of points is called a set of constant density .",
        (1, 5, 1, 2, 5, 5, 7, 5, 7, 10, 8, 5),
        (
            "det",
            "nsubjpass",
            "prep",
            "pobj",
            "auxpass",
            "ROOT",
            "det",
            "oprd",
            "prep",
            "amod",
            "pobj",
            "punct",
        ),
        ("DET", "NOUN", "ADP", "NOUN", "AUX", "VERB", "DET", "NOUN", "ADP", "ADJ", "NOUN", "PUNCT"),
        ("this", "set", "of", "point", "be", "call", "a", "set", "of", "constant", "density", "."),
    )
    assert found.term.text == "a set of constant density"
    assert found.content.text == "This set of points"
    assert found.interpretation == "explanation"


def test_historical_instead_of_keeps_the_contrast_and_withholds_defining_act(controlled):
    text = "Instead of defining expected value as a weighted average , Huygens assumed symmetry ."
    matches, scopes, components = matched(
        controlled,
        text,
        (11, 0, 1, 4, 2, 2, 8, 8, 5, 11, 11, 11, 11, 11),
        (
            "advmod",
            "prep",
            "pcomp",
            "amod",
            "dobj",
            "prep",
            "det",
            "amod",
            "pobj",
            "punct",
            "nsubj",
            "ROOT",
            "dobj",
            "punct",
        ),
        (
            "ADV",
            "ADP",
            "VERB",
            "ADJ",
            "NOUN",
            "ADP",
            "DET",
            "ADJ",
            "NOUN",
            "PUNCT",
            "PROPN",
            "VERB",
            "NOUN",
            "PUNCT",
        ),
        (
            "instead",
            "of",
            "define",
            "expect",
            "value",
            "as",
            "a",
            "weight",
            "average",
            ",",
            "Huygens",
            "assume",
            "symmetry",
            ".",
        ),
    )
    (reading,) = [m for m in matches if m.variant == "active_as"]
    scope = scopes[reading]
    assert not components
    assert (scope.act_host, scope.act_polarity, scope.disposition) == (2, "positive", "contrasted")
    (contrast,) = [cue for cue in scope.act_cues if cue.kind == "contrast"]
    assert (contrast.origin, contrast.hosts) == (11, (2,))
    assert any(text[a - 100 : b - 100] == "Instead of" for a, b in contrast.basis.extents)


def test_reported_definition_retains_attribution_without_an_unattributed_pair(controlled):
    text = "Huygens claimed that we define X as a value ."
    matches, scopes, components = matched(
        controlled,
        text,
        (1, 1, 4, 4, 1, 4, 4, 8, 6, 1),
        ("nsubj", "ROOT", "mark", "nsubj", "ccomp", "dobj", "prep", "det", "pobj", "punct"),
        ("PROPN", "VERB", "SCONJ", "PRON", "VERB", "NOUN", "ADP", "DET", "NOUN", "PUNCT"),
        ("Huygens", "claim", "that", "we", "define", "x", "as", "a", "value", "."),
    )
    (reading,) = [m for m in matches if m.variant == "active_as"]
    scope = scopes[reading]
    assert not components
    assert (scope.act_host, scope.act_polarity, scope.disposition) == (4, "positive", "attributed")
    (attribution,) = [cue for cue in scope.act_cues if cue.kind == "attribution"]
    assert (attribution.origin, attribution.hosts) == (1, (4,))


@pytest.mark.parametrize("conditional", (False, True))
def test_following_display_shares_the_defining_act_guard(controlled, conditional):
    text = ("If heads occur , " if conditional else "") + "X is defined by : F ."
    offset = 4 if conditional else 0
    matches, scopes, components = matched(
        controlled,
        text,
        ((2, 2, 6, 6) if conditional else ())
        + tuple(head + offset for head in (2, 2, 2, 2, 2, 2, 2)),
        (("mark", "nsubj", "advcl", "punct") if conditional else ())
        + ("nsubjpass", "auxpass", "ROOT", "agent", "punct", "dobj", "punct"),
        (("SCONJ", "NOUN", "VERB", "PUNCT") if conditional else ())
        + ("NOUN", "AUX", "VERB", "ADP", "PUNCT", "NOUN", "PUNCT"),
        (("if", "head", "occur", ",") if conditional else ())
        + ("x", "be", "define", "by", ":", "f", "."),
        display="F",
    )
    (reading,) = [m for m in matches if m.variant == "passive_following_display"]
    scope = scopes[reading]
    assert scope.disposition == ("qualified" if conditional else "supported")
    if conditional:
        assert not components
        (condition,) = scope.act_cues
        assert condition.hosts == (6,)
        assert tuple(text_span(condition, text)) == ("If heads occur",)
    else:
        (found,) = components
        assert (found.term.text, found.content.text, found.basis) == ("X", "F", "native_geometry")


def test_quoted_if_is_literal_defining_content(controlled):
    text = 'We define X as "if" .'
    matches, scopes, (found,) = matched(
        controlled,
        text,
        (1, 1, 1, 1, 5, 3, 5, 1),
        ("nsubj", "ROOT", "dobj", "prep", "punct", "pobj", "punct", "punct"),
        ("PRON", "VERB", "NOUN", "ADP", "PUNCT", "NOUN", "PUNCT", "PUNCT"),
        ("we", "define", "x", "as", '"', "if", '"', "."),
    )
    (reading,) = [m for m in matches if m.variant == "active_as"]
    assert found.content.text == '"if"'
    assert scopes[reading].disposition == "supported"
    assert not scopes[reading].act_cues and not scopes[reading].content_cues


def test_located_condition_within_the_exact_content_remains_literal(controlled):
    text = "We define X as a value that changes if heads occur ."
    matches, scopes, (found,) = matched(
        controlled,
        text,
        (1, 1, 1, 1, 5, 3, 7, 5, 10, 10, 7, 1),
        (
            "nsubj",
            "ROOT",
            "dobj",
            "prep",
            "det",
            "pobj",
            "nsubj",
            "relcl",
            "mark",
            "nsubj",
            "advcl",
            "punct",
        ),
        (
            "PRON",
            "VERB",
            "NOUN",
            "ADP",
            "DET",
            "NOUN",
            "PRON",
            "VERB",
            "SCONJ",
            "NOUN",
            "VERB",
            "PUNCT",
        ),
        ("we", "define", "x", "as", "a", "value", "that", "change", "if", "head", "occur", "."),
    )
    (reading,) = [m for m in matches if m.variant == "active_as"]
    assert found.content.text == "a value that changes if heads occur"
    scope = scopes[reading]
    assert not scope.act_cues
    (condition,) = scope.content_cues
    assert (condition.kind, condition.hosts, tuple(text_span(condition, text))) == (
        "condition",
        (7,),
        ("if heads occur",),
    )


def test_unsupported_condition_at_content_predicate_withholds_pair(controlled):
    text = "We define X to be 1 if ."
    matches, scopes, components = matched(
        controlled,
        text,
        (1, 1, 1, 4, 1, 4, 4, 1),
        ("nsubj", "ROOT", "dobj", "aux", "xcomp", "attr", "mark", "punct"),
        ("PRON", "VERB", "NOUN", "PART", "AUX", "NUM", "SCONJ", "PUNCT"),
        ("we", "define", "x", "to", "be", "1", "if", "."),
    )
    (reading,) = [m for m in matches if m.variant == "active_to_be"]
    scope = scopes[reading]
    assert not components
    assert scope.disposition == "unresolved"
    (condition,) = scope.content_cues
    assert (condition.kind, condition.status, condition.origin, condition.hosts) == (
        "condition",
        "unresolved",
        4,
        (),
    )
    assert tuple(text_span(condition, text)) == ("if",)
