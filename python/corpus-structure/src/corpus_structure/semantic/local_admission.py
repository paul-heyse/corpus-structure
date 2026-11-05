"""Exact local source claims through the common atomic publication owner.

An admitted quotation says what source pieces contain, never that a proposed role,
attachment, identity or scientific proposition is correct. Sealed source custody
supplies the deterministic proof; independent semantic judgment is not implemented
by this policy. Native publication recomputes these rows from the exact final cut.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Literal

from .identity import canonical_bytes

POLICY_ID = "exact-source-local-1"
POLICY_VERSION = "1"
BASIS = "deterministic_native_source_coordinates"
EVENTS = frozenset({"source_occurrence", "source_literal_quote"})


@dataclass(frozen=True)
class LocalAssertionRow:
    assertion_id: str
    claim_id: str
    selected_task_id: int
    origin_task_id: int
    cut_id: int
    contribution_id: str
    operation_key: str
    operation_version: str
    event: Literal["source_occurrence", "source_literal_quote"]
    policy_id: str
    policy_version: str
    basis: str
    source: str
    occurrence_id: str
    anchors_json: str
    literal_pieces_json: str


def assertion_identity(values: Mapping[str, Any]) -> str:
    return "local-assertion:" + sha256(canonical_bytes(values)).hexdigest()


def claim_identity(event: str, occurrence_id: str, pieces: Sequence[str]) -> str:
    """Physical claim grain excludes overlapping windows and producer observations."""
    return (
        "local-source-claim:" + sha256(canonical_bytes([event, occurrence_id, pieces])).hexdigest()
    )


def exact_source_event(
    contribution: Mapping[str, Any],
) -> Literal["source_occurrence", "source_literal_quote"] | None:
    """Select only physical extents with nonempty exact native source quotations."""
    anchors = contribution.get("anchors", ())
    if (
        contribution.get("kind") not in {"occurrence", "proposal"}
        or not contribution.get("occurrence_id")
        or contribution.get("anchor_role") == "inspection_subject"
        or not anchors
        or any(
            anchor.get("space") != "native"
            or anchor.get("precision") != "exact"
            or type(anchor.get("start")) is not int
            or type(anchor.get("end")) is not int
            or not 0 <= anchor["start"] < anchor["end"]
            or not isinstance(anchor.get("source_piece"), str)
            or len(anchor["source_piece"]) != anchor["end"] - anchor["start"]
            for anchor in anchors
        )
    ):
        return None
    return "source_occurrence" if contribution["kind"] == "occurrence" else "source_literal_quote"


def project_local_assertions(
    prepared, reports: Sequence[Mapping[str, Any]]
) -> tuple[LocalAssertionRow, ...]:
    """Prepare exact event rows without acquiring publication locks or model workers.

    Each report binds selected/origin task IDs, cut, source, contribution operations
    and contributions. This preparation grants no authority: the native publisher
    authenticates the complete staged row against immutable source products.
    """
    if "LocalContributionPublicationPolicy" not in prepared.index.definitions:
        return ()
    output = {}
    for report in reports:
        operations = {op["operation_key"]: op for op in report.get("contribution_operations", ())}
        for contribution in report.get("contributions", ()):
            event = exact_source_event(contribution)
            if event is None:
                continue
            operation = operations.get(contribution["operation_key"])
            if operation is None:
                raise ValueError("local assertion has no source operation")
            prepared.validate_python(
                "LocalContributionPublicationPolicy",
                dict(
                    policy_id=POLICY_ID,
                    policy_version=POLICY_VERSION,
                    event=event,
                    basis=BASIS,
                ),
            )
            anchors = contribution["anchors"]
            values = dict(
                claim_id=claim_identity(
                    event,
                    contribution["occurrence_id"],
                    [anchor["source_piece"] for anchor in anchors],
                ),
                selected_task_id=report["selected_task_id"],
                origin_task_id=report["origin_task_id"],
                cut_id=report["cut_id"],
                contribution_id=contribution["contribution_id"],
                operation_key=operation["operation_key"],
                operation_version=operation["operation_version"],
                event=event,
                policy_id=POLICY_ID,
                policy_version=POLICY_VERSION,
                basis=BASIS,
                source=report["source"],
                occurrence_id=contribution["occurrence_id"],
                anchors_json=canonical_bytes(anchors).decode(),
                literal_pieces_json=canonical_bytes(
                    [anchor["source_piece"] for anchor in anchors]
                ).decode(),
            )
            identity = assertion_identity(values)
            output[identity] = LocalAssertionRow(assertion_id=identity, **values)
    return tuple(output[key] for key in sorted(output))


def local_assertion_facets(values: Mapping[str, Any]) -> dict[str, Any]:
    """Summary standing does not require transferring or decoding evidence bodies."""
    return dict(
        **{
            key: value
            for key, value in values.items()
            if key not in {"anchors_json", "literal_pieces_json"}
        },
        standing="admitted_local_source_claim",
        assessment="not_included",
        interpretation="not_established_by_local_publication",
        scientific_support="unmodeled",
        source_fidelity="authenticated_captured_native_text_only",
        original_pdf_glyph_fidelity="not_established_by_local_publication",
    )


def local_assertion_support(row: LocalAssertionRow) -> dict[str, Any]:
    import json

    return dict(
        **local_assertion_facets(asdict(row)),
        anchors=json.loads(row.anchors_json),
        literal_pieces=json.loads(row.literal_pieces_json),
    )
