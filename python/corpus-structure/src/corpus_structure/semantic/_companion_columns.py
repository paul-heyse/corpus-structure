# Generated from model/semantic/companion-projections.yaml.
from typing import Literal

from sqlalchemy import Named, TypedColumns

from .identifiers import ContentDigest as ContentDigest
from .identifiers import ProductKey as ProductKey
from .identifiers import ReleaseId as ReleaseId
from .identifiers import TaskId as TaskId


class PublishedInputRow(TypedColumns):
    input_ordinal: Named[int]
    input_role: Named[Literal["alternative", "policy_input", "recognition", "structural"]]
    input_task_id: Named[TaskId]
    input_product_key: Named[str]
    input_content_digest: Named[str]
    project_id: Named[str]
    demand_id: Named[str]
    read_id: Named[str]
    use_id: Named[str]
    product_id: Named[str]
    derivation_id: Named[str]
    selection_release_id: Named[str]
    producer_release_id: Named[ReleaseId]
    task_id: Named[TaskId]
    product_key: Named[ProductKey]
    content_digest: Named[ContentDigest]
    projection_id: Named[str]


class PublishedRelationRow(TypedColumns):
    relation_id: Named[str]
    relation_kind: Named[Literal["correspondence", "decision"]]
    relation_outcome: Named[str]
    comparison: Named[Literal["geometry", "grid", "mathematical", "order", "text"]]
    policy: Named[str]
    evidence: Named[str]
    endpoint_ordinal: Named[int]
    endpoint_role: Named[Literal["alternative", "evidence", "input", "output"]]
    target_task_id: Named[int]
    target_product_key: Named[str]
    target_content_digest: Named[str]
    target_occurrence_id: Named[str]
    project_id: Named[str]
    demand_id: Named[str]
    read_id: Named[str]
    use_id: Named[str]
    product_id: Named[str]
    derivation_id: Named[str]
    selection_release_id: Named[str]
    producer_release_id: Named[ReleaseId]
    task_id: Named[TaskId]
    product_key: Named[ProductKey]
    content_digest: Named[ContentDigest]
    projection_id: Named[str]


class PublishedCoverageRow(TypedColumns):
    coverage_id: Named[str]
    scope: Named[str]
    coverage_family: Named[str]
    discovery_policy: Named[str]
    outcome: Named[
        Literal["capped", "complete", "partial", "unknown", "unrequested", "unsupported"]
    ]
    detail: Named[str]
    supports_json: Named[str | None]
    project_id: Named[str]
    demand_id: Named[str]
    read_id: Named[str]
    use_id: Named[str]
    product_id: Named[str]
    derivation_id: Named[str]
    selection_release_id: Named[str]
    producer_release_id: Named[ReleaseId]
    task_id: Named[TaskId]
    product_key: Named[ProductKey]
    content_digest: Named[ContentDigest]
    projection_id: Named[str]


class PublishedMappingReportRow(TypedColumns):
    report_ordinal: Named[int]
    input_index: Named[int]
    input_task_id: Named[TaskId]
    input_product_key: Named[str]
    input_content_digest: Named[str]
    occurrence_id: Named[str | None]
    outcome: Named[Literal["dropped", "evidence_only", "mapped", "unresolved", "unsupported"]]
    label: Named[str | None]
    reason: Named[str | None]
    raw_start: Named[int | None]
    coordinate_frame: Named[str | None]
    coordinate_scale: Named[float | None]
    normalization: Named[Literal["clipped", "inherited", "none", "normalized", "unknown"] | None]
    project_id: Named[str]
    demand_id: Named[str]
    read_id: Named[str]
    use_id: Named[str]
    product_id: Named[str]
    derivation_id: Named[str]
    selection_release_id: Named[str]
    producer_release_id: Named[ReleaseId]
    task_id: Named[TaskId]
    product_key: Named[ProductKey]
    content_digest: Named[ContentDigest]
    projection_id: Named[str]
