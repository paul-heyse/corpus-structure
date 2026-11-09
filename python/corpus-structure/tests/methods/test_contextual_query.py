"""Scope and evidence controls for independently attributed retrieval context."""

from dataclasses import replace

import pytest

from corpus_structure.methods.contextual_embeddings import (
    E5,
    ContextCoreLimited,
    ContextInput,
    render_context,
)
from corpus_structure.methods.contextual_query import QueryContextSelection, resolve_query_contexts
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.record_contracts import anchor_identity

from .test_contextual_candidates import PIN

TEXT = "A supervisor approves the request. She files it. Archive it."
NODES = {"#/texts/1": {"text": TEXT}, "#/texts/2": {"text": TEXT}}


def _anchor(literal, pointer="#/texts/1"):
    start = TEXT.index(literal)
    anchor = dict(
        pin=PIN,
        space="native",
        pointer=pointer,
        precision="exact",
        start=start,
        end=start + len(literal),
        source_piece=literal,
    )
    return dict(anchor, anchor_id=anchor_identity(anchor))


def _row(key, semantic_type, *, anchors=(), members=(), value=None):
    row = dict(
        operation_key="operator",
        semantic_type=semantic_type,
        item_key=key,
        anchors=anchors,
        pin=PIN,
        members=tuple(m["contribution_id"] for m in members),
        value=source_value(value),
    )
    return dict(row, contribution_id=contribution_identity(row))


def _location(literal, pointer="#/texts/1"):
    return _row(literal, "source_occurrence", anchors=(_anchor(literal, pointer),))


def _resolve(recipe, root, closure, focal, *, pointer="#/texts/1"):
    anchors = (_anchor(focal, pointer),)
    occurrence = occurrence_identity(anchors)
    selection = QueryContextSelection.model_validate(
        {
            "recipe": recipe,
            "bindings": [
                {
                    "occurrence_id": occurrence,
                    "evidence": {
                        "contribution_id": root["contribution_id"],
                        "project_id": "project",
                        "release_id": "release",
                        "run_id": 1,
                        "cut_id": 2,
                        "result_revision": 0,
                        "selected_task_id": 3,
                        "origin_task_id": 3,
                        "runtime_fingerprint": "runtime",
                    },
                }
            ],
        }
    )
    return resolve_query_contexts(
        selection,
        ({"contributions": (root, *closure), "sources": ({"pin": PIN},)},),
        ({"occurrence_id": occurrence, "anchors": anchors},),
        NODES,
        PIN,
    )[occurrence]


def test_located_frame_keeps_native_roles_and_exact_focal_input():
    predicate, argument = _location("approves"), _location("the request")
    root = _row(
        "frame",
        "linguistic.predicate_frame",
        members=(predicate, argument),
        value={
            "predicate": "approves",
            "dependency_arguments": [
                {"role": "obj", "location": "the request"},
                {"role": "nsubj", "location": "unmapped"},
            ],
            "srl_frames": [{"arguments": [{"role": "ARG1", "location": "the request"}]}],
        },
    )
    signal = _resolve("located-frame-1", root, (predicate, argument), "request")
    assert (
        signal.rendered == "Predicate: approves\nDependency obj: the request\nSRL ARG1: the request"
    )
    assert signal.omissions == ("Dependency nsubj has no exact source location",)
    start = TEXT.index("request")
    query = ContextInput("occ", "source", "query", "request", TEXT, start, start + 7)
    baseline = render_context(query, E5, len)
    enriched = render_context(
        replace(
            query,
            representation_digest=signal.representation_digest,
            query_context=signal.rendered,
        ),
        E5,
        len,
    )
    assert baseline.text.startswith("Mention: request\n")
    assert enriched.text.startswith("Mention: request\n")
    assert enriched.text.endswith("Context: " + TEXT)
    assert enriched.final_input_digest != baseline.final_input_digest
    assert (
        enriched.object_id == baseline.object_id
        and enriched.source_binding == baseline.source_binding
    )
    with pytest.raises(ValueError, match="does not locate"):
        _resolve("located-frame-1", root, (predicate, argument), "request", pointer="#/texts/2")


def test_required_signal_cannot_be_truncated_into_an_ordinary_query():
    profile = replace(E5, max_tokens=55)
    baseline = ContextInput("occ", "source", "query", "request", TEXT, TEXT.index("request"), 33)
    assert render_context(baseline, profile, len).text.startswith("Mention: request\n")
    with pytest.raises(ContextCoreLimited, match="discriminating context"):
        render_context(
            replace(baseline, representation_digest="signal", query_context="Predicate: approves"),
            profile,
            len,
        )
    with pytest.raises(ValueError, match="representation identity"):
        replace(baseline, role="document", representation_digest="signal", query_context="added")


def test_local_descriptor_uses_located_earlier_member_not_later_lookalike():
    earlier, focal, later = _location("A supervisor"), _location("She"), _location("Archive")
    members = tuple(
        _row(str(i), "maverick.mention", members=(location,), value={"first": first, "last": last})
        for i, (location, first, last) in enumerate(
            ((earlier, 0, 1), (focal, 6, 6), (later, 10, 10))
        )
    )
    root = _row("cluster", "maverick.cluster", members=members)
    closure = (*members, earlier, focal, later)
    signal = _resolve("located-referent-1", root, closure, "She")
    assert signal.rendered == "Earlier local mention: A supervisor"
    absent = _resolve("located-referent-1", root, closure, "supervisor")
    assert not absent.signals and not absent.representation_digest
    assert absent.omissions == ("no earlier local member has an exact source location",)


def test_discourse_uses_one_adjacent_leaf_and_records_wider_omission():
    pieces = ("A supervisor approves the request.", "She files it.", "Archive it.")
    locations = tuple(map(_location, pieces))
    members = tuple(
        _row(str(i), "dipo.edu", members=(location,), value={"edu": i, "arm": "learned"})
        for i, location in enumerate(locations)
    )
    root = _row(
        "tree",
        "dipo.tree",
        members=members,
        value={
            "arm": "learned",
            "root": [0, 3],
            "splits": [
                {"left": [0, 1], "right": [1, 3], "nuclearity": "NS", "relation": "elaboration"},
                {"left": [1, 2], "right": [2, 3], "nuclearity": "NN", "relation": "joint"},
            ],
        },
    )
    signal = _resolve("located-discourse-neighbor-1", root, (*members, *locations), "files")
    assert signal.rendered == "Discourse neighbor: Archive it."
    assert signal.omissions == ("EDUs [0, 1]: wider_than_selected",)
