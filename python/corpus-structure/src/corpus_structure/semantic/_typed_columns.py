"""Generated model column surfaces; python -m corpus_structure.semantic.typed_generation."""

from __future__ import annotations

from typing import Literal, Protocol, cast

from pydantic import JsonValue
from sqlalchemy import Column, Named, TypedColumns

from ._operation_ids import RealizationId as RealizationId
from ._operation_ids import ReleaseId as ReleaseId
from .metadata import table

PHYSICAL_MODEL_ID = "physical:4030f96368cefa382e29a0af03dfab497d095c0bb4dac8a4f82797fc663461a6"
TYPE_MODEL_ID = "c8df91a5a57e1de160f566b3cee282662fc81d185d769dc8e8efe3f48debbfa7"


class DataOccurrenceColumns(TypedColumns):
    realization_id: Named[RealizationId]
    release_id: Named[ReleaseId]
    occurrence_id: Named[str]
    fact_id: Named[str]
    source: Named[str]
    item: Named[str]
    batch_id: Named[str]
    report_object_value_id: Named[str]
    report_qualification_value_id: Named[str | None]


class DataOccurrenceColumnsSet(Protocol):
    realization_id: Column[RealizationId]
    release_id: Column[ReleaseId]
    occurrence_id: Column[str]
    fact_id: Column[str]
    source: Column[str]
    item: Column[str]
    batch_id: Column[str]
    report_object_value_id: Column[str]
    report_qualification_value_id: Column[str | None]


data_occurrence = table("data.occurrence").with_cols(DataOccurrenceColumns)
data_occurrence_columns = cast(DataOccurrenceColumnsSet, data_occurrence.c)


class OpsPdfStageDocumentColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    release_id: Named[ReleaseId]
    source_digest: Named[str]
    mapping_profile: Named[str]
    contract_version: Named[str]
    native_schema_digest: Named[str]
    root_id: Named[str]


class OpsPdfStageDocumentColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    release_id: Column[ReleaseId]
    source_digest: Column[str]
    mapping_profile: Column[str]
    contract_version: Column[str]
    native_schema_digest: Column[str]
    root_id: Column[str]


ops_pdf_stage_document = table("ops.pdf_stage_document").with_cols(OpsPdfStageDocumentColumns)
ops_pdf_stage_document_columns = cast(OpsPdfStageDocumentColumnsSet, ops_pdf_stage_document.c)


class OpsPdfStageNativeColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    record_id: Named[str]
    native_type: Named[str]
    family: Named[
        Literal["cell", "detail", "header", "node", "page", "provenance", "reference", "table"]
    ]
    native_address: Named[str | None]
    native_address_stream_id: Named[str | None]
    scalars_json: Named[JsonValue]
    structure_json: Named[JsonValue]


class OpsPdfStageNativeColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    record_id: Column[str]
    native_type: Column[str]
    family: Column[
        Literal["cell", "detail", "header", "node", "page", "provenance", "reference", "table"]
    ]
    native_address: Column[str | None]
    native_address_stream_id: Column[str | None]
    scalars_json: Column[JsonValue]
    structure_json: Column[JsonValue]


ops_pdf_stage_native = table("ops.pdf_stage_native").with_cols(OpsPdfStageNativeColumns)
ops_pdf_stage_native_columns = cast(OpsPdfStageNativeColumnsSet, ops_pdf_stage_native.c)


class OpsPdfStageMembershipColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    parent_id: Named[str]
    field_name: Named[str]
    ordinal: Named[int]
    member_key: Named[str | None]
    member_key_stream_id: Named[str | None]
    value_kind: Named[Literal["parts", "record", "scalar"]]
    record_id: Named[str | None]
    scalar_json: Named[JsonValue | None]
    stream_id: Named[str | None]


class OpsPdfStageMembershipColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    parent_id: Column[str]
    field_name: Column[str]
    ordinal: Column[int]
    member_key: Column[str | None]
    member_key_stream_id: Column[str | None]
    value_kind: Column[Literal["parts", "record", "scalar"]]
    record_id: Column[str | None]
    scalar_json: Column[JsonValue | None]
    stream_id: Column[str | None]


ops_pdf_stage_membership = table("ops.pdf_stage_membership").with_cols(OpsPdfStageMembershipColumns)
ops_pdf_stage_membership_columns = cast(OpsPdfStageMembershipColumnsSet, ops_pdf_stage_membership.c)


class OpsPdfStageReferenceColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    reference_id: Named[str]
    source_id: Named[str]
    field_name: Named[str]
    native_pointer: Named[str | None]
    native_pointer_stream_id: Named[str | None]
    target_id: Named[str | None]


class OpsPdfStageReferenceColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    reference_id: Column[str]
    source_id: Column[str]
    field_name: Column[str]
    native_pointer: Column[str | None]
    native_pointer_stream_id: Column[str | None]
    target_id: Column[str | None]


ops_pdf_stage_reference = table("ops.pdf_stage_reference").with_cols(OpsPdfStageReferenceColumns)
ops_pdf_stage_reference_columns = cast(OpsPdfStageReferenceColumnsSet, ops_pdf_stage_reference.c)


class OpsPdfStageArtifactStreamColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    stream_id: Named[str]
    byte_length: Named[int]
    serialization_sha256: Named[str | None]
    byte_root: Named[str]
    encoding_profile: Named[str]


class OpsPdfStageArtifactStreamColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    stream_id: Column[str]
    byte_length: Column[int]
    serialization_sha256: Column[str | None]
    byte_root: Column[str]
    encoding_profile: Column[str]


ops_pdf_stage_artifact_stream = table("ops.pdf_stage_artifact_stream").with_cols(
    OpsPdfStageArtifactStreamColumns
)
ops_pdf_stage_artifact_stream_columns = cast(
    OpsPdfStageArtifactStreamColumnsSet, ops_pdf_stage_artifact_stream.c
)


class OpsPdfStageArtifactPartColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    stream_id: Named[str]
    ordinal: Named[int]
    byte_offset: Named[int]
    byte_length: Named[int]
    body: Named[bytes]
    sha256_digest: Named[str]


class OpsPdfStageArtifactPartColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    stream_id: Column[str]
    ordinal: Column[int]
    byte_offset: Column[int]
    byte_length: Column[int]
    body: Column[bytes]
    sha256_digest: Column[str]


ops_pdf_stage_artifact_part = table("ops.pdf_stage_artifact_part").with_cols(
    OpsPdfStageArtifactPartColumns
)
ops_pdf_stage_artifact_part_columns = cast(
    OpsPdfStageArtifactPartColumnsSet, ops_pdf_stage_artifact_part.c
)
