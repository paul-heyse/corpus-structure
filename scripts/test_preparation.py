"""Fixture-owned preparation affinity resolved for one collected pytest item."""

from __future__ import annotations

from importlib.metadata import version

import pytest

_GROUP = "__corpus_preparation_group__"
_PYTEST_VERSION = version("pytest")


def preparation_fixture(group: str, **options):
    """Declare worker affinity together with the fixture that owns preparation."""

    def decorate(function):
        setattr(function, _GROUP, group)
        return pytest.fixture(**options)(function)

    return decorate


def preparation_group(item: pytest.Item) -> str | None:
    """Resolve overriding fixture definitions, including explicitly requested parents."""
    info = getattr(item, "_fixtureinfo", None)
    if _PYTEST_VERSION != "9.1.1" or not hasattr(info, "name2fixturedefs"):
        raise pytest.UsageError(
            f"{item.nodeid}: preparation fixture resolution requires pytest 9.1.1 fixture information"
        )
    definitions = info.name2fixturedefs
    groups: dict[str, list[str]] = {}
    visited = set()

    def visit(name, offset=1):
        candidates = definitions.get(name, ())
        if len(candidates) < offset:
            return
        definition = candidates[-offset]
        identity = id(definition)
        if identity in visited:
            return
        visited.add(identity)
        group = getattr(definition.func, _GROUP, None)
        if group is not None:
            groups.setdefault(group, []).append(f"{definition.baseid}:{name}")
        for dependency in definition.argnames:
            visit(dependency, offset + 1 if dependency == name else 1)

    for name in getattr(item, "fixturenames", ()):
        visit(name)
    for mark in item.iter_markers("xdist_group"):
        group = str(mark.args[0] if mark.args else mark.kwargs.get("name", "default"))
        groups.setdefault(group, []).append("explicit xdist_group")
    if len(groups) > 1:
        detail = "; ".join(
            f"{group} ({', '.join(owners)})" for group, owners in sorted(groups.items())
        )
        raise pytest.UsageError(f"{item.nodeid}: conflicting preparation affinity groups: {detail}")
    return next(iter(groups), None)
