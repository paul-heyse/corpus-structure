"""Finite public projection of released source records through the common publisher.

SourceRecord remains a private product, never a graph datatype. Its immutable occurrence
and interpretation identifiers survive projection. Public assertion bindings are separate
from the private assertion strings that participate in interpretation identity.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from types import MappingProxyType
from typing import Any, TypedDict

from .identity import canonical_bytes
from .types import ClassDefinition, PreparedArtifact, PreparedRelease

ARTIFACT = "record_projection.json"
ABI = "source-record-projection-2"
CANDIDATE_POLICY = "m1-candidate-only"
CANDIDATE_POLICY_VERSION = "1"
CALIBRATION = "not_calibrated"


@dataclass(frozen=True)
class RecordReportRow:
    selected_task_id: int
    origin_task_id: int
    cut_id: int
    source: str
    outcome: str
    records_present: bool


@dataclass(frozen=True)
class RecordReportMemberRow:
    selected_task_id: int
    position: int
    record_id: str
    interpretation_id: str


@dataclass(frozen=True)
class SourceRecordRow:
    record_id: str
    interpretation_id: str
    contract: str
    family: str
    occurrence_recipe: str
    source: str
    native_product_task_id: int
    product_key: str
    product_digest: str
    projection_digest: str
    recipe_digest: str
    source_view_id: int | None
    standing: str
    policy_version: str
    evidence_sets_present: bool
    computation_dependencies_present: bool
    assertion_members_present: bool


@dataclass(frozen=True)
class RecordFieldRow:
    record_id: str
    interpretation_id: str
    role: str
    position: int
    kind: str
    state: str
    meaning_changing: bool
    evidence_status: str
    value_kind: str | None
    text_value: str | None
    decimal_lexical: str | None
    classification: str | None
    native_pointer: str | None
    original: str | None
    original_pieces_present: bool
    evidence_sets_present: bool
    alternatives_present: bool
    premises_present: bool
    reason: str | None
    policy: str | None
    rule: str | None


@dataclass(frozen=True)
class RecordFieldPieceRow:
    record_id: str
    interpretation_id: str
    role: str
    position: int
    original_piece: str | None
    value_piece: str | None


@dataclass(frozen=True)
class RecordAlternativeRow:
    record_id: str
    interpretation_id: str
    role: str
    alternative_id: str
    position: int
    value_kind: str
    text_value: str | None
    decimal_lexical: str | None
    classification: str | None
    native_pointer: str | None
    evidence_sets_present: bool
    reason: str


@dataclass(frozen=True)
class RecordAlternativePieceRow:
    record_id: str
    interpretation_id: str
    role: str
    alternative_id: str
    position: int
    value_piece: str


@dataclass(frozen=True)
class RecordAnchorRow:
    record_id: str
    interpretation_id: str
    anchor_id: str
    position: int
    source: str
    native_product_task_id: int
    product_key: str
    product_digest: str
    projection_digest: str
    recipe_digest: str
    source_view_id: int | None
    space: str
    pointer: str
    precision: str
    start: int | None
    end: int | None
    source_piece: str | None
    binding_version: int | None
    binding_relationship: str | None
    binding_policy: str | None
    recognition_selected_occurrence_id: str | None
    recognition_task_id: int | None
    recognition_product_key: str | None
    recognition_content_digest: str | None
    recognition_occurrence_id: str | None
    recognition_relation_id: str | None
    recognition_endpoint_role: str | None
    recognition_relation_kind: str | None
    recognition_relation_outcome: str | None
    recognition_provider_occurrence_json: str | None
    recognition_observation_json: str | None


@dataclass(frozen=True)
class RecordOccurrenceAnchorRow:
    record_id: str
    interpretation_id: str
    position: int
    anchor_id: str


@dataclass(frozen=True)
class RecordEvidenceSetRow:
    record_id: str
    interpretation_id: str
    set_id: str
    position: int
    role: str
    ordering: str
    usage: str


@dataclass(frozen=True)
class RecordEvidenceMemberRow:
    record_id: str
    interpretation_id: str
    set_id: str
    position: int
    anchor_id: str


@dataclass(frozen=True)
class RecordFieldEvidenceRow:
    record_id: str
    interpretation_id: str
    role: str
    position: int
    set_id: str


@dataclass(frozen=True)
class RecordAlternativeEvidenceRow:
    record_id: str
    interpretation_id: str
    role: str
    alternative_id: str
    position: int
    set_id: str


@dataclass(frozen=True)
class RecordPremiseRow:
    record_id: str
    interpretation_id: str
    role: str
    position: int
    premise_role: str


@dataclass(frozen=True)
class RecordDependencyRow:
    record_id: str
    interpretation_id: str
    position: int
    dependency: str


@dataclass(frozen=True)
class RecordPrivateAssertionRow:
    record_id: str
    interpretation_id: str
    position: int
    assertion_ref: str


@dataclass(frozen=True)
class RecordAdmissionRow:
    record_id: str
    interpretation_id: str
    decision: str
    policy_id: str
    policy_version: str
    calibration: str
    reason: str
    instance_digest: str | None = None
    evaluation_id: int | None = None
    evaluation_digest: str | None = None
    probability_lexical: str | None = None
    binding_json: str | None = None


@dataclass(frozen=True)
class RecordAssertionRow:
    record_id: str
    interpretation_id: str
    role: str
    reading_id: str
    fact_id: str
    occurrence_id: str


@dataclass(frozen=True)
class RecordAssertionSupportRow:
    origin_task_id: int
    record_id: str
    interpretation_id: str
    role: str
    set_id: str
    anchor_id: str
    evidence_id: str
    occurrence_id: str


RECORD_ROW_TYPES = {
    "record_report": RecordReportRow,
    "source_record": SourceRecordRow,
    "record_report_member": RecordReportMemberRow,
    "record_field": RecordFieldRow,
    "record_field_piece": RecordFieldPieceRow,
    "record_alternative": RecordAlternativeRow,
    "record_alternative_piece": RecordAlternativePieceRow,
    "record_anchor": RecordAnchorRow,
    "record_occurrence_anchor": RecordOccurrenceAnchorRow,
    "record_evidence_set": RecordEvidenceSetRow,
    "record_evidence_member": RecordEvidenceMemberRow,
    "record_field_evidence": RecordFieldEvidenceRow,
    "record_alternative_evidence": RecordAlternativeEvidenceRow,
    "record_premise": RecordPremiseRow,
    "record_dependency": RecordDependencyRow,
    "record_private_assertion": RecordPrivateAssertionRow,
    "record_admission": RecordAdmissionRow,
    "record_assertion": RecordAssertionRow,
    "record_assertion_support": RecordAssertionSupportRow,
}


class RecordProjectionRows(TypedDict):
    record_report: tuple[RecordReportRow, ...]
    source_record: tuple[SourceRecordRow, ...]
    record_report_member: tuple[RecordReportMemberRow, ...]
    record_field: tuple[RecordFieldRow, ...]
    record_field_piece: tuple[RecordFieldPieceRow, ...]
    record_alternative: tuple[RecordAlternativeRow, ...]
    record_alternative_piece: tuple[RecordAlternativePieceRow, ...]
    record_anchor: tuple[RecordAnchorRow, ...]
    record_occurrence_anchor: tuple[RecordOccurrenceAnchorRow, ...]
    record_evidence_set: tuple[RecordEvidenceSetRow, ...]
    record_evidence_member: tuple[RecordEvidenceMemberRow, ...]
    record_field_evidence: tuple[RecordFieldEvidenceRow, ...]
    record_alternative_evidence: tuple[RecordAlternativeEvidenceRow, ...]
    record_premise: tuple[RecordPremiseRow, ...]
    record_dependency: tuple[RecordDependencyRow, ...]
    record_private_assertion: tuple[RecordPrivateAssertionRow, ...]
    record_admission: tuple[RecordAdmissionRow, ...]
    record_assertion: tuple[RecordAssertionRow, ...]
    record_assertion_support: tuple[RecordAssertionSupportRow, ...]


@dataclass
class _RecordRows:
    record_report: list[RecordReportRow] = dataclass_field(default_factory=list)
    source_record: list[SourceRecordRow] = dataclass_field(default_factory=list)
    record_report_member: list[RecordReportMemberRow] = dataclass_field(default_factory=list)
    record_field: list[RecordFieldRow] = dataclass_field(default_factory=list)
    record_field_piece: list[RecordFieldPieceRow] = dataclass_field(default_factory=list)
    record_alternative: list[RecordAlternativeRow] = dataclass_field(default_factory=list)
    record_alternative_piece: list[RecordAlternativePieceRow] = dataclass_field(
        default_factory=list
    )
    record_anchor: list[RecordAnchorRow] = dataclass_field(default_factory=list)
    record_occurrence_anchor: list[RecordOccurrenceAnchorRow] = dataclass_field(
        default_factory=list
    )
    record_evidence_set: list[RecordEvidenceSetRow] = dataclass_field(default_factory=list)
    record_evidence_member: list[RecordEvidenceMemberRow] = dataclass_field(default_factory=list)
    record_field_evidence: list[RecordFieldEvidenceRow] = dataclass_field(default_factory=list)
    record_alternative_evidence: list[RecordAlternativeEvidenceRow] = dataclass_field(
        default_factory=list
    )
    record_premise: list[RecordPremiseRow] = dataclass_field(default_factory=list)
    record_dependency: list[RecordDependencyRow] = dataclass_field(default_factory=list)
    record_private_assertion: list[RecordPrivateAssertionRow] = dataclass_field(
        default_factory=list
    )
    record_admission: list[RecordAdmissionRow] = dataclass_field(default_factory=list)
    record_assertion: list[RecordAssertionRow] = dataclass_field(default_factory=list)
    record_assertion_support: list[RecordAssertionSupportRow] = dataclass_field(
        default_factory=list
    )


_BINDING_FIELDS = ("version", "relationship", "policy")
_RECOGNITION_FIELDS = (
    "selected_occurrence_id",
    "task_id",
    "product_key",
    "content_digest",
    "occurrence_id",
    "relation_id",
    "endpoint_role",
    "relation_kind",
    "relation_outcome",
    "provider_occurrence_json",
    "observation_json",
)
_PIN_FIELDS = (
    "source",
    "native_product_task_id",
    "product_key",
    "product_digest",
    "projection_digest",
    "recipe_digest",
    "source_view_id",
)


def prepare_record_projection(definitions: Sequence[ClassDefinition]) -> PreparedArtifact | None:
    """Compile roles from effective definitions, never a second family schema."""
    classes = {definition.name: definition for definition in definitions}
    if "SourceRecord" not in classes:
        return None
    families = []
    for definition in definitions:
        if "SemanticRecordFields" not in definition.ancestors:
            continue
        properties = {prop.name: prop for prop in definition.properties}
        roles = []
        for prop in definition.properties:
            if prop.name in {"family", "occurrence_recipe"}:
                continue
            field = classes[prop.range]
            roles.append(
                dict(
                    role=prop.name,
                    field_class=field.name,
                    required="RequiredRecordField" in field.ancestors,
                    meaning_changing="MeaningChangingRecordField" in field.ancestors,
                )
            )
        families.append(
            dict(
                contract=definition.name,
                family=properties["family"].equals_string,
                occurrence_recipe=properties["occurrence_recipe"].equals_string,
                roles=roles,
            )
        )
    return PreparedArtifact(
        ARTIFACT,
        canonical_bytes(
            dict(
                abi=ABI,
                families=families,
                classification_kinds=sorted(
                    {
                        prop.equals_string
                        for definition in definitions
                        if definition.name == "RecordClassification"
                        or "RecordClassification" in definition.ancestors
                        for prop in definition.properties
                        if prop.name == "kind" and prop.equals_string
                    }
                ),
                relations=list(RECORD_ROW_TYPES),
                policy=dict(
                    id=CANDIDATE_POLICY,
                    version=CANDIDATE_POLICY_VERSION,
                    calibration=CALIBRATION,
                    accepted=False,
                    admission_overlay="evaluated-source-reading-1",
                ),
            )
        ),
    )


def read_record_projection(prepared: PreparedRelease) -> dict[str, Any]:
    """Read only the exact archived projection; a predecessor has no implied records."""
    artifacts = [a for a in prepared.artifacts if a.kind == ARTIFACT]
    if len(artifacts) != 1:
        raise ValueError("release has no unique public record projection")
    projection = json.loads(artifacts[0].content)
    if projection.get("abi") not in {"source-record-projection-1", ABI}:
        raise ValueError("unsupported public record projection")
    return projection


def _pin(row):
    return {key: row[key] for key in _PIN_FIELDS if row.get(key) is not None}


def _scalar(value: Mapping[str, Any] | None) -> dict[str, Any]:
    value = value or {}
    known = {"kind", "text", "lexical", "label", "pointer", "items"}
    if value.keys() - known:
        raise ValueError("source scalar has no finite public projection")
    return dict(
        value_kind=value.get("kind"),
        text_value=value.get("text"),
        decimal_lexical=value.get("lexical"),
        classification=value.get("label"),
        native_pointer=value.get("pointer"),
    )


def project_record_reports(
    prepared: PreparedRelease, reports: Sequence[Mapping[str, Any]]
) -> RecordProjectionRows:
    """Lower authenticated, sealed-cut reports into the existing publication row spine.

    Each input has selected_task_id, origin_task_id, cut_id, source, outcome and records.
    records=None preserves predecessor absence. Validation/authentication belongs to the
    record owner before this call; protected native publication independently enforces it.
    """
    projection = read_record_projection(prepared)
    contracts = {family["contract"]: family for family in projection["families"]}
    rows = _RecordRows()
    seen = {}
    for report in reports:
        records = report["records"]
        rows.record_report.append(
            RecordReportRow(
                report["selected_task_id"],
                report["origin_task_id"],
                report["cut_id"],
                report["source"],
                report["outcome"],
                records is not None,
            )
        )
        for position, model in enumerate(records or ()):
            record = (
                model.model_dump(mode="python") if hasattr(model, "model_dump") else dict(model)
            )
            if record["standing"] == "accepted":
                raise ValueError("candidate-only record policy refuses accepted standing")
            contract = contracts.get(record["contract"])
            if contract is None or (record["family"], record["occurrence_recipe"]) != (
                contract["family"],
                contract["occurrence_recipe"],
            ):
                raise ValueError("record differs from released projection family")
            expected = {role["role"]: role for role in contract["roles"]}
            if {f["role"] for f in record["fields"]} != expected.keys():
                raise ValueError("record projection roles differ from released contract")
            key = record["record_id"], record["interpretation_id"]
            rows.record_report_member.append(
                RecordReportMemberRow(
                    report["selected_task_id"],
                    position,
                    *key,
                )
            )
            if key in seen:
                if seen[key] != canonical_bytes(record):
                    raise ValueError("record identity has conflicting immutable contents")
                continue
            seen[key] = canonical_bytes(record)
            rows.source_record.append(
                SourceRecordRow(
                    *key,
                    record["contract"],
                    record["family"],
                    record["occurrence_recipe"],
                    **{name: record["pin"].get(name) for name in _PIN_FIELDS},
                    standing=record["standing"],
                    policy_version=record["policy_version"],
                    evidence_sets_present="evidence_sets" in record,
                    computation_dependencies_present="computation_dependencies" in record,
                    assertion_members_present="assertion_members" in record,
                )
            )
            for fp, field in enumerate(record["fields"]):
                role = field["role"]
                if field["meaning_changing"] != expected[role]["meaning_changing"]:
                    raise ValueError("record field meaning differs from released role")
                rows.record_field.append(
                    RecordFieldRow(
                        *key,
                        role,
                        fp,
                        field["kind"],
                        field["state"],
                        field["meaning_changing"],
                        field["evidence_status"],
                        **_scalar(field.get("value")),
                        original=field.get("original"),
                        original_pieces_present="original_pieces" in field,
                        evidence_sets_present="evidence_sets" in field,
                        alternatives_present="alternatives" in field,
                        premises_present="premises" in field,
                        reason=field.get("reason"),
                        policy=field.get("policy"),
                        rule=field.get("rule"),
                    )
                )
                original = field.get("original_pieces", ())
                values = field.get("value", {}).get("items", ())
                for i in range(max(len(original), len(values))):
                    rows.record_field_piece.append(
                        RecordFieldPieceRow(
                            *key,
                            role,
                            i,
                            original[i] if i < len(original) else None,
                            values[i] if i < len(values) else None,
                        )
                    )
                for i, sid in enumerate(field.get("evidence_sets", ())):
                    rows.record_field_evidence.append(RecordFieldEvidenceRow(*key, role, i, sid))
                for i, premise in enumerate(field.get("premises", ())):
                    rows.record_premise.append(RecordPremiseRow(*key, role, i, premise))
                for ap, alternative in enumerate(field.get("alternatives", ())):
                    aid = alternative["alternative_id"]
                    rows.record_alternative.append(
                        RecordAlternativeRow(
                            *key,
                            role,
                            aid,
                            ap,
                            **_scalar(alternative["value"]),
                            evidence_sets_present="evidence_sets" in alternative,
                            reason=alternative["reason"],
                        )
                    )
                    for i, piece in enumerate(alternative["value"].get("items", ())):
                        rows.record_alternative_piece.append(
                            RecordAlternativePieceRow(*key, role, aid, i, piece)
                        )
                    for i, sid in enumerate(alternative.get("evidence_sets", ())):
                        rows.record_alternative_evidence.append(
                            RecordAlternativeEvidenceRow(*key, role, aid, i, sid)
                        )
            for position, anchor in enumerate(record["anchors"]):
                rows.record_anchor.append(
                    RecordAnchorRow(
                        *key,
                        anchor["anchor_id"],
                        position,
                        **{name: anchor["pin"].get(name) for name in _PIN_FIELDS},
                        space=anchor["space"],
                        pointer=anchor["pointer"],
                        precision=anchor["precision"],
                        start=anchor.get("start"),
                        end=anchor.get("end"),
                        source_piece=anchor.get("source_piece"),
                        **{
                            "binding_" + name: anchor.get("binding", {}).get(name)
                            for name in _BINDING_FIELDS
                        },
                        **{
                            "recognition_" + name: anchor.get("recognition", {}).get(name)
                            for name in _RECOGNITION_FIELDS
                        },
                    )
                )
            for position, aid in enumerate(record["occurrence_anchors"]):
                rows.record_occurrence_anchor.append(RecordOccurrenceAnchorRow(*key, position, aid))
            for position, evidence in enumerate(record.get("evidence_sets", ())):
                sid = evidence["set_id"]
                rows.record_evidence_set.append(
                    RecordEvidenceSetRow(
                        *key,
                        sid,
                        position,
                        evidence["role"],
                        evidence["ordering"],
                        evidence["usage"],
                    )
                )
                for i, aid in enumerate(evidence["anchors"]):
                    rows.record_evidence_member.append(RecordEvidenceMemberRow(*key, sid, i, aid))
            for position, dependency in enumerate(record.get("computation_dependencies", ())):
                rows.record_dependency.append(RecordDependencyRow(*key, position, dependency))
            for position, assertion in enumerate(record.get("assertion_members", ())):
                rows.record_private_assertion.append(
                    RecordPrivateAssertionRow(*key, position, assertion)
                )
            rows.record_admission.append(
                RecordAdmissionRow(
                    *key,
                    record["standing"],
                    CANDIDATE_POLICY,
                    CANDIDATE_POLICY_VERSION,
                    CALIBRATION,
                    "Retained source interpretation; accepted record admission is unavailable",
                )
            )
    return RecordProjectionRows(
        record_report=tuple(rows.record_report),
        source_record=tuple(rows.source_record),
        record_report_member=tuple(rows.record_report_member),
        record_field=tuple(rows.record_field),
        record_field_piece=tuple(rows.record_field_piece),
        record_alternative=tuple(rows.record_alternative),
        record_alternative_piece=tuple(rows.record_alternative_piece),
        record_anchor=tuple(rows.record_anchor),
        record_occurrence_anchor=tuple(rows.record_occurrence_anchor),
        record_evidence_set=tuple(rows.record_evidence_set),
        record_evidence_member=tuple(rows.record_evidence_member),
        record_field_evidence=tuple(rows.record_field_evidence),
        record_alternative_evidence=tuple(rows.record_alternative_evidence),
        record_premise=tuple(rows.record_premise),
        record_dependency=tuple(rows.record_dependency),
        record_private_assertion=tuple(rows.record_private_assertion),
        record_admission=tuple(rows.record_admission),
        record_assertion=tuple(rows.record_assertion),
        record_assertion_support=tuple(rows.record_assertion_support),
    )


_RECONSTRUCTION_GROUPS = {
    "record_field_piece": ("role",),
    "record_field_evidence": ("role",),
    "record_premise": ("role",),
    "record_alternative": ("role",),
    "record_alternative_piece": ("alternative_id", "role"),
    "record_alternative_evidence": ("alternative_id", "role"),
    "record_evidence_member": ("set_id",),
}


@dataclass(frozen=True)
class PreparedRecordProjection:
    """Invocation-owned row groups; no database or global cache is retained."""

    records: Mapping[
        tuple[str, str],
        Mapping[tuple[str, tuple[tuple[str, Any], ...]], tuple[Mapping[str, Any], ...]],
    ]
    reports_by_task: Mapping[int, tuple[Mapping[str, Any], ...]]
    members_by_task: Mapping[int, tuple[Mapping[str, Any], ...]]

    def rows_for(
        self, record_id: str, interpretation_id: str, relation: str, **selectors: Any
    ) -> tuple[Mapping[str, Any], ...]:
        return self.records.get((record_id, interpretation_id), {}).get(
            (relation, tuple(sorted(selectors.items()))), ()
        )


def index_record_projection(
    rows: Mapping[str, Any] | PreparedRecordProjection,
) -> PreparedRecordProjection:
    """Convert and group each detached row once for all reconstruction consumers."""
    if isinstance(rows, PreparedRecordProjection):
        return rows
    records: dict[Any, dict[Any, list[Mapping[str, Any]]]] = {}
    reports: dict[int, list[Mapping[str, Any]]] = {}
    members: dict[int, list[Mapping[str, Any]]] = {}
    for name in RECORD_ROW_TYPES:
        for value in rows[name]:
            row = MappingProxyType(dict(value) if isinstance(value, Mapping) else asdict(value))
            if name == "record_report":
                reports.setdefault(row["selected_task_id"], []).append(row)
                continue
            if name == "record_report_member":
                members.setdefault(row["selected_task_id"], []).append(row)
                continue
            groups = records.setdefault((row["record_id"], row["interpretation_id"]), {})
            groups.setdefault((name, ()), []).append(row)
            if keys := _RECONSTRUCTION_GROUPS.get(name):
                selector = tuple((key, row[key]) for key in keys)
                groups.setdefault((name, selector), []).append(row)

    def ordered(values):
        return tuple(sorted(values, key=lambda row: row.get("position", 0)))

    return PreparedRecordProjection(
        MappingProxyType(
            {
                key: MappingProxyType({group: ordered(values) for group, values in groups.items()})
                for key, groups in records.items()
            }
        ),
        MappingProxyType({task: tuple(values) for task, values in reports.items()}),
        MappingProxyType({task: ordered(values) for task, values in members.items()}),
    )


def reconstruct_record(
    rows: Mapping[str, Any] | PreparedRecordProjection,
    record_id: str,
    interpretation_id: str,
) -> dict[str, Any]:
    """Stable consumer boundary: reconstruct one source report without graph relabelling."""

    index = index_record_projection(rows)

    def selected(name, **where):
        return index.rows_for(record_id, interpretation_id, name, **where)

    def scalar(row, pieces):
        kind = row["value_kind"]
        if kind is None:
            return None
        if row["classification"] is not None:
            return dict(kind=kind, label=row["classification"])
        if kind == "text_sequence":
            return dict(
                kind=kind,
                items=tuple(
                    piece["value_piece"] for piece in pieces if piece["value_piece"] is not None
                ),
            )
        field = {
            "text": "text_value",
            "decimal": "decimal_lexical",
            "classification": "classification",
            "native_location": "native_pointer",
        }.get(kind)
        if field is None:
            raise ValueError("unsupported finite record scalar")
        return dict(
            kind=kind,
            **{
                {
                    "text": "text",
                    "decimal": "lexical",
                    "classification": "label",
                    "native_location": "pointer",
                }[kind]: row[field]
            },
        )

    roots = selected("source_record")
    if len(roots) != 1:
        raise ValueError("record interpretation is unavailable or duplicated")
    root = roots[0]
    record = {
        k: root[k]
        for k in (
            "record_id",
            "interpretation_id",
            "contract",
            "family",
            "occurrence_recipe",
            "standing",
            "policy_version",
        )
    }
    record["pin"] = _pin(root)
    anchors = []
    for row in selected("record_anchor"):
        anchor = {k: row[k] for k in ("anchor_id", "space", "pointer", "precision")}
        anchor["pin"] = _pin(row)
        anchor.update({k: row[k] for k in ("start", "end", "source_piece") if row[k] is not None})
        if row["binding_version"] is not None:
            anchor["binding"] = {name: row["binding_" + name] for name in _BINDING_FIELDS}
        if row["recognition_task_id"] is not None:
            anchor["recognition"] = {
                name: row["recognition_" + name] for name in _RECOGNITION_FIELDS
            }
        anchors.append(anchor)
    record["anchors"] = tuple(anchors)
    record["occurrence_anchors"] = tuple(
        row["anchor_id"] for row in selected("record_occurrence_anchor")
    )
    output_fields = []
    for row in selected("record_field"):
        role = row["role"]
        field = {
            k: row[k] for k in ("role", "kind", "state", "meaning_changing", "evidence_status")
        }
        pieces = selected("record_field_piece", role=role)
        value = scalar(row, pieces)
        if value is not None:
            field["value"] = value
        field.update(
            {k: row[k] for k in ("original", "reason", "policy", "rule") if row[k] is not None}
        )
        if row["original_pieces_present"]:
            field["original_pieces"] = tuple(
                piece["original_piece"] for piece in pieces if piece["original_piece"] is not None
            )
        for key, relation, column in (
            ("evidence_sets", "record_field_evidence", "set_id"),
            ("premises", "record_premise", "premise_role"),
        ):
            if row[key + "_present"]:
                field[key] = tuple(link[column] for link in selected(relation, role=role))
        if row["alternatives_present"]:
            alternatives = []
            for alternative in selected("record_alternative", role=role):
                aid = alternative["alternative_id"]
                item = dict(
                    alternative_id=aid,
                    reason=alternative["reason"],
                    value=scalar(
                        alternative,
                        selected("record_alternative_piece", role=role, alternative_id=aid),
                    ),
                )
                if alternative["evidence_sets_present"]:
                    item["evidence_sets"] = tuple(
                        link["set_id"]
                        for link in selected(
                            "record_alternative_evidence", role=role, alternative_id=aid
                        )
                    )
                alternatives.append(item)
            field["alternatives"] = tuple(alternatives)
        output_fields.append(field)
    record["fields"] = tuple(output_fields)
    if root["evidence_sets_present"]:
        record["evidence_sets"] = tuple(
            dict(
                set_id=row["set_id"],
                role=row["role"],
                ordering=row["ordering"],
                usage=row["usage"],
                anchors=tuple(
                    member["anchor_id"]
                    for member in selected("record_evidence_member", set_id=row["set_id"])
                ),
            )
            for row in selected("record_evidence_set")
        )
    for key, relation, column in (
        ("computation_dependencies", "record_dependency", "dependency"),
        ("assertion_members", "record_private_assertion", "assertion_ref"),
    ):
        if root[key + "_present"]:
            record[key] = tuple(row[column] for row in selected(relation))
    return record
