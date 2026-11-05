"""Evaluator-owned, bounded history capture for portable operation review.

This reader never switches principals. Development and explicitly authorized
feature-fit histories require committed exposure receipts. Calibration/final
partitions produce an inventory without authored material.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from sqlalchemy import Connection, text

from corpus_structure.evaluate.semantic import ReferenceError
from corpus_structure.semantic.identity import canonical_bytes


def iter_assessment_review_rows(
    conn: Connection,
    *,
    project_id: str,
    set_id: int,
    exposure_receipt_id: int | None = None,
    group: bool = False,
    max_rows: int = 100_000,
    max_bytes: int = 64 * 1024 * 1024,
) -> Iterator[dict[str, Any]]:
    """Capture exact history in caller-owned transaction, closing its cursor on failure.

    The caller must spool these rows before settling the snapshot. A partial
    iterator is never a successful complete review capture.
    """
    if max_rows < 1 or max_bytes < 1:
        raise ValueError("assessment capture bounds must be positive")
    used = 0
    function = "structural_review_history" if group else "operation_review_history"
    with conn.execute(
        text(f"SELECT row FROM eval.{function}(:project,:set_id,:receipt) AS row"),
        {"project": project_id, "set_id": set_id, "receipt": exposure_receipt_id},
        execution_options={"stream_results": True, "yield_per": 128},
    ) as result:
        for number, raw in enumerate(result.scalars(), 1):
            value: dict[str, Any] = dict(raw)
            value.update(project_id=project_id, set_id=set_id, group=group)
            if value.get("kind") == "pass":
                payload = value["value"]
                # PostgreSQL's base64 encoder inserts RFC2045 line breaks.
                encoded = "".join(payload["authored_base64"].split())
                authored = base64.b64decode(encoded, validate=True)
                if sha256(authored).hexdigest() != payload["content_digest"]:
                    raise ReferenceError("review authored bytes differ from immutable digest")
            used += len(canonical_bytes(value)) + 1
            if number > max_rows or used > max_bytes:
                raise ReferenceError("assessment review capture exceeds declared bounds")
            yield value


def record_review_exposure(
    conn: Connection,
    *,
    project_id: str,
    set_id: int,
    purpose: str,
    recipient_class: str,
    group: bool = False,
    authorization_basis: str | None = None,
) -> int:
    """Commit this receipt before delivering labels; a later export failure retains it."""
    if group and authorization_basis is not None:
        raise ValueError("group references are development-only")
    function = ("record_structural_review_exposure" if group else
                "record_feature_fit_review_exposure" if authorization_basis is not None else
                "record_review_exposure")
    arguments = ":project,:set_id,:purpose,:recipient" + (",:basis" if authorization_basis is not None else "")
    return conn.execute(
        text(f"SELECT eval.{function}({arguments})"),
        {"project": project_id, "set_id": set_id, "purpose": purpose,
         "recipient": recipient_class, "basis": authorization_basis},
    ).scalar_one()


@dataclass(frozen=True)
class AssessmentReviewSelection:
    project_id: str
    set_id: int
    exposure_receipt_id: int | None = None
    group: bool = False


def assessment_review_capture(selections: tuple[AssessmentReviewSelection, ...]):
    """Build the trusted evaluator callback accepted by the common bundle writer.

    Receipts must already be committed through record_review_exposure. The wire
    review request does not grant this capability or select an elevated engine.
    """
    if len({(s.project_id, s.set_id, s.group) for s in selections}) != len(selections):
        raise ValueError("assessment selection repeats a reference set")

    def capture(conn: Connection):
        def rows():
            for selection in selections:
                yield from iter_assessment_review_rows(
                    conn, project_id=selection.project_id, set_id=selection.set_id,
                    exposure_receipt_id=selection.exposure_receipt_id,
                    group=selection.group,
                )
        return {"assessment_history": rows()}

    return capture
