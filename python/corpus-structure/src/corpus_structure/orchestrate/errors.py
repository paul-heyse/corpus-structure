"""Orchestration refusals without acquiring a historical database implementation."""

from collections.abc import Sequence


class RunError(ValueError):
    """A run that cannot be created or moved as asked."""


class ProfileRefused(RunError):
    """A source profile names a kind outside the run's schema version (DA-010)."""

    def __init__(self, issues: Sequence[tuple[str, str, str, str]]) -> None:
        self.issues = list(issues)  # (profile, code, field, value)
        super().__init__(
            "; ".join(
                f"source profile {p}: {field} {value!r}: {code}"
                for p, code, field, value in self.issues
            )
        )


class IllegalTransition(RunError):
    pass
