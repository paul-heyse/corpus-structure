"""Controlled encoder cohort and packet controls; no native/provider qualification."""

from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from corpus_structure.methods import contextual_embeddings as embeddings
from corpus_structure.semantic import contextual_encoder_batch as batch
from corpus_structure.semantic.contextual_encoder import checked_primary_query_rows
from corpus_structure.semantic.data_operation_cpu_basis import (
    CPUInputRole,
    cpu_authority_batch_values,
    cpu_input_basis,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.identity import canonical_bytes
from semantic.controlled_encoder_support import controlled_encoder, controlled_vector
from semantic.selected_context_support import case
from semantic.test_contextual_target_vectors import population


def _producer(index):
    return dict(
        request_id="controlled-request:" + str(index),
        generation=1,
        task_id=index + 1,
        attempt=1,
        holder="controlled-holder",
    )


def _query_members(*, selected=False, bad=None):
    frame, occurrence, primary, binding, evidence, _ = case("located-frame-2")
    pin = frame.pin.values()
    context = SubjectContext(
        pin["project_id"],
        pin["subject"],
        pin["original_source"],
        json_bytes(decode_semantic_value(json_loads(pin["analyzed_scope_meaning"]))),
        subject_definition=pin["subject_definition"],
    )
    result = []
    for index in range(2):
        value = deepcopy(occurrence)
        if index == 1 and bad == "pin":
            value["pin"]["source_member"] = "another-selected-member"
        parameters = {}
        if selected:
            reference = evidence.values()
            if index == 1 and bad == "context":
                reference = dict(reference, member_id="not-in-selected-parent")
            parameters = dict(context_selection=dict(recipe="located-frame-2", evidence=reference))
        roles = (
            CPUInputRole(
                "source",
                0,
                1,
                pin["source_product"],
                pin.get("source_member"),
                pin["kind_contract"],
                context,
                frame.value,
                (),
                producer_output=None,
            ),
            CPUInputRole(
                "occurrence",
                0,
                1,
                "controlled-occurrence",
                None,
                "controlled-occurrence-kind",
                context,
                value,
                (),
                producer_output=None,
            ),
            *(checked_primary_query_rows(primary, binding=binding) if selected else ()),
        )
        result.append(
            dict(
                member="controlled-member:" + str(index),
                producer=_producer(index),
                input_basis=cpu_input_basis(
                    "controlled-query-batch",
                    context,
                    roles,
                    parameters=canonical_bytes(semantic_value(parameters)),
                    replicate="controlled-sample:" + str(index),
                ),
            )
        )
    operation = (
        "retrieve.contextual_query/selected-context"
        if selected
        else "retrieve.contextual_query/declared"
    )
    return tuple(result), batch.encoder_packet(result, operation)


def _model(monkeypatch, *, invalid_vector=False, physical_error=False):
    calls = []

    model = controlled_encoder(
        lambda texts, options: calls.append(texts),
        invalid_vector=invalid_vector,
        physical_error=physical_error,
    )
    monkeypatch.setattr(
        embeddings, "_owned_cpu_encoder", lambda *args: (model, (("controlled", "1"),), ())
    )
    profile = embeddings.EncoderProfile(
        "controlled-batch", "a" * 40, 2, "query: ", "passage: ", "mean", max_tokens=4096
    )
    return profile, calls


@pytest.mark.parametrize("selected", [False, True])
def test_query_packet_interns_body_and_frame_and_preserves_duplicate_occurrence_observations(
    monkeypatch, selected
):
    members, packet = _query_members(selected=selected)
    profile, calls = _model(monkeypatch)
    assert len(packet["frames"]) == 1
    assert len(packet["bodies"]) == (3 if selected else 2)
    assert batch.unpack_encoder_packet(packet) == members
    from corpus_structure.semantic import declared_record_sources

    source_class = declared_record_sources.DeclaredNativeFrameSource
    initialize = source_class.__post_init__
    decoded = []

    def checked_frame(self):
        if type(self) is source_class:
            decoded.append(True)
        initialize(self)

    monkeypatch.setattr(source_class, "__post_init__", checked_frame)
    reply = batch.execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    values = cpu_authority_batch_values(canonical_bytes(reply), expected_members=members)
    assert len(decoded) == 1 and len(calls) == 1 and len(calls[0]) == 2
    assert len(values) == 2
    assert values[0]["query"]["carrier"] == values[1]["query"]["carrier"]
    assert values[0]["query"]["query_vector_id"] == values[1]["query"]["query_vector_id"]
    assert all(
        value["vector"]["vector"]["values"] == pytest.approx(controlled_vector(text))
        for value, text in zip(values, calls[0], strict=True)
    )


@pytest.mark.parametrize(
    "selected,bad,code",
    [
        (False, "pin", "source-coordinate-mismatch"),
        (True, "context", "selected-context-unavailable"),
    ],
)
def test_known_member_refusal_keeps_its_successful_sibling_and_exact_failure_slot(
    monkeypatch, selected, bad, code
):
    members, packet = _query_members(selected=selected, bad=bad)
    profile, calls = _model(monkeypatch)
    reply = batch.execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    values = cpu_authority_batch_values(canonical_bytes(reply), expected_members=members)
    assert "query" in values[0] and len(calls) == 1 and len(calls[0]) == 1
    assert values[1]["encoder_member_failure"]["code"] == code
    failed = batch.encoder_member_result(values[1])
    assert failed.value is None and failed.outcome == "failed"
    assert batch.encoder_member_result(values[0]).outcome is None


@pytest.mark.parametrize("tamper", ["body", "frame", "member-basis", "unselected-body"])
def test_packet_custody_refuses_whole_cohort_before_encoder(monkeypatch, tamper):
    _, packet = _query_members()
    profile, calls = _model(monkeypatch)
    packet = deepcopy(packet)
    if tamper == "body":
        key = next(iter(packet["bodies"]))
        packet["bodies"][key] = semantic_value({"changed": True})
    elif tamper == "frame":
        packet["members"][0]["frame"] = None
    elif tamper == "member-basis":
        basis = decode_semantic_value(packet["members"][0]["input_basis"])
        basis["replicate"] = "different-sample"
        packet["members"][0]["input_basis"] = semantic_value(basis)
    else:
        packet["bodies"][batch._digest(semantic_value("unselected"))] = semantic_value("unselected")
    with pytest.raises(ValueError, match="encoder packet"):
        batch.execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    assert calls == []


@pytest.mark.parametrize("drop_middle", [False, True])
def test_target_cohort_keeps_one_vector_per_target_without_query_source_custody(
    monkeypatch, drop_middle
):
    profile, calls = _model(monkeypatch)
    members = []
    for index, value in enumerate(population(("alpha", "beta", "gamma"))["members"]):
        context = SubjectContext(
            "controlled-project",
            value["context"]["subject"],
            None,
            json_bytes(value["context"]["analyzed_scope"]),
            subject_definition="contextual-target",
        )
        if drop_middle and index == 1:
            context = replace(context, subject="wrong-target-subject")
        basis = cpu_input_basis(
            "controlled-target-batch",
            context,
            (
                CPUInputRole(
                    "target",
                    0,
                    1,
                    "controlled-target:" + str(index),
                    None,
                    value["kind_contract"],
                    context,
                    value["body"],
                    (),
                    producer_output=None,
                ),
            ),
            parameters=canonical_bytes(semantic_value({})),
            replicate="controlled-target-observation",
        )
        members.append(dict(member=str(index), producer=_producer(index), input_basis=basis))
    packet = batch.encoder_packet(members, "retrieve.contextual_target_vector/declared")
    assert packet["frames"] == {}
    reply = batch.execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    values = cpu_authority_batch_values(canonical_bytes(reply), expected_members=members)
    if drop_middle:
        assert values[1]["encoder_member_failure"]["code"] == "source-coordinate-mismatch"
    survivors = [value for value in values if "encoder_member_failure" not in value]
    assert [value["vector"]["object_id"] for value in survivors] == (
        ["alpha", "gamma"] if drop_middle else ["alpha", "beta", "gamma"]
    )
    assert all(value["original_source"] is None for value in survivors)
    assert len(calls) == 1 and len(calls[0]) == len(survivors)
    for value, text in zip(survivors, calls[0], strict=True):
        assert value["vector"]["values"] == pytest.approx(controlled_vector(text))


def test_vector_admission_is_member_local_but_native_execution_fault_is_not(monkeypatch):
    members, packet = _query_members()
    profile, calls = _model(monkeypatch, invalid_vector=True)
    reply = batch.execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    values = cpu_authority_batch_values(canonical_bytes(reply), expected_members=members)
    assert "query" in values[0] and values[1]["encoder_member_failure"]["code"] == "invalid-vector"
    assert len(calls) == 1
    profile, calls = _model(monkeypatch, physical_error=True)
    with pytest.raises(RuntimeError, match="native model failure"):
        batch.execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    assert len(calls) == 1


def test_token_core_refusal_does_not_cut_or_poison_other_members(monkeypatch):
    profile, calls = _model(monkeypatch)
    profile = replace(profile, max_tokens=100)
    good = embeddings.ContextInput("good", "controlled", "query", "alpha", "alpha", 0, 5)
    bad = replace(
        good,
        object_id="bad",
        query_context="context " * 100,
        representation_digest="actual-context",
    )
    result = embeddings.encode_contexts((good, bad), profile, isolate_members=True)
    assert result.member_positions == (0,)
    assert [(value.position, value.code) for value in result.member_failures] == [
        (1, "token-core-limit")
    ]
    assert len(calls) == 1 and len(calls[0]) == 1


def test_policy_binds_exact_assets_padding_and_native_chunk_size():
    profile = embeddings.E5
    bound = profile.bind_artifacts((("weights", "a" * 64),))
    assert bound.profile_id != profile.profile_id
    assert bound.semantic_configuration["padding_side"] == "right"
    assert embeddings.QWEN.semantic_configuration["padding_side"] == "left"
    assert replace(bound, batch_size=bound.batch_size + 1).profile_id != bound.profile_id
    with pytest.raises(ValueError, match="artifact population"):
        bound.bind_artifacts((("weights", "b" * 64),))
    assert embeddings.ENCODER_NUMERICS.version == "cpu-encoder-numerics-v2"
    assert embeddings.ENCODER_NUMERICS.vector_identity == "cohort-independent"


def test_scalar_authority_reply_cannot_satisfy_encoder_batch_members():
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_reply

    members, _ = _query_members()
    scalar = cpu_authority_reply(members[0]["input_basis"], {"query": {}})
    with pytest.raises(ValueError, match="CPU batch reply"):
        cpu_authority_batch_values(canonical_bytes(scalar), expected_members=members)


@pytest.mark.parametrize("change", ["version", "code", "detail", "extra"])
def test_failed_member_cannot_expand_its_finite_outcome_contract(change):
    failure: dict[str, object] = dict(
        batch.member_failure("invalid-vector", "controlled invalid norm")["encoder_member_failure"]
    )
    value: dict[str, object] = {"encoder_member_failure": failure}
    if change == "version":
        failure["version"] = "historical"
    elif change == "code":
        failure["code"] = "worker-crash"
    elif change == "detail":
        failure["detail"] = 1
    else:
        value["extra"] = True
    with pytest.raises(ValueError, match="failure slot"):
        batch.encoder_member_result(value)
