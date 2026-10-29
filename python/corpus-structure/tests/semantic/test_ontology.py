"""Independent ontology, occurrence and conformance expectations."""

from pathlib import Path

import pytest
from linkml_runtime.linkml_model import PermissibleValue, SchemaDefinition
from linkml_runtime.linkml_model.meta import ReachabilityQuery
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from corpus_structure.semantic.ontology import (
    CS,
    OntologyError,
    build_graph_artifacts,
    expand_enum,
    qualified_assertion_graph,
    resolve_vocabularies,
    resolve_vocabularies_from_bytes,
    validate_bindings,
    validate_enum_meanings,
    validate_graph,
)


def view(**kwargs):
    return SchemaView(
        SchemaDefinition(
            id="https://example.org/model",
            name="test",
            default_prefix="ex",
            prefixes={
                "ex": {"prefix_reference": "https://example.org/"},
                "xsd": {"prefix_reference": "http://www.w3.org/2001/XMLSchema#"},
            },
            types={"string": {"uri": "xsd:string", "base": "str"}},
            **kwargs,
        )
    )


def test_canonical_generated_ontology_and_shapes():
    schema = view(
        classes={
            "Thing": {
                "class_uri": "ex:Thing",
                "attributes": {
                    "name": {"range": "string", "required": True, "slot_uri": "ex:name"}
                },
            }
        }
    )
    first = build_graph_artifacts(schema)
    assert first == build_graph_artifacts(schema)
    ontology = Graph().parse(data=first["owl"], format="nt")
    assert (
        URIRef("https://example.org/Thing"),
        RDF.type,
        URIRef("http://www.w3.org/2002/07/owl#Class"),
    ) in ontology
    shapes = Graph().parse(data=first["shacl"], format="nt")
    data = Graph()
    thing = URIRef("https://example.org/a")
    data.add((thing, RDF.type, URIRef("https://example.org/Thing")))
    assert not validate_graph(data, shapes).conforms
    data.add((thing, URIRef("https://example.org/name"), Literal("Alpha")))
    assert validate_graph(data, shapes).conforms


def test_parallel_assertions_do_not_entail_bare_triple():
    source = URIRef("https://example.org/source")
    records = [
        dict(
            id=f"https://example.org/assertion/{i}",
            subject="https://example.org/a",
            predicate="https://example.org/owns",
            object=URIRef("https://example.org/b"),
            polarity="positive",
            condition={"valid_from": "2026-01-01"},
            evidence=source,
        )
        for i in (1, 2)
    ]
    graph = qualified_assertion_graph(records)
    assert len(set(graph.subjects(RDF.type, RDF.Statement))) == 2
    assert (
        URIRef(records[0]["subject"]),
        URIRef(records[0]["predicate"]),
        records[0]["object"],
    ) not in graph
    assert (URIRef(records[1]["id"]), CS.evidence, source) in graph
    condition = graph.value(URIRef(records[0]["id"]), CS.condition)
    assert isinstance(condition, Literal)
    assert condition.datatype == RDF.JSON


def local_ontology(tmp_path: Path) -> Path:
    path = tmp_path / "test.obo"
    path.write_text("""format-version: 1.2
ontology: test

[Term]
id: TEST:1
name: root

[Term]
id: TEST:2
name: child
is_a: TEST:1 ! root

[Term]
id: TEST:3
name: grandchild
is_a: TEST:2 ! child
""")
    return path


def test_local_reachability_and_composition_without_cache(tmp_path, monkeypatch):
    path = local_ontology(tmp_path)
    monkeypatch.chdir(tmp_path)
    schema = view(
        enums={
            "Taxon": {
                "reachable_from": {
                    "source_ontology": "test",
                    "source_nodes": ["TEST:1"],
                    "include_self": False,
                    "relationship_types": ["rdfs:subClassOf"],
                }
            },
            "Selected": {"inherits": ["Taxon"], "minus": [{"concepts": ["TEST:3"]}]},
            "Static": {"permissible_values": {"CHILD": {"meaning": "TEST:2"}}},
        }
    )
    assert [m.value for m in expand_enum(schema, "Taxon", {"test": path})] == ["TEST:2", "TEST:3"]
    assert [m.value for m in expand_enum(schema, "Selected", {"test": path})] == ["TEST:2"]
    snapshots = resolve_vocabularies(schema, {"test": path})
    assert next(s for s in snapshots if s.enum_name == "Static").accepted_values == (
        "CHILD",
        "TEST:2",
    )
    assert "not4curation:unchecked" in snapshots[0].checks
    assert list(tmp_path.iterdir()) == [path]


def test_include_self_and_unknown_are_distinct(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(
        enums={
            "Taxon": {
                "reachable_from": {
                    "source_ontology": "test",
                    "source_nodes": ["TEST:1"],
                    "include_self": True,
                }
            }
        }
    )
    assert [m.value for m in expand_enum(schema, "Taxon", {"test": path})] == [
        "TEST:1",
        "TEST:2",
        "TEST:3",
    ]
    with pytest.raises(OntologyError, match="supplied local artifact"):
        expand_enum(schema, "Taxon", {})
    definition = schema.get_enum("Taxon")
    assert definition is not None
    query = definition.reachable_from
    assert isinstance(query, ReachabilityQuery)
    query.source_nodes = ["TEST:unknown"]
    with pytest.raises(OntologyError, match="unknown ontology root"):
        expand_enum(schema, "Taxon", {"test": path})


def test_unsupported_and_cycles_are_refused():
    schema = view(
        enums={
            "A": {"inherits": ["B"]},
            "B": {"inherits": ["A"]},
            "Pattern": {"matches": {"source_ontology": "test", "identifier_pattern": "TEST:.*"}},
        }
    )
    with pytest.raises(OntologyError, match="inheritance cycle"):
        expand_enum(schema, "A", {})
    with pytest.raises(OntologyError, match="matches"):
        expand_enum(schema, "Pattern", {})


def test_unresolved_imports_cannot_trigger_acquisition():
    schema = view(imports=["https://example.org/remote.yaml"])
    with pytest.raises(OntologyError, match="merged schema"):
        build_graph_artifacts(schema)


def test_obo_remote_import_is_rejected(tmp_path):
    path = local_ontology(tmp_path)
    path.write_text("import: https://example.org/remote.obo\n" + path.read_text())
    schema = view(
        enums={"A": {"reachable_from": {"source_ontology": "test", "source_nodes": ["TEST:1"]}}}
    )
    with pytest.raises(OntologyError, match="imports must be supplied"):
        expand_enum(schema, "A", {"test": path})


def test_ordered_roles_are_not_flattened_into_triple_sets():
    g = qualified_assertion_graph(
        [
            dict(
                id="urn:assertion:1",
                subject="urn:subject",
                predicate="urn:p",
                object=1,
                roles=[{"name": "first", "value": 1}, {"name": "second", "value": 1}],
            )
        ]
    )
    value = g.value(URIRef("urn:assertion:1"), CS.roles)
    assert str(value) == '[{"name":"first","value":1},{"name":"second","value":1}]'
    assert isinstance(value, Literal)
    assert value.datatype == RDF.JSON


def test_meaning_plugin_checks_labels_and_unknown_terms(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(
        enums={"Known": {"permissible_values": {"CHILD": {"meaning": "TEST:2", "title": "child"}}}}
    )
    assert validate_enum_meanings(schema, path) == ()
    member(schema, "Known", "CHILD").meaning = "TEST:unknown"
    assert "not found" in validate_enum_meanings(schema, path)[0]


def test_byte_preparation_recomputes_membership_without_persistent_cache(tmp_path, monkeypatch):
    path = local_ontology(tmp_path)
    schema = view(
        enums={"Taxon": {"reachable_from": {"source_ontology": "test", "source_nodes": ["TEST:1"]}}}
    )
    monkeypatch.chdir(tmp_path)
    first = resolve_vocabularies_from_bytes(schema, {"test": path.read_bytes()})
    assert first[0].accepted_values == ("TEST:2", "TEST:3")
    assert first == resolve_vocabularies_from_bytes(schema, {"test": path.read_bytes()})
    assert list(tmp_path.iterdir()) == [path]


def test_structured_object_and_conflicting_occurrence_identity():
    a = dict(id="urn:assertion", subject="urn:s", predicate="urn:p", object={"roles": [1, 2]})
    graph = qualified_assertion_graph([a])
    assert graph.value(URIRef("urn:assertion"), RDF.object) == Literal(
        '{"roles":[1,2]}', datatype=RDF.JSON
    )
    with pytest.raises(OntologyError, match="conflicting assertion"):
        qualified_assertion_graph([a, dict(a, object={"roles": [2, 1]})])


def test_resolved_meanings_are_checked_and_unbound_prefixes_explicit(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(
        enums={
            "Known": {
                "permissible_values": {
                    "child": {"meaning": "TEST:2"},
                    "other": {"meaning": "OTHER:1"},
                }
            }
        }
    )
    result = resolve_vocabularies(schema, {"test": path})[0]
    assert "meaning:TEST:2:checked" in result.checks
    assert "meaning:OTHER:1:unchecked" in result.checks
    member(schema, "Known", "child").meaning = "TEST:missing"
    with pytest.raises(OntologyError, match="not found"):
        resolve_vocabularies(schema, {"test": path})


def test_nested_binding_plugin_uses_local_enum_membership(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(
        enums={"Allowed": {"concepts": ["TEST:2"]}},
        classes={
            "Term": {"attributes": {"id": {"range": "string"}}},
            "Annotation": {
                "attributes": {
                    "term": {
                        "range": "Term",
                        "inlined": True,
                        "bindings": [
                            {
                                "binds_value_of": "id",
                                "range": "Allowed",
                                "obligation_level": "REQUIRED",
                            }
                        ],
                    }
                }
            },
        },
    )
    assert validate_bindings(schema, "Annotation", {"term": {"id": "TEST:2"}}, path) == ()
    assert validate_bindings(schema, "Annotation", {"term": {"id": "TEST:3"}}, path)


def test_explicit_concept_unknown_in_supplied_ontology_is_invalid(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(enums={"A": {"concepts": ["TEST:missing"]}})
    with pytest.raises(OntologyError, match="not found"):
        resolve_vocabularies(schema, {"test": path})


def member(schema: SchemaView, name: str, value: str) -> PermissibleValue:
    definition = schema.get_enum(name)
    assert definition is not None
    values = definition.permissible_values
    assert isinstance(values, dict)
    result = values[value]
    assert isinstance(result, PermissibleValue)
    return result
