"""Independent Dipo tree, offset, and context expectations."""

from dataclasses import replace

import pytest
from semantic.record_contracts_support import release_inputs

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.pm2_dipo_products import dipo_context, dipo_products
from corpus_structure.methods.pm2_products import PARSER_QUESTIONS
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.methods.pm2_source import (
    MappedSource,
    PM2SourceMap,
    SourceMapReason,
    SourceMapRefused,
    SourceMapSegment,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from methods.pm2_source_support import identity_map, source_context


def _row(tokens, chars, text):
    return {"tokens": tokens, "chars": chars, "text": text}


def _split(left, right, nuclearity="NS", relation="context-circumstance"):
    return {"left": left, "right": right, "nuclearity": nuclearity, "relation": relation}


def _break(end, *, learned=True, forced=False, disposition="retained"):
    return {"token_end": end, "learned": learned, "forced": forced, "disposition": disposition}


def test_raw_tree_preserves_leading_gap_coincident_and_merged_breaks():
    text = "  Valve opens. Alarm sounds."
    mapping = identity_map(text)
    request = {"text": text, "mode": "layout_forced"}
    boundaries = [
        _break(1, disposition="merged"),
        _break(3, forced=True),
        _break(6),
    ]
    reply = {
        "mode": "layout_forced",
        "post_tokenizer_tokens": 6,
        "edus": [_row([0, 3], [2, 14], "Valve opens."), _row([3, 6], [14, 28], "Alarm sounds.")],
        "spans": [_split([0, 1], [1, 2])],
        "boundaries": boundaries,
    }
    result = dipo_products(mapping, request, reply)
    first, second, tree = result.products
    assert tree.members == (first.key, second.key)
    assert tree.value["root"] == [0, 2]
    assert tree.value["provider_gaps"] == [[0, 2]]
    assert tree.value["boundaries"] == boundaries
    assert tree.value["splits"] == [_split([0, 1], [1, 2])]
    located = result.locations[second.members[0]]
    assert isinstance(located, MappedSource)
    assert [(piece.start, piece.end, piece.quote) for piece in located.pieces] == [
        (15, 28, "Alarm sounds.")
    ]
    assert dipo_context(tree.value, focal=0, located_edus={0, 1}, max_edus=2)["sibling"] == [1, 2]
    assert dipo_context(tree.value, focal=0, located_edus={0}, max_edus=2)["omitted"] == [
        {"range": [1, 2], "reason": "unmapped_edu"}
    ]
    assert dipo_context(tree.value, focal=0, located_edus={0, 1}, max_edus=1)["omitted"] == [
        {"range": [1, 2], "reason": "context_bound"}
    ]
    with pytest.raises(ValueError, match="ordered split"):
        dipo_products(mapping, request, {**reply, "spans": [_split([1, 2], [0, 1])]})
    with pytest.raises(ValueError, match="provenance differs"):
        dipo_products(mapping, request, {**reply, "boundaries": [_break(6)]})

    dimensions = {"question": PARSER_QUESTIONS["dipo"], "operation_version": "1"}
    profile = {"provider": "dipo"}
    retained = pm2_unit_result(
        UnitRef(TaskUnitType.SOURCE_VIEW, 1, "unit:1"),
        mapping,
        profile=profile,
        request=request,
        reply=dict(reply, outcome="succeeded"),
        input_digest=pm2_input_digest(mapping, profile, request, **dimensions),
        prepared=release_inputs()[2],
        **dimensions,
    )
    rows = {row["item_key"]: row for row in retained.contributions or ()}
    root = rows["layout_forced:tree"]
    assert root["contract"] == "PM2DipoTreeContributionV1"
    assert source_python(root["value"])["provider_gaps"] == [{"start": 0, "end": 2}]
    assert rows["layout_forced:edu:0"]["contract"] == "PM2DipoEDUContributionV1"


def test_singleton_can_have_exact_whitespace_pieces_without_claiming_the_gap():
    plain = source_context(
        (
            ("#/texts/1", "text", "μ opens", "μ opens"),
            (None, None, "\n", None),
            ("#/texts/2", "text", "the valve.", "the valve."),
        )
    )
    context = replace(plain, version=2, preparation=PreparedNativeSources((plain.primary,)))
    mapping = PM2SourceMap(
        context,
        context.text,
        (SourceMapSegment(0, len(context.text), 0),),
        (),
    )
    request = {"text": context.text}
    reply = {
        "post_tokenizer_tokens": 4,
        "edus": [_row([0, 4], [0, 18], "μ opens the valve.")],
        "spans": [],
        "boundaries": [_break(4)],
    }
    strict = dipo_products(mapping, request, reply)
    leaf, tree = strict.products
    assert isinstance(strict.locations[leaf.members[0]], SourceMapRefused)
    assert tree.value["root"] == [0, 1]
    result = dipo_products(mapping, request, reply, prepared=release_inputs()[2])
    leaf, tree = result.products
    located = result.locations[leaf.members[0]]
    assert isinstance(located, MappedSource)
    assert [piece.quote for piece in located.pieces] == ["μ opens", "the valve."]
    assert leaf.value["whitespace_reading"]["gaps"][0]["model_start"] == 7
    assert dipo_context(tree.value, focal=0, located_edus={0}, max_edus=1)["sibling"] is None


def test_paired_arms_keep_native_reconstruction_separate_and_verify_reviewed_ranges():
    text = "  Stop.\n\nStop.  "
    mapping = identity_map(text)
    request = {"mode": "supplied_edus", "text": text, "edu_ranges": [[2, 7], [9, 14]]}
    reply = {
        "mode": "supplied_edus",
        "post_tokenizer_tokens": 4,
        "reconstruction": {"text": "Stop.\n\nStop.", "raw_start": 2, "raw_end": 14},
        "arms": {
            "supplied": {
                "edus": [_row([0, 2], [0, 5], "Stop."), _row([2, 4], [7, 12], "Stop.")],
                "spans": [_split([0, 1], [1, 2])],
            },
            "predicted": {"edus": [_row([0, 4], [0, 12], "Stop.\n\nStop.")], "spans": []},
        },
    }
    result = dipo_products(mapping, request, reply)
    second = result.locations["supplied:edu:1:extent"]
    assert isinstance(second, MappedSource)
    assert second.pieces[0].start == 9
    assert result.products[-1].value["root"] == [0, 1]
    assert result.products[-1].value["provider_gaps"] == [[0, 2], [14, 16]]
    with pytest.raises(ValueError, match="reconstructed input"):
        dipo_products(
            mapping,
            request,
            {**reply, "reconstruction": {**reply["reconstruction"], "raw_start": 1}},
        )


def test_partial_protected_atom_is_unavailable_without_losing_the_tree():
    mapping = identity_map("x+y matters", atoms=((0, 3),))
    reply = {
        "post_tokenizer_tokens": 4,
        "edus": [_row([0, 1], [0, 1], "x"), _row([1, 4], [1, 11], "+y matters")],
        "spans": [_split([0, 1], [1, 2])],
        "boundaries": [_break(1), _break(4)],
    }
    result = dipo_products(mapping, {"text": mapping.provider_text}, reply)
    first = result.locations["learned:edu:0:extent"]
    assert isinstance(first, SourceMapRefused) and first.reason == SourceMapReason.PROTECTED_ATOM
    assert result.products[-1].value["root"] == [0, 2]
