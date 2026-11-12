"""Complete a private PM2 observation under the existing maintained source claim."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from corpus_structure.core.method import UnitRef
from corpus_structure.methods.pm2_products import PARSER_QUESTIONS
from corpus_structure.methods.pm2_result import (
    pm2_input_digest,
    pm2_unit_result,
    projects_completed_empty_d1,
)
from corpus_structure.methods.pm2_source import D1SourceField, PM2SourceMap, PM2TokenMap
from corpus_structure.methods.pm2_worker import Pm2WorkerError
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict, complete_unit_result

if TYPE_CHECKING:
    from corpus_structure.core.method import Method
    from corpus_structure.methods.pm2_gliner_classification import ClassificationWorker
    from corpus_structure.methods.native_host_clients import HostedPM2
    from corpus_structure.semantic._operation_calls import ClaimedTask
    from corpus_structure.semantic.claim_lifetime import ClaimOwner
    from corpus_structure.semantic.operations import OperationDescriptor
    from corpus_structure.semantic.types import PreparedRelease


def settle_pm2_claim(
    owner: ClaimOwner,
    claim: ClaimedTask,
    worker: HostedPM2 | ClassificationWorker | None,
    mapping: PM2SourceMap | PM2TokenMap,
    request: dict[str, Any],
    *,
    expected_profile: Mapping[str, Any],
    question: str,
    operation_version: str,
    prepared: PreparedRelease,
    method: Method[Any] | OperationDescriptor,
    configuration_hash: str,
    source_path: str | None = None,
    startup_error: str | None = None,
    prefetched_reply: dict[str, Any] | None = None,
):
    """Score outside a transaction, then settle through the caller's exact claim owner."""
    owner()
    task = table("ops.task")
    with owner.engine.connect() as conn:
        admitted = conn.scalar(
            select(task.c.input_hash).where(
                task.c.id == claim.task_id,
                task.c.status == "running",
                task.c.attempt == claim.attempt,
                task.c.claimed_by == claim.holder,
                task.c.lease_until > func.clock_timestamp(),
            )
        )
    if admitted is None:
        raise OperationConflict("PM2 claim attempt lost before inference")
    if (
        (worker is not None and worker.startup != expected_profile)
        or admitted
        != pm2_input_digest(
            mapping,
            expected_profile,
            request,
            question=question,
            operation_version=operation_version,
            source_path=source_path,
        )
        or claim.release_id != prepared.release_id
    ):
        raise OperationConflict("PM2 runtime, input or release differs from the admitted claim")
    ref = UnitRef(claim.unit_type, claim.unit_id, claim.unit_key)
    if prefetched_reply is not None:
        if worker is None:
            raise ValueError("prefetched PM2 result requires the admitted live worker")
        reply = prefetched_reply
    elif worker is None:
        if startup_error is None:
            raise ValueError("PM2 startup failure requires a diagnostic")
        reply = {"outcome": "failed", "reason": startup_error}
    else:
        try:
            reply = worker.infer(request, check_active=owner)
        except Pm2WorkerError as exc:
            owner()
            reply = {"outcome": "failed", "reason": str(exc)}

    def completed_product(reply):
        return reply.get("outcome") == "succeeded" or projects_completed_empty_d1(
            str(expected_profile["provider"]), operation_version, request, reply
        )

    def bind(reply):
        field = None
        if source_path is not None and completed_product(reply):
            ((start, end, _),) = (row for row in reply["state_fields"] if row[2] == source_path)
            if type(start) is not int or type(end) is not int:
                raise ValueError("d1 returned noninteger rendered source bounds")
            field = D1SourceField(reply["rendered_state"], source_path, start, end)
        return pm2_unit_result(
            ref,
            mapping,
            profile=expected_profile,
            request=request,
            reply=reply,
            field=field,
            question=question,
            operation_version=operation_version,
            input_digest=admitted,
            source_path=source_path,
            prepared=prepared,
        )

    try:
        result = bind(reply)
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        handles_product = (
            question in PARSER_QUESTIONS.values()
            or "interpretation" in request
            or expected_profile["provider"] == "gliner"
        )
        if not handles_product or not completed_product(reply):
            raise
        result = bind(
            {
                "outcome": "failed",
                "reason": f"invalid native PM2 product: {exc}",
                "rejected_reply": reply,
            }
        )
    return owner.settle(
        claim,
        lambda conn: complete_unit_result(
            conn,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=claim.holder,
            prepared=prepared,
            method=method,
            configuration_hash=configuration_hash,
            source=claim.unit_key or "",
            result=result,
        ),
    )
