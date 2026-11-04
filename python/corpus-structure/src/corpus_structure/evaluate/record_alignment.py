"""Private, strict guideline-bound reading agreement for five released record families.

This is a pure comparison of source-validated records in an explicitly supplied cut. It
does not authenticate that cut, protect references, resolve completed publications, or
establish extraction accuracy. There is no paraphrase or numeric equivalence policy:
original, normalized and derived readings remain distinct.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    validate_record_declarations,
)
from corpus_structure.semantic.types import PreparedRelease

from .semantic_alignment import TierCounts

FAMILIES = ("definition", "assertion", "measurement", "table", "formula_context")
TIERS = ("core", "full", "evidence")
COMPARISON_POLICY = "strict-source-occurrence-1"
APPLICABILITY_PROTOCOL = "source-record-reference-applicability-1"


def reference_contract(prepared: PreparedRelease) -> dict[str, Any]:
    """Only declarations consumed by strict source reading, never execution bytes.

    JSON schemas include their transitive value/state/coordinate definitions. The
    evolving grade/fit report is an output, not an authored source premise.
    """
    artifacts = {item.kind: item.content for item in prepared.artifacts}
    projection = json.loads(artifacts["record_projection.json"])
    names = {"SourceRecord", "RecordSourcePin", "RecordCoordinateText"}
    names.update(family["contract"] for family in projection["families"])
    # Independent reference authoring may be absent from a pure alignment release.
    names.update(
        name
        for name in ("ReferenceRecordBatch", "RecordReferenceAnchorScope")
        if f"json_schema/{name}" in artifacts
    )
    schemas = {name: json.loads(artifacts[f"json_schema/{name}"]) for name in sorted(names)}
    consumed = names | {name for schema in schemas.values() for name in schema.get("$defs", {})}
    definitions = sorted(
        (asdict(value) for value in prepared.definitions if value.name in consumed),
        key=lambda value: value["name"],
    )
    ranges = {prop["range"] for value in definitions for prop in value["properties"]}
    return json.loads(
        canonical_bytes(
            {
                "comparison_policy": COMPARISON_POLICY,
                "families": projection["families"],
                "classification_kinds": projection["classification_kinds"],
                "schemas": schemas,
                "definitions": definitions,
                "vocabularies": sorted(
                    (asdict(value) for value in prepared.vocabularies if value.enum in ranges),
                    key=lambda value: value["enum"],
                ),
                "enum_declarations": sorted(
                    (
                        {"kind": row.kind, "name": row.name, "body_hex": row.body.hex()}
                        for row in prepared.registry_rows
                        if row.kind == "enum" and row.name in ranges
                    ),
                    key=lambda value: value["name"],
                ),
            }
        )
    )


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
    reference_release_id: str | None = None
    match_bindings: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        result = {
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
        if self.reference_release_id is not None:
            result["reference_release_id"] = self.reference_release_id
            result["match_bindings"] = self.match_bindings
        return result


def _comparison_pin(pin, correspondence, side):
    matches = [row["physical_digest"] for row in correspondence if row[f"{side}_pin"] == pin]
    if len(matches) != 1:
        raise ValueError("comparison pin has no unique authenticated physical correspondence")
    return matches[0]


def comparison_record(record, correspondence, side) -> dict[str, Any]:
    """Detached comparison projection; original payload and IDs remain untouched.

    Correspondence authentication is the protected native caller's responsibility.
    This pure function preserves every coordinate, spelling and binding determinant.
    """

    def digest(value):
        return sha256(canonical_bytes(value)).hexdigest()

    anchors = {
        anchor["anchor_id"]: digest(
            {
                **{key: value for key, value in anchor.items() if key not in {"anchor_id", "pin"}},
                "pin": _comparison_pin(anchor["pin"], correspondence, side),
            }
        )
        for anchor in record["anchors"]
    }
    sets = {}
    for evidence in record.get("evidence_sets", ()):
        members = [anchors[value] for value in evidence["anchors"]]
        if evidence["ordering"] != "ordered":
            members.sort()
        sets[evidence["set_id"]] = digest(
            {
                **{key: value for key, value in evidence.items() if key != "set_id"},
                "anchors": members,
            }
        )
    fields = []
    for field_value in record["fields"]:
        value = dict(field_value)
        if "evidence_sets" in value:
            value["evidence_sets"] = [sets[identity] for identity in value["evidence_sets"]]
        if "alternatives" in value:
            value["alternatives"] = [
                dict(
                    alternative,
                    evidence_sets=[
                        sets[identity] for identity in alternative.get("evidence_sets", ())
                    ],
                )
                for alternative in value["alternatives"]
            ]
        fields.append(value)
    return {
        "occurrence": digest(
            [
                record["family"],
                record["occurrence_recipe"],
                _comparison_pin(record["pin"], correspondence, side),
                sorted(anchors[identity] for identity in record["occurrence_anchors"]),
            ]
        ),
        "fields": fields,
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


def _records(prepared, side, frame, contexts, contracts, *, reference, anchor_allowed=None):
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
            not (
                anchor_allowed(anchor)
                if anchor_allowed is not None
                else anchor_in_scope(anchor, allowed, frame["anchor_scopes"])
            )
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
    prediction_prepared: PreparedRelease | None = None,
    prediction_coordinate_texts: Sequence[Mapping[str, Any]] | None = None,
    correspondence: Sequence[Mapping[str, Any]] | None = None,
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
    target = prediction_prepared or prepared
    contracts = _contracts(prepared)
    ref_frame, pred_frame = _frame(prepared, reference.frame), _frame(target, prediction.frame)
    if correspondence is None:
        if canonical_bytes(ref_frame) != canonical_bytes(pred_frame):
            raise ValueError(
                "record alignment requires the same source-region/guideline frame and cut"
            )
    else:
        if reference_contract(prepared) != reference_contract(target):
            raise ValueError(
                "source reading declarations differ across reference and prediction releases"
            )
        for key in (
            "unit",
            "guideline_version",
            "reference_policy_version",
            "prediction_policy_version",
        ):
            if ref_frame[key] != pred_frame[key]:
                raise ValueError("source comparison guideline/policy/unit binding differs")
        for side, binding in (("reference", ref_frame), ("prediction", pred_frame)):
            pins = [binding["pin"], *binding["related_pins"]]
            mapped = [row[f"{side}_pin"] for row in correspondence]
            if (
                len(mapped) != len(pins)
                or len({canonical_bytes(pin) for pin in mapped}) != len(mapped)
                or {canonical_bytes(pin) for pin in pins}
                != {canonical_bytes(pin) for pin in mapped}
                or len({row["physical_digest"] for row in correspondence}) != len(correspondence)
            ):
                raise ValueError(
                    "source comparison requires a bijection over the frozen source closure"
                )
        ref_scopes = [
            dict(scope, pin=_comparison_pin(scope["pin"], correspondence, "reference"))
            for scope in ref_frame["anchor_scopes"]
        ]
        pred_scopes = [
            dict(scope, pin=_comparison_pin(scope["pin"], correspondence, "prediction"))
            for scope in pred_frame["anchor_scopes"]
        ]
        if sorted(ref_scopes, key=canonical_bytes) != sorted(pred_scopes, key=canonical_bytes):
            raise ValueError("source comparison scope correspondence differs")
    contexts = tuple(
        prepared.validate_python("RecordCoordinateText", raw).model_dump(mode="python")
        for raw in coordinate_texts
    )
    pins = {canonical_bytes(value) for value in (ref_frame["pin"], *ref_frame["related_pins"])}
    if any(canonical_bytes(context["pin"]) not in pins for context in contexts):
        raise ValueError("coordinate text has a stale or mismatched source pin")
    rr, _ = _records(prepared, reference, ref_frame, contexts, contracts, reference=True)
    prediction_contexts = (
        contexts
        if prediction_coordinate_texts is None
        else tuple(
            target.validate_python("RecordCoordinateText", raw).model_dump(mode="python")
            for raw in prediction_coordinate_texts
        )
    )
    pred_pins = {
        canonical_bytes(value) for value in (pred_frame["pin"], *pred_frame["related_pins"])
    }
    if any(canonical_bytes(context["pin"]) not in pred_pins for context in prediction_contexts):
        raise ValueError("prediction coordinate text has a stale or mismatched source pin")

    def prediction_anchor_allowed(anchor):
        pairs = [row for row in correspondence or () if row["prediction_pin"] == anchor["pin"]]
        if len(pairs) != 1:
            return False
        counterpart = dict(anchor, pin=pairs[0]["reference_pin"])
        counterpart["anchor_id"] = anchor_identity(counterpart)
        return anchor_in_scope(
            counterpart, frozenset(ref_frame["anchor_ids"]), ref_frame["anchor_scopes"]
        )

    pp, standings = _records(
        target,
        prediction,
        pred_frame,
        prediction_contexts,
        contracts,
        reference=False,
        anchor_allowed=prediction_anchor_allowed if correspondence is not None else None,
    )
    ref_rows, pred_rows = rr, pp
    if correspondence is not None:

        def index(rows, side):
            result: dict[str, dict[str, Any]] = {}
            for row in rows.values():
                projection = comparison_record(row, correspondence, side)
                key = projection["occurrence"]
                if key in result:
                    raise ValueError(
                        "multiple accepted interpretations for one physical source occurrence"
                    )
                result[key] = dict(row, fields=projection["fields"])
            return result

        rr, pp = index(rr, "reference"), index(pp, "prediction")
    out = RecordAlignment(
        reference.frame.unit,
        target.release_id,
        reference.frame.guideline_version,
        reference.frame.reference_policy_version,
        reference.frame.prediction_policy_version,
        prediction_standings=standings,
        reference_release_id=prepared.release_id if correspondence is not None else None,
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
                out.matches[tier].append(ref["record_id"])
        if correspondence is not None:
            out.match_bindings.append(
                {
                    "reference_record_id": ref["record_id"],
                    "reference_interpretation_id": ref["interpretation_id"],
                    "prediction_record_id": pred["record_id"],
                    "prediction_interpretation_id": pred["interpretation_id"],
                    "tiers": [
                        tier
                        for tier, matched in (
                            ("core", core),
                            ("full", full),
                            ("evidence", evidence),
                        )
                        if matched
                    ],
                }
            )
        if reading_errors or evidence_errors:
            failure = {
                "record_id": ref["record_id"],
                "family": ref["family"],
                "reading_roles": reading_errors,
                "evidence_roles": evidence_errors,
            }
            if correspondence is not None:
                failure.update(
                    reference_interpretation_id=ref["interpretation_id"],
                    prediction_record_id=pred["record_id"],
                    prediction_interpretation_id=pred["interpretation_id"],
                )
            out.field_failures.append(failure)
    for family in FAMILIES:
        ref_ids = {key for key, row in ref_rows.items() if row["family"] == family}
        pred_ids = {key for key, row in pred_rows.items() if row["family"] == family}
        out.family_counts[family] = {
            tier: TierCounts(
                len(ref_ids), len(pred_ids), len(ref_ids.intersection(out.matches[tier]))
            )
            for tier in TIERS
        }
    out.counts = {tier: TierCounts(len(rr), len(pp), len(out.matches[tier])) for tier in TIERS}
    for values in out.matches.values():
        values.sort()
    out.match_bindings.sort(key=lambda value: value["reference_record_id"])
    out.field_failures.sort(key=lambda value: value["record_id"])
    return out
