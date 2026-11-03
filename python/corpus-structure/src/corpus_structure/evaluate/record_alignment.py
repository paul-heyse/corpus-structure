"""Private, strict guideline-bound reading agreement for five released record families.

This is a pure comparison of source-validated records in an explicitly supplied cut. It
does not authenticate that cut, protect references, resolve completed publications, or
establish extraction accuracy. There is no paraphrase or numeric equivalence policy:
original, normalized and derived readings remain distinct.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import (
    bind_record_candidates,
    validate_record_declarations,
)
from corpus_structure.semantic.types import PreparedRelease

from .semantic_alignment import TierCounts

FAMILIES = ("definition", "assertion", "measurement", "table", "formula_context")
TIERS = ("core", "full", "evidence")
COMPARISON_POLICY = "strict-source-occurrence-1"


@dataclass(frozen=True)
class RecordEvaluationFrame:
    """Caller-supplied source region, including permitted shared context anchors.

    The two acceptance policies are deliberately independent of the authoring guideline
    and of each other. Anchor IDs bind precision and coordinate space as well as location.
    Native custody and independent population selection remain caller obligations.
    """

    unit: str
    release_id: str
    guideline_version: str
    reference_policy_version: str
    prediction_policy_version: str
    pin: Mapping[str, Any]
    anchor_ids: frozenset[str]
    related_pins: tuple[Mapping[str, Any], ...] = ()
    anchor_scopes: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class RecordSide:
    frame: RecordEvaluationFrame
    records: Sequence[Mapping[str, Any]] = ()


@dataclass
class RecordAlignment:
    unit: str
    release_id: str
    guideline_version: str
    reference_policy_version: str
    prediction_policy_version: str
    counts: dict[str, TierCounts] = field(default_factory=dict)
    family_counts: dict[str, dict[str, TierCounts]] = field(default_factory=dict)
    matches: dict[str, list[str]] = field(default_factory=lambda: {tier: [] for tier in TIERS})
    field_failures: list[dict[str, Any]] = field(default_factory=list)
    prediction_standings: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": "private_validated_records",
            "comparison_policy": COMPARISON_POLICY,
            "grain": "accepted_source_record_occurrence",
            "unit": self.unit,
            "release_id": self.release_id,
            "guideline_version": self.guideline_version,
            "reference_policy_version": self.reference_policy_version,
            "prediction_policy_version": self.prediction_policy_version,
            "tiers": {tier: counts.as_dict() for tier, counts in self.counts.items()},
            "families": {
                family: {tier: counts.as_dict() for tier, counts in tiers.items()}
                for family, tiers in self.family_counts.items()
            },
            "matches": self.matches,
            "field_failures": self.field_failures,
            "prediction_standings": self.prediction_standings,
        }


def _contracts(prepared: PreparedRelease):
    validate_record_declarations(prepared.definitions)
    contracts = {}
    for definition in prepared.definitions:
        if "SemanticRecordFields" not in definition.ancestors:
            continue
        properties = {prop.name: prop for prop in definition.properties}
        family = properties["family"].equals_string
        if family not in FAMILIES:
            continue
        roles = {
            name: prepared.index.definitions[prop.range]
            for name, prop in properties.items()
            if name not in {"family", "occurrence_recipe"}
        }
        contracts[family] = (
            definition.name,
            tuple(roles),
            tuple(name for name, role in roles.items() if "RequiredRecordField" in role.ancestors),
            tuple(
                name
                for name, role in roles.items()
                if "RequiredRecordField" in role.ancestors
                or "MeaningChangingRecordField" in role.ancestors
            ),
        )
    if set(contracts) != set(FAMILIES):
        raise ValueError("record alignment requires all five supported released families")
    return contracts


def _frame(prepared: PreparedRelease, frame: RecordEvaluationFrame) -> dict[str, Any]:
    if frame.release_id != prepared.release_id:
        raise ValueError("record evaluation frame has a mismatched release")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (
            frame.unit,
            frame.guideline_version,
            frame.reference_policy_version,
            frame.prediction_policy_version,
        )
    ):
        raise ValueError(
            "record evaluation requires explicit region, guideline and policy versions"
        )
    pin = prepared.validate_python("RecordSourcePin", frame.pin).model_dump(mode="python")
    related = tuple(
        prepared.validate_python("RecordSourcePin", value).model_dump(mode="python")
        for value in frame.related_pins
    )
    closure = (pin, *related)
    if len({canonical_bytes(value) for value in closure}) != len(closure):
        raise ValueError("record evaluation source closure contains duplicate pins")
    product = ("native_product_task_id", "product_key", "product_digest")
    if any(
        tuple(value[key] for key in product) != tuple(pin[key] for key in product)
        for value in related
    ):
        raise ValueError("related evaluation source requires the same native product")
    scopes = tuple(
        prepared.validate_python("RecordReferenceAnchorScope", value).model_dump(mode="python")
        for value in frame.anchor_scopes
    )
    for scope in scopes:
        if canonical_bytes(scope["pin"]) not in {canonical_bytes(value) for value in closure}:
            raise ValueError("evaluation scope is outside its frozen source closure")
        start, end = scope.get("start"), scope.get("end")
        if (
            scope["space"] == "model_context"
            or (
                scope["precision"] == "exact"
                and (not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end)
            )
            or (scope["precision"] != "exact" and (start is not None or end is not None))
        ):
            raise ValueError("evaluation scope has unsupported coordinate precision or bounds")
        if (scope["space"] == "captured_recognition") != ("recognition" in scope):
            raise ValueError("evaluation scope must retain its actual recognition coordinate")
    return {
        "unit": frame.unit,
        "release_id": frame.release_id,
        "guideline_version": frame.guideline_version,
        "reference_policy_version": frame.reference_policy_version,
        "prediction_policy_version": frame.prediction_policy_version,
        "pin": pin,
        "anchor_ids": sorted(frame.anchor_ids),
        "related_pins": sorted(related, key=canonical_bytes),
        "anchor_scopes": sorted(scopes, key=canonical_bytes),
    }


def anchor_in_scope(anchor, anchor_ids, scopes):
    """Frozen source-derived extent closure, independent of either side's predictions."""
    if anchor["anchor_id"] in anchor_ids:
        return True
    for scope in scopes:
        if any(
            anchor.get(key) != scope.get(key)
            for key in ("pin", "space", "pointer", "precision", "recognition")
        ):
            continue
        if scope["precision"] != "exact" or (
            scope["start"] <= anchor["start"] < anchor["end"] <= scope["end"]
        ):
            return True
    return False


def _records(prepared, side, frame, contexts, contracts, *, reference):
    rows = tuple(
        model.model_dump(mode="python")
        for model in bind_record_candidates(
            prepared,
            source=frame["pin"]["source"],
            records=side.records,
            coordinate_texts=contexts,
        )
    )
    expected_policy = frame[
        "reference_policy_version" if reference else "prediction_policy_version"
    ]
    allowed = frozenset(frame["anchor_ids"])
    pins = {canonical_bytes(value) for value in (frame["pin"], *frame["related_pins"])}
    accepted = {}
    standings = Counter()
    for row in rows:
        family = row["family"]
        if family not in contracts or row["contract"] != contracts[family][0]:
            raise ValueError("unsupported record family or contract for record alignment")
        if row["pin"] != frame["pin"]:
            raise ValueError("record has a stale or mismatched source pin")
        if row["policy_version"] != expected_policy:
            raise ValueError("record acceptance policy differs from its evaluation binding")
        if any(canonical_bytes(anchor["pin"]) not in pins for anchor in row["anchors"]):
            raise ValueError("record anchor source is outside the frozen source closure")
        if any(
            not anchor_in_scope(anchor, allowed, frame["anchor_scopes"])
            for anchor in row["anchors"]
        ):
            raise ValueError("record anchor is outside the explicit evaluation cut")
        if reference and row["standing"] != "accepted":
            raise ValueError("reference denominator requires accepted independent readings")
        standings[row["standing"]] += 1
        if row["standing"] != "accepted":
            continue
        if row["record_id"] in accepted:
            raise ValueError("multiple accepted interpretations for one source occurrence")
        accepted[row["record_id"]] = row
    return accepted, dict(standings)


def _meaning(value):
    # Explanatory prose and local IDs are not reading semantics. Evidence is assessed
    # separately, retaining exact set/anchor identity rather than weakening precision.
    result = {
        key: item
        for key, item in value.items()
        if key not in {"evidence_sets", "evidence_status", "reason", "alternatives"}
    }
    result["alternatives"] = sorted(
        (alternative["value"] for alternative in value.get("alternatives", ())),
        key=canonical_bytes,
    )
    return canonical_bytes(result)


def _evidence(value):
    return canonical_bytes(
        {
            "status": value["evidence_status"],
            "sets": sorted(value.get("evidence_sets", ())),
            "alternatives": sorted(
                (
                    [alternative["value"], sorted(alternative.get("evidence_sets", ()))]
                    for alternative in value.get("alternatives", ())
                ),
                key=canonical_bytes,
            ),
        }
    )


def align_records(
    reference: RecordSide,
    prediction: RecordSide,
    prepared: PreparedRelease,
    *,
    coordinate_texts: Sequence[Mapping[str, Any]] = (),
    comparison_policy: str = COMPARISON_POLICY,
) -> RecordAlignment:
    """Compare accepted occurrences; preserve empty prediction reference denominators.

    Core compares released required-role readings. Full compares every released role's
    reading (including supplemental transforms), plus required/meaning-changing evidence.
    Evidence additionally compares supplemental-role evidence. All tiers use exact source
    occurrence identity and one-to-one accounting. Candidate/rejected/unresolved predictions
    are validated and reported separately, never promoted to accepted true positives.

    Malformed, unsupported, stale and out-of-cut inputs refuse the entire operation; none
    are silently dropped from a successful score. The caller supplies immutable guideline
    and cut versions; this pure operation cannot verify author independence or storage ACLs.
    """
    if comparison_policy != COMPARISON_POLICY:
        raise ValueError("unsupported record comparison policy version")
    contracts = _contracts(prepared)
    ref_frame, pred_frame = _frame(prepared, reference.frame), _frame(prepared, prediction.frame)
    if canonical_bytes(ref_frame) != canonical_bytes(pred_frame):
        raise ValueError("record alignment requires the same source-region/guideline frame and cut")
    contexts = tuple(
        prepared.validate_python("RecordCoordinateText", raw).model_dump(mode="python")
        for raw in coordinate_texts
    )
    pins = {canonical_bytes(value) for value in (ref_frame["pin"], *ref_frame["related_pins"])}
    if any(canonical_bytes(context["pin"]) not in pins for context in contexts):
        raise ValueError("coordinate text has a stale or mismatched source pin")
    rr, _ = _records(prepared, reference, ref_frame, contexts, contracts, reference=True)
    pp, standings = _records(prepared, prediction, ref_frame, contexts, contracts, reference=False)
    out = RecordAlignment(
        reference.frame.unit,
        prepared.release_id,
        reference.frame.guideline_version,
        reference.frame.reference_policy_version,
        reference.frame.prediction_policy_version,
        prediction_standings=standings,
    )
    for identity in sorted(rr.keys() & pp.keys()):
        ref, pred = rr[identity], pp[identity]
        _, roles, required, meaning_changing = contracts[ref["family"]]
        rf = {value["role"]: value for value in ref["fields"]}
        pf = {value["role"]: value for value in pred["fields"]}
        reading_errors = tuple(role for role in roles if _meaning(rf[role]) != _meaning(pf[role]))
        evidence_errors = tuple(
            role for role in roles if _evidence(rf[role]) != _evidence(pf[role])
        )
        core = not set(reading_errors).intersection(required)
        full = (
            core and not reading_errors and not set(evidence_errors).intersection(meaning_changing)
        )
        evidence = full and not evidence_errors
        for tier, matched in (("core", core), ("full", full), ("evidence", evidence)):
            if matched:
                out.matches[tier].append(identity)
        if reading_errors or evidence_errors:
            out.field_failures.append(
                {
                    "record_id": identity,
                    "family": ref["family"],
                    "reading_roles": reading_errors,
                    "evidence_roles": evidence_errors,
                }
            )
    for family in FAMILIES:
        ref_ids = {key for key, row in rr.items() if row["family"] == family}
        pred_ids = {key for key, row in pp.items() if row["family"] == family}
        out.family_counts[family] = {
            tier: TierCounts(
                len(ref_ids), len(pred_ids), len(ref_ids.intersection(out.matches[tier]))
            )
            for tier in TIERS
        }
    out.counts = {tier: TierCounts(len(rr), len(pp), len(out.matches[tier])) for tier in TIERS}
    return out
