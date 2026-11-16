"""A known D1 refusal is inspectable attempt evidence, never candidate standing."""

import json
from dataclasses import asdict
from hashlib import sha256

from .identity import canonical_bytes


class D1KnownLimitation(ValueError):
    """Owned typed diagnostic; ordinary exception strings cannot supply its payload."""

    def __init__(self, diagnostic: bytes, receipt: bytes):
        super().__init__("native D1 declined its exact frozen question inspection")
        self.diagnostic = diagnostic
        self.receipt = receipt

    def failure(self, *, fence, runtime_id):
        from .data_operation_execution_evidence import bind_execution_evidence
        from .data_operation_wire import validate_native_wire

        diagnostic = json.loads(self.diagnostic)
        diagnostic["execution_evidence"] = bind_execution_evidence(
            None, fence=fence, runtime_id=runtime_id, provider_content=self.receipt
        )
        failure = {
            "code": "d1-known-limitation",
            "message": "native D1 question inspection was limited",
            "d1_limitation": diagnostic,
        }
        # The same closed contract guards Python ingress and native retention/read.
        request = {**fence, "physical_retirement": "confirmed", "failure": failure}
        validate_native_wire("release_data_attempt", "input", request)
        return failure


def classify_d1_limitation(request, native, reply, *, pin, selection, member_index):
    """Recognize only the two actual preflight refusals of the qualified D1 owner.

    The provider lane already authenticated the physical exchange and scatter.
    Authenticate this exact member before retaining any diagnostic, including
    refusal replies which have no rendered state or model answer.
    """
    from corpus_structure.methods.model_observation import validate_pm2_batch_receipt

    if native.get("outcome") != "limited":
        return None
    if len(request.content) > 67108864:
        raise ValueError("D1 limitation request exceeds bounded diagnostic custody")
    payload = request.payload
    validate_pm2_batch_receipt(native.get("batch_receipt"), payload, "d1")
    reason = native.get("reason")
    required = {"outcome", "reason", "limit", "batch_receipt"}
    if reason == "question_count":
        valid = set(native) == required and native["limit"] == 16 and len(payload["questions"]) > 16
    elif reason == "packed_row_tokens":
        lengths = native.get("row_tokens")
        valid = (
            set(native) == required | {"row_tokens"}
            and native["limit"] == 4096
            and 1 <= len(payload["questions"]) <= 16
            and isinstance(lengths, list)
            and 1 <= len(lengths) <= 16
            and all(type(value) is int and value > 0 for value in lengths)
            and max(lengths) > 4096
        )
    else:
        valid = False
    if not valid or type(native.get("limit")) is not int:
        raise ValueError("D1 limitation differs from the qualified native refusal contract")
    receipt = reply.execution_receipt
    header = native["batch_receipt"]["header"]
    if (
        selection.provider != "d1"
        or request.family.provider != "d1"
        or payload["interpretation"]["assessed_scope"]["pin"] != pin
        or payload["interpretation"]["declaration_digest"] != request.family.digest
        or header["profile"] != sha256(selection.profile).hexdigest()
        or header["runtime"] != sha256(selection.runtime).hexdigest()
        or receipt is None
        or not receipt.physical
        or not receipt.logical_members
        or any(
            physical.provider != "d1"
            or physical.profile != selection.native.fingerprint
            or physical.runtime != header["runtime"]
            for physical in receipt.physical
        )
    ):
        raise ValueError("D1 limitation lacks its exact source/profile/physical correspondence")
    from corpus_structure.methods.native_host import payload_digest

    member_digest = payload_digest(payload)
    if (
        type(member_index) is not int
        or not 0 <= member_index < len(receipt.native_member_digests)
        or receipt.native_member_digests[member_index] != member_digest
        or member_digest != sha256(request.content).hexdigest()
        or native["batch_receipt"]["member_ordinal"] != receipt.member_offset + member_index
        or tuple(native["batch_receipt"]["members"]) != receipt.cohort_members
    ):
        raise ValueError("D1 limitation is absent from its actual provider work")
    diagnostic = {
        "version": "d1-known-limitation-v1",
        "source_pin": pin,
        "family": request.family.family,
        "stage": request.stage,
        "request_json": request.content.decode("utf-8"),
        "request_digest": sha256(request.content).hexdigest(),
        "profile_digest": selection.native.fingerprint,
        "native_reply": native,
        "inspected_count": 0,
        "emitted_count": 0,
        "standing": "unperformed-question-inspection",
    }
    # No semantic observation/candidate output is returned by this exception path.
    return D1KnownLimitation(canonical_bytes(diagnostic), canonical_bytes([asdict(receipt)]))


def known_d1_failure(error, *, fence, runtime_id):
    """Select only this attempt's diagnostic, including an enclosing batch error."""
    if isinstance(error, BaseExceptionGroup):
        values = [
            value
            for child in error.exceptions
            if (value := known_d1_failure(child, fence=fence, runtime_id=runtime_id)) is not None
        ]
        if len(values) > 1:
            raise ValueError("one attempt has multiple ambiguous D1 limitation diagnostics")
        return values[0] if values else None
    if not isinstance(error, D1KnownLimitation):
        return None
    receipt = json.loads(error.receipt)
    claim = {name: fence[name] for name in ("request_id", "generation", "task_id", "attempt")}
    if any(
        {name: member[name] for name in claim} != claim
        for row in receipt
        for member in row["logical_members"]
    ):
        return None
    return error.failure(fence=fence, runtime_id=runtime_id)
