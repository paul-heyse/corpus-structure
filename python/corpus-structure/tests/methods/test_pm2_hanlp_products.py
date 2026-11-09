"""Independent native-coordinate controls for private HanLP products."""

from __future__ import annotations

from copy import deepcopy

import pytest
from semantic.test_record_contracts import release_inputs

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.pm2_hanlp_products import hanlp_products
from corpus_structure.methods.pm2_products import PARSER_QUESTIONS
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.methods.pm2_source import PM2TokenMap, ProviderToken, SourceMapRefused
from methods.test_pm2_source import identity_map


def _scope(words, tags, arcs, *, srl=(), lemmas=None, constituent=None, atoms=()):
    text = " ".join(words)
    starts = []
    cursor = 0
    for word in words:
        starts.append(cursor)
        cursor += len(word) + 1
    mapping = PM2TokenMap(
        identity_map(text, atoms=atoms),
        tuple(
            ProviderToken(word, start, start + len(word), 0)
            for word, start in zip(words, starts, strict=True)
        ),
    )
    prepared = [word if i == 0 else " " + word for i, word in enumerate(words)]
    arguments = [[(" ".join(prepared[a:b]), label, a, b) for label, a, b in frame] for frame in srl]
    children = [[tag, [word]] for tag, word in zip(tags, prepared, strict=True)]
    if constituent is not None:
        a, b = constituent
        children[a:b] = [["NP", children[a:b]]]
    tree = ["S", children]
    native_lemmas = [" " + lemma for lemma in (lemmas or words)]
    return (
        mapping,
        {"sentences": [words]},
        {
            "native": {
                "tok": [words],
                "lem": [native_lemmas],
                "pos": [tags],
                "dep": [arcs],
                "srl": [arguments],
                "con": [["TOP", [tree]]],
            },
            "preparation": [{"prepared_words": prepared}],
        },
    )


def _quoted(result, key):
    return [piece.quote for piece in result.locations[key].pieces]


def test_conditional_host_alternatives_and_srl_roles_remain_independent():
    words = ["If", "pressure", "rises", ",", "the", "valve", "must", "close", "and", "remain", "."]
    tags = ["IN", "NN", "VBZ", ",", "DT", "NN", "MD", "VB", "CC", "VB", "."]
    arcs = [
        [3, "mark"],
        [3, "nsubj"],
        [8, "advcl"],
        [3, "punct"],
        [6, "det"],
        [8, "nsubj"],
        [8, "aux"],
        [0, "root"],
        [10, "cc"],
        [8, "conj"],
        [8, "punct"],
    ]
    mapping, request, native = _scope(
        words,
        tags,
        arcs,
        srl=((("ARG1", 4, 6), ("PRED", 7, 8), ("R-ARG1", 1, 2), ("C-ARG1", 9, 10)),),
        constituent=(4, 6),
    )
    result = hanlp_products(mapping, request, native)
    products = {row.key: row.value for row in result.products}
    frame = products["s0/predicate/7"]
    assert frame["scheme"] == "hanlp-ud-ptb-propbank-1"
    assert _quoted(result, frame["predicate"]) == ["close"]
    assert _quoted(result, frame["focus"]) == ["the valve must close", "."]
    native_roles = frame["srl_frames"][0]["arguments"]
    assert [(role["role"], _quoted(result, role["location"])) for role in native_roles] == [
        ("ARG1", ["the valve"]),
        ("R-ARG1", ["pressure"]),
        ("C-ARG1", ["remain"]),
    ]
    assert products["s0/predicate/9"]["srl_frames"] == []
    cue = products["s0/cue/0/condition"]
    assert _quoted(result, cue["location"]) == ["If pressure rises ,"]
    assert cue["candidates"] == ["s0/predicate/7", "s0/predicate/9"]
    modal = products["s0/cue/6/modality"]
    assert modal["candidates"] == ["s0/predicate/7"]
    assert _quoted(result, modal["location"]) == ["must"]
    phrase = next(row.value for row in result.products if row.value.get("label") == "NP")
    assert _quoted(result, phrase["location"]) == ["the valve"]

    dimensions = {"question": PARSER_QUESTIONS["hanlp"], "operation_version": "1"}
    profile = {"provider": "hanlp"}
    retained = pm2_unit_result(
        UnitRef(TaskUnitType.SOURCE_VIEW, 1, "unit:1"),
        mapping,
        profile=profile,
        request=request,
        reply=dict(native, outcome="succeeded"),
        input_digest=pm2_input_digest(mapping, profile, request, **dimensions),
        prepared=release_inputs()[2],
        **dimensions,
    )
    assert {row["semantic_type"]: row["contract"] for row in retained.contributions or ()} == {
        "source_occurrence": "RetainedContributionSemantics",
        "linguistic.predicate_frame": "PM2HanLPFrameContributionV1",
        "linguistic.qualifier_cue": "PM2HanLPCueContributionV1",
        "linguistic.constituent": "PM2HanLPPhraseContributionV1",
    }


@pytest.mark.parametrize("noun", ["médiane", "valve"])
def test_reported_passive_keeps_grammatical_roles_and_nested_attribution(noun):
    words = ["They", "said", "the", noun, "was", "not", "replaced", "by", "Jo", "."]
    tags = ["PRP", "VBD", "DT", "NN", "VBD", "RB", "VBN", "IN", "NNP", "."]
    arcs = [
        [2, "nsubj"],
        [0, "root"],
        [4, "det"],
        [7, "nsubj:pass"],
        [7, "aux:pass"],
        [7, "advmod"],
        [2, "ccomp"],
        [9, "case"],
        [7, "obl:agent"],
        [2, "punct"],
    ]
    lemmas = ["they", "say", "the", noun, "be", "not", "replace", "by", "Jo", "."]
    result = hanlp_products(*_scope(words, tags, arcs, lemmas=lemmas))
    products = {row.key: row.value for row in result.products}
    frame = products["s0/predicate/6"]
    assert frame["voice"] == "passive"
    assert [
        (role["role"], _quoted(result, role["location"])) for role in frame["dependency_arguments"]
    ] == [
        ("nsubj:pass", ["the " + noun]),
        ("obl:agent", ["by Jo"]),
    ]
    assert products["s0/cue/5/negation"]["candidates"] == ["s0/predicate/6"]
    attribution = products["s0/cue/6/attribution"]
    assert attribution["attribution_source"] == "s0/predicate/1"
    assert attribution["candidates"] == ["s0/predicate/6"]


def test_forged_yield_refuses_and_partial_atom_retains_unmapped_location():
    words = ["x", "y", "changes"]
    tags = ["NN", "NN", "VBZ"]
    arcs = [[2, "compound"], [3, "nsubj"], [0, "root"]]
    mapping, request, reply = _scope(
        words, tags, arcs, atoms=((0, 3),), srl=((("ARG0", 0, 1), ("PRED", 2, 3)),)
    )
    result = hanlp_products(mapping, request, reply)
    frame = next(row.value for row in result.products if row.key == "s0/predicate/2")
    argument = frame["srl_frames"][0]["arguments"][0]
    assert isinstance(result.locations[argument["location"]], SourceMapRefused)
    assert _quoted(result, frame["predicate"]) == ["changes"]

    forged = deepcopy(reply)
    forged["native"]["con"][0][1][0][1][0][1] = ["y"]
    with pytest.raises(ValueError, match="yield differs"):
        hanlp_products(mapping, request, forged)


@pytest.mark.parametrize(("head", "host"), [(2, 1), (4, 3)])
def test_same_marker_distinguishes_defining_act_from_content_by_native_governor(head, host):
    words = ["It", "defines", "what", "works", "if", "pressure", "rises"]
    tags = ["PRP", "VBZ", "WP", "VBZ", "IN", "NN", "VBZ"]
    arcs = [
        [2, "nsubj"],
        [0, "root"],
        [4, "nsubj"],
        [2, "ccomp"],
        [7, "mark"],
        [7, "nsubj"],
        [head, "advcl"],
    ]
    result = hanlp_products(*_scope(words, tags, arcs))
    cue = next(row.value for row in result.products if row.key == "s0/cue/4/condition")
    assert _quoted(result, cue["marker"]) == ["if"]
    assert _quoted(result, cue["location"]) == ["if pressure rises"]
    assert cue["candidates"] == [f"s0/predicate/{host}"]
