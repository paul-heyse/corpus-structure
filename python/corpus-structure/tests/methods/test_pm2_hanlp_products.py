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
    assert {row.semantic_type for row in result.products} == {"linguistic.constituent"}
    labels = {row.value["label"] for row in result.products}
    assert {"TOP", "S", "NP", "MD", "IN"} <= labels
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
        "linguistic.constituent": "PM2HanLPPhraseContributionV1",
    }


def test_forged_yield_refuses_and_partial_atom_retains_unmapped_location():
    words = ["x", "y", "changes"]
    tags = ["NN", "NN", "VBZ"]
    arcs = [[2, "compound"], [3, "nsubj"], [0, "root"]]
    mapping, request, reply = _scope(
        words, tags, arcs, atoms=((0, 3),), srl=((("ARG0", 0, 1), ("PRED", 2, 3)),)
    )
    result = hanlp_products(mapping, request, reply)
    leaf = next(row.value for row in result.products if row.value["label"] == "NN")
    assert isinstance(result.locations[leaf["location"]], SourceMapRefused)
    verb = next(row.value for row in result.products if row.value["label"] == "VBZ")
    assert _quoted(result, verb["location"]) == ["changes"]

    forged = deepcopy(reply)
    forged["native"]["con"][0][1][0][1][0][1] = ["y"]
    with pytest.raises(ValueError, match="yield differs"):
        hanlp_products(mapping, request, forged)


@pytest.mark.parametrize("corruption", ["dependency", "srl_bounds", "srl_text"])
def test_native_input_protection_survives_interpretation_retirement(corruption):
    mapping, request, reply = _scope(["X", "moves"], ["NN", "VBZ"], [[2,"nsubj"],[0,"root"]],
                                  srl=((("ARG0",0,1),("PRED",1,2)),))
    if corruption == "dependency":
        reply["native"]["dep"][0][0][0] = 99
    elif corruption == "srl_bounds":
        reply["native"]["srl"][0][0][0] = ("X","ARG0",0,99)
    else:
        reply["native"]["srl"][0][0][0] = ("forged","ARG0",0,1)
    with pytest.raises(ValueError):
        hanlp_products(mapping,request,reply)
