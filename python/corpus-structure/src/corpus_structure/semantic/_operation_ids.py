"""Generated semantic identifiers from execution correspondences; do not edit."""

from typing import Literal, NewType

ContentDigest = NewType("ContentDigest", str)
CutId = NewType("CutId", int)
DocumentId = NewType("DocumentId", int)
InterventionId = NewType("InterventionId", int)
MethodConfigId = NewType("MethodConfigId", int)
MethodId = NewType("MethodId", int)
ProductKey = NewType("ProductKey", str)
ProjectId = NewType("ProjectId", str)
RealizationId = NewType("RealizationId", str)
ReleaseId = NewType("ReleaseId", str)
RunId = NewType("RunId", int)
RuntimeId = NewType("RuntimeId", str)
SourceViewId = NewType("SourceViewId", int)
TaskAttempt = NewType("TaskAttempt", int)
TaskId = NewType("TaskId", int)
type CompletionReceiptProtocol = Literal["done", "empty", "failed"]
type CompletionResultTransaction = Literal["applied", "replay"]
type NativeAdmissionParametersPurpose = Literal["admit", "evaluate", "read", "write"]
type PdfFrozenBuildKind = Literal["integrated", "native"]
type PdfPublishedRevisionKind = Literal["integrated", "native"]
type PdfRecordCompanionFamily = Literal[
    "coverage",
    "health",
    "input",
    "mapping_report",
    "native_metadata",
    "occurrence",
    "relation",
    "request_outcome",
]
type PdfSourceViewPublicationMembership = Literal["descendants", "direct"]
type PdfStageBuildState = Literal["abandoned", "frozen", "open", "published"]
type PublishedCoverageRowOutcome = Literal[
    "capped", "complete", "partial", "unknown", "unrequested", "unsupported"
]
type PublishedInputRowInputRole = Literal[
    "alternative", "policy_input", "recognition", "structural"
]
type PublishedMappingReportRowNormalization = Literal[
    "clipped", "inherited", "none", "normalized", "unknown"
]
type PublishedMappingReportRowOutcome = Literal[
    "dropped", "evidence_only", "mapped", "unresolved", "unsupported"
]
type PublishedRelationRowComparison = Literal["geometry", "grid", "mathematical", "order", "text"]
type PublishedRelationRowEndpointRole = Literal["alternative", "evidence", "input", "output"]
type PublishedRelationRowRelationKind = Literal["correspondence", "decision"]
type PublishedSectionNodeRowRole = Literal["ancestor", "selected"]
