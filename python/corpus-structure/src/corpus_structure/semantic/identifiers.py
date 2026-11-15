"""Current semantic identifiers generated from explicit physical declarations."""

from typing import NewType

ContentDigest = NewType("ContentDigest", str)
DocumentId = NewType("DocumentId", int)
ProductKey = NewType("ProductKey", str)
ProjectId = NewType("ProjectId", str)
RealizationId = NewType("RealizationId", str)
ReleaseId = NewType("ReleaseId", str)
RuntimeId = NewType("RuntimeId", str)
SourceViewId = NewType("SourceViewId", int)
TaskAttempt = NewType("TaskAttempt", int)
TaskId = NewType("TaskId", int)
