"""Generated closed native wire types and fixed call facade; do not edit."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal, NewType, NotRequired, Required, TypedDict, cast

from corpus_structure.semantic.identifiers import ReleaseId

type WireExactJSONValue = (
    dict[str, WireExactJSONValue]
    | list[WireExactJSONValue]
    | str
    | bool
    | int
    | float
    | Decimal
    | None
)

WireAdmissionId = NewType("WireAdmissionId", str)
WireAttempt = NewType("WireAttempt", int)
WireCompletionIntentId = NewType("WireCompletionIntentId", str)
WireDemandId = NewType("WireDemandId", str)
WireDerivationId = NewType("WireDerivationId", str)
WireExternalPacketId = NewType("WireExternalPacketId", str)
WireFailureId = NewType("WireFailureId", str)
WireGeneration = NewType("WireGeneration", int)
WireKindContract = NewType("WireKindContract", str)
WireMemberId = NewType("WireMemberId", str)
WireObligationId = NewType("WireObligationId", str)
WireOperationId = NewType("WireOperationId", str)
WireOriginalSourceId = NewType("WireOriginalSourceId", str)
WirePopulationId = NewType("WirePopulationId", str)
WireProductId = NewType("WireProductId", str)
WireProjectId = NewType("WireProjectId", str)
WirePublicationReceiptId = NewType("WirePublicationReceiptId", str)
WireReadIdentity = NewType("WireReadIdentity", str)
WireReadSnapshotIdentity = NewType("WireReadSnapshotIdentity", str)
WireRequestId = NewType("WireRequestId", str)
WireRuntimeId = NewType("WireRuntimeId", str)
WireSubjectId = NewType("WireSubjectId", str)
WireTaskIdentity = NewType("WireTaskIdentity", int)


class WireAuthoredFactRef(TypedDict):
    analyzed_scope: Required[WireDdoJsonValue]
    author: Required[str]
    kind: Required[Literal["authored-fact"]]
    kind_contract: Required[WireKindContract]
    meaning_body: Required[WireJsonValue]
    original_source: Required[WireOriginalSourceId]
    project_id: Required[WireProjectId]
    selection_id: Required[str]
    subject: Required[WireSubjectId]


class WireCPUExecutionReceipt(TypedDict):
    main_thread: Required[bool]
    native_pools_json: Required[str]
    native_thread_limit: Required[int | None]
    pid: Required[int]
    request_digest: Required[str]


class WireExternalExecutionReceipt(TypedDict):
    actor_assertion: Required[str]
    admitting_principal: Required[str]
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[str]
    model_assertion: Required[str | None]
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]
    receipt_id: Required[WirePublicationReceiptId]
    request_id: Required[WireRequestId]
    result_digest: Required[str]
    runtime_id: Required[WireRuntimeId]
    task_id: Required[WireTaskIdentity]
    version: Required[Literal["external-execution-receipt-v1"]]


class WireExternalSourceRef(TypedDict):
    coordinate_version: Required[Literal[2, 3]]
    cut_id: Required[int]
    native_content_digest: Required[str]
    native_product_key: Required[str]
    native_task_id: Required[int]
    project_id: Required[WireProjectId]
    projection_digest: Required[str]
    recipe_digest: Required[str]
    release_id: Required[ReleaseId]
    result_revision: Required[int]
    run_id: Required[int]
    source_view_id: Required[int]


class WireLogicalProviderMember(TypedDict):
    attempt: Required[WireAttempt]
    count: Required[int]
    generation: Required[WireGeneration]
    input_digest: Required[str]
    member: Required[str]
    request_id: Required[WireRequestId]
    start: Required[int]
    task_id: Required[WireTaskIdentity]


class WireNativeExecutionReceipt(TypedDict):
    host_generation: Required[str]
    input_digest: Required[str]
    output_digest: Required[str]
    profile: Required[str]
    provider: Required[str]
    request_id: Required[WireRequestId]
    runtime: Required[str]


class WireOriginalDocumentRef(TypedDict):
    content_hash: Required[str]
    document_key: Required[str]
    kind: Required[Literal["original-document"]]
    mime: Required[str]
    project_id: Required[WireProjectId]


class WirePublishedPdfDocumentRef(TypedDict):
    build_id: Required[str]
    frozen_digest: Required[str]
    kind: Required[str]
    logical_digest: Required[str]
    product_key: Required[str]
    recipe_digest: Required[str]
    release_id: Required[ReleaseId]
    schema_digest: Required[str]
    source_digest: Required[str]
    task_id: Required[WireTaskIdentity]


class WirePdfExecutionReceipt(TypedDict):
    publication: Required[WirePublishedPdfDocumentRef]
    publisher_attempt: Required[int]
    publisher_holder: Required[str]


class WireProviderExecutionReceipt(TypedDict):
    cohort_digest: Required[str]
    cohort_members: Required[list[str]]
    correlation: Required[str]
    logical_members: Required[list[WireLogicalProviderMember]]
    member_count: Required[int]
    member_offset: Required[int]
    native_member_digests: Required[list[str]]
    physical: Required[list[WireNativeExecutionReceipt]]
    work_members: Required[list[list[WireExactJSONValue]]]


class WireAuthoredFactSelector(TypedDict):
    scope: Required[Literal["authored-fact"]]


class WireAdmitAuthoredDataRequest(TypedDict):
    demand_id: Required[WireDemandId]
    reference: Required[WireAuthoredFactRef]
    selection_name: Required[WireIdentifier]
    selectors: Required[list[WireAuthoredFactSelector]]


class WireNativeExecutionEvidence(TypedDict):
    attempt: Required[WireAttempt]
    cpu_receipts: Required[list[WireCPUExecutionReceipt]]
    external_receipts: NotRequired[list[WireExternalExecutionReceipt]]
    generation: Required[WireGeneration]
    holder: Required[str]
    host_receipts: Required[list[WireNativeExecutionReceipt]]
    pdf_receipts: NotRequired[list[WirePdfExecutionReceipt]]
    provider_receipts: NotRequired[list[WireProviderExecutionReceipt]]
    request_id: Required[WireRequestId]
    runtime_id: Required[WireRuntimeId]
    task_id: Required[WireTaskIdentity]
    version: Required[Literal["native-execution-evidence-v1"]]


class WireInputMember(TypedDict):
    member_id: NotRequired[WireMemberId | None]
    multiplicity: Required[WirePositiveInteger]
    position: Required[WireNonnegativeInteger]
    product_id: Required[WireProductId]
    role: Required[WireIdentifier]
    support_derivation_id: NotRequired[WireIdentifier | None]


class WireChoice(TypedDict):
    alternative: Required[WireIdentifier]
    choice_group: Required[WireIdentifier]
    selected: Required[bool]


class WireMemberContext(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    original_source: Required[WireIdentifier]
    subject: Required[WireIdentifier]
    subject_definition: Required[WireIdentifier]


class WireCoordinate(TypedDict):
    end: Required[WireNonnegativeInteger]
    original_source: Required[WireOriginalSourceId]
    page: NotRequired[WireNonnegativeInteger | None]
    start: Required[WireNonnegativeInteger]


class WireCoverage(TypedDict):
    complete: Required[bool]
    end: Required[WireNonnegativeInteger]
    scope: Required[WireIdentifier]
    start: Required[WireNonnegativeInteger]


class WireEndpointVariant1(TypedDict):
    member_id: Required[WireMemberId]
    role: Required[WireIdentifier]
    scope: Required[Literal["local"]]


class WireEndpointVariant2(TypedDict):
    member_id: Required[WireMemberId]
    product_id: Required[WireProductId]
    role: Required[WireIdentifier]
    scope: Required[Literal["external"]]


class WireRoleMember(TypedDict):
    multiplicity: Required[WirePositiveInteger]
    position: Required[WireNonnegativeInteger]
    role: Required[WireIdentifier]


class WireProductMember(TypedDict):
    body: Required[WireSemanticValue]
    choices: NotRequired[list[WireChoice]]
    context: Required[WireMemberContext]
    coordinates: NotRequired[list[WireCoordinate]]
    coverage: NotRequired[list[WireCoverage]]
    endpoints: NotRequired[list[WireEndpoint]]
    kind_contract: Required[WireKindContract]
    member_id: Required[WireMemberId]
    roles: NotRequired[list[WireRoleMember]]


class WireProduct(TypedDict):
    artifact_digest: NotRequired[WireIdentifier | None]
    body: Required[WireSemanticValue]
    kind_contract: Required[WireKindContract]
    members: Required[list[WireProductMember]]


class WireOutputMember(TypedDict):
    member_id: NotRequired[WireMemberId | None]
    multiplicity: Required[WirePositiveInteger]
    position: Required[WireNonnegativeInteger]
    product: Required[WireProduct]
    role: Required[WireIdentifier]


class WireComputationalSupportMember(TypedDict):
    admission_use_id: NotRequired[WireIdentifier | None]
    derivation_id: Required[WireDerivationId]
    kind: NotRequired[Literal["computation"]]
    position: Required[WireNonnegativeInteger]
    role: Required[WireIdentifier]


class WireOriginalSourceSupportMember(TypedDict):
    admission_id: Required[WireAdmissionId]
    kind: Required[Literal["original-source"]]
    position: Required[WireNonnegativeInteger]
    role: Required[WireIdentifier]
    source_reference: Required[WireIdentifier]


class WireAuthoredFactSupportMember(TypedDict):
    admission_id: Required[WireAdmissionId]
    kind: Required[Literal["authored"]]
    position: Required[WireNonnegativeInteger]
    role: Required[WireIdentifier]
    source_reference: Required[WireIdentifier]


class WireCompletion(TypedDict):
    execution_evidence: NotRequired[WireNativeExecutionEvidence]
    implementation_revision: Required[WireIdentifier]
    inputs: Required[list[WireInputMember]]
    outcome: Required[WireIdentifier]
    outputs: Required[list[WireOutputMember]]
    support: Required[list[WireSupportMember]]


class WireAdmitExternalDataResultRequest(TypedDict):
    actor_assertion: Required[WireIdentifier]
    attempt: Required[WireAttempt]
    completion: Required[WireCompletion]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    model_assertion: Required[WireIdentifier | None]
    packet_id: Required[WireExternalPacketId]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireAdmitExternalDataResultResult(TypedDict):
    intent_id: Required[WireCompletionIntentId]
    receipt: Required[WireExternalExecutionReceipt]


class WireOriginalDocumentSelector(TypedDict):
    scope: Required[Literal["whole-document"]]


class WireAdmitOriginalDocumentAssetRequest(TypedDict):
    demand_id: Required[WireDemandId]
    reference: Required[WireOriginalDocumentRef]
    selection_name: Required[WireIdentifier]
    selectors: Required[list[WireOriginalDocumentSelector]]


class WireExternalSourceReference(TypedDict):
    coordinate_version: Required[Literal[2, 3]]
    cut_id: Required[int]
    native_content_digest: Required[str]
    native_product_key: Required[str]
    native_task_id: Required[int]
    project_id: Required[WireProjectId]
    projection_digest: Required[str]
    recipe_digest: Required[str]
    release_id: Required[ReleaseId]
    result_revision: Required[int]
    run_id: Required[int]
    source_view_id: Required[int]


class WireOriginalSourceSelector(TypedDict):
    end: NotRequired[WireNonnegativeInteger]
    native_pointer: NotRequired[WireIdentifier]
    page: NotRequired[WirePositiveInteger]
    projection: Required[WireIdentifier]
    start: NotRequired[WireNonnegativeInteger]


class WireAdmitOriginalSourceViewRequest(TypedDict):
    demand_id: Required[WireDemandId]
    reference: Required[WireExternalSourceReference]
    selection_name: Required[WireIdentifier]
    selectors: Required[list[WireOriginalSourceSelector]]


class WireAdmitOriginalSourceViewResult(TypedDict):
    admission_id: Required[WireAdmissionId]
    analyzed_scope: Required[WireJsonValue]
    evidence: Required[WireJsonValue]
    kind_contract: Required[WireKindContract]
    original_source: Required[WireOriginalSourceId]
    product_id: Required[WireProductId]
    selection_name: Required[WireIdentifier]
    source_reference: Required[WireIdentifier]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]
    trust_snapshot: Required[WireTrustSnapshot]


class WireAdoptDataCompletionIntentRequest(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    intent_id: Required[WireCompletionIntentId]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireAdoptDataCompletionIntentResult(TypedDict):
    intent_id: Required[WireCompletionIntentId]
    producer_attempt: Required[WirePositiveInteger]
    producer_task_id: Required[WireTaskId]


class WirePopulationReference(TypedDict):
    name: Required[WireIdentifier]
    population_id: Required[WirePopulationId]
    role: Required[WireIdentifier]


class WireBinding(TypedDict):
    inference: Required[WireIdentifier]
    inputs: Required[list[WireInputMember]]
    parameters: Required[WireTaggedMapping]
    populations: Required[list[WirePopulationReference]]
    read_id: Required[WireReadIdentity]
    request_inputs: Required[WireTaggedMapping]
    support: Required[list[WireSupportMember]]


class WireAttachDataRequestRequest(TypedDict):
    binding: Required[WireBinding]
    obligation_id: Required[WireObligationId]
    rebind_derivation: NotRequired[WireIdentifier]
    replicate: Required[WireIdentifier | None]
    request_key: NotRequired[WireIdentifier]
    request_meaning: Required[WireRequestMeaning]


class WireAttachDataRequestResult(TypedDict):
    action: Required[Literal["compute", "reconcile", "reuse"]]
    derivation_id: Required[WireDerivationId | None]
    fate: Required[Literal["attached", "fulfilled"]]
    generation: Required[WireGeneration]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    task_id: Required[WireTaskIdentity | None]
    trust_snapshot: Required[WireTrustSnapshot]
    use_id: Required[WireIdentifier]


class WireAttemptFailure(TypedDict):
    code: Required[WireIdentifier]
    message: Required[WireIdentifier]


class WireAttemptFailureObservation(TypedDict):
    attempt: Required[WireAttempt]
    failure: Required[WireAttemptFailure]
    failure_id: Required[WireFailureId]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireAuthoredFactSelection(TypedDict):
    reference: Required[WireAuthoredFactRef]
    selectors: Required[list[WireAuthoredFactSelector]]


class WireBindingReason(TypedDict):
    code: Required[WireIdentifier]
    detail: Required[WireText]
    location: Required[WireText]


class WireCancelDataDemandRequest(TypedDict):
    demand_id: Required[WireDemandId]
    reason: Required[WireIdentifier]


class WireCancelDataDemandResultRequestsItem(TypedDict):
    generation: Required[WireGeneration]
    interest: Required[Literal["shared", "orphaned"]]
    physical_retirement: Required[Literal["unconfirmed"]]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity | None]


class WireCancelDataDemandResult(TypedDict):
    demand_id: Required[WireDemandId]
    reason: Required[WireIdentifier]
    requests: Required[list[WireCancelDataDemandResultRequestsItem]]
    state: Required[Literal["cancelled"]]


class WireClaimDataRequestRequest(TypedDict):
    external_packet_id: NotRequired[WireExternalPacketId]
    holder: Required[WireIdentifier]
    lease_seconds: Required[int]
    request_id: Required[WireRequestId]


class WireClaimDataRequestResultVariant1(TypedDict):
    state: Required[Literal["no-work"]]


class WireClaimDataRequestResultVariant2(TypedDict):
    action: Required[Literal["compute", "reconcile"]]
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_until: Required[str]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    state: Required[Literal["claimed"]]
    task_id: Required[WireTaskIdentity]
    trust_snapshot: Required[WireTrustSnapshot]


class WireClaimExternalDataPacketRequest(TypedDict):
    demand_id: NotRequired[WireDemandId]
    holder: Required[WireIdentifier]
    lease_seconds: Required[int]
    packet_id: Required[WireExternalPacketId]
    project_id: Required[WireProjectId]


class WireCloseDataPopulationRequest(TypedDict):
    demand_id: Required[WireDemandId]
    derivation_id: Required[WireDerivationId]
    member_role: Required[WireIdentifier]
    name: Required[WireIdentifier]
    product_id: Required[WireProductId]


class WirePopulationProducerContext(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WirePopulationSelectionEvidence(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    choices: Required[WireParameterMap]
    definition: Required[WireIdentifier]
    eligibility: Required[WireIdentifier]
    filter: Required[WireJsonValue]
    obligation_id: Required[WireObligationId]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId]
    parameter_meaning: Required[WireSemanticValue]
    parent_population_id: Required[WireIdentifier]
    read_id: Required[WireReadIdentity]
    role: Required[WireIdentifier]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WirePopulationEvidence(TypedDict):
    admission_use_id: Required[WireIdentifier]
    derivation_id: Required[WireDerivationId]
    member_role: Required[WireIdentifier]
    population_id: Required[WirePopulationId]
    producer_context: NotRequired[WirePopulationProducerContext]
    product_id: Required[WireProductId]
    selection: NotRequired[WirePopulationSelectionEvidence]
    trust_snapshot: Required[WireTrustSnapshot]


class WirePopulationMember(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    member_id: Required[WireMemberId]
    original_source: Required[WireOriginalSourceId]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WireCloseDataPopulationResult(TypedDict):
    complete: Required[bool]
    evidence: Required[WirePopulationEvidence]
    members: Required[list[WirePopulationMember]]
    name: Required[WireIdentifier]
    population_id: Required[WirePopulationId]
    semantic_key: Required[WireIdentifier]


class WireDemandReadScope(TypedDict):
    operation_id: NotRequired[WireOperationId]
    original_source: NotRequired[WireOriginalSourceId]
    product_ids: NotRequired[list[WireProductId]]
    subject: NotRequired[WireSubjectId]


class WireDiscoverySelection(TypedDict):
    output_role: Required[WireIdentifier]
    population: Required[WireIdentifier]
    producer: Required[WireOperationId]
    target: Required[WireOperationId]
    target_role: NotRequired[WireIdentifier]


class WireSelectedOperation(TypedDict):
    choices: Required[WireParameterMap]
    definition: Required[WireIdentifier]
    dependencies: Required[list[WireOperationId]]
    eligibility: Required[WireIdentifier]
    operation: Required[WireOperationId]
    parameter_meaning: Required[WireTaggedMapping]
    parameters: Required[WireParameterMap]
    recipe: Required[WireIdentifier]
    replicate: Required[WireIdentifier | None]


class WireOriginalNativeSelection(TypedDict):
    reference: Required[WireExternalSourceReference]
    selectors: Required[list[WireOriginalSourceSelector]]


class WireOriginalDocumentSelection(TypedDict):
    reference: Required[WireOriginalDocumentRef]
    selectors: Required[list[WireOriginalDocumentSelector]]


class WireRootSubject(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    original_source: Required[WireOriginalSourceId]
    subject: Required[WireSubjectId]


class WireSemanticSourceReference(TypedDict):
    member_id: NotRequired[WireMemberId]
    product_id: Required[WireProductId]


class WireSourceSetEntry(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    member: Required[WireIdentifier | None]
    original_source: Required[WireOriginalSourceId]
    product: Required[WireIdentifier]
    project_id: Required[WireProjectId]
    reference: Required[WireExternalSourceReference | WireSemanticSourceReference]
    source_reference: Required[WireIdentifier]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WireDemandIntent(TypedDict):
    discovery: Required[list[WireDiscoverySelection]]
    execution_profile: Required[WireIdentifier]
    inference: Required[WireIdentifier]
    model: Required[str]
    operations: Required[list[WireSelectedOperation]]
    original_sources: NotRequired[dict[str, WireOriginalSourceSelection]]
    root_operations: Required[list[WireOperationId]]
    roots: Required[list[WireRootSubject]]
    source_sets: NotRequired[dict[str, list[WireSourceSetEntry]]]
    targets: Required[list[WireOperationId]]
    version: Required[Literal["data-demand-intent-v1"]]


class WireContinuation(TypedDict):
    after: Required[WireObligationId]
    demand_id: Required[WireDemandId]
    frontier_at: Required[WireFrontierAt]
    limit: Required[int]
    max_bytes: Required[int]
    read_id: Required[WireReadIdentity]
    read_snapshot: Required[WireReadSnapshot]
    scope: NotRequired[WireDemandReadScope]
    selection: Required[WireDemandIntent]
    support_after: NotRequired[WireIdentifier]
    trust_snapshot: Required[WireTrustSnapshot]
    view: Required[Literal["frontier", "products", "support"]]


class WireDataAttemptLostResult(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    reason: Required[Literal["fence", "cancelled", "revoked", "support-unavailable"]]
    request_id: Required[WireRequestId]
    state: Required[Literal["lost"]]
    task_id: Required[WireTaskIdentity]


class WireExpandDataObligationRequest(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    demand_id: Required[WireDemandId]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId]
    parameters: Required[WireParameterMap]
    population_id: NotRequired[WirePopulationId]
    subject: Required[WireSubjectId]


class WireExpandDataObligationResult(TypedDict):
    obligation_id: Required[WireObligationId]


class WireExternalPacketHead(TypedDict):
    generation: Required[WireGeneration]
    operation_id: Required[WireOperationId]
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]
    request_id: Required[WireRequestId]
    state: Required[Literal["awaiting-external"]]
    subject: Required[WireSubjectId]
    task_id: Required[WireTaskIdentity]


class WireInspectDataCompletionRequest(TypedDict):
    demand_id: NotRequired[WireDemandId]
    generation: NotRequired[WireGeneration]
    intent_id: Required[WireCompletionIntentId]
    request_id: NotRequired[WireRequestId]


class WireInspectDataCompletionResultVariant1(TypedDict):
    intent_retained: Required[Literal[False]]
    state: Required[Literal["known-uncommitted"]]


class WireInspectDataCompletionResultVariant2(TypedDict):
    intent_retained: Required[Literal[True]]
    producer_attempt: Required[WirePositiveInteger]
    producer_task_id: Required[WireTaskId]
    state: Required[Literal["known-uncommitted"]]


class WireInspectDataCompletionResultVariant3(TypedDict):
    completion_state: Required[Literal["success", "empty", "failed"]]
    derivation_id: Required[WireDerivationId]
    intent_retained: Required[Literal[True]]
    producer_attempt: Required[WirePositiveInteger]
    producer_task_id: Required[WireTaskId]
    receipt_id: Required[WirePublicationReceiptId]
    runtime_id: Required[WireRuntimeId]
    semantic_outcome: Required[WireIdentifier]
    state: Required[Literal["committed"]]
    trust_snapshot: Required[WireTrustSnapshot]


class WireInspectDataCompletionResultVariant4(TypedDict):
    intent_retained: Required[Literal[False]]
    reason: Required[Literal["intent-request-binding-unavailable"]]
    state: Required[Literal["unavailable"]]


class WireInspectDataExecutionRequest(TypedDict):
    operation_id: Required[WireOperationId]
    release_id: Required[ReleaseId]
    runtime_id: NotRequired[WireRuntimeId]


class WireInspectDataExecutionResultRuntimeVariant2(TypedDict):
    archive_sha256: Required[str]
    manifest_sha256: Required[str]


class WireInspectDataExecutionResult(TypedDict):
    implementation_revision: Required[WireIdentifier]
    input_roles: Required[list[WireJsonValue]]
    output_roles: Required[list[WireJsonValue]]
    profile: Required[WireIdentifier]
    recipe: Required[WireIdentifier]
    runtime: Required[WireInspectDataExecutionResultRuntimeVariant2 | None]


class WireInspectExternalDataResultRequest(TypedDict):
    packet_id: Required[WireExternalPacketId]


class WireInspectExternalDataResultResult(TypedDict):
    intent_id: Required[WireCompletionIntentId | None]
    packet_id: Required[WireExternalPacketId]
    publication: Required[WireJsonValue]
    receipt: Required[WireExternalExecutionReceipt | None]
    state: Required[
        Literal["awaiting-external", "retained", "committed", "cancelled", "superseded"]
    ]


class WirePopulation(TypedDict):
    complete: Required[bool]
    demand_id: Required[WireDemandId]
    evidence: Required[WirePopulationEvidence]
    id: Required[WireIdentifier]
    members: Required[list[WirePopulationMember]]
    name: Required[WireIdentifier]
    population_id: Required[WirePopulationId]
    semantic_key: Required[WireIdentifier]


class WirePublishDataDerivationRequest(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    intent_id: Required[WireCompletionIntentId]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]
    trust_snapshot: NotRequired[WireTrustSnapshot]


class WirePublishDataDerivationResult(TypedDict):
    derivation_id: Required[WireDerivationId]
    receipt_id: Required[WirePublicationReceiptId]
    replayed: Required[bool]
    trust_snapshot: Required[WireTrustSnapshot]


class WireReadDemandResultRequest(TypedDict):
    after: NotRequired[WireObligationId]
    demand_id: Required[WireDemandId]
    frontier_at: NotRequired[WireFrontierAt]
    limit: NotRequired[int]
    max_bytes: NotRequired[int]
    read_id: NotRequired[WireReadIdentity]
    read_snapshot: NotRequired[WireReadSnapshot]
    scope: NotRequired[WireDemandReadScope]
    selection: NotRequired[WireDemandIntent]
    support_after: NotRequired[WireIdentifier]
    trust_snapshot: NotRequired[WireTrustSnapshot]
    view: NotRequired[Literal["frontier", "products", "support"]]


class WireResultObligation(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    demand_id: Required[WireDemandId]
    fate: Required[WireVisibleFate]
    generation: Required[WireGeneration | None]
    historical_fate: Required[WireHistoricalFate | None]
    id: Required[WireIdentifier]
    intent_id: Required[WireCompletionIntentId | None]
    obligation_id: Required[WireObligationId]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId]
    parameters: Required[WireParameterMap]
    request_id: Required[WireRequestId | None]
    subject: Required[WireSubjectId]


class WireSelectedSupportRow(TypedDict):
    key: Required[WireIdentifier]
    record: Required[dict[str, WireJsonValue]]
    relation: Required[WireIdentifier]


class WireSelectedSupportPage(TypedDict):
    after: Required[WireIdentifier | None]
    complete: Required[bool]
    records: Required[list[WireSelectedSupportRow]]


class WireResultProduct(TypedDict):
    analyzed_scope: Required[WireJsonValue]
    body: NotRequired[WireSemanticValue]
    body_state: Required[Literal["not_requested", "present"]]
    kind_contract: Required[WireKindContract]
    member_id: Required[WireMemberId | None]
    multiplicity: Required[WirePositiveInteger]
    original_source: Required[WireOriginalSourceId]
    position: Required[WireNonnegativeInteger]
    product_id: Required[WireProductId]
    role: Required[WireIdentifier]
    subject: Required[WireSubjectId]


class WireResultBinding(TypedDict):
    execution_profile: Required[WireIdentifier]
    inference: Required[WireIdentifier]
    inputs: Required[list[WireInputMember]]
    parameters: Required[WireTaggedMapping]
    populations: Required[list[WirePopulationReference]]
    read_id: Required[WireReadIdentity]
    request_inputs: Required[WireTaggedMapping]
    support: Required[list[WireSupportMember]]


class WireReasonSelection(TypedDict):
    reasons: NotRequired[list[WireBindingReason]]


class WireResultUse(TypedDict):
    completion_state: Required[Literal["success", "empty", "failed"] | None]
    derivation_id: Required[WireDerivationId | None]
    fate: Required[WireVisibleFate]
    generation: Required[WireGeneration | None]
    historical_fate: Required[WireHistoricalFate]
    obligation_id: Required[WireObligationId]
    products: Required[list[WireResultProduct]]
    rebind_derivation: NotRequired[WireIdentifier | None]
    request_id: Required[WireRequestId | None]
    selection: Required[WireBinding | WireResultBinding | WireReasonSelection]
    semantic_outcome: Required[WireIdentifier | None]
    trust_snapshot: Required[WireTrustSnapshot]
    use_id: Required[WireIdentifier]


class WireReadDemandResultResult(TypedDict):
    attempt_failures: NotRequired[list[WireAttemptFailureObservation]]
    continuation: Required[WireContinuation | None]
    demand_id: Required[WireDemandId]
    frontier_at: Required[WireFrontierAt]
    intent: Required[WireDemandIntent]
    obligations: Required[list[WireResultObligation]]
    original_source_admissions: NotRequired[list[WireAdmitOriginalSourceViewResult]]
    populations: Required[list[WirePopulation]]
    project_id: Required[WireProjectId]
    read_id: Required[WireReadIdentity]
    read_snapshot: Required[WireReadSnapshot]
    release_id: Required[ReleaseId]
    root: Required[list[WireRootSubject]]
    runtime_id: Required[WireRuntimeId]
    scope: NotRequired[WireDemandReadScope]
    selection: Required[WireDemandIntent]
    state: NotRequired[Literal["active", "cancelled"]]
    support_page: NotRequired[WireSelectedSupportPage | None]
    trust_snapshot: Required[WireTrustSnapshot]
    uses: Required[list[WireResultUse]]
    view: Required[Literal["frontier", "products", "support"]]


class WireReadExternalDataPacketRequest(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    max_bytes: Required[WirePositiveInteger]
    packet_id: Required[WireExternalPacketId]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireReadExternalDataPacketResult(TypedDict):
    packet: Required[WireJsonValue]
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]


class WireReadExternalDataQueueRequest(TypedDict):
    demand_id: NotRequired[WireDemandId]
    limit: NotRequired[int]
    project_id: Required[WireProjectId]


class WireReadExternalDataQueueResult(TypedDict):
    packets: Required[list[WireExternalPacketHead]]


class WireRecordDataFateRequest(TypedDict):
    derivation_id: NotRequired[WireDerivationId | None]
    fate: Required[WireFate]
    generation: NotRequired[WireGeneration | None]
    obligation_id: Required[WireObligationId]
    request_id: NotRequired[WireRequestId | None]
    selection: Required[WireReasonSelection]
    trust_snapshot: NotRequired[WireTrustSnapshot]


class WireRecordDataFateResult(TypedDict):
    fate: Required[WireFate]
    use_id: Required[WireIdentifier]


class WireRegisterDataDemandRequest(TypedDict):
    project_id: Required[WireProjectId]
    release_id: Required[ReleaseId]
    root: Required[list[WireRootSubject]]
    runtime_id: Required[WireRuntimeId]
    selection: Required[WireDemandIntent]
    strength: Required[Literal["value", "episode", "independent"]]


class WireRegisterDataDemandResult(TypedDict):
    demand_id: Required[WireDemandId]
    selection: Required[WireDemandIntent]
    state: NotRequired[Literal["active", "cancelled"]]


class WireReleaseDataAttemptRequest(TypedDict):
    attempt: Required[WireAttempt]
    failure: Required[WireAttemptFailure]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    physical_retirement: Required[Literal["confirmed"]]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireReleaseDataAttemptResultVariant2(TypedDict):
    attempt: Required[WireAttempt]
    failure_id: Required[WireFailureId]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    replayed: Required[bool]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    state: Required[Literal["released"]]
    task_id: Required[WireTaskIdentity]


class WireReleaseExternalDataPacketRequest(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    packet_id: Required[WireExternalPacketId]
    reason: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireReleaseExternalDataPacketResult(TypedDict):
    packet_id: Required[WireExternalPacketId]
    released: Required[Literal[True]]
    state: Required[Literal["awaiting-external"]]


class WireRenewDataRequestRequest(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_seconds: Required[int]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


class WireRenewedDataRequestResult(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_until: Required[str]
    request_id: Required[WireRequestId]
    state: Required[Literal["renewed"]]
    task_id: Required[WireTaskIdentity]
    trust_snapshot: Required[WireTrustSnapshot]


class WireRetainDataCompletionIntentRequest(TypedDict):
    attempt: Required[WireAttempt]
    completion: Required[WireCompletion]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    runtime_id: Required[WireRuntimeId]
    task_id: Required[WireTaskIdentity]


class WireRetainDataCompletionIntentResult(TypedDict):
    intent_id: Required[WireCompletionIntentId]
    payload_digest: Required[WireIdentifier]


class WireRetainExternalDataPacketRequest(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    max_bytes: Required[WirePositiveInteger]
    request_id: Required[WireRequestId]
    runtime_id: Required[WireRuntimeId]
    task_id: Required[WireTaskIdentity]


class WireRetainExternalDataPacketResult(TypedDict):
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]
    state: Required[Literal["awaiting-external"]]


class WireRevokeDataSupportRequest(TypedDict):
    original_source: Required[WireOriginalSourceId]
    project_id: Required[WireProjectId]
    reason: Required[WireIdentifier]
    selector: Required[WireIdentifier]
    selector_kind: Required[
        Literal[
            "derivation", "recipe", "runtime", "product", "original-source", "original-admission"
        ]
    ]


class WireRevokeDataSupportResult(TypedDict):
    epoch: Required[WireNonnegativeInteger]
    revocation_id: Required[WireIdentifier]
    scope: Required[WireIdentifier]


class WireSelectDataPopulationRequest(TypedDict):
    obligation_id: Required[WireObligationId]
    parent_population_id: Required[WireIdentifier]
    population_name: Required[WireIdentifier]
    read_id: Required[WireReadIdentity]


class WireAttemptFence(TypedDict):
    attempt: Required[WireAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    task_id: Required[WireTaskIdentity]


type WireDdoJsonValue = (
    bool
    | int
    | int
    | float
    | Decimal
    | str
    | list[WireDdoJsonValue]
    | dict[str, WireDdoJsonValue]
    | None
)

type WireJsonValue = WireExactJSONValue

type WireIdentifier = str

type WirePositiveInteger = int

type WireNonnegativeInteger = int

type WireTaggedMapping = list[Literal["mapping"] | list[list[str | WireSemanticValue]]]

type WireSemanticValue = (
    list[Literal["null", "known-absent", "unknown", "unavailable"]]
    | list[Literal["boolean"] | bool]
    | list[Literal["string", "date", "datetime", "float"] | str]
    | list[Literal["integer"] | str]
    | list[Literal["decimal"] | str]
    | list[Literal["present"] | WireSemanticValue]
    | list[Literal["sequence", "ordered-bag", "bag", "set"] | list[WireSemanticValue]]
    | WireTaggedMapping
)

type WireEndpoint = WireEndpointVariant1 | WireEndpointVariant2

type WireSupportMember = (
    WireComputationalSupportMember | WireOriginalSourceSupportMember | WireAuthoredFactSupportMember
)

type WireTrustSnapshot = dict[str, WireNonnegativeInteger]

type WireTaskId = WireTaskIdentity

type WireRequestMeaning = (
    WireSemanticValue
    | list[Literal["ddo"] | Literal["semantic-request"] | Literal["1"] | WireSemanticValue]
)

type WireText = str

type WireClaimDataRequestResult = (
    WireClaimDataRequestResultVariant1 | WireClaimDataRequestResultVariant2
)

type WireParameterMap = dict[str, WireJsonValue]

type WireFrontierAt = str

type WireReadSnapshot = WireReadSnapshotIdentity

type WireOriginalSourceSelection = (
    WireOriginalNativeSelection | WireOriginalDocumentSelection | WireAuthoredFactSelection
)

type WireDataTaskState = Literal["pending", "running", "done", "empty", "failed", "cancelled"]

type WireFate = Literal[
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
]

type WireHistoricalFate = Literal[
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
    "attached",
    "fulfilled",
]

type WireInspectDataCompletionResult = (
    WireInspectDataCompletionResultVariant1
    | WireInspectDataCompletionResultVariant2
    | WireInspectDataCompletionResultVariant3
    | WireInspectDataCompletionResultVariant4
)

type WireOriginalSupportReference = (
    WireOriginalDocumentRef | WireExternalSourceRef | WireAuthoredFactRef
)

type WireVisibleFate = Literal[
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-external",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
    "attached",
    "fulfilled",
    "waiting",
]

type WireReadId = WireReadIdentity

type WireReleaseDataAttemptResult = WireDataAttemptLostResult | WireReleaseDataAttemptResultVariant2

type WireRenewDataRequestResult = WireRenewedDataRequestResult | WireDataAttemptLostResult


def wire_attempt_fence(value: Mapping[str, Any]) -> WireAttemptFence:
    return {
        "attempt": value["attempt"],
        "generation": value["generation"],
        "holder": value["holder"],
        "request_id": value["request_id"],
        "task_id": value["task_id"],
    }


class DataOperationCalls:
    def _invoke(self, name: str, payload: Any) -> Any:
        raise NotImplementedError

    def admit_authored_data(
        self, payload: WireAdmitAuthoredDataRequest
    ) -> WireAdmitOriginalSourceViewResult:
        return cast(WireAdmitOriginalSourceViewResult, self._invoke("admit_authored_data", payload))

    def inspect_data_execution(
        self, payload: WireInspectDataExecutionRequest
    ) -> WireInspectDataExecutionResult:
        return cast(WireInspectDataExecutionResult, self._invoke("inspect_data_execution", payload))

    def admit_original_document_asset(
        self, payload: WireAdmitOriginalDocumentAssetRequest
    ) -> WireAdmitOriginalSourceViewResult:
        return cast(
            WireAdmitOriginalSourceViewResult,
            self._invoke("admit_original_document_asset", payload),
        )

    def admit_original_source_view(
        self, payload: WireAdmitOriginalSourceViewRequest
    ) -> WireAdmitOriginalSourceViewResult:
        return cast(
            WireAdmitOriginalSourceViewResult, self._invoke("admit_original_source_view", payload)
        )

    def register_data_demand(
        self, payload: WireRegisterDataDemandRequest
    ) -> WireRegisterDataDemandResult:
        return cast(WireRegisterDataDemandResult, self._invoke("register_data_demand", payload))

    def cancel_data_demand(
        self, payload: WireCancelDataDemandRequest
    ) -> WireCancelDataDemandResult:
        return cast(WireCancelDataDemandResult, self._invoke("cancel_data_demand", payload))

    def expand_data_obligation(
        self, payload: WireExpandDataObligationRequest
    ) -> WireExpandDataObligationResult:
        return cast(WireExpandDataObligationResult, self._invoke("expand_data_obligation", payload))

    def record_data_fate(self, payload: WireRecordDataFateRequest) -> WireRecordDataFateResult:
        return cast(WireRecordDataFateResult, self._invoke("record_data_fate", payload))

    def select_data_population(
        self, payload: WireSelectDataPopulationRequest
    ) -> WireCloseDataPopulationResult:
        return cast(WireCloseDataPopulationResult, self._invoke("select_data_population", payload))

    def close_data_population(
        self, payload: WireCloseDataPopulationRequest
    ) -> WireCloseDataPopulationResult:
        return cast(WireCloseDataPopulationResult, self._invoke("close_data_population", payload))

    def attach_data_request(
        self, payload: WireAttachDataRequestRequest
    ) -> WireAttachDataRequestResult:
        return cast(WireAttachDataRequestResult, self._invoke("attach_data_request", payload))

    def claim_data_request(
        self, payload: WireClaimDataRequestRequest
    ) -> WireClaimDataRequestResult:
        return cast(WireClaimDataRequestResult, self._invoke("claim_data_request", payload))

    def renew_data_request(
        self, payload: WireRenewDataRequestRequest
    ) -> WireRenewDataRequestResult:
        return cast(WireRenewDataRequestResult, self._invoke("renew_data_request", payload))

    def release_data_attempt(
        self, payload: WireReleaseDataAttemptRequest
    ) -> WireReleaseDataAttemptResult:
        return cast(WireReleaseDataAttemptResult, self._invoke("release_data_attempt", payload))

    def retain_data_completion_intent(
        self, payload: WireRetainDataCompletionIntentRequest
    ) -> WireRetainDataCompletionIntentResult:
        return cast(
            WireRetainDataCompletionIntentResult,
            self._invoke("retain_data_completion_intent", payload),
        )

    def adopt_data_completion_intent(
        self, payload: WireAdoptDataCompletionIntentRequest
    ) -> WireAdoptDataCompletionIntentResult:
        return cast(
            WireAdoptDataCompletionIntentResult,
            self._invoke("adopt_data_completion_intent", payload),
        )

    def publish_data_derivation(
        self, payload: WirePublishDataDerivationRequest
    ) -> WirePublishDataDerivationResult:
        return cast(
            WirePublishDataDerivationResult, self._invoke("publish_data_derivation", payload)
        )

    def inspect_data_completion(
        self, payload: WireInspectDataCompletionRequest
    ) -> WireInspectDataCompletionResult:
        return cast(
            WireInspectDataCompletionResult, self._invoke("inspect_data_completion", payload)
        )

    def revoke_data_support(
        self, payload: WireRevokeDataSupportRequest
    ) -> WireRevokeDataSupportResult:
        return cast(WireRevokeDataSupportResult, self._invoke("revoke_data_support", payload))

    def read_demand_result(
        self, payload: WireReadDemandResultRequest
    ) -> WireReadDemandResultResult:
        return cast(WireReadDemandResultResult, self._invoke("read_demand_result", payload))

    def retain_external_data_packet(
        self, payload: WireRetainExternalDataPacketRequest
    ) -> WireRetainExternalDataPacketResult:
        return cast(
            WireRetainExternalDataPacketResult, self._invoke("retain_external_data_packet", payload)
        )

    def read_external_data_queue(
        self, payload: WireReadExternalDataQueueRequest
    ) -> WireReadExternalDataQueueResult:
        return cast(
            WireReadExternalDataQueueResult, self._invoke("read_external_data_queue", payload)
        )

    def read_external_data_packet(
        self, payload: WireReadExternalDataPacketRequest
    ) -> WireReadExternalDataPacketResult:
        return cast(
            WireReadExternalDataPacketResult, self._invoke("read_external_data_packet", payload)
        )

    def admit_external_data_result(
        self, payload: WireAdmitExternalDataResultRequest
    ) -> WireAdmitExternalDataResultResult:
        return cast(
            WireAdmitExternalDataResultResult, self._invoke("admit_external_data_result", payload)
        )

    def inspect_external_data_result(
        self, payload: WireInspectExternalDataResultRequest
    ) -> WireInspectExternalDataResultResult:
        return cast(
            WireInspectExternalDataResultResult,
            self._invoke("inspect_external_data_result", payload),
        )

    def release_external_data_packet(
        self, payload: WireReleaseExternalDataPacketRequest
    ) -> WireReleaseExternalDataPacketResult:
        return cast(
            WireReleaseExternalDataPacketResult,
            self._invoke("release_external_data_packet", payload),
        )

    def claim_external_data_packet(
        self, payload: WireClaimExternalDataPacketRequest
    ) -> WireClaimDataRequestResult:
        return cast(WireClaimDataRequestResult, self._invoke("claim_external_data_packet", payload))
