"""Generated semantic identifiers from execution correspondences; do not edit."""

from typing import Literal, NewType

CutId = NewType("CutId", int)
MethodConfigId = NewType("MethodConfigId", int)
MethodId = NewType("MethodId", int)
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
