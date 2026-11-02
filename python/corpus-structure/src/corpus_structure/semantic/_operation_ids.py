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
SourceViewId = NewType("SourceViewId", int)
TaskAttempt = NewType("TaskAttempt", int)
TaskId = NewType("TaskId", int)
type NativeAdmissionParametersPurpose = Literal["admit", "evaluate", "read", "write"]
type PdfFrozenBuildKind = Literal["integrated", "native"]
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
