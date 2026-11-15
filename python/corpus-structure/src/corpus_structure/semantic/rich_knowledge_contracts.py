"""Closed current rich graph members; source assertions and scientific facts stay distinct."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_json import DdoJsonValue
from .data_operation_model import EffectiveDataOperationModel, SubjectContext

Nonempty = Annotated[str, Field(min_length=1)]


class RichRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DdoRichContext(RichRecord):
    subject: Nonempty
    subject_definition: Nonempty
    original_source: Nonempty | None
    analyzed_scope: DdoJsonValue


class DdoRichSelectedMember(RichRecord):
    product_id: Nonempty
    member_id: Nonempty | None
    kind_contract: Nonempty


class DdoRichValueEntry(RichRecord):
    name: Nonempty
    position: Annotated[int, Field(ge=0)]
    value_id: Nonempty


class DdoRichPropertyValue(RichRecord):
    property_contract: Nonempty
    value_id: Nonempty


class DdoRichScalarValue(RichRecord):
    member_type: Literal["scalar-value"]
    value_id: Nonempty
    kind_contract: Nonempty
    datatype: Literal["string", "boolean", "integer", "decimal", "float", "date", "datetime"]
    lexical: str

    @model_validator(mode="after")
    def actual_canonical_scalar(self):
        from datetime import date, datetime
        from decimal import Decimal
        from .value_codec import value_meaning

        if self.datatype == "string":
            return self
        if self.datatype == "boolean":
            if self.lexical not in {"true", "false"}:
                raise ValueError("rich boolean requires its canonical literal")
            return self
        parser = {"integer": int, "decimal": Decimal, "float": float.fromhex,
                  "date": date.fromisoformat, "datetime": datetime.fromisoformat}[self.datatype]
        meaning = value_meaning(parser(self.lexical))
        if meaning != [self.datatype, self.lexical]:
            raise ValueError("rich scalar differs from its canonical declared meaning")
        return self


class DdoRichEntityValue(RichRecord):
    member_type: Literal["entity-value"]
    value_id: Nonempty
    kind_contract: Nonempty
    entity_id: Nonempty


class DdoRichRecordValue(RichRecord):
    member_type: Literal["record-value"]
    value_id: Nonempty
    kind_contract: Nonempty
    fields: tuple[DdoRichPropertyValue, ...]


class DdoRichCollectionValue(RichRecord):
    member_type: Literal["collection-value"]
    value_id: Nonempty
    element_contract: Nonempty
    collection: Literal["sequence", "mapping"]
    entries: tuple[DdoRichValueEntry, ...]


class DdoRichCasefoldText(RichRecord):
    """Policy equality value; never labelled as the source enum/property value."""
    member_type: Literal["casefold-text"]
    value_id: Nonempty
    property_contract: Nonempty
    text: str


class DdoRichQualificationMeaning(RichRecord):
    member_type: Literal["qualification-meaning"]
    value_id: Nonempty
    qualification_contract: Nonempty
    fields: tuple[DdoRichPropertyValue, ...]


class DdoRichEntity(RichRecord):
    member_type: Literal["entity"]
    entity_id: Nonempty
    class_contracts: Annotated[tuple[Nonempty, ...], Field(min_length=1)]
    source_members: tuple[DdoRichSelectedMember, ...]


class DdoRichFact(RichRecord):
    """Property meaning, independent of whether a source asserts or supports it."""
    member_type: Literal["fact"]
    fact_id: Nonempty
    subject_entity: Nonempty
    property_contract: Nonempty
    predicate: Nonempty
    object_value: Nonempty
    qualification_meaning: Nonempty


class DdoRichOccurrence(RichRecord):
    member_type: Literal["source-occurrence"]
    occurrence_id: Nonempty
    fact_id: Nonempty
    original: DdoRichSelectedMember
    statement: DdoRichSelectedMember | None
    observed_qualification_value: Nonempty
    dependencies: tuple[Nonempty, ...]


class DdoRichSourceReadingAssertion(RichRecord):
    """An assertion about a retained reading, without scientific claim standing."""
    member_type: Literal["source-reading-assertion"]
    reading_id: Nonempty
    record_id: Nonempty
    interpretation_id: Nonempty
    original: DdoRichSelectedMember
    reading_value: Nonempty


class DdoRichAlternative(RichRecord):
    member_type: Literal["alternative"]
    alternative_id: Nonempty
    fact_ids: Annotated[tuple[Nonempty, ...], Field(min_length=2)]
    origin: Literal["source-proposal", "value-disagreement"]
    faithful: bool
    reason: Nonempty
    source_members: tuple[DdoRichSelectedMember, ...]


class DdoRichAssessment(RichRecord):
    member_type: Literal["assessment"]
    assessment_id: Nonempty
    occurrences: Annotated[tuple[Nonempty, ...], Field(min_length=1)]
    rule: Nonempty
    outcome: Literal["equivalent", "different", "undecided", "valid", "invalid", "not-applicable"]
    reason: Nonempty
    evidence_members: tuple[DdoRichSelectedMember, ...]


class DdoRichDiagnostic(RichRecord):
    member_type: Literal["diagnostic"]
    diagnostic_id: Nonempty
    code: Nonempty
    reason: Nonempty
    source_members: tuple[DdoRichSelectedMember, ...]


type DdoRichMemberBody = (
    DdoRichScalarValue | DdoRichEntityValue | DdoRichRecordValue | DdoRichCollectionValue
    | DdoRichCasefoldText | DdoRichQualificationMeaning
    | DdoRichEntity | DdoRichFact | DdoRichOccurrence | DdoRichSourceReadingAssertion
    | DdoRichAlternative | DdoRichAssessment | DdoRichDiagnostic
)


class DdoRichPacket(RichRecord):
    member_id: Nonempty
    kind_contract: Nonempty
    context: DdoRichContext
    body: DdoRichMemberBody


class DdoRichContextPin(RichRecord):
    """Internal CPU custody, using the existing exact tagged context meaning."""
    project_id: Nonempty
    subject: Nonempty
    subject_definition: Nonempty
    original_source: Nonempty | None
    analyzed_scope_meaning: Nonempty


class DdoRichComputedMember(RichRecord):
    member_id: Nonempty
    kind_contract: Nonempty
    context_pin: DdoRichContextPin
    body: DdoRichMemberBody


class DdoRichComputation(RichRecord):
    """Prepared kernel result, never a native/public product packet."""
    version: Literal["rich-computation-1"]
    members: tuple[DdoRichComputedMember, ...]
    input_population: tuple[DdoRichSelectedMember, ...]


class DdoRichConsolidation(RichRecord):
    version: Literal["rich-consolidation-1"]
    standing: Literal["private-consolidated"]
    members: tuple[DdoRichPacket, ...]
    input_population: tuple[DdoRichSelectedMember, ...]


class DdoRichAdmission(RichRecord):
    version: Literal["rich-admission-1"]
    standing: Literal["accepted"]
    members: tuple[DdoRichPacket, ...]
    consolidation: DdoRichSelectedMember
    policy_authorizations: tuple[DdoRichSelectedMember, ...]


def rich_context_pin(context: SubjectContext) -> DdoRichContextPin:
    from .data_operation_model import json_context_meaning

    return DdoRichContextPin(
        project_id=context.project_id, subject=context.subject,
        subject_definition=context.subject_definition, original_source=context.original_source,
        analyzed_scope_meaning=json_context_meaning(context.analyzed_scope).decode(),
    )


def materialize_rich_context(pin: DdoRichContextPin, model: EffectiveDataOperationModel, *, expected_context: SubjectContext) -> DdoRichContext:
    """Recover actual JSON only against the invocation's selected authentic context."""
    from .data_operation_identity import decode_semantic_value
    from .data_operation_json import json_loads, json_bytes
    from .data_operation_model import SubjectContext, validate_subject_context
    from .identity import canonical_bytes

    scope = decode_semantic_value(json_loads(pin.analyzed_scope_meaning))
    context = SubjectContext(
        project_id=pin.project_id, subject=pin.subject, subject_definition=pin.subject_definition,
        original_source=pin.original_source, analyzed_scope=json_bytes(scope),
    )
    validate_subject_context(model, context)
    validate_subject_context(model, expected_context)
    if context != expected_context:
        raise ValueError("rich computed context differs from its actual selected invocation/source")
    return DdoRichContext(
        subject=context.subject, subject_definition=context.subject_definition,
        original_source=context.original_source, analyzed_scope=json_loads(context.analyzed_scope),
    )


def rich_kind_declarations():
    """Capture supplied DTO schemas through the existing single nominal owner."""
    from .nominal_schema_kinds import nominal_schema_kinds

    namespace = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    records = {}
    for owner in (DdoRichConsolidation, DdoRichAdmission):
        for record in nominal_schema_kinds(owner.model_json_schema(), namespace=namespace, root_name=owner.__name__):
            previous = records.get(record["id"])
            if previous is not None and previous != record:
                raise ValueError("rich contract schemas disagree about their shared nominal owner")
            records[record["id"]] = record
    return tuple(records[key] for key in sorted(records))
