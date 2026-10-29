"""Local ontology acquisition and deterministic semantic RDF projections.

Acquisition reads explicitly supplied files. The pure release compiler consumes its
immutable snapshots; it never opens an OAK endpoint or acquires an ontology itself.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from linkml.generators.owlgen import OwlSchemaGenerator
from linkml.generators.shaclgen import ShaclGenerator
from linkml_runtime.linkml_model import ClassDefinition, EnumDefinition, SchemaDefinition
from linkml_runtime.utils.schemaview import SchemaView
from linkml.validator.validation_context import ValidationContext
from linkml_term_validator.plugins import DynamicEnumPlugin, PermissibleValueMeaningPlugin
from oaklib import get_adapter
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import to_canonical_graph
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
        return tuple(sorted({v for m in self.members for v in (m.value, m.meaning) if v is not None}))


@dataclass(frozen=True)
class GraphValidation:
    conforms: bool
    report: bytes
    message: str


def canonical_graph_bytes(graph: Graph) -> bytes:
    """Canonicalize blank nodes, then sort triples without changing assertion identity."""
    canonical = to_canonical_graph(graph)
    return ("".join(sorted(f"{s.n3()} {p.n3()} {o.n3()} .\n" for s, p, o in canonical))).encode()


def build_graph_artifacts(view: SchemaView) -> Mapping[str, bytes]:
    """Generate OWL/SHACL for a fully resolved, admitted local schema.

    Imports must be merged by the caller. This prevents generator import resolution
    from consulting undeclared paths or URLs during preparation.
    """
    if view.schema.imports:
        raise OntologyError("graph generation requires a merged schema without unresolved imports")
    return {
        "owl": canonical_graph_bytes(OwlSchemaGenerator(
            view.schema, skip_vacuous_min_zero_cardinality_axioms=True,
            skip_vacuous_local_range_axioms=True, consolidate_cardinality_axioms=True,
        ).as_graph()),
        "shacl": canonical_graph_bytes(ShaclGenerator(view.schema).as_graph()),
    }


def generate_ontology_artifacts(schema: SchemaDefinition) -> tuple[OntologyArtifact, ...]:
    return tuple(OntologyArtifact(k, v) for k, v in sorted(build_graph_artifacts(SchemaView(schema)).items()))


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
    if view.schema.imports:
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
            members = {k: m for k, m in members.items() if not ({m.value, m.meaning} & excluded_ids)}
        return members

    definition = view.get_enum(enum_name)
    if definition is None:
        raise OntologyError(f"unknown enum {enum_name!r}")
    return tuple(sorted(walk(definition, (enum_name,)).values(), key=lambda m: m.value))


def resolve_vocabularies(
    view: SchemaView, ontology_sources: Mapping[str, Path]
) -> tuple[ResolvedVocabulary, ...]:
    """Acquire immutable enum snapshots from explicit artifacts, without file caches."""
    hashes = tuple(sorted((name, hashlib.sha256(_local_path(path).read_bytes()).hexdigest())
                          for name, path in ontology_sources.items()))
    snapshots = tuple(ResolvedVocabulary(name, expand_enum(view, name, ontology_sources), hashes)
                      for name in sorted(view.all_enums()))
    after = tuple(sorted((name, hashlib.sha256(_local_path(path).read_bytes()).hexdigest())
                         for name, path in ontology_sources.items()))
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
    for assertion in assertions:
        node = URIRef(str(assertion["id"]))
        graph.add((node, RDF.type, RDF.Statement))
        graph.add((node, RDF.subject, URIRef(str(assertion["subject"]))))
        graph.add((node, RDF.predicate, URIRef(str(assertion["predicate"]))))
        obj = assertion["object"]
        graph.add((node, RDF.object, obj if isinstance(obj, (URIRef, Literal)) else Literal(obj)))
        for key, value in assertion.items():
            if key in {"id", "subject", "predicate", "object"}:
                continue
            if isinstance(value, URIRef | Literal):
                rdf_value = value
            elif isinstance(value, dict | tuple | list):
                rdf_value = Literal(json.dumps(value, sort_keys=True, separators=(",", ":")), datatype=RDF.JSON)
            else:
                rdf_value = Literal(value)
            graph.add((node, CS[key], rdf_value))
    return graph


def validate_graph(data: Graph, shapes: Graph, ontology: Graph | None = None) -> GraphValidation:
    """Conformance only: no implicit entailment, imports, mutation or SHACL rules."""
    conforms, report, message = validate(
        data, shacl_graph=shapes, ont_graph=ontology, inference="none",
        inplace=False, advanced=False, do_owl_imports=False,
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
        oak_adapter_string=f"pronto:{path}", cache_labels=False, strict_mode=True,
    )
    schema = copy.deepcopy(view.schema)
    root = "VocabularyValidationRoot"
    schema.classes[root] = ClassDefinition(name=root)
    context = ValidationContext(schema, target_class=root)
    plugin.pre_process(context)
    return tuple(str(result.message) for result in plugin.process({}, context))


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
