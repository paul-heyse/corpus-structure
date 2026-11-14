"""Independent native members and complete evidence, never provider-accuracy claims."""

from types import SimpleNamespace
from typing import Any, ClassVar

import pytest
import spacy
from annotation_support import item

from corpus_structure.core.method import MethodSettings, UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import annotate
from corpus_structure.ingest.sentences import Block
from corpus_structure.methods import native_evidence as producer
from corpus_structure.methods.native_evidence import (
    NativeEvidenceConfig,
    NativeEvidenceMethod,
    _batch_sentences,
)
from corpus_structure.methods.native_evidence_layers import (
    HANLP_FAMILIES,
    SPACY_FAMILIES,
    NativeEvidenceBuilder,
    retained_spacy_docs,
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


def test_restored_spacy_docs_need_no_pipeline_and_preserve_exact_whitespace(
    native_source, prepared, monkeypatch
):
    controlled, request, _, view, _, _, _ = native_source
    text = " X  X\né x+y [3]."
    request = item(controlled, text, start=0, block=Block(text, ((8, 11),), (), ((12, 15),)))
    (product,) = annotate([request])
    view = SimpleNamespace(
        ref=view.ref, text=text, pieces=[p.to_wire() for p in request.native_pieces]
    )
    builder, _ = builder_for(native_source, full=False)
    # Use a new layer with only this whole block.
    builder = NativeEvidenceBuilder(
        builder.base,
        builder.scope,
        builder.operation,
        profile="spacy_only",
        families=SPACY_FAMILIES,
    )
    builder.spacy(view, product, "spacy")
    metadata(builder)
    report = builder.finish(prepared)
    monkeypatch.setattr(
        annotations, "pipeline", lambda _: pytest.fail("retained replay invoked native model")
    )
    (doc,) = retained_spacy_docs(report, {view.ref.id: view}, spacy.blank("en").vocab).values()
    assert doc.text == text
    assert [(t.idx, t.text) for t in doc if t.text == "X"] == [(1, "X"), (4, "X")]
    assert [t.dep_ for t in doc] == ["ROOT", *(["dep"] * (len(doc) - 1))]
    assert [t.head.i for t in doc] == [0] * len(doc)


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


def test_method_uses_authoritative_operation_and_retains_cost_without_private_frames(
    native_source, prepared, monkeypatch, tmp_path
):
    controlled, request, _, view, base, scope, operation = native_source
    monkeypatch.setattr(producer, "pipeline", lambda _: controlled)
    monkeypatch.setattr(producer, "annotation_inputs", lambda *args, **kwargs: (request,))
    reader = SimpleNamespace(
        prepared=prepared,
        source_views=lambda: [view.ref],
        source_view=lambda _: view,
        source_view_ref={view.ref.id: view.ref}.__getitem__,
    )
    run = SimpleNamespace(reader=reader)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.DOCUMENT, 17), run=run)
    ctx = SimpleNamespace(
        check_active=lambda: None,
        characterization_operation=lambda ref: operation,
        settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    cfg = NativeEvidenceConfig(
        characterization_base_document=base,
        characterization_source_scope=scope,
        characterization_profile="spacy_only",
    )
    (result,) = NativeEvidenceMethod().run([unit], cfg, ctx)
    assert result.cost is not None
    assert result.characterization_layer is not None
    assert result.cost.wall_ms >= 0
    assert result.characterization_layer.payload["operation"]["input"] == "input:fixture"
    assert {a["kind"] for a in result.characterization_layer.payload["annotations"]} == {
        "native.block",
        "native.sentence",
        "native.token",
    }
    assert result.parse_detail is None and result.contributions is None


def test_language_refusal_and_boundary_profile_are_explicit_weaker_results(
    native_source, prepared, tmp_path
):
    _, _, _, view, base, scope, operation = native_source
    reader = SimpleNamespace(
        prepared=prepared,
        source_views=lambda: [view.ref],
        source_view=lambda _: view,
        source_view_ref={view.ref.id: view.ref}.__getitem__,
    )
    unit = SimpleNamespace(
        ref=UnitRef(TaskUnitType.DOCUMENT, 17), run=SimpleNamespace(reader=reader)
    )
    ctx = SimpleNamespace(
        check_active=lambda: None,
        characterization_operation=lambda ref: operation,
        settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    cfg = NativeEvidenceConfig(
        characterization_base_document=base,
        characterization_source_scope=scope,
        language="fr",
        characterization_profile="boundary_only",
    )
    (result,) = NativeEvidenceMethod().run([unit], cfg, ctx)
    assert result.characterization_layer is not None
    assert {c["family"] for c in result.characterization_layer.payload["coverage"]} == {
        "spacy.tokens",
        "spacy.sentences",
    }
    assert all(
        c["outcome"] == "unsupported" for c in result.characterization_layer.payload["coverage"]
    )


def test_actual_subword_preparation_resizes_only_outer_batch(native_source):
    builder, words = builder_for(native_source)

    class Worker:
        startup: ClassVar = dict(max_sentences=8, max_batch_chars=32768, max_padded_subwords=750)

        def __init__(self):
            self.requests = []

        def infer(self, request, **kwargs):
            self.requests.append(request)
            if False:
                yield ()
            if request.get("prepare_bulk"):
                return dict(
                    outcome="prepared_batch",
                    members=[
                        dict(ordinal=i, outcome="prepared", row_tokens=400)
                        for i in range(len(request["sentences"]))
                    ],
                )
            # All-head failure is recorded as one attempt, not invented head success.
            return dict(outcome="limited", reason="fixture-native-failure")

    worker = Worker()
    entries = [(native_source[3], native_source[2], words, i) for i in range(3)]
    from corpus_structure.core.method import drive_prepared_work

    drive_prepared_work(_batch_sentences(worker, entries, builder, lambda: None), lambda: None)
    assert len([r for r in worker.requests if r.get("prepare_bulk")]) == 1
    inference = [r for r in worker.requests if not r.get("prepare_bulk")]
    assert [len(r["sentences"]) for r in inference] == [1, 1, 1]
    assert all(r["sentences"] == [[t["text"] for t in words]] for r in inference)
    assert all(
        status == "failed" for family in HANLP_FAMILIES for _, status, _ in builder.covered[family]
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


def test_overlong_sentence_is_not_cut_and_cancellation_propagates(native_source):
    builder, words = builder_for(native_source)
    entry = (native_source[3], native_source[2], words, 0)

    class LimitedWorker:
        startup: ClassVar = {}

        def infer(self, request, **kwargs):
            assert request["sentences"] == [[t["text"] for t in words]]
            if False:
                yield ()
            return dict(
                outcome="prepared_batch",
                members=[dict(ordinal=0, outcome="limited", reason="sentence_subwords", limit=512)],
            )

    from corpus_structure.core.method import drive_prepared_work

    drive_prepared_work(
        _batch_sentences(LimitedWorker(), [entry], builder, lambda: None), lambda: None
    )
    assert all(builder.covered[family][0][1] == "unsupported" for family in HANLP_FAMILIES)

    class Cancelled(Exception):
        pass

    def cancel():
        raise Cancelled("fixture task lease lost")

    with pytest.raises(Cancelled, match="lease lost"):
        drive_prepared_work(_batch_sentences(LimitedWorker(), [entry], builder, cancel), cancel)


@pytest.mark.parametrize("producer_name", ("native", "formal", "construction"))
def test_explicit_primary_scope_keeps_context_only_source_and_exact_base(
    native_source, producer_name
):
    from corpus_structure.methods.construction_characterization import (
        ConstructionCharacterizationMethod,
    )
    from corpus_structure.methods.formal_evidence import FormalEvidenceMethod

    _, _, _, view, base, scope, _ = native_source
    from pydantic import BaseModel

    from corpus_structure.core.method import Method

    def verify[C: BaseModel](selected: Method[C]):
        cfg = selected.Config(
            characterization_base_document=base,
            characterization_source_scope=scope,
        )
        # Domain-analysis enumeration omits this retained context view; the
        # exact-reference port authenticates its original selected identity.
        reader = SimpleNamespace(
            source_views=lambda: (), source_view_ref={view.ref.id: view.ref}.__getitem__
        )
        run = SimpleNamespace(reader=reader)
        assert tuple(selected.select(run, cfg)) == (UnitRef(TaskUnitType.DOCUMENT, 17),)
        wrong_base = cfg.model_copy(
            update={"characterization_base_document": dict(base, content_digest="f" * 64)}
        )
        with pytest.raises(ValueError, match=r"(base|selected document)"):
            tuple(selected.select(run, wrong_base))

    if producer_name == "native":
        verify(NativeEvidenceMethod())
    elif producer_name == "formal":
        verify(FormalEvidenceMethod())
    else:
        verify(ConstructionCharacterizationMethod())


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
