"""Current semantic identifiers generated from explicit physical declarations."""

from typing import NewType

ContentDigest = NewType("ContentDigest", str)
DocumentId = NewType("DocumentId", int)
ProductKey = NewType("ProductKey", str)
ProjectId = NewType("ProjectId", str)
ReleaseId = NewType("ReleaseId", str)
RuntimeId = NewType("RuntimeId", str)
TaskAttempt = NewType("TaskAttempt", int)
TaskId = NewType("TaskId", int)
