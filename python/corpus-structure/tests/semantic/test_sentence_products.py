"""Original-source geometry, actual CUDA spaCy, and retained sentence consumer controls."""

import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic import (
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    SentenceSourceReadings,
    prepare_sentence_profile,
    sentence_operation_sources,
    sentence_product_inputs,
    validate_sentence_inventory,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, native_projection_identity


@pytest.fixture(scope="module")
def profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = sentence_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(bundle)
    model = compile_data_operations(
        schema=bundle,
        python_sources=sentence_operation_sources(),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return prepare_sentence_profile(prepared, model)


def selected(profile, text="The mean is 2. The variance is 4."):
    pieces = (
        [
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ]
        if text
        else []
    )
    items = (
        [dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])]
        if text
        else []
    )
    projection = native_projection_identity(text, pieces, items, [])
    return FrozenNativeSource.acquire(
        profile.prepared,
        dict(
            source=dict(
                document="document:" + sha256(text.encode()).hexdigest(),
                section_pointer="#/groups/0",
                membership="descendants",
                projection=projection,
            ),
            text=text,
            pieces=pieces,
            items=items,
            recognition=[],
            selectors=[
                dict(projection=projection, **(dict(native_pointer="#/texts/0") if text else {}))
            ],
        ),
    )


def test_original_source_identity_excludes_legacy_task_recipe_and_diagnostic_salts(profile):
    text = "Original text."
    views = []
    for number in (1, 2):
        view = SimpleNamespace(
            ref=SimpleNamespace(
                section_pointer="#/groups/0",
                membership="descendants",
                projection_digest=str(number) * 64,
                recipe_digest=str(number + 2) * 64,
            ),
            text=text,
            pieces=[
                dict(
                    kind="native_text",
                    start=0,
                    end=len(text),
                    item_ref="#/texts/0",
                    source_field="text",
                )
            ],
            items=[
                dict(
                    self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)]
                )
            ],
            health={"formula_outcomes": [], "diagnostic_ref": {"task_id": number}},
        )
        views.append(
            FrozenNativeSource.from_source_view(
                profile.prepared,
                view,
                document="document:one",
                selectors=[dict(projection=str(number) * 64, native_pointer="#/texts/0")],
            )
        )
    assert views[0].content == views[1].content
    assert b"task_id" not in views[0].content and b"recipe_digest" not in views[0].content
    changed = views[0].value
    changed["text"] = "Forged content."
    with pytest.raises(ValueError, match=r"source meaning|exceed|partition"):
        FrozenNativeSource.acquire(profile.prepared, changed)


def test_empty_and_partial_block_scope_never_invent_canonical_sentences(profile, monkeypatch):
    monkeypatch.setattr(
        "corpus_structure.semantic.sentence_products.pipeline",
        lambda *_: pytest.fail("unexamined/empty scope invoked a model"),
    )
    empty = profile.run(selected(profile, ""))
    assert empty.inventory("sentence") == () and empty.value.outcome == "complete"
    source = selected(profile)
    value = source.value
    value["selectors"][0]["start"] = 4
    partial = profile.run(FrozenNativeSource.acquire(profile.prepared, value))
    assert partial.inventory("sentence") == () and partial.value.outcome == "partial"
    assert partial.value.coverage[0].outcome == "unsupported"


@pytest.fixture(scope="module")
def gpu_host():
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.methods.native_host import NativeHostGroup
    from corpus_structure.settings import NemotronSettings

    with NativeHostGroup(CharacterizationExecutionPolicy(), NemotronSettings().endpoint) as host:
        yield host


@pytest.mark.gpu
@pytest.mark.parametrize(
    "text", ["The mean is 2. The variance is 4.", "A valve opens. Pressure falls."]
)
def test_actual_cuda_spacy_preserves_original_sentence_token_inventory(
    profile, text, monkeypatch, gpu_host
):
    source = selected(profile, text)
    product = profile.run(source, host=gpu_host)
    sentences = product.inventory("sentence")
    assert [text[row["start"] : row["end"]] for row in sentences] == [
        part.strip() + "." for part in text.split(".") if part.strip()
    ]
    assert product.value.outcome == "complete"
    from corpus_structure.semantic.canonical_sentences import canonical_sentence_values

    complete = json.loads(product.content)
    canonical = canonical_sentence_values(complete)
    relabeled = json.loads(product.content)
    for packet in relabeled["members"]:
        if packet["body"]["record_type"] == "token":
            packet["body"]["lemma"] = "another-native-label"
    assert canonical_sentence_values(relabeled) == canonical
    assert canonical_bytes(relabeled) != product.content
    profile.prepared.validate_json("DdoCanonicalSentences", canonical_bytes(canonical))
    original_tokens = product.inventory("token")
    assert all(
        {"lemma", "pos", "tag", "morphology", "dependency"} <= token.keys()
        for token in original_tokens
    )
    assert all(token.get("head_ref") for token in original_tokens if token["dependency"])
    assert any(token["lemma"] for token in original_tokens)
    assert all(
        row["attributes"]["DEP"] == "complete"
        for row in json.loads(product.content)["annotation_columns"]
    )
    assert all(
        set(packet) == {"member_id", "kind_contract", "context", "body"}
        for packet in json.loads(product.content)["members"]
    )
    assert product.execution_receipts
    receipts = [json.loads(receipt) for receipt in product.execution_receipts]
    assert all(
        receipt["provider"] == "spacy" and receipt["input_digest"] and receipt["output_digest"]
        for receipt in receipts
    )
    assert b"runtime" not in product.content and b"task_id" not in product.content
    monkeypatch.setattr(
        "corpus_structure.semantic.sentence_products.pipeline",
        lambda *_: pytest.fail("sentence reader reran NLP"),
    )
    reader = SentenceSourceReadings(product, source)
    assert reader.sentences() == sentences
    assert reader.annotation_availability()
    assert all(
        row["start"] == 0 and row["end"] == len(text) for row in reader.annotation_availability()
    )
    assert all("sent_start" in token for token in original_tokens)
    assert product.semantic_id.startswith("product:")
    assert reader.native_annotations(sentences[0]["local_id"]) == reader.tokens(
        sentences[0]["local_id"]
    )
    for sentence in sentences:
        tokens = reader.tokens(sentence["local_id"])
        assert all(token["sentence_ref"] == sentence["local_id"] for token in tokens)
        assert all(text[token["start"] : token["end"]] for token in tokens)
        assert all(token["piece_indices"] == [0] for token in tokens)
    changed = json.loads(product.content)
    changed["members"][0]["body"]["start"] += 1
    with pytest.raises(ValueError, match=r"member identity|coordinates"):
        validate_sentence_inventory(profile.prepared, profile.model, changed, source)


def test_original_declared_sentence_capability_is_captured(profile):
    operation = profile.model.operation("segment.sentences/source-native")
    assert operation.outcomes == ("success", "failed")
    assert operation.capabilities.preparation == "resource"
    assert operation.capabilities.cancellation == "cooperative"
    assert operation.roles[0].kind.endswith("/DdoSelectedNativeSource")
    assert operation.roles[1].kind.endswith("/DdoSentenceInventory")
    assert operation.callable_surfaces[0].declaration.endswith("SentenceEvidenceOperation.run")
    assert all(implementation.complete for implementation in profile.model.implementation_slices)


def admitted_port(profile):
    from dataclasses import asdict

    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.sentence_products import resolve_sentence_port

    operation = profile.model.operation("segment.sentences/source-native")
    ids = {(identity.owner, identity.domain): identity.key for identity in profile.model.identities}
    sources = sentence_operation_sources()
    boundaries = (
        *operation.assets,
        *(
            boundary
            for implementation in profile.model.implementation_slices
            if implementation.root == operation.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    identity = PreparedCapabilityIdentity(
        sha256(profile.model.content).hexdigest(),
        operation.semantic_id,
        ids[operation.semantic_id, "definition"],
        ids[operation.semantic_id, "recipe"],
        ids[operation.implementation_root, "implementation-slice"],
        "corpus_structure.methods.sentence_evidence.SentenceEvidenceOperation.run",
        sha256(
            canonical_bytes(
                tuple(
                    (source.module, sha256(source.content).hexdigest())
                    for source in sources.sources
                )
            )
        ).hexdigest(),
        canonical_bytes(asdict(operation.capabilities)),
        ids[operation.semantic_id, "eligibility"],
        "runtime:explicit-test",
        canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )
    return resolve_sentence_port(
        profile.prepared,
        profile.model,
        operation.semantic_id,
        identity=identity,
        authorize=lambda acquired: None,
        custody=sources.boundary_contracts,
    )


def test_admitted_prepared_sentence_port_emits_typed_empty_inventory_and_refuses_diversion(
    profile, monkeypatch
):
    from corpus_structure.methods.sentence_evidence import SentenceEvidenceOperation
    from corpus_structure.semantic.data_operation_ports import PortRefusal, PythonRoleValue

    port = admitted_port(profile)
    source = selected(profile, "")
    kind = next(
        identity.key
        for identity in profile.model.identities
        if identity.owner == port.operation.roles[0].kind and identity.domain == "kind"
    )
    value = PythonRoleValue("source", kind, source)
    completion = port.invoke_python((value,))
    assert completion.operation == "segment.sentences/source-native"
    assert completion.execution_evidence is not None
    assert json.loads(completion.execution_evidence) == []
    assert json.loads(completion.outputs[0].content)["members"] == []
    with pytest.raises(PortRefusal, match="nominal"):
        port.invoke_python((PythonRoleValue("source", "another-kind", source),))
    monkeypatch.setattr(SentenceEvidenceOperation, "run", lambda *_: None)
    with pytest.raises(PortRefusal, match="loaded sentence endpoint"):
        port.invoke_python((value,))


def test_sentence_members_derive_from_actual_nominal_body_graph(profile):
    from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds

    container = profile.prepared.index.definitions["DdoSentenceInventory"].iri
    expected = {
        profile.prepared.index.definitions[name].iri
        for name in ("DdoNativeToken", "DdoNativeSentence")
    }
    assert set(derive_member_kinds(profile.model, container)) == expected


def test_declared_canonical_projection_stops_native_label_only_changes(profile):
    from corpus_structure.semantic.canonical_sentences import canonical_sentence_operation_sources
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue, resolve_python_port

    bundle = sentence_product_inputs(
        SourceBundle(
            "core",
            (
                SourceArtifact(
                    "core",
                    (
                        Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
                    ).read_bytes(),
                ),
            ),
        )
    )
    sources = canonical_sentence_operation_sources()
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        definitions=profile.prepared.definitions,
        vocabularies=profile.prepared.vocabularies,
    )
    operation = model.operation("segment.sentences/canonical-projection")
    port = resolve_python_port(
        model,
        sources,
        operation.semantic_id,
        schema=bundle,
        prepared=profile.prepared,
        authorize=lambda _: None,
    )
    source = selected(profile, "")
    value = json.loads(profile.run(source).content)
    kind = next(
        identity.key
        for identity in model.identities
        if identity.owner == operation.roles[0].kind and identity.domain == "kind"
    )
    result = port.invoke_python((PythonRoleValue("inventory", kind, value),))
    expected = {key: value[key] for key in ("source", "selectors", "outcome", "coverage")}
    expected["sentences"] = []
    assert json.loads(result.outputs[0].content) == expected
    profile.prepared.validate_json("DdoCanonicalSentences", result.outputs[0].content)


def test_prepared_sentence_plan_uses_invocation_work_and_host_owner(profile):
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

    port = admitted_port(profile)
    source = selected(profile, "")
    kind = next(
        identity.key
        for identity in profile.model.identities
        if identity.owner == port.operation.roles[0].kind and identity.domain == "kind"
    )
    pending = []
    owner = SimpleNamespace(
        native_hosts=object(), submit_python=lambda callback: pending.append(callback)
    )
    plan = port.plan_python((PythonRoleValue("source", kind, source),), execution_owner=owner)
    (work,) = next(plan)
    work.try_submit()
    assert len(pending) == 1
    result = pending[0]()
    with pytest.raises(StopIteration) as complete:
        plan.send((result,))
    assert complete.value.value is result
    assert port.native_selections[0].native.provider == "spacy"


def test_native_inventory_keeps_original_synthetic_piece_and_block_whitespace():
    import spacy

    from corpus_structure.ingest.sentences import Block, make_doc, prepare_layout
    from corpus_structure.semantic.sentence_products import _Block, _native_records

    nlp = spacy.blank("en")
    text = "A  B."
    original = Block(text, (), (), ())
    layout = prepare_layout(nlp, original, start=7)
    doc = make_doc(nlp, original, layout, start=7)
    for token in doc:
        token.is_sent_start = token.i == 0
    source = dict(
        source=dict(
            document="original", section_pointer="#/g", membership="direct", projection="a" * 64
        ),
        pieces=[dict(start=7, end=8), dict(start=8, end=10), dict(start=10, end=12)],
    )
    records, standing = _native_records(
        source, _Block("block", 7, 12, original, (0, 2)), layout, doc
    )
    assert standing["start"] == 7 and standing["end"] == 12
    tokens = [body for kind, body in records if kind == "token"]
    assert any(1 in token["piece_indices"] for token in tokens)
    assert all(
        token["piece_indices"]
        == [
            index
            for index, piece in enumerate(source["pieces"])
            if piece["start"] < token["end"] and token["start"] < piece["end"]
        ]
        for token in tokens
    )
    assert standing["attributes"]["LEMMA"] == "absent"
