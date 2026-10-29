"""Explicit immutable inputs and products of semantic release preparation."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Literal, get_args

from pydantic import BaseModel, TypeAdapter

SEMANTIC_COMPILER_VERSION = "10"  # protected references and selected completed results are release-bound


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
    ontology_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreparationProfile:
    version: str = "semantic-1"
    compiler_version: str = SEMANTIC_COMPILER_VERSION
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
    collection_key: str | None = None
    reference_role: str | None = None


@dataclass(frozen=True)
class ClassDefinition:
    name: str
    iri: str
    ancestors: tuple[str, ...]
    properties: tuple[PropertyDefinition, ...]
    identity_slots: tuple[str, ...]
    identity_groups: tuple[tuple[str, ...], ...] = ()
    abstract: bool = False


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
class PropertyPreview:
    name: str
    iri: str
    range: str


@dataclass(frozen=True)
class ClassPreview:
    name: str
    iri: str
    ancestors: tuple[str, ...]
    properties: tuple[PropertyPreview, ...]
    abstract: bool


@dataclass(frozen=True)
class SchemaPreview:
    """Names and closed vocabulary for authoring inputs, without release admission artifacts."""

    classes: tuple[ClassPreview, ...]
    vocabularies: tuple[VocabularySnapshot, ...]
    diagnostics: tuple[Diagnostic, ...]

    def enum_members(self, name: str) -> frozenset[str]:
        vocabulary = next(v for v in self.vocabularies if v.enum == name)
        return frozenset(m.value for m in vocabulary.members)


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
    execution_model_id: str | None = None

    def expand_name(self, name: str) -> str:
        """Resolve only prefixes archived with this release; never installed namespaces."""
        import json

        if name.startswith(("http://", "https://", "urn:")):
            return name
        prefix, separator, local = name.partition(":")
        if separator:
            for row in self.registry_rows:
                if row.kind == "prefix" and row.name == prefix:
                    return str(json.loads(row.body)["uri"]) + local
        raise KeyError(f"unresolved release name {name}")

    def enum_members(self, name: str, *, subset: str | None = None) -> frozenset[str]:
        """Closed membership and authored member properties share release authority."""
        import json

        vocabulary = next(v for v in self.vocabularies if v.enum == name)
        if subset is None:
            return frozenset(m.value for m in vocabulary.members)
        definitions = {r.name: json.loads(r.body) for r in self.registry_rows
                       if r.kind == "enum_definition"}

        def properties(expression: dict[str, Any], stack: tuple[str, ...]) -> dict[str, dict[str, Any]]:
            # Membership has already been resolved by the ontology/value-set compiler. This
            # resolves authored member metadata only, in the same seed/override order.
            result: dict[str, dict[str, Any]] = {}
            for parent in expression.get("inherits") or ():
                if parent in stack:
                    raise ValueError("cyclic archived enum metadata")
                result.update(properties(definitions[parent], (*stack, parent)))
            result.update(expression.get("permissible_values") or {})
            for included in expression.get("include") or ():
                result.update(properties(included, stack))
            return result

        members = properties(definitions[name], (name,))
        return frozenset(m.value for m in vocabulary.members
                         if subset in members.get(m.value, {}).get("in_subset", ()))

    def entity_keys(
        self,
        class_name: str,
        realization: str,
        values: dict[str, object],
        *,
        include_identifier: bool = True,
    ) -> tuple[str, ...]:
        """Canonical candidate keys for each declared unique group; not entity resolution."""
        from .identity import _meaning, canonical_bytes

        definition = next(d for d in self.definitions if d.name == class_name)
        props = {p.name: p for p in definition.properties}
        out = []
        for group in definition.identity_groups:
            if not include_identifier and group == definition.identity_slots:
                continue
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

    def qualification_definition(self, class_name: str = "Qualification") -> ClassDefinition:
        """Resolve an explicitly named qualification type; never guess from submitted fields."""
        definition = next((d for d in self.definitions if d.name == class_name), None)
        if definition is None or not (
            definition.name == "Qualification" or "Qualification" in definition.ancestors
        ):
            raise ValueError(f"{class_name!r} is not an admitted Qualification class")
        return definition

    def fact_identity(
        self,
        realization: str,
        subject: str,
        predicate: str,
        object_: object,
        qualification: dict[str, object],
        *,
        qualification_class: str = "Qualification",
    ) -> str:
        """Key canonical values using the admitted Qualification key-role/case definitions."""
        from .identity import fact_key

        definition = self.qualification_definition(qualification_class)
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

    def property_adapter(
        self, class_name: str, property_name: str, *, item: bool = False
    ) -> TypeAdapter[Any]:
        """Strict output boundary derived from the prepared field, including its constraints."""
        for name, adapter in self._adapters:
            if name == class_name:
                model = adapter._type
                if not isinstance(model, type) or not issubclass(model, BaseModel):
                    raise TypeError("prepared class adapter has no model")
                field = model.model_fields[property_name]
                annotation = field.rebuild_annotation()
                if item:
                    from typing import get_origin

                    annotation = get_args(field.annotation)[
                        -1 if get_origin(field.annotation) is dict else 0
                    ]
                return TypeAdapter(annotation)
        raise KeyError(class_name)

    def validate_python(self, class_name: str, data: object) -> BaseModel:
        """Validate reconstructed native values without JSON's numeric/date conversions."""
        for name, adapter in self._adapters:
            if name == class_name:
                return adapter.validate_python(data, strict=True)
        raise KeyError(class_name)

    def validate_json(self, class_name: str, data: str | bytes) -> BaseModel:
        for name, adapter in self._adapters:
            if name == class_name:
                return adapter.validate_json(data, strict=True)
        raise KeyError(class_name)

    def json_schema(
        self, class_name: str, *, mode: Literal["validation", "serialization"] = "validation"
    ) -> dict[str, object]:
        for name, adapter in self._adapters:
            if name == class_name:
                return adapter.json_schema(mode=mode)
        raise KeyError(class_name)
