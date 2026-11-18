"""Typed changes to facts from two explicitly captured released models."""

from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.model.compiled import CompiledModel, SchemaYamlLoader


class ModelFactChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    element: str
    kind: Literal["added", "removed", "changed"]
    before: JsonValue = None
    after: JsonValue = None


class CompiledModelComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    before: str
    after: str
    changes: tuple[ModelFactChange, ...]


def compare_compiled_models(before: CompiledModel, after: CompiledModel) -> CompiledModelComparison:
    """Compare parsed declaration facts, preserving source and authoritative field paths."""
    changes = []
    absent = object()

    def visit(source: str, path: tuple[str, ...], old: Any, new: Any):
        if old == new:
            return
        if isinstance(old, dict) and isinstance(new, dict):
            for name in sorted(old.keys() | new.keys()):
                visit(source, (*path, str(name)), old.get(name, absent), new.get(name, absent))
            return
        changes.append(
            ModelFactChange(
                source=source,
                element="/".join(path),
                kind="added" if old is absent else "removed" if new is absent else "changed",
                before=None if old is absent else old,
                after=None if new is absent else new,
            )
        )

    for source in sorted(before.sources.keys() | after.sources.keys()):
        if source == "linkml:types":
            continue
        old = (
            yaml.load(before.sources[source], Loader=SchemaYamlLoader)
            if source in before.sources
            else absent
        )
        new = (
            yaml.load(after.sources[source], Loader=SchemaYamlLoader)
            if source in after.sources
            else absent
        )
        visit(source, (), old, new)
    return CompiledModelComparison(
        before=before.identity, after=after.identity, changes=tuple(changes)
    )
