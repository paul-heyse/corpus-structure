"""Independent native meanings survive current nominal source and HanLP products."""

import json

import pytest

from corpus_structure.ingest.annotations import annotate
from methods.native_evidence_support import native_source as native_source
from methods.native_evidence_support import retained_hanlp
from methods.navigation_fixture import source_primary_products


def hanlp_reply(case, *, missing_predicate=False):
    text = case.primary.source.value["text"]
    words = [text[row["start"] : row["end"]] for row in case.words]
    prepared = [word if index == 0 else " " + word for index, word in enumerate(words)]
    arcs = [[len(words), "dep"] for _ in words]
    arcs[-1] = [0, "root"]
    labels = [("ARG1", 0, 1), ("R-ARG1", 1, 2), ("C-ARG1", 3, 4)]
    if not missing_predicate:
        labels.insert(1, ("PRED", 2, 3))
    return dict(
        lemma=[" " + word for word in words],
        pos=["NN"] * len(words),
        dependency=arcs,
        constituency=[
            "TOP",
            [
                [
                    "FRAG",
                    [
                        ["WHADVP", [["NN", [prepared[0]]]]],
                        *[["NN", [word]] for word in prepared[1:]],
                    ],
                ]
            ],
        ],
        srl=[[(" ".join(prepared[a:b]), label, a, b) for label, a, b in labels]],
    ), dict(
        prepared_words=prepared,
        word_subwords=[[i + 1] for i in range(len(words))],
        input_ids=[100, *range(1, len(words) + 1), 101],
    )


def test_complete_native_constituents_raw_srl_and_conflicting_heads_survive_current_products(
    native_source,
):
    native, preparation = hanlp_reply(native_source)
    product, canonical = retained_hanlp(native_source, native, preparation)
    body = product.value.model_dump(mode="json", exclude_unset=True)
    units = [packet["body"] for packet in body["members"]]
    constituents = [row for row in units if row["record_type"] == "constituent"]
    assert {row["label"] for row in constituents} == {"TOP", "FRAG", "WHADVP", "NN"}
    assert len(constituents) == len(native_source.words) + 3
    (group,) = [row for row in units if row["record_type"] == "srl_group"]
    assert [(role["label"], role["start"], role["end"]) for role in group["roles"]] == [
        ("ARG1", 0, 1),
        ("PRED", 2, 3),
        ("R-ARG1", 1, 2),
        ("C-ARG1", 3, 4),
    ]
    assert [role["native_text"] for role in group["roles"]] == ["X", " é", " X", " x+y"]
    tokens = [row for row in units if row["record_type"] == "token"]
    assert tokens[0]["dependency_head"] == len(tokens)
    assert tokens[-1]["dependency_head"] == 0
    assert tokens[1]["lemma"] == " X"
    source_native = native_source.primary.native
    assert source_native is not None
    source_columns = json.loads(source_native.content)["blocks"][0]["annotation"]["tokens"]
    assert source_columns[0]["head"] == 0
    assert source_columns[-1]["head"] == 0
    canonical_tokens = {
        packet["member_id"]: packet["body"]
        for packet in json.loads(canonical.content)["members"]
        if packet["body"]["record_type"] == "token"
    }
    text = native_source.primary.frame.text
    assert [
        [
            text[
                canonical_tokens[ref["member_id"]]["start"] : canonical_tokens[ref["member_id"]][
                    "end"
                ]
            ]
            for ref in role["tokens"]
        ]
        for role in group["roles"]
    ] == [["X"], ["é"], ["X"], ["x+y"]]
    assert all(
        ref["product_id"] == canonical.reference.product_id
        for role in group["roles"]
        for ref in role["tokens"]
    )
    assert body["canonical"] == canonical.reference.values()
    assert all(row["outcome"] == "complete" for row in body["coverage"])
    assert sum(len(row["children"]) for row in constituents) == len(tokens) * 2 + 2


def test_missing_predicate_keeps_native_roles_and_marks_only_srl_partial(native_source):
    native, preparation = hanlp_reply(native_source, missing_predicate=True)
    product, _ = retained_hanlp(native_source, native, preparation)
    body = json.loads(product.content)
    (group,) = [
        packet["body"] for packet in body["members"] if packet["body"]["record_type"] == "srl_group"
    ]
    assert len(group["roles"]) == 3
    coverage = {row["family"]: row["outcome"] for row in body["coverage"]}
    assert coverage["hanlp.srl"] == "partial"
    assert coverage["hanlp.constituency"] == "complete"


@pytest.mark.parametrize("head", ["srl", "constituency", "dependency"])
def test_malformed_head_retains_independent_valid_native_siblings(native_source, head):
    native, preparation = hanlp_reply(native_source)
    native[head] = (
        [[0, "broken"]]
        if head == "dependency"
        else ["wrong-yield"]
        if head == "constituency"
        else [[("wrong", "ARG1", 0, 99)]]
    )
    product, _ = retained_hanlp(native_source, native, preparation)
    coverage = {row["family"]: row["outcome"] for row in json.loads(product.content)["coverage"]}
    assert coverage["hanlp." + head] == "failed"
    assert all(
        coverage["hanlp." + sibling] == "complete"
        for sibling in {"srl", "constituency", "dependency"} - {head}
    )


def test_optional_spacy_columns_retain_independent_available_families(native_source):
    native_source.controlled.omit = "lemma"
    (annotation,) = annotate([native_source.request], native_source.profile, require_complete=False)
    primary = source_primary_products(
        native_source.primary.frame, (annotation,), profile=native_source.profile
    )
    assert primary.native is not None
    coverage = {
        row["family"]: row["outcome"] for row in json.loads(primary.native.content)["coverage"]
    }
    assert coverage["spacy.lemma"] == "partial"
    assert coverage["spacy.dependency"] == "complete"


def test_cross_page_exact_members_keep_page_and_synthetic_gap(native_source):
    from corpus_structure.semantic.contextual_characterization import (
        ContextInput,
        ContextPart,
        ContextualLayer,
    )
    from methods.declared_primary_fixture import selected_source

    text = native_source.primary.frame.text
    _, frame, _ = selected_source(
        text,
        pieces=[
            dict(kind="native_text", item_ref="#/texts/left", source_field="text", start=0, end=1),
            dict(kind="synthetic_separator", start=1, end=2),
            dict(
                kind="native_text",
                item_ref="#/texts/right",
                source_field="text",
                start=2,
                end=len(text),
            ),
        ],
        items=[
            dict(
                self_ref="#/texts/left",
                label="text",
                text=text[:1],
                orig=text[:1],
                prov=[dict(page_no=3)],
            ),
            dict(
                self_ref="#/texts/right",
                label="text",
                text=text[2:],
                orig=text[2:],
                prov=[dict(page_no=4)],
            ),
        ],
    )
    context = ContextInput.build([ContextPart(frame, 0, len(text))], [])
    builder = ContextualLayer(frame.value["source"], {"selectors": []}, {"key": "fixture"}, context)
    repeated = [builder.occurrence(frame, 0, 1), builder.occurrence(frame, 2, 3)]
    assert [builder.occurrences[key]["extents"][0]["page"] for key in repeated] == [3, 4]
    assert [
        (row["start"], row["end"], row["synthetic"])
        for row in builder.occurrences[builder.support[0]]["extents"]
    ] == [(0, 1, False), (1, 2, True), (2, 14, False)]
