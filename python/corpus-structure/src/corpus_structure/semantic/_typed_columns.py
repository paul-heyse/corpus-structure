"""Generated model column surfaces; python -m corpus_structure.semantic.typed_generation."""

from __future__ import annotations

from typing import Literal, Protocol, cast

from pydantic import JsonValue
from sqlalchemy import Column, Named, TypedColumns

from .identifiers import ReleaseId as ReleaseId
from .identifiers import RuntimeId as RuntimeId
from .metadata import table

PHYSICAL_MODEL_ID = "physical:ef2f67139be0d7207fcdf02099877d4b09f9f2a2143b12a4375ea7fc11110387"
TYPE_MODEL_ID = "89771079ba81a91d2c6beba47ef8535eba77d6be6dc3369c4aebe4c737f2351f"


class SemRuntimeBindingColumns(TypedColumns):
    release_id: Named[str]
    runtime_id: Named[RuntimeId]
    manifest_bytes: Named[bytes]
    execution_profile: Named[str]
    archive_bytes: Named[bytes]


class SemRuntimeBindingColumnsSet(Protocol):
    release_id: Column[str]
    runtime_id: Column[RuntimeId]
    manifest_bytes: Column[bytes]
    execution_profile: Column[str]
    archive_bytes: Column[bytes]


sem_runtime_binding = table("sem.runtime_binding").with_cols(SemRuntimeBindingColumns)
sem_runtime_binding_columns = cast(SemRuntimeBindingColumnsSet, sem_runtime_binding.c)


class OpsPdfStageDocumentColumns(TypedColumns):
    product_id: Named[str]
    revision_id: Named[str]
    release_id: Named[ReleaseId]
    source_digest: Named[str]
    mapping_profile: Named[Literal["pdf-native-records-v1"]]
    contract_version: Named[Literal["pdf-native-records-v1"]]
    native_schema_digest: Named[str]
    root_id: Named[str]


class OpsPdfStageDocumentColumnsSet(Protocol):
    product_id: Column[str]
    revision_id: Column[str]
    release_id: Column[ReleaseId]
    source_digest: Column[str]
    mapping_profile: Column[Literal["pdf-native-records-v1"]]
    contract_version: Column[Literal["pdf-native-records-v1"]]
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
