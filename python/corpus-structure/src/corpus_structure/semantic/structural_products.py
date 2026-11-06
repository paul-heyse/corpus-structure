"""Private cross-source products with original custody and explicit semantic limits.

These values are reports, not admission witnesses. Their source references must be
validated at native task completion; model validation alone grants no authority.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contextual_links import RetainedRelationshipDecisionRef
from .identity import canonical_bytes

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


class StructuralValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def identity(self) -> str:
        return sha256(canonical_bytes(self.model_dump(mode="json", exclude_none=True))).hexdigest()


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


class LocatedDefinitionComponent(StructuralValue):
    component_id: Digest
    term: LocatedDefinitionSpan
    content: LocatedDefinitionSpan
    interpretation: Literal["definition", "explanation", "unresolved"]
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


class DefinitionComponentsProduct(StructuralValue):
    components: tuple[LocatedDefinitionComponent, ...]
    stages: tuple[DefinitionStage, ...]

    @model_validator(mode="after")
    def unique_components(self) -> Self:
        if len({c.component_id for c in self.components}) != len(self.components):
            raise ValueError("duplicate definition component")
        return self


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


class ClauseField(StructuralValue):
    dimension: Dimension
    lexical_value: Nonempty
    evidence: tuple[Nonempty, ...] = Field(min_length=1)


class ClauseReading(StructuralValue):
    passage_id: Nonempty
    fields: tuple[ClauseField, ...]

    @model_validator(mode="after")
    def dimensions(self) -> Self:
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


class ComparisonProduct(StructuralValue):
    left_id: Nonempty
    right_id: Nonempty
    dimensions: tuple[DimensionComparison, ...]
    equivalence: Literal["not_asserted"] = "not_asserted"
    identity_standing: Literal["not_asserted"] = "not_asserted"


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


class DossierMember(StructuralValue):
    member_id: Nonempty
    passage_id: Nonempty
    role: MemberRole
    sense: Nonempty
    scope: Nonempty
    effective_version: str | None = None
    relation_product_id: Nonempty
    qualification: Literal[
        "proposed", "independently_supported", "ambiguous", "rejected", "unsupported"
    ] = "proposed"
    assessment_id: str | None = None

    @model_validator(mode="after")
    def assessment(self) -> Self:
        if self.qualification == "independently_supported" and not self.assessment_id:
            raise ValueError("supported member requires its independent assessment reference")
        return self


class DossierProduct(StructuralValue):
    root_id: Nonempty
    members: tuple[DossierMember, ...]
    representatives: tuple[Nonempty, ...]
    missing_sections: tuple[MemberRole, ...]
    membership_completeness: Literal["declared_selection"] = "declared_selection"

    @model_validator(mode="after")
    def membership(self) -> Self:
        ids = {m.member_id for m in self.members}
        if len(ids) != len(self.members):
            raise ValueError("duplicate dossier member")
        if (
            len(set(self.representatives)) != len(self.representatives)
            or not set(self.representatives) <= ids
        ):
            raise ValueError("invalid representative membership")
        return self


class StructuralProductReport(StructuralValue):
    version: Literal["structural-product-2"] = "structural-product-2"
    kind: Literal[
        "definition_components", "definition_applicability", "qualified_comparison", "dossier"
    ]
    inputs: StructuralInput
    standing: Literal["private_proposal"] = "private_proposal"
    definition_components: DefinitionComponentsProduct | None = None
    definition: DefinitionProduct | None = None
    comparison: ComparisonProduct | None = None
    dossier: DossierProduct | None = None
    # The released ContextualEnrichmentReport validates this ordinary upstream report.
    retrieval_report: dict[str, Any] | None = None

    @model_validator(mode="after")
    def closure(self) -> Self:
        if (
            self.definition_components is not None,
            self.definition is not None,
            self.comparison is not None,
            self.dossier is not None,
        ) != (
            self.kind == "definition_components",
            self.kind == "definition_applicability",
            self.kind == "qualified_comparison",
            self.kind == "dossier",
        ):
            raise ValueError("structural report must contain exactly its declared product")
        passages = {p.passage_id for p in self.inputs.passages}
        cited: set[str] = set()
        if self.definition_components:
            by_id = {p.passage_id: p for p in self.inputs.passages}
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
            cited.update((self.comparison.left_id, self.comparison.right_id))
            if tuple(d.dimension for d in self.comparison.dimensions) != DIMENSIONS:
                raise ValueError("comparison requires every ordered dimension, including unknowns")
            for dimension in self.comparison.dimensions:
                for side in (dimension.left, dimension.right):
                    if side:
                        cited.update(side.evidence)
        if self.dossier:
            cited.update(m.passage_id for m in self.dossier.members)
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
