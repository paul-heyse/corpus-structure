"""Immutable curator-supplied target descriptions, separate from attributed source quotations."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.methods.contextual_embeddings import identity
from corpus_structure.semantic.contextual_retrieval import target_representation


class RegistryTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    target_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    type_name: str | None = None
    parent: str | None = None
    scope: str = "global"
    effective_version: str | None = None


def registry_input(targets: Sequence[RegistryTarget]):
    if not targets or len({t.target_id for t in targets}) != len(targets):
        raise ValueError("curated registry needs distinct targets")
    ordered = tuple(sorted(targets, key=lambda t: t.target_id))
    registry_id = identity("curated-registry", [t.model_dump(mode="json") for t in ordered])
    representations = tuple(
        target_representation(
            source_binding=identity("curated-target", t.model_dump(mode="json")),
            **t.model_dump(mode="python"),
        )
        for t in ordered
    )
    return registry_id, representations
