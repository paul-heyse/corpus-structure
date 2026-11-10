"""Independent ontology, occurrence and conformance expectations."""

from functools import lru_cache
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


def test_qualified_projection_exposes_structured_paths_and_required_closure():

    occurrence = {
        "id": "urn:occ:1",
        "subject": "urn:entity:1",
        "predicate": "urn:p",
        "object": "value",
        "condition": {"roles": ["same", "same"]},
    }
    projection = _bound_projection(
        "r",
        "z",
        3,
        "qualified-validation",
        (occurrence,),
        {
            "urn:entity:1": {"kind": "entity"},
            "urn:proof:1": {"kind": "direct", "premises": [URIRef("urn:occ:1")]},
        },
        {"urn:occ:1": ("urn:proof:1",)},
    )
    graph = projection.graph()
    assert (URIRef("urn:occ:1"), CS.requiredNode, URIRef("urn:proof:1")) in graph
    condition = graph.value(URIRef("urn:occ:1"), CS.conditionNode)
    roles = graph.value(condition, CS.roles)
    members = set(graph.objects(roles, CS.member))
    assert len(members) == 2
    assert {int(str(graph.value(member, CS.position))) for member in members} == {0, 1}
    assert {str(graph.value(member, CS.value)) for member in members} == {"same"}
    from dataclasses import replace

    with pytest.raises(OntologyError, match="missing required related node"):
        replace(projection, related_nodes={}).graph()


def test_projected_validation_uses_nested_qualified_path():
    from corpus_structure.semantic.ontology import (
        validate_projected_graph,
    )

    row = {
        "id": "urn:occ:1",
        "subject": "urn:s",
        "predicate": "urn:p",
        "object": "v",
        "condition": {"count": "invalid"},
    }
    projection = _bound_projection(
        "r", "z", 0, "graph-validation", (row,), {"urn:s": {"kind": "entity"}}, {}
    )
    shapes = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix cs: <https://corpus-structure.dev/semantic/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<urn:shape> a sh:NodeShape; sh:targetClass cs:Record;
 sh:property [sh:path cs:count; sh:datatype xsd:integer] .""",
        format="turtle",
    )
    result = validate_projected_graph(projection, shapes)
    assert not result.conforms
    assert result.validation is not None
    located = result.validation.model_dump(mode="json")
    assert located["release_id"] == projection.release_id
    assert located["model_id"] == projection.contract_binding.execution_model_id
    observation = located["observations"][0]
    assert observation["operation"] == "graph_validate"
    assert observation["model_path"]
    assert observation["input_path"]
    assert observation["scope"] == "z@0/graph-validation"
    from hashlib import sha256

    assert located["evidence"]["digest"] == sha256(result.report).hexdigest()
    assert located["evidence"]["kind"] == "marker"
    assert located["evidence"]["sensitivity"] == "safe"


def test_graph_operation_invalid_shape_retains_bound_diagnostic_through_tool_boundary():
    import json

    from fastmcp.exceptions import ToolError
    from pyshacl.errors import ConstraintLoadError

    from corpus_structure.semantic.ontology import (
        GraphExecutionError,
        GraphShapeError,
        validate_projected_graph,
    )
    from corpus_structure.semantic.refusals import tool_refusals

    projection = _bound_projection(
        "release:graph-errors", "realization:graph-errors", 7, "graph-errors", (), {}, {}
    )
    invalid = Graph().parse(
        data="""@prefix sh: <http://www.w3.org/ns/shacl#> .
<urn:invalid-shape> a sh:NodeShape; sh:targetNode <urn:missing>;
 sh:property [sh:path <urn:field>; sh:minCount "wrong"] .""",
        format="turtle",
    )
    # This is the maintained generic tool error adapter around the actual
    # model-owned operation, without registering a new public graph tool.
    guarded = tool_refusals(GraphShapeError, GraphExecutionError)(validate_projected_graph)
    with pytest.raises(ToolError) as caught:
        guarded(projection, invalid)
    graph_error = caught.value.__cause__
    assert isinstance(graph_error, GraphShapeError)
    raw_cause = graph_error.__cause__
    assert isinstance(raw_cause, ConstraintLoadError)
    assert "sh:minCount" in str(raw_cause) and "xsd:integer" in str(raw_cause)
    failure = json.loads(str(caught.value))
    assert failure["code"] == "GraphShapeError"
    assert failure["message"] == (
        "Graph validation failed; request correction detail for structural paths."
    )
    located = failure["validation"]
    assert located["release_id"] == "release:graph-errors"
    assert located["model_id"] == projection.contract_binding.execution_model_id
    assert located["complete"] is True
    assert located["observations"] == [
        {
            "category": "invalid_shape",
            "code": "invalid_shape",
            "model_path": "graph/shapes",
            "operation": "graph_validate",
            "scope": "realization:graph-errors@7/graph-errors",
            "message": "Boundary validation failed: GraphShapeError",
        }
    ]


def test_graph_operation_controlled_dependency_failure_reaches_located_cli_boundary(
    monkeypatch, capsys
):
    import json

    import typer
    from pyshacl.errors import ReportableRuntimeError

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic import ontology
    from corpus_structure.semantic.ontology import GraphExecutionError, GraphShapeError

    projection = _bound_projection(
        "release:graph-errors", "realization:graph-errors", 7, "graph-errors", (), {}, {}
    )
    dependency_error = ReportableRuntimeError("controlled pySHACL dependency failure")
    calls = []

    def unavailable(data_graph, **kwargs):
        calls.append(data_graph)
        raise dependency_error

    # A controlled library-boundary failure tests propagation through the real
    # operation and adapter; it does not qualify live infrastructure availability.
    monkeypatch.setattr(ontology, "validate", unavailable)
    with (
        pytest.raises(typer.Exit) as caught,
        failure_boundary(True, expected=(GraphShapeError, GraphExecutionError)),
    ):
        ontology.validate_projected_graph(projection)
    assert len(calls) == 1
    assert isinstance(calls[0], Graph)
    graph_error = caught.value.__context__
    assert isinstance(graph_error, GraphExecutionError)
    assert graph_error.__cause__ is dependency_error
    failure = json.loads(capsys.readouterr().out)["error"]
    assert failure["code"] == "GraphExecutionError"
    assert failure["message"] == (
        "Graph validation failed; request correction detail for structural paths."
    )
    located = failure["validation"]
    assert located["release_id"] == "release:graph-errors"
    assert located["model_id"] == projection.contract_binding.execution_model_id
    assert located["complete"] is True
    assert located["observations"] == [
        {
            "category": "validator_failure",
            "code": "runtime_failure",
            "model_path": "graph/validator",
            "operation": "graph_validate",
            "scope": "realization:graph-errors@7/graph-errors",
            "message": "Boundary validation failed: GraphExecutionError",
        }
    ]


def test_projected_null_remains_distinct_from_absence_and_literal_text():

    row = {
        "id": "urn:occ:1",
        "subject": "urn:s",
        "predicate": "urn:p",
        "object": None,
        "qualification": {"null": None, "text": "None"},
    }
    graph = _bound_projection(
        "r", "z", 0, "graph-validation", (row,), {"urn:s": {"kind": "entity"}}, {}
    ).graph()
    qualification = graph.value(URIRef("urn:occ:1"), CS.qualificationNode)
    null = graph.value(qualification, CS.null)
    assert (null, RDF.type, CS.Null) in graph
    assert graph.value(qualification, CS.text) == Literal("None")
    assert graph.value(qualification, CS.absent) is None


def test_typed_graph_references_derive_transitive_closure_without_reference_map():
    from dataclasses import replace

    from corpus_structure.semantic.ontology import QualifiedGraphReference

    row = {
        "id": "urn:occ",
        "subject": QualifiedGraphReference("urn:entity"),
        "predicate": "urn:p",
        "object": "value",
        "qualification": {"proof": QualifiedGraphReference("urn:proof")},
    }
    projection = _bound_projection(
        "r",
        "z",
        0,
        "graph-validation",
        (row,),
        {
            "urn:entity": {"kind": "entity"},
            "urn:proof": {"premise": QualifiedGraphReference("urn:evidence")},
            "urn:evidence": {"kind": "evidence"},
        },
        {},
    )
    graph = projection.graph()
    assert (URIRef("urn:proof"), CS.requiredNode, URIRef("urn:evidence")) in graph
    nodes = dict(projection.related_nodes)
    del nodes["urn:evidence"]
    with pytest.raises(OntologyError, match="missing required related node"):
        replace(projection, related_nodes=nodes).graph()


def test_reified_collection_shapes_reject_duplicate_member_positions():
    from corpus_structure.semantic.ontology import qualified_projection_shapes, validate_graph

    graph = Graph()
    parent, a, b = map(URIRef, ("urn:collection", "urn:a", "urn:b"))
    graph.add((parent, RDF.type, CS.Collection))
    for member in (a, b):
        graph.add((parent, CS.member, member))
        graph.add((member, RDF.type, CS.CollectionMember))
        graph.add((member, CS.position, Literal(0)))
        graph.add((member, CS.value, Literal("same")))
    assert not validate_graph(graph, qualified_projection_shapes()).conforms


def test_qualified_projection_refuses_node_binding_relabeling():

    row = {"id": "urn:occ", "subject": "urn:s", "predicate": "urn:p", "object": "value"}
    projection = _bound_projection(
        "r",
        "z",
        2,
        "graph-validation",
        (row,),
        {"urn:s": {"kind": "entity", "realization_id": "other"}},
        {},
    )
    with pytest.raises(OntologyError, match="wrong graph node scope"):
        projection.graph()


def test_identity_exclusions_are_qualified_constraints_with_complete_closure():
    from dataclasses import replace

    from rdflib.namespace import OWL

    from corpus_structure.semantic.ontology import (
        QualifiedGraphReference,
        validate_projected_graph,
    )

    first = {
        "id": "urn:exclusion:first",
        "left": QualifiedGraphReference("urn:entity:a"),
        "right": QualifiedGraphReference("urn:entity:b"),
        "evidence": (QualifiedGraphReference("urn:evidence:first"),),
        "reason": "source distinguishes the entities",
    }
    second = {**first, "id": "urn:exclusion:second"}
    projection = _bound_projection(
        "release",
        "realization",
        2,
        "qualified-identity-exclusions",
        (),
        {
            "urn:entity:a": {"kind": "entity"},
            "urn:entity:b": {"kind": "entity"},
            "urn:evidence:first": {"kind": "evidence"},
        },
        {},
        (first, second),
    )
    graph = projection.graph()
    assert set(graph.subjects(RDF.type, CS.IdentityExclusion)) == {
        URIRef("urn:exclusion:first"),
        URIRef("urn:exclusion:second"),
    }
    assert not list(graph.triples((None, OWL.differentFrom, None)))
    assert (URIRef("urn:exclusion:first"), CS.left, URIRef("urn:entity:a")) in graph
    assert (URIRef("urn:exclusion:first"), CS.requiredNode, URIRef("urn:evidence:first")) in graph
    assert validate_projected_graph(projection).conforms
    with pytest.raises(OntologyError, match="missing required related node"):
        replace(projection, related_nodes={"urn:entity:a": {}}).graph()
    with pytest.raises(OntologyError, match="endpoints collapse"):
        replace(projection, identity_exclusions=({**first, "right": first["left"]},)).graph()
    with pytest.raises(OntologyError, match="typed endpoint references"):
        replace(projection, identity_exclusions=({**first, "left": "urn:entity:a"},)).graph()
    with pytest.raises(OntologyError, match="typed evidence"):
        replace(projection, identity_exclusions=({**first, "evidence": ()},)).graph()


def _bound_projection(*args, **kwargs):
    """Explicit trusted contract fixture; each test supplies its independent node universe."""
    from corpus_structure.semantic.ontology import GraphProjectionBinding, QualifiedGraphProjection

    model = _graph_model()
    contract = next(p for p in model.projections if p.id == "graph_validation")
    roots = tuple(str(row["id"]) for row in args[4])
    if len(args) > 7:
        roots += tuple(str(row["id"]) for row in args[7])
    return QualifiedGraphProjection(
        *args,
        contract_binding=GraphProjectionBinding(
            args[0],
            model.model_id,
            contract,
            next(op.outcomes for op in model.operations if op.id == "graph_validate"),
        ),
        source_universe=roots,
        snapshot_guard=lambda: True,
        **kwargs,
    )


@lru_cache(maxsize=1)
def _graph_model():
    from corpus_structure.semantic.contracts import (
        compile_execution_model,
        trusted_execution_inputs,
    )

    return compile_execution_model(trusted_execution_inputs())


def test_graph_contract_and_snapshot_are_enforced():
    from dataclasses import replace

    projection = _bound_projection(
        "r", "z", 0, "instance-label", (), {"urn:e": {"kind": "entity"}}, {}
    )
    with pytest.raises(OntologyError, match="wrong graph contract release"):
        replace(
            projection, contract_binding=replace(projection.contract_binding, release_id="other")
        ).graph()
    with pytest.raises(OntologyError, match="snapshot is closed"):
        replace(projection, snapshot_guard=lambda: False).graph()
    with pytest.raises(OntologyError, match="source universe"):
        replace(projection, source_universe=("urn:missing",)).graph()
    with pytest.raises(OntologyError, match="node kind"):
        replace(projection, related_nodes={"urn:e": {"kind": "unmodeled"}}).graph()


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
