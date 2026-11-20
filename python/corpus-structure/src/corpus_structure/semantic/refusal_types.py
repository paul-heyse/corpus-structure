"""Passive semantic refusal identities shared by preparation, readers and transports."""


class SemanticRefusal(ValueError):
    """An owned boundary deliberately refuses an unsupported or incompatible request."""


class ReadLimit(SemanticRefusal):
    def __init__(self, message: str, *, reason: str):
        self.reason = reason
        super().__init__(message)


class ReferenceError(ValueError):
    """A reference is incomplete, stale or belongs to another immutable binding."""


class OperationConflict(ValueError):
    """Immutable input identity changed or a task/pass fence was lost."""


class SourceReadRefused(OperationConflict):
    """An owned source-read failure with an explicit modeled outcome."""

    def __init__(self, outcome: str, reason: str):
        self.outcome = outcome
        super().__init__(reason)


class ContinuationRefusal(SemanticRefusal):
    """A continuation cannot be used, with a stable machine-readable reason."""

    reason = "invalid_token"

    def __init__(self, message: str, *, reason: str | None = None):
        super().__init__(message)
        if reason is not None:
            self.reason = reason


class InvalidContinuation(ContinuationRefusal):
    """The token or query-owned cursor is malformed or unsupported."""


class WrongBinding(ContinuationRefusal):
    """The token describes another request identity."""

    reason = "wrong_query"


class WrongRelease(WrongBinding):
    """A handle or selector belongs to another semantic release."""

    reason = "wrong_release"


class StaleSnapshot(ContinuationRefusal):
    """The bound revision or implementation no longer supports continuation."""

    reason = "stale_revision"


class RichQueryRefused(SemanticRefusal):
    """An exact rich query lacks its declared scope or admitted work/response capacity."""
