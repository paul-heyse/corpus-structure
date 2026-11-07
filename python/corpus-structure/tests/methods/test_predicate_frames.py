"""Retained-source frame boundaries and qualifier ownership."""

from dataclasses import replace
from typing import Literal

import pytest

from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout
from corpus_structure.methods.structural_roles import predicate_frames, procedure_frames
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_contexts import NativeSourcePin

_PREFIX = "outside the block: "


@pytest.fixture(scope="module")
def profile():
    return AnnotationProfile()


def retained(
    text,
    profile,
    *,
    block_id="paragraph:3",
    kind: Literal["paragraph", "list_item", "table_cell", "caption"] = "paragraph",
    pieces=None,
):
    block = Block(text, (), (), ())
    layout = prepare_layout(pipeline(profile.configuration), block, start=len(_PREFIX))
    source = NativeSourcePin(
        7,
        "source:7",
        ProductReference(17, "integrated", "a" * 64),
        "#/groups/7",
        "descendants",
        "b" * 64,
        "c" * 64,
        3,
    )
    if pieces is None:
        pieces = (ProjectedPiece("#/texts/3", len(_PREFIX), len(_PREFIX + text), "native_text"),)
    request = AnnotationInput(source, block_id, kind, block, layout, pieces)
    (product,) = annotate((request,), profile)
    return _PREFIX + text, product


def strings(text, span):
    return tuple(text[a:b] for a, b in span.extents)


def readings(text, result):
    assert not result.issues
    return {strings(text, frame.predicate)[0].casefold(): frame for frame in result.frames}


def role(text, frame, name):
    return tuple(strings(text, role.span) for role in frame.roles if role.name == name)


def cues(frame, kind):
    return tuple(cue for cue in frame.cues if cue.kind == kind)


def test_pin_reconstruction_and_exact_passive_probability_subject(profile):
    text, product = retained(
        "The probability that X is less than Y is given by the integral.", profile
    )
    frames = readings(text, predicate_frames(text, (product,)))
    given = frames["given"]
    assert given.block_id == product.block_id
    assert given.dependency == product.dependency_digest
    assert given.voice == "passive"
    assert given.variant == "passive_probability_subject"
    assert given.interpretation == "explanation"
    assert role(text, given, "object") == (("The probability that X is less than Y",),)
    assert role(text, given, "actor") == (("the integral",),)
    assert strings(text, given.focus) == (
        "The probability that X is less than Y is given by the integral",
    )
    # Old and new recipes get exactly the same retained dependency rows.
    baseline = procedure_frames(text, (product,))
    old = next(frame for frame in baseline if text[slice(*frame["action"])] == "given")
    assert tuple(text[a:b] for a, b in old["object"]) != ("The probability that X is less than Y",)


def test_naming_complement_and_embedded_negation_have_separate_hosts(profile):
    text, product = retained(
        "This set of points is called a set of constant density. "
        "A dry run means a run that does not change data.",
        profile,
    )
    frames = readings(text, predicate_frames(text, (product,)))
    called, means, change = (frames[name] for name in ("called", "means", "change"))
    assert called.reading == "naming" and called.variant == "naming_passive"
    assert role(text, called, "object") == (("This set of points",),)
    assert role(text, called, "complement") == (("a set of constant density",),)
    assert means.interpretation == "definition" and means.polarity == "positive"
    assert not cues(means, "negation")
    assert change.polarity == "negative"
    (negation,) = cues(change, "negation")
    assert negation.origin == change.predicate.tokens[0]
    assert strings(text, negation.basis) == ("not",)
    assert all(token not in means.focus.tokens for token in negation.basis.tokens)


def test_coordination_preserves_ambiguous_negation_and_contrast(profile):
    text, product = retained("Do not heat and stir.", profile)
    frames = readings(text, predicate_frames(text, (product,)))
    heat, stir = frames["heat"], frames["stir"]
    assert heat.polarity == stir.polarity == "negative_scope_unresolved"
    (negation,) = cues(heat, "negation")
    assert negation.status == "unresolved"
    assert negation.hosts == (heat.predicate.tokens[0], stir.predicate.tokens[0])
    assert cues(stir, "negation") == (negation,)

    text, product = retained("Do not heat, but stir.", profile)
    frames = readings(text, predicate_frames(text, (product,)))
    assert frames["heat"].polarity == "negative"
    assert frames["stir"].polarity == "positive"
    assert not cues(frames["stir"], "negation")


def test_fronted_shared_condition_and_independent_local_conditions(profile):
    text, product = retained("If pressure rises, heat the water and stir the mixture.", profile)
    frames = readings(text, predicate_frames(text, (product,)))
    heat, stir = frames["heat"], frames["stir"]
    (condition,) = cues(heat, "condition")
    assert cues(stir, "condition") == (condition,)
    assert strings(text, condition.span) == ("If pressure rises",)
    assert condition.origin == heat.predicate.tokens[0]
    assert condition.hosts == (heat.predicate.tokens[0], stir.predicate.tokens[0])
    assert strings(text, heat.focus) == ("heat the water",)
    assert strings(text, stir.focus) == ("stir the mixture",)

    text, product = retained(
        "Heat the water if pressure rises and stir the mixture if the alarm sounds.", profile
    )
    frames = readings(text, predicate_frames(text, (product,)))
    for name, expected in (("heat", "if pressure rises"), ("stir", "if the alarm sounds")):
        (condition,) = cues(frames[name], "condition")
        assert condition.hosts == frames[name].predicate.tokens
        assert strings(text, condition.span) == (expected,)


def test_quoted_marker_historical_contrast_and_attributed_assumption(profile):
    text, product = retained(
        "The word “if” denotes a condition. Instead of defining the value, "
        "Huygens assumed that X is nonnegative.",
        profile,
    )
    result = predicate_frames(text, (product,))
    frames = readings(text, result)
    assert not any(cues(frame, "condition") for frame in frames.values())
    assert not result.unresolved_cues
    assert frames["defining"].interpretation == "reference"
    (contrast,) = cues(frames["defining"], "contrast")
    assert strings(text, contrast.basis) == ("Instead of",)
    assumed, reported = frames["assumed"], frames["is"]
    assert assumed.reading == "reported_assumption"
    assert assumed.interpretation == "assumption_restriction"
    (attribution,) = cues(reported, "attribution")
    assert attribution.origin == assumed.predicate.tokens[0]
    assert attribution.hosts == reported.predicate.tokens
    assert strings(text, attribution.span) == ("Huygens assumed",)


def test_modality_alone_and_unrelated_exception_are_insufficient(profile):
    text, product = retained("X must be greater than zero. Managers must review forms.", profile)
    frames = readings(text, predicate_frames(text, (product,)))
    assert frames["be"].interpretation == "explanation"
    assert frames["review"].interpretation == "unresolved"
    policy = readings(text, predicate_frames(text, (product,), layout="policy"))
    assert policy["review"].interpretation == "prescribed_action"
    assert policy["be"].interpretation == "explanation"
    assert frames["review"].predicate == policy["review"].predicate
    assert frames["review"].focus == policy["review"].focus

    text, product = retained(
        "Manager reviews all forms except receipts. Analysts file reports.", profile
    )
    result = predicate_frames(text, (product,))
    frames = readings(text, result)
    assert not cues(frames["file"], "exception")
    (exception,) = result.unresolved_cues
    assert exception.kind == "exception" and exception.status == "unresolved"
    assert strings(text, exception.span) == ("except receipts",)


def test_noncontiguous_role_stays_separate_with_controlled_retained_heads(profile):
    text, product = retained("Manager reviews current and archived files.", profile)
    # The controlled dependency rows give only "current" to "files", leaving
    # "and archived" as competing material between two role members.
    tokens = tuple(
        replace(row, dependency=dependency, head=head)
        for row, (dependency, head) in zip(
            product.tokens,
            (
                ("nsubj", 1),
                ("ROOT", 1),
                ("amod", 5),
                ("cc", 2),
                ("conj", 2),
                ("dobj", 1),
                ("punct", 1),
            ),
            strict=True,
        )
    )
    adjusted = replace(product, tokens=tokens)
    frame = readings(text, predicate_frames(text, (adjusted,)))["reviews"]
    assert role(text, frame, "object") == (("current", "files"),)
    assert strings(text, frame.focus) == ("Manager reviews current", "files")


def test_unavailable_and_unsupported_alignment_are_distinct(profile):
    text, product = retained("Manager reviews the report.", profile)
    missing = replace(product, availability=(), block_id="unavailable")
    invalid = replace(product, text_digest="0" * 64, block_id="unaligned")
    result = predicate_frames(text, (missing, invalid, product))
    assert [(issue.block_id, issue.status) for issue in result.issues] == [
        ("unavailable", "unavailable"),
        ("unaligned", "unsupported_alignment"),
    ]
    (frame,) = result.frames
    assert strings(text, frame.focus) == ("Manager reviews the report",)


def test_local_temporal_order_and_independent_coordinate_scope(profile):
    text, product = retained("Before heating the water, stir the mixture.", profile)
    frames = readings(text, predicate_frames(text, (product,)))
    (order,) = cues(frames["stir"], "order")
    assert order.variant == "before"
    assert order.hosts == frames["stir"].predicate.tokens
    assert order.component == frames["heating"].predicate.tokens[0]
    assert strings(text, order.span) == ("Before heating the water",)
    assert strings(text, frames["stir"].focus) == ("stir the mixture",)

    text, product = retained(
        "If the alarm sounds, the manager will inspect the door and "
        "the analyst will open the window.",
        profile,
    )
    frames = readings(text, predicate_frames(text, (product,)))
    assert not cues(frames["open"], "condition")
    (condition,) = cues(frames["inspect"], "condition")
    assert condition.hosts == frames["inspect"].predicate.tokens
    assert role(text, frames["open"], "actor") == (("the analyst",),)
    (modal,) = cues(frames["open"], "modality")
    assert modal.origin == frames["open"].predicate.tokens[0]


def test_native_piece_boundary_separates_even_adjacent_role_tokens(profile):
    sentence = "The manager reviews a report."
    cut = len(_PREFIX) + sentence.index("report")
    pieces = (
        ProjectedPiece("#/texts/3", len(_PREFIX), cut, "native_text"),
        ProjectedPiece("#/texts/4", cut, len(_PREFIX + sentence), "native_text"),
    )
    text, product = retained(sentence, profile, pieces=pieces)
    frames = readings(text, predicate_frames(text, (product,)))
    frame = frames["reviews"]
    assert role(text, frame, "object") == (("a", "report"),)
    assert strings(text, frame.focus) == ("The manager reviews a", "report")


def test_compound_if_then_keeps_premise_parse_conflict_unresolved(profile):
    text, product = retained(
        "Definition 6.2 If F is any event and X is a random variable with "
        "sample space Ω = {x1, x2, . . .}, then the conditional expectation "
        "given F is defined by",
        profile,
    )
    result = predicate_frames(text, (product,))
    frames = readings(text, result)
    (cue,) = cues(frames["defined"], "condition")
    assert cue.status == "unresolved" and cue.variant == "compound_if_then"
    assert strings(text, cue.span) == (
        "If F is any event and X is a random variable with sample space Ω = {x1, x2, . . .}",
    )
    assert frames["defined"].predicate.tokens[0] in cue.hosts
    assert not any(
        candidate.status == "located"
        for frame in result.frames
        for candidate in cues(frame, "condition")
    )
