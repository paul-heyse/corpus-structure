"""Complete private SourceRecord alternatives under exact selected native roots.

The captured nominal schema owns each reading body. These DTOs own only grouping
and provenance; they do not declare a second field ontology or accepted standing.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_json import DdoJsonValue, json_bytes, json_loads
from .data_operation_model import json_context_meaning
from .declared_candidate_products import candidate_member_id, candidate_member_values
from .record_contracts import interpretation_identity, record_family_contract, record_identity
from .rich_knowledge_contracts import DdoRichContext, DdoRichSelectedMember

if TYPE_CHECKING:
    from collections.abc import Sequence

    from corpus_structure.semantic.selected_contribution_input import SelectedContribution

    from .data_operation_model import EffectiveDataOperationModel
    from .types import PreparedRelease

Nonempty = Annotated[str, Field(min_length=1)]


class GroupedRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class InterpretationRoot(GroupedRecord):
    product_id: Nonempty
    member_id: Nonempty | None = None
    interpretation_id: Nonempty | None = None


class AuthoredJudgmentRead(GroupedRecord):
    """Explicit independent authored input read; its scope is part of the pinned cut."""

    demand_id: Nonempty
    read_id: Nonempty
    expected_cut: Nonempty
    scope: dict[str, DdoJsonValue]
    product_ids: Annotated[tuple[Nonempty, ...], Field(min_length=1, max_length=100)]


class GroupedInterpretationRequest(GroupedRecord):
    project_id: Nonempty
    demand_id: Nonempty
    roots: Annotated[tuple[InterpretationRoot, ...], Field(min_length=1, max_length=100)]
    authored_products: Annotated[tuple[Nonempty, ...], Field(max_length=100)] = ()
    authored_reads: Annotated[tuple[AuthoredJudgmentRead, ...], Field(max_length=100)] = ()
    read_id: Nonempty | None = None
    expected_cut: Nonempty | None = None
    operation_id: Nonempty | None = None
    subject: Nonempty | None = None
    original_source: Nonempty | None = None
    # The existing acquisition owner uses these bounds independently of output paging.
    max_graph_bytes: int = Field(default=8388608, strict=True, ge=1024, le=67108864)
    max_graph_records: int = Field(default=100000, strict=True, ge=1, le=1000000)
    max_support_edges: int = Field(default=100000, strict=True, ge=1, le=1000000)
    implementation: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    cursor: str | None = Field(default=None, max_length=32768)
    limit: int = Field(default=20, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=1048576, strict=True, ge=1024, le=67108864)

    @model_validator(mode="after")
    def pinned_read(self):
        if (self.read_id is None) != (self.expected_cut is None):
            raise ValueError("grouped interpretation read requires both read_id and expected_cut")
        return self

    @property
    def product_id(self):
        return None

    def selection(self):
        value = self.model_dump(
            mode="python",
            exclude={"read_id", "expected_cut", "implementation", "cursor", "limit", "max_bytes"},
        )
        if "original_source" not in self.model_fields_set:
            value.pop("original_source")
        return value


class RetainedReading(GroupedRecord):
    reference: DdoRichSelectedMember
    interpretation_id: Nonempty
    body: dict[str, DdoJsonValue]
    reading_events: tuple[dict[str, DdoJsonValue], ...] = ()


class RetainedFiniteInterpretation(GroupedRecord):
    reference: DdoRichSelectedMember
    report: dict[str, DdoJsonValue]


class RetainedAuthoredJudgment(GroupedRecord):
    reference: DdoRichSelectedMember
    author: Nonempty = Field(
        description="Author assertion from the immutable AuthoredFactRef; the support reference identifies actual native admission."
    )
    selection_id: Nonempty
    source_reference: Nonempty
    body: dict[str, DdoJsonValue]
    standing: Literal["private_authored_judgment"] = "private_authored_judgment"


class RecordInterpretationGroup(GroupedRecord):
    identity: Nonempty
    record_id: Nonempty
    family: Nonempty
    family_contract: Nonempty
    context: DdoRichContext
    candidate_universe: DdoRichSelectedMember
    readings: tuple[RetainedReading, ...]
    finite_interpretations: tuple[RetainedFiniteInterpretation, ...] = ()
    authored_judgments: tuple[RetainedAuthoredJudgment, ...] = ()
    dependency_coverage: Literal["recorded", "unknown"] = Field(
        description="Presence of dependency lists on every retained reading; recorded does not establish exhaustive provenance."
    )
    computation_dependencies: tuple[str, ...]
    retained_input_digest: Nonempty
    standing: Literal["private_uncalibrated_candidates"] = "private_uncalibrated_candidates"
    alternatives_complete_within: Literal["selected_candidate_product"] = (
        "selected_candidate_product"
    )


def grouped_candidate_product(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    selected: SelectedContribution,
    roots: Sequence[InterpretationRoot],
) -> tuple[RecordInterpretationGroup, ...]:
    """Validate one complete captured report, then select whole occurrence groups.

    A member/reading selector identifies an occurrence. It never truncates that
    occurrence's alternatives or implies completeness outside the selected product.
    """
    from corpus_structure.methods.record_readings import retained_reading_groups

    from .reading_resolution_products import resolved_reading_events

    definition = next(
        (value for value in prepared.definitions if value.iri == selected.nominal), None
    )
    if definition is None or not (
        definition.name == "DdoCandidateInspectionReport"
        or "DdoCandidateInspectionReport" in definition.ancestors
    ):
        raise ValueError("grouped interpretation root is not a captured candidate report")
    report = prepared.validate_json(definition.name, json_bytes(selected.body)).model_dump(
        mode="python", exclude_unset=True
    )
    if report["standing"] != "private_uncalibrated_candidates":
        raise ValueError("grouped interpretations require private candidate standing")
    context = DdoRichContext(
        subject=selected.context.subject,
        subject_definition=selected.context.subject_definition,
        original_source=selected.context.original_source,
        analyzed_scope=json_loads(selected.context.analyzed_scope),
    )
    pin = report["source_pin"]
    if (
        pin["project_id"],
        pin["subject"],
        pin["subject_definition"],
        pin["original_source"],
        pin["analyzed_scope_meaning"],
    ) != (
        selected.context.project_id,
        context.subject,
        context.subject_definition,
        context.original_source,
        json_context_meaning(selected.context.analyzed_scope).decode(),
    ):
        raise ValueError("candidate universe differs from its selected source context")
    packets = {packet["member_id"]: packet for packet in report["members"]}
    if len(packets) != len(report["members"]):
        raise ValueError("candidate universe repeats a member identity")
    definitions = {value.iri: value for value in prepared.definitions}
    nominal_contracts = {
        value.key: definitions[value.owner]
        for value in model.identities
        if value.domain == "kind" and value.owner in definitions
    }
    for packet in packets.values():
        nominal = nominal_contracts.get(packet["kind_contract"])
        if nominal is None or not (
            nominal.name == "DdoCandidateValue" or "DdoCandidateValue" in nominal.ancestors
        ):
            raise ValueError("candidate packet lacks its actual captured nominal kind")
        checked = prepared.validate_json(nominal.name, json_bytes(packet["body"])).model_dump(
            mode="python", exclude_unset=True
        )
        if json_bytes(checked) != json_bytes(packet["body"]):
            raise ValueError("candidate packet differs from its captured concrete kind")
    records = candidate_member_values(report, candidate_type="record")
    partitions = defaultdict(list)
    for row in records:
        family_contract = record_family_contract(model, row["contract"])
        fields = {value["role"]: value for value in row["fields"]}
        if len(fields) != len(row["fields"]):
            raise ValueError("candidate reading repeats a field role")
        prepared.validate_json(
            row["contract"],
            json_bytes(
                {
                    "family": row["family"],
                    "occurrence_recipe": row["occurrence_recipe"],
                    **fields,
                }
            ),
        )
        if row["record_id"] != record_identity(family_contract, row) or row[
            "interpretation_id"
        ] != interpretation_identity(row):
            raise ValueError(
                "candidate reading differs from its exact occurrence or reading identity"
            )
        if json_bytes(row["pin"]) != json_bytes(pin):
            raise ValueError("candidate reading differs from its complete source universe")
        packet = packets[candidate_member_id("record", row)]
        if json_bytes(packet["context"]) != json_bytes(context.model_dump(mode="python")):
            raise ValueError("candidate reading differs from its selected member context")
        partitions[family_contract].append(row)
    events = ()
    if (
        definition.name == "DdoResolvedReadingReport"
        or "DdoResolvedReadingReport" in definition.ancestors
    ):
        events = resolved_reading_events(report)
    event_map = defaultdict(list)
    identities = {(row["record_id"], row["interpretation_id"]) for row in records}
    for event in events:
        key = event["record_id"], event["interpretation_id"]
        if key not in identities or event_map[key]:
            raise ValueError("resolved event is duplicated or outside its candidate universe")
        event_map[key].append(event)
    selected_groups = set()
    for root in roots:
        if root.product_id != selected.reference.product_id:
            raise ValueError("interpretation root differs from the selected candidate universe")
        if root.member_id is not None and root.member_id not in packets:
            raise ValueError("selected interpretation member is outside its candidate universe")
        matched = [
            row
            for row in records
            if (root.member_id is None or candidate_member_id("record", row) == root.member_id)
            and (
                root.interpretation_id is None or row["interpretation_id"] == root.interpretation_id
            )
        ]
        if (root.member_id is not None or root.interpretation_id is not None) and not matched:
            raise ValueError("selected interpretation root does not identify a retained reading")
        selected_groups.update(
            (record_family_contract(model, row["contract"]), row["record_id"]) for row in matched
        )
    result = []
    for family_contract, rows in sorted(partitions.items()):
        for group in retained_reading_groups(rows):
            if (family_contract, group.record_id) not in selected_groups:
                continue
            readings = []
            for row in group.readings:
                packet = packets[candidate_member_id("record", row)]
                readings.append(
                    RetainedReading(
                        reference=DdoRichSelectedMember(
                            product_id=selected.reference.product_id,
                            member_id=packet["member_id"],
                            kind_contract=packet["kind_contract"],
                            support_references=selected.reference.support_references,
                        ),
                        interpretation_id=row["interpretation_id"],
                        body=dict(row),
                        reading_events=tuple(event_map[group.record_id, row["interpretation_id"]]),
                    )
                )
            identity = sha256(
                json_bytes(
                    [
                        selected.reference.model_dump(mode="python"),
                        context.model_dump(mode="python"),
                        family_contract,
                        group.record_id,
                    ]
                )
            ).hexdigest()
            result.append(
                RecordInterpretationGroup(
                    identity=identity,
                    record_id=group.record_id,
                    family=group.family,
                    family_contract=family_contract,
                    context=context,
                    candidate_universe=selected.reference,
                    readings=tuple(readings),
                    dependency_coverage=(
                        "recorded"
                        if all("computation_dependencies" in row for row in group.readings)
                        else "unknown"
                    ),
                    computation_dependencies=group.dependencies,
                    retained_input_digest=group.input_digest,
                )
            )
    return tuple(result)


def attach_finite_interpretations(prepared, selected, groups, *, candidate_product_id):
    """Attach actual record-mode reports only to their exact bound candidate universe."""
    from .finite_interpretation_products import finite_interpretation_reports

    definition = next(
        (value for value in prepared.definitions if value.iri == selected.nominal), None
    )
    if definition is None or not (
        definition.name == "DdoFiniteInterpretationProduct"
        or "DdoFiniteInterpretationProduct" in definition.ancestors
    ):
        raise ValueError("finite root lacks its captured interpretation product kind")
    product = prepared.validate_json(definition.name, json_bytes(selected.body)).model_dump(
        mode="python", exclude_unset=True
    )
    if product["mode"] != "records":
        raise ValueError("occurrence grouping requires actual record-mode finite interpretation")
    reports = finite_interpretation_reports(product)
    by_record = {}
    for report in reports:
        record_id = report["record_id"]
        if record_id in by_record:
            raise ValueError("finite interpretation repeats an occurrence report")
        by_record[record_id] = report
    result = []
    for group in groups:
        if group.candidate_universe.product_id != candidate_product_id:
            result.append(group)
            continue
        if json_bytes(product["source_pin"]) != json_bytes(group.readings[0].body["pin"]):
            raise ValueError("finite interpretation differs from its actual source universe")
        report = by_record.get(group.record_id)
        if report is not None:
            if (
                report["family"] != group.family
                or report["retained_input_digest"] != group.retained_input_digest
                or sorted(report["interpretation_ids"])
                != sorted(row.interpretation_id for row in group.readings)
            ):
                raise ValueError(
                    "finite interpretation differs from the complete retained readings"
                )
            value = RetainedFiniteInterpretation(reference=selected.reference, report=report)
            group = group.model_copy(
                update={"finite_interpretations": (*group.finite_interpretations, value)}
            )
        result.append(group)
    return tuple(result)
