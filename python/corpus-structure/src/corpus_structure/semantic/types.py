"""Explicit immutable inputs and products of semantic release preparation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from hashlib import sha256
from threading import RLock
from types import MappingProxyType
from typing import Any, Literal, get_args

from pydantic import BaseModel, TypeAdapter

from .refusals import SemanticRefusal

SEMANTIC_COMPILER_VERSION: Literal["16"] = "16"
READABLE_COMPILER_VERSIONS = frozenset({"14", "15", "16"})
BOUNDARY_ABI_VERSION = "12"


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
    contract_id: str | None = None
    consumer: str | None = None
    expected: str | None = None
    actual: str | None = None
    remedy: str | None = None


class PreparationError(SemanticRefusal):
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



@lru_cache(maxsize=512)
def _enum_members(vocabularies, registry_rows, name: str, subset: str | None = None) -> frozenset[str]:
    """Shared effective closed membership and authored contextual metadata resolution."""
    import json

    vocabulary = next(v for v in vocabularies if v.enum == name)
    if subset is None:
        return frozenset(m.value for m in vocabulary.members)
    definitions = {
        r.name: json.loads(r.body) for r in registry_rows if r.kind == "enum_definition"
    }

    def properties(
        expression: dict[str, Any], stack: tuple[str, ...]
    ) -> dict[str, dict[str, Any]]:
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
    return frozenset(
        m.value
        for m in vocabulary.members
        if subset in members.get(m.value, {}).get("in_subset", ())
    )



@dataclass(frozen=True)
class SchemaPreview:
    """Names and closed vocabulary for authoring inputs, without release admission artifacts."""

    classes: tuple[ClassPreview, ...]
    vocabularies: tuple[VocabularySnapshot, ...]
    diagnostics: tuple[Diagnostic, ...]
    enum_definitions: tuple[RegistryRow, ...] = ()

    def enum_members(self, name: str, *, subset: str | None = None) -> frozenset[str]:
        return _enum_members(self.vocabularies, self.enum_definitions, name, subset)


class _AdapterLookup(Mapping[str, TypeAdapter[BaseModel]]):
    def __init__(self, release: PreparedRelease):
        self._release = release

    def __getitem__(self, name: str) -> TypeAdapter[BaseModel]:
        return self._release.adapter(name)

    def __iter__(self):
        return iter(self._release.index.definitions)

    def __len__(self) -> int:
        return len(self._release.definitions)


@dataclass(frozen=True)
class ReleaseIndex:
    """Read-only lookup acceleration; never part of release identity."""

    definitions: Mapping[str, ClassDefinition]
    by_iri: Mapping[str, ClassDefinition]
    properties: Mapping[tuple[str, str], PropertyDefinition]
    properties_by_class: Mapping[str, Mapping[str, PropertyDefinition]]
    adapters: Mapping[str, TypeAdapter[BaseModel]]
    property_roles: Mapping[tuple[str, str], frozenset[str]]


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
    _adapter_loader: Callable[[str], TypeAdapter[BaseModel]] | None = field(
        default=None, repr=False, compare=False
    )
    _adapter_lock: Any = field(default_factory=RLock, repr=False, compare=False)
    _loaded_adapters: dict[str, TypeAdapter[BaseModel]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _boundary_models: dict[str, type[BaseModel]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _property_adapters: dict[tuple[str, str, bool], TypeAdapter[Any]] = field(
        default_factory=dict, repr=False, compare=False, init=False
    )
    _enum_memberships: dict[tuple[str, str | None], frozenset[str]] = field(
        default_factory=dict, repr=False, compare=False, init=False
    )
    _result_adapters: dict[tuple[str, str, str | None], TypeAdapter[Any]] = field(
        default_factory=dict, repr=False, compare=False, init=False
    )

    _relational_preparations: dict[str, Any] = field(
        default_factory=dict, repr=False, compare=False, init=False
    )

    def adapter(self, class_name: str) -> TypeAdapter[BaseModel]:
        if self._adapter_loader is None:
            return self.index.adapters[class_name]
        with self._adapter_lock:
            if class_name not in self._loaded_adapters:
                self._loaded_adapters[class_name] = self._adapter_loader(class_name)
            return self._loaded_adapters[class_name]

    @cached_property
    def index(self) -> ReleaseIndex:
        from .property_roles import property_roles

        return ReleaseIndex(
            MappingProxyType({d.name: d for d in self.definitions}),
            MappingProxyType({d.iri: d for d in self.definitions}),
            MappingProxyType({(d.name, p.name): p for d in self.definitions for p in d.properties}),
            MappingProxyType(
                {
                    d.name: MappingProxyType({p.name: p for p in d.properties})
                    for d in self.definitions
                }
            ),
            _AdapterLookup(self)
            if self._adapter_loader is not None
            else MappingProxyType(dict(self._adapters)),
            property_roles(self),
        )

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
        key = (name, subset)
        if key not in self._enum_memberships:
            self._enum_memberships[key] = _enum_members(self.vocabularies, self.registry_rows, name, subset)
        return self._enum_memberships[key]

    def source_establishments(self) -> frozenset[str]:
        """Source admission is narrower than general occurrence storage."""
        return self.enum_members("Establishment", subset="source_admissible")

    def reference_splits(self) -> frozenset[str]:
        return self.enum_members("ReferenceSplit", subset="executable")

    def member_has_behavior(self, vocabulary: str, member: str | None, behavior: str) -> bool:
        return member is not None and member in self.enum_members(vocabulary, subset=behavior)

    def display_properties(self, class_id: str) -> tuple[PropertyDefinition, ...]:
        """Ordered released display bindings; names carry no display semantics."""
        import json

        definition = self.index.definitions.get(class_id) or self.index.by_iri[class_id]
        metadata = {
            body["property"]: body
            for row in self.registry_rows
            if row.kind == "operation_property"
            for body in (json.loads(row.body),)
            if body["class"] == definition.name
        }
        return tuple(sorted(
            (prop for prop in definition.properties
             if "display" in self.index.property_roles.get((definition.iri, prop.iri), ())),
            key=lambda prop: (int(metadata[prop.iri].get("cs:display_order", "0")), prop.iri),
        ))

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

        definition = self.index.definitions[class_name]
        props = self.index.properties_by_class[class_name]
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
                    from .unicode_identity import identity_casefold
                    value = identity_casefold(value)
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
        definition = self.index.definitions.get(class_name)
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
        props = self.index.properties_by_class[definition.name]
        result = {}
        for name, value in qualification.items():
            if name not in props:
                raise ValueError(f"undeclared qualification {name}")
            if props[name].key_role == "provenance":
                continue
            if props[name].case_policy == "casefold" and isinstance(value, str):
                from .unicode_identity import identity_casefold
                value = identity_casefold(value)
            result[name] = value
        return fact_key(self.release_id, realization, subject, predicate, object_, result)

    def property_adapter(
        self, class_name: str, property_name: str, *, item: bool = False
    ) -> TypeAdapter[Any]:
        """Strict output boundary derived from the prepared field, including its constraints."""
        key = (class_name, property_name, item)
        with self._adapter_lock:
            if key in self._property_adapters:
                return self._property_adapters[key]
            self.adapter(class_name)
            model = self._boundary_models.get(class_name)
            if model is None:
                raise KeyError(f"prepared boundary model unavailable: {class_name}")
            field = model.model_fields[property_name]
            annotation = field.rebuild_annotation()
            if item:
                from typing import get_origin

                annotation = get_args(field.annotation)[
                    -1 if get_origin(field.annotation) is dict else 0
                ]
            adapter = TypeAdapter(annotation)
            # Complete deferred schemas while holding the same registry lock.
            adapter.rebuild()
            self._property_adapters[key] = adapter
            return adapter

    def validate_python(self, class_name: str, data: object) -> BaseModel:
        """Validate reconstructed native values without JSON's numeric/date conversions."""
        return self.adapter(class_name).validate_python(
            data, strict=True, context={"validation_purpose": "structural"}
        )

    def validate_json(self, class_name: str, data: str | bytes) -> BaseModel:
        return self.adapter(class_name).validate_json(
            data, strict=True, context={"validation_purpose": "structural"}
        )

    def validate_accepted_python(self, class_name: str, data: object) -> BaseModel:
        """Validate the accepted projection; native publication still enforces shared state."""
        return self.adapter(class_name).validate_python(
            data, strict=True, context={"validation_purpose": "accepted_value"}
        )

    def validate_accepted_json(self, class_name: str, data: str | bytes) -> BaseModel:
        return self.adapter(class_name).validate_json(
            data, strict=True, context={"validation_purpose": "accepted_value"}
        )

    def json_schema(
        self, class_name: str, *, mode: Literal["validation", "serialization"] = "validation"
    ) -> dict[str, object]:
        return self.adapter(class_name).json_schema(mode=mode)
