"""Actual CPU reply correspondence over controlled current extraction operands.

The source/input headers below are unadmitted scalar fixtures. Actual CPU replies
prove execution correspondence here; they do not fabricate native producer or
publication custody. Native guard journeys are owned by their captured kernel.
"""

import inspect
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import drive_prepared_work
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.cpu_execution import CPUExecutionScope
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
from corpus_structure.semantic.data_operation_cpu_basis import (
    cpu_authority_value,
    cpu_input_basis_from_binding,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BoundRoleMember,
    ExternalExecutorContract,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.external_extraction import (
    execute_rich_kernel,
    external_extraction_assets,
    external_extraction_operation_sources,
    rich_external_declarations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.proposals_support import batch
from semantic.test_external_rich_extraction import frame, packet
from semantic.test_external_rich_extraction import rich_bundle as rich_bundle


@pytest.fixture(scope="module")
def captured_rich(rich_bundle):
    from corpus_structure.semantic.declared_math_products import math_operation_declarations

    declarations = (
        math_operation_declarations(),
        rich_external_declarations(
            ExternalExecutorContract(
                "external-executor-v1",
                "Read selected packet and emit source reports.",
                "explicit-external-agent",
                "asserted-model",
                "declared-inputs-only",
            )
        ),
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), declarations, external_extraction_operation_sources()
    )
    prepared = prepare_release(rich_bundle, dependencies)
    return prepared, bound_data_operation_model(prepared)


def bound_inputs(model, operation, values, context):
    declarations = {
        role.name: role for role in model.operation(operation).roles if role.direction == "input"
    }
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    bodies, roles = {}, []
    for name, declaration in declarations.items():
        bodies[name] = (
            (values[name],) if declaration.collection == "scalar" else tuple(values[name])
        )
        roles.append(
            ResolvedRoleBinding(
                name,
                "present" if bodies[name] else "known-absent",
                tuple(
                    BoundRoleMember(
                        product="unadmitted:input:" + name + ":" + str(index),
                        member=None,
                        kind_contract=ids[declaration.kind],
                        subject=context.subject,
                        subject_definition=context.subject_definition,
                        original_source=context.original_source,
                        analyzed_scope=context.analyzed_scope,
                        coverage=b"{}",
                        support_episodes=(),
                        support_evidence=b"{}",
                        support_references=(),
                        position=index,
                    )
                    for index, _ in enumerate(bodies[name])
                ),
            )
        )
    binding = BindingResult(
        operation=operation,
        subject=context.subject,
        roles=tuple(roles),
        status="ready",
        reasons=(),
        parameters=canonical_bytes(semantic_value({})),
        choices=b"{}",
        model_version=MODEL_VERSION,
        definition="unadmitted:controlled-input-definition",
        eligibility="unadmitted:controlled-input-eligibility",
        admission_evidence=(),
        subject_context=context,
    replicate=None)
    recipe = next(
        item.key for item in model.identities if item.owner == operation and item.domain == "recipe"
    )
    return cpu_input_basis_from_binding(recipe, binding, bodies)


def locate_basis(model):
    actual = frame()
    raw = batch()
    raw["unit_ref"] = actual.unit_ref
    raw["statements"][0]["anchor"] = actual.unit_ref
    raw["claims"][0]["evidence"][0]["sentence"] = "native_evidence:1"
    context = SubjectContext(
        "project:one",
        "subject:one",
        "document:one",
        b"{}",
        subject_definition="original-source-view",
    )
    return bound_inputs(
        model, "locate.external_extraction", {"packet": packet(), "authored": raw}, context
    )


def prepare_basis(prepared, model, *, with_context=False):
    from corpus_structure.semantic.original_documents import original_document_subject
    from corpus_structure.semantic.sentence_products import (
        source_annotation_packets,
        spacy_family_coverage,
    )
    from corpus_structure.semantic.source_products import (
        FrozenNativeSource,
        native_projection_identity,
    )

    ancestors = [{"self_ref": "#/groups/parent", "label": "section_header"}] if with_context else []
    projection = native_projection_identity("", [], [], [], ancestors)
    source = FrozenNativeSource.acquire(
        prepared,
        {
            "source": {
                "document": "document:empty",
                "document_subject": original_document_subject("document:empty"),
                "projection": projection,
                "section_pointer": "#/groups/0",
                "membership": "descendants",
            },
            "text": "",
            "pieces": [],
            "items": [],
            "ancestors": ancestors,
            "recognition": [],
            "selectors": [{"projection": projection}],
        },
    ).value
    annotations = dict(
        source=source["source"],
        selectors=source["selectors"],
        outcome="complete",
        block_coverage=[],
        coverage=spacy_family_coverage(source, [], []),
        blocks=[],
        configuration=SentenceConfig().model_dump(mode="json"),
        execution_profile="unadmitted:empty-scalar-profile",
    )
    annotations["members"] = source_annotation_packets(prepared, model, annotations)
    policy = {
        "version": "external-extraction-policy-1",
        "guideline": "Read the actual empty source.",
        "known_reference_standing": "authored",
        "known_classes": source_value({}),
        "known_entities": [],
        "bootstrap_terms": [],
        "macros": source_value({}),
        "context_sources": [],
        "scope_standing": "explicitly-none",
    }
    context = SubjectContext(
        "project:one",
        "subject:empty",
        "document:empty",
        json_bytes({"source": source["source"], "selectors": source["selectors"]}),
        subject_definition="original-source-view",
    )
    contexts, context_annotations = (), ()
    if with_context:
        parent = deepcopy(source)
        parent["ancestors"] = []
        parent["source"].update(
            section_pointer="#/groups/parent",
            membership="direct",
            projection=native_projection_identity("", [], [], []),
        )
        parent["selectors"] = [{"projection": parent["source"]["projection"]}]
        parent = FrozenNativeSource.acquire(prepared, parent).value
        parent_annotations = deepcopy(annotations)
        parent_annotations.update(
            source=parent["source"],
            selectors=parent["selectors"],
            coverage=spacy_family_coverage(parent, [], []),
        )
        parent_annotations["members"] = source_annotation_packets(
            prepared, model, parent_annotations
        )
        contexts, context_annotations = (parent,), (parent_annotations,)
        policy["context_sources"] = ['["unadmitted:input:context_sources:0",null]']
    return bound_inputs(
        model,
        "prepare.external_extraction",
        {
            "source": source,
            "annotations": annotations,
            "policy": policy,
            "context_sources": contexts,
            "context_annotations": context_annotations,
            "scopes": (),
        },
        context,
    )


@pytest.fixture(scope="module")
def actual_extraction_replies(captured_rich):
    prepared, model = captured_rich
    sources = external_extraction_operation_sources()
    asset = external_extraction_assets().content.decode()
    signature = inspect.signature(execute_rich_kernel, eval_str=True)
    replies = {}
    cpu = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1, max_submissions=1))
    try:
        descriptor = PythonCPUDescriptor(
            tuple((source.module, source.filename, source.content) for source in sources.sources),
            "corpus_structure.semantic.external_extraction.execute_rich_kernel",
            (),
            verification="prepared-kernel",
            control_parameter="check_active",
            prepared_parameter="prepared",
            prepared_release_id=prepared.release_id,
        )
        for action, basis in (
            ("prepare.external_extraction", prepare_basis(prepared, model)),
            ("locate.external_extraction", locate_basis(model)),
        ):
            bound = signature.bind(
                action=action,
                input_basis=basis,
                asset_content=asset,
                prepared=prepared,
                check_active=lambda: None,
            )
            packet_digest = sha256(descriptor.packet(bound.arguments, signature)).hexdigest()
            reply = drive_prepared_work(
                plan_cpu_call(
                    descriptor,
                    bound,
                    signature,
                    verify=lambda: None,
                    execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                    check_active=lambda: None,
                ),
                lambda: None,
            )
            replies[action] = basis, reply, packet_digest
    finally:
        cpu.close()
    assert cpu.budget.used_bytes == 0
    return replies


def test_actual_prepare_reply_derives_source_pin_from_processed_header(actual_extraction_replies):
    basis, reply, packet_digest = actual_extraction_replies["prepare.external_extraction"]
    output = cpu_authority_value(reply.content, expected_basis=basis)
    assert reply.execution_receipt.result_digest == sha256(reply.content).hexdigest()
    assert reply.execution_receipt.request_digest == packet_digest
    assert output["source_pin"]["source_product"] == "unadmitted:input:source:0"
    assert output["source_pin"]["source"] == '["unadmitted:input:source:0",null]'
    assert output["source_pin"]["subject"] == "subject:empty"
    assert output["source_pin"]["original_source"] == "document:empty"
    assert output["source_pin"]["project_id"] == "project:one"
    assert output["scope_standing"] == "explicitly-none"


def test_actual_locate_reply_retains_placement_and_exact_input_basis(actual_extraction_replies):
    basis, reply, packet_digest = actual_extraction_replies["locate.external_extraction"]
    output = cpu_authority_value(reply.content, expected_basis=basis)
    assert reply.execution_receipt.result_digest == sha256(reply.content).hexdigest()
    assert reply.execution_receipt.request_digest == packet_digest
    claim = next(
        row["body"] for row in output["members"] if row["body"]["proposal_type"] == "claim"
    )
    assert (claim["evidence"][0]["start"], claim["evidence"][0]["end"]) == (15, 29)
    assert claim["evidence"][0]["outcome"] == "located"
    assert output["standing"] == "private_proposed"
    changed = decode_semantic_value(basis)
    next(row for row in changed["roles"] if row["role"] == "packet")["product_id"] = (
        "unadmitted:different-selected-packet"
    )
    with pytest.raises(ValueError, match="processed input basis"):
        cpu_authority_value(reply.content, expected_basis=semantic_value(changed))


def test_child_refuses_changed_policy_bytes_under_unchanged_basis(captured_rich):
    prepared, model = captured_rich
    from corpus_structure.semantic.data_operation_json import wire_json_loads

    asset = wire_json_loads(external_extraction_assets().content)
    asset["placement_policy"]["token_cutoff"] += 1
    with pytest.raises(ValueError, match="actual captured asset"):
        execute_rich_kernel(
            "locate.external_extraction",
            locate_basis(model),
            canonical_bytes(asset).decode(),
            prepared=prepared,
            check_active=lambda: None,
        )


def test_child_refuses_other_recipe_and_wrong_source_context(captured_rich):
    prepared, model = captured_rich
    asset = external_extraction_assets().content.decode()
    basis = decode_semantic_value(locate_basis(model))
    basis["recipe"] = "unadmitted:other-recipe"
    with pytest.raises(ValueError, match="actual admitted recipe"):
        execute_rich_kernel(
            "locate.external_extraction",
            semantic_value(basis),
            asset,
            prepared=prepared,
            check_active=lambda: None,
        )
    basis = decode_semantic_value(prepare_basis(prepared, model))
    next(row for row in basis["roles"] if row["role"] == "source")["context"]["original_source"] = (
        "document:other"
    )
    with pytest.raises(ValueError, match="bound original document"):
        execute_rich_kernel(
            "prepare.external_extraction",
            semantic_value(basis),
            asset,
            prepared=prepared,
            check_active=lambda: None,
        )


def test_child_preserves_actual_nondense_sequence_positions(captured_rich):
    prepared, model = captured_rich
    basis = decode_semantic_value(prepare_basis(prepared, model, with_context=True))
    next(row for row in basis["roles"] if row["role"] == "context_sources")["position"] = 7
    next(row for row in basis["roles"] if row["role"] == "context_annotations")["position"] = 12
    tagged = semantic_value(basis)
    reply = execute_rich_kernel(
        "prepare.external_extraction",
        tagged,
        external_extraction_assets().content.decode(),
        prepared=prepared,
        check_active=lambda: None,
    )
    output = cpu_authority_value(json_bytes(reply), expected_basis=tagged)
    from corpus_structure.semantic.observations import source_python

    frame_value = source_python(output["frame"])
    from corpus_structure.semantic.data_operation_json import wire_json_loads

    context_pin = wire_json_loads(frame_value["context_sources"][0]["pin_content"])
    assert context_pin["source_product"] == "unadmitted:input:context_sources:0"
    assert context_pin["section_pointer"] == "#/groups/parent"
    assert context_pin["membership"] == "direct"
