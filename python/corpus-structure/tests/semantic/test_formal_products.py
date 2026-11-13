"""Actual positioned parser controls for source-native formal products."""

from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    FrozenFormalSource,
    formal_product_inputs,
    prepare_formal_evidence,
)


@pytest.fixture(scope="module")
def profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    prepared = prepare_release(bundle, data_operation_dependencies(ResolvedDependencies(), python_sources=formal_operation_sources()), PreparationProfile(version="semantic-2"))
    return prepare_formal_evidence(prepared, bound_data_operation_model(prepared), grammar=grammar_identity())


def selected(profile, text="Quantity: 2 kg\nusing the equation x = 2.", **changes):
    value = dict(
        source=dict(document="document:original-content", section_pointer="#/groups/0", membership="descendants", projection="b" * 64),
        text=text,
        pieces=[dict(kind="native_text", start=0, end=len(text), item_ref="#/texts/0", source_field="text")],
        items=[dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])],
        recognition=[],
        selectors=[dict(projection="b" * 64, native_pointer="#/texts/0", start=0, end=len(text))],
        **changes,
    )
    return acquire_source(profile, value)



def acquire_source(profile, value):
    from corpus_structure.semantic.source_products import native_projection_identity

    projection = native_projection_identity(value["text"], value["pieces"], value["items"], value.get("recognition", ()))
    value["source"]["projection"] = projection
    for selector in value["selectors"]:
        selector["projection"] = projection
    return FrozenFormalSource.acquire(profile.prepared, value)

def test_actual_formal_product_retains_positioned_rules_symbols_terms_and_witnesses(profile):
    source = selected(profile)
    product = profile.run(source, FormalEvidenceOptions())
    body = product.inventory()
    assert {row["kind"] for row in body["annotations"]} >= {"formal.input", "formal.rule", "formal.token", "formal.symbol"}
    assert any(row["kind"] == "operator" for row in body["terms"])
    assert all(row["extents"][0]["projection"] == source.value["source"]["projection"] for row in body["occurrences"])
    assert all("source_view_id" not in extent for row in body["occurrences"] for extent in row["extents"])
    assert all(member.member_id and member.kind.startswith("https://") for member in product.members)
    assert product.value.source.document == "document:original-content"
    assert [row.family for row in product.value.coverage] == ["formal.lexical", "formal.number", "formal.threshold", "formal.date", "formal.identifier", "formal.quantity", "formal.interval", "formal.math"]


def test_formal_semantics_do_not_depend_on_execution_limits_or_receipt_placement(profile):
    source = selected(profile, "Quantity: 2 kg")
    left = profile.run(source, FormalEvidenceOptions(parse_seconds=2, max_forest_nodes=20000))
    right = profile.run(source, FormalEvidenceOptions(parse_seconds=3, max_forest_nodes=30000, max_inline_chars=4096))
    assert left.content == right.content
    assert left.semantic_id == right.semantic_id
    assert b"release_id" not in left.content and b"task_id" not in left.content
    assert b"configuration" not in left.content and b"runtime" not in left.content


def test_formal_source_identity_and_exact_scope_change_meaning(profile):
    full = selected(profile, "Quantity: 2 kg")
    changed = full.value
    changed["source"]["document"] = "document:another-original"
    other = FrozenFormalSource.acquire(profile.prepared, changed)
    first = profile.run(full, FormalEvidenceOptions())
    second = profile.run(other, FormalEvidenceOptions())
    assert {m.member_id for m in first.members}.isdisjoint({m.member_id for m in second.members})
    scoped = full.value
    scoped["selectors"][0]["end"] = 8
    result = profile.run(FrozenFormalSource.acquire(profile.prepared, scoped), FormalEvidenceOptions())
    assert all(extent.get("end", 0) <= 8 for row in result.inventory()["occurrences"] for extent in row["extents"])
    assert result.value.selectors[0].end == 8


def test_selected_source_is_detached_and_refuses_forged_coordinates(profile):
    original = selected(profile, "x ≥ 2")
    changed = original.value
    changed["items"][0]["text"] = "caller mutation"
    assert original.value["items"][0]["text"] == "x ≥ 2"
    changed = original.value
    changed["selectors"][0]["projection"] = "c" * 64
    with pytest.raises(ValueError, match="another projection"):
        FrozenFormalSource.acquire(profile.prepared, changed)
    changed = original.value
    changed["pieces"][0]["item_ref"] = "#/missing"
    with pytest.raises(ValueError, match="original atom"):
        FrozenFormalSource.acquire(profile.prepared, changed)


def test_unprojected_recognized_formula_preserves_atom_and_unknown_correspondence(profile):
    value = dict(source=dict(document="document:original-content", section_pointer="#/groups/0", membership="descendants", projection="b" * 64), text="", pieces=[], items=[dict(self_ref="#/texts/0", label="formula", text="x+1", orig="", prov=[dict(page_no=1)])], recognition=[dict(pointer="#/texts/0", outcome="succeeded")], selectors=[dict(projection="b" * 64, native_pointer="#/texts/0")])
    product = profile.run(acquire_source(profile, value), FormalEvidenceOptions())
    inputs = [row["formal_input"] for row in product.inventory()["annotations"] if "formal_input" in row]
    assert inputs[0]["representation"] == "recognized_latex"
    assert inputs[0]["correspondence"][0]["relation"] == "contained_in_atom"
    assert product.value.outcome == "partial"
    assert all("start" not in extent for row in product.inventory()["occurrences"] for extent in row["extents"])


def test_cooperative_cancellation_prevents_complete_product(profile):
    def cancel():
        raise RuntimeError("cancelled original request")
    with pytest.raises(RuntimeError, match="cancelled original request"):
        profile.run(selected(profile), FormalEvidenceOptions(), check_active=cancel)


def test_immediate_construction_boundary_reuses_formal_facts_without_parser(profile, monkeypatch):
    from corpus_structure.semantic import formal_evidence
    from corpus_structure.semantic.formal_readings import FormalSourceReadings, SemanticFormalReference

    source = selected(profile, "Quantity: 2 kg")
    product = profile.run(source, FormalEvidenceOptions())
    monkeypatch.setattr(formal_evidence, "formal_field_grammar", lambda *_: pytest.fail("consumer reparsed formal text"))
    boundary = FormalSourceReadings.from_products((product,), source)
    fields, complete = boundary.fields(family="formal.quantity", start=0, end=len(source.value["text"]))
    assert complete and len(fields) == 1
    assert fields[0].normalized["value"] == "2"
    assert fields[0].normalized["unit"] == "kg"
    assert isinstance(fields[0].reference, SemanticFormalReference)
    assert fields[0].reference.layer.product == product.semantic_id
    changed = source.value
    changed["source"]["document"] = "another-original"
    with pytest.raises(ValueError, match="another original source"):
        FormalSourceReadings.from_products((product,), FrozenFormalSource.acquire(profile.prepared, changed))


def test_captured_formal_source_profile_declares_real_nominal_products_and_assets(profile):
    from corpus_structure.semantic.formal_products import formal_operation_sources, formal_product_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    model = compile_data_operations(schema=bundle, python_sources=formal_operation_sources())
    operation = model.operation("text.formal_evidence/source-native")
    assert operation.capabilities.preparation == "resource"
    assert operation.assets[0].content_digest == formal_operation_sources().boundary_contracts[0].digest
    assert operation.callable_surfaces[0].declaration.endswith("FormalEvidenceOperation.run")
    assert model.implementation_slices[0].complete


def admitted_port(profile):
    from dataclasses import asdict
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.formal_products import formal_operation_sources, resolve_formal_evidence_port
    from corpus_structure.semantic.identity import canonical_bytes

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    sources = formal_operation_sources()
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.types import ResolvedDependencies
    from corpus_structure.semantic.types import PreparationProfile
    prepared = prepare_release(bundle, data_operation_dependencies(ResolvedDependencies(), python_sources=sources), PreparationProfile(version="semantic-2"))
    model = bound_data_operation_model(prepared)
    operation = model.operation("text.formal_evidence/source-native")
    ids = {(item.owner, item.domain): item.key for item in model.identities}
    assert operation.implementation_root is not None
    boundaries = (*operation.assets, *model.implementation_slices[0].boundaries)
    identity = PreparedCapabilityIdentity(
        sha256(model.content).hexdigest(), operation.semantic_id,
        ids[operation.semantic_id, "definition"], ids[operation.semantic_id, "recipe"],
        ids[operation.implementation_root, "implementation-slice"], operation.callable_surfaces[0].declaration,
        sha256(canonical_bytes(tuple((s.module, sha256(s.content).hexdigest()) for s in sources.sources))).hexdigest(),
        canonical_bytes(asdict(operation.capabilities)), ids[operation.semantic_id, "eligibility"],
        "runtime:controlled-profile", canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )
    def authorize(actual):
        if actual != identity:
            raise ValueError("not the controlled acquired identity")
    return resolve_formal_evidence_port(prepared, model, operation.semantic_id, identity=identity, authorize=authorize, custody=sources.boundary_contracts)


def test_original_prepared_entrypoint_emits_typed_body_and_native_members(profile):
    import json

    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    port = admitted_port(profile)
    source = selected(profile, "Quantity: 2 kg")
    role = next(role for role in port.operation.roles if role.direction == "input")
    contract = next(i.key for i in port.profile.model.identities if (i.owner, i.domain) == (role.kind, "kind"))
    completion = port.invoke_python((PythonRoleValue("source", contract, source.value),))
    output, = completion.outputs
    assert output.meaning is not None
    assert decode_semantic_value(json.loads(output.meaning))["source"]["document"] == "document:original-content"
    assert output.members
    native = [json.loads(packet) for packet in output.members]
    assert all(packet["context"]["original_source"] == "document:original-content" for packet in native)
    assert all(set(packet) == {"member_id", "kind_contract", "context", "body"} for packet in native)
    # Exercise the actual native completion wire, without pretending this controlled
    # private calculation is a live native publication or provider qualification.
    payload = dict(request_id="request:formal", generation=1, task_id=1, attempt=1, holder="worker", runtime_id=port.identity.runtime, completion=dict(outcome="addressed", implementation_revision=port.identity.implementation, inputs=[], support=[], outputs=[dict(role="result", position=0, multiplicity=1, product=dict(kind_contract=output.kind_contract, body=json.loads(output.meaning), members=native))]))
    assert validate_native_wire("retain_data_completion_intent", "input", payload)["completion"]["outputs"][0]["product"]["members"] == native


def test_prepared_formal_profile_rejects_changed_source_assets_and_nominal_input(profile, monkeypatch):
    from corpus_structure.semantic import formal_products
    from corpus_structure.semantic.data_operation_ports import PortRefusal, PythonRoleValue

    port = admitted_port(profile)
    with pytest.raises(PortRefusal, match="nominal contract"):
        port.invoke_python((PythonRoleValue("source", "kind:another", selected(profile).value),))
    monkeypatch.setattr(formal_products, "formal_profile_assets", lambda: SourceArtifact("formal/profile-assets", b"changed actual parser"))
    with pytest.raises(PortRefusal, match="assets differ"):
        port._verify()


def test_asset_contract_resolution_is_explicit_and_changed_bytes_change_recipe(profile):
    from dataclasses import replace

    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.types import PreparationError

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    sources = formal_operation_sources()
    with pytest.raises(PreparationError, match="captured semantic asset"):
        compile_data_operations(schema=bundle, python_sources=replace(sources, boundary_contracts=()))
    first = compile_data_operations(schema=bundle, python_sources=sources)
    second = compile_data_operations(schema=bundle, python_sources=replace(sources, boundary_contracts=(SourceArtifact("formal/profile-assets", b"different explicitly supplied parser"),)))
    assert first.operation("text.formal_evidence/source-native").assets != second.operation("text.formal_evidence/source-native").assets
    assert next(i.key for i in first.identities if i.domain == "recipe") != next(i.key for i in second.identities if i.domain == "recipe")


def test_target_preserves_packed_alternatives_and_original_source_custody_is_not_meaning(profile, monkeypatch):
    from dataclasses import replace

    from corpus_structure.methods.math import grammar
    from corpus_structure.semantic.product_reference import ProductReference
    from semantic.test_formal_evidence import source as original_source

    view = original_source(("original", "formula", "f(x)", "succeeded"))
    selectors = [dict(projection=view.ref.projection_digest, start=0, end=len(view.text))]
    first = FrozenFormalSource.from_source_view(profile.prepared, view, document="document:exact-original", selectors=selectors)
    relocated = replace(view, ref=replace(view.ref, id=99, document_id=50, native_product=ProductReference(777, "relocated-document", view.ref.native_product.content_digest)))
    second = FrozenFormalSource.from_source_view(profile.prepared, relocated, document="document:exact-original", selectors=selectors)
    assert first.content == second.content
    monkeypatch.setattr(grammar, "syntax", lambda *a, **k: pytest.fail("expanded conventional trees"))
    monkeypatch.setattr(grammar, "to_sympy", lambda *a, **k: pytest.fail("constructed native algebra"))
    left = profile.run(first, FormalEvidenceOptions())
    right = profile.run(second, FormalEvidenceOptions())
    assert left.content == right.content
    body = left.inventory()
    assert body["choices"]
    assert {"application", "multiply"} <= {row["value"] for row in body["terms"]}
    assert any("choice_group" in edge for row in body["terms"] for edge in row.get("children", ()))


def test_formal_nominal_packet_kinds_compile_to_native_publication_contract(profile):
    import json

    from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
    from corpus_structure.semantic.data_operation_storage import data_operation_definition_projection
    from corpus_structure.semantic.formal_products import formal_operation_sources

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    model = compile_data_operations(schema=bundle, python_sources=formal_operation_sources())
    kind = profile.prepared.index.definitions["DdoFormalProduct"].iri
    members = derive_member_kinds(model, kind)
    assert set(members) == {
        profile.prepared.index.definitions[name].iri for name in (
            "DdoFormalOccurrence", "DdoFormalAnnotation", "DdoFormalMembership",
            "DdoFormalTerm", "DdoFormalChoice",
        )
    }
    projected = json.loads(data_operation_definition_projection(profile.prepared, model, native_digest="native:controlled-profile"))
    contract = next(row for row in projected["kinds"] if row["kind"] == kind)
    assert len(contract["member_contracts"]) == 5
    assert contract["member_schema"] != {"not": {}}
    assert contract["universe"] == "source"
    for member in members:
        body = next(row for row in projected["kinds"] if row["kind"] == member)
        assert body["universe"] == "source"
        assert body["families"] == []


def test_prepared_formal_reused_port_runs_independent_requests_in_owned_child_main_threads(profile):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import ReadyGroup, drive_prepared_work
    from corpus_structure.methods.math.grammar import OffMainThread
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope, OwnedByteBudget
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

    port = admitted_port(profile)
    sources = (selected(profile, "using the equation x = 2."), selected(profile, "using the equation y = 3."))
    role = next(role for role in port.operation.roles if role.direction == "input")
    contract = next(i.key for i in port.profile.model.identities if (i.owner, i.domain) == (role.kind, "kind"))
    values = tuple((PythonRoleValue("source", contract, source.value),) for source in sources)
    with ThreadPoolExecutor(max_workers=1) as threads, pytest.raises(OffMainThread):
        threads.submit(port.invoke_python, values[0]).result()
    policy = CharacterizationExecutionPolicy(workers=2, max_submissions=2, max_packet_bytes=8 * 1024**2, max_reply_bytes=8 * 1024**2, max_owned_bytes=96 * 1024**2)
    budget = OwnedByteBudget(policy.max_owned_bytes)
    cpu = CPUExecutionScope(port.profile.prepared, policy, budget=budget, retain_schema=False)
    credits = []
    try:
        cpu.prepare()
        capsule_bytes = budget.used_bytes
        for _ in values:
            credits.append(budget.admit(policy.max_packet_bytes + policy.max_reply_bytes))
        admitted = budget.used_bytes
        assert admitted == capsule_bytes + 2 * (policy.max_packet_bytes + policy.max_reply_bytes)
        plans = tuple(port.plan_python(value, execution_owner=SimpleNamespace(cpu=cpu, reservation=credit)) for value, credit in zip(values, credits, strict=True))
        def together():
            return (yield ReadyGroup(plans, max_active=2))
        completions = drive_prepared_work(together(), lambda: None)
        assert len(completions) == 2
        assert completions[0].outputs[0].content == port.invoke_python(values[0]).outputs[0].content
        assert completions[1].outputs[0].content == port.invoke_python(values[1]).outputs[0].content
        assert completions[0].outputs[0].content != completions[1].outputs[0].content
        assert cpu.native_thread_reports
        import json
        for completion in completions:
            receipt = json.loads(completion.cpu_execution_evidence)
            assert receipt["main_thread"] is True and receipt["pid"] > 0
            assert len(receipt["request_digest"]) == 64
            assert receipt["native_thread_limit"] == policy.cpu_native_threads
            assert isinstance(json.loads(receipt["native_pools_json"]), list)
        assert budget.used_bytes == admitted
    finally:
        cpu.close()
        for credit in credits:
            credit.release()
    assert budget.used_bytes == 0


def test_shared_owned_byte_credit_cannot_reuse_capacity_until_every_owner_retires():
    from corpus_structure.semantic.cpu_execution import CapacityExceeded, OwnedByteBudget

    budget = OwnedByteBudget(10)
    parent = budget.admit(10)
    child = parent.share()
    parent.release()
    parent.release()
    assert budget.used_bytes == 10
    with pytest.raises(CapacityExceeded):
        budget.admit(1)
    child.release()
    child.release()
    assert budget.used_bytes == 0
    with pytest.raises(RuntimeError, match="retired"):
        parent.share()


def test_prepared_formal_refuses_monkeypatched_loaded_original_endpoint(profile, monkeypatch):
    from corpus_structure.methods.formal_evidence import FormalEvidenceOperation
    from corpus_structure.semantic.data_operation_ports import PortRefusal

    port = admitted_port(profile)
    monkeypatch.setattr(FormalEvidenceOperation, "run", lambda self, source: "invented result")
    with pytest.raises(PortRefusal, match="loaded formal endpoint"):
        port._verify()


def test_formal_product_cannot_relabel_typed_member_contract(profile):
    import json

    from corpus_structure.semantic.formal_products import validate_formal_product

    source = selected(profile, "Quantity: 2 kg")
    product = profile.run(source, FormalEvidenceOptions())
    value = json.loads(product.content)
    nominal = profile.prepared.index.definitions["DdoFormalAnnotation"].iri
    value["members"][0]["kind_contract"] = next(identity.key for identity in profile.model.identities if (identity.owner,identity.domain) == (nominal,"kind"))
    with pytest.raises(ValueError, match="nominal member contract"):
        validate_formal_product(profile.prepared, value, source, model=profile.model)


def test_schema_free_target_cpu_owner_refuses_legacy_work_and_retires_shared_credit(profile):
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope, OwnedByteBudget

    policy = CharacterizationExecutionPolicy(max_packet_bytes=1024, max_reply_bytes=1024)
    budget = OwnedByteBudget(policy.max_owned_bytes)
    scope = CPUExecutionScope(profile.prepared, policy, budget=budget, retain_schema=False)
    parent = budget.admit(2048)
    try:
        scope.prepare()
        assert budget.used_bytes == 2048
        permit = scope.try_admit(reservation=parent)
        assert permit is not None
        with pytest.raises(ValueError, match="refuses legacy"):
            scope.submit(permit, b"{}", {})
        assert budget.used_bytes == 2048
    finally:
        scope.close()
        parent.release()
    assert budget.used_bytes == 0


@pytest.mark.parametrize("changed", [
    {"status": "private_proposal"},
    {"family": "context.private_answers"},
    {"context": {}},
    {"external_premises": [{"layer":{"task_id":9,"product_key":"private","content_digest":"c"*64},"local_id":"external"}]},
    {"required_external_choices": [{"layer":{"task_id":9,"product_key":"private","content_digest":"c"*64},"local_id":"external"}]},
])
def test_target_formal_source_kind_rejects_generic_private_or_contextual_authority(profile, changed):
    import json

    from jsonschema.validators import validator_for
    from pydantic import ValidationError

    from corpus_structure.semantic.data_operation_storage import data_operation_definition_projection
    from corpus_structure.semantic.identity import canonical_bytes

    product = profile.run(selected(profile, "Quantity: 2 kg"), FormalEvidenceOptions())
    original = product.inventory()["annotations"][0]
    candidate = {**original, **changed}
    # These fields/states are legal in the shared broader released record. The
    # target source-native subtype must enforce its narrower authority itself.
    generic = {name:value for name,value in candidate.items() if name != "record_type"}
    profile.prepared.validate_json("CharacterizationAnnotation", canonical_bytes(generic))
    with pytest.raises(ValidationError):
        profile.prepared.validate_json("DdoFormalAnnotation", canonical_bytes(candidate))
    port = admitted_port(profile)
    projected = json.loads(data_operation_definition_projection(port.profile.prepared, port.profile.model, native_digest="native:controlled-profile"))
    schema = next(row["body_schema"] for row in projected["kinds"] if row["kind"] == profile.prepared.index.definitions["DdoFormalAnnotation"].iri)
    validator = validator_for(schema)(schema)
    assert validator.is_valid(original)
    assert not validator.is_valid(candidate)


def test_physical_custody_changes_do_not_change_formal_semantic_recipe(profile, monkeypatch):
    from corpus_structure.semantic import formal_products

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    source = formal_products.formal_operation_sources()
    original = compile_data_operations(schema=bundle, python_sources=source)
    semantic_assets = formal_products.formal_profile_assets()
    port = admitted_port(profile)
    monkeypatch.setattr(formal_products, "formal_execution_custody", lambda: SourceArtifact("formal/execution-custody", b"changed physical CPU/receipt code"))
    changed = compile_data_operations(schema=bundle, python_sources=formal_products.formal_operation_sources())
    assert formal_products.formal_profile_assets() == semantic_assets
    assert {(item.owner,item.domain):item.key for item in original.identities} == {(item.owner,item.domain):item.key for item in changed.identities}
    from corpus_structure.semantic.data_operation_ports import PortRefusal
    with pytest.raises(PortRefusal, match="acquired custody"):
        port._verify()
