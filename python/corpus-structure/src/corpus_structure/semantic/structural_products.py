"""Private cross-source products with original custody and explicit semantic limits.

These values are reports, not admission witnesses. Their source references must be
validated against admitted product context; model validation alone grants no authority.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import ConfigDict, Field, JsonValue, TypeAdapter, model_validator

from .artifact_identity import (
    ArtifactAliasSpan,
    ArtifactCitation,
    ArtifactPair,
    ArtifactPairKey,
    ArtifactReferenceResolution,
    ArtifactRouteCount,
    ArtifactScoringPolicy,
    ArtifactSourceLabel,
    artifact_identity_invariants,
    artifact_nomination_invariants,
    source_artifact_invariants,
)
from .declared_structural_references import (
    DeclaredComponentRef,
    DeclaredContributionRef,
    DeclaredProductRef,
    DeclaredRelationshipRef,
    DeclaredStructuralRef,
    DeclaredStructuralSource,
)
from .identity import canonical_bytes
from .structural_base import StructuralValue

Positive = Annotated[int, Field(strict=True, gt=0)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Nonempty = Annotated[str, Field(min_length=1)]
Dimension = Literal[
    "actor",
    "action",
    "object",
    "modality",
    "condition",
    "threshold_unit",
    "exception",
    "order_dependency",
    "parent",
    "version",
]
DIMENSIONS: tuple[Dimension, ...] = (
    "actor",
    "action",
    "object",
    "modality",
    "condition",
    "threshold_unit",
    "exception",
    "order_dependency",
    "parent",
    "version",
)


class StructuralPassage(StructuralValue):
    passage_id: Nonempty
    source_ref: Nonempty
    start: Annotated[int, Field(strict=True, ge=0)]
    end: Positive
    text: Nonempty
    scope: Nonempty
    effective_version: str | None = None
    parent: str | None = None

    @model_validator(mode="after")
    def extent(self) -> Self:
        if self.end <= self.start or self.end - self.start != len(self.text):
            raise ValueError("passage text must equal its exact projected extent")
        return self


class StructuralExclusion(StructuralValue):
    left: Nonempty
    right: Nonempty


class LocatedDefinitionSpan(StructuralValue):
    passage_id: Nonempty
    start: Annotated[int, Field(strict=True, ge=0)]
    end: Positive
    text: Nonempty

    @model_validator(mode="after")
    def extent(self) -> Self:
        if self.end - self.start != len(self.text):
            raise ValueError("definition span text differs from exact extent")
        return self


DefinitionInterpretation = Literal["definition", "explanation", "unresolved"]


class DeclarationChainBinding(StructuralValue):
    frame: Nonempty
    subject_token: Annotated[int, Field(strict=True, ge=0)]
    use_token: Annotated[int, Field(strict=True, ge=0)]


def _make_definition_component(value_type, meaning):
    wire = {key: value for key, value in meaning.items() if value is not None}
    wire.setdefault("alternatives", ())
    wire = {
        key: (
            value.model_dump(mode="json", exclude_none=True)
            if isinstance(value, StructuralValue)
            else value
        )
        for key, value in wire.items()
    }
    return value_type.model_validate(
        dict(component_id=sha256(canonical_bytes(wire)).hexdigest(), **wire)
    )


class DefinitionStage(StructuralValue):
    passage_id: Nonempty
    operation: Literal["located_extraction", "attachment", "usage_applicability"]
    outcome: Literal["succeeded", "empty", "unavailable", "failed", "not_run"]
    reason: Nonempty


class DefinitionRoleCandidate(StructuralValue):
    """Exactly located provider proposal with immutable envelope coordinates."""

    role: Literal["term", "content"]
    span: LocatedDefinitionSpan
    window_start: Annotated[int, Field(strict=True, ge=0)]
    window_end: Positive
    envelope: Nonempty
    index: Annotated[int, Field(strict=True, ge=0)]

    @model_validator(mode="after")
    def within_window(self) -> Self:
        if not self.window_start <= self.span.start < self.span.end <= self.window_end:
            raise ValueError("definition role lies outside its provider window")
        return self


class ClauseModelLabel(StructuralValue):
    label: Nonempty
    score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    accepted: bool


class ApplicabilityPremise(StructuralValue):
    dimension: Literal["scope", "parent", "parameterization", "convention", "version", "sense"]
    state: Literal["compatible", "incompatible", "unknown", "inapplicable"]
    evidence: tuple[Nonempty, ...]
    reason: Nonempty


DefinitionOutcome = Literal[
    "applicable_definition",
    "applicable_explanation",
    "mention",
    "example",
    "incompatible",
    "unresolved",
]


class TriggerInterval(StructuralValue):
    lower: str | None = None
    upper: str | None = None
    lower_closed: bool = False
    upper_closed: bool = False

    @model_validator(mode="after")
    def finite_extent(self) -> Self:
        from decimal import Decimal, InvalidOperation

        try:
            lo = Decimal(self.lower) if self.lower is not None else None
            hi = Decimal(self.upper) if self.upper is not None else None
            if any(value is not None and not value.is_finite() for value in (lo, hi)):
                raise ValueError("interval endpoints must be finite")
            if (
                lo is not None
                and hi is not None
                and (lo > hi or (lo == hi and not (self.lower_closed and self.upper_closed)))
            ):
                raise ValueError("empty or reversed interval")
            if (lo is None and self.lower_closed) or (hi is None and self.upper_closed):
                raise ValueError("infinite endpoint cannot be closed")
        except InvalidOperation as error:
            raise ValueError("invalid decimal endpoint") from error
        return self


class ComparisonLiteral(StructuralValue):
    kind: Literal["date", "identifier", "quantity", "range"]
    value: str | None = None
    unit: str | None = None
    lower: str | None = None
    upper: str | None = None
    lower_closed: bool | None = None
    upper_closed: bool | None = None

    @model_validator(mode="after")
    def valid_domain_value(self) -> Self:
        from datetime import date
        from decimal import Decimal, InvalidOperation

        if self.kind in {"date", "identifier", "quantity"} and not self.value:
            raise ValueError("formal literal requires its explicit value")
        if self.kind == "date":
            assert self.value is not None
            date.fromisoformat(self.value)
        if self.kind in {"quantity", "range"}:
            if not self.unit:
                raise ValueError("numeric literal requires an explicit lexical unit")
            try:
                if self.kind == "quantity":
                    assert self.value is not None
                    values = [Decimal(self.value)]
                else:
                    if self.lower is None or self.upper is None:
                        raise ValueError("range literal requires both explicit bounds")
                    values = [Decimal(self.lower), Decimal(self.upper)]
                if any(not value.is_finite() for value in values):
                    raise ValueError("numeric literal values must be finite")
                if any(value and abs(value.adjusted()) > 100 for value in values):
                    raise ValueError("numeric comparison literal exceeds its bounded decimal range")
                if self.kind == "range" and (
                    values[0] > values[1]
                    or (values[0] == values[1] and not (self.lower_closed and self.upper_closed))
                ):
                    raise ValueError("range literal must be nonempty and ordered")
            except (InvalidOperation, TypeError) as error:
                raise ValueError("numeric literal has an invalid decimal value") from error
        return self


class ComparisonMemberDecision(StructuralValue):
    left_index: int = Field(ge=0)
    right_index: int = Field(ge=0)
    outcome: Literal["equivalent", "different"]


MemberRole = Literal[
    "definition",
    "terminology",
    "usage",
    "relationship",
    "variant",
    "exception",
    "revision",
    "conflict",
    "unresolved_sense",
    "open_question",
]
MANDATORY_ROLES = frozenset({"exception", "revision", "conflict"})


class DossierContributionCitation(StructuralValue):
    contribution_id: Nonempty
    source_ref: Nonempty
    source_pointer: Nonempty
    span: LocatedDefinitionSpan


class DossierDependency(StructuralValue):
    relation: Literal["depends_on"] = "depends_on"
    dependent: tuple[DossierContributionCitation, ...] = Field(min_length=1)
    prerequisite: tuple[DossierContributionCitation, ...] = Field(min_length=1)


class DossierFacet(StructuralValue):
    definition_interpretation: DefinitionInterpretation | None = None
    applicability_outcome: DefinitionOutcome | None = None
    facet_id: Nonempty
    kind: Nonempty
    scope: Nonempty
    member_id: Nonempty
    assessment_id: Nonempty
    assessment_scope: Literal["comparison_statement"] | None = None
    evidence: tuple[Nonempty, ...] = Field(min_length=1)


class DossierRepresentation(StructuralValue):
    policy: Literal["supported-facet-greedy-1", "source-order-control-1"]
    member_budget: Positive
    selected: tuple[Nonempty, ...]
    omitted: tuple[Nonempty, ...]
    represented_facets: tuple[Nonempty, ...]
    missing_facets: tuple[Nonempty, ...]
    mandatory_overflow: bool
    membership_digest: Digest
    facet_digest: Digest


class ConditionRoleCitation(StructuralValue):
    source_pointer: Nonempty
    span: LocatedDefinitionSpan


class DeclaredStructuralInput(StructuralValue):
    question: Nonempty
    scope: Nonempty
    inventory_id: Nonempty
    policy_id: Nonempty
    sources: tuple[DeclaredStructuralSource, ...] = Field(min_length=1)
    passages: tuple[StructuralPassage, ...] = Field(min_length=1)
    dependencies: tuple[Nonempty, ...] = Field(min_length=1)
    exclusions: tuple[StructuralExclusion, ...] = ()
    coverage_limits: tuple[Nonempty, ...] = ()

    @model_validator(mode="after")
    def closure(self) -> Self:
        refs = {s.identity for s in self.sources}
        if len(refs) != len(self.sources):
            raise ValueError("duplicate original source reference")
        if len({p.passage_id for p in self.passages}) != len(self.passages):
            raise ValueError("duplicate passage identity")
        if any(p.source_ref not in refs for p in self.passages):
            raise ValueError("passage refers outside declared original sources")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("duplicate computational dependency")
        return self


class DeclaredTypedPremise(StructuralValue):
    span: LocatedDefinitionSpan
    grammar: Nonempty
    state: Literal["parsed", "unsupported", "ambiguous"]
    value: str | None = None
    comparator: Literal[">", ">=", "<", "<=", "="] | None = None
    quantity: str | None = None
    unit: str | None = None
    basis: str | None = None
    basis_evidence: LocatedDefinitionSpan | None = None
    primary_formal: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    primary_basis: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def faithful_values(self) -> Self:
        return _typed_premise_invariants(self)


class DeclaredClauseField(StructuralValue):
    dimension: Dimension
    lexical_value: Nonempty
    evidence: tuple[Nonempty, ...] = Field(min_length=1)
    typed: DeclaredTypedPremise | None = None
    span: LocatedDefinitionSpan | None = None
    spans: tuple[LocatedDefinitionSpan, ...] | None = None
    contribution_id: Nonempty | None = None
    literal: ComparisonLiteral | None = None
    condition: dict[str, Any] | None = None
    primary_formal: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def formal_source(self) -> Self:
        return _clause_field_invariants(self)


class DeclaredClauseFieldGroup(StructuralValue):
    state: Literal["absent", "empty", "present", "unresolved"]
    grouping: Literal["singleton", "conjunction", "disjunction", "unresolved"] | None = None
    members: tuple[DeclaredClauseField, ...] = ()
    witnesses: tuple[LocatedDefinitionSpan, ...] = ()
    primary_witnesses: tuple[DeclaredPrimaryReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def complete(self) -> Self:
        return _clause_group_invariants(self)


class DeclaredClauseReading(StructuralValue):
    passage_id: Nonempty
    fields: tuple[DeclaredClauseField, ...] = ()
    groups: dict[Dimension, DeclaredClauseFieldGroup] | None = None
    focus: LocatedDefinitionSpan | None = None

    @model_validator(mode="after")
    def dimensions(self) -> Self:
        return _clause_reading_invariants(self)


class DeclaredDimensionComparison(StructuralValue):
    dimension: Dimension
    outcome: Literal[
        "same_lexical_value", "different_lexical_value", "unknown", "incompatible_applicability"
    ]
    left: DeclaredClauseField | None = None
    right: DeclaredClauseField | None = None
    left_group: DeclaredClauseFieldGroup | None = None
    right_group: DeclaredClauseFieldGroup | None = None
    grouping_outcome: Literal["same", "different", "unresolved"] | None = None
    member_comparisons: tuple[ComparisonMemberDecision, ...] | None = None
    typed_outcome: Literal["equivalent", "different", "unknown", "unsupported", "ambiguous"] = (
        "unknown"
    )
    removed_interval: TriggerInterval | None = None
    added_interval: TriggerInterval | None = None
    assumptions: tuple[Nonempty, ...] = ()
    reason: Nonempty = "No source-qualified typed comparison has been established."


class DeclaredRevisionSuccession(StructuralValue):
    older_id: Nonempty
    newer_id: Nonempty
    evidence: LocatedDefinitionSpan
    older_evidence: LocatedDefinitionSpan
    primary_witnesses: tuple[DeclaredPrimaryReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


class DeclaredComparisonProduct(StructuralValue):
    left_id: Nonempty
    right_id: Nonempty
    dimensions: tuple[DeclaredDimensionComparison, ...]
    left_reading: DeclaredContributionRef
    right_reading: DeclaredContributionRef
    left_focus: LocatedDefinitionSpan | None = None
    right_focus: LocatedDefinitionSpan | None = None
    equivalence: Literal["not_asserted"] = "not_asserted"
    identity_standing: Literal["not_asserted"] = "not_asserted"
    applicability: Literal[
        "co_applicable", "successive_revisions", "differently_scoped", "unestablished"
    ] = "unestablished"
    applicability_reason: Nonempty = "No complete applicability premises have been established."
    succession: DeclaredRevisionSuccession | None = None

    @model_validator(mode="after")
    def succession_custody(self) -> Self:
        return _comparison_product_invariants(self)


class DeclaredDossierComparisonSelection(StructuralValue):
    comparison_product_id: Nonempty
    side: Literal["left", "right"]
    relationship_ref: DeclaredRelationshipRef
    applicability_ref: DeclaredStructuralRef | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    conflict_passage_id: Nonempty | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class DeclaredDossierComparisonBinding(StructuralValue):
    comparison_ref: DeclaredStructuralRef
    side: Literal["left", "right"]
    relationship_ref: DeclaredRelationshipRef
    relationship: Literal["denotes", "defined-by", "specializes"]
    root: DeclaredComponentRef
    source: DeclaredStructuralSource
    citation: LocatedDefinitionSpan
    occurrence: tuple[LocatedDefinitionSpan, ...] = Field(min_length=1)
    comparison: DeclaredComparisonProduct
    opposite_source: DeclaredStructuralSource
    opposite_citation: LocatedDefinitionSpan
    applicability_ref: DeclaredStructuralRef | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    conflict_evidence: LocatedDefinitionSpan | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def sides(self) -> Self:
        return _dossier_binding_invariants(self)


class DeclaredDossierMember(StructuralValue):
    member_id: Nonempty
    passage_id: Nonempty
    citation: LocatedDefinitionSpan
    role: MemberRole
    sense: Nonempty
    scope: Nonempty
    effective_version: str | None = None
    relation_product_id: Nonempty = Field(
        description="Domain report identity; the exact native product address is carried by the typed predecessor reference."
    )
    definition_interpretation: DefinitionInterpretation | None = None
    applicability_outcome: DefinitionOutcome | None = None
    comparison_binding: DeclaredDossierComparisonBinding | None = None
    contribution_ref: DeclaredContributionRef | None = None
    contribution_citations: tuple[DossierContributionCitation, ...] | None = None
    semantic_dependency: DossierDependency | None = None
    computation_dependencies: tuple[Nonempty, ...] | None = None
    qualification: Literal[
        "proposed", "independently_supported", "ambiguous", "rejected", "unsupported"
    ] = "proposed"
    assessment_id: str | None = None

    @model_validator(mode="after")
    def assessment(self) -> Self:
        return _dossier_member_invariants(self)


class DeclaredDossierProduct(StructuralValue):
    root_id: Nonempty
    root_component: DeclaredComponentRef
    members: tuple[DeclaredDossierMember, ...]
    predecessors: tuple[DeclaredStructuralRef, ...] = ()
    contribution_predecessors: tuple[DeclaredContributionRef, ...] = ()
    comparison_selections: tuple[DeclaredDossierComparisonSelection, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    representatives: tuple[Nonempty, ...]
    missing_sections: tuple[MemberRole, ...]
    supported_facets: tuple[DossierFacet, ...] = ()
    representation: DossierRepresentation
    membership_completeness: Literal["declared_selection"] = "declared_selection"

    @model_validator(mode="after")
    def membership(self) -> Self:
        return _dossier_product_invariants(self)


class DeclaredConditionQualificationProduct(StructuralValue):
    relation: Literal["condition", "assumption"]
    attachment: DeclaredContributionRef
    effective_version: Nonempty | None = Field(default=None, exclude_if=lambda value: value is None)
    qualifier: tuple[ConditionRoleCitation, ...] = Field(min_length=1)
    host_predicate: tuple[ConditionRoleCitation, ...] = Field(min_length=1)


class DeclaredPrimaryReference(StructuralValue):
    product_id: Nonempty
    member_id: Nonempty

    @property
    def product(self):
        from .data_product_reference import DataProductReference

        return DataProductReference(self.product_id)

    @property
    def local_id(self):
        return self.member_id

    def values(self):
        return self.model_dump(mode="json")

    @property
    def identity(self):
        return "member:" + sha256(canonical_bytes(self.values())).hexdigest()


class DeclaredDefinitionBasisWitness(StructuralValue):
    annotation_product: DeclaredProductRef
    block_id: Nonempty
    dependency_digest: Digest
    rule: Nonempty
    variant: Nonempty
    nodes: tuple[Annotated[int, Field(strict=True, ge=0)], ...] = Field(min_length=1)
    label_nodes: tuple[Annotated[int, Field(strict=True, ge=0)], ...] | None = None
    primary_match: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    primary_scope: tuple[DeclaredPrimaryReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


class DeclaredDeclarationChainWitness(StructuralValue):
    version: Literal["definition-declaration-chain-2"] = "definition-declaration-chain-2"
    primary_evidence: tuple[DeclaredPrimaryReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    scope_digest: Digest
    label: LocatedDefinitionSpan
    bindings: tuple[DeclarationChainBinding, ...] = Field(min_length=1, max_length=4)
    construction_frame: Nonempty
    construction_subject_token: Annotated[int, Field(strict=True, ge=0)]
    naming_frame: Nonempty
    naming_antecedent_token: Annotated[int, Field(strict=True, ge=0)]

    @model_validator(mode="after")
    def distinct_roles(self) -> Self:
        if not self.primary_evidence:
            raise ValueError("declared chain requires genuine primary semantic evidence")
        return _declaration_role_invariants(self)


class DeclaredLocatedDefinitionComponent(StructuralValue):
    component_id: Digest
    term: LocatedDefinitionSpan
    content: LocatedDefinitionSpan
    interpretation: DefinitionInterpretation
    basis: Literal[
        "matched_cue",
        "native_geometry",
        "declaration_chain",
        "model_reading",
        "unqualified",
    ]
    witness: DeclaredDefinitionBasisWitness | None = None
    declaration_chain: DeclaredDeclarationChainWitness | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    scope: Nonempty
    effective_version: str | None = None
    alternatives: tuple[Nonempty, ...] = ()
    evidence: tuple[Nonempty, ...] = Field(min_length=1)
    reason: Nonempty

    @model_validator(mode="after")
    def bound_identity(self) -> Self:
        return _definition_component_invariants(self)


def declared_definition_component(**meaning) -> DeclaredLocatedDefinitionComponent:
    return _make_definition_component(DeclaredLocatedDefinitionComponent, meaning)


class DeclaredDefinitionComponentsProduct(StructuralValue):
    components: tuple[DeclaredLocatedDefinitionComponent, ...]
    stages: tuple[DefinitionStage, ...]
    role_candidates: tuple[DefinitionRoleCandidate, ...] | None = None

    @model_validator(mode="after")
    def unique_components(self) -> Self:
        return _definition_components_invariants(self)


class DeclaredStructuralDefinitionReading(StructuralValue):
    target_id: Nonempty
    component_ref: DeclaredComponentRef
    link_ref: DeclaredRelationshipRef
    component: DeclaredLocatedDefinitionComponent
    outcome: DefinitionOutcome
    evidence: tuple[Nonempty, ...] = Field(min_length=1)
    premises: tuple[ApplicabilityPremise, ...] = Field(min_length=1)
    reason: Nonempty

    @model_validator(mode="after")
    def supported_premises(self) -> Self:
        return _definition_reading_invariants(self)


class DeclaredDefinitionProduct(StructuralValue):
    usage_id: Nonempty
    candidate_list_id: Nonempty
    eligible_targets: tuple[Nonempty, ...]
    candidate_targets: tuple[Nonempty, ...]
    readings: tuple[DeclaredStructuralDefinitionReading, ...]
    inventory_coverage: Literal["declared_selection", "known_gap"] = "declared_selection"
    retrieval_diagnosis: Literal["not_independently_assessed"] = "not_independently_assessed"

    @model_validator(mode="after")
    def membership(self) -> Self:
        return _definition_membership_invariants(self)


class DeclaredClauseFocusSelection(StructuralValue):
    passage_id: Nonempty
    frame: DeclaredContributionRef


class DeclaredClauseModelReading(StructuralValue):
    selection: DeclaredClauseFocusSelection
    focus: LocatedDefinitionSpan
    preceding: LocatedDefinitionSpan | None = None
    following: LocatedDefinitionSpan | None = None
    context_digest: Digest
    envelope: Nonempty | None = None
    function: tuple[ClauseModelLabel, ...] = ()
    presentation: tuple[ClauseModelLabel, ...] = ()
    disposition: Literal["observed", "withheld", "failed"]
    reason: Nonempty
    primary_functions: tuple[DeclaredPrimaryReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    primary_context: tuple[DeclaredPrimaryReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


class DeclaredClauseClassificationProduct(StructuralValue):
    context_policy: Literal["exact_focus", "adjacent_sentences"]
    readings: tuple[DeclaredClauseModelReading, ...]
    inspection_outcome: Literal["complete", "partial"] = "complete"
    inspected_frames: tuple[DeclaredContributionRef, ...] = ()
    unprojectable_frames: tuple[DeclaredContributionRef, ...] = ()

    @model_validator(mode="after")
    def inspected_closure(self) -> Self:
        inspected, unavailable = set(self.inspected_frames), set(self.unprojectable_frames)
        projected = {reading.selection.frame for reading in self.readings}
        if (
            len(inspected) != len(self.inspected_frames)
            or len(unavailable) != len(self.unprojectable_frames)
            or not unavailable <= inspected
            or projected & unavailable
            or projected | unavailable != inspected
        ):
            raise ValueError(
                "clause inspection must retain its exact distinct inspected frame closure"
            )
        if unavailable and self.inspection_outcome != "partial":
            raise ValueError("unprojectable clause frames require partial inspection")
        return self


class DeclaredSourceArtifactOccurrence(StructuralValue):
    protocol: Literal["source-artifact-occurrence-2"] = "source-artifact-occurrence-2"
    artifact_kind: Literal["table", "figure", "theorem", "section"]
    source_work: str = Field(min_length=1)
    controlled_code: str | None = None
    title: str | None = None
    aliases: tuple[str, ...] = ()
    alias_state: Literal["unknown", "known_empty", "observed"] = "unknown"
    alias_occurrences: tuple[ArtifactAliasSpan, ...] = ()
    alias_absence: ArtifactAliasSpan | None = None
    revision: str | None = None
    revision_state: Literal["observed", "unknown", "malformed", "unresolved"] = "unknown"
    occurrence_role: Literal["caption", "reference"]
    scope: str = Field(min_length=1)
    source_pointer: str = Field(min_length=1)
    dependencies: tuple[str, ...] = Field(min_length=1)
    primary_node: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def provenance(self) -> Self:
        return source_artifact_invariants(self)


class DeclaredArtifactReferenceDesignator(StructuralValue):
    target_code: str
    target_numbering: str
    cue: ArtifactAliasSpan
    primary_node: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class DeclaredArtifactRecord(StructuralValue):
    contribution_id: str = Field(min_length=1)
    occurrence_id: str = Field(min_length=1)
    artifact: DeclaredSourceArtifactOccurrence
    source_contribution: dict[str, JsonValue]
    citations: tuple[ArtifactCitation, ...] = Field(min_length=1)
    numbering: ArtifactSourceLabel = Field(default_factory=ArtifactSourceLabel)
    revision: ArtifactSourceLabel = Field(default_factory=ArtifactSourceLabel)
    explicit_reference: DeclaredArtifactReferenceDesignator | None = None
    primary_node: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class DeclaredArtifactNominationEndpoint(StructuralValue):
    role: Literal["attachment", "target"]
    record_id: str
    contribution_id: str
    origin_source: Nonempty
    origin_anchor_id: str


class DeclaredArtifactNomination(StructuralValue):
    kind: Literal["artifact_reference_target"] = "artifact_reference_target"
    relationship: DeclaredContributionRef
    endpoints: tuple[DeclaredArtifactNominationEndpoint, DeclaredArtifactNominationEndpoint]
    origin_cue: ArtifactAliasSpan
    primary_node: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    left: str = Field(min_length=1)
    right: str = Field(min_length=1)

    @model_validator(mode="after")
    def direction(self) -> Self:
        return artifact_nomination_invariants(self)


class DeclaredArtifactDeclaredEndpoint(StructuralValue):
    record_id: str
    citation: ArtifactCitation
    work_cue: ArtifactCitation | None = Field(default=None, exclude_if=lambda value: value is None)
    work_primary_node: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class DeclaredArtifactDeclaredRelationship(StructuralValue):
    kind: Literal["reference", "same_lineage", "supersedes"]
    source_id: str
    origin: ArtifactCitation
    targets: tuple[DeclaredArtifactDeclaredEndpoint, ...]
    outcome: Literal["witnessed_candidate", "ambiguous", "no_compatible_candidate"]
    primary_node: DeclaredPrimaryReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class DeclaredArtifactIdentityProduct(StructuralValue):
    protocol: Literal["artifact-identity-5"] = "artifact-identity-5"
    identity_grain: Literal["source_work_artifact_lineage"] = "source_work_artifact_lineage"
    records: tuple[DeclaredArtifactRecord, ...] = ()
    pairs: tuple[ArtifactPair, ...] = ()
    native_alias_pairs: tuple[ArtifactPairKey, ...] = ()
    external_nominations: tuple[DeclaredArtifactNomination, ...] = ()
    explicit_references: tuple[ArtifactReferenceResolution, ...] = ()
    declared_relationships: tuple[DeclaredArtifactDeclaredRelationship, ...] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    route_counts: tuple[ArtifactRouteCount, ...]
    policy: ArtifactScoringPolicy
    source_mapping_provenance: tuple[str, ...] = ()
    known_anchor_ids: tuple[str, ...] = ()
    unbound_sources: tuple[Nonempty, ...] = ()
    standing: Literal["candidate_relative_private"] = "candidate_relative_private"

    @model_validator(mode="after")
    def membership(self) -> Self:
        return artifact_identity_invariants(self)


class DeclaredStructuralProductReport(StructuralValue):
    version: Literal["structural-product-3"] = "structural-product-3"
    kind: Literal[
        "definition_components",
        "definition_applicability",
        "qualified_comparison",
        "dossier",
        "artifact_identity",
        "clause_classification",
        "condition_qualification",
    ]
    inputs: DeclaredStructuralInput
    standing: Literal["private_proposal"] = "private_proposal"
    definition_components: DeclaredDefinitionComponentsProduct | None = None
    definition: DeclaredDefinitionProduct | None = None
    comparison: DeclaredComparisonProduct | None = None
    dossier: DeclaredDossierProduct | None = None
    artifact_identity: DeclaredArtifactIdentityProduct | None = None
    clause_classification: DeclaredClauseClassificationProduct | None = None
    condition_qualification: DeclaredConditionQualificationProduct | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def closure(self) -> Self:
        return _structural_report_invariants(self)

    @property
    def product_id(self):
        return (
            "structural:"
            + sha256(canonical_bytes(self.model_dump(mode="json", exclude_none=True))).hexdigest()
        )


class DeclaredStructuralInputPin(DeclaredProductRef):
    original_source: Nonempty
    reference: Nonempty

    @classmethod
    def from_bound(cls, member, *, project, **values):
        value = DeclaredProductRef.from_bound(member, project=project, **values)
        return cls(
            **value.model_dump(),
            reference=canonical_bytes([member.product, member.member]).decode(),
        )


class DeclaredComparisonReport(DeclaredStructuralProductReport):
    formal_input: tuple[DeclaredStructuralInputPin, ...] = ()
    kind: Literal["qualified_comparison"] = "qualified_comparison"
    comparison: DeclaredComparisonProduct
    dossier: None = None
    condition_qualification: None = None
    sources_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)
    reports_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)


class DeclaredDossierReport(DeclaredStructuralProductReport):
    kind: Literal["dossier"] = "dossier"
    dossier: DeclaredDossierProduct
    comparison: None = None
    condition_qualification: None = None
    sources_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)
    components_input: DeclaredStructuralInputPin
    definitions_input: tuple[DeclaredStructuralInputPin, ...] = ()
    comparisons_input: tuple[DeclaredStructuralInputPin, ...] = ()
    candidates_input: tuple[DeclaredStructuralInputPin, ...] = ()
    relationships_input: tuple[DeclaredStructuralInputPin, ...] = ()
    admissions_input: tuple[DeclaredStructuralInputPin, ...]


class DeclaredConditionReport(DeclaredStructuralProductReport):
    kind: Literal["condition_qualification"] = "condition_qualification"
    condition_qualification: DeclaredConditionQualificationProduct
    comparison: None = None
    dossier: None = None
    source_input: DeclaredStructuralInputPin
    report_input: DeclaredStructuralInputPin


class DeclaredDefinitionComponentsReport(DeclaredStructuralProductReport):
    model_config = ConfigDict(json_schema_extra={"x-ddo-definition-variant": "components"})
    kind: Literal["definition_components"] = "definition_components"
    definition_components: DeclaredDefinitionComponentsProduct
    sources_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)
    reports_input: tuple[DeclaredStructuralInputPin, ...] = ()


class DeclaredDefinitionApplicabilityReport(DeclaredStructuralProductReport):
    model_config = ConfigDict(json_schema_extra={"x-ddo-definition-variant": "applicability"})
    """Current usage result with independently bound exact component/relationship pins."""

    kind: Literal["definition_applicability"] = "definition_applicability"
    definition: DeclaredDefinitionProduct
    sources_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)
    components_input: DeclaredStructuralInputPin
    relationship_input: DeclaredStructuralInputPin


class DeclaredArtifactReport(DeclaredStructuralProductReport):
    kind: Literal["artifact_identity"] = "artifact_identity"
    artifact_identity: DeclaredArtifactIdentityProduct
    sources_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)
    reports_input: tuple[DeclaredStructuralInputPin, ...] = ()


class DeclaredClauseReport(DeclaredStructuralProductReport):
    kind: Literal["clause_classification"] = "clause_classification"
    clause_classification: DeclaredClauseClassificationProduct
    sources_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)
    reports_input: tuple[DeclaredStructuralInputPin, ...] = Field(min_length=1)


def _definition_component_invariants(value: Any) -> Any:
    if value.basis == "unqualified" and value.interpretation != "unresolved":
        raise ValueError("unqualified definition candidates have unresolved interpretation")
    if value.witness is not None and value.basis not in {"matched_cue", "native_geometry"}:
        raise ValueError("definition annotation witness belongs to a named or geometry basis")
    if (value.declaration_chain is not None) != (value.basis == "declaration_chain") or (
        value.declaration_chain is not None
        and (
            value.interpretation != "definition"
            or value.declaration_chain.label.passage_id != value.term.passage_id
            or value.content.passage_id != value.term.passage_id
        )
    ):
        raise ValueError("definition declaration chain requires its exact witnessed basis")
    meaning = value.model_dump(mode="json", exclude_none=True, exclude={"component_id"})
    if value.component_id != sha256(canonical_bytes(meaning)).hexdigest():
        raise ValueError("component identity differs from complete interpretation")
    return value


def _definition_components_invariants(value: Any) -> Any:
    if len({c.component_id for c in value.components}) != len(value.components):
        raise ValueError("duplicate definition component")
    roles = value.role_candidates or ()
    if len({(r.envelope, r.role, r.index) for r in roles}) != len(roles):
        raise ValueError("duplicate definition role envelope index")
    return value


def _definition_reading_invariants(value: Any) -> Any:
    if value.component_ref.component_id != value.component.component_id:
        raise ValueError("applicability reading substitutes its component")
    if {p.dimension for p in value.premises} != {
        "sense",
        "parameterization",
        "convention",
        "scope",
        "version",
        "parent",
    } or len(value.premises) != 6:
        raise ValueError("applicability requires exactly six distinct declared dimensions")
    states = {p.state for p in value.premises}
    if value.outcome.startswith("applicable_") and (
        "unknown" in states or "incompatible" in states
    ):
        raise ValueError("applicable reading requires resolved compatible premises")
    if value.outcome == "incompatible" and "incompatible" not in states:
        raise ValueError("incompatibility requires an explicit incompatible premise")
    return value


def _definition_membership_invariants(value: Any) -> Any:
    if len(set(value.eligible_targets)) != len(value.eligible_targets) or len(
        set(value.candidate_targets)
    ) != len(value.candidate_targets):
        raise ValueError("duplicate eligible target or candidate")
    if not set(value.candidate_targets) <= set(value.eligible_targets):
        raise ValueError("candidate is outside eligible inventory")
    if len({(r.target_id, r.component_ref.identity) for r in value.readings}) != len(
        value.readings
    ):
        raise ValueError("duplicate target component reading")
    if not {r.target_id for r in value.readings} <= set(value.candidate_targets):
        raise ValueError("reading is outside fixed candidate list")
    return value


def _structural_report_invariants(value: Any) -> Any:
    if (
        value.definition_components is not None,
        value.definition is not None,
        value.comparison is not None,
        value.dossier is not None,
        value.artifact_identity is not None,
        value.clause_classification is not None,
        value.condition_qualification is not None,
    ) != (
        value.kind == "definition_components",
        value.kind == "definition_applicability",
        value.kind == "qualified_comparison",
        value.kind == "dossier",
        value.kind == "artifact_identity",
        value.kind == "clause_classification",
        value.kind == "condition_qualification",
    ):
        raise ValueError("structural report must contain exactly its declared product")
    passages = {p.passage_id for p in value.inputs.passages}
    cited: set[str] = set()
    if value.condition_qualification is not None:
        by_id = {p.passage_id: p for p in value.inputs.passages}
        for citations in (
            value.condition_qualification.qualifier,
            value.condition_qualification.host_predicate,
        ):
            if len(set(canonical_bytes(c.model_dump(mode="json")) for c in citations)) != len(
                citations
            ):
                raise ValueError("condition role repeats source evidence")
            for citation in citations:
                span = citation.span
                passage = by_id.get(span.passage_id)
                if (
                    passage is None
                    or passage.scope != value.inputs.scope
                    or passage.effective_version != value.condition_qualification.effective_version
                    or not passage.start <= span.start < span.end <= passage.end
                    or passage.text[span.start - passage.start : span.end - passage.start]
                    != span.text
                ):
                    raise ValueError("condition role differs from its selected source scope")
                cited.add(span.passage_id)
    if value.clause_classification is not None:
        by_id = {p.passage_id: p for p in value.inputs.passages}
        readings = value.clause_classification.readings
        if any(
            reference.product_id not in value.inputs.dependencies
            or reference.contribution_id not in value.inputs.dependencies
            for reference in value.clause_classification.inspected_frames
        ):
            raise ValueError(
                "clause inspection lacks its actual retained native frame dependencies"
            )
        if len({r.selection for r in readings}) != len(readings):
            raise ValueError("clause classification requires distinct selected focuses")
        for row in readings:
            passage = by_id.get(row.selection.passage_id)
            if (
                passage is None
                or row.selection.frame.contribution_id not in value.inputs.dependencies
            ):
                raise ValueError("clause classification lacks its selected source dependency")
            if value.clause_classification.context_policy == "exact_focus" and (
                row.preceding is not None or row.following is not None
            ):
                raise ValueError("exact focus cannot include adjacent context")
            for span in (row.focus, row.preceding, row.following):
                if span is not None and (
                    span.passage_id != passage.passage_id
                    or not passage.start <= span.start < span.end <= passage.end
                    or span.text
                    != passage.text[span.start - passage.start : span.end - passage.start]
                ):
                    raise ValueError("model context span differs from its selected source")
            if (row.preceding is not None and row.preceding.end > row.focus.start) or (
                row.following is not None and row.following.start < row.focus.end
            ):
                raise ValueError("clause model context crosses its exact focus")
            cited.add(passage.passage_id)
    if value.definition_components:
        by_id = {p.passage_id: p for p in value.inputs.passages}
        for candidate in value.definition_components.role_candidates or ():
            span = candidate.span
            passage = by_id.get(span.passage_id)
            if (
                passage is None
                or not passage.start <= candidate.window_start < candidate.window_end <= passage.end
                or passage.text[span.start - passage.start : span.end - passage.start] != span.text
            ):
                raise ValueError("definition role differs from original passage")
            cited.add(span.passage_id)
        for component in value.definition_components.components:
            cited.update(component.evidence)
            chain = component.declaration_chain
            if chain is not None and any(
                ref.product_id not in value.inputs.dependencies for ref in chain.primary_evidence
            ):
                raise ValueError("definition chain lacks its exact primary product dependency")
            for span in (
                component.term,
                component.content,
                *((chain.label,) if chain is not None else ()),
            ):
                passage = by_id.get(span.passage_id)
                if (
                    passage is None
                    or not passage.start <= span.start < span.end <= passage.end
                    or passage.text[span.start - passage.start : span.end - passage.start]
                    != span.text
                ):
                    raise ValueError("definition span differs from original passage")
                if (
                    component.scope != passage.scope
                    or component.effective_version != passage.effective_version
                ):
                    raise ValueError("definition component scope/version differs from passage")
                cited.add(span.passage_id)
        cited.update(stage.passage_id for stage in value.definition_components.stages)
    if value.definition:
        cited.add(value.definition.usage_id)
        for reading in value.definition.readings:
            cited.update(reading.evidence)
            for premise in reading.premises:
                cited.update(premise.evidence)
            if reading.component_ref.product_id not in value.inputs.dependencies:
                raise ValueError("applicability component is not a declared dependency")
    if value.comparison:
        by_id = {p.passage_id: p for p in value.inputs.passages}

        def exact(span: LocatedDefinitionSpan) -> bool:
            passage = by_id.get(span.passage_id)
            return (
                passage is not None
                and passage.start <= span.start < span.end <= passage.end
                and passage.text[span.start - passage.start : span.end - passage.start] == span.text
            )

        cited.update((value.comparison.left_id, value.comparison.right_id))
        if succession := value.comparison.succession:
            older, newer = by_id.get(succession.older_id), by_id.get(succession.newer_id)
            if (
                older is None
                or newer is None
                or not older.parent
                or older.parent != newer.parent
                or older.scope != newer.scope
                or older.source_ref != newer.source_ref
                or not (older.end <= newer.start or newer.end <= older.start)
                or not older.effective_version
                or not newer.effective_version
                or older.effective_version == newer.effective_version
                or (bool(succession.primary_witnesses) and len(succession.primary_witnesses) != 4)
                or not exact(succession.evidence)
                or not exact(succession.older_evidence)
            ):
                raise ValueError("succession differs from its exact original source")
        if tuple(d.dimension for d in value.comparison.dimensions) != DIMENSIONS:
            raise ValueError("comparison requires every ordered dimension, including unknowns")
        for dimension in value.comparison.dimensions:
            for passage_id, group in (
                (value.comparison.left_id, dimension.left_group),
                (value.comparison.right_id, dimension.right_group),
            ):
                if group is None:
                    continue
                if any(
                    not exact(span) or span.passage_id != passage_id for span in group.witnesses
                ):
                    raise ValueError("group witness differs from selected original passage")
                for member in group.members:
                    if member.dimension != dimension.dimension or member.evidence != (passage_id,):
                        raise ValueError("group member differs from selected dimension/passage")
                    if member.spans and (
                        any(
                            not exact(span) or span.passage_id != passage_id
                            for span in member.spans
                        )
                        or member.lexical_value != " ".join(span.text for span in member.spans)
                    ):
                        raise ValueError("group member differs from original source spans")
            sides = [dimension.left, dimension.right]
            for group in (dimension.left_group, dimension.right_group):
                if group is not None:
                    sides.extend(group.members)
            for side in sides:
                if side:
                    cited.update(side.evidence)
                    if side.span is not None:
                        span = side.span
                        selected = next(
                            (p for p in value.inputs.passages if p.passage_id == span.passage_id),
                            None,
                        )
                        if (
                            selected is None
                            or not selected.start <= span.start < span.end <= selected.end
                            or selected.text[
                                span.start - selected.start : span.end - selected.start
                            ]
                            != span.text
                            or side.lexical_value != span.text
                        ):
                            raise ValueError("clause field differs from its exact original source")
                        cited.add(span.passage_id)
                    if side.typed is not None:
                        span = side.typed.span
                        basis = side.typed.basis_evidence
                        if not exact(span) or (basis is not None and not exact(basis)):
                            raise ValueError("typed field differs from its exact original source")
                        cited.add(span.passage_id)
    if value.dossier:
        cited.update(m.passage_id for m in value.dossier.members)
        for member in value.dossier.members:
            span = member.citation
            passage = next(
                (p for p in value.inputs.passages if p.passage_id == member.passage_id), None
            )
            if (
                passage is None
                or span.passage_id != member.passage_id
                or not passage.start <= span.start < span.end <= passage.end
                or passage.text[span.start - passage.start : span.end - passage.start] != span.text
            ):
                raise ValueError("dossier member citation differs from original source")
    if value.artifact_identity:
        by_id = {p.passage_id: p for p in value.inputs.passages}
        for record in value.artifact_identity.records:
            for citation in record.citations:
                passage = by_id.get(citation.passage_id)
                if (
                    passage is None
                    or citation.source_ref != passage.source_ref
                    or not passage.start <= citation.start < citation.end <= passage.end
                    or passage.text[citation.start - passage.start : citation.end - passage.start]
                    != citation.text
                ):
                    raise ValueError("artifact citation differs from its exact original source")
                cited.add(citation.passage_id)
    if not cited <= passages:
        raise ValueError("structural evidence lies outside declared passage closure")
    return value


def _declaration_role_invariants(value: Any) -> Any:
    if (
        len({row.frame for row in value.bindings}) != len(value.bindings)
        or len({row.subject_token for row in value.bindings}) != len(value.bindings)
        or len({row.use_token for row in value.bindings}) != len(value.bindings)
        or len(
            {value.construction_frame, value.naming_frame, *(row.frame for row in value.bindings)}
        )
        != len(value.bindings) + 2
    ):
        raise ValueError("declaration chain requires distinct ordered role occurrences")
    return value


DeclaredStructuralReport = Annotated[
    DeclaredComparisonReport
    | DeclaredDossierReport
    | DeclaredConditionReport
    | DeclaredDefinitionComponentsReport
    | DeclaredDefinitionApplicabilityReport
    | DeclaredArtifactReport
    | DeclaredClauseReport,
    Field(discriminator="kind"),
]
_DECLARED_STRUCTURAL_REPORT = TypeAdapter(DeclaredStructuralReport)


def read_structural_product_report(value):
    """Read the declared discriminated report without task/run protocol alternatives."""
    if isinstance(value, DeclaredStructuralProductReport):
        return value
    return _DECLARED_STRUCTURAL_REPORT.validate_python(value)


def _typed_premise_invariants(value: Any) -> Any:
    from decimal import Decimal, InvalidOperation

    if (
        value.basis is not None
        or value.basis_evidence is not None
        or value.primary_basis is not None
    ):
        witness = value.basis_evidence
        if (
            value.state != "parsed"
            or witness is None
            or witness.passage_id != value.span.passage_id
            or not value.basis
        ):
            raise ValueError("typed basis requires its exact source declaration")
        if value.primary_formal is not None and value.primary_basis is None:
            raise ValueError("primary threshold basis requires its retained lexical witness")
    if value.state == "parsed":
        try:
            if (
                value.value is None
                or value.comparator is None
                or not Decimal(value.value).is_finite()
            ):
                raise ValueError("typed threshold requires a finite numeric value and comparator")
        except InvalidOperation as error:
            raise ValueError("typed threshold has an invalid decimal value") from error
    elif (
        value.value is not None or value.comparator is not None or value.primary_formal is not None
    ):
        raise ValueError("unparsed premise cannot carry interpreted numeric values")
    return value


def _clause_field_invariants(value: Any) -> Any:
    if value.literal is not None and (value.spans is None or len(value.spans) != 1):
        raise ValueError("formal operand requires one exact located source interval")
    if value.primary_formal is not None and value.literal is None:
        raise ValueError("formal source reference requires its explicit typed literal")
    return value


def _clause_group_invariants(value: Any) -> Any:
    if value.state == "present" and not value.members:
        raise ValueError("present dimension requires members")
    if value.state in {"absent", "empty"} and (value.members or value.grouping):
        raise ValueError("absent or empty dimension cannot have members")
    if value.state == "empty" and not value.witnesses:
        raise ValueError("known empty dimension requires its source witness")
    if value.grouping == "singleton" and len(value.members) != 1:
        raise ValueError("singleton dimension requires one member")
    if value.grouping in {"conjunction", "disjunction"} and (
        len(value.members) < 2 or len(value.witnesses) != len(value.members) - 1
    ):
        raise ValueError("grouped members require an exact witness between each pair")
    return value


def _clause_reading_invariants(value: Any) -> Any:
    if value.groups is not None and (value.fields or set(value.groups) != set(DIMENSIONS)):
        raise ValueError("a grouped reading requires every dimension and no legacy fields")
    if len({f.dimension for f in value.fields}) != len(value.fields):
        raise ValueError("duplicate clause dimension")
    return value


def _comparison_product_invariants(value: Any) -> Any:
    grouped = value.left_reading is not None
    if any(
        focus is not None and (not grouped or focus.passage_id != passage)
        for focus, passage in (
            (value.left_focus, value.left_id),
            (value.right_focus, value.right_id),
        )
    ):
        raise ValueError("comparison focus must identify its exact grouped side")
    if grouped != (value.right_reading is not None) or any(
        (d.left_group is not None) != grouped
        or (d.right_group is not None) != grouped
        or (grouped and (d.left is not None or d.right is not None))
        for d in value.dimensions
    ):
        raise ValueError("comparison must bind both grouped sides")
    if (value.succession is not None) != (value.applicability == "successive_revisions"):
        raise ValueError("successive revisions require their directed source witness")
    if value.succession and (
        {value.succession.older_id, value.succession.newer_id} != {value.left_id, value.right_id}
        or value.succession.evidence.passage_id != value.succession.newer_id
        or value.succession.older_evidence.passage_id != value.succession.older_id
    ):
        raise ValueError("succession witness differs from compared revisions")
    return value


def _dossier_binding_invariants(value: Any) -> Any:
    left, right = (value.citation, value.opposite_citation)
    if value.side == "right":
        left, right = right, left
    if (
        (left.passage_id, right.passage_id) != (value.comparison.left_id, value.comparison.right_id)
        or value.comparison.left_reading is None
        or any(
            span.passage_id != value.citation.passage_id
            or not value.citation.start <= span.start < span.end <= value.citation.end
            for span in value.occurrence
        )
    ):
        raise ValueError("comparison binding differs from its exact located sides")
    return value


def _dossier_member_invariants(value: Any) -> Any:
    if value.qualification == "independently_supported" and not value.assessment_id:
        raise ValueError("supported member requires its independent assessment reference")
    if value.comparison_binding is not None and (
        value.contribution_ref is not None
        or value.comparison_binding.comparison_ref.structural_id
        != value.relation_product_id
        or value.comparison_binding.root.component_id != value.sense
        or value.comparison_binding.citation.passage_id != value.passage_id
    ):
        raise ValueError("member differs from its comparison binding")
    if value.contribution_ref is not None:
        if (
            not value.contribution_citations
            or not value.computation_dependencies
            or value.relation_product_id != value.contribution_ref.contribution_id
            or value.citation != value.contribution_citations[0].span
            or value.passage_id != value.citation.passage_id
            or any(
                c.contribution_id not in value.computation_dependencies
                for c in value.contribution_citations
            )
        ):
            raise ValueError(
                "source member requires its exact contribution and endpoint citation closure"
            )
        if value.qualification != "proposed" or value.assessment_id is not None:
            raise ValueError(
                "source contribution membership does not establish independent semantic support"
            )
    elif value.contribution_citations is not None or value.computation_dependencies is not None:
        raise ValueError(
            "source citation closure requires an exact retained contribution reference"
        )
    if value.semantic_dependency is not None and (
        value.role != "relationship"
        or not value.contribution_citations
        or not set(value.semantic_dependency.dependent + value.semantic_dependency.prerequisite)
        <= set(value.contribution_citations)
        or {c.contribution_id for c in value.semantic_dependency.dependent}
        & {c.contribution_id for c in value.semantic_dependency.prerequisite}
    ):
        raise ValueError("typed dependency requires distinct qualified source endpoints")
    return value


def _dossier_product_invariants(value: Any) -> Any:
    if value.root_component is not None and (
        value.root_id != value.root_component.component_id
        or not any(p.product_id == value.root_component.product_id for p in value.predecessors)
        or any(member.sense != value.root_id for member in value.members)
    ):
        raise ValueError("dossier membership differs from its exact root sense")
    if any(
        binding.root != value.root_component
        or binding.comparison_ref not in value.predecessors
        or DeclaredDossierComparisonSelection(
            comparison_product_id=binding.comparison_ref.product_id,
            side=binding.side,
            relationship_ref=binding.relationship_ref,
            applicability_ref=binding.applicability_ref,
            conflict_passage_id=(
                binding.conflict_evidence.passage_id
                if binding.conflict_evidence is not None
                else None
            ),
        )
        not in value.comparison_selections
        for member in value.members
        if (binding := member.comparison_binding) is not None
    ):
        raise ValueError("comparison binding is outside exact dossier predecessors")
    ids = {m.member_id for m in value.members}
    if len(ids) != len(value.members):
        raise ValueError("duplicate dossier member")
    if (
        len(set(value.representatives)) != len(value.representatives)
        or not set(value.representatives) <= ids
    ):
        raise ValueError("invalid representative membership")
    if value.representatives != value.representation.selected or set(
        value.representation.omitted
    ) != ids - set(value.representatives):
        raise ValueError("dossier representation differs from its full membership")
    if any(f.member_id not in ids for f in value.supported_facets):
        raise ValueError("dossier facet refers outside full membership")
    facets = {f.facet_id for f in value.supported_facets if f.member_id in value.representatives}
    if set(value.representation.represented_facets) != facets:
        raise ValueError("represented facet lacks its selected supported member")
    all_facets = {f.facet_id for f in value.supported_facets}
    if (
        len(all_facets) != len(value.supported_facets)
        or set(value.representation.missing_facets) != all_facets - facets
    ):
        raise ValueError("facet representation is incomplete or duplicated")
    if (
        value.representation.membership_digest
        != sha256(
            canonical_bytes([m.model_dump(mode="json", exclude_none=True) for m in value.members])
        ).hexdigest()
    ):
        raise ValueError("membership digest differs from full membership")
    if (
        value.representation.facet_digest
        != sha256(
            canonical_bytes(
                [f.model_dump(mode="json", exclude_none=True) for f in value.supported_facets]
            )
        ).hexdigest()
    ):
        raise ValueError("facet digest differs from supported facets")
    mandatory = {m.member_id for m in value.members if m.role in MANDATORY_ROLES}
    if not mandatory <= set(value.representatives) or value.representation.mandatory_overflow != (
        len(mandatory) > value.representation.member_budget
    ):
        raise ValueError("mandatory dossier members must be retained")
    if len(value.representatives) > max(value.representation.member_budget, len(mandatory)):
        raise ValueError("representation exceeds declared member budget")
    return value
