"""Exact local qualifier witnesses and their refusal boundaries."""

import pytest
from spacy.lang.en import English

from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.predicate_frames import predicate_frame_result

from .test_predicate_frames import retained, strings

EVENT = (
    "Definition 6.2 If F is any event and X is a random variable "
    "with sample space Ω = {x1, x2, . . .}, then the conditional expectation given F is defined by"
)
VARIANCE = (
    "Let X and Y be random variables with positive variance. "
    "The correlation of X and Y is defined as"
)
PARAMETERS = "The normal density function with parameters µ and \u03c3 is defined as follows:"
POPULATION = (
    "Note that in this case we are counting the waiting time of all customers, "
    "even those that do not have to wait at all."
)


def _analyze(text, kind):
    source, product = retained(text, AnnotationProfile(), kind=kind)
    view = annotation_view(
        product, source[product.block_start : product.block_end], English().vocab
    )
    base = predicate_frame_result(view)
    return source, view, base, base


@pytest.mark.parametrize(
    ("text", "kind", "variant", "cue_kind", "expected", "host"),
    [
        (
            EVENT,
            "paragraph",
            "event_compound_then",
            "condition",
            "If F is any event and X is a random variable with sample space Ω = {x1, x2, . . .}",
            "defined",
        ),
        (
            VARIANCE,
            "list_item",
            "adjacent_variance_premise",
            "assumption",
            "Let X and Y be random variables with positive variance",
            "defined",
        ),
        (
            PARAMETERS,
            "paragraph",
            "nominal_parameter_pair",
            "parameterization",
            "with parameters µ and \u03c3",
            "defined",
        ),
        (
            POPULATION,
            "paragraph",
            "customer_population_inclusion",
            "population_inclusion",
            "even those that do not have to wait at all",
            "counting",
        ),
    ],
)
def test_attaches_exact_cue_to_one_host(text, kind, variant, cue_kind, expected, host):
    source, view, base, result = _analyze(text, kind)
    assert result.issues == base.issues == ()
    (attachment,) = [
        (frame, cue) for frame in result.frames for cue in frame.cues if cue.variant == variant
    ]
    frame, cue = attachment
    assert cue.kind == cue_kind
    assert cue.status == "located"
    assert cue.hosts == frame.predicate.tokens
    assert view.doc[cue.hosts[0]].text == host
    assert strings(source, cue.span) == (expected,)
    assert not any(
        cue.variant == "compound_if_then" for frame in result.frames for cue in frame.cues
    )
    assert tuple(frame.predicate for frame in result.frames) == tuple(
        frame.predicate for frame in base.frames
    )


@pytest.mark.parametrize(
    ("text", "kind", "variant"),
    [
        (EVENT.replace(", then ", ", "), "paragraph", "event_compound_then"),
        (
            VARIANCE.replace("correlation of X and Y", "correlation of Y and X"),
            "list_item",
            "adjacent_variance_premise",
        ),
        (VARIANCE, "paragraph", "adjacent_variance_premise"),
        (
            PARAMETERS.replace("µ and \u03c3", "\u03c3 and \u03c3"),
            "paragraph",
            "nominal_parameter_pair",
        ),
        (
            POPULATION.replace("all customers", "some customers"),
            "paragraph",
            "customer_population_inclusion",
        ),
    ],
)
def test_refuses_unwitnessed_host(text, kind, variant):
    _, _, _, result = _analyze(text, kind)
    assert not any(cue.variant == variant for frame in result.frames for cue in frame.cues)
    if kind == "list_item":
        (cue,) = [cue for cue in result.unresolved_cues if cue.variant == variant]
        assert cue.status == "unresolved" and cue.hosts == ()
