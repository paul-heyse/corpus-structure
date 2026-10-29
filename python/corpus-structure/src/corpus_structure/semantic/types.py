"""Explicit immutable inputs and products of semantic release preparation."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, TypeAdapter


@dataclass(frozen=True)
class SourceArtifact:
    name: str
    content: bytes

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


@dataclass(frozen=True)
class SourceBundle:
    root: str
    sources: tuple[SourceArtifact, ...]


@dataclass(frozen=True)
class VocabularyMember:
    value: str
    meaning: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class VocabularySnapshot:
    enum: str
    members: tuple[VocabularyMember, ...]
    dependency: str
    definition_digest: str = ""
    dependency_digest: str = ""
    unchecked: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedDependencies:
    artifacts: tuple[SourceArtifact, ...] = ()
    vocabularies: tuple[VocabularySnapshot, ...] = ()


@dataclass(frozen=True)
class PreparationProfile:
    version: str = "semantic-1"
    compiler_version: str = "1"
    constraint_scope: Literal["shape", "occurrence", "accepted_value", "context"] = "shape"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    location: str
    message: str
    outcome: Literal["invalid", "unsupported", "unresolved", "unchecked"] = "invalid"


class PreparationError(ValueError):
    def __init__(self, diagnostics: tuple[Diagnostic, ...]):
        self.diagnostics = diagnostics
        super().__init__("; ".join(f"{d.location}: {d.message}" for d in diagnostics))


@dataclass(frozen=True)
class PropertyDefinition:
    name: str
    iri: str
    range: str
    required: bool
    multivalued: bool
    minimum_cardinality: int | None
    maximum_cardinality: int | None
    minimum: str | None
    maximum: str | None
    pattern: str | None
    inlined: bool
    constraint_scope: str = "shape"
    inverse: str | None = None
    symmetric: bool = False
    transitive: bool = False
    case_policy: str = "preserve"
    key_role: str = "meaning"
    patterns: tuple[str, ...] = ()
    equals_string: str | None = None


@dataclass(frozen=True)
class ClassDefinition:
    name: str
    iri: str
    ancestors: tuple[str, ...]
    properties: tuple[PropertyDefinition, ...]
    identity_slots: tuple[str, ...]
    identity_groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class RegistryRow:
    kind: str
    name: str
    body: bytes


@dataclass(frozen=True)
class PreparedArtifact:
    kind: str
    content: bytes

    @property
    def digest(self) -> str:
        return sha256(self.content).hexdigest()


@dataclass(frozen=True)
class QueryDescriptor:
    class_iri: str
    properties: tuple[PropertyDefinition, ...]


@dataclass(frozen=True)
class PreparedRelease:
    release_id: str
    manifest: bytes
    definitions: tuple[ClassDefinition, ...]
    vocabularies: tuple[VocabularySnapshot, ...]
    registry_rows: tuple[RegistryRow, ...]
    queries: tuple[QueryDescriptor, ...]
    artifacts: tuple[PreparedArtifact, ...]
    required_capabilities: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    _adapters: tuple[tuple[str, TypeAdapter[BaseModel]], ...] = field(repr=False, compare=False)

    def entity_keys(
        self, class_name: str, realization: str, values: dict[str, object]
    ) -> tuple[str, ...]:
        """Canonical candidate keys for each declared unique group; not entity resolution."""
        from .identity import _meaning, canonical_bytes

        definition = next(d for d in self.definitions if d.name == class_name)
        props = {p.name: p for p in definition.properties}
        out = []
        for group in definition.identity_groups:
            pairs = []
            for name in group:
                if name not in values:
                    raise ValueError(f"missing identifying property {name}")
                value = values[name]
                if props[name].case_policy == "casefold" and isinstance(value, str):
                    value = value.casefold()
                pairs.append((name, _meaning(value)))
            out.append(
                "entity:"
                + sha256(
                    canonical_bytes([self.release_id, realization, definition.iri, pairs])
                ).hexdigest()
            )
        if not out:
            raise ValueError(f"{class_name} declares no identity group")
        return tuple(out)

    def fact_identity(
        self,
        realization: str,
        subject: str,
        predicate: str,
        object_: object,
        qualification: dict[str, object],
    ) -> str:
        """Key canonical values using the admitted Qualification key-role/case definitions."""
        from .identity import fact_key

        definition = next(d for d in self.definitions if d.name == "Qualification")
        props = {p.name: p for p in definition.properties}
        result = {}
        for name, value in qualification.items():
            if name not in props:
                raise ValueError(f"undeclared qualification {name}")
            if props[name].key_role == "provenance":
                continue
            if props[name].case_policy == "casefold" and isinstance(value, str):
                value = value.casefold()
            result[name] = value
        return fact_key(self.release_id, realization, subject, predicate, object_, result)

    def validate_json(self, class_name: str, data: str | bytes) -> BaseModel:
        for name, adapter in self._adapters:
            if name == class_name:
                return adapter.validate_json(data, strict=True)
        raise KeyError(class_name)

    def json_schema(self, class_name: str) -> dict[str, object]:
        for name, adapter in self._adapters:
            if name == class_name:
                return adapter.json_schema()
        raise KeyError(class_name)
