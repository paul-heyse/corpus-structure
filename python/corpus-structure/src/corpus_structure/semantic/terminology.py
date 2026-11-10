"""Closed terminology acquisition and immutable descriptive vocabulary products."""

from __future__ import annotations

import json
import re
import warnings
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDFS, SKOS

from .identity import canonical_bytes
from .types import PreparedArtifact, SourceArtifact

ARTIFACT = "vocabularies/metadata.json"
PROFILE = "terminology/stato/source.json"
ORIGINAL = "terminology/stato/stato-2026-04-20.owl"
CONVERTED = "terminology/stato/stato-2026-04-20.obo"
IAO_DEFINITION = URIRef("http://purl.obolibrary.org/obo/IAO_0000115")
SYNONYMS = {
    "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym": "exact",
    "http://www.geneontology.org/formats/oboInOwl#hasBroadSynonym": "broad",
    "http://www.geneontology.org/formats/oboInOwl#hasNarrowSynonym": "narrow",
    "http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym": "related",
    "http://purl.obolibrary.org/obo/IAO_0000118": "unclassified",
    "http://purl.obolibrary.org/obo/STATO_0000032": "unclassified",
}


def canonical_obo(content: bytes) -> bytes:
    """Order an existing OBO AST without changing its clauses or interpreting OWL."""
    from importlib import import_module

    fastobo: Any = import_module("fastobo")
    doc = fastobo.load(BytesIO(content))
    frames = [type(frame)(frame.id, sorted(frame, key=str)) for frame in doc]
    frames.sort(key=lambda frame: (type(frame).__name__, str(frame.id)))
    ordered = fastobo.doc.OboDoc(
        fastobo.header.HeaderFrame(
            sorted(
                doc.header,
                key=lambda clause: (not str(clause).startswith("format-version:"), str(clause)),
            )
        ),
        frames,
    )
    result = str(ordered).encode()
    # Parse the emitted syntax and independently preserve all original clauses.
    reopened = fastobo.load(BytesIO(result))

    def clauses(document):
        return sorted(
            (type(frame).__name__, str(frame.id), sorted(map(str, frame))) for frame in document
        )

    if clauses(doc) != clauses(reopened) or sorted(map(str, doc.header)) != sorted(
        map(str, reopened.header)
    ):
        raise ValueError("OBO canonical ordering changed clauses")
    return result


def convert_stato(original: bytes) -> tuple[bytes, tuple[str, ...]]:
    """Explicit pinned acquisition projection, not an ontology-equivalence assertion."""
    from pronto import Ontology

    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        ontology = Ontology(BytesIO(original), import_depth=0)
    target = BytesIO()
    ontology.dump(target, format="obo")
    return canonical_obo(target.getvalue()), tuple(
        sorted({re.sub(r" at 0x[0-9a-fA-F]+(?=>)", "", str(item.message)) for item in seen})
    )


def qualify_conversion(original: bytes, converted: bytes, selected_terms: list[str]) -> None:
    """Check the promised projection against independently read original RDF facts."""
    from pronto import Ontology, Term

    graph = Graph().parse(data=original, format="xml")
    if list(graph.objects(None, OWL.imports)):
        raise ValueError("terminology original has unresolved imports")
    ontology = Ontology(BytesIO(converted), import_depth=0)
    for identifier in selected_terms:
        if not identifier.startswith("STATO:"):
            raise ValueError("unsupported selected terminology prefix")
        term = ontology[identifier]
        if not isinstance(term, Term):
            raise ValueError("selected terminology identifier is not a term: " + identifier)
        uri = URIRef("http://purl.obolibrary.org/obo/" + identifier.replace(":", "_", 1))
        if str(term.name) not in {str(v) for v in graph.objects(uri, RDFS.label)}:
            raise ValueError("converted selected label differs: " + identifier)
        if str(term.definition) not in {str(v) for v in graph.objects(uri, IAO_DEFINITION)}:
            raise ValueError("converted selected definition differs: " + identifier)
        expected = {str(v) for v in graph.objects(uri, RDFS.subClassOf) if isinstance(v, URIRef)}
        observed = {
            "http://purl.obolibrary.org/obo/" + parent.id.replace(":", "_", 1)
            for parent in term.superclasses(distance=1, with_self=False)
        }
        if observed != expected:
            raise ValueError("converted selected named parents differ: " + identifier)


def acquire_terminology(
    pack: Path,
) -> tuple[tuple[SourceArtifact, ...], tuple[SourceArtifact, ...], tuple[str, ...]]:
    """Read only explicitly named local pack inputs; no endpoint or directory discovery."""
    module = pack / "terminology.yaml"
    if not module.exists():
        return (), (), ()
    root = pack / "terminology/sources"
    profile_content = (root / "source.json").read_bytes()
    profile = json.loads(profile_content)
    if type(profile.get("version")) is not int or profile["version"] != 1:
        raise ValueError("unsupported terminology acquisition profile")
    assets = []
    for key, name in (("original", ORIGINAL), ("converted", CONVERTED)):
        filename = profile[key]
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError("terminology source must name a local file")
        content = (root / filename).read_bytes()
        if sha256(content).hexdigest() != profile[key + "_sha256"]:
            raise ValueError("terminology source digest differs: " + key)
        assets.append(SourceArtifact(name, content))
    qualify_conversion(assets[0].content, assets[1].content, profile["selected_terms"])
    assets.append(SourceArtifact(PROFILE, profile_content))
    import yaml

    body = yaml.safe_load(module.read_bytes())
    return (SourceArtifact(body["name"], module.read_bytes()),), tuple(assets), (CONVERTED,)


def _object(value):
    if isinstance(value, Literal):
        return dict(
            kind="literal",
            value=str(value),
            language=value.language,
            datatype=str(value.datatype) if value.datatype else None,
        )
    return dict(kind="iri", value=str(value))


def build_vocabulary_metadata(
    view, vocabularies, dependencies, *, preparation=None
) -> PreparedArtifact:
    """Supplement authoritative membership with bounded, predicate-preserving source detail."""
    inputs = {source.name: source for source in dependencies.artifacts}
    profiles = {}
    graph = None
    if PROFILE in inputs:
        profile = json.loads(inputs[PROFILE].content)
        if type(profile.get("version")) is not int or profile["version"] != 1:
            raise ValueError("unsupported terminology source profile")
        for name, key in ((ORIGINAL, "original"), (CONVERTED, "converted")):
            if name not in inputs or inputs[name].digest != profile[key + "_sha256"]:
                raise ValueError("terminology input differs from its profile")
        graph = Graph().parse(data=inputs[ORIGINAL].content, format="xml")
        if list(graph.objects(None, OWL.imports)):
            raise ValueError("terminology original has unresolved imports")
        profiles["stato"] = profile
    field_bindings: dict[str, list] = {}
    for cls in sorted(view.all_classes()):
        for prop in view.class_induced_slots(cls):
            if str(prop.range) in view.all_enums():
                field_bindings.setdefault(str(prop.range), []).append(
                    dict(class_name=cls, property=str(prop.name))
                )
    enums = {}
    for snapshot in vocabularies:
        members = []
        for member in snapshot.members:
            detail: dict[str, Any] = dict(
                value=member.value,
                meaning=member.meaning,
                label=member.label,
                status="unchecked" if member.meaning else "local",
                definitions=[],
                synonyms=[],
                relationships=[],
                mappings=[],
                annotations=[],
                obsolete=None,
                replacements=[],
            )
            if graph is not None and member.meaning and member.meaning.startswith("STATO:"):
                uri = URIRef(
                    "http://purl.obolibrary.org/obo/" + member.meaning.replace(":", "_", 1)
                )
                labels = sorted(str(v) for v in graph.objects(uri, RDFS.label))
                if not labels:
                    raise ValueError(
                        "selected meaning is absent from original terminology: " + member.meaning
                    )
                if preparation is not None:
                    adapter = preparation.adapters[CONVERTED]
                    if adapter.label(member.meaning) not in labels:
                        raise ValueError("converted terminology label differs from original")
                detail.update(
                    status="checked",
                    label=labels[0],
                    labels=labels,
                    definitions=sorted(str(v) for v in graph.objects(uri, IAO_DEFINITION)),
                    source="stato",
                    source_digest=inputs[ORIGINAL].digest,
                    coverage=dict(
                        relationships="asserted_named_parents_only", owl_equivalence="unassessed"
                    ),
                )
                for predicate, value in sorted(
                    graph.predicate_objects(uri),
                    key=lambda pair: (str(pair[0]), canonical_bytes(_object(pair[1]))),
                ):
                    if isinstance(value, BNode):
                        continue  # Blank-node restrictions are outside this descriptive profile.
                    detail["annotations"].append(
                        dict(predicate=str(predicate), object=_object(value))
                    )
                    if str(predicate) in SYNONYMS:
                        detail["synonyms"].append(
                            dict(
                                value=str(value),
                                predicate=str(predicate),
                                scope=SYNONYMS[str(predicate)],
                            )
                        )
                    if predicate == RDFS.subClassOf and isinstance(value, URIRef):
                        detail["relationships"].append(
                            dict(
                                predicate=str(predicate),
                                direction="outgoing",
                                target=str(value),
                                labels=sorted(str(v) for v in graph.objects(value, RDFS.label)),
                            )
                        )
                    if predicate in {
                        SKOS.exactMatch,
                        SKOS.closeMatch,
                        SKOS.broadMatch,
                        SKOS.narrowMatch,
                        SKOS.relatedMatch,
                        URIRef("http://www.geneontology.org/formats/oboInOwl#hasDbXref"),
                    }:
                        detail["mappings"].append(
                            dict(
                                predicate=str(predicate),
                                direction="outgoing",
                                object=_object(value),
                                provenance="asserted_original_rdf",
                            )
                        )
                    if predicate == OWL.deprecated:
                        detail["obsolete"] = str(value).lower() == "true"
                    if str(predicate) == "http://purl.obolibrary.org/obo/IAO_0100001":
                        detail["replacements"].append(_object(value))
            members.append(detail)
        enums[snapshot.enum] = dict(
            fields=field_bindings.get(snapshot.enum, []),
            members=members,
            unchecked=list(snapshot.unchecked),
            definition_digest=snapshot.definition_digest,
        )
    return PreparedArtifact(
        ARTIFACT, canonical_bytes(dict(version=1, sources=profiles, enums=enums))
    )


def decode_vocabulary_metadata(prepared) -> dict:
    base = dict(
        status="unavailable",
        reason="vocabulary detail unavailable in this archive",
        enums={},
        sources={},
    )
    artifact = next((a for a in prepared.artifacts if a.kind == ARTIFACT), None)
    if artifact is None:
        if int(json.loads(prepared.manifest)["profile"]["compiler_version"]) >= 21:
            return dict(
                base, status="corrupt", reason="required vocabulary metadata product missing"
            )
        return base
    try:
        body = json.loads(artifact.content)
        if type(body.get("version")) is not int:
            raise ValueError("invalid vocabulary metadata version type")
        if body["version"] != 1:
            return dict(
                base, status="unsupported", reason="unsupported vocabulary metadata version"
            )
        if (
            set(body) != {"version", "sources", "enums"}
            or not isinstance(body["sources"], dict)
            or not isinstance(body["enums"], dict)
        ):
            raise ValueError("invalid vocabulary metadata root")
        dependencies = dict(json.loads(prepared.manifest)["dependencies"])
        for source, profile in body["sources"].items():
            if (
                source != "stato"
                or type(profile.get("version")) is not int
                or profile["version"] != 1
            ):
                raise ValueError("unsupported vocabulary metadata source profile")
            if (
                dependencies.get(ORIGINAL) != profile["original_sha256"]
                or dependencies.get(CONVERTED) != profile["converted_sha256"]
            ):
                raise ValueError("vocabulary metadata source pins differ")
        expected = {snapshot.enum: snapshot for snapshot in prepared.vocabularies}
        if set(body["enums"]) != set(expected):
            raise ValueError("vocabulary metadata enum universe differs")
        for name, record in body["enums"].items():
            if not isinstance(record, dict) or set(record) != {
                "fields",
                "members",
                "unchecked",
                "definition_digest",
            }:
                raise ValueError("invalid vocabulary metadata enum")
            if (
                record["unchecked"] != list(expected[name].unchecked)
                or record["definition_digest"] != expected[name].definition_digest
            ):
                raise ValueError("vocabulary metadata checking state differs")
            fields = sorted(
                (definition.name, prop.name)
                for definition in prepared.definitions
                for prop in definition.properties
                if prop.range == name
            )
            if (
                sorted((field["class_name"], field["property"]) for field in record["fields"])
                != fields
            ):
                raise ValueError("vocabulary metadata field bindings differ")
            for member in record["members"]:
                if member["status"] not in {"local", "checked", "unchecked"} or not all(
                    isinstance(member[key], list)
                    for key in (
                        "definitions",
                        "synonyms",
                        "relationships",
                        "mappings",
                        "annotations",
                        "replacements",
                    )
                ):
                    raise ValueError("invalid vocabulary metadata member")
                if member["status"] == "checked" and (
                    member.get("source") not in body["sources"]
                    or member.get("source_digest")
                    != body["sources"][member["source"]]["original_sha256"]
                ):
                    raise ValueError("vocabulary member source differs")
            if [(m["value"], m["meaning"]) for m in record["members"]] != [
                (m.value, m.meaning) for m in expected[name].members
            ]:
                raise ValueError("vocabulary metadata membership differs")
        return dict(body, status="available", reason=None, artifact_digest=artifact.digest)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return dict(base, status="corrupt", reason=str(error))
