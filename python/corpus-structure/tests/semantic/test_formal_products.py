"""Actual positioned parser controls for source-native formal products."""

from pathlib import Path

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    FrozenFormalSource,
    formal_product_inputs,
)
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.formal_products_support import (
    acquire_source as acquire_source,
)
from semantic.formal_products_support import (
    profile as profile,
)
from semantic.formal_products_support import (
    selected as selected,
)


def test_actual_formal_product_retains_positioned_rules_symbols_terms_and_witnesses(profile):
    source = selected(profile)
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    body = product.inventory()
    assert {row["kind"] for row in body["annotations"]} >= {
        "formal.input",
        "formal.rule",
        "formal.token",
        "formal.symbol",
    }
    assert any(row["kind"] == "operator" for row in body["terms"])
    assert all(
        row["extents"][0]["projection"] == source.value["source"]["projection"]
        for row in body["occurrences"]
    )
    assert all(
        "source_view_id" not in extent for row in body["occurrences"] for extent in row["extents"]
    )
    assert all(
        member.member_id and member.kind.startswith("https://") for member in product.members
    )
    assert product.value.source.document == "document:original-content"
    assert [row.family for row in product.value.coverage] == [
        "formal.lexical",
        "formal.number",
        "formal.threshold",
        "formal.date",
        "formal.identifier",
        "formal.quantity",
        "formal.interval",
        "formal.math",
    ]


def test_formal_semantics_do_not_depend_on_execution_limits_or_receipt_placement(profile):
    source = selected(profile, "Quantity: 2 kg")
    left = profile.run(
        source,
        FormalEvidenceOptions(parse_seconds=2, max_forest_nodes=20000),
        subject_context=_publication_context(source),
    )
    right = profile.run(
        source,
        FormalEvidenceOptions(parse_seconds=3, max_forest_nodes=30000, max_inline_chars=4096),
        subject_context=_publication_context(source),
    )
    assert left.content == right.content
    assert left.semantic_id == right.semantic_id
    assert b"release_id" not in left.content and b"task_id" not in left.content
    assert b"configuration" not in left.content and b"runtime" not in left.content


def test_formal_source_identity_and_exact_scope_change_meaning(profile):
    full = selected(profile, "Quantity: 2 kg")
    changed = thaw_native(full.value)
    changed["source"]["document"] = "document:another-original"
    changed["source"]["document_subject"] = original_document_subject("document:another-original")
    other = FrozenFormalSource.acquire(profile.prepared, changed)
    first = profile.run(full, FormalEvidenceOptions(), subject_context=_publication_context(full))
    second = profile.run(
        other, FormalEvidenceOptions(), subject_context=_publication_context(other)
    )
    assert {m.member_id for m in first.members}.isdisjoint({m.member_id for m in second.members})
    scoped = thaw_native(full.value)
    scoped["selectors"][0]["end"] = 8
    result = profile.run(
        FrozenFormalSource.acquire(profile.prepared, scoped),
        FormalEvidenceOptions(),
        subject_context=_publication_context(FrozenFormalSource.acquire(profile.prepared, scoped)),
    )
    assert all(
        extent.get("end", 0) <= 8
        for row in result.inventory()["occurrences"]
        for extent in row["extents"]
    )
    assert result.value.selectors[0].end == 8


def test_selected_source_is_detached_and_refuses_forged_coordinates(profile):
    original = selected(profile, "x ≥ 2")
    changed = thaw_native(original.value)
    changed["items"][0]["text"] = "caller mutation"
    assert original.value["items"][0]["text"] == "x ≥ 2"
    changed = thaw_native(original.value)
    changed["selectors"][0]["projection"] = "c" * 64
    with pytest.raises(ValueError, match="another projection"):
        FrozenFormalSource.acquire(profile.prepared, changed)
    changed = thaw_native(original.value)
    changed["pieces"][0]["item_ref"] = "#/missing"
    with pytest.raises(ValueError, match="original atom"):
        FrozenFormalSource.acquire(profile.prepared, changed)


def test_unprojected_recognized_formula_preserves_atom_and_unknown_correspondence(profile):
    value = dict(
        source=dict(
            document="document:original-content",
            document_subject=original_document_subject("document:original-content"),
            section_pointer="#/groups/0",
            membership="descendants",
            projection="b" * 64,
        ),
        text="",
        pieces=[],
        items=[
            dict(self_ref="#/texts/0", label="formula", text="x+1", orig="", prov=[dict(page_no=1)])
        ],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
        selectors=[dict(projection="b" * 64, native_pointer="#/texts/0")],
    )
    product = profile.run(
        acquire_source(profile, value),
        FormalEvidenceOptions(),
        subject_context=_publication_context(acquire_source(profile, value)),
    )
    inputs = [
        row["formal_input"] for row in product.inventory()["annotations"] if "formal_input" in row
    ]
    assert inputs[0]["representation"] == "recognized_latex"
    assert inputs[0]["correspondence"][0]["relation"] == "contained_in_atom"
    assert product.value.outcome == "partial"
    assert all(
        "start" not in extent
        for row in product.inventory()["occurrences"]
        for extent in row["extents"]
    )


@pytest.mark.parametrize("latex,expected", [("x+1", "ok"), ("f(x)", "ambiguous")])
def test_source_native_math_readings_restore_retained_syntax_without_parser(
    profile, monkeypatch, latex, expected
):
    from corpus_structure.methods.math import grammar
    from corpus_structure.semantic.formal_forest import SourceNativeMathReadings

    source = selected(
        profile,
        latex,
        items=[
            dict(
                self_ref="#/texts/0",
                label="formula",
                text=latex,
                orig=latex,
                prov=[dict(page_no=1)],
            )
        ],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
    )
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    readings = SourceNativeMathReadings(source, (product,))

    def refuse_parse(*args, **kwargs):
        pytest.fail("retained mathematical consumer reran recognition")

    monkeypatch.setattr(grammar, "syntax", refuse_parse)
    monkeypatch.setattr(grammar, "syntax_forest", refuse_parse)
    syntax = readings.syntax("#/texts/0", latex)
    assert syntax.status.value == expected, syntax.failure
    assert syntax.tree is not None
    inventory = readings.inventory("#/texts/0", latex)
    assert inventory["input"]["product_id"] == product.semantic_id
    assert inventory["input"]["member_id"] in {member.member_id for member in product.members}
    assert all(
        set(row["primary_node"]) == {"product_id", "member_id"} for row in inventory["nodes"]
    )
    missing = readings.syntax("#/texts/999", latex).failure
    assert missing is not None and missing.category == "missing_primary_input"
    competing = SourceNativeMathReadings(source, (product, product))
    ambiguous = competing.syntax("#/texts/0", latex).failure
    assert ambiguous is not None and ambiguous.category == "ambiguous_primary_input"


def test_source_native_math_readings_refuse_different_original_coordinate(profile):
    from corpus_structure.semantic.formal_forest import SourceNativeMathReadings

    source = selected(profile)
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    changed = thaw_native(source.value)
    changed["source"]["membership"] = "direct"
    other = FrozenFormalSource.acquire(profile.prepared, changed)
    with pytest.raises(ValueError, match="another source"):
        SourceNativeMathReadings(other, (product,))


def test_cooperative_cancellation_prevents_complete_product(profile):
    def cancel():
        raise RuntimeError("cancelled original request")

    with pytest.raises(RuntimeError, match="cancelled original request"):
        profile.run(
            selected(profile),
            FormalEvidenceOptions(),
            check_active=cancel,
            subject_context=_publication_context(selected(profile)),
        )


def test_immediate_construction_boundary_reuses_formal_facts_without_parser(profile, monkeypatch):
    from corpus_structure.semantic import formal_evidence
    from corpus_structure.semantic.data_product_reference import DataProductMemberReference
    from corpus_structure.semantic.formal_readings import FormalSourceReadings

    source = selected(profile, "Quantity: 2 kg")
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    monkeypatch.setattr(
        formal_evidence,
        "formal_field_grammar",
        lambda *_: pytest.fail("consumer reparsed formal text"),
    )
    boundary = FormalSourceReadings.from_products((product,), source)
    fields, complete = boundary.fields(
        family="formal.quantity", start=0, end=len(source.value["text"])
    )
    assert complete and len(fields) == 1
    assert fields[0].normalized["value"] == "2"
    assert fields[0].normalized["unit"] == "kg"
    assert isinstance(fields[0].reference, DataProductMemberReference)
    assert fields[0].reference.product.product_id == product.semantic_id
    changed = thaw_native(source.value)
    changed["source"]["document"] = "another-original"
    changed["source"]["document_subject"] = original_document_subject("another-original")
    with pytest.raises(ValueError, match="another original source"):
        FormalSourceReadings.from_products(
            (product,), FrozenFormalSource.acquire(profile.prepared, changed)
        )


def test_captured_formal_source_profile_declares_real_nominal_products_and_assets(profile):
    from corpus_structure.semantic.formal_products import (
        formal_operation_sources,
        formal_product_inputs,
    )

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    model = compile_data_operations(schema=bundle, python_sources=formal_operation_sources())
    operation = model.operation("text.formal_evidence/source-native")
    assert operation.capabilities.preparation == "resource"
    assert (
        operation.assets[0].content_digest
        == formal_operation_sources().boundary_contracts[0].digest
    )
    assert operation.callable_surfaces[0].declaration.endswith("FormalEvidenceOperation.run")
    assert model.implementation_slices[0].complete


def admitted_port(profile):
    from dataclasses import asdict
    from hashlib import sha256

    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.formal_products import (
        formal_operation_sources,
        resolve_formal_evidence_port,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = formal_operation_sources()
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    prepared = prepare_release(
        bundle,
        data_operation_dependencies(ResolvedDependencies(), python_sources=sources),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    operation = model.operation("text.formal_evidence/source-native")
    ids = {(item.owner, item.domain): item.key for item in model.identities}
    assert operation.implementation_root is not None
    boundaries = (*operation.assets, *model.implementation_slices[0].boundaries)
    identity = PreparedCapabilityIdentity(
        sha256(model.content).hexdigest(),
        operation.semantic_id,
        ids[operation.semantic_id, "definition"],
        ids[operation.semantic_id, "recipe"],
        ids[operation.implementation_root, "implementation-slice"],
        operation.callable_surfaces[0].declaration,
        sha256(
            canonical_bytes(
                tuple((s.module, sha256(s.content).hexdigest()) for s in sources.sources)
            )
        ).hexdigest(),
        canonical_bytes(asdict(operation.capabilities)),
        ids[operation.semantic_id, "eligibility"],
        "runtime:controlled-profile",
        canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )

    def authorize(actual):
        if actual != identity:
            raise ValueError("not the controlled acquired identity")

    return resolve_formal_evidence_port(
        prepared,
        model,
        operation.semantic_id,
        identity=identity,
        authorize=authorize,
        custody=sources.boundary_contracts,
    )


def test_original_prepared_entrypoint_emits_typed_body_and_native_members(profile):
    import json

    from corpus_structure.semantic.data_operation_ports import PythonRoleValue
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    port = admitted_port(profile)
    source = selected(profile, "Quantity: 2 kg")
    role = next(role for role in port.operation.roles if role.direction == "input")
    contract = next(
        i.key for i in port.profile.model.identities if (i.owner, i.domain) == (role.kind, "kind")
    )
    completion = port.invoke_python((PythonRoleValue("source", contract, source.value),))
    (output,) = completion.outputs
    assert output.meaning is not None
    assert (
        decode_semantic_value(json.loads(output.meaning))["source"]["document"]
        == "document:original-content"
    )
    assert output.members
    native = [json.loads(packet) for packet in output.members]
    assert all(
        packet["context"]["original_source"] == "document:original-content" for packet in native
    )
    assert all(
        set(packet) == {"member_id", "kind_contract", "context", "body"} for packet in native
    )
    # Exercise the actual native completion wire, without pretending this controlled
    # private calculation is a live native publication or provider qualification.
    payload = dict(
        request_id="request:formal",
        generation=1,
        task_id=1,
        attempt=1,
        holder="worker",
        runtime_id=port.identity.runtime,
        completion=dict(
            outcome="addressed",
            implementation_revision=port.identity.implementation,
            inputs=[],
            support=[],
            outputs=[
                dict(
                    role="result",
                    position=0,
                    multiplicity=1,
                    product=dict(
                        kind_contract=output.kind_contract,
                        body=json.loads(output.meaning),
                        members=native,
                    ),
                )
            ],
        ),
    )
    assert (
        validate_native_wire("retain_data_completion_intent", "input", payload)["completion"][
            "outputs"
        ][0]["product"]["members"]
        == native
    )


def test_prepared_formal_profile_rejects_changed_source_assets_and_nominal_input(
    profile, monkeypatch
):
    from corpus_structure.semantic import formal_products
    from corpus_structure.semantic.data_operation_ports import PortRefusal, PythonRoleValue

    port = admitted_port(profile)
    with pytest.raises(PortRefusal, match="nominal contract"):
        port.invoke_python((PythonRoleValue("source", "kind:another", selected(profile).value),))
    monkeypatch.setattr(
        formal_products,
        "formal_profile_assets",
        lambda: SourceArtifact("formal/profile-assets", b"changed actual parser"),
    )
    with pytest.raises(PortRefusal, match=r"resources differ|assets differ"):
        port._verify()


def test_asset_contract_resolution_is_explicit_and_changed_bytes_change_recipe(profile):
    from dataclasses import replace

    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.types import PreparationError

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = formal_operation_sources()
    with pytest.raises(PreparationError, match="captured semantic asset"):
        compile_data_operations(
            schema=bundle,
            python_sources=replace(
                sources,
                boundary_contracts=tuple(
                    asset
                    for asset in sources.boundary_contracts
                    if asset.name != "formal/profile-assets"
                ),
            ),
        )
    first = compile_data_operations(schema=bundle, python_sources=sources)
    second = compile_data_operations(
        schema=bundle,
        python_sources=replace(
            sources,
            boundary_contracts=tuple(
                SourceArtifact(asset.name, b"different explicitly supplied parser")
                if asset.name == "formal/profile-assets"
                else asset
                for asset in sources.boundary_contracts
            ),
        ),
    )
    assert (
        first.operation("text.formal_evidence/source-native").assets
        != second.operation("text.formal_evidence/source-native").assets
    )
    assert next(i.key for i in first.identities if i.domain == "recipe") != next(
        i.key for i in second.identities if i.domain == "recipe"
    )


def test_target_preserves_packed_alternatives_for_current_source_projection(profile, monkeypatch):
    from corpus_structure.methods.math import grammar

    first = selected(
        profile,
        "f(x)",
        items=[
            dict(
                self_ref="#/texts/0",
                label="formula",
                text="f(x)",
                orig="f(x)",
                prov=[dict(page_no=1)],
            )
        ],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
    )
    monkeypatch.setattr(
        grammar, "syntax", lambda *a, **k: pytest.fail("expanded conventional trees")
    )
    monkeypatch.setattr(
        grammar, "to_sympy", lambda *a, **k: pytest.fail("constructed native algebra")
    )
    left = profile.run(first, FormalEvidenceOptions(), subject_context=_publication_context(first))
    body = left.inventory()
    assert body["choices"]
    assert {"application", "multiply"} <= {row["value"] for row in body["terms"]}
    assert any("choice_group" in edge for row in body["terms"] for edge in row.get("children", ()))


def test_formal_nominal_packet_kinds_compile_to_native_publication_contract(profile):
    import json

    from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )
    from corpus_structure.semantic.formal_products import formal_operation_sources

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    model = compile_data_operations(schema=bundle, python_sources=formal_operation_sources())
    kind = profile.prepared.index.definitions["DdoFormalProduct"].iri
    members = derive_member_kinds(model, kind)
    assert set(members) == {
        profile.prepared.index.definitions[name].iri
        for name in (
            "DdoFormalOccurrence",
            "DdoFormalAnnotation",
            "DdoFormalMembership",
            "DdoFormalTerm",
            "DdoFormalChoice",
            "DdoFormalAlternative",
            "DdoFormalManifest",
        )
    }
    projected = json.loads(
        data_operation_definition_projection(
            profile.prepared, model, native_digest="native:controlled-profile"
        )
    )
    contract = next(row for row in projected["kinds"] if row["kind"] == kind)
    assert len(contract["member_contracts"]) == 7
    assert contract["member_schema"] != {"not": {}}
    assert contract["universe"] == "source"
    for member in members:
        body = next(row for row in projected["kinds"] if row["kind"] == member)
        assert body["universe"] == (
            "ordinary"
            if member == profile.prepared.index.definitions["DdoFormalManifest"].iri
            else "source"
        )


def test_prepared_formal_reused_port_runs_independent_requests_in_owned_child_main_threads(profile):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import ReadyGroup, drive_prepared_work
    from corpus_structure.methods.math.grammar import OffMainThread
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope, OwnedByteBudget
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue

    port = admitted_port(profile)
    sources = (
        selected(profile, "using the equation x = 2."),
        selected(profile, "using the equation y = 3."),
    )
    role = next(role for role in port.operation.roles if role.direction == "input")
    contract = next(
        i.key for i in port.profile.model.identities if (i.owner, i.domain) == (role.kind, "kind")
    )
    values = tuple((PythonRoleValue("source", contract, source.value),) for source in sources)
    with ThreadPoolExecutor(max_workers=1) as threads, pytest.raises(OffMainThread):
        threads.submit(port.invoke_python, values[0]).result()
    policy = CharacterizationExecutionPolicy(
        workers=2,
        max_submissions=2,
        max_packet_bytes=8 * 1024**2,
        max_reply_bytes=8 * 1024**2,
        max_owned_bytes=96 * 1024**2,
    )
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
        plans = tuple(
            port.plan_python(value, execution_owner=SimpleNamespace(cpu=cpu, reservation=credit))
            for value, credit in zip(values, credits, strict=True)
        )

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
    with pytest.raises(PortRefusal, match="callable is outside its required source subset"):
        port._verify()


def test_formal_product_cannot_relabel_typed_member_contract(profile):
    import json

    from corpus_structure.semantic.formal_products import validate_formal_product

    source = selected(profile, "Quantity: 2 kg")
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    value = json.loads(product.content)
    nominal = profile.prepared.index.definitions["DdoFormalAnnotation"].iri
    value["members"][0]["kind_contract"] = next(
        identity.key
        for identity in profile.model.identities
        if (identity.owner, identity.domain) == (nominal, "kind")
    )
    with pytest.raises(ValueError, match="nominal member contract"):
        validate_formal_product(profile.prepared, value, source, model=profile.model)


def test_schema_free_target_cpu_owner_retires_shared_credit(profile):
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
        scope.release_admission(permit)
        assert budget.used_bytes == 2048
    finally:
        scope.close()
        parent.release()
    assert budget.used_bytes == 0


@pytest.mark.parametrize(
    "changed",
    [
        {"status": "private_proposal"},
        {"family": "context.private_answers"},
        {"context": {}},
        {
            "external_premises": [
                {
                    "product_id": "unadmitted:private-source",
                    "member_id": "external",
                }
            ]
        },
        {
            "required_external_choices": [
                {
                    "product_id": "unadmitted:private-source",
                    "member_id": "external",
                }
            ]
        },
    ],
)
def test_target_formal_source_kind_rejects_generic_private_or_contextual_authority(
    profile, changed
):
    import json

    from jsonschema.validators import validator_for
    from pydantic import ValidationError

    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    product = profile.run(
        selected(profile, "Quantity: 2 kg"),
        FormalEvidenceOptions(),
        subject_context=_publication_context(selected(profile, "Quantity: 2 kg")),
    )
    original = product.inventory()["annotations"][0]
    candidate = {**original, **changed}
    # These fields/states are legal in the shared broader released record. The
    # target source-native subtype must enforce its narrower authority itself.
    generic = {name: value for name, value in candidate.items() if name != "record_type"}
    profile.prepared.validate_json("CharacterizationAnnotation", canonical_bytes(generic))
    with pytest.raises(ValidationError):
        profile.prepared.validate_json("DdoFormalAnnotation", canonical_bytes(candidate))
    port = admitted_port(profile)
    projected = json.loads(
        data_operation_definition_projection(
            port.profile.prepared, port.profile.model, native_digest="native:controlled-profile"
        )
    )
    schema = next(
        row["body_schema"]
        for row in projected["kinds"]
        if row["kind"] == profile.prepared.index.definitions["DdoFormalAnnotation"].iri
    )
    validator = validator_for(schema)(schema)
    assert validator.is_valid(original)
    assert not validator.is_valid(candidate)


def test_physical_custody_changes_do_not_change_formal_semantic_recipe(profile, monkeypatch):
    from corpus_structure.semantic import formal_products

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    source = formal_products.formal_operation_sources()
    original = compile_data_operations(schema=bundle, python_sources=source)
    semantic_assets = formal_products.formal_profile_assets()
    port = admitted_port(profile)
    monkeypatch.setattr(
        formal_products,
        "formal_execution_custody",
        lambda: SourceArtifact(
            "formal/execution-custody", b"changed physical CPU/receipt code", runtime_transport=True
        ),
    )
    changed = compile_data_operations(
        schema=bundle, python_sources=formal_products.formal_operation_sources()
    )
    assert formal_products.formal_profile_assets() == semantic_assets
    assert {(item.owner, item.domain): item.key for item in original.identities} == {
        (item.owner, item.domain): item.key for item in changed.identities
    }
    from corpus_structure.semantic.data_operation_ports import PortRefusal

    with pytest.raises(PortRefusal, match="acquired custody"):
        port._verify()


def test_primary_lexicon_is_consumed_without_reclassification(profile, monkeypatch):
    from corpus_structure.semantic.constructions import forest
    from corpus_structure.semantic.formal_readings import FormalSourceReadings

    source = selected(profile, "All samples are finite.")
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    readings = FormalSourceReadings.from_products((product,), source)
    atoms, terminals = readings.positioned(start=0, end=len(source.value["text"]))
    assert not atoms
    assert {(row.terminal, row.text) for row in terminals} >= {
        ("QUANT", "All"),
        ("COPULA", "are"),
        ("WORD", "samples"),
    }

    def no_classification(*args, **kwargs):
        pytest.fail("construction reclassified primary source language")

    monkeypatch.setattr(forest, "classify", no_classification)
    result = forest.recognize(source.value["text"], atoms, terminals=terminals)
    assert result.reducer is not None
    assert any(row["kind"] == "binder" for row in result.reducer.terms.values())
    assert any(row["kind"] == "predicate" for row in result.reducer.terms.values())


def test_primary_lexicon_protects_fields_and_rejects_forged_slices(profile):
    from corpus_structure.semantic.formal_products import validate_formal_product
    from corpus_structure.semantic.formal_readings import FormalSourceReadings

    source = selected(profile, "All samples use Quantity: 2 kg.")
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    atoms, terminals = FormalSourceReadings.from_products((product,), source).positioned(
        start=0, end=len(source.value["text"])
    )
    assert atoms
    assert all(
        not (atom.start < row.end and row.start < atom.end) for atom in atoms for row in terminals
    )
    body = product.value.model_dump(mode="json", exclude_unset=True)
    body["lexicon"][0]["terminals"][0]["text"] = "forged"
    with pytest.raises(ValueError, match="original unprotected slice"):
        validate_formal_product(profile.prepared, body, source, model=profile.model)


def test_each_retained_formal_choice_has_an_addressable_exact_member_packet(profile):
    from corpus_structure.semantic.formal_products import validate_formal_product

    source = selected(
        profile,
        "f(x)",
        items=[
            dict(
                self_ref="#/texts/0",
                label="formula",
                text="f(x)",
                orig="f(x)",
                prov=[dict(page_no=1)],
            )
        ],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
    )
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    body = product.value.model_dump(mode="json", exclude_unset=True)
    groups = [
        packet["body"] for packet in body["members"] if packet["body"]["record_type"] == "choice"
    ]
    alternatives = {
        packet["member_id"]: packet["body"]
        for packet in body["members"]
        if packet["body"]["record_type"] == "choice_member"
    }
    assert groups and alternatives
    assert alternatives == {
        member["local_id"]: dict(record_type="choice_member", group_id=group["local_id"], **member)
        for group in groups
        for member in group["members"]
    }
    body["members"] = [
        packet for packet in body["members"] if packet["body"]["record_type"] != "choice_member"
    ]
    with pytest.raises(ValueError, match="owning packed group"):
        validate_formal_product(profile.prepared, body, source, model=profile.model)


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
        subject_definition="original-source-view",
    )


def test_publication_identity_requires_context_and_distinguishes_authority_scope(profile):
    from dataclasses import replace

    source = selected(profile, "All samples are finite.")
    context = _publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    other = replace(product, subject_context=replace(context, project_id="another-project"))
    assert other.content == product.content
    assert other.semantic_id != product.semantic_id
    with pytest.raises(ValueError, match="explicit acquired subject context"):
        _ = replace(product, subject_context=None).semantic_id


def test_prepared_family_completion_preserves_declared_success_outcome(profile):
    from dataclasses import replace

    from corpus_structure.semantic.data_operation_model import StateTransition

    source = selected(profile, "Quantity: 2 kg")
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    original = admitted_port(profile)
    declared = replace(
        original.operation,
        outcomes=("produced", "failed"),
        transitions=(StateTransition("completion", "pending", "success", "produced"),),
    )
    completion = replace(original, operation=declared)._completion(product, source)
    assert completion.outcome == "produced"
    assert completion.outputs[0].content == product.content
    assert {attestation.rule_id for attestation in completion.rule_attestations} == {
        "text.formal_evidence/literal-source-geometry",
        "text.formal_evidence/packed-choice-members",
        "text.formal_evidence/examined-scope",
        "text.formal_evidence/lexical-inventory-links",
        "text.formal_evidence/symbolic-inventory-positions",
        "text.formal_evidence/numeric-normalization",
        "text.formal_evidence/occurrence-origin",
        "text.formal_evidence/family-roster",
        "text.formal_evidence/member-local-addresses",
        "text.formal_evidence/inventory-topology",
        "text.formal_evidence/native-numeric-scores",
    }


def test_formal_inventory_topology_checks_owned_links_and_cycles():
    from corpus_structure.semantic.formal_products import verify_formal_inventory_topology

    def term(id_, children):
        return {
            "member_id": id_,
            "body": {
                "record_type": "term",
                "local_id": id_,
                "kind": "operator",
                "children": [
                    {"target": target, "structural": True, "role": "operand"} for target in children
                ],
            },
        }

    verify_formal_inventory_topology((term("x", ("y",)), term("y", ())))
    with pytest.raises(ValueError, match="term/containment structural cycle"):
        verify_formal_inventory_topology((term("x", ("y",)), term("y", ("x",))))
    with pytest.raises(ValueError, match="dangling term/site"):
        verify_formal_inventory_topology((term("x", ("missing",)),))


def test_native_inventory_scores_require_the_exact_numeric_source_codec():
    from corpus_structure.semantic.characterization import verify_inventory_native_scores

    def packet(value):
        return {"body": {"record_type": "term", "scores": [{"value": value}]}}

    verify_inventory_native_scores(
        (
            packet({"kind": "null"}),
            packet({"kind": "integer", "integer": 1 << 90}),
            packet({"kind": "float", "hexadecimal": "-0x0.0p+0"}),
        )
    )
    with pytest.raises(ValueError, match="native score requires an exact numeric source"):
        verify_inventory_native_scores((packet({"kind": "boolean", "boolean": False}),))
    with pytest.raises(ValueError, match="noncanonical hexadecimal float"):
        verify_inventory_native_scores((packet({"kind": "float", "hexadecimal": "0x1p+0"}),))


def test_formal_family_roster_requires_all_families_in_order():
    from corpus_structure.semantic.formal_products import verify_formal_family_roster

    coverage = [
        {"family": "formal.lexical"},
        {"family": "formal.number"},
        {"family": "formal.threshold"},
        {"family": "formal.date"},
        {"family": "formal.identifier"},
        {"family": "formal.quantity"},
        {"family": "formal.interval"},
        {"family": "formal.math"},
    ]
    verify_formal_family_roster(coverage)
    for invalid in (
        coverage[:-1],
        [*coverage[:-1], {"family": "formal.unknown"}],
        [coverage[1], coverage[0], *coverage[2:]],
    ):
        with pytest.raises(ValueError, match="retain every examined family outcome"):
            verify_formal_family_roster(invalid)


def test_formal_member_local_addresses_refuse_packet_and_packed_collisions():
    from corpus_structure.semantic.formal_products import verify_formal_member_local_addresses

    term = {"member_id": "term", "body": {"local_id": "term", "record_type": "term"}}
    group = {
        "member_id": "site",
        "body": {"local_id": "site", "record_type": "choice", "members": [{"local_id": "alt"}]},
    }
    alternative = {"member_id": "alt", "body": {"local_id": "alt", "record_type": "choice_member"}}
    _, _, nodes, choices = verify_formal_member_local_addresses((term, group, alternative))
    assert set(nodes) == {"term", "site", "alt"}
    assert choices == {"alt": group["body"]}
    with pytest.raises(ValueError, match="original semantic source/member"):
        verify_formal_member_local_addresses(({**term, "member_id": "other"},))
    with pytest.raises(ValueError, match="packet repeats member identity"):
        verify_formal_member_local_addresses((term, term))
    for packed in ([{"local_id": "alt"}, {"local_id": "alt"}], [{"local_id": "term"}]):
        fake_group = {**group, "body": {**group["body"], "members": packed}}
        with pytest.raises(ValueError, match="choice member repeats local identity"):
            verify_formal_member_local_addresses((term, fake_group, alternative))


def test_formal_occurrence_origin_requires_actual_page_and_selector_ancestry():
    from corpus_structure.semantic.formal_products import verify_formal_occurrence_origin

    selected = {
        "source": {"projection": "original"},
        "text": "alpha",
        "items": [{"self_ref": "#/texts/1", "parent": "#/groups/2", "prov": [{"page_no": 3}]}],
        "ancestors": [{"self_ref": "#/groups/2", "parent": "#/body"}],
        "selectors": [{"native_pointer": "#/body", "page": 3, "start": 1, "end": 4}],
    }
    extent = {
        "native_pointer": "#/texts/1",
        "projection": "original",
        "page": 3,
        "start": 1,
        "end": 4,
    }
    verify_formal_occurrence_origin(({"extents": [extent]},), selected)
    with pytest.raises(ValueError, match="another original page"):
        verify_formal_occurrence_origin(({"extents": [{**extent, "page": 2}]},), selected)
    with pytest.raises(ValueError, match="escapes the selected examined scope"):
        verify_formal_occurrence_origin(({"extents": [extent]},), {**selected, "ancestors": []})
    with pytest.raises(ValueError, match="escapes the selected examined scope"):
        verify_formal_occurrence_origin(({"extents": [{**extent, "end": 5}]},), selected)


def test_declared_formal_adapter_retains_inline_symbol_addresses_without_task_aliases(profile):
    from corpus_structure.methods.inline_formula_occurrences import inline_equations, inline_symbols
    from corpus_structure.semantic.declared_formal_readings import declared_formal_layers

    source = selected(profile)
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    retained = declared_formal_layers((product,), source)
    value = source.value
    equations = tuple(
        inline_equations(
            value["text"],
            value["pieces"],
            {item["self_ref"]: item for item in value["items"]},
            None,
            max_chars=2048,
            primary_layers=retained,
            projection=value["source"]["projection"],
        )
    )
    assert len(equations) == 1
    assert equations[0].primary_input is not None
    assert equations[0].primary_input["product_id"] == product.semantic_id
    symbols, status = inline_symbols(
        value["text"],
        equations[0],
        primary_layers=retained,
        projection=value["source"]["projection"],
    )
    assert status == "parsed"
    assert [value["text"][symbol.start : symbol.end] for symbol in symbols] == ["x"]
    for symbol in symbols:
        assert symbol.primary_node is not None
        assert symbol.primary_node["product_id"] == product.semantic_id
        assert "task_id" not in symbol.primary_node


def test_declared_formal_adapter_refuses_scope_substitution_or_duplicate_product(profile):
    from corpus_structure.semantic.declared_formal_readings import declared_formal_layers

    source = selected(profile)
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    with pytest.raises(ValueError, match="repeats"):
        declared_formal_layers((product, product), source)
    changed = thaw_native(source.value)
    changed["selectors"][0]["end"] -= 1
    narrowed = FrozenFormalSource.acquire(profile.prepared, changed)
    with pytest.raises(ValueError, match="analyzed scope"):
        declared_formal_layers((product,), narrowed)


def test_target_threshold_reader_keeps_genuine_semantic_members_and_refuses_foreign_source(profile):
    from corpus_structure.methods.structural_products import threshold_readings
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.formal_readings import FormalSourceReadings
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.structural_products import StructuralPassage

    text = "revenue > 25000 USD\nComparison basis: annual gross revenue."
    source = selected(profile, text)
    product = profile.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    primary = FormalSourceReadings.from_products((product,), source)
    coordinate = source.value["source"]
    # This address is an independently authored pure reader fixture, not a native
    # admission claim. All parser fields and primary member addresses above are real.
    address = DeclaredStructuralSource(
        source=canonical_bytes(["fixture:native-source", None]).decode(),
        source_product="fixture:native-source",
        kind_contract="kind:fixture-source",
        subject=coordinate["document_subject"],
        document=coordinate["document"],
        projection_digest=coordinate["projection"],
        section_pointer=coordinate["section_pointer"],
        membership=coordinate["membership"],
        project_id="fixture",
        original_source=coordinate["document"],
        analyzed_scope_meaning="{}",
        subject_definition="original-source-view",
    )
    passage = StructuralPassage(
        passage_id="p",
        source_ref=address.identity,
        start=0,
        end=len(text),
        text=text,
        scope="selected",
    )
    (field,) = threshold_readings(passage, source=address, primary_layers=primary)
    from corpus_structure.semantic.structural_products import DeclaredClauseField

    assert isinstance(field, DeclaredClauseField)
    assert field.typed is not None and field.typed.value == "25000"
    assert field.typed.unit == "USD" and field.typed.basis == "annual gross revenue"
    assert (
        field.typed.primary_formal is not None
        and field.typed.primary_formal.product_id == product.semantic_id
    )
    assert (
        field.typed.primary_basis is not None
        and field.typed.primary_basis.product_id == product.semantic_id
    )
    assert all(
        "layer" not in value
        for value in (field.typed.primary_formal.values(), field.typed.primary_basis.values())
    )
    with pytest.raises(ValueError, match="another original source"):
        threshold_readings(
            passage,
            source=address.model_copy(update={"document": "document:foreign"}),
            primary_layers=primary,
        )


def test_target_formal_profile_refuses_stale_captured_grammar(profile):
    from dataclasses import replace

    source = selected(profile, "x+y=1")
    with pytest.raises(ValueError, match="effective grammar"):
        replace(profile, grammar="obsolete").run(
            source, FormalEvidenceOptions(), subject_context=_publication_context(source)
        )


def test_target_distinct_original_projections_keep_disjoint_formal_members(profile):
    from semantic.formal_products_support import selected_rows

    left, right = (
        selected_rows(profile, (text, "formula", text, "succeeded")) for text in ("x+y=1", "x-y=2")
    )
    assert left.value["source"]["document"] == right.value["source"]["document"]
    assert left.value["source"]["projection"] != right.value["source"]["projection"]
    results = tuple(
        profile.run(
            source,
            FormalEvidenceOptions(math_start="formula"),
            subject_context=_publication_context(source),
        )
        for source in (left, right)
    )
    members = [{member.member_id for member in product.members} for product in results]
    assert members[0] and members[1] and members[0].isdisjoint(members[1])
    assert all(
        any(row["kind"] == "formal.symbol" for row in product.inventory()["annotations"])
        for product in results
    )
