"""Typed source-statement materialization binding archived in the agent schema."""

from __future__ import annotations

from .types import ClassDefinition, PreparedRelease


def statement_definition(prepared: PreparedRelease) -> ClassDefinition:
    """Resolve the explicit operation binding; older archives retain the base class."""
    binding = next((d for d in prepared.definitions if d.name == "AgentStatementBinding"), None)
    name = (next(p.range for p in binding.properties if p.name == "statement")
            if binding is not None else "SourceStatement")
    definition = next(d for d in prepared.definitions if d.name == name)
    if definition.name != "SourceStatement" and "SourceStatement" not in definition.ancestors:
        raise ValueError("source statement binding must name SourceStatement or a declared subclass")
    return definition


def statement_kinds(prepared: PreparedRelease, *, subset: str | None = None) -> frozenset[str]:
    definition = statement_definition(prepared)
    enum = next(p.range for p in definition.properties if p.name == "statement_kind")
    return prepared.enum_members(enum, subset=subset)
