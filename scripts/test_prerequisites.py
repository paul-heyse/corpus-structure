"""Known external prerequisite absences, shared by native fixtures and outcome reporting.

Failures in authentication, configuration, migration, posture or cleanup are deliberately not
prerequisites: callers must leave those exceptions intact.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, MutableMapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


class PrerequisiteUnavailable(RuntimeError):
    def __init__(self, category: str, reason: str) -> None:
        self.category = category
        self.reason = reason
        super().__init__(reason)


def mark_prerequisites(
    items: Iterable[pytest.Item],
    checks: Mapping[str, Callable[[], str | None]],
    cache: MutableMapping[str, str | None],
) -> None:
    """Annotate all missing named prerequisites before fixtures, checking each name once.

    The caller owns the small named registry and passes only the final selected items.
    Runtime acquisition failures retain the independent PrerequisiteUnavailable route.
    """
    import pytest

    for item in items:
        names = {"corpus"} if item.get_closest_marker("corpus") else set()
        for marker in item.iter_markers("prerequisite"):
            if len(marker.args) != 1 or not isinstance(marker.args[0], str) or marker.kwargs:
                raise pytest.UsageError(f"{item.nodeid}: prerequisite expects one name")
            names.add(marker.args[0])
        missing = []
        for name in sorted(names):
            if name not in checks:
                raise pytest.UsageError(f"{item.nodeid}: unknown prerequisite {name!r}")
            if name not in cache:
                cache[name] = checks[name]()
            unavailable = cache[name]
            if unavailable is not None:
                missing.append({"name": name, "reason": unavailable})
        if missing:
            reason = "; ".join(f"{entry['name']}: {entry['reason']}" for entry in missing)
            item.user_properties.extend(
                [("qualification_prerequisites", missing), ("qualification_reason", reason)]
            )
            item.add_marker(pytest.mark.skip(reason=reason))
