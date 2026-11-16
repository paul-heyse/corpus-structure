"""Independent native members and complete evidence, never provider-accuracy claims."""

from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.ingest.annotations import annotate
from corpus_structure.methods.native_evidence_layers import (
    SPACY_FAMILIES,
    NativeEvidenceBuilder,
)
from corpus_structure.semantic.characterization import (
    decode_layer,
    encode_layer,
)
from methods.native_evidence_support import (
    builder_for as builder_for,
)
from methods.native_evidence_support import (
    metadata as metadata,
)
from methods.native_evidence_support import (
    native_source as native_source,
)
from methods.native_evidence_support import (
    prepared as prepared,
)


def hanlp_reply(words, *, missing_predicate=False) -> tuple[dict[str, Any], dict[str, Any]]:
    prepared = [t["text"] if i == 0 else " " + t["text"] for i, t in enumerate(words)]
    # Deliberately disagree with spaCy, including the native root convention.
    arcs = [[len(words), "dep"] for _ in words]
    arcs[-1] = [0, "root"]
    labels = [("ARG1", 0, 1), ("R-ARG1", 1, 2), ("C-ARG1", 3, 4)]
    if not missing_predicate:
        labels.insert(1, ("PRED", 2, 3))
    srl = [[(" ".join(prepared[a:b]), label, a, b) for label, a, b in labels]]
    children = [["WHADVP", [["NN", [prepared[0]]]]], *[["NN", [word]] for word in prepared[1:]]]
    tree = ["TOP", [["FRAG", children]]]
    native = dict(
        lemma=[" " + t["text"] for t in words],
        pos=["NN"] * len(words),
        dependency=arcs,
        constituency=tree,
        srl=srl,
    )
    preparation = dict(prepared_words=prepared, word_subwords=[[i + 1] for i in range(len(words))])
    return native, preparation


def quoted(body, annotation):
    occurrences = {o["local_id"]: o for o in body["occurrences"]}
    return [
        (e["start"], e["end"], e["text"])
        for oid in annotation["occurrences"]
        for e in occurrences[oid]["extents"]
    ]


def test_complete_native_constituents_raw_srl_and_conflicting_heads_survive_shared_codec(
    native_source, prepared
):
    builder, words = builder_for(native_source)
    view, product = native_source[3], native_source[2]
    native, preparation = hanlp_reply(words)
    builder.hanlp_sentence(view, product, words, 0, native, preparation, "hanlp")
    metadata(builder)
    retained = decode_layer(prepared, encode_layer(builder.finish(prepared)))
    body = retained.payload
    constituents = [a for a in body["annotations"] if a["kind"] == "native.constituent"]
    assert {a["native_label"] for a in constituents} == {"TOP", "FRAG", "WHADVP", "NN"}
    assert len(constituents) == len(words) + 3
    roles = [a for a in body["annotations"] if a["kind"] == "native.srl_role"]
    assert [(a["native_label"], quoted(body, a)) for a in roles] == [
        ("ARG1", [(0, 1, "X")]),
        ("PRED", [(4, 5, "é")]),
        ("R-ARG1", [(2, 3, "X")]),
        ("C-ARG1", [(6, 9, "x+y")]),
    ]
    assert {a["native_scheme"] for a in roles} == {"hanlp-propbank-srl-native-1"}
    token_rows = [a["native_token"] for a in body["annotations"] if a["kind"] == "native.token"]
    assert any(
        t["native_run"] == "spacy" and t["index"] == 0 and t["native_head"] == 0 for t in token_rows
    )
    assert any(
        t["native_run"] == "hanlp"
        and t["index"] == len(words) - 1
        and t["native_head"] == 0
        and t["head_index_base"] == 1
        for t in token_rows
    )
    assert (
        next(t for t in token_rows if t["native_run"] == "hanlp" and t["index"] == 1)["lemma"]
        == " X"
    )
    assert all(row["outcome"] == "complete" for row in body["coverage"])
    child_edges = [m for m in body["memberships"] if m["role"] == "child"]
    assert len(child_edges) == len(words) * 2 + 2


def test_missing_predicate_keeps_native_roles_and_marks_only_srl_partial(native_source, prepared):
    builder, words = builder_for(native_source)
    native, preparation = hanlp_reply(words, missing_predicate=True)
    builder.hanlp_sentence(
        native_source[3], native_source[2], words, 0, native, preparation, "hanlp"
    )
    metadata(builder)
    body = builder.finish(prepared).payload
    assert len([a for a in body["annotations"] if a["kind"] == "native.srl_role"]) == 3
    assert {c["family"]: c["outcome"] for c in body["coverage"]}["hanlp.srl"] == "partial"
    assert (
        next(c for c in body["coverage"] if c["family"] == "hanlp.constituency")["outcome"]
        == "complete"
    )


@pytest.mark.parametrize("head", ["srl", "constituency", "dependency"])
def test_malformed_head_retains_independent_valid_native_siblings(native_source, prepared, head):
    builder, words = builder_for(native_source)
    native, preparation = hanlp_reply(words)
    native[head] = (
        [[0, "broken"]]
        if head == "dependency"
        else ["wrong-yield"]
        if head == "constituency"
        else [[("wrong", "ARG1", 0, 99)]]
    )
    builder.hanlp_sentence(
        native_source[3], native_source[2], words, 0, native, preparation, "hanlp"
    )
    metadata(builder)
    body = builder.finish(prepared).payload
    coverage = {c["family"]: c for c in body["coverage"]}
    assert coverage["hanlp." + head]["outcome"] == "failed"
    assert all(
        coverage["hanlp." + name]["outcome"] == "complete"
        for name in {"srl", "constituency", "dependency"} - {head}
    )


def test_optional_spacy_columns_retain_independent_available_families(native_source, prepared):
    controlled, request = native_source[:2]
    controlled.omit = "lemma"
    (product,) = annotate([request], require_complete=False)
    builder = NativeEvidenceBuilder(
        native_source[4],
        native_source[5],
        native_source[6],
        profile="spacy_only",
        families=SPACY_FAMILIES,
    )
    builder.spacy(native_source[3], product, "spacy")
    metadata(builder)
    body = builder.finish(prepared).payload
    assert next(c for c in body["coverage"] if c["family"] == "spacy.lemma")["outcome"] == "partial"
    assert (
        next(c for c in body["coverage"] if c["family"] == "spacy.dependency")["outcome"]
        == "complete"
    )


def test_cross_page_exact_members_keep_page_and_synthetic_gap(native_source, prepared):
    _, _, product, view, base, scope, operation = native_source
    view = SimpleNamespace(
        ref=view.ref,
        text=view.text,
        pieces=[
            dict(kind="native_text", item_ref="#/texts/left", start=0, end=1),
            dict(kind="synthetic_separator", start=1, end=2),
            dict(kind="native_text", item_ref="#/texts/right", start=2, end=len(view.text)),
        ],
        items=[
            dict(self_ref="#/texts/left", prov=[dict(page_no=3)]),
            dict(self_ref="#/texts/right", prov=[dict(page_no=4)]),
        ],
    )
    builder = NativeEvidenceBuilder(
        base, scope, operation, profile="spacy_only", families=SPACY_FAMILIES
    )
    builder.spacy(view, product, "spacy")
    metadata(builder)
    body = builder.finish(prepared).payload
    tokens = [a for a in body["annotations"] if a["kind"] == "native.token"]
    repeated = [a for a in tokens if a["native_token"]["text"] == "X"]
    occurrences = {o["local_id"]: o for o in body["occurrences"]}
    assert [occurrences[a["occurrences"][0]]["extents"][0]["page"] for a in repeated] == [3, 4]
    block = next(a for a in body["annotations"] if a["kind"] == "native.block")
    assert [
        (e["start"], e["end"], e["synthetic"])
        for e in occurrences[block["occurrences"][0]]["extents"]
    ] == [(0, 1, False), (1, 2, True), (2, 14, False)]


@pytest.mark.parametrize("corruption", (None, "missing", "ordinal", "member", "digest"))
def test_current_hanlp_sentence_requires_exact_physical_batch_commitment(
    native_source, prepared, corruption
):
    from hashlib import sha256

    from corpus_structure.semantic.characterization import validate_layer
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.observations import source_python, source_value

    output, words = builder_for(native_source)
    output.operation["version"] = "2"
    native, preparation = hanlp_reply(words)
    header = dict(provider="hanlp", profile="b" * 64, runtime="c" * 64)
    members = [sha256(canonical_bytes([token["text"] for token in words])).hexdigest()]
    receipt = dict(
        version=1,
        header=header,
        members=members,
        digest=sha256(canonical_bytes([header, members])).hexdigest(),
        member_ordinal=0,
    )
    preparation["batch_receipt"] = receipt
    output.hanlp_sentence(
        native_source[3], native_source[2], words, 0, native, preparation, "hanlp"
    )
    metadata(output)
    layer = output.finish(prepared)
    payload = layer.payload
    sentence = next(
        row
        for row in payload["annotations"]
        if row["family"] == "hanlp.tokens" and row["kind"] == "native.sentence"
    )
    if corruption is None:
        assert source_python(sentence["native_batch"]) == receipt
        return
    if corruption == "missing":
        del sentence["native_batch"]
    else:
        broken = source_python(sentence["native_batch"])
        if corruption == "ordinal":
            broken["member_ordinal"] = 1
        elif corruption == "member":
            broken["members"] = ["d" * 64]
            broken["digest"] = sha256(canonical_bytes([header, broken["members"]])).hexdigest()
        else:
            broken["digest"] = "e" * 64
        sentence["native_batch"] = source_value(broken)
    with pytest.raises(ValueError, match="batch"):
        validate_layer(prepared, payload)
