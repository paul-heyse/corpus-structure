"""Released, source-preserving private interpretations; lexical matches are candidates."""

from __future__ import annotations

import unicodedata
from typing import Any

from .identity import canonical_bytes
from .terminology import ARTIFACT

FIELD_ENUMS = {
    "distribution_family": "StatisticalDistributionFamily",
    "distribution_attribute": "StatisticalDistributionAttribute",
}
SEMANTIC_TYPES = {"terminology.interpretation", "measurement.interpretation"}
MAPPINGS = frozenset(
    "http://www.w3.org/2004/02/skos/core#" + k
    for k in ("exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch")
)
LOOKUP_POLICY = "released-lexical-1"


def normalize_term(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def metadata_binding(prepared) -> tuple[str, dict]:
    metadata = prepared.vocabulary_metadata
    if metadata["status"] != "available":
        raise ValueError("vocabulary metadata is unavailable or corrupt")
    artifact = next(a for a in prepared.artifacts if a.kind == ARTIFACT)
    return artifact.digest, metadata


def lookup_terms(prepared, field: str, query: str | None = None, *, browse=False) -> dict:
    """Examine only released members. Explicit browsing is not a lexical match."""
    if field not in FIELD_ENUMS or type(browse) is not bool:
        raise ValueError("unknown terminology field or browse mode")
    if browse == (query is not None):
        raise ValueError("supply either a query or explicit browse mode")
    digest, metadata = metadata_binding(prepared)
    members = metadata["enums"][FIELD_ENUMS[field]]["members"]
    result = []
    for member in members:
        forms = [("value", member["value"], ""), ("label", member.get("label") or "", "")]
        forms += [("synonym", s["value"], s["predicate"]) for s in member.get("synonyms", ())]
        matches = (
            [("browse", "", "")]
            if browse
            else [f for f in forms if normalize_term(f[1]) == normalize_term(query or "")]
        )
        for kind, _, predicate in matches:
            result.append(
                dict(
                    value=member["value"],
                    meaning=member["meaning"],
                    label=member.get("label") or member["value"],
                    matching_field=kind,
                    matching_predicate=predicate,
                )
            )
    # Multiple matched fields remain evidence; one candidate per released member has a
    # deterministic first reason, never a confidence or equivalence score.
    distinct = {r["value"]: r for r in reversed(result)}
    return dict(
        release_id=prepared.release_id,
        metadata_digest=digest,
        field=field,
        policy=LOOKUP_POLICY,
        query=query,
        browse=browse,
        examined=len(members),
        candidates=[distinct[k] for k in sorted(distinct)],
        complete=True,
    )


def validate_interpretation_payload(prepared, semantic_type: str, payload: dict[str, Any]) -> None:
    """Semantic closure after released shape validation; native completion adds source custody."""
    if semantic_type not in SEMANTIC_TYPES:
        return
    digest, metadata = metadata_binding(prepared)
    if payload["vocabulary_release"] != prepared.release_id or payload["metadata_digest"] != digest:
        raise ValueError("interpretation vocabulary differs from its released metadata")
    if semantic_type == "measurement.interpretation":
        if payload["outcome"] == "selected":
            if not payload.get("unit") or not payload.get("quantity_kind"):
                raise ValueError("selected measurement requires unit and quantity kind")
        elif payload.get("unit") is not None or payload.get("quantity_kind") is not None:
            raise ValueError("unresolved measurement cannot claim selected identifiers")
        if (payload["basis_status"] == "identified") != bool(payload.get("basis")):
            raise ValueError("measurement basis status differs from its evidence")
        return
    fields = set()
    for decision in payload["decisions"]:
        field = decision["field"]
        if field in fields:
            raise ValueError("duplicate terminology field decision")
        fields.add(field)
        members = {m["value"]: m for m in metadata["enums"][FIELD_ENUMS[field]]["members"]}
        candidates = {}
        for candidate in decision["candidates"]:
            value = candidate["value"]
            if (
                value in candidates
                or value not in members
                or candidate["meaning"] != members[value]["meaning"]
                or candidate["label"] != (members[value].get("label") or value)
            ):
                raise ValueError("candidate differs from released vocabulary or is repeated")
            if candidate["matching_field"] not in {"value", "label", "synonym", "browse"}:
                raise ValueError("unsupported candidate matching field")
            if candidate["matching_field"] == "synonym" and candidate["matching_predicate"] not in {
                s["predicate"] for s in members[value].get("synonyms", ())
            }:
                raise ValueError("candidate synonym predicate differs from source metadata")
            if candidate["matching_field"] != "synonym" and candidate["matching_predicate"] != "":
                raise ValueError("non-synonym candidate cannot claim a synonym predicate")
            candidates[value] = candidate
        selected = decision.get("selected_value")
        if decision["outcome"] == "selected":
            if (
                selected not in candidates
                or decision.get("mapping_predicate") not in MAPPINGS
                or decision.get("mapping_direction") != "source_to_term"
            ):
                raise ValueError(
                    "selected mapping lacks examined candidate, predicate or direction"
                )
        elif any(
            decision.get(k) is not None
            for k in ("selected_value", "mapping_predicate", "mapping_direction")
        ):
            raise ValueError("unresolved terminology decision cannot claim a selected mapping")
        if decision["outcome"] == "no_match" and candidates:
            raise ValueError("no-match decision cannot retain examined candidates as matches")


def interpretation_contribution(
    prepared, *, semantic_type, payload, operation_key, item_key, pin, anchors
):
    """Build a normal sealed contribution; this does not bypass task completion."""
    from .contributions import contribution_identity, occurrence_identity
    from .observations import source_value

    contract = {
        "terminology.interpretation": "TerminologyInterpretationV1",
        "measurement.interpretation": "MeasurementInterpretationV1",
    }[semantic_type]
    question = {
        "terminology.interpretation": "interpret.terminology",
        "measurement.interpretation": "interpret.measurement",
    }[semantic_type]
    prepared.validate_json(
        contract,
        canonical_bytes(
            dict(
                kind="proposal",
                semantic_type=semantic_type,
                effect="retain_private",
                assessment_event="local-contribution-1",
                question=question,
                value=payload,
            )
        ),
    )
    validate_interpretation_payload(prepared, semantic_type, payload)
    row = dict(
        contract=contract,
        kind="proposal",
        semantic_type=semantic_type,
        operation_key=operation_key,
        item_key=item_key,
        pin=pin,
        anchors=tuple(anchors),
        disposition="unassessed",
        standing="retained_private",
        score_state="missing",
        value=source_value(payload),
    )
    if anchors:
        row["occurrence_id"] = occurrence_identity(anchors)
    row["contribution_id"] = contribution_identity(row)
    return row
