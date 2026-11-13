"""Independent SQL execution fixtures for the closed binding normal form."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, create_engine

from corpus_structure.semantic.data_operation_bindings import (
    PopulationBinding,
    ProjectionBinding,
    ProjectionField,
    compile_binding,
    execute_binding,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BindingExpression,
    BindingField,
    BindingOperand,
    EffectiveDataOperationModel,
    EffectiveIdentity,
    EffectiveKind,
    EffectiveOperation,
    ImplementationCapabilities,
    InputSupport,
    OperationRole,
    RelationalBinding,
    read_effective_data_operations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact


def model(
    expression,
    *,
    collection="set",
    minimum=1,
    maximum=None,
    presence="required",
    parameters=None,
    names=("items",),
):
    roles = tuple(
        OperationRole(
            name,
            "urn:item",
            "input",
            minimum,
            maximum,
            collection,
            presence,
            InputSupport("exact", "original", "complete", identity_requirements=("episode",)),
        )
        for name in names
    )
    operation = EffectiveOperation(
        "urn:op",
        "derivation",
        "document",
        (),
        roles,
        (),
        (),
        "complete",
        ("produced",),
        "exact",
        (),
        (),
        (),
        (),
        ImplementationCapabilities(("scalar",), "none", "boundary", "immutable"),
        "revision-1",
        canonical_bytes(parameters or {}),
        (),
        (),
        None,
        (),
        "urn:binding",
    )
    return EffectiveDataOperationModel(
        MODEL_VERSION,
        (EffectiveKind("urn:item", "Item", "class", b"{}"),),
        (operation,),
        (RelationalBinding("urn:binding", "urn:op", expression),),
        (),
        (),
        identities=(
            EffectiveIdentity("urn:op", "definition", "definition:fixed", b"{}"),
            EffectiveIdentity("urn:op", "eligibility", "eligibility:fixed", b"{}"),
            EffectiveIdentity("urn:item", "kind", "kind:fixed", b"{}"),
        ),
    )


@pytest.fixture
def storage():
    table = Table(
        "admitted",
        MetaData(),
        *(
            Column(name, String)
            for name in (
                "product",
                "kind_contract",
                "subject",
                "original_source",
                "member",
                "provider_identity",
                "alternative_identity",
            )
        ),
        *(
            Column(name, JSON)
            for name in ("analyzed_scope", "coverage", "support_episodes", "support_evidence")
        ),
        Column("position", Integer),
        Column("multiplicity", Integer),
        Column("value", Integer),
        Column("base", String),
    )
    engine = create_engine("sqlite://")
    table.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            table.insert(),
            [
                dict(
                    product=f"p{value}",
                    kind_contract="kind:fixed",
                    subject="doc",
                    original_source="source",
                    member=f"m{value}",
                    provider_identity=None,
                    alternative_identity=None,
                    analyzed_scope={"page": 1},
                    coverage={"complete": True},
                    support_episodes=[f"ep{value}"],
                    support_evidence={"trust": "pinned"},
                    position=3 - value,
                    multiplicity=1,
                    value=value,
                    base="b",
                )
                for value in (1, 2, 3)
            ],
        )
        projection = ProjectionBinding(
            "urn:item",
            table,
            (
                ProjectionField("value", "value", "integer"),
                ProjectionField("base", "base", "string"),
            ),
            b'{"trust":"pinned"}',
        )
        yield connection, table, projection


def field(name="value", role="items"):
    return BindingOperand("field", "integer", BindingField(role, "urn:item", name))


def test_sql_range_membership_defaults_and_exact_identity(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "all",
        children=(
            BindingExpression(
                "range",
                operands=(
                    field(),
                    BindingOperand("literal", "integer", value=b'["integer","2"]'),
                    BindingOperand("parameter", "integer", name="maximum"),
                ),
            ),
            BindingExpression(
                "membership",
                operands=(field(), BindingOperand("parameter", "integer", name="allowed")),
            ),
        ),
    )
    compiled = compile_binding(
        model(expression, parameters={"maximum": {"value_type": "integer", "default": 3}}),
        "urn:op",
        (projection,),
        subject="doc",
        parameters={"allowed": [2, 3]},
    )
    result = execute_binding(connection, compiled)
    assert result.status == "ready"
    assert {m.product for m in result.roles[0].members} == {"p2", "p3"}
    assert result.roles[0].members[0].support_episodes
    assert result.definition == "definition:fixed"
    assert json.loads(result.parameters) == {"allowed": [2, 3], "maximum": 3}
    resolved = result.resolved(
        inference="exact", authorization=b"{}", trust_evidence=b"{}", execution_profile="native"
    )
    assert resolved.roles == result.roles


def test_join_distinct_sequence_order_and_cardinality_are_sql(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "all",
        children=(
            BindingExpression(
                "join",
                roles=("left", "right"),
                fields=(
                    BindingField("left", "urn:item", "base"),
                    BindingField("right", "urn:item", "base"),
                ),
            ),
            BindingExpression("distinct", roles=("left", "right")),
            BindingExpression(
                "literal",
                fields=(BindingField("left", "urn:item", "value"),),
                value=b'["integer","1"]',
            ),
        ),
    )
    result = execute_binding(
        connection,
        compile_binding(
            model(expression, collection="sequence", names=("left", "right")),
            "urn:op",
            (projection,),
            subject="doc",
        ),
    )
    assert result.sufficient
    assert [m.product for m in result.roles[0].members] == ["p1"]
    assert [m.product for m in result.roles[1].members] == ["p3", "p2"]


def test_null_is_unknown_not_empty_or_absent(storage):
    connection, table, projection = storage
    connection.execute(table.update().values(value=None))
    result = execute_binding(
        connection,
        compile_binding(
            model(
                BindingExpression(
                    "membership",
                    operands=(field(), BindingOperand("parameter", "integer", name="allowed")),
                )
            ),
            "urn:op",
            (projection,),
            subject="doc",
            parameters={"allowed": [2]},
        ),
    )
    assert result.status == "unknown"
    assert any(reason.code == "unknown-comparison" for reason in result.reasons)


def test_closed_population_required_for_quantification_and_absence(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "forall",
        roles=("items",),
        population="items",
        children=(BindingExpression("scan", roles=("items",)),),
    )
    open_result = execute_binding(
        connection, compile_binding(model(expression), "urn:op", (projection,), subject="doc")
    )
    assert open_result.status == "awaiting-population"
    population = PopulationBinding(
        "items", "population:one", True, ("m1", "m2", "m3"), b'{"closed":true}'
    )
    result = execute_binding(
        connection,
        compile_binding(
            model(expression), "urn:op", (projection,), subject="doc", populations=(population,)
        ),
    )
    assert result.sufficient
    assert json.loads(result.roles[0].population_witness)["identity"] == "population:one"
    missing = replace(population, members=(*population.members, "m4"))
    assert (
        execute_binding(
            connection,
            compile_binding(
                model(expression), "urn:op", (projection,), subject="doc", populations=(missing,)
            ),
        ).status
        == "not-applicable"
    )


def test_present_empty_closed_absent_and_unavailable_remain_distinct(storage):
    connection, _, projection = storage
    optional = model(BindingExpression("scan", roles=("items",)), minimum=0, presence="optional")
    result = execute_binding(
        connection, compile_binding(optional, "urn:op", (projection,), subject="missing")
    )
    assert (
        result.sufficient and result.roles[0].state == "present" and result.roles[0].members == ()
    )
    population = PopulationBinding("items", "population:empty", True, (), b'{"closed":true}')
    absent = execute_binding(
        connection,
        compile_binding(
            optional, "urn:op", (projection,), subject="missing", populations=(population,)
        ),
    )
    assert absent.sufficient and absent.roles[0].state == "known-absent"
    unavailable = execute_binding(
        connection, compile_binding(optional, "urn:op", (), subject="doc")
    )
    assert unavailable.status == "unavailable"


def test_projection_contract_and_typed_demand_refuse_unsafe_inputs(storage):
    _, table, projection = storage
    with pytest.raises(ValueError, match="admission evidence"):
        ProjectionBinding("urn:item", table, (), b"")
    expression = BindingExpression(
        "range",
        operands=(
            field(),
            BindingOperand("parameter", "integer", name="lo"),
            BindingOperand("parameter", "integer", name="hi"),
        ),
    )
    with pytest.raises(ValueError, match="missing frozen demand parameter"):
        compile_binding(model(expression), "urn:op", (projection,), subject="doc")
    with pytest.raises(ValueError, match="does not match"):
        compile_binding(
            model(expression),
            "urn:op",
            (projection,),
            subject="doc",
            parameters={"lo": True, "hi": 3},
        )


def test_archived_v1_shape_is_exact_and_current_defaults_never_enter():
    source = model(BindingExpression("scan", roles=("items",)))
    archived = replace(source, version="data-operation-model-v1")
    content = archived.content
    assert b'"operands"' not in content and b'"potential_dependencies"' not in content
    assert read_effective_data_operations(content).content == content
    corrupt = json.loads(content)
    corrupt["bindings"][0]["expression"]["operands"] = []
    with pytest.raises(ValueError):
        read_effective_data_operations(canonical_bytes(corrupt))


def declaration(identifier="urn:op", **changes):
    return {
        "id": identifier,
        "profile": "derivation",
        "subject": "document",
        "context": [],
        "roles": [
            {
                "name": "items",
                "kind": "integer",
                "direction": "input",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
                "parameter": "x",
                "support": {
                    "provenance": "exact",
                    "source": "original",
                    "coverage": "complete",
                    "identity_requirements": ["episode"],
                },
            },
            {
                "name": "result",
                "kind": "integer",
                "direction": "output",
                "minimum": 1,
                "maximum": 1,
                "collection": "scalar",
                "presence": "required",
            },
        ],
        "applicability": [],
        "invariants": [],
        "coverage": "complete",
        "outcomes": ["produced"],
        "precision": "exact",
        "dependencies": [],
        "effects": [],
        "capabilities": {
            "forms": ["scalar"],
            "preparation": "none",
            "cancellation": "boundary",
            "ownership": "immutable",
        },
        "behavior": "revision-1",
        "parameters": {},
        "binding": {"operator": "scan", "roles": ["items"]},
        **changes,
    }


def test_potential_producer_cycles_do_not_become_mandatory_prerequisites():
    left = declaration("urn:left", potential_dependencies=["urn:right"])
    right = declaration("urn:right", potential_dependencies=["urn:left"])
    product = compile_data_operations(
        declarations=(
            SourceArtifact(
                "ops.json", canonical_bytes({"version": MODEL_VERSION, "operations": [left, right]})
            ),
        )
    )
    assert {
        edge.relation for edge in product.edges if edge.source in {"urn:left", "urn:right"}
    } >= {"potential_operation_dependency"}
    assert all(not op.dependencies for op in product.operations)


def test_python_field_facts_share_schema_property_shape_and_typed_binding():
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    raw = declaration()
    raw["roles"][0]["kind"] = "urn:item"
    raw["kinds"] = [{"id": "urn:item", "python": "fixture.Item"}]
    raw["binding"] = {
        "operator": "range",
        "operands": [
            {
                "kind": "field",
                "value_type": "integer",
                "field": {"role": "items", "projection": "urn:item", "field": "value"},
            },
            {"kind": "literal", "value_type": "integer", "value": 1},
            {"kind": "parameter", "value_type": "integer", "name": "maximum"},
        ],
    }
    source = f"class Item:\n    value: int\ndef derive(x: Item) -> int:\n    return x.value\nderive__data_operation__ = {raw!r}\n"
    product = compile_data_operations(
        python_sources=PythonSourceCollection(
            (PythonSource("fixture", source.encode(), "fixture.py"),)
        )
    )
    facts = json.loads(
        next(kind.facts for kind in product.kinds if kind.semantic_id == "urn:item/property/value")
    )
    assert facts["range"] == "primitive:integer" and facts["required"] is True
    assert any(
        edge.source == "urn:item" and edge.target == "urn:item/property/value"
        for edge in product.edges
    )
    assert read_effective_data_operations(product.content).content == product.content
    wrong = source.replace("'kind': 'urn:item'", "'kind': 'string'")
    with pytest.raises(Exception, match="role kind differs"):
        compile_data_operations(
            python_sources=PythonSourceCollection(
                (PythonSource("fixture", wrong.encode(), "fixture.py"),)
            )
        )
