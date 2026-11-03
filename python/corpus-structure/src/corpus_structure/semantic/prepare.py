"""Pure, explicit-input LinkML release preparation; no installed revision defaults."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
from typing import Any, Never, cast

import yaml
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.linkml_model import SchemaDefinition
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from pydantic import AwareDatetime

from .conditional_rules import (
    CONDITIONAL_RULE_OPTIONS,
    compile_conditional_rules,
    compile_native_conditionals,
    inspect_rule_declarations,
)
from .determinants import ANALYSIS_LIBRARIES, determinant_version, release_library_versions
from .determinants import BYTE_LIBRARIES as _LIBRARIES
from .identity import canonical_bytes
from .types import (
    BOUNDARY_ABI_VERSION,
    SEMANTIC_COMPILER_VERSION,
    ClassDefinition,
    ClassPreview,
    Diagnostic,
    PreparationError,
    PreparationProfile,
    PreparedArtifact,
    PreparedRelease,
    PropertyDefinition,
    PropertyPreview,
    QueryDescriptor,
    RegistryRow,
    ResolvedDependencies,
    SchemaPreview,
    SourceBundle,
    VocabularyMember,
    VocabularySnapshot,
)

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
_SAFE_ANNOTATIONS = frozenset(
    {
        "cs:constraint_scope",
        "cs:key_role",
        "cs:case",
        "cs:role",
        "cs:qualifiers",
        "cs:identity_qualifiers",
        "cs:param_map",
        "cs:extract",
        "cs:functional",
        "cs:scope",
        "cs:reference_role",
    }
)
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
        "value_presence",
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
        "in_subset",
        "inverse",
        "symmetric",
        "transitive",
        "annotations",
    },
    "types": _METADATA | {"typeof", "base", "uri", "repr", "pattern", "annotations"},
    "enums": _METADATA
    | {
        "enum_uri",
        "permissible_values",
        "reachable_from",
        "concepts",
        "include",
        "minus",
        "inherits",
        "annotations",
    },
    "permissible_values": _METADATA | {"text", "meaning", "annotations", "in_subset"},
    "unique_keys": _METADATA | {"unique_key_slots"},
}
_ALLOWED["attributes"] = _ALLOWED["slots"]
_ALLOWED["slot_usage"] = _ALLOWED["slots"]


def _inspect(value: Any, location: str, profile: PreparationProfile | None = None) -> None:
    if isinstance(value, dict):
        parts = location.split("/")
        parent = parts[-2] if len(parts) > 1 else ""
        if parent in _ALLOWED:
            for key in value:
                if key not in _ALLOWED[parent] and not (
                    key == "rules"
                    and parent == "classes"
                    and profile is not None
                    and profile.version == "semantic-2"
                ):
                    _fail("unsupported_construct", f"{location}/{key}", str(key), "unsupported")
        for key, item in value.items():
            child = f"{location}/{key}"
            if (
                key == "rules"
                and parent == "classes"
                and profile is not None
                and profile.version == "semantic-2"
            ):
                inspect_rule_declarations(item, child)
                continue
            if key in _UNSUPPORTED and item:
                _fail("unsupported_construct", child, f"{key} is outside semantic-1", "unsupported")
            if key == "annotations":
                if item and parent not in {"slots", "attributes", "slot_usage", "classes"}:
                    _fail(
                        "unsupported_annotation_placement",
                        child,
                        "semantic annotations are supported only on properties",
                        "unsupported",
                    )
                for annotation in item or {}:
                    if parent == "classes" and annotation not in {
                        "cs:scope",
                        "cs:case",
                        "cs:extract",
                    }:
                        _fail(
                            "unsupported_annotation_placement",
                            child,
                            str(annotation),
                            "unsupported",
                        )
                    if annotation not in _SAFE_ANNOTATIONS and annotation != "cp:source":
                        _fail("unsupported_annotation", child, str(annotation), "unsupported")
            _inspect(item, child, profile)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _inspect(item, f"{location}/{i}", profile)


class _SchemaYamlLoader(DupCheckYamlLoader):
    """LinkML duplicate checks with standard YAML empty-sequence-member semantics."""

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        # LinkML's data loader additionally rejects empty sequence members. Schema examples
        # and unsupported-construct diagnostics must retain ordinary SafeLoader sequences.
        self.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG, yaml.SafeLoader.construct_yaml_seq
        )


def _view(bundle: SourceBundle, profile: PreparationProfile | None = None) -> SchemaView:
    schemas: dict[str, SchemaDefinition] = {}
    elements: dict[tuple[str, str], str] = {}
    prefixes: dict[str, str] = {}
    if not bundle.sources or len({s.name for s in bundle.sources}) != len(bundle.sources):
        _fail("source_identity", "sources", "sources must have unique names")
    for source in bundle.sources:
        try:
            body = yaml.load(source.content, Loader=_SchemaYamlLoader)
            if not isinstance(body, dict):
                _fail("schema", source.name, "schema must be a mapping")
            _inspect(body, source.name, profile)
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
        for enum in cast(dict[str, Any], schema.enums or {}).values():
            if enum.enum_uri is None:
                enum.enum_uri = (
                    f"{prefix}:{enum.name}" if schema.default_prefix else f"{schema.id}/{enum.name}"
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
    from linkml_runtime.dumpers import json_dumper

    view = SchemaView(
        schemas[bundle.root],
        importmap={
            key: cast(dict[str, Any], json_dumper.to_dict(value)) for key, value in schemas.items()
        },
    )
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
    return {str(k): str(getattr(v, "value", v)) for k, v in items if str(k) in _SAFE_ANNOTATIONS}


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
            patterns.append(typ.pattern)
        rng = str(typ.typeof or typ.base or "string")
    return low, high, patterns


_EMPTY_DEPENDENCIES = ResolvedDependencies()
_DEFAULT_PROFILE = PreparationProfile()


def _compiler_stack() -> tuple[tuple[str, str], ...]:
    # Read the current stack at the cache boundary, not once at module import.
    return (
        ("compiler", SEMANTIC_COMPILER_VERSION),
        ("python", sys.version),
        *((name, determinant_version(name)) for name in _LIBRARIES),
    )


def _view_and_vocabularies(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies,
    profile: PreparationProfile | None = None,
) -> tuple[SchemaView, tuple[VocabularySnapshot, ...], tuple[Diagnostic, ...]]:
    view = _view(bundle, profile)
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
    return view, tuple(vocabularies), tuple(diagnostics)


def preview_schema(
    bundle: SourceBundle, dependencies: ResolvedDependencies = _EMPTY_DEPENDENCIES
) -> SchemaPreview:
    """Resolve exact names/vocabulary without generating models, graphs or release artifacts."""
    view, vocabularies, diagnostics = _view_and_vocabularies(bundle, dependencies)
    classes = tuple(
        ClassPreview(
            str(name),
            view.get_uri(cls, expand=True),
            tuple(sorted(str(parent) for parent in view.class_ancestors(name, reflexive=False))),
            tuple(
                PropertyPreview(
                    str(slot.name), view.get_uri(slot, expand=True), str(slot.range or "string")
                )
                for slot in view.class_induced_slots(name)
            ),
            bool(cls.abstract),
        )
        for name, cls in sorted(view.all_classes().items())
    )
    return SchemaPreview(classes, vocabularies, diagnostics)


def prepare_release(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies = _EMPTY_DEPENDENCIES,
    profile: PreparationProfile = _DEFAULT_PROFILE,
) -> PreparedRelease:
    """Prepare a complete interpretation; cache only immutable pure inputs, never database state."""
    if (
        profile.version not in {"semantic-1", "semantic-2"}
        or profile.compiler_version != SEMANTIC_COMPILER_VERSION
    ):
        _fail("profile", "profile", "unsupported profile", "unsupported")
    stack = _compiler_stack()
    try:
        libraries = release_library_versions(
            dependencies, base={name: value for name, value in stack if name in _LIBRARIES}
        )
    except ValueError as error:
        _fail("analysis_runtime", "execution/implementation/libraries.json", str(error))
    # Ordinary non-analysis preparation has no analyzer dependency. Repeated library
    # names already present in the base stack retain their one manifest entry.
    stack = tuple(dict((*stack, *libraries.items())).items())
    try:
        hash((bundle, dependencies, profile))
    except TypeError:
        # Malformed mutable inputs still reach the existing preparation diagnostics.
        return _prepare_release_uncached(bundle, dependencies, profile, stack)
    return _prepare_release_cached(bundle, dependencies, profile, stack)


@lru_cache(maxsize=8)
def _prepare_release_cached(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies,
    profile: PreparationProfile,
    stack: tuple[tuple[str, str], ...],
) -> PreparedRelease:
    return _prepare_release_uncached(bundle, dependencies, profile, stack)


def _prepare_release_uncached(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies,
    profile: PreparationProfile,
    stack: tuple[tuple[str, str], ...],
) -> PreparedRelease:
    """Prepare a complete interpretation. This does not persist, activate or enforce SQL rules."""
    execution = None
    if profile.version == "semantic-2":
        from .composed import execution_model_from_dependencies

        try:
            execution = execution_model_from_dependencies(dependencies)
        except (ValueError, KeyError, TypeError) as exc:
            _fail("execution_model", "execution", str(exc))
    elif any(a.name.startswith("execution/") for a in dependencies.artifacts):
        _fail("execution_model", "execution", "execution inputs require semantic-2")
    operation_inputs = {}
    for dependency in dependencies.artifacts:
        if dependency.name in {
            "operation/domain-rules.yaml",
            "operation/rule-view.yaml",
            "operation/scientific-policy.json",
        }:
            try:
                declared = yaml.load(dependency.content, Loader=_SchemaYamlLoader)
            except (yaml.YAMLError, ValueError) as exc:
                _fail("operation_rules", dependency.name, str(exc))
            if not isinstance(declared, dict):
                _fail("operation_rules", dependency.name, "rules must be a mapping")
            operation_inputs[dependency.name] = declared
    view, vocabularies, diagnostics = _view_and_vocabularies(bundle, dependencies, profile)
    rule_fragments = compile_conditional_rules(view) if profile.version == "semantic-2" else {}
    enum_types = {s.enum: tuple(m.value for m in s.members) for s in vocabularies}
    definitions: list[ClassDefinition] = []
    classes = {str(name): cls for name, cls in view.all_classes().items()}
    for name in sorted(classes):
        cls = classes[name]
        class_annotations = _annotations(cls)
        if class_annotations.get("cs:scope") not in {None, "global", "local"}:
            _fail("entity_scope", name, "unsupported entity scope", "unsupported")
        if class_annotations.get("cs:case", "preserve") not in {"preserve", "casefold"}:
            _fail("case_policy", name, "unsupported class case policy", "unsupported")
        slots: list[PropertyDefinition] = []
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
            if "cs:functional" in ann and ann["cs:functional"].lower() not in {"true", "false"}:
                _fail(
                    "functional_policy",
                    f"{name}/{sn}",
                    "functional must be an explicit boolean",
                    "unsupported",
                )
            reference_role = ann.get("cs:reference_role")
            if reference_role not in {None, "fact"}:
                _fail("reference_role", f"{name}/{sn}", "unsupported reference role", "unsupported")
            if reference_role and (
                rng in classes or rng in enum_types or _primitive(view, rng) is not str
            ):
                _fail(
                    "reference_role",
                    f"{name}/{sn}",
                    "fact references require a string range",
                    "unsupported",
                )
            scope = ann.get("cs:constraint_scope", profile.constraint_scope)
            if scope not in {"shape", "occurrence", "accepted_value", "context"}:
                _fail("constraint_scope", f"{name}/{sn}", scope)
            presence = str(slot.value_presence) if slot.value_presence is not None else None
            if presence not in {None, "PRESENT"} or (presence is not None and scope != "shape"):
                _fail(
                    "value_presence",
                    f"{name}/{sn}",
                    "the supported presence profile is PRESENT at shape scope",
                    "unsupported",
                )
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
                                inherited.value_presence is not None,
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
                patterns.append(slot.pattern)
            if low and high and max(low) > min(high):
                _fail("incompatible_bounds", f"{name}/{sn}", "minimum exceeds maximum")
            collection_key = None
            if slot.multivalued and slot.inlined and not slot.inlined_as_list and rng in classes:
                identifiers = [
                    str(field.name) for field in view.class_induced_slots(rng) if field.identifier
                ]
                if len(identifiers) == 1:
                    collection_key = identifiers[0]
            prop = PropertyDefinition(
                sn,
                view.get_uri(slot, expand=True),
                rng,
                bool(
                    slot.required
                    or slot.identifier
                    or presence == "PRESENT"
                    or (slot.minimum_cardinality or 0) > 0
                ),
                bool(slot.multivalued),
                minimum_cardinality,
                slot.maximum_cardinality,
                str(max(low)) if low else None,
                str(min(high)) if high else None,
                slot.pattern if slot.pattern else None,
                bool(slot.inlined or slot.inlined_as_list),
                scope,
                str(slot.inverse) if slot.inverse else None,
                bool(slot.symmetric),
                bool(slot.transitive),
                ann.get("cs:case", "preserve"),
                ann.get("cs:key_role", "meaning"),
                tuple(patterns),
                str.__str__(slot.equals_string) if slot.equals_string is not None else None,
                collection_key,
                reference_role,
            )
            slots.append(prop)
        keys = tuple(str(s.name) for s in view.class_induced_slots(name) if s.identifier)
        groups = ((keys,) if keys else ()) + tuple(
            tuple(str(x) for x in unique.unique_key_slots)
            for _, unique in sorted(cast(dict[str, Any], cls.unique_keys or {}).items())
        )
        for group in groups:
            if not group or any(k not in {p.name for p in slots} for k in group):
                _fail("identity_slots", name, "identity references missing properties")
        definitions.append(
            ClassDefinition(
                name,
                view.get_uri(cls, expand=True),
                tuple(sorted(str(x) for x in view.class_ancestors(name, reflexive=False))),
                tuple(slots),
                keys,
                groups,
                bool(cls.abstract),
            )
        )
    from .record_contracts import validate_record_declarations

    validate_record_declarations(tuple(definitions))
    from .boundary import build_boundary_adapters
    from .statement_types import compile_effective_bindings

    aliases = {
        (d.name, p.name): view.induced_slot(p.name, d.name).alias or p.name
        for d in definitions
        for p in d.properties
    }
    primitives = {
        p.range: _primitive(view, p.range)
        for d in definitions
        for p in d.properties
        if p.range not in classes and p.range not in enum_types
    }
    descendants = {
        name: tuple(
            str(n)
            for n in view.class_descendants(name, reflexive=False)
            if not classes[str(n)].abstract
        )
        for name in classes
    }
    boundary_models: dict[str, Any] = {}
    try:
        adapters = build_boundary_adapters(
            tuple(definitions),
            tuple(vocabularies),
            primitive_types=primitives,
            aliases=aliases,
            conditional_fragments=rule_fragments,
            conditional_scope=profile.constraint_scope,
            finite_fields=True,
            descendant_order=descendants,
            models_out=boundary_models,
        )
        effective_bindings = compile_effective_bindings(
            tuple(definitions), tuple(vocabularies), primitive_types=primitives
        )
    except PreparationError:
        raise
    except (ValueError, KeyError, TypeError) as exc:
        _fail("boundary", "models", str(exc))
    primitive_tokens = {typ: name for name, typ in _PRIMITIVES.items()}
    # Normalize duplicate Python primitive spellings without changing their runtime meaning.
    primitive_tokens.update({str: "string", float: "float"})
    from .coverage_contract import coverage_recipe

    boundary_recipe = {
        "abi": "semantic-boundary-" + BOUNDARY_ABI_VERSION,
        "primitives": {name: primitive_tokens[typ] for name, typ in primitives.items()},
        "aliases": {
            d.name: {p.name: aliases[d.name, p.name] for p in d.properties} for d in definitions
        },
        "descendants": descendants,
        "conditional_scope": profile.constraint_scope,
    }
    from .comparison_projection import compile_comparison_projection, projection_bytes

    comparison = compile_comparison_projection(
        tuple(definitions),
        {
            (d.name, p.iri): _annotations(view.induced_slot(p.name, d.name))
            for d in definitions
            for p in d.properties
        },
        effective_bindings["qualification"],
    )
    manifest = canonical_bytes(
        {
            "root": bundle.root,
            **({"execution_model_id": execution.model_id} if execution is not None else {}),
            "profile": asdict(profile),
            "libraries": {
                name: value
                for name, value in stack
                if name in _LIBRARIES or name in ANALYSIS_LIBRARIES
            },
            "sources": sorted((s.name, s.digest) for s in bundle.sources),
            "dependencies": sorted((a.name, a.digest) for a in dependencies.artifacts),
            "ontology_sources": sorted(dependencies.ontology_sources),
            "vocabularies": [asdict(v) for v in vocabularies],
        }
    )
    release_id = "release:" + sha256(manifest).hexdigest()
    artifacts = [
        PreparedArtifact("definitions.json", canonical_bytes([asdict(d) for d in definitions])),
        PreparedArtifact("boundary_recipe.json", canonical_bytes(boundary_recipe)),
        PreparedArtifact("query_coverage.json", canonical_bytes(coverage_recipe())),
        PreparedArtifact("effective_bindings.json", canonical_bytes(effective_bindings)),
    ]
    from .alias_policy import ARTIFACT as ALIAS_ARTIFACT
    from .alias_policy import RULE_INPUT, compile_alias_policy

    domain_policy = next((a for a in dependencies.artifacts if a.name == RULE_INPUT), None)
    if domain_policy is not None:
        try:
            identity = operation_inputs[RULE_INPUT].get("identity", {})
            compiled_aliases = compile_alias_policy(
                bundle, tuple(definitions), identity, view.expand_curie
            )
        except (ValueError, TypeError, KeyError) as exc:
            _fail("alias_policy", RULE_INPUT, str(exc))
        if compiled_aliases is not None:
            artifacts.append(PreparedArtifact(ALIAS_ARTIFACT, compiled_aliases))
    if comparison is not None:
        artifacts.append(
            PreparedArtifact("comparison_projection.json", projection_bytes(comparison))
        )
    if profile.version == "semantic-2":
        artifacts.extend(
            (
                PreparedArtifact("conditional_rules.json", canonical_bytes(rule_fragments)),
                PreparedArtifact(
                    "conditional_rules_native.json",
                    canonical_bytes(
                        compile_native_conditionals(view, rule_fragments, profile.constraint_scope)
                    ),
                ),
                PreparedArtifact(
                    "conditional_rule_options.json", canonical_bytes(CONDITIONAL_RULE_OPTIONS)
                ),
                PreparedArtifact(
                    "conditional_rule_coverage.json",
                    canonical_bytes(
                        {
                            "boundary": "native_json_schema",
                            "persisted_state": "requires_native_enforcement",
                            "shacl": "not_lowered",
                            "owl": "not_lowered",
                        }
                    ),
                ),
            )
        )

    # Optional analytical semantics are explicit archived inputs, never installed defaults.
    for dependency in dependencies.artifacts:
        if dependency.name == "analytical-profile.json":
            adapter = dict(adapters).get("AnalyticalProfile")
            if adapter is None:
                _fail("analytical_profile", dependency.name, "AnalyticalProfile is not declared")
            try:
                adapter.validate_json(dependency.content, strict=True)
            except Exception as exc:
                _fail("analytical_profile", dependency.name, str(exc))
            artifacts.append(PreparedArtifact(dependency.name, dependency.content))
    for dependency in dependencies.artifacts:
        if dependency.name in operation_inputs:
            artifacts.append(PreparedArtifact(dependency.name, dependency.content))
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
    rows += (
        RegistryRow(
            "effective_bindings", "effective-bindings-11", canonical_bytes(effective_bindings)
        ),
    )
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
    for dependency in dependencies.artifacts:
        if dependency.name == "operation/metric-definitions.yaml":
            try:
                declared = yaml.load(dependency.content, Loader=_SchemaYamlLoader)
                if (
                    not isinstance(declared, dict)
                    or set(declared) != {"metrics"}
                    or not isinstance(declared["metrics"], list)
                ):
                    raise ValueError("metric declarations require a metrics sequence")
                adapter = dict(adapters).get("SourceMetricDefinition")
                if adapter is None:
                    raise ValueError("SourceMetricDefinition is not declared")
                metric_ids = set()
                metric_rows = []
                for item in declared["metrics"]:
                    body = adapter.validate_json(json.dumps(item), strict=True).model_dump(
                        mode="json"
                    )
                    if not body["id"] or body["id"] in metric_ids:
                        raise ValueError("metric IDs must be nonempty and unique")
                    metric_ids.add(body["id"])
                    metric_rows.append(
                        RegistryRow("metric_definition", body["id"], canonical_bytes(body))
                    )
                rows += tuple(sorted(metric_rows, key=lambda row: row.name))
                artifacts.append(PreparedArtifact(dependency.name, dependency.content))
            except Exception as exc:
                _fail("metric_definitions", dependency.name, str(exc))
    # Rule declarations are normalized once, from the same resolved LinkML authority.
    # A runtime cannot silently reinterpret installed schemas or change rule versions.
    rule_products: dict[str, RegistryRow] = {}
    hierarchy: set[tuple[str, str]] = set()
    for definition in definitions:
        for prop in definition.properties:
            declared = view.get_slot(prop.name)
            if declared is not None:
                for ancestor in view.slot_ancestors(prop.name, reflexive=False):
                    parent = view.get_slot(ancestor)
                    if parent is not None:
                        hierarchy.add((prop.iri, view.get_uri(parent, expand=True)))
            candidates: list[tuple[str, str | None]] = []
            if prop.inverse:
                inverse = view.get_slot(prop.inverse)
                if inverse is None:
                    _fail("inverse_property", prop.name, "inverse names an undeclared slot")
                candidates.append(("inverse", view.get_uri(inverse, expand=True)))
            if prop.symmetric:
                candidates.append(("symmetric", None))
            if prop.transitive:
                candidates.append(("transitive", None))
            candidates.extend(
                ("subproperty", target) for child, target in hierarchy if child == prop.iri
            )
            for kind, target in candidates:
                body = {"kind": kind, "predicate": prop.iri}
                if target is not None:
                    body["target"] = target
                digest = sha256(canonical_bytes(body)).hexdigest()
                rule_id = "rule:" + digest
                rule_products[rule_id] = RegistryRow(
                    "inference_rule",
                    rule_id,
                    canonical_bytes({**body, "rule_id": rule_id, "rule_version": digest}),
                )
                if kind == "inverse":
                    reverse = {"kind": kind, "predicate": target, "target": prop.iri}
                    reverse_digest = sha256(canonical_bytes(reverse)).hexdigest()
                    reverse_id = "rule:" + reverse_digest
                    rule_products[reverse_id] = RegistryRow(
                        "inference_rule",
                        reverse_id,
                        canonical_bytes(
                            {**reverse, "rule_id": reverse_id, "rule_version": reverse_digest}
                        ),
                    )
    rows += tuple(
        RegistryRow(
            "property_hierarchy",
            child + " -> " + parent,
            canonical_bytes({"property": child, "ancestor": parent}),
        )
        for child, parent in sorted(hierarchy)
    )
    rows += tuple(rule_products[key] for key in sorted(rule_products))
    schema = view.schema
    if schema is None:
        _fail("schema", bundle.root, "schema is unavailable")
    rows += tuple(
        RegistryRow("prefix", name, canonical_bytes({"uri": str(prefix.prefix_reference)}))
        for name, prefix in sorted(cast(dict[str, Any], schema.prefixes or {}).items())
    )
    rows += tuple(
        RegistryRow(
            "operation_class",
            definition.name,
            canonical_bytes(
                {
                    "class": definition.name,
                    "iri": definition.iri,
                    **_annotations(view.get_class(definition.name)),
                }
            ),
        )
        for definition in definitions
    )
    rows += tuple(
        RegistryRow(
            "operation_property",
            f"{definition.name}/{prop.name}",
            canonical_bytes(
                {
                    "class": definition.name,
                    "property": prop.iri,
                    "name": prop.name,
                    "groups": tuple(
                        str(group)
                        for group in (view.induced_slot(prop.name, definition.name).in_subset or ())
                    ),
                    **_annotations(view.induced_slot(prop.name, definition.name)),
                }
            ),
        )
        for definition in definitions
        for prop in definition.properties
    )
    rows += tuple(
        RegistryRow("enum_definition", str(name), canonical_bytes(json_dumper.to_dict(enum)))
        for name, enum in sorted(view.all_enums().items())
    )
    rows += tuple(RegistryRow("enum", v.enum, canonical_bytes(asdict(v))) for v in vocabularies)
    if execution is not None:
        artifacts.append(PreparedArtifact("execution/contracts.json", execution.content))
        rows += (RegistryRow("execution_model", execution.model_id, execution.content),)
    from .query_compatibility import prepare_query_bindings

    query_products = prepare_query_bindings(dependencies)
    if query_products is not None:
        query_artifact, query_rows = query_products
        artifacts.append(query_artifact)
        rows += query_rows
    from .projection_analysis_products import prepare_projection_analysis

    projection_analysis = prepare_projection_analysis(dependencies)
    if projection_analysis is not None:
        artifacts.append(projection_analysis)
    required = ("semantic_registry", "scoped_publication", "typed_values")
    if execution is not None:
        required += execution.required_capabilities
    if rule_fragments:
        required += ("conditional_rules_native",)
    prepared = PreparedRelease(
        release_id,
        manifest,
        tuple(definitions),
        tuple(vocabularies),
        rows,
        tuple(QueryDescriptor(d.iri, d.properties) for d in definitions),
        tuple(artifacts),
        tuple(sorted(set(required))),
        tuple(diagnostics),
        adapters,
        execution.model_id if execution is not None else None,
        _boundary_models=boundary_models,
    )

    # Admission must not archive an operation artifact whose required rules cannot execute.
    # The policy constructor compiles only immutable release products and performs no I/O.
    if any(artifact.kind == "operation/domain-rules.yaml" for artifact in prepared.artifacts):
        from .domain_operations import RULE_INPUT, ReleasedRulesPolicy

        try:
            ReleasedRulesPolicy(prepared)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            _fail("domain_rules", RULE_INPUT, str(exc), "unsupported")
    return prepared
