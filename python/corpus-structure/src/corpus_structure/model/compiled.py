"""Closed, content-addressed model composition shared by every projection.

Acquisition supplies named bytes. Composition never acquires an import from disk
or the network. Mutable library schemas remain private to a projection.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from struct import pack
from threading import RLock
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, TypeVar, cast

import yaml
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader

if TYPE_CHECKING:
    from sqlalchemy import MetaData
    from sqlalchemy.types import TypeEngine

T = TypeVar("T")


class SchemaYamlLoader(DupCheckYamlLoader):
    """Duplicate-safe schema loading with ordinary empty sequence members."""

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, yaml.SafeLoader.construct_yaml_seq
        )


def annotation_values(element: Any) -> dict[str, Any]:
    """Decode annotation scalars once without turning booleans into strings."""
    raw = getattr(element, "annotations", None) or {}
    items = raw.items() if hasattr(raw, "items") else vars(raw).items()
    result: dict[str, Any] = {}
    for name, annotation in items:
        value = getattr(annotation, "value", annotation)
        result[str(name)] = (
            deepcopy(value) if isinstance(value, bool | int | list | dict) else str(value)
        )
    return result


def boolean_annotation(element: Any, name: str, default: bool = False) -> bool:
    return annotation_boolean(annotation_values(element).get(name, default), name)


def annotation_boolean(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError(f"{name}: expected a boolean annotation")


def private_schema_view(schema: SchemaDefinition) -> SchemaView:
    """An isolated derived schema, without a second import-resolution route."""
    if schema.imports:
        raise ValueError("derived schema requires an already closed import closure")
    return SchemaView(deepcopy(schema))


def _source_name(name: str, supplied: Mapping[str, Any]) -> str:
    if name in supplied:
        return name
    if name + ".yaml" in supplied:
        return name + ".yaml"
    raise ValueError(f"model import is not supplied: {name}")


def _compose(
    documents: Mapping[str, Mapping[str, Any]],
    root: str,
    *,
    merge: bool,
    normalize: bool,
) -> SchemaView:
    schemas: dict[str, SchemaDefinition] = {}
    importmap: dict[str, str | dict[str, Any]] = {}

    def visit(name: str) -> SchemaDefinition:
        name = _source_name(name, documents)
        if name in schemas:
            return schemas[name]
        document = deepcopy(dict(documents[name]))
        if normalize:
            prefix = str(document.get("default_prefix") or document["id"])

            def uri(local: str) -> str:
                return (
                    f"{prefix}:{local}"
                    if document.get("default_prefix")
                    else f"{document['id']}/{local}"
                )

            for name_, cls in (document.get("classes") or {}).items():
                if cls is None:
                    cls = document["classes"][name_] = {}
                cls.setdefault("class_uri", uri(name_))
                for slot_name, slot in (cls.get("attributes") or {}).items():
                    if slot is None:
                        slot = cls["attributes"][slot_name] = {}
                    slot.setdefault("range", document.get("default_range") or "string")
                    slot.setdefault("slot_uri", uri(slot_name))
            for name_, enum in (document.get("enums") or {}).items():
                if enum is None:
                    enum = document["enums"][name_] = {}
                enum.setdefault("enum_uri", uri(name_))
            for name_, slot in (document.get("slots") or {}).items():
                if slot is None:
                    slot = document["slots"][name_] = {}
                slot.setdefault("range", document.get("default_range") or "string")
                slot.setdefault("slot_uri", uri(name_))
        schema = yaml_loader.load(document, SchemaDefinition)
        if not isinstance(schema, SchemaDefinition):
            raise ValueError(f"model source is not a SchemaDefinition: {name}")
        schemas[name] = schema
        # Keep the captured mapping. LinkML's JSON dumper deliberately removes
        # empty values, including meaningful structured annotation lists.
        importmap[name.removesuffix(".yaml")] = document
        for imported in schema.imports or ():
            target_name = _source_name(str(imported), documents)
            visit(target_name)
            importmap[str(imported)] = importmap[target_name.removesuffix(".yaml")]
        return schema

    schema = visit(root)
    view = SchemaView(schema, importmap=importmap)
    if merge:
        view.imports_closure()
        view.merge_imports()
        merged = view.schema
        if merged is None:
            raise ValueError("merged model is unavailable")
        merged.imports = []
        return SchemaView(merged)
    return view


@dataclass(frozen=True)
class _Failure:
    error: Exception


@dataclass(frozen=True)
class FieldKind:
    python: str
    postgres: str
    sqlalchemy: TypeEngine[Any]

    @property
    def expression(self) -> str:
        return repr(self.sqlalchemy)


@dataclass(frozen=True)
class CompanionColumns:
    group: str
    distinct: str | None
    provenance: tuple[str, ...]
    values: tuple[str, ...]


class CompiledModel:
    """One source capture with lazy, independently identified projections."""

    def __init__(self, sources: tuple[tuple[str, bytes], ...]):
        self._sources: Mapping[str, bytes] = MappingProxyType(dict(sources))
        digest = sha256(b"corpus-model-sources-1\0")
        for name, content in sources:
            encoded = name.encode()
            digest.update(pack(">Q", len(encoded)))
            digest.update(encoded)
            digest.update(pack(">Q", len(content)))
            digest.update(content)
        self._identity = "model:" + digest.hexdigest()
        self._projections: dict[Hashable, Any] = {}
        self._lock = RLock()

    @property
    def identity(self) -> str:
        return self._identity

    @property
    def sources(self) -> Mapping[str, bytes]:
        return self._sources

    def projection(self, key: Hashable, build: Callable[[], T]) -> T:
        with self._lock:
            if key not in self._projections:
                try:
                    self._projections[key] = build()
                except Exception as error:
                    self._projections[key] = _Failure(error)
            result = self._projections[key]
            if isinstance(result, _Failure):
                raise result.error
            return cast(T, result)

    def _documents(self) -> Mapping[str, Mapping[str, Any]]:
        def build():
            result: dict[str, Mapping[str, Any]] = {}
            for name, content in self.sources.items():
                if Path(name).suffix not in {"", ".yaml", ".json"}:
                    continue
                value = yaml.load(content, Loader=SchemaYamlLoader)
                if not isinstance(value, dict):
                    # Captures also retain catalogs and instance data. They are
                    # dependencies, not schema roots or import candidates.
                    continue
                result[name] = value
            return MappingProxyType(result)

        return self.projection(("documents",), build)

    def _view(self, root: str, *, merge: bool, normalize: bool) -> SchemaView:
        return self.projection(
            ("view", root, merge, normalize),
            lambda: _compose(self._documents(), root, merge=merge, normalize=normalize),
        )

    def view(self, root: str, *, merge: bool = True, normalize: bool = False) -> SchemaView:
        """Give a consumer isolated mutable library state over held composition."""
        view = self._view(root, merge=merge, normalize=normalize)
        if view.schema is None:
            raise ValueError("compiled schema is unavailable")
        if merge:
            return private_schema_view(view.schema)
        return SchemaView(deepcopy(view.schema), importmap=deepcopy(dict(view.importmap or {})))

    def private_view(self, root: str, *, normalize: bool = False) -> SchemaView:
        return self.view(root, normalize=normalize)

    def physical(self, root: str = "physical.yaml", *, target: str = "semantic") -> MetaData:
        def build():
            from corpus_structure.schema.declarations import ModelError
            from corpus_structure.schema.physical import (
                physical_model_documents,
                physical_source_closure,
                physical_sources_id,
            )
            from corpus_structure.schema.relational import compile_metadata

            sources = physical_source_closure(root, self.sources.get)
            documents = physical_model_documents(sources, root=root)
            types = yaml.load(self.sources["linkml:types"], Loader=DupCheckYamlLoader)
            if not isinstance(types, dict) or types.get("imports"):
                raise ModelError(["unsupported retained LinkML types"])
            documents["linkml:types"] = types
            try:
                view = _compose(documents, root, merge=False, normalize=False)
                metadata = compile_metadata(view, target=target)
            except ModelError:
                raise
            except (ValueError, TypeError, KeyError) as error:
                raise ModelError([f"invalid physical declaration: {error}"]) from error
            metadata.info["physical_model_id"] = physical_sources_id(sources)
            metadata.info["physical_sources"] = sources
            metadata.info["physical_linkml_types"] = self.sources["linkml:types"]
            return metadata

        return self.projection(("physical", root, target), build)

    def field_kinds(self) -> Mapping[str, FieldKind]:
        def build():
            from corpus_structure.schema.relational import physical_range_type

            view = self.private_view("native-field-kinds.yaml")
            result: dict[str, FieldKind] = {}
            for name, definition in view.all_types().items():
                python = definition.base or ""
                postgres = annotation_values(definition).get("ph:sql_type")
                if (
                    not python.isidentifier()
                    or not isinstance(postgres, str)
                    or not postgres.isidentifier()
                ):
                    raise ValueError(f"{name}: field kind requires Python and PostgreSQL types")
                result[str(name)] = FieldKind(
                    python, postgres, physical_range_type(view, str(name))
                )
            return MappingProxyType(result)

        return self.projection(("field-kinds",), build)

    def companion_columns(self) -> Mapping[str, CompanionColumns]:
        def build():
            view = self.private_view("companion-projections.yaml")
            result: dict[str, CompanionColumns] = {}
            for name, cls in view.all_classes().items():
                declared = annotation_values(cls)
                family = declared.get("cp:family")
                if family is None:
                    continue
                slots = {str(s.name): annotation_values(s) for s in view.class_induced_slots(name)}
                group = declared.get("cp:group_by")
                distinct = declared.get("cp:inventory_distinct")
                if group not in slots or (distinct is not None and distinct not in slots):
                    raise ValueError(f"{name}: inventory columns must name declared fields")
                result[str(family)] = CompanionColumns(
                    group,
                    distinct,
                    tuple(n for n, a in slots.items() if a.get("cp:role") == "provenance"),
                    tuple(n for n, a in slots.items() if a.get("cp:role") != "provenance"),
                )
            return MappingProxyType(result)

        return self.projection(("companion-columns",), build)


@lru_cache(maxsize=4)
def _compiled_model(sources: tuple[tuple[str, bytes], ...]) -> CompiledModel:
    return CompiledModel(sources)


_capture_lock = RLock()


def compiled_model(sources: Mapping[str, bytes]) -> CompiledModel:
    if any(
        not isinstance(name, str) or not isinstance(body, bytes) for name, body in sources.items()
    ):
        raise TypeError("model capture requires named bytes")
    with _capture_lock:
        return _compiled_model(tuple(sorted(sources.items())))


@lru_cache(maxsize=1)
def running_model() -> CompiledModel:
    """Acquire the running package once; UDM-13 owns next-request observation."""
    from corpus_structure.schema.physical import linkml_types_source

    root = Path(__file__).parent / "semantic"
    sources = {path.name: path.read_bytes() for path in sorted(root.glob("*.yaml"))}
    sources["linkml:types"] = linkml_types_source()
    return compiled_model(sources)


def field_kinds() -> Mapping[str, FieldKind]:
    return running_model().field_kinds()
