"""Public wire types for the bounded exclusion comparison."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Wire(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ComparisonBinding(_Wire):
    release_id: str
    realization_id: str
    data_revision: int
    capture_id: str


class ComparisonInput(_Wire):
    run: int
    cut: int
    binding: ComparisonBinding


class ExclusionDeclaration(_Wire):
    left_kind: Literal["local", "known"]
    left_ref: str
    right_kind: Literal["local", "known"]
    right_ref: str
    reason: str


class ExclusionResolution(_Wire):
    left_entity_id: str
    right_entity_id: str


class ExclusionWitness(_Wire):
    source_uri: str
    locator: str
    provider: str
    operation_version: str
    source_view_id: int | None
    rendition_id: int | None
    span_id: int | None
    native_address: str | None


class CapturedExclusion(_Wire):
    observation_key: str
    local_id: str
    operation_id: str
    operation_version: str
    declaration: ExclusionDeclaration
    resolution: ExclusionResolution
    evidence: list[ExclusionWitness]


class ExclusionChange(_Wire):
    identity: tuple[str, str]
    kind: Literal["added", "removed", "changed", "unmatched_unassessed", "incomparable_operation"]
    facets: list[Literal["declaration", "resolution", "evidence"]] = []
    before: CapturedExclusion | None
    after: CapturedExclusion | None


class ExclusionComparison(_Wire):
    before: ComparisonInput
    after: ComparisonInput
    changes: list[ExclusionChange]
    examined_before: int
    examined_after: int
    complete: bool
    unknowns: list[str]


class RetainedComparison(_Wire):
    result_id: str
    role: str
    sha256: str


class ExclusionComparisonDelivery(_Wire):
    comparison: ExclusionComparison
    retained: RetainedComparison | None = None
