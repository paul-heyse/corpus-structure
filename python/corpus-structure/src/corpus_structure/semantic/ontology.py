"""Local ontology acquisition and deterministic semantic RDF projections.

Acquisition reads explicitly supplied files. The pure release compiler consumes its
immutable snapshots; it never opens an OAK endpoint or acquires an ontology itself.
"""

from __future__ import annotations

import copy
import hashlib
import json
import warnings
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import Any
from typing import Literal as TypingLiteral

from linkml.generators.owlgen import OwlSchemaGenerator
from linkml.generators.shaclgen import ShaclGenerator
from linkml.validator.validation_context import ValidationContext
from linkml_runtime.dumpers import json_dumper
from linkml_runtime.linkml_model import (
    ClassDefinition,
    EnumDefinition,
    PermissibleValue,
    SchemaDefinition,
    SlotDefinition,
    TypeDefinition,
)
from linkml_runtime.utils.rdf_canonicalize import RDFCanonicalizationWarning, canonicalize_rdf_graph
from linkml_runtime.utils.schemaview import SchemaView
from linkml_term_validator.plugins import (
    BindingValidationPlugin,
    DynamicEnumPlugin,
    PermissibleValueMeaningPlugin,
)
from oaklib import get_adapter
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

CS = Namespace("https://corpus-structure.dev/semantic/")


class OntologyError(ValueError):
    """A declared ontology or vocabulary could not be resolved completely."""


@dataclass(frozen=True)
class OntologyArtifact:
    kind: str
    content: bytes


@dataclass(frozen=True)
class VocabularyMember:
    value: str
    meaning: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class ResolvedVocabulary:
    enum_name: str
    members: tuple[VocabularyMember, ...]
    source_hashes: tuple[tuple[str, str], ...]
    checks: tuple[str, ...] = ("membership:complete", "not4curation:unchecked")

    @property
    def accepted_values(self) -> tuple[str, ...]:
        return tuple(
            sorted({v for m in self.members for v in (m.value, m.meaning) if v is not None})
        )


@dataclass(frozen=True)
class GraphValidation:
    conforms: bool
    report: bytes
    message: str

    @property
    def outcome(self) -> TypingLiteral["conformant", "nonconformant"]:
        return "conformant" if self.conforms else "nonconformant"


def _schema(view: SchemaView) -> SchemaDefinition:
    schema = view.schema
    if schema is None:
        raise OntologyError("schema is unavailable")
    return schema


def canonical_graph_bytes(graph: Graph) -> bytes:
    """Use LinkML's native RDFC-1.0 path for deterministic RDF 1.1 serialization."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", RDFCanonicalizationWarning)
        try:
            return canonicalize_rdf_graph(graph, output_format="nt").encode()
        except RDFCanonicalizationWarning as exc:
            raise OntologyError("RDF canonicalization requires standard absolute-IRI RDF") from exc


_INTEGRITY_FIELDS = (
    "required",
    "identifier",
    "key",
    "minimum_cardinality",
    "maximum_cardinality",
    "exact_cardinality",
    "minimum_value",
    "maximum_value",
    "pattern",
    "structured_pattern",
)


def _clear_integrity(slot: Any) -> None:
    for field in _INTEGRITY_FIELDS:
        setattr(slot, field, None)
    # Native generators infer maxCount/cardinality=1 from scalar slots.
    slot.multivalued = True


def _scope_projected_schema(view: SchemaView, default_scope: str) -> SchemaDefinition:
    """Lower only shape-scoped integrity into unconditional OWL/SHACL.

    Materialize effective slots before clearing global defaults so inheritance is
    resolved once from the original semantic authority. The copy is a projection,
    never a modification of the admitted model or its relational descriptors.
    """
    scopes = {"shape", "occurrence", "accepted_value", "context"}
    if default_scope not in scopes:
        raise OntologyError(f"unsupported constraint scope {default_scope!r}")
    # SchemaView induced-slot resolution can populate domain_of on source slots;
    # compute against a private view as well as a private output schema.
    view = SchemaView(copy.deepcopy(_schema(view)))
    schema = copy.deepcopy(_schema(view))
    classes = schema.classes
    slots = schema.slots
    types = schema.types
    if not isinstance(classes, dict) or not isinstance(slots, dict) or not isinstance(types, dict):
        raise OntologyError("graph projection requires normalized metamodel mappings")

    def carrier_range(name: str) -> str:
        if view.get_type(name) is None:
            return name
        current = name
        seen = set()
        uri = None
        base = None
        while current:
            if current in seen:
                raise OntologyError("datatype inheritance cycle")
            seen.add(current)
            definition = view.get_type(current)
            if definition is None:
                raise OntologyError(f"unknown datatype {current!r}")
            if definition.uri:
                uri = definition.uri
            if definition.base:
                base = definition.base
            current = str(definition.typeof) if definition.typeof else ""
        if uri is None:
            raise OntologyError(f"datatype {name!r} has no primitive URI")
        alias = f"ScopedCarrier_{name}"
        if alias in view.all_types():
            raise OntologyError(f"reserved projection datatype name {alias!r}")
        types[alias] = TypeDefinition(name=alias, uri=uri, base=base)
        return alias

    for name in view.all_classes():
        cls = classes[name]
        if not isinstance(cls, ClassDefinition):
            raise OntologyError("graph projection requires normalized classes")
        attributes = {}
        for effective in view.class_induced_slots(name):
            fields = json_dumper.to_dict(effective)
            if not isinstance(fields, Mapping):
                raise OntologyError("induced slot serialization must be a mapping")
            attribute = SlotDefinition(**{str(key): value for key, value in fields.items()})
            annotations = getattr(attribute, "annotations", None) or {}
            scope_annotation = annotations.get("cs:constraint_scope")
            scope = str(scope_annotation.value) if scope_annotation is not None else default_scope
            if scope not in scopes:
                raise OntologyError(f"unsupported constraint scope {scope!r}")
            # Already materialized; do not inherit global slot constraints again.
            attribute.is_a = None
            attribute.mixins = []
            if scope != "shape":
                _clear_integrity(attribute)
                if attribute.range:
                    attribute.range = carrier_range(str(attribute.range))
            attributes[str(attribute.name)] = attribute
        # Mutate normalized containers rather than assigning plain dicts through
        # the LinkML JsonObj setter, which would lose the metamodel mapping type.
        if not isinstance(cls.attributes, dict) or not isinstance(cls.slot_usage, dict):
            raise OntologyError("graph projection requires normalized class slot mappings")
        cls.attributes.clear()
        cls.attributes.update(attributes)
        cls.slot_usage.clear()
        cls.slots = []
    for slot in slots.values():
        if not isinstance(slot, SlotDefinition):
            raise OntologyError("graph projection requires normalized slots")
        _clear_integrity(slot)
        if slot.range:
            slot.range = carrier_range(str(slot.range))
    return schema


def build_graph_artifacts(
    view: SchemaView, *, default_constraint_scope: str = "shape"
) -> Mapping[str, bytes]:
    """Generate OWL/SHACL for a fully resolved, admitted local schema.

    Imports must be merged by the caller. This prevents generator import resolution
    from consulting undeclared paths or URLs during preparation.
    """
    if _schema(view).imports:
        raise OntologyError("graph generation requires a merged schema without unresolved imports")
    schema = _scope_projected_schema(view, default_constraint_scope)
    return {
        "owl": canonical_graph_bytes(
            OwlSchemaGenerator(
                schema,
                skip_vacuous_min_zero_cardinality_axioms=True,
                skip_vacuous_local_range_axioms=True,
                consolidate_cardinality_axioms=True,
            ).as_graph()
        ),
        "shacl": canonical_graph_bytes(ShaclGenerator(schema).as_graph()),
    }


def generate_ontology_artifacts(schema: SchemaDefinition) -> tuple[OntologyArtifact, ...]:
    return tuple(
        OntologyArtifact(k, v) for k, v in sorted(build_graph_artifacts(SchemaView(schema)).items())
    )


def _local_path(path: Path) -> Path:
    path = Path(path)
    if not path.is_file():
        raise OntologyError(f"ontology artifact is unavailable: {path}")
    # Pronto must not follow imports to remote resources during local acquisition.
    if path.suffix.lower() != ".obo":
        raise OntologyError("the selected local Pronto profile accepts .obo artifacts only")
    content = path.read_text()
    if any(line.strip().startswith("import:") for line in content.splitlines()):
        raise OntologyError(f"ontology imports must be supplied as resolved artifacts: {path}")
    return path.resolve()


def expand_enum(
    view: SchemaView, enum_name: str, ontology_sources: Mapping[str, Path]
) -> tuple[VocabularyMember, ...]:
    """Resolve supported enum composition using local OAK and Term Validator leaves.

    Composition is explicit because Term Validator 0.4.5 applies minus before
    inherits/static values; subtraction here applies to the complete union.
    """
    if _schema(view).imports:
        raise OntologyError("vocabulary expansion requires merged schema imports")
    adapters: dict[str, Any] = {}

    def adapter_for(source: str) -> tuple[Any, Path]:
        if source not in ontology_sources:
            raise OntologyError(f"ontology source {source!r} has no supplied local artifact")
        path = _local_path(ontology_sources[source])
        if source not in adapters:
            adapters[source] = get_adapter(f"pronto:{path}")
        return adapters[source], path

    def walk(expr: Any, stack: tuple[str, ...]) -> dict[str, VocabularyMember]:
        if getattr(expr, "matches", None):
            raise OntologyError("matches expressions are not supported")
        members: dict[str, VocabularyMember] = {}
        for parent in getattr(expr, "inherits", None) or ():
            parent = str(parent)
            if parent in stack:
                raise OntologyError(f"enum inheritance cycle: {' -> '.join((*stack, parent))}")
            definition = view.get_enum(parent)
            if definition is None:
                raise OntologyError(f"unknown inherited enum {parent!r}")
            members.update(walk(definition, (*stack, parent)))
        for value, pv in (getattr(expr, "permissible_values", None) or {}).items():
            meaning = str(pv.meaning) if pv.meaning else None
            members[str(value)] = VocabularyMember(str(value), meaning, pv.title or pv.description)
        for value in getattr(expr, "concepts", None) or ():
            members[str(value)] = VocabularyMember(str(value), str(value))
        query = getattr(expr, "reachable_from", None)
        if query is not None:
            source = str(query.source_ontology or "")
            adapter, path = adapter_for(source)
            roots = tuple(str(n) for n in query.source_nodes or ())
            if not roots:
                raise OntologyError("reachable_from requires at least one source node")
            for root in roots:
                if adapter.label(root) is None:
                    raise OntologyError(f"unknown ontology root {root!r} in {source!r}")
            plugin = DynamicEnumPlugin(
                oak_adapter_string=f"pronto:{path}",
                cache_labels=False,
                cache_enum_expansions=False,
            )
            leaf = EnumDefinition(name="resolved_leaf", reachable_from=query)
            for value in plugin.expand_enum(leaf, use_cache=False):
                members[value] = VocabularyMember(value, value, adapter.label(value))
        for include in getattr(expr, "include", None) or ():
            members.update(walk(include, stack))
        for minus in getattr(expr, "minus", None) or ():
            excluded = walk(minus, stack)
            excluded_ids = {v for m in excluded.values() for v in (m.value, m.meaning) if v}
            members = {
                k: m for k, m in members.items() if not ({m.value, m.meaning} & excluded_ids)
            }
        return members

    definition = view.get_enum(enum_name)
    if definition is None:
        raise OntologyError(f"unknown enum {enum_name!r}")
    return tuple(sorted(walk(definition, (enum_name,)).values(), key=lambda m: m.value))


def resolve_vocabularies(
    view: SchemaView, ontology_sources: Mapping[str, Path]
) -> tuple[ResolvedVocabulary, ...]:
    """Acquire immutable enum snapshots from explicit artifacts, without file caches."""
    hashes = tuple(
        sorted(
            (name, hashlib.sha256(_local_path(path).read_bytes()).hexdigest())
            for name, path in ontology_sources.items()
        )
    )
    snapshots = tuple(
        ResolvedVocabulary(
            name,
            expand_enum(view, name, ontology_sources),
            hashes,
            (
                "membership:complete",
                "not4curation:unchecked",
                *_meaning_checks(view, name, ontology_sources),
            ),
        )
        for name in sorted(view.all_enums())
    )
    after = tuple(
        sorted(
            (name, hashlib.sha256(_local_path(path).read_bytes()).hexdigest())
            for name, path in ontology_sources.items()
        )
    )
    if hashes != after:
        raise OntologyError("ontology artifacts changed during acquisition")
    return snapshots


def qualified_assertion_graph(assertions: Iterable[Mapping[str, Any]]) -> Graph:
    """Represent source assertions without entailing their unqualified triple.

    Each record requires id, subject, predicate and object. URIRef objects are
    resource references; other values are literals, preserving JSON structure
    for qualification values that have no scalar representation.
    """
    graph = Graph()
    seen = {}
    for assertion in assertions:
        identity = str(assertion["id"])
        if identity in seen and seen[identity] != assertion:
            raise OntologyError(f"conflicting assertion occurrence identity {identity!r}")
        seen[identity] = copy.deepcopy(assertion)
        node = URIRef(str(assertion["id"]))
        graph.add((node, RDF.type, RDF.Statement))
        graph.add((node, RDF.subject, URIRef(str(assertion["subject"]))))
        graph.add((node, RDF.predicate, URIRef(str(assertion["predicate"]))))
        obj = assertion["object"]
        if isinstance(obj, dict | tuple | list):
            object_value = Literal(
                json.dumps(obj, sort_keys=True, separators=(",", ":")), datatype=RDF.JSON
            )
        else:
            object_value = obj if isinstance(obj, (URIRef, Literal)) else Literal(obj)
        graph.add((node, RDF.object, object_value))
        for key, value in assertion.items():
            if key in {"id", "subject", "predicate", "object"}:
                continue
            if isinstance(value, URIRef | Literal):
                rdf_value = value
            elif isinstance(value, dict | tuple | list):
                rdf_value = Literal(
                    json.dumps(value, sort_keys=True, separators=(",", ":")), datatype=RDF.JSON
                )
            else:
                rdf_value = Literal(value)
            graph.add((node, CS[key], rdf_value))
    return graph


@dataclass(frozen=True)
class QualifiedGraphReference:
    """An instance reference whose target must be present in validation closure."""

    target_id: str

    def __post_init__(self) -> None:
        if type(self.target_id) is not str or not self.target_id:
            raise OntologyError("qualified reference requires target identity")


@dataclass(frozen=True)
class QualifiedGraphProjection:
    """Explicit validation universe; output focus does not narrow its required closure."""

    release_id: str
    realization_id: str
    data_revision: int
    projection_id: str
    assertions: tuple[Mapping[str, Any], ...]
    related_nodes: Mapping[str, Mapping[str, Any]]
    references: Mapping[str, tuple[str, ...]]
    identity_exclusions: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        def freeze(value: Any) -> Any:
            if isinstance(value, Mapping):
                return MappingProxyType({key: freeze(child) for key, child in value.items()})
            if isinstance(value, tuple | list):
                return tuple(freeze(child) for child in value)
            return value

        object.__setattr__(self, "assertions", freeze(self.assertions))
        object.__setattr__(self, "related_nodes", freeze(self.related_nodes))
        object.__setattr__(self, "references", freeze(self.references))
        object.__setattr__(self, "identity_exclusions", freeze(self.identity_exclusions))

    def graph(self) -> Graph:
        if not self.release_id or not self.realization_id or not self.projection_id:
            raise OntologyError("graph projection requires release, realization and projection")
        if type(self.data_revision) is not int or self.data_revision < 0:
            raise OntologyError("graph projection requires snapshot revision")
        assertions = {str(row["id"]): row for row in self.assertions}
        if len(assertions) != len(self.assertions):
            raise OntologyError("duplicate projected occurrence identity")
        exclusions = {str(row["id"]): row for row in self.identity_exclusions}
        if len(exclusions) != len(self.identity_exclusions):
            raise OntologyError("duplicate projected identity exclusion")
        overlap = (assertions.keys() & self.related_nodes.keys()) | (
            exclusions.keys() & (assertions.keys() | self.related_nodes.keys())
        )
        if overlap:
            raise OntologyError("projected node identities overlap")
        for row in exclusions.values():
            left, right = row.get("left"), row.get("right")
            if not isinstance(left, QualifiedGraphReference) or not isinstance(
                right, QualifiedGraphReference
            ):
                raise OntologyError("identity exclusion requires typed endpoint references")
            if left == right:
                raise OntologyError("identity exclusion endpoints collapse")
            evidence = row.get("evidence")
            if (
                not isinstance(evidence, tuple | list)
                or not evidence
                or any(not isinstance(item, QualifiedGraphReference) for item in evidence)
            ):
                raise OntologyError("identity exclusion needs typed evidence closure")
        available = {**self.related_nodes, **assertions, **exclusions}
        if self.references.keys() - available.keys():
            raise OntologyError("reference source is outside projected node universe")
        for row in available.values():
            for key, expected in (
                ("release_id", self.release_id),
                ("realization_id", self.realization_id),
                ("data_revision", self.data_revision),
            ):
                if key in row and row[key] != expected:
                    raise OntologyError(f"wrong graph node scope: {key}")

        def instance_references(value: Any) -> set[str]:
            if isinstance(value, QualifiedGraphReference):
                return {value.target_id}
            if isinstance(value, URIRef):
                return {str(value)}
            if isinstance(value, Mapping):
                return set().union(
                    *(
                        instance_references(child)
                        for key, child in value.items()
                        if key not in {"predicate", "rdf_type", "class_iri"}
                    )
                )
            if isinstance(value, tuple | list):
                return set().union(*(instance_references(child) for child in value))
            return set()

        references = {
            identity: set(self.references.get(identity, ())) | instance_references(row)
            for identity, row in available.items()
        }
        for identity, assertion in assertions.items():
            subject = assertion["subject"]
            references[identity].add(
                subject.target_id if isinstance(subject, QualifiedGraphReference) else str(subject)
            )
        required = set(assertions) | set(exclusions)
        pending = list(required)
        while pending:
            source = pending.pop()
            for target in references.get(source, ()):
                if target not in available:
                    raise OntologyError(f"missing required related node {target!r}")
                if target not in required:
                    required.add(target)
                    pending.append(target)
        graph = Graph()
        binding = {
            "release": self.release_id,
            "realization": self.realization_id,
            "data_revision": self.data_revision,
            "projection": self.projection_id,
        }

        def structure(owner: URIRef, path: tuple[str, ...], value: Any) -> URIRef | Literal:
            if isinstance(value, QualifiedGraphReference):
                return URIRef(value.target_id)
            if isinstance(value, URIRef | Literal):
                return value
            if value is None:
                node = URIRef(
                    "urn:cs:projection-null:"
                    + hashlib.sha256(
                        json.dumps([binding, str(owner), path], sort_keys=True).encode()
                    ).hexdigest()
                )
                graph.add((node, RDF.type, CS.Null))
                return node
            if not isinstance(value, Mapping | tuple | list):
                return Literal(value)
            # Paths retain duplicate member positions, independently of RDF set semantics.
            node = URIRef(
                "urn:cs:projection-value:"
                + hashlib.sha256(
                    json.dumps([binding, str(owner), path], sort_keys=True).encode()
                ).hexdigest()
            )
            if isinstance(value, Mapping):
                graph.add((node, RDF.type, CS.Record))
                for key, child in value.items():
                    if type(key) is not str:
                        raise OntologyError("qualified record keys must be strings")
                    graph.add((node, CS[key], structure(owner, (*path, key), child)))
            else:
                graph.add((node, RDF.type, CS.Collection))
                for position, child in enumerate(value):
                    member = URIRef(str(node) + ":" + str(position))
                    graph.add((node, CS.member, member))
                    graph.add((member, RDF.type, CS.CollectionMember))
                    graph.add((member, CS.position, Literal(position)))
                    graph.add((member, CS.value, structure(owner, (*path, str(position)), child)))
            return node

        for assertion in self.assertions:
            node = URIRef(str(assertion["id"]))
            graph.add((node, RDF.type, RDF.Statement))
            subject = assertion["subject"]
            graph.add(
                (
                    node,
                    RDF.subject,
                    URIRef(
                        subject.target_id
                        if isinstance(subject, QualifiedGraphReference)
                        else str(subject)
                    ),
                )
            )
            graph.add((node, RDF.predicate, URIRef(str(assertion["predicate"]))))
            graph.add((node, RDF.object, structure(node, ("object",), assertion["object"])))
        for identity in exclusions:
            node = URIRef(identity)
            graph.add((node, RDF.type, CS.IdentityExclusion))
            graph.add((node, CS.left, URIRef(exclusions[identity]["left"].target_id)))
            graph.add((node, CS.right, URIRef(exclusions[identity]["right"].target_id)))
        for identity in sorted(required):
            node = URIRef(identity)
            for key, value in binding.items():
                graph.add((node, CS[key], Literal(value)))
            row = available[identity]
            for key, value in row.items():
                if key in {"id", "subject", "predicate", "object"} and identity in assertions:
                    continue
                graph.add((node, CS[key + "Node"], structure(node, (key,), value)))
            for target in sorted(references.get(identity, ())):
                graph.add((node, CS.requiredNode, URIRef(target)))
        return graph


def validate_graph(data: Graph, shapes: Graph, ontology: Graph | None = None) -> GraphValidation:
    """Conformance only: no implicit entailment, imports, mutation or SHACL rules."""
    conforms, report, message = validate(
        data,
        shacl_graph=shapes,
        ont_graph=ontology,
        inference="none",
        inplace=False,
        advanced=False,
        do_owl_imports=False,
    )
    if not isinstance(report, Graph):
        raise OntologyError(f"SHACL validation failed: {message}")
    return GraphValidation(bool(conforms), canonical_graph_bytes(report), str(message))


def validate_enum_meanings(view: SchemaView, ontology_path: Path) -> tuple[str, ...]:
    """Check schema enum meanings with Term Validator against one declared ontology.

    This optional acquisition check is scoped to a supplied single local source;
    callers partition schemas by ontology before invoking it. Labels and obsolete
    terms are checked by the plugin; Not4Curation remains explicitly unchecked.
    """
    path = _local_path(ontology_path)
    plugin = PermissibleValueMeaningPlugin(
        oak_adapter_string=f"pronto:{path}",
        cache_labels=False,
        strict_mode=True,
    )
    source = _schema(view)
    root = "VocabularyValidationRoot"
    schema = SchemaDefinition(
        id=source.id,
        name=source.name,
        prefixes=source.prefixes,
        types=source.types,
        enums=[copy.deepcopy(e) for e in view.all_enums(imports=False).values()],
        classes={root: ClassDefinition(name=root)},
    )
    context = ValidationContext(schema, target_class=root)
    plugin.pre_process(context)
    return tuple(result.message for result in plugin.process({}, context))


def resolve_vocabularies_from_bytes(
    view: SchemaView, ontology_sources: Mapping[str, bytes]
) -> tuple[ResolvedVocabulary, ...]:
    """Expand supplied immutable artifacts in an owned temporary directory.

    This is deterministic preparation with bounded temporary materialization for
    OAK's path-based parser: no network acquisition, persistent cache or globals.
    Names identify dependencies in the manifest, never filesystem destinations.
    """
    with TemporaryDirectory(prefix="corpus-semantic-ontology-") as directory:
        paths = {}
        for index, (name, content) in enumerate(sorted(ontology_sources.items())):
            path = Path(directory) / f"ontology-{index}.obo"
            path.write_bytes(content)
            paths[name] = path
        return resolve_vocabularies(view, paths)


def _meaning_checks(
    view: SchemaView, enum_name: str, ontology_sources: Mapping[str, Path]
) -> tuple[str, ...]:
    definition = view.get_enum(enum_name)
    if definition is None:
        raise OntologyError(f"unknown enum {enum_name!r}")
    prefixes = {}
    for source, path in ontology_sources.items():
        adapter = get_adapter(f"pronto:{_local_path(path)}")
        for entity in adapter.entities():
            prefix = str(entity).partition(":")[0]
            previous = prefixes.setdefault(prefix, source)
            if previous != source:
                raise OntologyError(f"ambiguous ontology source for prefix {prefix!r}")
    checks = []

    def expression_meanings(
        expr: Any, stack: tuple[str, ...], ancestors: frozenset[int] = frozenset()
    ) -> Iterable[tuple[str, PermissibleValue]]:
        identity = id(expr)
        if identity in ancestors:
            raise OntologyError("recursive enum expression")
        ancestors = ancestors | {identity}
        permissible = getattr(expr, "permissible_values", None) or {}
        if not isinstance(permissible, Mapping):
            raise OntologyError("permissible values must be normalized mappings")
        for name, value in permissible.items():
            if not isinstance(value, PermissibleValue):
                raise OntologyError("permissible values must be normalized metamodel values")
            yield str(name), value
        for concept in getattr(expr, "concepts", None) or ():
            yield str(concept), PermissibleValue(text=str(concept), meaning=str(concept))
        for parent_name in getattr(expr, "inherits", None) or ():
            parent_name = str(parent_name)
            if parent_name in stack:
                raise OntologyError(f"enum inheritance cycle: {' -> '.join((*stack, parent_name))}")
            parent = view.get_enum(parent_name)
            if parent is None:
                raise OntologyError(f"unknown inherited enum {parent_name!r}")
            yield from expression_meanings(parent, (*stack, parent_name), ancestors)
        # Excluded concepts still declare ontology terms and must be resolved;
        # subtraction must not hide invalid or unchecked semantic dependencies.
        for operator in ("include", "minus"):
            for child in getattr(expr, operator, None) or ():
                yield from expression_meanings(child, stack, ancestors)

    candidates = expression_meanings(definition, (enum_name,))
    for name, pv in candidates:
        if not isinstance(pv, PermissibleValue):
            raise OntologyError("permissible values must be normalized metamodel values")
        if not pv.meaning:
            continue
        source = prefixes.get(str(pv.meaning).partition(":")[0])
        if source is None:
            checks.append(f"meaning:{pv.meaning}:unchecked")
            continue
        source_schema = _schema(view)
        schema = SchemaDefinition(
            id=source_schema.id,
            name=source_schema.name,
            prefixes=source_schema.prefixes,
            types=source_schema.types,
            enums={
                enum_name: EnumDefinition(
                    name=enum_name, permissible_values={name: copy.deepcopy(pv)}
                )
            },
        )
        messages = validate_enum_meanings(SchemaView(schema), ontology_sources[source])
        if messages:
            raise OntologyError("; ".join(messages))
        checks.append(f"meaning:{pv.meaning}:checked")
    return tuple(sorted(set(checks)))


def validate_bindings(
    view: SchemaView, target_class: str, instance: Mapping[str, Any], ontology_path: Path
) -> tuple[str, ...]:
    """Validate supported nested term bindings against an explicitly local ontology.

    The caller must use a merged admitted schema. This acquisition/diagnostic
    helper is not PostgreSQL publication enforcement.
    """
    if _schema(view).imports:
        raise OntologyError("binding validation requires merged schema imports")
    path = _local_path(ontology_path)
    plugin = BindingValidationPlugin(
        oak_adapter_string=f"pronto:{path}",
        validate_labels=True,
        strict=True,
        cache_labels=False,
        cache_enum_expansions=False,
    )
    context = ValidationContext(_schema(view), target_class=target_class)
    plugin.pre_process(context)
    return tuple(result.message for result in plugin.process(dict(instance), context))


def qualified_validation_graph(projection: QualifiedGraphProjection) -> Graph:
    """Materialize the declared qualified validation closure, never a bare-domain graph."""
    return projection.graph()


def qualified_projection_shapes() -> Graph:
    """Core shapes target reified statements, structural records and positional members."""
    return Graph().parse(
        data='''@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix cs: <https://corpus-structure.dev/semantic/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
cs:StatementShape a sh:NodeShape; sh:targetClass rdf:Statement;
 sh:property [sh:path rdf:subject; sh:minCount 1; sh:maxCount 1; sh:nodeKind sh:IRI];
 sh:property [sh:path rdf:predicate; sh:minCount 1; sh:maxCount 1; sh:nodeKind sh:IRI];
 sh:property [sh:path rdf:object; sh:minCount 1; sh:maxCount 1] .
cs:IdentityExclusionShape a sh:NodeShape; sh:targetClass cs:IdentityExclusion;
 sh:property [sh:path cs:left; sh:minCount 1; sh:maxCount 1; sh:nodeKind sh:IRI];
 sh:property [sh:path cs:right; sh:minCount 1; sh:maxCount 1; sh:nodeKind sh:IRI];
 sh:sparql [sh:message "Identity exclusion endpoints must differ";
 sh:select """SELECT $this WHERE {
   $this <https://corpus-structure.dev/semantic/left> ?e;
   <https://corpus-structure.dev/semantic/right> ?e . }"""] .
cs:MemberShape a sh:NodeShape; sh:targetClass cs:CollectionMember;
 sh:property [sh:path cs:position; sh:datatype xsd:integer;
              sh:minInclusive 0; sh:minCount 1; sh:maxCount 1];
 sh:property [sh:path cs:value; sh:minCount 1; sh:maxCount 1] .
cs:CollectionShape a sh:NodeShape; sh:targetClass cs:Collection;
 sh:property [sh:path cs:member; sh:class cs:CollectionMember];
 sh:sparql [sh:message "Collection member positions must be unique";
 sh:select """SELECT $this WHERE {
   $this <https://corpus-structure.dev/semantic/member> ?a, ?b . FILTER(?a != ?b)
   ?a <https://corpus-structure.dev/semantic/position> ?p .
   ?b <https://corpus-structure.dev/semantic/position> ?p . }"""] .
cs:ScopedNodeShape a sh:NodeShape; sh:targetSubjectsOf cs:projection;
 sh:property [sh:path cs:release; sh:minCount 1; sh:maxCount 1];
 sh:property [sh:path cs:realization; sh:minCount 1; sh:maxCount 1];
 sh:property [sh:path cs:data_revision; sh:datatype xsd:integer;
              sh:minInclusive 0; sh:minCount 1; sh:maxCount 1] .
''',
        format="turtle",
    )


def validate_projected_graph(
    projection: QualifiedGraphProjection, shapes: Graph | None = None, ontology: Graph | None = None
) -> GraphValidation:
    selected = qualified_projection_shapes()
    if shapes is not None:
        selected += shapes
    return validate_graph(qualified_validation_graph(projection), selected, ontology)
