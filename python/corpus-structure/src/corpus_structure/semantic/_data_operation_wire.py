"""Generated closed native wire types and fixed call facade; do not edit."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Literal, NewType, NotRequired, Required, TypedDict, cast

from corpus_structure.semantic.data_operation_json import ContextualJsonValue
from corpus_structure.semantic.identifiers import (
    ProjectId,
    ReleaseId,
    RuntimeId,
    TaskAttempt,
    TaskId,
)

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
WirePublicationReceiptId = NewType("WirePublicationReceiptId", str)
WireReadIdentity = NewType("WireReadIdentity", str)
WireReadSnapshotIdentity = NewType("WireReadSnapshotIdentity", str)
WireRequestId = NewType("WireRequestId", str)
WireSubjectId = NewType("WireSubjectId", str)
WireUseIdentity = NewType("WireUseIdentity", str)


class WireAuthoredFactRef(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    author: Required[str]
    kind: Required[Literal["authored-fact"]]
    kind_contract: Required[WireKindContract]
    meaning_body: Required[WireJsonValue]
    original_source: Required[WireOriginalSourceId | None]
    project_id: Required[ProjectId]
    selection_id: Required[str]
    subject: Required[WireSubjectId]
    subject_definition: Required[str]


class WireCPUExecutionReceipt(TypedDict):
    main_thread: Required[bool]
    native_pools_json: Required[str]
    native_thread_limit: Required[int | None]
    pid: Required[int]
    request_digest: Required[str]
    result_digest: Required[str]


class WireExternalExecutionReceipt(TypedDict):
    actor_assertion: Required[str]
    admitting_principal: Required[str]
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[str]
    model_assertion: Required[str | None]
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]
    receipt_id: Required[WirePublicationReceiptId]
    request_id: Required[WireRequestId]
    result_digest: Required[str]
    runtime_id: Required[RuntimeId]
    task_id: Required[TaskId]
    version: Required[Literal["external-execution-receipt-v1"]]


class WireLogicalProviderMember(TypedDict):
    attempt: Required[TaskAttempt]
    count: Required[int]
    generation: Required[WireGeneration]
    input_digest: Required[str]
    member: Required[str]
    request_id: Required[WireRequestId]
    start: Required[int]
    task_id: Required[TaskId]


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
    project_id: Required[ProjectId]


class WirePdfPublicationCertification(TypedDict):
    attested_logical_digest: Required[str]
    basis: Required[Literal["producer-certified", "round-trip-verified"]]
    lowering_identity: Required[str]
    native_document_digest: Required[str]
    oracle_receipt_id: Required[str]


class WirePdfSpoolContributorReceipt(TypedDict):
    adopter_attempt: Required[int]
    adopter_holder: Required[str]
    manifest_digest: Required[str]
    producer_attempt: Required[int]
    producer_holder: Required[str]
    producer_id: Required[str]
    runtime_id: Required[str]
    runtime_manifest_digest: Required[str]
    selection_digest: Required[str]
    task_id: Required[int]


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
    task_id: Required[TaskId]


class WirePdfExecutionReceipt(TypedDict):
    certification: Required[WirePdfPublicationCertification]
    contributors: Required[list[WirePdfSpoolContributorReceipt]]
    publication: Required[WirePublishedPdfDocumentRef]
    publisher_attempt: Required[int]
    publisher_holder: Required[str]


class WirePdfObservationPublicationContext(TypedDict):
    attempt: Required[int]
    generation: Required[int]
    holder: Required[str]
    release_id: Required[str]
    request_id: Required[str]
    runtime_id: Required[str]
    source_digest: Required[str]
    task_id: Required[int]
    version: Required[Literal["pdf-observation-publication-1"]]


class WirePdfObservedRequest(TypedDict):
    content_digest: Required[str]
    ordinal: Required[int]
    product_key: Required[str]
    publication_context: Required[WirePdfObservationPublicationContext]
    task_id: Required[int]


class WirePdfObservedPage(TypedDict):
    adapter_reused: Required[bool]
    observations: Required[list[WirePdfObservedRequest]]
    page_no: Required[int]
    recipe_digest: Required[str]
    report_digest: Required[str]


class WirePdfObservationExecutionReceipt(TypedDict):
    attempt: Required[int]
    generation: Required[int]
    holder: Required[str]
    pages: Required[list[WirePdfObservedPage]]
    recipe_digest: Required[str]
    request_id: Required[str]
    runtime_id: Required[str]
    source_digest: Required[str]
    task_id: Required[int]
    version: Required[Literal["pdf-observation-execution-1"]]


class WireProviderExecutionReceipt(TypedDict):
    cohort_digest: Required[str]
    cohort_members: Required[list[str]]
    correlation: Required[str]
    logical_members: Required[list[WireLogicalProviderMember]]
    member_count: Required[int]
    member_offset: Required[int]
    native_member_digests: Required[list[str]]
    physical: Required[list[WireNativeExecutionReceipt]]
    work_members: Required[list[list[str | int]]]


class WireRuleAttestation(TypedDict):
    output_position: Required[int]
    output_role: Required[str]
    partition_key: Required[str | None]
    premise: Required[str]
    rule_fingerprint: Required[str]
    rule_id: Required[str]


class WireAuthoredFactSelector(TypedDict):
    scope: Required[Literal["authored-fact"]]


class WireAdmitAuthoredDataRequest(TypedDict):
    demand_id: Required[WireDemandId]
    reference: Required[WireAuthoredFactRef]
    selection_name: Required[WireIdentifier]
    selectors: Required[list[WireAuthoredFactSelector]]


class WireNativeExecutionEvidence(TypedDict):
    attempt: Required[TaskAttempt]
    cpu_receipts: Required[list[WireCPUExecutionReceipt]]
    cpu_replies: NotRequired[list[str]]
    external_receipts: NotRequired[list[WireExternalExecutionReceipt]]
    generation: Required[WireGeneration]
    holder: Required[str]
    host_receipts: Required[list[WireNativeExecutionReceipt]]
    pdf_observation_receipts: NotRequired[list[WirePdfObservationExecutionReceipt]]
    pdf_receipts: NotRequired[list[WirePdfExecutionReceipt]]
    provider_receipts: NotRequired[list[WireProviderExecutionReceipt]]
    request_id: Required[WireRequestId]
    rule_attestations: NotRequired[list[WireRuleAttestation]]
    runtime_id: Required[RuntimeId]
    task_id: Required[TaskId]
    version: Required[Literal["native-execution-evidence-v1"]]


class WireProducerOutputOccurrence(TypedDict):
    member_id: Required[WireIdentifier | None]
    multiplicity: Required[int]
    position: Required[int]
    role: Required[WireIdentifier]


class WireInputMember(TypedDict):
    member_id: NotRequired[WireMemberId | None]
    multiplicity: Required[WirePositiveInteger]
    position: Required[WireNonnegativeInteger]
    producer_output: Required[WireProducerOutputOccurrence | None]
    product_id: Required[WireProductId]
    role: Required[WireIdentifier]
    support_derivation_ids: Required[list[WireIdentifier]]


class WireMemberContext(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    original_source: Required[WireIdentifier | None]
    subject: Required[WireIdentifier]
    subject_definition: Required[WireIdentifier]


class WireProductMember(TypedDict):
    body: Required[WireSemanticValue]
    context: Required[WireMemberContext]
    kind_contract: Required[WireKindContract]
    member_id: Required[WireMemberId]


class WireProductPartitionPlacement(TypedDict):
    end: Required[WireNonnegativeInteger]
    start: Required[WireNonnegativeInteger]


class WireProductPartition(TypedDict):
    body: Required[WireSemanticValue]
    collection: Required[WireIdentifier]
    ordinal: Required[WireNonnegativeInteger]
    partition_digest: Required[WireIdentifier]
    partition_key: Required[WireIdentifier]
    placement: Required[WireProductPartitionPlacement]


class WireProduct(TypedDict):
    artifact_digest: NotRequired[WireIdentifier | None]
    body: Required[WireSemanticValue]
    kind_contract: Required[WireKindContract]
    members: Required[list[WireProductMember]]
    partitions: NotRequired[list[WireProductPartition]]


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
    attempt: Required[TaskAttempt]
    completion: Required[WireCompletion]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    model_assertion: Required[WireIdentifier | None]
    packet_id: Required[WireExternalPacketId]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


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


class WireAdoptDataCompletionIntentRequest(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    intent_id: Required[WireCompletionIntentId]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


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
    binding: Required[WireBinding]
    binding_demand_id: Required[WireIdentifier]
    binding_obligation_id: Required[WireIdentifier]
    derivation_id: Required[WireDerivationId | None]
    fate: Required[Literal["attached", "fulfilled"]]
    generation: Required[WireGeneration]
    release_id: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    runtime_id: Required[WireIdentifier]
    task_id: Required[TaskId | None]
    trust_snapshot: Required[WireTrustSnapshot]
    use_id: Required[WireIdentifier]


class WireAttachDataRequestsAttachedResult(TypedDict):
    action: Required[Literal["compute", "reconcile", "reuse"]]
    binding: Required[WireBinding]
    binding_demand_id: Required[WireIdentifier]
    binding_obligation_id: Required[WireIdentifier]
    derivation_id: Required[WireDerivationId | None]
    fate: Required[Literal["attached"]]
    generation: Required[WireGeneration]
    release_id: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    runtime_id: Required[WireIdentifier]
    task_id: Required[TaskId | None]
    trust_snapshot: Required[WireTrustSnapshot]
    use_id: Required[WireIdentifier]


class WireAttachDataRequestsFulfilledResult(TypedDict):
    action: Required[Literal["compute", "reconcile", "reuse"]]
    binding: Required[WireBinding]
    binding_demand_id: Required[WireIdentifier]
    binding_obligation_id: Required[WireIdentifier]
    derivation_id: Required[WireDerivationId | None]
    fate: Required[Literal["fulfilled"]]
    generation: Required[WireGeneration]
    release_id: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    runtime_id: Required[WireIdentifier]
    task_id: Required[TaskId | None]
    trust_snapshot: Required[WireTrustSnapshot]
    use_id: Required[WireIdentifier]


class WireAttachDataRequestsItem(TypedDict):
    binding: Required[WireBinding]
    obligation_id: Required[WireObligationId]
    rebind_derivation: NotRequired[WireIdentifier]
    replicate: Required[WireIdentifier | None]
    request_key: NotRequired[WireIdentifier]
    request_meaning: Required[WireRequestMeaning]


class WireAttachDataRequestsRequest(TypedDict):
    items: Required[list[WireAttachDataRequestsItem]]
    read_id: Required[WireReadIdentity]


class WireAttachDataRequestsResultItemsItemVariant1(TypedDict):
    result: Required[WireAttachDataRequestsAttachedResult]
    state: Required[Literal["attached"]]


class WireAttachDataRequestsResultItemsItemVariant2(TypedDict):
    result: Required[WireAttachDataRequestsFulfilledResult]
    state: Required[Literal["fulfilled"]]


class WireAttachDataRequestsResultItemsItemVariant3(TypedDict):
    reason: Required[str]
    sqlstate: Required[str]
    state: Required[Literal["refused"]]


class WireAttachDataRequestsResult(TypedDict):
    items: Required[
        list[
            WireAttachDataRequestsResultItemsItemVariant1
            | WireAttachDataRequestsResultItemsItemVariant2
            | WireAttachDataRequestsResultItemsItemVariant3
        ]
    ]


class WireD1LimitationBatchReceiptHeader(TypedDict):
    profile: Required[str]
    provider: Required[Literal["d1"]]
    runtime: Required[str]


class WireD1LimitationBatchReceipt(TypedDict):
    digest: Required[str]
    header: Required[WireD1LimitationBatchReceiptHeader]
    member_ordinal: Required[int]
    members: Required[list[str]]
    version: Required[Literal[2]]


class WireD1LimitationReplyVariant1(TypedDict):
    batch_receipt: Required[WireD1LimitationBatchReceipt]
    limit: Required[Literal[16]]
    outcome: Required[Literal["limited"]]
    reason: Required[Literal["question_count"]]


class WireD1LimitationReplyVariant2(TypedDict):
    batch_receipt: Required[WireD1LimitationBatchReceipt]
    limit: Required[Literal[4096]]
    outcome: Required[Literal["limited"]]
    reason: Required[Literal["packed_row_tokens"]]
    row_tokens: Required[list[int]]


class WireD1LimitationSourcePin(TypedDict):
    analyzed_scope_meaning: Required[WireIdentifier]
    document: Required[WireIdentifier]
    format: Required[Literal["declared-native-source-v1"]]
    kind_contract: Required[WireIdentifier]
    membership: Required[WireIdentifier]
    original_source: Required[WireIdentifier]
    project_id: Required[WireIdentifier]
    projection_digest: Required[str]
    section_pointer: Required[str]
    source: Required[WireIdentifier]
    source_member: NotRequired[WireIdentifier]
    source_product: Required[WireIdentifier]
    subject: Required[WireIdentifier]
    subject_definition: Required[WireIdentifier]


class WireD1KnownLimitation(TypedDict):
    emitted_count: Required[Literal[0]]
    execution_evidence: Required[WireNativeExecutionEvidence]
    family: Required[WireIdentifier]
    inspected_count: Required[Literal[0]]
    native_reply: Required[WireD1LimitationReply]
    profile_digest: Required[str]
    request_digest: Required[str]
    request_json: Required[str]
    source_pin: Required[WireD1LimitationSourcePin]
    stage: Required[int]
    standing: Required[Literal["unperformed-question-inspection"]]
    version: Required[Literal["d1-known-limitation-v1"]]


class WireAttemptFailure(TypedDict):
    code: Required[WireIdentifier]
    d1_limitation: NotRequired[WireD1KnownLimitation]
    message: Required[WireIdentifier]


class WireAttemptFailureObservationFailureVariant2(TypedDict):
    code: Required[WireIdentifier]
    d1_limitation_disclosure: Required[Literal["undisclosed"]]
    message: Required[WireIdentifier]


class WireAttemptFailureObservation(TypedDict):
    attempt: Required[TaskAttempt]
    failure: Required[WireAttemptFailure | WireAttemptFailureObservationFailureVariant2]
    failure_id: Required[WireFailureId]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


class WireAuthoredFactSelection(TypedDict):
    reference: Required[WireAuthoredFactRef]
    selectors: Required[list[WireAuthoredFactSelector]]


class WireAuthoritySelection(TypedDict):
    kind: Required[Literal["native-authority"]]
    protected_dependencies: Required[Literal["undisclosed"]]


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
    task_id: Required[TaskId | None]


class WireCancelDataDemandResult(TypedDict):
    demand_id: Required[WireDemandId]
    reason: Required[WireIdentifier]
    requests: Required[list[WireCancelDataDemandResultRequestsItem]]
    state: Required[Literal["cancelled"]]


class WireClaimDataRequestRequest(TypedDict):
    external_packet_id: NotRequired[WireExternalPacketId]
    generation: Required[WirePositiveInteger]
    holder: Required[WireIdentifier]
    lease_seconds: Required[int]
    request_id: Required[WireRequestId]


class WireClaimDataRequestResultVariant1(TypedDict):
    state: Required[Literal["no-work"]]


class WireClaimDataRequestResultVariant2(TypedDict):
    action: Required[Literal["compute", "reconcile"]]
    attempt: Required[TaskAttempt]
    binding: Required[WireBinding]
    binding_demand_id: Required[WireIdentifier]
    binding_obligation_id: Required[WireIdentifier]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_until: Required[str]
    release_id: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    runtime_id: Required[WireIdentifier]
    state: Required[Literal["claimed"]]
    task_id: Required[TaskId]
    trust_snapshot: Required[WireTrustSnapshot]


class WireClaimDataRequestsClaimedResult(TypedDict):
    action: Required[Literal["compute", "reconcile"]]
    attempt: Required[TaskAttempt]
    binding: Required[WireBinding]
    binding_demand_id: Required[WireIdentifier]
    binding_obligation_id: Required[WireIdentifier]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_until: Required[str]
    release_id: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    runtime_id: Required[WireIdentifier]
    state: Required[Literal["claimed"]]
    task_id: Required[TaskId]
    trust_snapshot: Required[WireTrustSnapshot]


class WireClaimDataRequestsItem(TypedDict):
    external_packet_id: NotRequired[WireExternalPacketId]
    generation: Required[WirePositiveInteger]
    request_id: Required[WireRequestId]


class WireClaimDataRequestsRequest(TypedDict):
    holder: Required[WireIdentifier]
    items: Required[list[WireClaimDataRequestsItem]]
    lease_seconds: Required[int]


class WireClaimDataRequestsResultItemsItemVariant1(TypedDict):
    state: Required[Literal["no-work"]]


class WireClaimDataRequestsResultItemsItemVariant2(TypedDict):
    result: Required[WireClaimDataRequestsClaimedResult]
    state: Required[Literal["claimed"]]


class WireClaimDataRequestsResultItemsItemVariant3(TypedDict):
    reason: Required[str]
    sqlstate: Required[str]
    state: Required[Literal["refused"]]


class WireClaimDataRequestsResult(TypedDict):
    items: Required[
        list[
            WireClaimDataRequestsResultItemsItemVariant1
            | WireClaimDataRequestsResultItemsItemVariant2
            | WireClaimDataRequestsResultItemsItemVariant3
        ]
    ]


class WireClaimExternalDataPacketRequest(TypedDict):
    demand_id: NotRequired[WireDemandId]
    holder: Required[WireIdentifier]
    lease_seconds: Required[int]
    packet_id: Required[WireExternalPacketId]
    project_id: Required[ProjectId]


class WireCloseDataPopulationRequest(TypedDict):
    demand_id: Required[WireDemandId]
    derivation_id: Required[WireDerivationId]
    member_role: Required[WireIdentifier]
    name: Required[WireIdentifier]
    product_id: Required[WireProductId]


class WirePopulationProducerContext(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId | None]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WirePopulationSelectionEvidence(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    choices: Required[WireParameterMap]
    definition: Required[WireIdentifier]
    eligibility: Required[WireIdentifier]
    filter: Required[WireJsonValue]
    obligation_id: Required[WireObligationId]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId | None]
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
    analyzed_scope: Required[ContextualJsonValue]
    member_id: Required[WireMemberId]
    original_source: Required[WireOriginalSourceId | None]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WireCloseDataPopulationResult(TypedDict):
    complete: Required[bool]
    evidence: Required[WirePopulationEvidence]
    inserted_obligations: Required[int]
    members: Required[list[WirePopulationMember]]
    name: Required[WireIdentifier]
    population_id: Required[WirePopulationId]
    semantic_key: Required[WireIdentifier]


class WireConsumeDataCompletionDraftRequest(TypedDict):
    attempt: Required[WirePositiveInteger]
    completion: Required[WireCompletion]
    draft_id: Required[WireIdentifier]
    generation: Required[WirePositiveInteger]
    holder: Required[WireIdentifier]
    origin_id: Required[WireIdentifier]
    request_id: Required[WireIdentifier]
    task_id: Required[WireTaskId]


class WireDemandReadScope(TypedDict):
    operation_id: NotRequired[WireOperationId]
    original_source: NotRequired[WireOriginalSourceId | None]
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


class WireOriginalDocumentSelection(TypedDict):
    reference: Required[WireOriginalDocumentRef]
    selectors: Required[list[WireOriginalDocumentSelector]]


class WireRootSubject(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    original_source: Required[WireOriginalSourceId | None]
    subject: Required[WireSubjectId]


class WireSelectedSourceSupport(TypedDict):
    admission_use_id: Required[WireIdentifier]
    derivation_id: Required[WireIdentifier]
    kind: Required[Literal["computation"]]


class WireSelectedSourceProof(TypedDict):
    anchor_use_id: Required[WireIdentifier]
    member_id: Required[WireIdentifier | None]
    output: Required[WireProducerOutputOccurrence]
    product_id: Required[WireIdentifier]
    support: Required[WireSelectedSourceSupport]


class WireSelectedSourceRead(TypedDict):
    cut_canonical_json: Required[WireIdentifier]
    cut_id: Required[WireIdentifier]
    demand_id: Required[WireIdentifier]
    project_id: Required[WireIdentifier]
    read_id: Required[WireIdentifier]
    release_id: Required[WireIdentifier]
    runtime_id: Required[WireIdentifier]


class WireSourceReadBasis(TypedDict):
    proofs: Required[list[WireSelectedSourceProof]]
    selection: Required[WireSelectedSourceRead]


class WireSourceSetAcquisitionVariant1(TypedDict):
    kind: Required[Literal["selected-support-v1"]]
    reads: Required[list[WireSourceReadBasis]]


class WireSourceSetAcquisitionVariant2(TypedDict):
    kind: Required[Literal["all-admissible-support-v1"]]


class WireSemanticSourceReference(TypedDict):
    member_id: NotRequired[WireMemberId]
    product_id: Required[WireProductId]


class WireSourceSetEntry(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    member: Required[WireIdentifier | None]
    original_source: Required[WireOriginalSourceId | None]
    product: Required[WireIdentifier]
    project_id: Required[ProjectId]
    reference: Required[WireSemanticSourceReference]
    source_reference: Required[WireIdentifier]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WireFrozenSourceSet(TypedDict):
    acquisition: Required[WireSourceSetAcquisition]
    entries: Required[list[WireSourceSetEntry]]


class WireDemandIntent(TypedDict):
    discovery: Required[list[WireDiscoverySelection]]
    execution_profile: Required[WireIdentifier]
    inference: Required[WireIdentifier]
    model: Required[str]
    operations: Required[list[WireSelectedOperation]]
    original_sources: NotRequired[dict[str, WireOriginalSourceSelection]]
    root_operations: Required[list[WireOperationId]]
    roots: Required[list[WireRootSubject]]
    source_sets: NotRequired[dict[str, WireFrozenSourceSet]]
    targets: Required[list[WireOperationId]]
    version: Required[Literal["data-demand-intent-v2"]]


class WirePublicDemandSelection(TypedDict):
    discovery: Required[list[WireDiscoverySelection]]
    intent_digest: Required[WireIdentifier]
    model: Required[str]
    root_operations: Required[list[WireIdentifier]]
    roots: Required[list[WireRootSubject]]
    targets: Required[list[WireIdentifier]]
    version: Required[Literal["data-demand-public-selection-v1"]]


class WireContinuation(TypedDict):
    after: Required[WireObligationId]
    demand_id: Required[WireDemandId]
    frontier_at: Required[WireFrontierAt]
    limit: Required[int]
    max_bytes: Required[int]
    read_id: Required[WireReadIdentity]
    read_snapshot: Required[WireReadSnapshot]
    scope: NotRequired[WireDemandReadScope]
    selection: Required[WireReadDemandSelection]
    support_after: NotRequired[WireIdentifier]
    trust_snapshot: Required[WireTrustSnapshot]
    view: Required[Literal["frontier", "products", "support"]]


class WireCutSelection(TypedDict):
    demand_id: Required[WireDemandId]
    frontier_at: Required[WireFrontierAt]
    project_id: Required[ProjectId]
    read_id: Required[WireReadIdentity]
    read_snapshot: Required[WireReadSnapshot]
    release_id: Required[ReleaseId]
    runtime_id: Required[RuntimeId]
    scope: Required[WireDemandReadScope]
    selection: Required[WireReadDemandSelection]
    trust_snapshot: Required[WireTrustSnapshot]


class WireDataAttemptLostResult(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    reason: Required[Literal["fence", "cancelled", "revoked", "support-unavailable"]]
    request_id: Required[WireRequestId]
    state: Required[Literal["lost"]]
    task_id: Required[TaskId]


class WirePdfSearchRecipeOrganizationOwner(TypedDict):
    content_digest: Required[WirePdfSearchDigest]
    product_key: Required[WireIdentifier]
    task_id: Required[WireTaskId]


class WirePdfSearchRecipe(TypedDict):
    analysis_eligible: Required[Literal[True]]
    organization_owner: Required[WirePdfSearchRecipeOrganizationOwner]
    policy_digest: Required[WirePdfSearchDigest]
    renderer: Required[WirePdfSearchDigest]
    version: Required[Literal["pdf-source-search-v1"]]


class WirePdfSearchOutcome(TypedDict):
    outcome: Required[WireIdentifier]
    pointer: Required[WireIdentifier]


class WirePdfSearchProjectionRowProjectionHealth(TypedDict):
    formula_outcomes: Required[list[WirePdfSearchOutcome]]


class WirePdfSearchPiece(TypedDict):
    cell_index: NotRequired[WireNonnegativeInteger]
    end: Required[WireNonnegativeInteger]
    item_ref: NotRequired[str]
    kind: Required[Literal["native_text", "synthetic_separator"]]
    source_field: NotRequired[str]
    start: Required[WireNonnegativeInteger]


class WirePdfSearchProjectionRowProjection(TypedDict):
    ancestors: Required[list[WireIdentifier]]
    health: Required[WirePdfSearchProjectionRowProjectionHealth]
    items: Required[list[WireIdentifier]]
    pieces: Required[list[WirePdfSearchPiece]]
    text: Required[str]


class WirePdfSearchProjectionRow(TypedDict):
    membership: Required[Literal["direct", "descendants"]]
    projection: Required[WirePdfSearchProjectionRowProjection]
    projection_digest: Required[WirePdfSearchDigest]
    section_pointer: Required[WireIdentifier]


class WireReadSelectedPdfSourceRequest(TypedDict):
    demand_id: Required[WireDemandId]
    derivation_id: Required[WireDerivationId]
    product_id: Required[WireProductId]
    project_id: Required[ProjectId]
    read_id: Required[WireReadIdentity]
    use_id: Required[WireUseIdentity]


class WireEnsurePdfSearchProjectionRequest(TypedDict):
    configuration: Required[Literal["english"]]
    fill_max_bytes: Required[int]
    recipe: Required[WirePdfSearchRecipe]
    rows: NotRequired[list[WirePdfSearchProjectionRow]]
    source: Required[WireReadSelectedPdfSourceRequest]


class WireEnsurePdfSearchProjectionResult(TypedDict):
    population_id: Required[WireIdentifier]
    row_count: Required[WireNonnegativeInteger]
    set_digest: Required[str | None]
    state: Required[Literal["missing", "ready"]]


class WireEstablishDataRuleProofRequest(TypedDict):
    demand_id: Required[WireIdentifier]
    derivation_id: Required[WireIdentifier]
    partition_key: NotRequired[WireIdentifier]
    product_id: Required[WireIdentifier]
    read_id: Required[WireReadId]
    rule_id: Required[WireIdentifier]
    target_partition_key: NotRequired[WireIdentifier]
    target_product_id: NotRequired[WireIdentifier]
    use_id: Required[WireIdentifier]


class WireEstablishDataRuleProofResult(TypedDict):
    established: Required[int]
    matched: Required[int]


class WireExternalPacketHead(TypedDict):
    generation: Required[WireGeneration]
    operation_id: Required[WireOperationId]
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]
    request_id: Required[WireRequestId]
    state: Required[Literal["awaiting-external"]]
    subject: Required[WireSubjectId]
    task_id: Required[TaskId]


class WireInitializeSourceProjectRequest(TypedDict):
    project_id: Required[ProjectId]
    release_id: Required[ReleaseId]


class WireInitializeSourceProjectResult(TypedDict):
    project_id: Required[ProjectId]
    release_id: Required[ReleaseId]


class WireRetainDataCompletionIntentRequest(TypedDict):
    attempt: Required[TaskAttempt]
    completion: Required[WireCompletion]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    runtime_id: Required[RuntimeId]
    task_id: Required[TaskId]


class WireInspectDataCompletionDraftRequest(TypedDict):
    draft_id: Required[str]
    origin_id: Required[WireIdentifier]
    producer: Required[WireRetainDataCompletionIntentRequest]
    project_id: Required[WireIdentifier]


class WireInspectDataCompletionDraftResult(TypedDict):
    failure_id: Required[str | None]
    intent_id: Required[str | None]
    reason: Required[Literal["retired", "unpublished", "retirement-unconfirmed"]]
    receipt_id: Required[str | None]
    state: Required[Literal["eligible", "retained"]]


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
    runtime_id: Required[RuntimeId]
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
    runtime_id: NotRequired[RuntimeId]


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


class WireInspectDataOperationReleaseRequest(TypedDict):
    release_id: Required[WireIdentifier]
    validity_only: NotRequired[bool]


class WireInspectDataOperationReleaseResult(TypedDict):
    conservative_operations: Required[list[WireIdentifier]]
    model_digest: Required[str]
    native_digest: Required[str]
    release_id: Required[WireIdentifier]


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


class WireReadinessIdentity(TypedDict):
    input: Required[WireInputMember]
    support: Required[list[WireSupportMember]]


class WireReadinessRole(TypedDict):
    identity: Required[WireReadinessIdentity | None]
    input_role: Required[WireIdentifier]
    state: Required[Literal["ready", "missing", "ambiguous", "invalid"]]


class WireObligationReadiness(TypedDict):
    ready: Required[bool]
    roles: Required[list[WireReadinessRole]]


class WireOperationEventFrameDeclaredProductRef(TypedDict):
    analyzed_scope_meaning: Required[str]
    kind_contract: Required[str]
    member_id: NotRequired[str | None]
    original_source: Required[str | None]
    product_id: Required[str]
    project_id: Required[str]
    subject: Required[str]
    subject_definition: Required[str]


class WireOperationEventFrameDeclaredStructuralSource(TypedDict):
    analyzed_scope_meaning: Required[str]
    document: Required[str]
    format: NotRequired[Literal["declared-native-source-v1"]]
    kind_contract: Required[str]
    membership: Required[Literal["direct", "descendants"]]
    original_source: Required[str]
    project_id: Required[str]
    projection_digest: Required[str]
    section_pointer: Required[str]
    source: Required[str]
    source_member: NotRequired[str | None]
    source_product: Required[str]
    subject: Required[str]
    subject_definition: Required[str]


class WireOperationEventFrameSelectedDefinitionEvent(TypedDict):
    component_id: Required[str]
    derivation_id: Required[str]
    origin_group: Required[str]
    producer_operation: Required[
        Literal[
            "structure.definition_components/declared",
            "structure.definition_declaration_components/declared",
            "structure.definition_named_components/declared",
        ]
    ]
    producer_revision: Required[str]
    report: Required[WireOperationEventFrameDeclaredProductRef]
    source: Required[WireOperationEventFrameDeclaredStructuralSource]
    use_id: Required[str]


class WireOperationEventFrameIndependentEventJudgment(TypedDict):
    facets: Required[dict[str, Literal["supported", "unsupported", "ambiguous", "unassessed"]]]
    judgment: Required[Literal["supported", "unsupported", "ambiguous", "unassessed"]]
    selection: Required[WireOperationEventFrameSelectedDefinitionEvent]


class WireOperationEventFrameSelectedReadReference(TypedDict):
    cut_canonical_json: Required[str]
    cut_id: Required[str]
    demand_id: Required[str]
    project_id: Required[str]
    read_id: Required[str]
    release_id: Required[str]
    runtime_id: Required[str]


class WireOperationEventFrameDdoOperationEventQuestion(TypedDict):
    author: Required[str]
    corpus_id: Required[str]
    event: Required[Literal["defined_by_correctness", "defining_text_attachment_correctness"]]
    exposure: NotRequired[Literal["output_first"]]
    judgments: Required[list[WireOperationEventFrameIndependentEventJudgment]]
    original_selection: Required[WireOperationEventFrameSelectedReadReference]
    partition: Required[Literal["development", "feature_fit"]]
    pass_kind: NotRequired[Literal["C"]]
    prediction_selection: Required[WireOperationEventFrameSelectedReadReference]
    reference_name: Required[str]
    rubric: Required[str]
    rubric_version: Required[str]
    version: NotRequired[Literal["selected-operation-event-question-1"]]


class WireOperationEventFrameSelectedEventFeatureUnavailable(TypedDict):
    event_id: Required[str]
    judgment: Required[Literal["supported", "unsupported", "ambiguous", "unassessed"]]
    reason: Required[Literal["missing_common_passage", "incomparable_endpoint_anchors"]]
    selection: Required[WireOperationEventFrameSelectedDefinitionEvent]


class WireOperationEventFrameSelectedEventObservation(TypedDict):
    event_id: Required[str]
    facets: Required[dict[str, Literal["supported", "unsupported", "ambiguous", "unassessed"]]]
    features: Required[list[int | float | Decimal]]
    judgment: Required[Literal["supported", "unsupported", "ambiguous", "unassessed"]]
    selection: Required[WireOperationEventFrameSelectedDefinitionEvent]


class WireOperationEventFrameSelectedOperationEventFrame(TypedDict):
    event_ids: Required[list[str]]
    event_version: Required[str]
    feature_names: Required[list[str]]
    feature_unavailable: Required[list[WireOperationEventFrameSelectedEventFeatureUnavailable]]
    observations: Required[list[WireOperationEventFrameSelectedEventObservation]]
    producer_version: Required[str]
    question: Required[WireOperationEventFrameDdoOperationEventQuestion]
    question_reference: Required[WireOperationEventFrameDeclaredProductRef]
    version: NotRequired[Literal["selected-operation-event-frame-1"]]


class WireOriginalSourceAdmissionResult(TypedDict):
    admission_id: Required[WireAdmissionId]
    analyzed_scope: Required[ContextualJsonValue]
    evidence: Required[WireJsonValue]
    kind_contract: Required[WireKindContract]
    original_source: Required[WireOriginalSourceId | None]
    product_id: Required[WireProductId]
    selection_name: Required[WireIdentifier]
    source_reference: Required[WireIdentifier]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]
    trust_snapshot: Required[WireTrustSnapshot]


class WirePdfSearchAfter(TypedDict):
    key: Required[str]
    score: Required[int | float | Decimal]
    selection: Required[WirePdfSearchDigest]


class WirePdfSearchBinding(TypedDict):
    demand_id: Required[WireIdentifier]
    max_bytes: Required[int]
    max_rows: Required[int]
    membership: Required[Literal["direct", "descendants"]]
    project_id: Required[WireIdentifier]
    read_id: Required[WireReadId]
    sections: Required[list[str]]
    sources: Required[list[WireReadSelectedPdfSourceRequest]]
    text: Required[str]
    version: Required[Literal[5]]


class WirePdfSearchHit(TypedDict):
    excerpt: Required[str]
    key: Required[str]
    membership: Required[Literal["direct", "descendants"]]
    projection_digest: Required[WirePdfSearchDigest]
    score: Required[int | float | Decimal]
    section_pointer: Required[WireIdentifier]
    source_index: Required[int]


class WirePdfSearchPin(TypedDict):
    recipe: Required[WirePdfSearchRecipe]
    source: Required[WireReadSelectedPdfSourceRequest]


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
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    intent_id: Required[WireCompletionIntentId]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]
    trust_snapshot: NotRequired[WireTrustSnapshot]


class WirePublishDataDerivationResult(TypedDict):
    derivation_id: Required[WireDerivationId]
    receipt_id: Required[WirePublicationReceiptId]
    replayed: Required[bool]
    trust_snapshot: Required[WireTrustSnapshot]


class WireRankPdfSearchProjectionRequest(TypedDict):
    after: NotRequired[WirePdfSearchAfter]
    binding: Required[WirePdfSearchBinding]
    cut_id: Required[WireIdentifier]
    limit: Required[int]
    sources: Required[list[WirePdfSearchPin]]


class WireRankPdfSearchProjectionResult(TypedDict):
    more: Required[bool]
    rows: Required[list[WirePdfSearchHit]]
    selection: Required[WirePdfSearchDigest]


class WireReadDemandResultRequest(TypedDict):
    after: NotRequired[WireObligationId]
    demand_id: Required[WireDemandId]
    frontier_at: NotRequired[WireFrontierAt]
    limit: NotRequired[int]
    max_bytes: NotRequired[int]
    obligation_id: NotRequired[WireObligationId]
    read_id: NotRequired[WireReadIdentity]
    read_snapshot: NotRequired[WireReadSnapshot]
    recheck_bodies: NotRequired[bool]
    scope: NotRequired[WireDemandReadScope]
    selection: NotRequired[WireReadDemandSelection]
    support_after: NotRequired[WireIdentifier]
    support_scope: NotRequired[Literal["page", "read"]]
    trust_snapshot: NotRequired[WireTrustSnapshot]
    view: NotRequired[Literal["frontier", "products", "support"]]


class WireResultObligation(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    binding_authority_changed: NotRequired[bool]
    demand_id: Required[WireDemandId]
    fate: Required[WireVisibleFate]
    generation: Required[WireGeneration | None]
    historical_fate: Required[WireHistoricalFate | None]
    id: Required[WireIdentifier]
    inputs_watermark: NotRequired[str]
    intent_id: Required[WireCompletionIntentId | None]
    native_readiness: Required[WireObligationReadiness | None]
    obligation_id: Required[WireObligationId]
    operation_id: Required[WireOperationId]
    original_source: Required[WireOriginalSourceId | None]
    parameters: Required[WireParameterMap]
    request_id: Required[WireRequestId | None]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


class WireSelectedSupportRow(TypedDict):
    key: Required[WireIdentifier]
    record: Required[dict[str, WireJsonValue]]
    relation: Required[WireIdentifier]


class WireSelectedSupportPage(TypedDict):
    after: Required[WireIdentifier | None]
    complete: Required[bool]
    records: Required[list[WireSelectedSupportRow]]


class WireResultProduct(TypedDict):
    analyzed_scope: Required[ContextualJsonValue]
    body: NotRequired[WireSemanticValue]
    body_state: Required[Literal["not_requested", "present"]]
    kind_contract: Required[WireKindContract]
    member_id: Required[WireMemberId | None]
    multiplicity: Required[WirePositiveInteger]
    original_source: Required[WireOriginalSourceId | None]
    position: Required[WireNonnegativeInteger]
    product_id: Required[WireProductId]
    role: Required[WireIdentifier]
    subject: Required[WireSubjectId]
    subject_definition: Required[WireIdentifier]


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
    inputs_watermark: NotRequired[str]
    read_id: NotRequired[WireReadId]
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
    selection: Required[
        WireBinding | WireResultBinding | WireReasonSelection | WireAuthoritySelection
    ]
    semantic_outcome: Required[WireIdentifier | None]
    trust_snapshot: Required[WireTrustSnapshot]
    use_id: Required[WireUseIdentity]


class WireReadDemandResultResult(TypedDict):
    attempt_failures: NotRequired[list[WireAttemptFailureObservation]]
    continuation: Required[WireContinuation | None]
    demand_id: Required[WireDemandId]
    frontier_at: Required[WireFrontierAt]
    intent: Required[WireReadDemandSelection]
    obligations: Required[list[WireResultObligation]]
    original_source_admissions: NotRequired[list[WireOriginalSourceAdmissionResult]]
    populations: Required[list[WirePopulation]]
    project_id: Required[ProjectId]
    read_id: Required[WireReadIdentity]
    read_snapshot: Required[WireReadSnapshot]
    release_id: Required[ReleaseId]
    root: Required[list[WireRootSubject]]
    runtime_id: Required[RuntimeId]
    scope: Required[WireDemandReadScope]
    selection: Required[WireReadDemandSelection]
    state: NotRequired[Literal["active", "cancelled"]]
    support_page: NotRequired[WireSelectedSupportPage | None]
    trust_snapshot: Required[WireTrustSnapshot]
    uses: Required[list[WireResultUse]]
    view: Required[Literal["frontier", "products", "support"]]


class WireReadExternalDataPacketRequest(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    max_bytes: Required[WirePositiveInteger]
    packet_id: Required[WireExternalPacketId]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


class WireReadExternalDataPacketResult(TypedDict):
    packet: Required[WireJsonValue]
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]


class WireReadExternalDataQueueRequest(TypedDict):
    demand_id: NotRequired[WireDemandId]
    limit: NotRequired[int]
    project_id: Required[ProjectId]


class WireReadExternalDataQueueResult(TypedDict):
    packets: Required[list[WireExternalPacketHead]]


class WireReadSelectedFeatureFitFrameRequest(TypedDict):
    cut_canonical_json: Required[str]
    demand_id: Required[WireIdentifier]
    derivation_id: Required[WireIdentifier]
    expected_cut: Required[str]
    frame_digest: Required[str]
    max_bytes: NotRequired[int]
    product_id: Required[WireIdentifier]
    project_id: Required[WireIdentifier]
    read_id: Required[WireReadId]
    use_id: Required[WireIdentifier]
    variant: Required[Literal["record-feature-grade", "operation-event-frame"]]


class WireRecordGradeDeclaredProductRef(TypedDict):
    analyzed_scope_meaning: Required[str]
    kind_contract: Required[str]
    member_id: NotRequired[str | None]
    original_source: Required[str | None]
    product_id: Required[str]
    project_id: Required[str]
    subject: Required[str]
    subject_definition: Required[str]


class WireRecordGradeDeclaredStructuralSource(TypedDict):
    analyzed_scope_meaning: Required[str]
    document: Required[str]
    format: NotRequired[Literal["declared-native-source-v1"]]
    kind_contract: Required[str]
    membership: Required[Literal["direct", "descendants"]]
    original_source: Required[str]
    project_id: Required[str]
    projection_digest: Required[str]
    section_pointer: Required[str]
    source: Required[str]
    source_member: NotRequired[str | None]
    source_product: Required[str]
    subject: Required[str]
    subject_definition: Required[str]


class WireRecordGradeDdoRecordCoverage(TypedDict):
    event_ids: Required[list[str]]
    failure_request_id: NotRequired[str | None]
    failure_use_id: NotRequired[str | None]
    outcome: Required[Literal["completed", "no_output", "failed"]]
    outputs: Required[list[WireRecordGradeDeclaredProductRef]]
    source: Required[WireRecordGradeDeclaredStructuralSource]


class WireRecordGradeRecordFeatures(TypedDict):
    family: Required[Literal["definition", "assertion", "measurement", "table", "formula_context"]]
    feature_signature: Required[str]
    input_digest: Required[str]
    interpretation_id: Required[str]
    names: Required[list[str]]
    record_id: Required[str]
    release_id: Required[str]
    unavailable: NotRequired[list[str]]
    values: Required[list[int | float | Decimal | None]]


class WireRecordGradeDdoRecordFinalEvent(TypedDict):
    event_procedure: Required[str]
    feature_input_digest: Required[str]
    feature_instance_digest: Required[str]
    final_event_score: Required[int | float | Decimal]
    outcome: NotRequired[Literal["completed"]]


class WireRecordGradeDdoRecordGradeEvent(TypedDict):
    correct: Required[bool]
    derivation_id: Required[str]
    features: Required[WireRecordGradeRecordFeatures]
    final_event: NotRequired[WireRecordGradeDdoRecordFinalEvent | None]
    interpretation_id: Required[str]
    origin_group: Required[str]
    reading: Required[WireRecordGradeDeclaredProductRef]
    reading_recipe: Required[str]
    record_id: Required[str]
    sample_weight: NotRequired[int | float | Decimal]
    source: Required[WireRecordGradeDeclaredStructuralSource]
    source_release_id: Required[str]


class WireRecordGradeDdoRecordOrigin(TypedDict):
    copied_from: NotRequired[list[WireRecordGradeDeclaredStructuralSource]]
    origin_group: Required[str]
    source: Required[WireRecordGradeDeclaredStructuralSource]


class WireRecordGradeDdoRecordReferencePass(TypedDict):
    adjudicates: NotRequired[list[str]]
    author: Required[str]
    content_digest: Required[str]
    exposed_outputs: NotRequired[list[WireRecordGradeDeclaredProductRef]]
    pass_kind: Required[Literal["A", "B", "C"]]
    question_digest: Required[str]
    reference: Required[WireRecordGradeDeclaredProductRef]
    rubric_digest: Required[str]
    source: Required[WireRecordGradeDeclaredStructuralSource]
    source_cut_id: Required[str]


class WireRecordGradeDdoRecordGradeFrame(TypedDict):
    coverage: Required[list[WireRecordGradeDdoRecordCoverage]]
    events: Required[list[WireRecordGradeDdoRecordGradeEvent]]
    family: Required[Literal["definition", "assertion", "measurement", "table", "formula_context"]]
    family_contract: Required[str]
    held_out_from: NotRequired[list[str]]
    origin_groups: Required[list[WireRecordGradeDdoRecordOrigin]]
    partition: Required[
        Literal["development", "feature_fit", "final_event_calibration", "final_assessment"]
    ]
    prediction_cut_id: Required[str]
    prediction_release_id: Required[str]
    project_id: Required[str]
    question_digest: Required[str]
    reading_recipe: Required[str]
    reference_digest: Required[str]
    reference_passes: Required[list[WireRecordGradeDdoRecordReferencePass]]
    rubric_digest: Required[str]
    source_cut_id: Required[str]
    source_release_id: Required[str]
    sources: Required[list[WireRecordGradeDeclaredStructuralSource]]
    subset: Required[str]


class WireSelectedRecordGrade(TypedDict):
    frame: Required[WireRecordGradeDdoRecordGradeFrame]
    frame_canonical_json: Required[str]
    frame_digest: Required[str]
    version: NotRequired[Literal["record-grade-1"]]


class WireSelectedOperationEventFrame(TypedDict):
    frame: Required[WireOperationEventFrameSelectedOperationEventFrame]
    frame_canonical_json: Required[str]
    frame_digest: Required[str]
    version: NotRequired[Literal["selected-operation-event-frame-product-1"]]


class WireReadSelectedFeatureFitFrameResult(TypedDict):
    cut: Required[WireCutSelection]
    derivation_id: Required[WireIdentifier]
    frame: Required[WireSelectedRecordGrade | WireSelectedOperationEventFrame]
    product_id: Required[WireIdentifier]
    receipt_id: Required[WireIdentifier]
    variant: Required[Literal["record-feature-grade", "operation-event-frame"]]


class WireReadSelectedPdfObservationsResult(TypedDict):
    cut: Required[WireCutSelection]
    original_source: Required[WireIdentifier]
    receipt: Required[WirePdfObservationExecutionReceipt]


class WireReadSelectedPdfSourceResult(TypedDict):
    cut: Required[WireCutSelection]
    original_source: Required[WireOriginalSourceId]
    receipt: Required[WirePdfExecutionReceipt]


class WireVisualEvidencePin(TypedDict):
    derivation_id: Required[WireDerivationId]
    product_id: Required[WireProductId]
    use_id: Required[WireUseIdentity]


class WireVisualReadVisualSourceRegion(TypedDict):
    address_space: NotRequired[Literal["pdf_points"]]
    bottom: Required[int | float | Decimal]
    enclosing_occurrence_id: NotRequired[str | None]
    left: Required[int | float | Decimal]
    origin: NotRequired[Literal["top_left"]]
    precision: NotRequired[Literal["coarse"]]
    right: Required[int | float | Decimal]
    top: Required[int | float | Decimal]


class WireReadSelectedVisualEvidenceRequest(TypedDict):
    after: Required[int]
    artifact_digest: NotRequired[str]
    cell_index: NotRequired[int]
    evidence: Required[WireVisualEvidencePin]
    kind: NotRequired[
        Literal[
            "picture",
            "caption",
            "caption_candidate",
            "picture_description",
            "picture_text",
            "formula",
            "mermaid",
            "table",
            "cell_group",
            "cell_text",
        ]
    ]
    limit: Required[int]
    max_bytes: Required[int]
    mode: Required[Literal["header", "rows", "artifact"]]
    occurrence_id: NotRequired[WireIdentifier]
    query: NotRequired[WireIdentifier]
    regions: Required[list[WireVisualReadVisualSourceRegion]]
    source: Required[WireReadSelectedPdfSourceRequest]


class WireVisualReadVisualEvidencePin(TypedDict):
    derivation_id: Required[WireDerivationId]
    product_id: Required[WireProductId]
    use_id: Required[WireUseIdentity]


class WireVisualReadVisualReadHeader(TypedDict):
    evidence: Required[WireVisualReadVisualEvidencePin]
    mapped_digest: Required[str | None]
    mapping: Required[dict[str, WireVisualReadJsonValue] | None]
    mapping_availability: Required[Literal["not_selected", "unavailable", "available"]]
    observation: Required[dict[str, WireVisualReadJsonValue]]
    producer: Required[dict[str, WireVisualReadJsonValue]]
    raw: Required[WireVisualReadVisualEvidencePin]
    raw_producer: Required[dict[str, WireVisualReadJsonValue]]


class WireVisualReadVisualHeaderReply(TypedDict):
    header: Required[WireVisualReadVisualReadHeader]
    kind: Required[Literal["header"]]


class WireVisualReadVisualPicture(TypedDict):
    kind: NotRequired[Literal["picture"]]
    metadata: NotRequired[dict[str, WireVisualReadJsonValue] | None]
    occurrence_id: Required[str]
    parent_occurrence_id: NotRequired[str | None]
    provider_locator: NotRequired[str | None]
    source_region: NotRequired[WireVisualReadVisualSourceRegion | None]


class WireVisualReadVisualCaption(TypedDict):
    kind: NotRequired[Literal["caption"]]
    occurrence_id: Required[str]
    parent_occurrence_id: Required[str]
    parser_attachment_occurrence_ids: NotRequired[list[str]]
    provider_locator: NotRequired[str | None]
    source_region: NotRequired[WireVisualReadVisualSourceRegion | None]
    text: Required[str]


class WireVisualReadVisualCaptionCandidate(TypedDict):
    associated_picture_occurrence_ids: NotRequired[list[str]]
    kind: NotRequired[Literal["caption_candidate"]]
    occurrence_id: Required[str]
    parent_occurrence_id: NotRequired[None]
    parser_attachment_occurrence_ids: NotRequired[list[str]]
    provider_locator: NotRequired[str | None]
    source_region: NotRequired[WireVisualReadVisualSourceRegion | None]
    text: Required[str]


class WireVisualReadVisualText(TypedDict):
    kind: Required[
        Literal["picture_description", "picture_text", "formula", "mermaid", "cell_text"]
    ]
    native_label: NotRequired[str | None]
    occurrence_id: Required[str]
    original_text: NotRequired[str | None]
    parent_occurrence_id: NotRequired[str | None]
    provider_locator: NotRequired[str | None]
    source_region: NotRequired[WireVisualReadVisualSourceRegion | None]
    text: Required[str]


class WireVisualReadVisualTableCell(TypedDict):
    column_header: NotRequired[bool]
    column_header_path: NotRequired[list[int]]
    content_occurrence_id: NotRequired[str | None]
    end_col_offset_idx: Required[int]
    end_row_offset_idx: Required[int]
    row_header: NotRequired[bool]
    row_header_path: NotRequired[list[int]]
    start_col_offset_idx: Required[int]
    start_row_offset_idx: Required[int]
    text: Required[str]


class WireVisualReadVisualTable(TypedDict):
    cells: Required[list[WireVisualReadVisualTableCell]]
    kind: NotRequired[Literal["table"]]
    num_cols: Required[int]
    num_rows: Required[int]
    occurrence_id: Required[str]
    parent_occurrence_id: NotRequired[str | None]
    provider_locator: NotRequired[str | None]
    source_region: NotRequired[WireVisualReadVisualSourceRegion | None]


class WireVisualReadVisualCellGroup(TypedDict):
    kind: NotRequired[Literal["cell_group"]]
    native_label: Required[str]
    occurrence_id: Required[str]
    parent_occurrence_id: Required[str]
    provider_locator: NotRequired[str | None]
    source_region: NotRequired[WireVisualReadVisualSourceRegion | None]


class WireVisualReadVisualRowsReply(TypedDict):
    items: Required[
        list[
            WireVisualReadVisualPicture
            | WireVisualReadVisualCaption
            | WireVisualReadVisualCaptionCandidate
            | WireVisualReadVisualText
            | WireVisualReadVisualTable
            | WireVisualReadVisualCellGroup
        ]
    ]
    kind: Required[Literal["rows"]]
    next_after: Required[int | None]


class WireVisualReadVisualArtifactReply(TypedDict):
    content_hex: Required[str]
    digest: Required[str]
    kind: Required[Literal["artifact"]]
    media_type: Required[Literal["image/png", "text/html; charset=utf-8", "application/json"]]
    next_offset: Required[int | None]
    offset: Required[int]
    total_bytes: Required[int]


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
    project_id: Required[ProjectId]
    release_id: Required[ReleaseId]
    root: Required[list[WireRootSubject]]
    runtime_id: Required[RuntimeId]
    selection: Required[WireDemandIntent]
    strength: Required[Literal["value", "episode", "independent"]]


class WireRegisterDataDemandResult(TypedDict):
    demand_id: Required[WireDemandId]
    inserted_obligations: Required[int]
    selection: Required[WireDemandIntent]
    state: NotRequired[Literal["active", "cancelled"]]


class WireRegisterDataExecutionOriginRequest(TypedDict):
    attempt: Required[WirePositiveInteger]
    generation: Required[WirePositiveInteger]
    holder: Required[WireIdentifier]
    request_id: Required[WireIdentifier]
    runtime_id: Required[WireIdentifier]
    task_id: Required[WireTaskId]


class WireRegisterDataExecutionOriginResultCandidatesItem(TypedDict):
    generation: Required[WirePositiveInteger]
    origin_id: Required[WireIdentifier]
    request_id: Required[WireIdentifier]


class WireRegisterDataExecutionOriginResult(TypedDict):
    candidates: Required[list[WireRegisterDataExecutionOriginResultCandidatesItem]]
    origin_id: Required[WireIdentifier]


class WireReleaseDataAttemptRequest(TypedDict):
    attempt: Required[TaskAttempt]
    failure: Required[WireAttemptFailure]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    physical_retirement: Required[Literal["confirmed"]]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


class WireReleaseDataAttemptResultVariant2(TypedDict):
    attempt: Required[TaskAttempt]
    failure_id: Required[WireFailureId]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    replayed: Required[bool]
    request_id: Required[WireRequestId]
    retained_intent_id: Required[WireCompletionIntentId | None]
    state: Required[Literal["released"]]
    task_id: Required[TaskId]


class WireReleaseExternalDataPacketRequest(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    packet_id: Required[WireExternalPacketId]
    reason: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


class WireReleaseExternalDataPacketResult(TypedDict):
    packet_id: Required[WireExternalPacketId]
    released: Required[Literal[True]]
    state: Required[Literal["awaiting-external"]]


class WireRenewDataRequestRequest(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_seconds: Required[int]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


class WireRenewedDataRequestResult(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    lease_until: Required[str]
    request_id: Required[WireRequestId]
    state: Required[Literal["renewed"]]
    task_id: Required[TaskId]
    trust_snapshot: Required[WireTrustSnapshot]


class WireRetainDataCompletionIntentResult(TypedDict):
    intent_id: Required[WireCompletionIntentId]
    payload_digest: Required[WireIdentifier]


class WireRetainExternalDataPacketRequest(TypedDict):
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    max_bytes: Required[WirePositiveInteger]
    request_id: Required[WireRequestId]
    runtime_id: Required[RuntimeId]
    task_id: Required[TaskId]


class WireRetainExternalDataPacketResult(TypedDict):
    packet_digest: Required[str]
    packet_id: Required[WireExternalPacketId]
    state: Required[Literal["awaiting-external"]]


class WireRevokeDataSupportRequest(TypedDict):
    original_source: Required[WireOriginalSourceId | None]
    project_id: Required[ProjectId]
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
    attempt: Required[TaskAttempt]
    generation: Required[WireGeneration]
    holder: Required[WireIdentifier]
    request_id: Required[WireRequestId]
    task_id: Required[TaskId]


type WireJsonValue = WireExactJSONValue

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

type WireSupportMember = (
    WireComputationalSupportMember | WireOriginalSourceSupportMember | WireAuthoredFactSupportMember
)

type WireTaskId = TaskId

type WireRequestMeaning = (
    WireSemanticValue
    | list[Literal["ddo"] | Literal["semantic-request"] | Literal["1"] | WireSemanticValue]
)

type WireTrustSnapshot = dict[str, WireNonnegativeInteger]

type WireD1LimitationReply = WireD1LimitationReplyVariant1 | WireD1LimitationReplyVariant2

type WireText = str

type WireClaimDataRequestResult = (
    WireClaimDataRequestResultVariant1 | WireClaimDataRequestResultVariant2
)

type WireParameterMap = dict[str, WireJsonValue]

type WireFrontierAt = str

type WireReadSnapshot = WireReadSnapshotIdentity

type WireOriginalSourceSelection = WireOriginalDocumentSelection | WireAuthoredFactSelection

type WireSourceSetAcquisition = WireSourceSetAcquisitionVariant1 | WireSourceSetAcquisitionVariant2

type WireReadDemandSelection = WireDemandIntent | WirePublicDemandSelection

type WireDataTaskState = Literal["pending", "running", "done", "empty", "failed", "cancelled"]

type WirePdfSearchDigest = str

type WireReadId = WireReadIdentity

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

type WireOriginalSupportReference = WireOriginalDocumentRef | WireAuthoredFactRef

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

type WireVisualReadJsonValue = WireExactJSONValue

type WireSelectedVisualRead = (
    WireVisualReadVisualHeaderReply
    | WireVisualReadVisualRowsReply
    | WireVisualReadVisualArtifactReply
)

type WireReadSelectedVisualEvidenceResult = WireSelectedVisualRead

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

    def read_selected_feature_fit_frame(
        self, payload: WireReadSelectedFeatureFitFrameRequest
    ) -> WireReadSelectedFeatureFitFrameResult:
        return cast(
            WireReadSelectedFeatureFitFrameResult,
            self._invoke("read_selected_feature_fit_frame", payload),
        )

    def admit_authored_data(
        self, payload: WireAdmitAuthoredDataRequest
    ) -> WireOriginalSourceAdmissionResult:
        return cast(WireOriginalSourceAdmissionResult, self._invoke("admit_authored_data", payload))

    def inspect_data_operation_release(
        self, payload: WireInspectDataOperationReleaseRequest
    ) -> WireInspectDataOperationReleaseResult:
        return cast(
            WireInspectDataOperationReleaseResult,
            self._invoke("inspect_data_operation_release", payload),
        )

    def inspect_data_execution(
        self, payload: WireInspectDataExecutionRequest
    ) -> WireInspectDataExecutionResult:
        return cast(WireInspectDataExecutionResult, self._invoke("inspect_data_execution", payload))

    def admit_original_document_asset(
        self, payload: WireAdmitOriginalDocumentAssetRequest
    ) -> WireOriginalSourceAdmissionResult:
        return cast(
            WireOriginalSourceAdmissionResult,
            self._invoke("admit_original_document_asset", payload),
        )

    def register_data_demand(
        self, payload: WireRegisterDataDemandRequest
    ) -> WireRegisterDataDemandResult:
        return cast(WireRegisterDataDemandResult, self._invoke("register_data_demand", payload))

    def cancel_data_demand(
        self, payload: WireCancelDataDemandRequest
    ) -> WireCancelDataDemandResult:
        return cast(WireCancelDataDemandResult, self._invoke("cancel_data_demand", payload))

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

    def attach_data_requests(
        self, payload: WireAttachDataRequestsRequest
    ) -> WireAttachDataRequestsResult:
        return cast(WireAttachDataRequestsResult, self._invoke("attach_data_requests", payload))

    def establish_data_rule_proof(
        self, payload: WireEstablishDataRuleProofRequest
    ) -> WireEstablishDataRuleProofResult:
        return cast(
            WireEstablishDataRuleProofResult, self._invoke("establish_data_rule_proof", payload)
        )

    def claim_data_requests(
        self, payload: WireClaimDataRequestsRequest
    ) -> WireClaimDataRequestsResult:
        return cast(WireClaimDataRequestsResult, self._invoke("claim_data_requests", payload))

    def renew_data_request(
        self, payload: WireRenewDataRequestRequest
    ) -> WireRenewDataRequestResult:
        return cast(WireRenewDataRequestResult, self._invoke("renew_data_request", payload))

    def release_data_attempt(
        self, payload: WireReleaseDataAttemptRequest
    ) -> WireReleaseDataAttemptResult:
        return cast(WireReleaseDataAttemptResult, self._invoke("release_data_attempt", payload))

    def register_data_execution_origin(
        self, payload: WireRegisterDataExecutionOriginRequest
    ) -> WireRegisterDataExecutionOriginResult:
        return cast(
            WireRegisterDataExecutionOriginResult,
            self._invoke("register_data_execution_origin", payload),
        )

    def consume_data_completion_draft(
        self, payload: WireConsumeDataCompletionDraftRequest
    ) -> WireRetainDataCompletionIntentResult:
        return cast(
            WireRetainDataCompletionIntentResult,
            self._invoke("consume_data_completion_draft", payload),
        )

    def inspect_data_completion_draft(
        self, payload: WireInspectDataCompletionDraftRequest
    ) -> WireInspectDataCompletionDraftResult:
        return cast(
            WireInspectDataCompletionDraftResult,
            self._invoke("inspect_data_completion_draft", payload),
        )

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

    def read_selected_pdf_source(
        self, payload: WireReadSelectedPdfSourceRequest
    ) -> WireReadSelectedPdfSourceResult:
        return cast(
            WireReadSelectedPdfSourceResult, self._invoke("read_selected_pdf_source", payload)
        )

    def read_selected_pdf_observations(
        self, payload: WireReadSelectedPdfSourceRequest
    ) -> WireReadSelectedPdfObservationsResult:
        return cast(
            WireReadSelectedPdfObservationsResult,
            self._invoke("read_selected_pdf_observations", payload),
        )

    def initialize_source_project(
        self, payload: WireInitializeSourceProjectRequest
    ) -> WireInitializeSourceProjectResult:
        return cast(
            WireInitializeSourceProjectResult, self._invoke("initialize_source_project", payload)
        )

    def read_selected_visual_evidence(
        self, payload: WireReadSelectedVisualEvidenceRequest
    ) -> WireReadSelectedVisualEvidenceResult:
        return cast(
            WireReadSelectedVisualEvidenceResult,
            self._invoke("read_selected_visual_evidence", payload),
        )

    def ensure_pdf_search_projection(
        self, payload: WireEnsurePdfSearchProjectionRequest
    ) -> WireEnsurePdfSearchProjectionResult:
        return cast(
            WireEnsurePdfSearchProjectionResult,
            self._invoke("ensure_pdf_search_projection", payload),
        )

    def rank_pdf_search_projection(
        self, payload: WireRankPdfSearchProjectionRequest
    ) -> WireRankPdfSearchProjectionResult:
        return cast(
            WireRankPdfSearchProjectionResult, self._invoke("rank_pdf_search_projection", payload)
        )
