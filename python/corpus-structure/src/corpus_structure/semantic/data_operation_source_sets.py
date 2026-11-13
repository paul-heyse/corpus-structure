"""Frozen exact original-source pins for explicitly declared cross-source roles.

These values select an authenticated product/member. They grant no authority by
construction; native acquisition validates custody, the projected reference and
producing support before exposing any matching row.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .identity import canonical_bytes

if TYPE_CHECKING:
    from .structural_products import ExternalSourceRef, StructuralInput


@dataclass(frozen=True)
class SourceSetEntry:
    project_id: str
    original_source: str
    subject: str
    analyzed_scope: bytes
    product: str
    member: str | None
    source_reference: str
    reference: bytes

    def __post_init__(self) -> None:
        from .structural_products import ExternalSourceRef

        if (
            any(
                type(value) is not str
                for value in (
                    self.project_id,
                    self.original_source,
                    self.subject,
                    self.product,
                    self.source_reference,
                )
            )
            or type(self.reference) is not bytes
            or type(self.analyzed_scope) is not bytes
        ):
            raise TypeError("source-set custody and reference pins require immutable exact types")
        if self.member is not None and type(self.member) is not str:
            raise TypeError("source-set member must be an original string identifier")
        reference = ExternalSourceRef.model_validate_json(self.reference)
        if reference.project_id != self.project_id or reference.identity != self.source_reference:
            raise ValueError("source-set reference differs from its original identity/project")
        if not all((self.project_id, self.original_source, self.subject, self.product)):
            raise ValueError("source-set entries require exact qualified original custody")
        if self.member is not None and not self.member:
            raise ValueError("source-set member is null or a nonempty original identifier")
        if (
            not isinstance(json.loads(self.analyzed_scope), dict)
            or canonical_bytes(json.loads(self.analyzed_scope)) != self.analyzed_scope
        ):
            raise ValueError("source-set scope must be canonical JSON")
        if canonical_bytes(reference.model_dump(mode="json", exclude_none=True)) != self.reference:
            raise ValueError("source-set original reference must be canonical")

    @classmethod
    def from_structural_source(
        cls,
        reference: ExternalSourceRef,
        *,
        original_source: str,
        subject: str,
        analyzed_scope: bytes,
        product: str,
        member: str | None = None,
    ) -> SourceSetEntry:
        return cls(
            reference.project_id,
            original_source,
            subject,
            analyzed_scope,
            product,
            member,
            reference.identity,
            canonical_bytes(reference.model_dump(mode="json", exclude_none=True)),
        )

    def record(self) -> dict:
        return {
            "project_id": self.project_id,
            "original_source": self.original_source,
            "subject": self.subject,
            "analyzed_scope": json.loads(self.analyzed_scope),
            "product": self.product,
            "member": self.member,
            "source_reference": self.source_reference,
            "reference": json.loads(self.reference),
        }


@dataclass(frozen=True)
class FrozenSourceSet:
    name: str
    entries: tuple[SourceSetEntry, ...]

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str
            or type(self.entries) is not tuple
            or any(not isinstance(entry, SourceSetEntry) for entry in self.entries)
        ):
            raise TypeError("source sets require an immutable typed entry tuple")
        if not self.name or not self.entries:
            raise ValueError("source sets require a name and exact original members")
        identities = {(entry.product, entry.member) for entry in self.entries}
        if len(identities) != len(self.entries):
            raise ValueError("source sets require unique qualified product/member pins")

    @classmethod
    def from_structural_input(
        cls, name: str, inputs: StructuralInput, entries: tuple[SourceSetEntry, ...]
    ) -> FrozenSourceSet:
        references = {
            source.identity: canonical_bytes(source.model_dump(mode="json", exclude_none=True))
            for source in inputs.sources
        }
        if any(references.get(entry.source_reference) != entry.reference for entry in entries):
            raise ValueError(
                "source-set entry is outside the captured StructuralInput original sources"
            )
        return cls(name, entries)

    def record(self) -> list[dict]:
        return [
            entry.record()
            for entry in sorted(self.entries, key=lambda entry: (entry.product, entry.member or ""))
        ]


def source_sets_record(source_sets: tuple[FrozenSourceSet, ...]) -> dict:
    if len({scope.name for scope in source_sets}) != len(source_sets):
        raise ValueError("duplicate frozen source-set name")
    return {
        scope.name: scope.record() for scope in sorted(source_sets, key=lambda scope: scope.name)
    }


def read_source_sets(record: dict) -> tuple[FrozenSourceSet, ...]:
    return tuple(
        FrozenSourceSet(
            name,
            tuple(
                SourceSetEntry(
                    entry["project_id"],
                    entry["original_source"],
                    entry["subject"],
                    canonical_bytes(entry["analyzed_scope"]),
                    entry["product"],
                    entry["member"],
                    entry["source_reference"],
                    canonical_bytes(entry["reference"]),
                )
                for entry in entries
            ),
        )
        for name, entries in sorted(record.items())
    )
