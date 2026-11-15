"""Closed current rich graph members; source assertions and scientific facts stay distinct."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_json import DdoJsonValue
from .data_operation_model import EffectiveDataOperationModel, SubjectContext
from .data_operation_support import SupportReference, read_support_references, support_reference_records

Nonempty = Annotated[str, Field(min_length=1)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


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
    support_references: Annotated[tuple[SupportReference, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def normalized_support(self):
        references = rich_support_records(self.support_references)
        object.__setattr__(self, "support_references", read_support_references(references))
        return self


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


class DdoRichEntityIdentity(RichRecord):
    """An actual class/key/label basis, retained for a later closed-universe join."""
    class_contract: Nonempty
    fields: tuple[DdoRichPropertyValue, ...]
    label: str | None


class DdoRichEntity(RichRecord):
    member_type: Literal["entity"]
    entity_id: Nonempty
    class_contracts: Annotated[tuple[Nonempty, ...], Field(min_length=1)]
    identities: Annotated[tuple[DdoRichEntityIdentity, ...], Field(min_length=1)]
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
    source_interpretation_id: Nonempty
    interpretation_id: Nonempty
    original: DdoRichSelectedMember
    resolution: DdoRichSelectedMember
    resolved: DdoRichSelectedMember
    reading_value: Nonempty

    @model_validator(mode="after")
    def actual_record_selection(self):
        if self.original.member_id is None or self.resolved.member_id is None or self.resolution.member_id is not None:
            raise ValueError("rich source reading requires raw/resolved members and a whole resolution report")
        if (self.resolved.product_id, self.resolved.support_references) != (self.resolution.product_id, self.resolution.support_references):
            raise ValueError("resolved reading differs from its actual whole-report support")
        return self


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


class DdoRichAuthoredPropositions(RichRecord):
    """Explicit typed propositions; actual authored admission supplies their origin."""
    version: Literal["rich-authored-propositions-1"]
    standing: Literal["authored-propositions"]
    members: tuple[DdoRichPacket, ...]


class DdoRichConsolidationPolicy(RichRecord):
    version: Literal["rich-consolidation-policy-1"]
    qualification_contract: Nonempty
    statement_contract: Nonempty
    rules_digest: Digest
    scientific_digest: Digest
    analysis_profile_digest: Digest


class DdoRichReadingDecision(RichRecord):
    original: DdoRichSelectedMember
    resolution: DdoRichSelectedMember | None
    resolved: DdoRichSelectedMember | None
    record_id: Nonempty
    source_interpretation_id: Nonempty
    interpretation_id: Nonempty | None
    authorization: DdoRichSelectedMember | None
    outcome: Literal["accepted", "below-threshold", "not-checkable"]
    feature_input_digest: Digest | None
    feature_instance_digest: Digest | None
    event_procedure: Nonempty | None
    score_hex: Nonempty | None
    probability_hex: Nonempty | None
    reason_code: Literal["authorized-final-event-threshold", "below-threshold", "policy-unavailable", "ambiguous-policy", "unavailable-feature-instance", "incomplete-source-reading", "invalid-final-event", "resolution-unavailable"]
    assertion_member_id: Nonempty | None

    @model_validator(mode="after")
    def actual_application_shape(self):
        import math

        if self.original.member_id is None:
            raise ValueError("reading decision requires its actual raw member selection")
        unresolved = self.resolution is None or self.resolved is None or self.interpretation_id is None
        if unresolved:
            if any(value is not None for value in (self.resolution, self.resolved, self.interpretation_id)):
                raise ValueError("missing resolution cannot retain a fabricated partial selection")
            if self.outcome != "not-checkable" or self.reason_code != "resolution-unavailable":
                raise ValueError("missing resolution requires an explicit uncheckable decision")
            if any(value is not None for value in (self.authorization, self.feature_input_digest,
                   self.feature_instance_digest, self.event_procedure, self.score_hex, self.probability_hex)):
                raise ValueError("missing resolution cannot claim a policy/event basis")
        else:
            assert self.resolved is not None and self.resolution is not None
            if self.resolved.member_id is None or self.resolution.member_id is not None:
                raise ValueError("reading decision requires actual raw/resolved member selections")
            if (self.resolved.product_id, self.resolved.support_references) != (self.resolution.product_id, self.resolution.support_references):
                raise ValueError("reading decision differs from its actual resolution report")
            if self.reason_code == "resolution-unavailable":
                raise ValueError("an actual resolution cannot claim to be unavailable")
        for value in (self.score_hex, self.probability_hex):
            if value is not None and (not math.isfinite(float.fromhex(value)) or float.fromhex(value).hex() != value):
                raise ValueError("reading decision requires canonical finite float meanings")
        if self.probability_hex is not None and not 0 <= float.fromhex(self.probability_hex) <= 1:
            raise ValueError("reading decision probability is outside its actual range")
        if self.outcome in {"accepted", "below-threshold"} and any(value is None for value in (
            self.authorization, self.feature_input_digest, self.feature_instance_digest,
            self.event_procedure, self.score_hex, self.probability_hex,
        )):
            raise ValueError("scored reading decision lacks its actual policy/event basis")
        if (self.outcome == "accepted") != (self.assertion_member_id is not None):
            raise ValueError("only an accepted reading can retain its assertion member")
        expected = {"accepted": "authorized-final-event-threshold", "below-threshold": "below-threshold"}
        if self.outcome in expected and self.reason_code != expected[self.outcome]:
            raise ValueError("reading decision reason differs from its actual outcome")
        if self.outcome == "not-checkable" and self.reason_code in expected.values():
            raise ValueError("uncheckable reading cannot claim a threshold decision")
        return self


class DdoRichAdmission(RichRecord):
    version: Literal["rich-admission-1"]
    standing: Literal["accepted"]
    members: tuple[DdoRichPacket, ...]
    consolidation: DdoRichSelectedMember
    policy_authorizations: tuple[DdoRichSelectedMember, ...]
    reading_decisions: tuple[DdoRichReadingDecision, ...]



def rich_support_records(references: tuple[SupportReference, ...]) -> list[dict]:
    from .data_operation_identity import semantic_value
    from .identity import canonical_bytes

    unique = {canonical_bytes(semantic_value(record)): record for record in support_reference_records(references)}
    return [unique[key] for key in sorted(unique)]


def rich_reference_key(reference: DdoRichSelectedMember) -> bytes:
    from .identity import canonical_bytes
    return canonical_bytes([reference.product_id, reference.member_id, reference.kind_contract,
                            rich_support_records(reference.support_references)])


def rich_selected_member(member) -> DdoRichSelectedMember:
    """Copy actual frozen binding value/support facts, without choosing a producer."""
    return DdoRichSelectedMember.model_validate({
        "product_id": member.product, "member_id": member.member, "kind_contract": member.kind_contract,
        "support_references": tuple(rich_support_records(member.support_references)),
    }, strict=True)


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
    for owner in (DdoRichConsolidation, DdoRichAdmission, DdoRichAuthoredPropositions, DdoRichConsolidationPolicy):
        for record in nominal_schema_kinds(owner.model_json_schema(), namespace=namespace, root_name=owner.__name__):
            previous = records.get(record["id"])
            if previous is not None and previous != record:
                raise ValueError("rich contract schemas disagree about their shared nominal owner")
            records[record["id"]] = record
    return tuple(records[key] for key in sorted(records))
