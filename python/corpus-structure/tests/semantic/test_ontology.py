"""Independent ontology, occurrence and conformance expectations."""

from pathlib import Path

import pytest
from linkml_runtime.linkml_model import PermissibleValue, SchemaDefinition
from linkml_runtime.linkml_model.meta import ReachabilityQuery
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from corpus_structure.semantic.ontology import (
    OntologyError,
    build_graph_artifacts,
    expand_enum,
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
            types=kwargs.pop("types", {"string": {"uri": "xsd:string", "base": "str"}}),
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


@pytest.mark.parametrize("operator", ["include", "minus"])
def test_nested_expression_concepts_are_validated_even_when_excluded(tmp_path, operator):
    path = local_ontology(tmp_path)
    schema = view(enums={"A": {operator: [{"include": [{"concepts": ["TEST:missing"]}]}]}})
    with pytest.raises(OntologyError, match="not found"):
        resolve_vocabularies(schema, {"test": path})


def test_nested_unbound_meaning_is_recorded_unchecked(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(enums={"A": {"include": [{"concepts": ["OTHER:1"]}]}})
    result = resolve_vocabularies(schema, {"test": path})[0]
    assert "meaning:OTHER:1:unchecked" in result.checks


def test_inherited_nested_concept_validation_keeps_parent_semantics(tmp_path):
    path = local_ontology(tmp_path)
    schema = view(
        enums={
            "A": {"include": [{"concepts": ["TEST:missing"]}]},
            "B": {"inherits": ["A"]},
        }
    )
    with pytest.raises(OntologyError, match="not found"):
        resolve_vocabularies(schema, {"test": path})


@pytest.mark.parametrize(
    "scope, constrained", [("shape", True), ("accepted_value", False), ("context", False)]
)
def test_graph_integrity_respects_constraint_scope_without_mutating_model(scope, constrained):
    from rdflib.namespace import OWL, SH

    schema = view(
        classes={
            "Record": {
                "class_uri": "ex:Record",
                "attributes": {
                    "value": {
                        "slot_uri": "ex:value",
                        "range": "string",
                        "required": True,
                        "maximum_cardinality": 1,
                        "pattern": "^[A-Z]+$",
                        "annotations": {"cs:constraint_scope": scope},
                    }
                },
            }
        }
    )
    source = schema.get_class("Record")
    assert source is not None
    before = str(schema.schema)
    artifacts = build_graph_artifacts(schema)
    shacl = Graph().parse(data=artifacts["shacl"], format="nt")
    owl = Graph().parse(data=artifacts["owl"], format="nt")
    assert bool(list(shacl.objects(None, SH.maxCount))) is constrained
    assert bool(list(shacl.objects(None, SH.minCount))) is constrained
    assert bool(list(shacl.objects(None, SH.pattern))) is constrained
    cardinalities = (
        OWL.cardinality,
        OWL.minCardinality,
        OWL.maxCardinality,
        OWL.qualifiedCardinality,
        OWL.minQualifiedCardinality,
        OWL.maxQualifiedCardinality,
    )
    restrictions = set(owl.subjects(OWL.onProperty, URIRef("https://example.org/value")))
    assert (
        any(
            list(owl.objects(node, predicate))
            for node in restrictions
            for predicate in cardinalities
        )
        is constrained
    )
    assert str(schema.schema) == before


def test_nonshape_inherited_slot_and_datatype_constraints_are_not_unconditional():
    from rdflib.namespace import SH

    schema = view(
        types={"string": {"uri": "xsd:string", "base": "str", "pattern": "^[A-Z]+$"}},
        slots={
            "value": {
                "slot_uri": "ex:value",
                "range": "string",
                "required": True,
                "maximum_cardinality": 1,
                "annotations": {"cs:constraint_scope": "accepted_value"},
            }
        },
        classes={"Parent": {"slots": ["value"]}, "Child": {"is_a": "Parent"}},
    )
    shapes = Graph().parse(data=build_graph_artifacts(schema)["shacl"], format="nt")
    assert not list(shapes.objects(None, SH.maxCount))
    assert not list(shapes.objects(None, SH.minCount))
    assert not list(shapes.objects(None, SH.pattern))


def test_profile_default_scope_is_applied_to_graph_projection():
    from rdflib.namespace import SH

    schema = view(
        classes={
            "Record": {
                "attributes": {
                    "value": {"range": "string", "required": True, "maximum_cardinality": 1}
                }
            }
        }
    )
    artifacts = build_graph_artifacts(schema, default_constraint_scope="occurrence")
    shapes = Graph().parse(data=artifacts["shacl"], format="nt")
    assert not list(shapes.objects(None, SH.maxCount))
    assert not list(shapes.objects(None, SH.minCount))


def test_shacl_nonconformance_has_located_diagnostics_and_invalid_shapes_are_errors():
    from corpus_structure.semantic.ontology import GraphShapeError, validate_graph

    data = Graph().parse(data='@prefix ex: <urn:> . ex:s ex:p "wrong" .', format="turtle")
    shapes = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:s>;
 sh:property [sh:path <urn:p>; sh:datatype xsd:integer] .""",
        format="turtle",
    )
    result = validate_graph(data, shapes)
    assert not result.conforms
    assert result.diagnostics[0].focus_node == "urn:s"
    assert result.diagnostics[0].path == "urn:p"
    assert result.diagnostics[0].constraint is not None
    assert result.diagnostics[0].constraint.endswith("DatatypeConstraintComponent")
    invalid = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:s>;
 sh:property [sh:path <urn:p>; sh:minCount "wrong"] .""",
        format="turtle",
    )
    with pytest.raises(GraphShapeError):
        validate_graph(data, invalid)


def test_generic_shacl_nested_paths_locate_failure_without_mutating_graphs():
    data = Graph().parse(
        data="""@prefix ex: <urn:> .
ex:source ex:condition [ex:count "invalid"] .""",
        format="turtle",
    )
    shapes = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:source>;
 sh:property [sh:path (<urn:condition> <urn:count>); sh:datatype xsd:integer] .""",
        format="turtle",
    )
    before = set(data), set(shapes)
    result = validate_graph(data, shapes)
    assert not result.conforms and result.outcome == "nonconformant"
    assert (set(data), set(shapes)) == before
    assert len(result.diagnostics) == 1
    failure = result.diagnostics[0]
    assert failure.focus_node == "urn:source" and failure.path is not None
    assert failure.constraint is not None and failure.constraint.endswith(
        "DatatypeConstraintComponent"
    )
    assert failure.source_shape is not None


@pytest.mark.parametrize("dataset", [False, True])
def test_graph_validation_keeps_supplied_data_shapes_and_ontology_operation_local(dataset):
    from rdflib import Dataset

    data = Dataset(default_union=False) if dataset else Graph()
    target = data.graph(URIRef("urn:source-graph")) if isinstance(data, Dataset) else data
    target.add((URIRef("urn:item"), URIRef("urn:count"), Literal(7)))
    shapes = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:item>;
 sh:property [sh:path <urn:count>; sh:minCount 1] .""",
        format="turtle",
    )
    ontology = Graph().parse(
        data="""@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<urn:Child> rdfs:subClassOf <urn:Parent> .""",
        format="turtle",
    )
    before = set(target), set(shapes), set(ontology)
    assert validate_graph(data, shapes, ontology).conforms
    assert (set(target), set(shapes), set(ontology)) == before
    if isinstance(data, Dataset):
        assert data.default_union is False


def test_generic_shacl_preserves_exact_large_integer_and_decimal_comparisons():
    from decimal import Decimal

    from rdflib.namespace import XSD

    data = Graph()
    subject, count, amount = map(URIRef, ("urn:item", "urn:count", "urn:amount"))
    data.add((subject, count, Literal(2**90)))
    precise = Literal(Decimal("0.10000000000000000001"))
    data.add((subject, amount, precise))
    shapes = Graph().parse(
        data=f"""@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:item>;
 sh:property [sh:path <urn:count>; sh:datatype xsd:integer; sh:minInclusive {2**90 - 1}];
 sh:property [sh:path <urn:amount>; sh:datatype xsd:decimal;
 sh:minExclusive "0.1"^^xsd:decimal; sh:maxExclusive "0.10000000000000000002"^^xsd:decimal] .""",
        format="turtle",
    )
    assert validate_graph(data, shapes).conforms
    observed = data.value(subject, count)
    assert isinstance(observed, Literal) and observed.toPython() == 2**90
    assert precise.datatype == XSD.decimal and str(precise) == "0.10000000000000000001"
    data.set((subject, amount, Literal(Decimal("0.10000000000000000002"))))
    assert not validate_graph(data, shapes).conforms


def test_generic_graph_validation_does_not_entail_reified_claims_or_run_shacl_rules():
    data = Graph().parse(
        data="""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
<urn:assertion:1> a rdf:Statement; rdf:subject <urn:a>; rdf:predicate <urn:owns>; rdf:object <urn:b> .
<urn:assertion:2> a rdf:Statement; rdf:subject <urn:a>; rdf:predicate <urn:owns>; rdf:object <urn:b> .""",
        format="turtle",
    )
    shapes = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:a>;
 sh:property [sh:path <urn:owns>; sh:minCount 1];
 sh:rule [a sh:TripleRule; sh:subject sh:this; sh:predicate <urn:owns>; sh:object <urn:b>] .""",
        format="turtle",
    )
    before = set(data)
    assert not validate_graph(data, shapes).conforms
    assert set(data) == before
    assert len(set(data.subjects(RDF.type, RDF.Statement))) == 2
    assert (URIRef("urn:a"), URIRef("urn:owns"), URIRef("urn:b")) not in data


def test_invalid_generic_shape_keeps_cause_and_trusted_current_context_through_tool_boundary():
    import json

    from fastmcp.exceptions import ToolError
    from pyshacl.errors import ConstraintLoadError

    from corpus_structure.semantic.ontology import GraphExecutionError, GraphShapeError
    from corpus_structure.semantic.refusals import (
        located_failure_context,
        tool_refusals,
        trusted_operation_model_id,
    )
    from semantic.operation_reporting_support import prepared

    actual = prepared()
    invalid = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
<urn:shape> a sh:NodeShape; sh:targetNode <urn:missing>;
 sh:property [sh:path <urn:field>; sh:minCount "wrong"] .""",
        format="turtle",
    )

    @tool_refusals(GraphShapeError, GraphExecutionError)
    def check_supplied_graph():
        with located_failure_context(actual, scope="supplied generic graph"):
            return validate_graph(Graph(), invalid)

    with pytest.raises(ToolError) as caught:
        check_supplied_graph()
    assert isinstance(caught.value.__cause__, GraphShapeError)
    assert isinstance(caught.value.__cause__.__cause__, ConstraintLoadError)
    failure = json.loads(str(caught.value))
    assert failure["code"] == "GraphShapeError"
    report = failure["validation"]
    assert report["release_id"] == actual.release_id
    assert report["model_id"] == trusted_operation_model_id(actual)
    assert report["observations"][0]["category"] == "invalid_shape"
    assert report["observations"][0]["model_path"] == "graph/shapes"
    assert report["observations"][0]["scope"] == "supplied generic graph"


def test_generic_graph_library_failure_keeps_cause_and_context_through_cli_boundary(
    monkeypatch, capsys
):
    import json

    import typer
    from pyshacl.errors import ReportableRuntimeError

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic import ontology
    from corpus_structure.semantic.ontology import GraphExecutionError, GraphShapeError
    from corpus_structure.semantic.refusals import trusted_operation_model_id
    from semantic.operation_reporting_support import prepared

    original = ReportableRuntimeError("controlled library failure")
    calls = []

    def unavailable(data, **options):
        calls.append((data, options))
        raise original

    monkeypatch.setattr(ontology, "validate", unavailable)
    actual = prepared()
    with (
        pytest.raises(typer.Exit) as caught,
        failure_boundary(True, expected=(GraphShapeError, GraphExecutionError)) as context,
    ):
        context.bind(actual, scope="supplied generic graph")
        validate_graph(Graph(), Graph())
    assert len(calls) == 1 and isinstance(calls[0][0], Graph)
    assert calls[0][1] == dict(
        shacl_graph=calls[0][1]["shacl_graph"],
        ont_graph=None,
        inference="none",
        inplace=True,
        advanced=False,
        do_owl_imports=False,
    )
    assert isinstance(caught.value.__context__, GraphExecutionError)
    assert caught.value.__context__.__cause__ is original
    failure = json.loads(capsys.readouterr().out)["error"]
    assert failure["code"] == "GraphExecutionError"
    report = failure["validation"]
    assert report["release_id"] == actual.release_id and report[
        "model_id"
    ] == trusted_operation_model_id(actual)
    assert report["observations"][0]["category"] == "validator_failure"
    assert report["observations"][0]["model_path"] == "graph/validator"
    assert report["observations"][0]["scope"] == "supplied generic graph"
