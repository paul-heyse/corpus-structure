"""Named citation cues use their physical piece inside a joined annotation block."""

from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.semantic.constructions.navigation import (
    NAMED_COVERAGE_VERSION,
    NAMED_PIECE_VERSION,
    match_named_source_links,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralPassage
from methods.m1_source_preparation_support import source

_WRAPPER = "#/texts/20"
_INLINE = "#/groups/40"
_FIRST = "#/texts/21"
_SECOND = "#/texts/22"


def _joined(prefix, suffix, *, select_suffix=True):
    text = prefix + suffix
    nodes = (
        dict(self_ref=_WRAPPER, label="paragraph", parent={"$ref": "#/groups/1"}),
        dict(self_ref=_INLINE, label="inline", parent={"$ref": _WRAPPER}),
        *(
            dict(self_ref=pointer, label="text", text=literal, parent={"$ref": _INLINE})
            for pointer, literal in ((_FIRST, prefix), (_SECOND, suffix))
        ),
    )
    items = tuple(dict(node, content_layer="body") for node in nodes)
    pieces = (
        dict(kind="native_text", item_ref=_FIRST, source_field="text", start=0, end=len(prefix)),
        dict(
            kind="native_text",
            item_ref=_SECOND,
            source_field="text",
            start=len(prefix),
            end=len(text),
        ),
    )
    projection = dict(
        text=text,
        pieces=pieces,
        items=[node["self_ref"] for node in items],
        ancestors=[],
        health={},
    )
    base = source("placeholder", labels=("text",))
    view = replace(
        base,
        text=text,
        items=items,
        pieces=pieces,
        ref=replace(base.ref, projection_digest=sha256(canonical_bytes(projection)).hexdigest()),
    )
    prepared = prepare_source(view, annotations_only=True)
    assert not prepared.annotation_errors
    (annotation,) = prepared.annotations
    assert annotation.block_id == _WRAPPER
    passage = StructuralPassage(
        passage_id="runbook",
        source_ref="fixture",
        start=len(prefix) if select_suffix else 0,
        end=len(text),
        scope="incident-response",
        effective_version="R2",
        text=suffix if select_suffix else text,
    )
    return view, passage, annotation


def _inspect(view, passage, *annotations, version=NAMED_PIECE_VERSION, native_piece_policy=None):
    return match_named_source_links(
        view.text,
        view.pieces,
        {item["self_ref"]: item for item in view.items},
        (passage,),
        annotations,
        version=version,
        native_piece_policy=native_piece_policy,
    )


@pytest.mark.parametrize(
    ("tail", "kind", "subject", "cue"),
    [
        ("see Section 5.2.", "section_citation", "Section 5.2", "see"),
        (
            '"Response time" as defined in Section 6.3.',
            "definition_reference",
            "Section 6.3",
            "as defined in",
        ),
    ],
)
def test_named_link_distinguishes_physical_citation_piece_from_annotation_block(
    tail, kind, subject, cue
):
    view, passage, annotation = _joined("For operational context, ", tail)
    output = _inspect(view, passage, annotation)
    (match,) = output.matches
    assert (output.inspected_count, output.incomplete, output.outcome()) == (1, False, "limited")
    assert match.pointer == _SECOND
    assert match.witness.block == _WRAPPER
    assert match.witness.annotation == "annotation:" + annotation.dependency_digest
    assert match.kind == kind
    assert view.text[slice(*match.left)] == subject
    assert view.text[slice(*match.cue)] == cue
    assert all(
        annotation.tokens[index].piece_indices == (1,) for index in match.witness.tokens.values()
    )
    assert match.resolution == "target_selection_required"
    assert match.target_pointer is None

    previous = _inspect(view, passage, annotation, version=NAMED_COVERAGE_VERSION)
    assert previous.matches == () and previous.outcome() == "unsupported"


@pytest.mark.parametrize(
    "control", ["unmapped", "ambiguous", "duplicate", "synthetic", "wrong_role"]
)
def test_joined_citation_refuses_unproved_source_piece_or_token_ownership(control):
    view, passage, annotation = _joined("For earlier instructions, ", "see Section 5.2.")
    annotations = (annotation,)
    if control in {"unmapped", "synthetic"}:
        first, second = annotation.native_pieces
        second = (
            replace(second, start=second.start + 1)
            if control == "unmapped"
            else replace(second, kind="synthetic_separator", item_ref=None, source_field=None)
        )
        annotations = (replace(annotation, native_pieces=(first, second)),)
    elif control == "ambiguous":
        annotations = (annotation, replace(annotation, block_id="#/texts/other"))
    elif control == "duplicate":
        view = replace(view, pieces=(*view.pieces, view.pieces[1]))
    else:
        # The designator is a source role even though it is not a recipe node.
        tokens = tuple(
            replace(token, piece_indices=(0, 1))
            if view.text[token.start : token.end] == "5.2"
            else token
            for token in annotation.tokens
        )
        assert tokens != annotation.tokens
        annotations = (replace(annotation, tokens=tokens),)
    output = _inspect(view, passage, *annotations)
    assert output.matches == ()
    assert output.outcome() == ("empty" if control == "wrong_role" else "unsupported")


@pytest.mark.parametrize(
    ("prefix", "suffix"),
    [("For earlier instructions, see ", "Section 5.2."), ("See Section ", "5.2.")],
)
def test_joined_block_does_not_merge_cross_piece_cue_or_subject(prefix, suffix):
    view, passage, annotation = _joined(prefix, suffix, select_suffix=False)
    output = _inspect(view, passage, annotation)
    assert output.inspected_count == 2 and output.matches == () and output.outcome() == "empty"


def test_detached_match_can_apply_exact_archived_joined_piece_policy():
    view, passage, annotation = _joined("For context, ", "see Section 5.2.")
    output = _inspect(
        view,
        passage,
        annotation,
        native_piece_policy=b'{"version":"4","joined_piece_kinds":["definition_reference"]}',
    )
    assert output.inspected_count == 1 and output.outcome() == "empty"
    with pytest.raises(ValueError, match="native-piece policy"):
        _inspect(view, passage, annotation, native_piece_policy=b'{"version":"3"}')


def test_optional_definition_concept_requires_its_own_exact_piece_tokens():
    view, passage, annotation = _joined(
        "For context, ", 'definition ID "response-time" as defined in Section 6.3.'
    )
    (match,) = _inspect(view, passage, annotation).matches
    assert match.definition_subject is not None
    extent, kind = match.definition_subject
    assert view.text[slice(*extent)] == "response-time" and kind == "identifier"
    forged = tuple(
        replace(token, piece_indices=(0, 1))
        if token.start < extent[1] and extent[0] < token.end
        else token
        for token in annotation.tokens
    )
    assert forged != annotation.tokens
    (retained,) = _inspect(view, passage, replace(annotation, tokens=forged)).matches
    assert retained.definition_subject is None
    assert (retained.left, retained.cue, retained.evidence()) == (
        match.left,
        match.cue,
        match.evidence(),
    )


def test_v4_keeps_same_block_roles_and_limits_joined_pieces_to_citation_rules():
    text = "Version B supersedes Version A."
    view = source(text, labels=("text",))
    view = replace(view, items=tuple(dict(item, content_layer="body") for item in view.items))
    prepared = prepare_source(view, annotations_only=True)
    assert not prepared.annotation_errors
    passage = StructuralPassage(
        passage_id="runbook",
        source_ref="fixture",
        start=0,
        end=len(text),
        scope="incident-response",
        text=text,
    )
    v3 = _inspect(view, passage, *prepared.annotations, version=NAMED_COVERAGE_VERSION)
    v4 = _inspect(view, passage, *prepared.annotations)
    assert len(v3.matches) == 1
    assert v3 == v4
    joined, joined_passage, joined_annotation = _joined("For operational context, ", text)
    output = _inspect(joined, joined_passage, joined_annotation)
    assert output.inspected_count == 1 and output.outcome() == "empty"
