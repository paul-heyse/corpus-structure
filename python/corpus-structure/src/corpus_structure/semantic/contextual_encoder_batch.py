"""Interned contextual encoder cohorts and independent authenticated member outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from corpus_structure.methods.contextual_embeddings import ContextInput

from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_json import json_bytes
from .identity import canonical_bytes

PACKET_VERSION = "contextual-encoder-packet-1"
MEMBER_FAILURE_VERSION = "contextual-encoder-member-failure-1"
MEMBER_FAILURE_CODES = frozenset({
    "source-coordinate-mismatch", "selected-context-unavailable", "token-core-limit", "invalid-vector",
})


def _digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def _frame_record(source):
    from .data_operation_model import SubjectContext
    from .declared_record_sources import DeclaredRecordSource

    body = source["body"]
    coordinate = body["source"]
    context = source["context"]
    context = SubjectContext(
        context["project_id"], context["subject"], context["original_source"],
        json_bytes(context["analyzed_scope"]), subject_definition=context["subject_definition"],
    )
    pin = DeclaredRecordSource(
        coordinate["document"], coordinate["projection"], coordinate["section_pointer"],
        coordinate["membership"], context, source["product_id"], source["member_id"], source["kind_contract"],
    ).pin()
    return dict(body=_digest(semantic_value(body)), pin=semantic_value(pin), version=4)


def encoder_packet(members, operation):
    """Carry each role body once; frame references never carry another source body."""
    from .data_operation_cpu_basis import _batch_members

    bodies, frames, population = {}, {}, []
    for member in _batch_members(members):
        basis = decode_semantic_value(member["input_basis"])
        frame = None
        for row in basis["roles"]:
            body = semantic_value(row["body"])
            digest = _digest(body)
            bodies.setdefault(digest, body)
            if row["role"] == "source":
                record = _frame_record(row)
                frame = _digest(record)
                frames.setdefault(frame, record)
            row["body"] = dict(encoder_body=digest)
        population.append(dict(
            member=member["member"], producer=member["producer"],
            input_basis=semantic_value(basis), input_basis_digest=_digest(member["input_basis"]),
            frame=frame,
        ))
    return dict(version=PACKET_VERSION, operation=operation, bodies=bodies, frames=frames, members=population)


def unpack_encoder_packet(packet):
    """Authenticate the entire packet before any member or native model work."""
    from .data_operation_cpu_basis import _batch_members

    if (
        not isinstance(packet, dict) or set(packet) != {"version", "operation", "bodies", "frames", "members"}
        or packet["version"] != PACKET_VERSION
        or packet["operation"] not in {"retrieve.contextual_query/declared", "retrieve.contextual_query/selected-context", "retrieve.contextual_target_vector/declared"}
        or not isinstance(packet["bodies"], dict) or not isinstance(packet["frames"], dict)
        or not isinstance(packet["members"], list)
    ):
        raise ValueError("encoder packet differs from its current finite contract")
    for digest, body in packet["bodies"].items():
        if _digest(body) != digest:
            raise ValueError("encoder packet body digest changed")
    for digest, frame in packet["frames"].items():
        if (
            not isinstance(frame, dict) or set(frame) != {"body", "pin", "version"}
            or _digest(frame) != digest or frame["body"] not in packet["bodies"] or frame["version"] != 4
        ):
            raise ValueError("encoder packet source frame changed")
    members, used_bodies, used_frames = [], set(), set()
    for member in packet["members"]:
        if not isinstance(member, dict) or set(member) != {"member", "producer", "input_basis", "input_basis_digest", "frame"}:
            raise ValueError("encoder packet member contract changed")
        basis = decode_semantic_value(member["input_basis"])
        frame = None
        for row in basis["roles"]:
            reference = row["body"]
            if not isinstance(reference, dict) or set(reference) != {"encoder_body"} or reference["encoder_body"] not in packet["bodies"]:
                raise ValueError("encoder packet body reference changed")
            digest = reference["encoder_body"]
            used_bodies.add(digest)
            row["body"] = decode_semantic_value(packet["bodies"][digest])
            if row["role"] == "source":
                frame = _digest(_frame_record(row))
        restored = semantic_value(basis)
        if _digest(restored) != member["input_basis_digest"] or frame != member["frame"] or (frame is not None and frame not in packet["frames"]):
            raise ValueError("encoder packet member basis/frame correspondence changed")
        if frame is not None:
            used_frames.add(frame)
        members.append(dict(member=member["member"], producer=member["producer"], input_basis=restored))
    if used_bodies != packet["bodies"].keys() or used_frames != packet["frames"].keys():
        raise ValueError("encoder packet carries an unselected body or frame")
    return _batch_members(members)


def member_failure(code, error):
    if code not in MEMBER_FAILURE_CODES:
        raise ValueError("encoder member failure requires its finite semantic code")
    return dict(encoder_member_failure=dict(version=MEMBER_FAILURE_VERSION, code=code, detail=str(error)[:1024]))


def encoder_member_result(value):
    from .data_operation_prepared_call import PreparedCallResult

    if isinstance(value, dict) and "encoder_member_failure" in value:
        failure = value["encoder_member_failure"]
        if (
            set(value) != {"encoder_member_failure"} or not isinstance(failure, dict)
            or set(failure) != {"version", "code", "detail"} or failure["version"] != MEMBER_FAILURE_VERSION
            or type(failure["code"]) is not str or failure["code"] not in MEMBER_FAILURE_CODES or type(failure["detail"]) is not str
            or len(failure["detail"]) > 1024
        ):
            raise ValueError("encoder member failure slot differs from its declared contract")
        return PreparedCallResult(None, outcome="failed")
    return PreparedCallResult(value)


@dataclass(frozen=True)
class PreparedEncoderMember:
    position: int
    item: ContextInput
    metadata: dict


def prepare_encoder_members(packet, members, *, check_active=lambda: None):
    """Decode one prepared view per source; semantic refusals stay member-local."""
    from .contextual_encoder import SelectedQueryContextUnavailable, prepare_query_encoder_member, prepare_target_encoder_member
    from .data_operation_cpu_basis import cpu_basis_values
    from .declared_record_sources import DeclaredNativeFrameSource

    frames, prepared, failures = {}, [], {}
    for digest, record in packet["frames"].items():
        check_active()
        try:
            frames[digest] = DeclaredNativeFrameSource(
                json_bytes(decode_semantic_value(packet["bodies"][record["body"]])).decode(),
                json_bytes(decode_semantic_value(record["pin"])).decode(), record["version"],
            )
        except ValueError as error:
            frames[digest] = error
    for position, member in enumerate(members):
        check_active()
        if packet["operation"] == "retrieve.contextual_target_vector/declared":
            try:
                item, metadata = prepare_target_encoder_member(member["input_basis"])
            except ValueError as error:
                failures[position] = member_failure("source-coordinate-mismatch", error)
                continue
        else:
            frame = frames[packet["members"][position]["frame"]]
            if isinstance(frame, ValueError):
                failures[position] = member_failure("source-coordinate-mismatch", frame)
                continue
            try:
                roles, context = cpu_basis_values(member["input_basis"], scalar_roles=("source", "occurrence"), set_roles=(), sequence_roles=("primary",))
                source, occurrence = roles["source"][0], roles["occurrence"][0]
                from .contextual_cpu import checked_native_frame

                if source.context != context or occurrence.context != context or occurrence.body["pin"] != frame.pin.values():
                    raise ValueError("query carrier differs from its selected source/context")
                checked_native_frame(frame, source)
            except ValueError as error:
                failures[position] = member_failure("source-coordinate-mismatch", error)
                continue
            try:
                item, metadata = prepare_query_encoder_member(member["input_basis"], frame)
            except SelectedQueryContextUnavailable as error:
                failures[position] = member_failure("selected-context-unavailable", error)
                continue
            except ValueError as error:
                failures[position] = member_failure("source-coordinate-mismatch", error)
                continue
        prepared.append(PreparedEncoderMember(position, item, metadata))
    return tuple(prepared), failures


def execute_encoder_batch(packet, profile_record, model_path, artifacts, *, check_active):
    from corpus_structure.methods.contextual_embeddings import EncoderProfile, encode_contexts
    from pydantic import TypeAdapter

    from .contextual_encoder import finish_query_encoder_member, finish_target_encoder_member
    from .data_operation_cpu_basis import cpu_authority_batch_reply

    check_active()
    members = unpack_encoder_packet(packet)
    prepared, failures = prepare_encoder_members(packet, members, check_active=check_active)
    profile = TypeAdapter(EncoderProfile).validate_python(profile_record).bind_artifacts(artifacts)
    outputs = dict(failures)
    if prepared:
        encoded = encode_contexts(
            tuple(member.item for member in prepared), profile, model_path=model_path,
            artifact_hashes=artifacts, check_active=check_active, isolate_members=True,
        )
        for failure in encoded.member_failures:
            outputs[prepared[failure.position].position] = member_failure(failure.code, failure.detail)
        finish = finish_target_encoder_member if packet["operation"] == "retrieve.contextual_target_vector/declared" else finish_query_encoder_member
        for position, vector, rendered in zip(encoded.member_positions, encoded.vectors, encoded.inputs, strict=True):
            member = prepared[position]
            outputs[member.position] = finish(member.metadata, profile, vector, rendered)
    check_active()
    if outputs.keys() != set(range(len(members))):
        raise ValueError("encoder batch did not cover its exact logical population")
    return cpu_authority_batch_reply(members, (outputs[position] for position in range(len(members))))
