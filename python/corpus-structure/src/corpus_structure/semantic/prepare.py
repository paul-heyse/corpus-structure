"""Pure, explicit-input LinkML release preparation; no installed revision defaults."""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from functools import reduce
from hashlib import sha256
from importlib.metadata import version
from operator import or_
from typing import Annotated, Any, ForwardRef, Literal, Never, cast

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.linkml_model import SchemaDefinition, SchemaDefinitionName
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import (
    MISSING,
    AfterValidator,
    AwareDatetime,
    ConfigDict,
    Field,
    TypeAdapter,
    create_model,
)

from .identity import canonical_bytes
from .types import (
    SEMANTIC_COMPILER_VERSION,
    ClassDefinition,
    Diagnostic,
    PreparationError,
    PreparationProfile,
    PreparedArtifact,
    PreparedRelease,
    PropertyDefinition,
    QueryDescriptor,
    RegistryRow,
    ResolvedDependencies,
    SourceBundle,
    VocabularyMember,
    VocabularySnapshot,
)

# Runtime type factories are intentionally dynamic; normalized products remain statically typed.
_LITERAL: Any = Literal
_ANNOTATED: Any = Annotated
_TUPLE: Any = tuple

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_UNSUPPORTED = frozenset(
    {
        "rules",
        "classification_rules",
        "equals_expression",
        "equals_number",
        "any_of",
        "all_of",
        "exactly_one_of",
        "none_of",
        "structured_pattern",
        "has_member",
        "all_members",
        "some_of",
        "ifabsent",
        "union_of",
        "slot_conditions",
    }
)
_SAFE_ANNOTATIONS = frozenset({"cs:constraint_scope", "cs:key_role", "cs:case"})
_PRIMITIVES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "float": float,
    "double": float,
    "decimal": Decimal,
    "date": date,
    "datetime": AwareDatetime,
    "uri": str,
    "uriorcurie": str,
}


def _fail(code: str, location: str, message: str, outcome: Any = "invalid") -> Never:
    raise PreparationError((Diagnostic(code, location, message, outcome),))


_METADATA = {
    "name",
    "description",
    "title",
    "comments",
    "notes",
    "see_also",
    "aliases",
    "from_schema",
    "exact_mappings",
    "close_mappings",
    "broad_mappings",
    "narrow_mappings",
    "related_mappings",
    "mappings",
    "conforms_to",
    "status",
    "contributors",
    "instantiates",
}
_ALLOWED = {
    "classes": _METADATA
    | {
        "class_uri",
        "is_a",
        "mixins",
        "abstract",
        "slots",
        "attributes",
        "slot_usage",
        "unique_keys",
        "annotations",
    },
    "slots": _METADATA
    | {
        "slot_uri",
        "range",
        "domain",
        "is_a",
        "mixins",
        "required",
        "multivalued",
        "identifier",
        "inlined",
        "inlined_as_list",
        "minimum_cardinality",
        "maximum_cardinality",
        "minimum_value",
        "maximum_value",
        "pattern",
        "equals_string",
        "alias",
        "inverse",
        "symmetric",
        "transitive",
        "annotations",
    },
    "types": _METADATA | {"typeof", "base", "uri", "repr", "pattern", "annotations"},
    "enums": _METADATA
    | {
        "permissible_values",
        "reachable_from",
        "concepts",
        "include",
        "minus",
        "inherits",
        "annotations",
    },
    "permissible_values": _METADATA | {"text", "meaning", "annotations"},
    "unique_keys": _METADATA | {"unique_key_slots"},
}
_ALLOWED["attributes"] = _ALLOWED["slots"]
_ALLOWED["slot_usage"] = _ALLOWED["slots"]


def _inspect(value: Any, location: str) -> None:
    if isinstance(value, dict):
        parts = location.split("/")
        parent = parts[-2] if len(parts) > 1 else ""
        if parent in _ALLOWED:
            for key in value:
                if key not in _ALLOWED[parent]:
                    _fail("unsupported_construct", f"{location}/{key}", str(key), "unsupported")
        for key, item in value.items():
            child = f"{location}/{key}"
            if key in _UNSUPPORTED and item:
                _fail("unsupported_construct", child, f"{key} is outside semantic-1", "unsupported")
            if key == "annotations":
                if item and parent not in {"slots", "attributes", "slot_usage"}:
                    _fail(
                        "unsupported_annotation_placement",
                        child,
                        "semantic annotations are supported only on properties",
                        "unsupported",
                    )
                for annotation in item or {}:
                    if annotation not in _SAFE_ANNOTATIONS:
                        _fail("unsupported_annotation", child, str(annotation), "unsupported")
            _inspect(item, child)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _inspect(item, f"{location}/{i}")


def _view(bundle: SourceBundle) -> SchemaView:
    schemas: dict[str, SchemaDefinition] = {}
    elements: dict[tuple[str, str], str] = {}
    prefixes: dict[str, str] = {}
    if not bundle.sources or len({s.name for s in bundle.sources}) != len(bundle.sources):
        _fail("source_identity", "sources", "sources must have unique names")
    for source in bundle.sources:
        try:
            body = yaml.safe_load(source.content)
            if not isinstance(body, dict):
                _fail("schema", source.name, "schema must be a mapping")
            _inspect(body, source.name)
            schema = cast(SchemaDefinition, yaml_loader.load(body, SchemaDefinition))
        except PreparationError:
            raise
        except Exception as exc:
            _fail("schema", source.name, str(exc))
        for prefix, uri in (body.get("prefixes") or {}).items():
            uri = uri.get("prefix_reference") if isinstance(uri, dict) else uri
            if prefix in prefixes and prefixes[prefix] != uri:
                _fail("namespace_collision", source.name, f"conflicting prefix {prefix}")
            prefixes[str(prefix)] = str(uri)
        for kind in ("classes", "slots", "types", "enums"):
            for name in body.get(kind) or {}:
                if not _NAME.fullmatch(name):
                    _fail("identifier", f"{source.name}/{kind}/{name}", "unsupported element name")
                if (kind, name) in elements:
                    _fail("definition_collision", source.name, f"duplicate {kind}/{name}")
                elements[kind, name] = source.name
        # Materialize source-relative semantic identifiers before flattening imports.
        # A merged root's default_prefix must never relabel an imported declaration.
        prefix = str(schema.default_prefix or schema.id)
        for cls in cast(dict[str, Any], schema.classes or {}).values():
            if cls.class_uri is None:
                cls.class_uri = (
                    f"{prefix}:{cls.name}" if schema.default_prefix else f"{schema.id}/{cls.name}"
                )
            for attr in cast(dict[str, Any], cls.attributes or {}).values():
                if attr.range is None:
                    attr.range = schema.default_range or "string"
                if attr.slot_uri is None:
                    attr.slot_uri = (
                        f"{prefix}:{attr.name}"
                        if schema.default_prefix
                        else f"{schema.id}/{attr.name}"
                    )
        for slot in cast(dict[str, Any], schema.slots or {}).values():
            if slot.range is None:
                slot.range = schema.default_range or "string"
            if slot.slot_uri is None:
                slot.slot_uri = (
                    f"{prefix}:{slot.name}" if schema.default_prefix else f"{schema.id}/{slot.name}"
                )
        schemas[source.name] = schema
    names: set[str] = set()
    for key, schema in schemas.items():
        name = str(schema.name)
        if name in names or (name in schemas and schemas[name] is not schema):
            _fail("schema_collision", key, f"ambiguous schema name {name}")
        names.add(name)
    if bundle.root not in schemas:
        _fail("missing_root", bundle.root, "root is not supplied", "unresolved")
    # Seed every import before asking SchemaView to traverse it: no filesystem/network fallback.
    for source, schema in schemas.items():
        for imp in schema.imports or ():
            if str(imp) not in schemas:
                _fail("missing_import", source, f"import {imp} is not supplied", "unresolved")
    view = SchemaView(schemas[bundle.root])
    # Import keys can be CURIEs/URLs although SchemaView annotates them as NCNames.
    mapping = {cast(SchemaDefinitionName, k): v for k, v in schemas.items()}
    mapping[SchemaDefinitionName(str(schemas[bundle.root].name))] = schemas[bundle.root]
    view.schema_map = mapping
    view.imports_closure()
    # Generators work on the explicit, fully materialized import closure only.
    view.merge_imports()
    merged = view.schema
    assert merged is not None
    merged.imports = []
    return SchemaView(merged)


def _primitive(view: SchemaView, name: str, seen: tuple[str, ...] = ()) -> Any:
    if name in _PRIMITIVES:
        return _PRIMITIVES[name]
    if name in seen:
        _fail("type_cycle", name, "cyclic datatype inheritance")
    typ = view.get_type(name)
    if typ is None:
        _fail("unknown_range", name, "range is not a type, enum or class", "unresolved")
    base = str(typ.typeof or typ.base or "string")
    base = {"str": "string", "int": "integer", "bool": "boolean", "Decimal": "decimal"}.get(
        base, base
    )
    return _primitive(view, base, (*seen, name))


def _annotations(element: Any) -> dict[str, str]:
    raw = element.annotations or {}
    items = raw.items() if hasattr(raw, "items") else vars(raw).items()
    return {str(k): str(getattr(v, "value", v)) for k, v in items}


def _bounds(view: SchemaView, rng: str) -> tuple[list[Decimal], list[Decimal], list[str]]:
    low, high, patterns = [], [], []
    seen: set[str] = set()
    while rng not in _PRIMITIVES:
        if rng in seen:
            _fail("type_cycle", rng, "cyclic datatype inheritance")
        seen.add(rng)
        typ = view.get_type(rng)
        if typ is None:
            break
        if getattr(typ, "minimum_value", None) is not None:
            low.append(Decimal(str(typ.minimum_value)))
        if getattr(typ, "maximum_value", None) is not None:
            high.append(Decimal(str(typ.maximum_value)))
        if typ.pattern:
            patterns.append(str(typ.pattern))
        rng = str(typ.typeof or typ.base or "string")
    return low, high, patterns


def _pattern_validator(patterns: tuple[str, ...]) -> Any:
    compiled = tuple(re.compile(p) for p in patterns)

    def check(value: Any) -> Any:
        if not isinstance(value, str) or any(p.search(value) is None for p in compiled):
            raise ValueError("value violates declared patterns")
        return value

    return check


_EMPTY_DEPENDENCIES = ResolvedDependencies()
_DEFAULT_PROFILE = PreparationProfile()


def prepare_release(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies = _EMPTY_DEPENDENCIES,
    profile: PreparationProfile = _DEFAULT_PROFILE,
) -> PreparedRelease:
    """Prepare a complete interpretation. This does not persist, activate or enforce SQL rules."""
    if profile.version != "semantic-1" or profile.compiler_version != SEMANTIC_COMPILER_VERSION:
        _fail("profile", "profile", "unsupported profile", "unsupported")
    view = _view(bundle)
    supplied = {s.enum: s for s in dependencies.vocabularies}
    if len(supplied) != len(dependencies.vocabularies):
        _fail("vocabulary", "dependencies", "duplicate vocabulary snapshots")
    dependency_names = {a.name for a in dependencies.artifacts}
    if len(dependency_names) != len(dependencies.artifacts):
        _fail("dependency", "dependencies", "duplicate dependency artifacts")
    ontology_names = set(dependencies.ontology_sources)
    if (
        len(ontology_names) != len(dependencies.ontology_sources)
        or not ontology_names <= dependency_names
    ):
        _fail(
            "dependency",
            "ontology_sources",
            "ontology sources must name distinct supplied artifacts",
        )
    from .ontology import resolve_vocabularies_from_bytes

    try:
        resolved = {
            v.enum_name: v
            for v in resolve_vocabularies_from_bytes(
                view,
                {a.name: a.content for a in dependencies.artifacts if a.name in ontology_names},
            )
        }
    except Exception as exc:
        _fail("ontology", "dependencies", str(exc), "unresolved")
    diagnostics: list[Diagnostic] = []
    vocabularies: list[VocabularySnapshot] = []
    for name, enum in sorted(view.all_enums().items()):
        if enum.matches:
            _fail("unsupported_enum", name, "matches is not executable", "unsupported")
        dynamic = any(
            getattr(enum, key, None)
            for key in ("reachable_from", "concepts", "include", "minus", "inherits")
        )
        if dynamic:
            result = resolved.get(name)
            if result is None:
                _fail("missing_vocabulary", name, "resolved membership is required", "unresolved")
            members = tuple(VocabularyMember(m.value, m.meaning, m.label) for m in result.members)
            if name in supplied and supplied[name].members != members:
                _fail("vocabulary_mismatch", name, "supplied membership differs from ontology")
            snapshot = VocabularySnapshot(
                name,
                members,
                ";".join(n for n, _ in result.source_hashes),
                sha256(canonical_bytes(json_dumper.to_dict(enum))).hexdigest(),
                sha256(canonical_bytes(result.source_hashes)).hexdigest(),
                tuple(c for c in result.checks if "unchecked" in c),
            )
        else:
            snapshot = VocabularySnapshot(
                name,
                tuple(
                    VocabularyMember(
                        str(pv.text or key),
                        str(pv.meaning) if pv.meaning else None,
                        str(pv.title) if pv.title else None,
                    )
                    for key, pv in sorted(
                        cast(dict[str, Any], enum.permissible_values or {}).items()
                    )
                ),
                "local",
            )
        if len({m.value for m in snapshot.members}) != len(snapshot.members):
            _fail("vocabulary_collision", name, "duplicate membership values")
        if not dynamic and name in resolved:
            result = resolved[name]
            snapshot = VocabularySnapshot(
                name,
                tuple(VocabularyMember(m.value, m.meaning, m.label) for m in result.members),
                ";".join(n for n, _ in result.source_hashes) or "local",
                sha256(canonical_bytes(json_dumper.to_dict(enum))).hexdigest(),
                sha256(canonical_bytes(result.source_hashes)).hexdigest(),
                tuple(c for c in result.checks if "unchecked" in c),
            )
        if not snapshot.members:
            _fail("empty_enum", name, "enumeration has no permitted values")
        vocabularies.append(snapshot)
        diagnostics.extend(
            Diagnostic("unchecked_term", name, item, "unchecked") for item in snapshot.unchecked
        )
    enum_types = {s.enum: _LITERAL[tuple(m.value for m in s.members)] for s in vocabularies}
    definitions: list[ClassDefinition] = []
    classes = {str(name): cls for name, cls in view.all_classes().items()}
    models: dict[str, Any] = {}
    for name in sorted(classes):
        cls = classes[name]
        slots: list[PropertyDefinition] = []
        fields: dict[str, Any] = {}
        for slot in view.class_induced_slots(name):
            sn = str(slot.name)
            if not _NAME.fullmatch(sn):
                _fail("identifier", f"{name}/{sn}", "unsupported property name")
            rng = str(slot.range or "string")
            ann = _annotations(slot)
            if ann.get("cs:case", "preserve") not in {"preserve", "casefold"}:
                _fail("case_policy", f"{name}/{sn}", "unsupported case policy", "unsupported")
            if ann.get("cs:key_role", "meaning") not in {"meaning", "identity", "provenance"}:
                _fail("key_role", f"{name}/{sn}", "unsupported key role", "unsupported")
            scope = ann.get("cs:constraint_scope", profile.constraint_scope)
            if scope not in {"shape", "occurrence", "accepted_value", "context"}:
                _fail("constraint_scope", f"{name}/{sn}", scope)
            if scope != "shape":
                for ancestor in view.class_ancestors(name, reflexive=False):
                    for inherited in view.class_induced_slots(ancestor):
                        if str(inherited.name) != sn:
                            continue
                        parent_scope = _annotations(inherited).get(
                            "cs:constraint_scope", profile.constraint_scope
                        )
                        bounds = _bounds(view, str(inherited.range or "string"))
                        constrained = any(
                            (
                                inherited.required,
                                not inherited.multivalued,
                                inherited.identifier,
                                inherited.minimum_cardinality is not None,
                                inherited.maximum_cardinality is not None,
                                inherited.minimum_value is not None,
                                inherited.maximum_value is not None,
                                inherited.pattern,
                                any(bounds),
                            )
                        )
                        if parent_scope == "shape" and constrained:
                            _fail(
                                "constraint_scope_override",
                                f"{name}/{sn}",
                                "a subclass cannot weaken inherited shape constraints",
                                "unsupported",
                            )
            if not slot.multivalued and (
                slot.minimum_cardinality not in (None, 0, 1)
                or slot.maximum_cardinality not in (None, 1)
            ):
                _fail(
                    "scalar_cardinality",
                    f"{name}/{sn}",
                    "unsupported scalar cardinality",
                    "unsupported",
                )
            minimum_cardinality = slot.minimum_cardinality
            if slot.required or slot.identifier:
                minimum_cardinality = max(minimum_cardinality or 0, 1)
            if (
                minimum_cardinality is not None
                and slot.maximum_cardinality is not None
                and minimum_cardinality > slot.maximum_cardinality
            ):
                _fail("incompatible_cardinality", f"{name}/{sn}", "minimum exceeds maximum")
            low, high, patterns = _bounds(view, rng)
            if slot.minimum_value is not None:
                low.append(Decimal(str(slot.minimum_value)))
            if slot.maximum_value is not None:
                high.append(Decimal(str(slot.maximum_value)))
            if slot.pattern:
                patterns.append(str(slot.pattern))
            if low and high and max(low) > min(high):
                _fail("incompatible_bounds", f"{name}/{sn}", "minimum exceeds maximum")
            prop = PropertyDefinition(
                sn,
                str(view.get_uri(slot, expand=True)),
                rng,
                bool(slot.required or slot.identifier or (slot.minimum_cardinality or 0) > 0),
                bool(slot.multivalued),
                minimum_cardinality,
                slot.maximum_cardinality,
                str(max(low)) if low else None,
                str(min(high)) if high else None,
                str(slot.pattern) if slot.pattern else None,
                bool(slot.inlined or slot.inlined_as_list),
                scope,
                str(slot.inverse) if slot.inverse else None,
                bool(slot.symmetric),
                bool(slot.transitive),
                ann.get("cs:case", "preserve"),
                ann.get("cs:key_role", "meaning"),
                tuple(patterns),
                str(slot.equals_string) if slot.equals_string is not None else None,
            )
            slots.append(prop)
            if rng in classes:
                if prop.inlined and classes[rng].abstract:
                    concrete = [
                        n
                        for n in view.class_descendants(rng, reflexive=False)
                        if not classes[n].abstract
                    ]
                    if not concrete:
                        _fail("abstract_range", rng, "abstract range has no concrete members")
                    annotation = _ANNOTATED[
                        reduce(or_, (ForwardRef(n) for n in concrete)), Field(discriminator="kind")
                    ]
                else:
                    annotation = ForwardRef(rng) if prop.inlined else str
            elif rng in enum_types:
                annotation = enum_types[rng]
            else:
                annotation = _primitive(view, rng)
            if slot.equals_string is not None:
                annotation = _LITERAL[str(slot.equals_string)]
            limits: dict[str, Any] = {}
            if scope == "shape" and prop.minimum is not None:
                limits["ge"] = Decimal(prop.minimum)
            if scope == "shape" and prop.maximum is not None:
                limits["le"] = Decimal(prop.maximum)
            if scope == "shape" and prop.patterns:
                annotation = _ANNOTATED[
                    annotation, AfterValidator(_pattern_validator(prop.patterns))
                ]
                limits["json_schema_extra"] = {"allOf": [{"pattern": p} for p in prop.patterns]}
            if limits:
                annotation = _ANNOTATED[annotation, Field(**limits)]
            if prop.multivalued:
                annotation = _TUPLE[annotation, ...]
                limits = {}
                if scope == "shape" and prop.minimum_cardinality is not None:
                    limits["min_length"] = prop.minimum_cardinality
                if scope == "shape" and prop.maximum_cardinality is not None:
                    limits["max_length"] = prop.maximum_cardinality
                if limits:
                    annotation = _ANNOTATED[annotation, Field(**limits)]
            fields[sn] = (
                annotation,
                Field(
                    default=...
                    if (slot.identifier or (scope == "shape" and prop.required))
                    else MISSING,
                    alias=str(slot.alias or sn),
                ),
            )
        keys = tuple(str(s.name) for s in view.class_induced_slots(name) if s.identifier)
        groups = ((keys,) if keys else ()) + tuple(
            tuple(str(x) for x in unique.unique_key_slots)
            for _, unique in sorted(cast(dict[str, Any], cls.unique_keys or {}).items())
        )
        for group in groups:
            if not group or any(k not in fields for k in group):
                _fail("identity_slots", name, "identity references missing properties")
        definitions.append(
            ClassDefinition(
                name,
                str(view.get_uri(cls, expand=True)),
                tuple(sorted(str(x) for x in view.class_ancestors(name, reflexive=False))),
                tuple(slots),
                keys,
                groups,
                bool(cls.abstract),
            )
        )
        try:
            models[name] = create_model(
                name, __config__=ConfigDict(frozen=True, extra="forbid", strict=True), **fields
            )
        except Exception as exc:
            _fail("boundary", name, str(exc))
    try:
        for model in models.values():
            model.model_rebuild(_types_namespace=models)
    except Exception as exc:
        _fail("boundary", "models", str(exc))
    manifest = canonical_bytes(
        {
            "root": bundle.root,
            "profile": asdict(profile),
            "libraries": {
                name: version(name)
                for name in (
                    "linkml",
                    "linkml-runtime",
                    "pydantic",
                    "rdflib",
                    "pyshacl",
                    "oaklib",
                    "linkml-term-validator",
                    "valuesets",
                )
            },
            "sources": sorted((s.name, s.digest) for s in bundle.sources),
            "dependencies": sorted((a.name, a.digest) for a in dependencies.artifacts),
            "ontology_sources": sorted(dependencies.ontology_sources),
            "vocabularies": [asdict(v) for v in vocabularies],
        }
    )
    release_id = "release:" + sha256(manifest).hexdigest()
    artifacts = [
        PreparedArtifact("definitions.json", canonical_bytes([asdict(d) for d in definitions]))
    ]

    def boundary(name: str, model: Any) -> Any:
        if classes[name].abstract:
            concrete = [
                models[n]
                for n in view.class_descendants(name, reflexive=False)
                if not classes[n].abstract
            ]
            if not concrete:
                _fail("abstract_range", name, "abstract boundary has no concrete members")
            try:
                return TypeAdapter(_ANNOTATED[reduce(or_, concrete), Field(discriminator="kind")])
            except Exception as exc:
                _fail("abstract_discriminator", name, str(exc), "unsupported")
        return TypeAdapter(model)

    adapters = tuple((name, boundary(name, model)) for name, model in sorted(models.items()))
    for name, adapter in adapters:
        artifacts.append(
            PreparedArtifact(f"json_schema/{name}", canonical_bytes(adapter.json_schema()))
        )
    from .ontology import build_graph_artifacts

    for kind, content in sorted(
        build_graph_artifacts(view, default_constraint_scope=profile.constraint_scope).items()
    ):
        artifacts.append(PreparedArtifact(kind, content))
    rows = tuple(RegistryRow("class", d.name, canonical_bytes(asdict(d))) for d in definitions)
    rows += tuple(
        RegistryRow("type", name, canonical_bytes(json_dumper.to_dict(typ)))
        for name, typ in sorted(view.all_types().items())
    )
    rows += tuple(
        RegistryRow("property", f"{d.name}/{p.name}", canonical_bytes(asdict(p)))
        for d in definitions
        for p in d.properties
    )
    rows += tuple(
        RegistryRow(
            "constraint",
            f"{d.name}/{p.name}",
            canonical_bytes(
                {
                    "scope": p.constraint_scope,
                    "required": p.required,
                    "minimum_cardinality": p.minimum_cardinality,
                    "maximum_cardinality": p.maximum_cardinality,
                    "minimum": p.minimum,
                    "maximum": p.maximum,
                    "patterns": p.patterns,
                }
            ),
        )
        for d in definitions
        for p in d.properties
    )
    rows += tuple(
        RegistryRow("identity", d.name, canonical_bytes({"groups": d.identity_groups}))
        for d in definitions
    )
    rows += tuple(RegistryRow("enum", v.enum, canonical_bytes(asdict(v))) for v in vocabularies)
    return PreparedRelease(
        release_id,
        manifest,
        tuple(definitions),
        tuple(vocabularies),
        rows,
        tuple(QueryDescriptor(d.iri, d.properties) for d in definitions),
        tuple(artifacts),
        ("semantic_registry", "scoped_publication", "typed_values"),
        tuple(diagnostics),
        adapters,
    )
