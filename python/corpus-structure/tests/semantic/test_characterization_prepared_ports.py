"""Actual acquired family kernels on the shared managed CPU process owner."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization_ports import (
    construction_operation_sources,
    contextual_operation_sources,
    resolve_construction_port,
    resolve_contextual_port,
)
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import construction_product_inputs
from corpus_structure.semantic.data_operation_admission import (
    PreparedCapabilityIdentity,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_ports import PythonRoleValue, python_port_identity
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

from .test_formal_products import selected


@pytest.fixture(scope="module")
def acquired():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    collections = (
        formal_operation_sources(),
        construction_operation_sources(),
        contextual_operation_sources(),
    )
    contracts = {
        artifact.name: artifact
        for collection in collections
        for artifact in collection.boundary_contracts
    }
    sources = PythonSourceCollection(
        tuple(source for collection in collections for source in collection.sources),
        boundary_contracts=tuple(contracts.values()),
    )
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(ResolvedDependencies(), python_sources=sources),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    formal = prepare_formal_evidence(prepared, model, grammar=grammar_identity())
    return bundle, sources, prepared, model, formal


def admitted(acquired, operation, factory):
    bundle, sources, prepared, model, _ = acquired
    selected_op = model.operation(operation)
    base = python_port_identity(model, sources, operation, schema=bundle, prepared=prepared)
    boundaries = (
        *selected_op.assets,
        *(
            boundary
            for implementation in model.implementation_slices
            if implementation.root == selected_op.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    identity = PreparedCapabilityIdentity(
        **asdict(base),
        runtime="controlled:family-source-custody",
        assets=canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )

    def authorize(actual):
        if actual != identity:
            raise ValueError("not the exact controlled acquired execution identity")

    return factory(
        prepared,
        model,
        operation,
        identity=identity,
        authorize=authorize,
        custody=sources.boundary_contracts,
        sources=sources,
    )


def values(port, **provided):
    contracts = {
        (identity.owner, identity.domain): identity.key for identity in port.model.identities
    }
    return tuple(
        PythonRoleValue(role.name, contracts[role.kind, "kind"], provided[role.name])
        for role in port.operation.roles
        if role.direction == "input" and role.name in provided
    )


def test_acquired_construction_kernel_runs_real_parser_in_child_and_preserves_typed_packets(
    acquired,
):
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value

    _, _, prepared, _, formal = acquired
    source = selected(formal, "Not every trial succeeds.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    port = admitted(acquired, "text.constructions/source-native", resolve_construction_port)
    inputs = values(port, source=source.value, formal=(primary,))
    expected = port.invoke_python(inputs)
    cpu = CPUExecutionScope(
        prepared,
        CharacterizationExecutionPolicy(
            workers=1, max_submissions=1, max_packet_bytes=8 * 1024**2, max_reply_bytes=8 * 1024**2
        ),
        retain_schema=False,
    )
    try:
        actual = drive_prepared_work(
            port.plan_python(inputs, execution_owner=SimpleNamespace(cpu=cpu, reservation=None)),
            lambda: None,
        )
        assert actual.outputs[0].content == expected.outputs[0].content
        body = decode_semantic_value(json.loads(actual.outputs[0].meaning))
        assert any(packet["body"].get("kind") == "binder" for packet in body["members"])
        receipt = json.loads(actual.cpu_execution_evidence)
        assert receipt["pid"] != os.getpid() and receipt["main_thread"] is True
        assert receipt["native_thread_limit"] == 1
        assert len(actual.outputs[0].members) == len(body["members"])
        assert cpu._capsule_bytes == 0
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0


def test_actual_contextual_kernel_uses_same_retained_symbols_and_no_schema_capsule(acquired):
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.construction_products import PreparedConstructionProfile
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope

    _, _, prepared, model, formal = acquired
    source = selected(formal, "All samples are finite.")
    primary = formal.run(
        source, FormalEvidenceOptions(), subject_context=_publication_context(source)
    )
    symbolic = PreparedConstructionProfile(prepared, model).run(
        source, (primary,), subject_context=_publication_context(source)
    )
    port = admitted(acquired, "text.contextual_evaluation/source-native", resolve_contextual_port)
    inputs = values(port, source=source.value, formal=(primary,), constructions=(symbolic,))
    expected = port.invoke_python(inputs)
    cpu = CPUExecutionScope(
        prepared,
        CharacterizationExecutionPolicy(
            workers=1, max_submissions=1, max_packet_bytes=8 * 1024**2, max_reply_bytes=8 * 1024**2
        ),
        retain_schema=False,
    )
    try:
        actual = drive_prepared_work(
            port.plan_python(inputs, execution_owner=SimpleNamespace(cpu=cpu, reservation=None)),
            lambda: None,
        )
        assert actual.outputs[0].content == expected.outputs[0].content
        assert json.loads(actual.cpu_execution_evidence)["pid"] != os.getpid()
        assert cpu._capsule_bytes == 0
    finally:
        cpu.close()


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


def test_retained_family_ingress_uses_selected_member_context_and_checks_native_id(acquired):
    from dataclasses import replace
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_ports import PortRefusal

    _, _, _, _, formal = acquired
    source = selected(formal, "All samples are finite.")
    context = _publication_context(source)
    original = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    port = admitted(acquired, "text.constructions/source-native", resolve_construction_port)
    member = SimpleNamespace(
        product=original.semantic_id,
        subject=context.subject,
        original_source=context.original_source,
        analyzed_scope=context.analyzed_scope,
        member=None,
        multiplicity=1,
    )
    binding = SimpleNamespace(
        subject_context=context, roles=(SimpleNamespace(role="formal", members=(member,)),)
    )
    unbound = replace(original, subject_context=None)
    restored = port._selected_product(unbound, binding, "formal", 0)
    assert restored.content == original.content
    assert restored.subject_context == context
    assert restored.semantic_id == member.product
    other_project = SimpleNamespace(
        subject_context=replace(context, project_id="another-project"), roles=binding.roles
    )
    with pytest.raises(PortRefusal, match="selected native product identity"):
        port._selected_product(unbound, other_project, "formal", 0)
