"""Private cross-source products with original custody and explicit semantic limits.

These values are reports, not admission witnesses. Their source references must be
validated at native task completion; model validation alone grants no authority.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from .artifact_identity import ArtifactIdentityProduct
from .contextual_links import RetainedRelationshipDecisionRef
from .identity import canonical_bytes
from .retained_contributions import RetainedContributionRef
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


class ExternalSourceRef(StructuralValue):
    project_id: Nonempty
    run_id: Positive
    cut_id: Positive
    release_id: Nonempty
    result_revision: Annotated[int, Field(strict=True, ge=0)]
    source_view_id: Positive
    native_task_id: Positive
    native_product_key: Nonempty
    native_content_digest: Digest
    projection_digest: Digest
    recipe_digest: Digest
    coordinate_version: Literal[2, 3]


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


class StructuralInput(StructuralValue):
    question: Nonempty
    scope: Nonempty
    inventory_id: Nonempty
    policy_id: Nonempty
    sources: tuple[ExternalSourceRef, ...] = Field(min_length=1)
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


class RetainedComponentRef(StructuralValue):
    product_id: Nonempty
    component_id: Digest
    operation_id: Nonempty
    operation_version: Nonempty
    project_id: Nonempty
    run_id: Positive
    cut_id: Positive
    release_id: Nonempty
    result_revision: Annotated[int, Field(strict=True, ge=0)]
    selected_task_id: Positive
    origin_task_id: Positive
    runtime_fingerprint: Nonempty
    dependencies: tuple[Nonempty, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_dependencies(self) -> Self:
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("duplicate component dependency")
        return self


class RetainedStructuralRef(StructuralValue):
    product_id: Nonempty
    project_id: Nonempty
    run_id: Positive
    cut_id: Positive
    release_id: Nonempty
    result_revision: Annotated[int, Field(strict=True, ge=0)]
    selected_task_id: Positive
    origin_task_id: Positive
    runtime_fingerprint: Nonempty


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


class LocatedDefinitionComponent(StructuralValue):
    component_id: Digest
    term: LocatedDefinitionSpan
    content: LocatedDefinitionSpan
    interpretation: DefinitionInterpretation
    basis: Literal[
        "matched_cue",
        "returned_producer_group",
        "native_geometry",
        "model_reading",
        "admitted_derivation",
    ]
    scope: Nonempty
    effective_version: str | None = None
    alternatives: tuple[Nonempty, ...] = ()
    evidence: tuple[Nonempty, ...] = Field(min_length=1)
    reason: Nonempty

    @model_validator(mode="after")
    def bound_identity(self) -> Self:
        meaning = self.model_dump(mode="json", exclude_none=True, exclude={"component_id"})
        if self.component_id != sha256(canonical_bytes(meaning)).hexdigest():
            raise ValueError("component identity differs from complete interpretation")
        return self


def definition_component(**meaning) -> LocatedDefinitionComponent:
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
    return LocatedDefinitionComponent.model_validate(
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


class DefinitionComponentsProduct(StructuralValue):
    components: tuple[LocatedDefinitionComponent, ...]
    stages: tuple[DefinitionStage, ...]
    role_candidates: tuple[DefinitionRoleCandidate, ...] | None = None

    @model_validator(mode="after")
    def unique_components(self) -> Self:
        if len({c.component_id for c in self.components}) != len(self.components):
            raise ValueError("duplicate definition component")
        roles = self.role_candidates or ()
        if len({(r.envelope, r.role, r.index) for r in roles}) != len(roles):
            raise ValueError("duplicate definition role envelope index")
        return self


class ClauseFocusSelection(StructuralValue):
    passage_id: Nonempty
    frame: RetainedContributionRef


class ClauseModelLabel(StructuralValue):
    label: Nonempty
    score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    accepted: bool


class ClauseModelReading(StructuralValue):
    selection: ClauseFocusSelection
    focus: LocatedDefinitionSpan
    preceding: LocatedDefinitionSpan | None = None
    following: LocatedDefinitionSpan | None = None
    context_digest: Digest
    envelope: Nonempty | None = None
    function: tuple[ClauseModelLabel, ...] = ()
    presentation: tuple[ClauseModelLabel, ...] = ()
    disposition: Literal["observed", "withheld", "failed"]
    reason: Nonempty


class ClauseClassificationProduct(StructuralValue):
    context_policy: Literal["exact_focus", "adjacent_sentences"]
    readings: tuple[ClauseModelReading, ...]


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


class StructuralDefinitionReading(StructuralValue):
    target_id: Nonempty
    component_ref: RetainedComponentRef
    link_ref: RetainedRelationshipDecisionRef
    component: LocatedDefinitionComponent
    outcome: DefinitionOutcome
    evidence: tuple[Nonempty, ...] = Field(min_length=1)
    premises: tuple[ApplicabilityPremise, ...] = Field(min_length=1)
    reason: Nonempty

    @model_validator(mode="after")
    def supported_premises(self) -> Self:
        if self.component_ref.component_id != self.component.component_id:
            raise ValueError("applicability reading substitutes its component")
        if {p.dimension for p in self.premises} != {
            "sense",
            "parameterization",
            "convention",
            "scope",
            "version",
            "parent",
        } or len(self.premises) != 6:
            raise ValueError("applicability requires exactly six distinct declared dimensions")
        states = {p.state for p in self.premises}
        if self.outcome.startswith("applicable_") and (
            "unknown" in states or "incompatible" in states
        ):
            raise ValueError("applicable reading requires resolved compatible premises")
        if self.outcome == "incompatible" and "incompatible" not in states:
            raise ValueError("incompatibility requires an explicit incompatible premise")
        return self


class DefinitionProduct(StructuralValue):
    usage_id: Nonempty
    candidate_list_id: Nonempty
    eligible_targets: tuple[Nonempty, ...]
    candidate_targets: tuple[Nonempty, ...]
    readings: tuple[StructuralDefinitionReading, ...]
    inventory_coverage: Literal["declared_selection", "known_gap"] = "declared_selection"
    retrieval_diagnosis: Literal["not_independently_assessed"] = "not_independently_assessed"

    @model_validator(mode="after")
    def membership(self) -> Self:
        if len(set(self.eligible_targets)) != len(self.eligible_targets) or len(
            set(self.candidate_targets)
        ) != len(self.candidate_targets):
            raise ValueError("duplicate eligible target or candidate")
        if not set(self.candidate_targets) <= set(self.eligible_targets):
            raise ValueError("candidate is outside eligible inventory")
        if len({(r.target_id, r.component_ref.identity) for r in self.readings}) != len(
            self.readings
        ):
            raise ValueError("duplicate target component reading")
        if not {r.target_id for r in self.readings} <= set(self.candidate_targets):
            raise ValueError("reading is outside fixed candidate list")
        return self


class TypedPremise(StructuralValue):
    """Exact source field and a separately qualified numerical reading."""

    span: LocatedDefinitionSpan
    grammar: Nonempty
    state: Literal["parsed", "unsupported", "ambiguous"]
    value: str | None = None
    comparator: Literal[">", ">=", "<", "<=", "="] | None = None
    quantity: str | None = None
    unit: str | None = None
    basis: str | None = None
    basis_evidence: LocatedDefinitionSpan | None = None

    @model_validator(mode="after")
    def faithful_parse(self) -> Self:
        if self.basis is not None or self.basis_evidence is not None:
            from .structural_parsing import COMPARISON_BASIS

            witness = self.basis_evidence
            match = COMPARISON_BASIS.fullmatch(witness.text) if witness is not None else None
            if (
                self.state != "parsed"
                or witness is None
                or witness.passage_id != self.span.passage_id
                or match is None
                or not self.basis
                or match[1].strip() != self.basis
            ):
                raise ValueError("typed basis requires its exact comparison-basis declaration")
        if self.state == "parsed":
            from .structural_parsing import parse_threshold

            actual = parse_threshold(self.span.text)
            if (
                actual is None
                or self.grammar != actual["grammar"]
                or (actual["value"], actual["comparator"], actual["quantity"], actual["unit"])
                != (self.value, self.comparator, self.quantity, self.unit)
            ):
                raise ValueError("typed premise differs from its source grammar")
        elif self.value is not None or self.comparator is not None:
            raise ValueError("unparsed premise cannot carry interpreted numeric values")
        return self


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


class ClauseField(StructuralValue):
    dimension: Dimension
    lexical_value: Nonempty
    evidence: tuple[Nonempty, ...] = Field(min_length=1)
    typed: TypedPremise | None = None
    span: LocatedDefinitionSpan | None = None
    spans: tuple[LocatedDefinitionSpan, ...] | None = None
    contribution_id: Nonempty | None = None
    literal: ComparisonLiteral | None = None
    condition: dict[str, Any] | None = None

    @model_validator(mode="after")
    def formal_source(self) -> Self:
        if self.literal is not None:
            from .structural_parsing import parse_comparison_literal

            if (
                self.spans is None
                or len(self.spans) != 1
                or parse_comparison_literal(self.spans[0].text)
                != self.literal.model_dump(mode="json", exclude_none=True)
            ):
                raise ValueError("formal operand differs from exact located syntax")
        return self


class ComparisonLiteral(StructuralValue):
    kind: Literal["date", "identifier", "quantity", "range"]
    value: str | None = None
    unit: str | None = None
    lower: str | None = None
    upper: str | None = None
    lower_closed: bool | None = None
    upper_closed: bool | None = None


class ClauseFieldGroup(StructuralValue):
    state: Literal["absent", "empty", "present", "unresolved"]
    grouping: Literal["singleton", "conjunction", "disjunction", "unresolved"] | None = None
    members: tuple[ClauseField, ...] = ()
    witnesses: tuple[LocatedDefinitionSpan, ...] = ()

    @model_validator(mode="after")
    def complete(self) -> Self:
        if self.state == "present" and not self.members:
            raise ValueError("present dimension requires members")
        if self.state in {"absent", "empty"} and (self.members or self.grouping):
            raise ValueError("absent or empty dimension cannot have members")
        if self.state == "empty" and not self.witnesses:
            raise ValueError("known empty dimension requires its source witness")
        if self.grouping == "singleton" and len(self.members) != 1:
            raise ValueError("singleton dimension requires one member")
        if self.grouping in {"conjunction", "disjunction"} and (
            len(self.members) < 2 or len(self.witnesses) != len(self.members) - 1
        ):
            raise ValueError("grouped members require an exact witness between each pair")
        return self


class ClauseReading(StructuralValue):
    passage_id: Nonempty
    fields: tuple[ClauseField, ...] = ()
    groups: dict[Dimension, ClauseFieldGroup] | None = None

    @model_validator(mode="after")
    def dimensions(self) -> Self:
        if self.groups is not None and (self.fields or set(self.groups) != set(DIMENSIONS)):
            raise ValueError("a grouped reading requires every dimension and no legacy fields")
        if len({f.dimension for f in self.fields}) != len(self.fields):
            raise ValueError("duplicate clause dimension")
        return self


class DimensionComparison(StructuralValue):
    dimension: Dimension
    outcome: Literal[
        "same_lexical_value", "different_lexical_value", "unknown", "incompatible_applicability"
    ]
    left: ClauseField | None = None
    right: ClauseField | None = None
    left_group: ClauseFieldGroup | None = None
    right_group: ClauseFieldGroup | None = None
    typed_outcome: Literal["equivalent", "different", "unknown", "unsupported", "ambiguous"] = (
        "unknown"
    )
    removed_interval: TriggerInterval | None = None
    added_interval: TriggerInterval | None = None
    assumptions: tuple[Nonempty, ...] = ()
    reason: Nonempty = "No source-qualified typed comparison has been established."


class RevisionSuccession(StructuralValue):
    older_id: Nonempty
    newer_id: Nonempty
    evidence: LocatedDefinitionSpan
    older_evidence: LocatedDefinitionSpan


class ComparisonProduct(StructuralValue):
    left_id: Nonempty
    right_id: Nonempty
    dimensions: tuple[DimensionComparison, ...]
    left_reading: RetainedContributionRef | None = None
    right_reading: RetainedContributionRef | None = None
    equivalence: Literal["not_asserted"] = "not_asserted"
    identity_standing: Literal["not_asserted"] = "not_asserted"
    applicability: Literal[
        "co_applicable", "successive_revisions", "differently_scoped", "unestablished"
    ] = "unestablished"
    applicability_reason: Nonempty = "No complete applicability premises have been established."
    succession: RevisionSuccession | None = None

    @model_validator(mode="after")
    def succession_custody(self) -> Self:
        grouped = self.left_reading is not None
        if grouped != (self.right_reading is not None) or any(
            (d.left_group is not None) != grouped
            or (d.right_group is not None) != grouped
            or (grouped and (d.left is not None or d.right is not None))
            for d in self.dimensions
        ):
            raise ValueError("comparison must bind both grouped sides")
        if (self.succession is not None) != (self.applicability == "successive_revisions"):
            raise ValueError("successive revisions require their directed source witness")
        if self.succession and (
            {self.succession.older_id, self.succession.newer_id} != {self.left_id, self.right_id}
            or self.succession.evidence.passage_id != self.succession.newer_id
            or self.succession.older_evidence.passage_id != self.succession.older_id
        ):
            raise ValueError("succession witness differs from compared revisions")
        return self


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


class DossierComparisonSelection(StructuralValue):
    comparison_product_id: Nonempty
    side: Literal["left", "right"]
    relationship_ref: RetainedRelationshipDecisionRef


class DossierComparisonBinding(StructuralValue):
    comparison_ref: RetainedStructuralRef
    side: Literal["left", "right"]
    relationship_ref: RetainedRelationshipDecisionRef
    relationship: Literal["denotes", "defined-by", "specializes"]
    root: RetainedComponentRef
    source: ExternalSourceRef
    citation: LocatedDefinitionSpan
    occurrence: tuple[LocatedDefinitionSpan, ...] = Field(min_length=1)
    comparison: ComparisonProduct
    opposite_source: ExternalSourceRef
    opposite_citation: LocatedDefinitionSpan

    @model_validator(mode="after")
    def sides(self) -> Self:
        left, right = (self.citation, self.opposite_citation)
        if self.side == "right":
            left, right = right, left
        if (
            (left.passage_id, right.passage_id)
            != (self.comparison.left_id, self.comparison.right_id)
            or self.comparison.left_reading is None
            or any(
                span.passage_id != self.citation.passage_id
                or not self.citation.start <= span.start < span.end <= self.citation.end
                for span in self.occurrence
            )
        ):
            raise ValueError("comparison binding differs from its exact located sides")
        return self


class DossierMember(StructuralValue):
    member_id: Nonempty
    passage_id: Nonempty
    citation: LocatedDefinitionSpan
    role: MemberRole
    sense: Nonempty
    scope: Nonempty
    effective_version: str | None = None
    relation_product_id: Nonempty
    definition_interpretation: DefinitionInterpretation | None = None
    applicability_outcome: DefinitionOutcome | None = None
    comparison_binding: DossierComparisonBinding | None = None
    contribution_ref: RetainedContributionRef | None = None
    contribution_citations: tuple[DossierContributionCitation, ...] | None = None
    semantic_dependency: DossierDependency | None = None
    computation_dependencies: tuple[Nonempty, ...] | None = None
    qualification: Literal[
        "proposed", "independently_supported", "ambiguous", "rejected", "unsupported"
    ] = "proposed"
    assessment_id: str | None = None

    @model_validator(mode="after")
    def assessment(self) -> Self:
        if self.qualification == "independently_supported" and not self.assessment_id:
            raise ValueError("supported member requires its independent assessment reference")
        if self.comparison_binding is not None and (
            self.contribution_ref is not None
            or self.comparison_binding.comparison_ref.product_id != self.relation_product_id
            or self.comparison_binding.root.component_id != self.sense
            or self.comparison_binding.citation.passage_id != self.passage_id
        ):
            raise ValueError("member differs from its comparison binding")
        if self.contribution_ref is not None:
            if (
                not self.contribution_citations
                or not self.computation_dependencies
                or self.relation_product_id != self.contribution_ref.contribution_id
                or self.citation != self.contribution_citations[0].span
                or self.passage_id != self.citation.passage_id
                or any(
                    c.contribution_id not in self.computation_dependencies
                    for c in self.contribution_citations
                )
            ):
                raise ValueError(
                    "source member requires its exact contribution and endpoint citation closure"
                )
            if self.qualification != "proposed" or self.assessment_id is not None:
                raise ValueError(
                    "source contribution membership does not establish independent semantic support"
                )
        elif self.contribution_citations is not None or self.computation_dependencies is not None:
            raise ValueError(
                "source citation closure requires an exact retained contribution reference"
            )
        if self.semantic_dependency is not None and (
            self.role != "relationship"
            or not self.contribution_citations
            or not set(self.semantic_dependency.dependent + self.semantic_dependency.prerequisite)
            <= set(self.contribution_citations)
            or {c.contribution_id for c in self.semantic_dependency.dependent}
            & {c.contribution_id for c in self.semantic_dependency.prerequisite}
        ):
            raise ValueError("typed dependency requires distinct qualified source endpoints")
        return self


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


class DossierProduct(StructuralValue):
    root_id: Nonempty
    root_component: RetainedComponentRef | None = None
    members: tuple[DossierMember, ...]
    predecessors: tuple[RetainedStructuralRef, ...] = ()
    contribution_predecessors: tuple[RetainedContributionRef, ...] = ()
    comparison_selections: tuple[DossierComparisonSelection, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    representatives: tuple[Nonempty, ...]
    missing_sections: tuple[MemberRole, ...]
    supported_facets: tuple[DossierFacet, ...] = ()
    representation: DossierRepresentation
    membership_completeness: Literal["declared_selection"] = "declared_selection"

    @model_validator(mode="after")
    def membership(self) -> Self:
        if self.root_component is not None and (
            self.root_id != self.root_component.component_id
            or not any(p.product_id == self.root_component.product_id for p in self.predecessors)
            or any(member.sense != self.root_id for member in self.members)
        ):
            raise ValueError("dossier membership differs from its exact root sense")
        if any(
            binding.root != self.root_component
            or binding.comparison_ref not in self.predecessors
            or DossierComparisonSelection(
                comparison_product_id=binding.comparison_ref.product_id,
                side=binding.side,
                relationship_ref=binding.relationship_ref,
            )
            not in self.comparison_selections
            for member in self.members
            if (binding := member.comparison_binding) is not None
        ):
            raise ValueError("comparison binding is outside exact dossier predecessors")
        ids = {m.member_id for m in self.members}
        if len(ids) != len(self.members):
            raise ValueError("duplicate dossier member")
        if (
            len(set(self.representatives)) != len(self.representatives)
            or not set(self.representatives) <= ids
        ):
            raise ValueError("invalid representative membership")
        if self.representatives != self.representation.selected or set(
            self.representation.omitted
        ) != ids - set(self.representatives):
            raise ValueError("dossier representation differs from its full membership")
        if any(f.member_id not in ids for f in self.supported_facets):
            raise ValueError("dossier facet refers outside full membership")
        facets = {f.facet_id for f in self.supported_facets if f.member_id in self.representatives}
        if set(self.representation.represented_facets) != facets:
            raise ValueError("represented facet lacks its selected supported member")
        all_facets = {f.facet_id for f in self.supported_facets}
        if (
            len(all_facets) != len(self.supported_facets)
            or set(self.representation.missing_facets) != all_facets - facets
        ):
            raise ValueError("facet representation is incomplete or duplicated")
        if (
            self.representation.membership_digest
            != sha256(
                canonical_bytes(
                    [m.model_dump(mode="json", exclude_none=True) for m in self.members]
                )
            ).hexdigest()
        ):
            raise ValueError("membership digest differs from full membership")
        if (
            self.representation.facet_digest
            != sha256(
                canonical_bytes(
                    [f.model_dump(mode="json", exclude_none=True) for f in self.supported_facets]
                )
            ).hexdigest()
        ):
            raise ValueError("facet digest differs from supported facets")
        mandatory = {m.member_id for m in self.members if m.role in MANDATORY_ROLES}
        if not mandatory <= set(self.representatives) or self.representation.mandatory_overflow != (
            len(mandatory) > self.representation.member_budget
        ):
            raise ValueError("mandatory dossier members must be retained")
        if len(self.representatives) > max(self.representation.member_budget, len(mandatory)):
            raise ValueError("representation exceeds declared member budget")
        return self


class StructuralProductReport(StructuralValue):
    version: Literal["structural-product-3"] = "structural-product-3"
    kind: Literal[
        "definition_components",
        "definition_applicability",
        "qualified_comparison",
        "dossier",
        "artifact_identity",
        "clause_classification",
    ]
    inputs: StructuralInput
    standing: Literal["private_proposal"] = "private_proposal"
    definition_components: DefinitionComponentsProduct | None = None
    definition: DefinitionProduct | None = None
    comparison: ComparisonProduct | None = None
    dossier: DossierProduct | None = None
    artifact_identity: ArtifactIdentityProduct | None = None
    clause_classification: ClauseClassificationProduct | None = None
    # The released ContextualEnrichmentReport validates this ordinary upstream report.
    retrieval_report: dict[str, Any] | None = None

    @model_validator(mode="after")
    def closure(self) -> Self:
        if (
            self.definition_components is not None,
            self.definition is not None,
            self.comparison is not None,
            self.dossier is not None,
            self.artifact_identity is not None,
            self.clause_classification is not None,
        ) != (
            self.kind == "definition_components",
            self.kind == "definition_applicability",
            self.kind == "qualified_comparison",
            self.kind == "dossier",
            self.kind == "artifact_identity",
            self.kind == "clause_classification",
        ):
            raise ValueError("structural report must contain exactly its declared product")
        passages = {p.passage_id for p in self.inputs.passages}
        cited: set[str] = set()
        if self.clause_classification is not None:
            by_id = {p.passage_id: p for p in self.inputs.passages}
            readings = self.clause_classification.readings
            if not readings or len({r.selection for r in readings}) != len(readings):
                raise ValueError("clause classification requires distinct selected focuses")
            for row in readings:
                passage = by_id.get(row.selection.passage_id)
                if (
                    passage is None
                    or row.selection.frame.contribution_id not in self.inputs.dependencies
                ):
                    raise ValueError("clause classification lacks its selected source dependency")
                if self.clause_classification.context_policy == "exact_focus" and (
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
        if self.definition_components:
            by_id = {p.passage_id: p for p in self.inputs.passages}
            for candidate in self.definition_components.role_candidates or ():
                span = candidate.span
                passage = by_id.get(span.passage_id)
                if (
                    passage is None
                    or not passage.start
                    <= candidate.window_start
                    < candidate.window_end
                    <= passage.end
                    or passage.text[span.start - passage.start : span.end - passage.start]
                    != span.text
                ):
                    raise ValueError("definition role differs from original passage")
                cited.add(span.passage_id)
            for component in self.definition_components.components:
                cited.update(component.evidence)
                for span in (component.term, component.content):
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
            cited.update(stage.passage_id for stage in self.definition_components.stages)
        if self.definition:
            cited.add(self.definition.usage_id)
            for reading in self.definition.readings:
                cited.update(reading.evidence)
                for premise in reading.premises:
                    cited.update(premise.evidence)
                if reading.component_ref.product_id not in self.inputs.dependencies:
                    raise ValueError("applicability component is not a declared dependency")
        if self.comparison:
            from .structural_parsing import (
                REVISION_DECLARATION,
                REVISION_LINEAGE,
                REVISION_SUCCESSION,
            )

            by_id = {p.passage_id: p for p in self.inputs.passages}

            def exact(span: LocatedDefinitionSpan) -> bool:
                passage = by_id.get(span.passage_id)
                return (
                    passage is not None
                    and passage.start <= span.start < span.end <= passage.end
                    and passage.text[span.start - passage.start : span.end - passage.start]
                    == span.text
                )

            cited.update((self.comparison.left_id, self.comparison.right_id))
            if succession := self.comparison.succession:
                older, newer = by_id.get(succession.older_id), by_id.get(succession.newer_id)
                match = REVISION_SUCCESSION.fullmatch(succession.evidence.text)
                old_match = REVISION_DECLARATION.fullmatch(succession.older_evidence.text)
                if (
                    older is None
                    or newer is None
                    or not older.parent
                    or older.parent != newer.parent
                    or older.scope != newer.scope
                    or older.source_ref != newer.source_ref
                    or not (older.end <= newer.start or newer.end <= older.start)
                    or any(
                        REVISION_LINEAGE.findall(passage.text) != [older.parent]
                        for passage in (older, newer)
                    )
                    or older.effective_version == newer.effective_version
                    or old_match is None
                    or old_match[1] != older.effective_version
                    or REVISION_DECLARATION.findall(older.text) != [older.effective_version]
                    or match is None
                    or match.groups() != (newer.effective_version, older.effective_version)
                    or not exact(succession.evidence)
                    or not exact(succession.older_evidence)
                ):
                    raise ValueError("succession differs from its exact original source")
            if tuple(d.dimension for d in self.comparison.dimensions) != DIMENSIONS:
                raise ValueError("comparison requires every ordered dimension, including unknowns")
            for dimension in self.comparison.dimensions:
                for passage_id, group in (
                    (self.comparison.left_id, dimension.left_group),
                    (self.comparison.right_id, dimension.right_group),
                ):
                    if group is None:
                        continue
                    if any(
                        not exact(span) or span.passage_id != passage_id for span in group.witnesses
                    ):
                        raise ValueError("group witness differs from selected original passage")
                    for member in group.members:
                        if member.dimension != dimension.dimension or member.evidence != (
                            passage_id,
                        ):
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
                                (
                                    p
                                    for p in self.inputs.passages
                                    if p.passage_id == span.passage_id
                                ),
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
                                raise ValueError(
                                    "clause field differs from its exact original source"
                                )
                            cited.add(span.passage_id)
                        if side.typed is not None:
                            span = side.typed.span
                            basis = side.typed.basis_evidence
                            if not exact(span) or (basis is not None and not exact(basis)):
                                raise ValueError(
                                    "typed field differs from its exact original source"
                                )
                            cited.add(span.passage_id)
        if self.dossier:
            cited.update(m.passage_id for m in self.dossier.members)
            for member in self.dossier.members:
                span = member.citation
                passage = next(
                    (p for p in self.inputs.passages if p.passage_id == member.passage_id), None
                )
                if (
                    passage is None
                    or span.passage_id != member.passage_id
                    or not passage.start <= span.start < span.end <= passage.end
                    or passage.text[span.start - passage.start : span.end - passage.start]
                    != span.text
                ):
                    raise ValueError("dossier member citation differs from original source")
        if self.artifact_identity:
            by_id = {p.passage_id: p for p in self.inputs.passages}
            for record in self.artifact_identity.records:
                for citation in record.citations:
                    passage = by_id.get(citation.passage_id)
                    if (
                        passage is None
                        or citation.source_ref != passage.source_ref
                        or not passage.start <= citation.start < citation.end <= passage.end
                        or passage.text[
                            citation.start - passage.start : citation.end - passage.start
                        ]
                        != citation.text
                    ):
                        raise ValueError("artifact citation differs from its exact original source")
                    cited.add(citation.passage_id)
        if not cited <= passages:
            raise ValueError("structural evidence lies outside declared passage closure")
        return self

    @property
    def product_id(self) -> str:
        return (
            "structural:"
            + sha256(
                canonical_bytes(
                    self.model_dump(mode="json", exclude_none=True, exclude={"retrieval_report"})
                )
            ).hexdigest()
        )
