"""Processed contextual input correspondence; controlled models are not provider evidence."""

import inspect
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from corpus_structure.core.work import drive_prepared_work
from corpus_structure.semantic.contextual_cpu import execute_contextual_projection_kernel
from corpus_structure.semantic.contextual_encoder_batch import encoder_packet, execute_encoder_batch
from corpus_structure.semantic.contextual_operations import contextual_operation_sources
from corpus_structure.semantic.contextual_target_products import curated_target_population
from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
from corpus_structure.semantic.data_operation_cpu_basis import (
    CPUInputRole,
    cpu_authority_batch_values,
    cpu_authority_value,
    cpu_input_basis,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from semantic.controlled_encoder_support import controlled_encoder_producer
from semantic.data_operation_port_support import scope
from semantic.test_contextual_target_vectors import controlled_model, profile


def basis(context, role, body):
    return cpu_input_basis(
        "controlled-contextual-inputs",
        context,
        (
            CPUInputRole(
                role,
                0,
                1,
                "controlled-input",
                None,
                "controlled-kind",
                context,
                body,
                (),
                producer_output=None,
            ),
        ),
        parameters=canonical_bytes(semantic_value({})),
        replicate=None,
    )


def test_curated_projection_runs_on_actual_owned_cpu_and_keeps_project_origin():
    context = SubjectContext(
        "project", "contextual-registry", None, b"{}", subject_definition="knowledge-universe"
    )
    selected = dict(
        targets=source_value([dict(target_id="one", label="alpha", description="Meaning one")])
    )
    processed = basis(context, "selection", selected)
    kernel = execute_contextual_projection_kernel
    signature = inspect.signature(kernel)
    bound = signature.bind(
        input_basis=processed,
        operation="retrieve.contextual_targets/curated",
        member_contract="controlled-member",
        check_active=lambda: None,
    )
    sources = contextual_operation_sources()
    descriptor = PythonCPUDescriptor(
        tuple((source.module, source.filename, source.content) for source in sources.sources),
        kernel.__module__ + "." + kernel.__name__,
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
    )
    cpu = scope()
    try:
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
        result = cpu_authority_value(reply.content, expected_basis=processed)
        assert reply.execution_receipt.result_digest
        assert result["members"][0]["body"]["original_source"] is None
        assert result["members"][0]["context"]["original_source"] is None
        changed = semantic_value(
            dict(
                version="cpu-input-basis-3",
                recipe="controlled-contextual-inputs",
                context=context.identity_record,
                roles=[],
                parameters={"selection": "different"},
                replicate=None,
            )
        )
        with pytest.raises(ValueError, match="processed input basis"):
            cpu_authority_value(reply.content, expected_basis=changed)
    finally:
        cpu.close()


def test_target_authority_uses_processed_target_and_refuses_query_origin(monkeypatch):
    controlled_model(monkeypatch)
    packet = curated_target_population(
        dict(
            targets=source_value([dict(target_id="one", label="alpha", description="Meaning one")])
        ),
        kind_contract="controlled-member",
    )["members"][0]
    raw = packet["context"]
    context = SubjectContext(
        "project",
        raw["subject"],
        None,
        json_bytes(raw["analyzed_scope"]),
        subject_definition="contextual-target",
    )
    processed = basis(context, "target", packet["body"])
    members = (
        dict(
            member="controlled-target",
            producer=controlled_encoder_producer(0),
            input_basis=processed,
        ),
    )
    result = execute_encoder_batch(
        encoder_packet(members, "retrieve.contextual_target_vector/declared"),
        asdict(profile()),
        "",
        (),
        check_active=lambda: None,
    )
    (decoded,) = cpu_authority_batch_values(canonical_bytes(result), expected_members=members)
    assert canonical_bytes(decoded["target"]) == canonical_bytes(packet["body"])
    assert decoded["vector"]["object_id"] == "one"
    wrong = SubjectContext(
        "project",
        raw["subject"],
        "query-document",
        context.analyzed_scope,
        subject_definition="contextual-target",
    )
    wrong_members = (dict(members[0], input_basis=basis(wrong, "target", packet["body"])),)
    refused = execute_encoder_batch(
        encoder_packet(wrong_members, "retrieve.contextual_target_vector/declared"),
        asdict(profile()),
        "",
        (),
        check_active=lambda: None,
    )
    (failed,) = cpu_authority_batch_values(canonical_bytes(refused), expected_members=wrong_members)
    assert failed["encoder_member_failure"]["code"] == "source-coordinate-mismatch"
    assert "exact discovered context" in failed["encoder_member_failure"]["detail"]


@pytest.mark.parametrize(
    "recipe", ["located-frame-2", "located-referent-2", "located-discourse-neighbor-2"]
)
def test_query_authority_rebuilds_actual_selected_primary_context(recipe, monkeypatch):
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from semantic.selected_context_support import case
    from semantic.test_contextual_encoder_batch import _query_members

    frame, occurrence, _, _, _, expected = case(recipe)
    calls = controlled_model(monkeypatch)
    members, packet = _query_members(selected=True, recipe=recipe)
    reply = execute_encoder_batch(packet, asdict(profile()), "", (), check_active=lambda: None)
    result = cpu_authority_batch_values(canonical_bytes(reply), expected_members=members)[0]
    assert result["query"]["carrier"]["product_id"] == "controlled-occurrence"
    assert result["query"]["carrier"]["contribution_id"] == occurrence["contribution_id"]
    assert result["query"]["context"]["rendered"] == expected
    assert result["query"]["context_inputs"][0]["product_id"] == "product:primary"

    foreign_members = deepcopy(members)
    foreign = decode_semantic_value(foreign_members[0]["input_basis"])
    foreign["context"]["subject"] = "another-consumer"
    foreign_members[0]["input_basis"] = semantic_value(foreign)
    refused = execute_encoder_batch(
        encoder_packet(foreign_members, "retrieve.contextual_query/selected-context"),
        asdict(profile()),
        "",
        (),
        check_active=lambda: None,
    )
    values = cpu_authority_batch_values(canonical_bytes(refused), expected_members=foreign_members)
    assert values[0]["encoder_member_failure"]["code"] == "source-coordinate-mismatch"
    assert "selected source/context" in values[0]["encoder_member_failure"]["detail"]
    assert values[1]["query"]["context"]["rendered"] == expected

    wrong = deepcopy(packet)
    record = next(iter(wrong["frames"].values()))
    pin = frame.pin.values()
    wrong_pin = dict(pin, source_member="another-member")
    wrong_pin["source"] = canonical_bytes([pin["source_product"], "another-member"]).decode()
    record["pin"] = semantic_value(wrong_pin)
    before = len(calls)
    with pytest.raises(ValueError, match="encoder packet source frame changed"):
        execute_encoder_batch(wrong, asdict(profile()), "", (), check_active=lambda: None)
    assert len(calls) == before


def test_retrieval_reduction_uses_owned_cpu_with_exact_controlled_score_input():
    """The CPU execution is actual; controlled scores do not claim native admission."""
    from corpus_structure.semantic.contextual_numerics import default_retrieval_numerics
    from corpus_structure.semantic.contextual_scores import execute_contextual_retrieval_kernel
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.observations import source_python
    from semantic.test_contextual_scores import controlled_scores

    values, _, scores = controlled_scores()
    context = SubjectContext(
        "project", "source", "original", b"{}", subject_definition="selected-native-source"
    )
    assert context.original_source is not None
    values["query"]["source_pin"].update(
        project_id=context.project_id,
        subject=context.subject,
        subject_definition="original-source-view",
        original_source=context.original_source,
        analyzed_scope_meaning=json_context_meaning(context.analyzed_scope).decode(),
    )
    values["scores"] = scores
    processed = cpu_input_basis(
        "controlled-reduction",
        context,
        tuple(
            CPUInputRole(
                name,
                0,
                1,
                "controlled:" + name,
                None,
                "controlled-kind:" + name,
                context,
                body,
                (),
                producer_output=None,
            )
            for name, body in values.items()
        ),
        parameters=canonical_bytes(semantic_value({})),
        replicate=None,
    )
    kernel = execute_contextual_retrieval_kernel
    signature = inspect.signature(kernel)
    bound = signature.bind(
        input_basis=processed,
        numerical_policy=default_retrieval_numerics().model_dump(mode="json"),
        witnessed=False,
        check_active=lambda: None,
    )
    sources = contextual_operation_sources()
    descriptor = PythonCPUDescriptor(
        tuple((source.module, source.filename, source.content) for source in sources.sources),
        kernel.__module__ + "." + kernel.__name__,
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
    )
    cpu = scope()
    try:
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
        actual = cpu_authority_value(reply.content, expected_basis=processed)
        assert actual["source_pin"]["subject_definition"] == "original-source-view"
        candidates = source_python(actual["candidate_list"])
        assert [row["target_id"] for row in candidates["candidates"]] == ["one", "two"]
        assert source_python(actual["relationship_decision"])["outcome"] == "insufficient_evidence"
        assert reply.execution_receipt.main_thread
    finally:
        cpu.close()
