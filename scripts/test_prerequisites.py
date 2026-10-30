"""Known external prerequisite absences, shared by native fixtures and outcome reporting.

Failures in authentication, configuration, migration, posture or cleanup are deliberately not
prerequisites: callers must leave those exceptions intact.
"""


class PrerequisiteUnavailable(RuntimeError):
    def __init__(self, category: str, reason: str) -> None:
        self.category = category
        self.reason = reason
        super().__init__(reason)
