"""Original-source geometry, actual CUDA spaCy, and retained sentence consumer controls."""

import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
import spacy
from corpus_structure.ingest.sentences import SentenceConfig

from corpus_structure.semantic import (
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    SourceAnnotationReadings,
    prepare_sentence_profile,
    sentence_operation_sources,
    sentence_product_inputs,
    validate_source_annotations,
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
    from corpus_structure.semantic.original_documents import original_document_subject
    projection = native_projection_identity(text, pieces, items, [])
    return FrozenNativeSource.acquire(
        profile.prepared,
        dict(
            source=dict(
                document="document:" + sha256(text.encode()).hexdigest(),
                document_subject=original_document_subject("document:" + sha256(text.encode()).hexdigest()),
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
            ancestors=[],
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
    empty = profile.run(
        selected(profile, ""), subject_context=_publication_context(selected(profile, ""))
    )
    assert empty.inventory("sentence") == () and empty.value.outcome == "complete"
    source = selected(profile)
    value = source.value
    value["selectors"][0]["start"] = 4
    partial = profile.run(
        FrozenNativeSource.acquire(profile.prepared, value),
        subject_context=_publication_context(FrozenNativeSource.acquire(profile.prepared, value)),
    )
    assert partial.inventory("sentence") == () and partial.value.outcome == "partial"
    assert partial.value.block_coverage[0].outcome == "unsupported"


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
    product = profile.run(source, host=gpu_host, subject_context=_publication_context(source), source_pin=_controlled_source_pin(source))
    sentences = product.inventory("sentence")
    assert [text[row["start"] : row["end"]] for row in sentences] == [
        part.strip() + "." for part in text.split(".") if part.strip()
    ]
    assert product.value.outcome == "complete"
    from corpus_structure.semantic.canonical_sentences import (
        canonical_packet_values,
        canonical_projection_spec,
    )

    complete = json.loads(product.content)
    canonical_kind = profile.prepared.index.definitions["DdoCanonicalSentences"].iri
    projection = canonical_projection_spec(profile.model, canonical_kind)
    canonical = canonical_packet_values(complete, projection)
    relabeled = json.loads(product.content)
    for block in relabeled["blocks"]:
        for token in block["annotation"]["tokens"]:
            token["lemma"] = "another-native-label"
    assert canonical_packet_values(relabeled, projection) == canonical
    assert canonical_bytes(relabeled) != product.content
    profile.prepared.validate_json("DdoCanonicalSentences", canonical_bytes(canonical))
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

    port = canonical_port(profile)
    input_kind = next(
        item.key
        for item in port.profile.model.identities
        if item.owner == port.operation.roles[0].kind and item.domain == "kind"
    )
    completion = port.invoke_python((PythonRoleValue("inventory", input_kind, complete),))
    assert len(completion.outputs[0].members) == len(canonical["members"])
    native_contracts = {packet["kind_contract"] for packet in complete["members"]}
    assert all(
        json.loads(member)["kind_contract"] not in native_contracts
        for member in completion.outputs[0].members
    )
    original_tokens = product.inventory("token")
    assert all(
        {
            "lemma",
            "pos",
            "tag",
            "morphology",
            "dependency",
            "lower",
            "is_alpha",
            "is_space",
            "is_punct",
            "is_quote",
            "like_num",
        }
        <= token.keys()
        for token in original_tokens
    )
    assert all(
        token["lower"] == text[token["start"] : token["end"]].lower() for token in original_tokens
    )
    assert all(
        token["is_alpha"] == text[token["start"] : token["end"]].isalpha()
        for token in original_tokens
    )
    assert all(
        "lower" not in packet["body"] and "is_alpha" not in packet["body"]
        for packet in canonical["members"]
    )
    assert all(token.get("head_ref") for token in original_tokens if token["dependency"])
    assert any(token["lemma"] for token in original_tokens)
    assert all(
        next(column["status"] for column in row["annotation"]["availability"] if column["attribute"] == "DEP") == "complete"
        for row in json.loads(product.content)["blocks"]
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
    reader = SourceAnnotationReadings(product, source)
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
    changed["blocks"][0]["annotation"]["tokens"][0]["start"] = -1
    with pytest.raises(ValueError):
        validate_source_annotations(profile.prepared, profile.model, changed, source)


def test_original_declared_sentence_capability_is_captured(profile):
    operation = profile.model.operation("segment.sentences/source-native")
    assert operation.outcomes == ("success", "failed")
    assert operation.capabilities.preparation == "resource"
    assert operation.capabilities.cancellation == "cooperative"
    assert operation.roles[0].kind.endswith("/DdoSelectedNativeSource")
    assert operation.roles[1].kind.endswith("/DdoSourceAnnotations")
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
    assert len(json.loads(completion.outputs[0].content)["members"]) == 1
    assert json.loads(completion.outputs[0].content)["blocks"] == []
    with pytest.raises(PortRefusal, match="nominal"):
        port.invoke_python((PythonRoleValue("source", "another-kind", source),))
    monkeypatch.setattr(SentenceEvidenceOperation, "run", lambda *_: None)
    with pytest.raises(PortRefusal, match="loaded sentence endpoint"):
        port.invoke_python((value,))


def test_sentence_members_derive_from_actual_nominal_body_graph(profile):
    from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds

    container = profile.prepared.index.definitions["DdoSourceAnnotations"].iri
    expected = {
        profile.prepared.index.definitions[name].iri
        for name in ("DdoSourceAnnotationManifest",)
    }
    assert set(derive_member_kinds(profile.model, container)) == expected


def canonical_port(profile, extra_sources=()):
    from dataclasses import asdict, replace

    from corpus_structure.semantic.canonical_sentences import (
        canonical_sentence_operation_sources,
        resolve_canonical_sentence_port,
    )
    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = sentence_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    own_sources = canonical_sentence_operation_sources()
    sources = replace(own_sources, sources=(*own_sources.sources, *extra_sources))
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        definitions=profile.prepared.definitions,
        vocabularies=profile.prepared.vocabularies,
    )
    operation = model.operation("segment.sentences/canonical-projection")
    assert operation.implementation_root is not None
    ids = {(item.owner, item.domain): item.key for item in model.identities}
    boundaries = (
        *operation.assets,
        *(
            boundary
            for impl in model.implementation_slices
            if impl.root == operation.implementation_root
            for boundary in impl.boundaries
        ),
    )
    identity = PreparedCapabilityIdentity(
        sha256(model.content).hexdigest(),
        operation.semantic_id,
        ids[operation.semantic_id, "definition"],
        ids[operation.semantic_id, "recipe"],
        ids[operation.implementation_root, "implementation-slice"],
        operation.callable_surfaces[0].declaration,
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
        "runtime:test",
        canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )
    return resolve_canonical_sentence_port(
        profile.prepared,
        model,
        operation.semantic_id,
        identity=identity,
        authorize=lambda _: None,
        custody=sources.boundary_contracts,
        sources=sources,
    )


def test_declared_canonical_projection_has_actual_independent_member_contracts(profile):
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

    port = canonical_port(profile)
    inventory = json.loads(
        profile.run(
            selected(profile, ""), subject_context=_publication_context(selected(profile, ""))
        ).content
    )
    kind = next(
        item.key
        for item in port.profile.model.identities
        if item.owner == port.operation.roles[0].kind and item.domain == "kind"
    )
    result = port.invoke_python((PythonRoleValue("inventory", kind, inventory),))
    value = json.loads(result.outputs[0].content)
    assert value["members"] == [] and result.outputs[0].members == ()
    assert {row["family"] for row in value["coverage"]} == {"spacy.tokens", "spacy.sentences"}
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


def test_native_inventory_keeps_original_synthetic_piece_and_block_whitespace(monkeypatch):
    from corpus_structure.ingest import annotations
    from corpus_structure.ingest.sentences import Block, make_doc, prepare_layout
    from corpus_structure.semantic.declared_record_sources import DeclaredSourcePin
    from corpus_structure.semantic.sentence_products import _Block, _detach_annotation_block, source_annotation_member_values
    nlp = spacy.blank("en")
    monkeypatch.setattr(annotations, "pipeline", lambda _: nlp)
    text = "A  B."
    original = Block(text, (), (), ())
    layout = prepare_layout(nlp, original, start=7)
    doc = make_doc(nlp, original, layout, start=7)
    for token in doc:
        token.is_sent_start = token.i == 0
    source = dict(source=dict(document="original", section_pointer="#/g", membership="direct", projection="a" * 64),
        items=[], pieces=[dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=7, end=8),
                         dict(kind="synthetic_separator", start=8, end=10),
                         dict(kind="native_text", item_ref="#/texts/1", source_field="text", start=10, end=12)])
    block = _detach_annotation_block(source, _Block("block", 7, 12, original, (0, 1, 2)), layout, doc,
                                    DeclaredSourcePin("{}"), SentenceConfig(exclude=("ner",)), "controlled-profile")
    records = source_annotation_member_values({"source": source["source"], "blocks": [block]})
    tokens = [body for body in records if body["record_type"] == "token"]
    assert any(1 in token["piece_indices"] for token in tokens)
    assert all(token["piece_indices"] == [index for index, piece in enumerate(source["pieces"])
        if piece["start"] < token["end"] and token["start"] < piece["end"]] for token in tokens)
    assert {row["attribute"]: row["status"] for row in block["annotation"]["availability"]}["LEMMA"] == "absent"


def test_flat_original_formula_parent_preserves_protected_inline_atom(profile):
    from corpus_structure.semantic.sentence_products import _blocks

    value = selected(profile, "Let x = 2.").value
    value["items"] = [
        dict(self_ref="#/texts/0", label="text", text="Let x = 2.", orig="Let x = 2."),
        dict(self_ref="#/groups/inline", label="inline", parent="#/texts/0"),
        dict(
            self_ref="#/texts/formula",
            label="formula",
            text="x",
            orig="x",
            parent="#/groups/inline",
        ),
    ]
    value["pieces"] = [
        dict(kind="native_text", start=0, end=4, item_ref="#/texts/0", source_field="text"),
        dict(kind="native_text", start=4, end=5, item_ref="#/texts/formula", source_field="text"),
        dict(kind="native_text", start=5, end=10, item_ref="#/texts/0", source_field="text"),
    ]
    projection = native_projection_identity(value["text"], value["pieces"], value["items"], [])
    value["source"]["projection"] = projection
    value["selectors"][0]["projection"] = projection
    source = FrozenNativeSource.acquire(profile.prepared, value)
    (block,), coverage = _blocks(source)
    assert block.block.inline == ((4, 5),) and block.block.display == ()
    assert block.block_id == "#/texts/0"
    assert coverage == [
        dict(block_id="#/texts/0", native_pointer="#/texts/0", start=0, end=10, outcome="complete")
    ]
    assert source.value["items"][2]["parent"] == "#/groups/inline"


def test_canonical_prepared_kernel_runs_in_actual_shared_cpu_scope(profile):
    import os

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

    port = canonical_port(profile)
    inventory = json.loads(
        profile.run(
            selected(profile, ""), subject_context=_publication_context(selected(profile, ""))
        ).content
    )
    kind = next(
        item.key
        for item in port.profile.model.identities
        if item.owner == port.operation.roles[0].kind and item.domain == "kind"
    )
    cpu = CPUExecutionScope(
        profile.prepared,
        CharacterizationExecutionPolicy(workers=1, max_submissions=1),
        retain_schema=False,
    )
    try:
        result = drive_prepared_work(
            port.plan_python(
                (PythonRoleValue("inventory", kind, inventory),),
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
            ),
            lambda: None,
        )
        evidence = json.loads(result.cpu_execution_evidence)
        assert evidence["pid"] != os.getpid() and evidence["main_thread"] is True
        assert cpu._capsule_bytes == 0
        assert json.loads(result.outputs[0].content)["members"] == []
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_prepared_canonical_full_source_digest_accepts_authenticated_required_subset(
    profile, tmp_path
):
    from corpus_structure.semantic.python_operation_sources import PythonSource

    path = tmp_path / "extra_original.py"
    path.write_text("PASSIVE = 1\n")
    port = canonical_port(profile, (PythonSource("extra_original", path.read_bytes(), str(path)),))
    assert len(port.sources.sources) == 2
    port._verify()


def test_unprojected_requested_native_text_is_unknown_instead_of_empty_language(
    profile, monkeypatch
):
    value = selected(profile, "").value
    value["items"] = [dict(self_ref="#/texts/raw", label="formula", text="", orig="x + 1")]
    projection = native_projection_identity("", [], value["items"], [])
    value["source"]["projection"] = projection
    value["selectors"][0]["projection"] = projection
    monkeypatch.setattr(
        "corpus_structure.semantic.sentence_products.pipeline",
        lambda *_: pytest.fail("unprojected source invoked NLP"),
    )
    result = profile.run(
        FrozenNativeSource.acquire(profile.prepared, value),
        subject_context=_publication_context(FrozenNativeSource.acquire(profile.prepared, value)),
    )
    assert result.value.outcome == "partial" and result.inventory("token") == ()
    assert all(row.outcome == "unsupported" and row.unexamined for row in result.value.coverage)


def _publication_context(source, *, document=False):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject

    value = source.value
    return SubjectContext(
        "family-test",
        value["source"]["document"] if document else source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
    )


def _controlled_source_pin(source):
    """Controlled input identity for provider checks; no native original-custody claim."""
    from corpus_structure.semantic.data_operation_model import BoundRoleMember
    from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource, DeclaredSourcePin
    context = _publication_context(source)
    member = BoundRoleMember("controlled-original", "controlled-kind", context.subject,
        context.original_source, context.analyzed_scope, b"{}", (), b"{}")
    return DeclaredSourcePin(canonical_bytes(DeclaredRecordSource.from_bound(source, member,
        project=context.project_id).pin()).decode())
