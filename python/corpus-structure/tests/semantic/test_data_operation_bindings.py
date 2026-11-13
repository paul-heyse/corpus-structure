"""Independent SQL execution fixtures for the closed binding normal form."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Literal

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
    collection: Literal["scalar", "sequence", "bag", "set"] = "set",
    minimum: int = 1,
    maximum: int | None = None,
    presence: Literal["required", "optional", "alternative"] = "required",
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
    assert result.roles[0].population_witness is not None
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
    source = (
        "class Item:\n    value: int\n"
        "def derive(x: Item) -> int:\n    return x.value\n"
        f"derive__data_operation__ = {raw!r}\n"
    )
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


def test_optional_demand_filter_preserves_absence_and_explicit_value(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "optional",
        roles=("items",),
        children=(
            BindingExpression(
                "equal",
                operands=(field(), BindingOperand("parameter", "integer", name="occurrence")),
            ),
        ),
    )
    product = model(
        expression, parameters={"occurrence": {"value_type": "integer", "required": False}}
    )
    unfiltered = execute_binding(
        connection, compile_binding(product, "urn:op", (projection,), subject="doc")
    )
    filtered = execute_binding(
        connection,
        compile_binding(
            product, "urn:op", (projection,), subject="doc", parameters={"occurrence": 2}
        ),
    )
    assert {member.product for member in unfiltered.roles[0].members} == {"p1", "p2", "p3"}
    assert [member.product for member in filtered.roles[0].members] == ["p2"]
    with pytest.raises(ValueError):
        compile_binding(
            product, "urn:op", (projection,), subject="doc", parameters={"occurrence": None}
        )


def test_frozen_branch_selects_only_declared_alternative(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "choice",
        choice_parameter="producer",
        children=(
            BindingExpression("scan", roles=("left",)),
            BindingExpression("scan", roles=("right",)),
        ),
    )
    product = model(expression, names=("left", "right"), minimum=0, presence="optional")
    result = execute_binding(
        connection,
        compile_binding(
            product, "urn:op", (projection,), subject="doc", choices={"producer": "right"}
        ),
    )
    assert result.sufficient
    assert result.roles[0].state == "known-absent" and result.roles[0].population_witness
    assert {member.product for member in result.roles[1].members} == {"p1", "p2", "p3"}
    with pytest.raises(ValueError, match="exactly one"):
        compile_binding(
            product, "urn:op", (projection,), subject="doc", choices={"producer": "unknown"}
        )


def test_population_scopes_output_and_member_distinctness(storage):
    connection, table, projection = storage
    population = PopulationBinding(
        "retained", "population:subset", True, ("m2",), b'{"closed":true}'
    )
    expression = BindingExpression(
        "forall",
        roles=("items",),
        population="retained",
        children=(BindingExpression("scan", roles=("items",)),),
    )
    result = execute_binding(
        connection,
        compile_binding(
            model(expression), "urn:op", (projection,), subject="doc", populations=(population,)
        ),
    )
    assert [member.member for member in result.roles[0].members] == ["m2"]
    assert result.roles[0].population_witness is not None
    assert json.loads(result.roles[0].population_witness)["identity"] == "population:subset"
    connection.execute(table.update().values(product="same-product"))
    pair = model(BindingExpression("distinct", roles=("left", "right")), names=("left", "right"))
    distinct = execute_binding(
        connection, compile_binding(pair, "urn:op", (projection,), subject="doc")
    )
    # Row-pair matches cannot silently become incompatible whole role bundles.
    assert distinct.status == "not-applicable"
    assert any(reason.code == "bundle-relation" for reason in distinct.reasons)
    fixed = replace(
        pair,
        bindings=(
            replace(
                pair.bindings[0],
                expression=BindingExpression(
                    "all",
                    children=(
                        pair.bindings[0].expression,
                        BindingExpression(
                            "literal",
                            fields=(BindingField("left", "urn:item", "value"),),
                            value=b'["integer","1"]',
                        ),
                        BindingExpression(
                            "literal",
                            fields=(BindingField("right", "urn:item", "value"),),
                            value=b'["integer","2"]',
                        ),
                    ),
                ),
            ),
        ),
    )
    selected = execute_binding(
        connection, compile_binding(fixed, "urn:op", (projection,), subject="doc")
    )
    assert selected.sufficient
    assert selected.roles[0].members[0].member == "m1"
    assert selected.roles[1].members[0].member == "m2"


def test_bag_multiplicity_and_sequence_ordinal_defects_remain_explicit(storage):
    connection, table, projection = storage
    connection.execute(table.update().where(table.c.value == 2).values(multiplicity=3))
    bag = model(BindingExpression("scan", roles=("items",)), collection="bag", minimum=5, maximum=5)
    result = execute_binding(
        connection, compile_binding(bag, "urn:op", (projection,), subject="doc")
    )
    assert result.sufficient and sum(member.multiplicity for member in result.roles[0].members) == 5
    sequence = replace(
        bag,
        operations=(
            replace(
                bag.operations[0],
                roles=(replace(bag.operations[0].roles[0], collection="sequence"),),
            ),
        ),
    )
    invalid = execute_binding(
        connection, compile_binding(sequence, "urn:op", (projection,), subject="doc")
    )
    assert invalid.status == "invalid"
    connection.execute(table.update().values(multiplicity=1, position=0))
    invalid = execute_binding(
        connection, compile_binding(sequence, "urn:op", (projection,), subject="doc")
    )
    assert invalid.status == "invalid" and any(
        reason.code == "sequence-ordinal" for reason in invalid.reasons
    )


def test_unknown_kind_and_unadmitted_fingerprint_cannot_be_ready(storage):
    connection, table, projection = storage
    product = model(BindingExpression("scan", roles=("items",)))
    incomplete = replace(
        product,
        identities=tuple(identity for identity in product.identities if identity.domain != "kind"),
    )
    result = execute_binding(
        connection, compile_binding(incomplete, "urn:op", (projection,), subject="doc")
    )
    assert result.status == "unknown" and any(
        reason.code == "unknown-contract" for reason in result.reasons
    )
    connection.execute(table.update().values(kind_contract="kind:other"))
    rejected = execute_binding(
        connection, compile_binding(product, "urn:op", (projection,), subject="doc")
    )
    assert not rejected.sufficient and rejected.roles[0].members == ()


def test_optional_role_filter_never_suppresses_required_peer(storage):
    connection, _, projection = storage
    optional_filter = BindingExpression(
        "optional",
        roles=("right",),
        children=(
            BindingExpression(
                "literal",
                fields=(BindingField("right", "urn:item", "value"),),
                value=b'["integer","99"]',
            ),
        ),
    )
    product = model(
        BindingExpression(
            "all", children=(BindingExpression("scan", roles=("left",)), optional_filter)
        ),
        names=("left", "right"),
    )
    operation = product.operations[0]
    product = replace(
        product,
        operations=(
            replace(
                operation,
                roles=(
                    operation.roles[0],
                    replace(operation.roles[1], minimum=0, presence="optional"),
                ),
            ),
        ),
    )
    result = execute_binding(
        connection, compile_binding(product, "urn:op", (projection,), subject="doc")
    )
    assert result.sufficient
    assert {member.product for member in result.roles[0].members} == {"p1", "p2", "p3"}
    assert result.roles[1].state == "present" and result.roles[1].members == ()


def test_scoped_absence_retains_required_positive_sibling(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "all",
        children=(
            BindingExpression("scan", roles=("left",)),
            BindingExpression("absent", roles=("right",), population="forbidden"),
        ),
    )
    product = model(expression, names=("left", "right"))
    operation = product.operations[0]
    product = replace(
        product,
        operations=(
            replace(
                operation,
                roles=(
                    operation.roles[0],
                    replace(operation.roles[1], minimum=0, presence="optional"),
                ),
            ),
        ),
    )
    population = PopulationBinding("forbidden", "population:empty", True, (), b'{"closed":true}')
    result = execute_binding(
        connection,
        compile_binding(product, "urn:op", (projection,), subject="doc", populations=(population,)),
    )
    assert result.sufficient
    assert {member.product for member in result.roles[0].members} == {"p1", "p2", "p3"}
    assert result.roles[1].state == "known-absent" and result.roles[1].members == ()
    forbidden = replace(population, identity="population:one", members=("m2",))
    result = execute_binding(
        connection,
        compile_binding(product, "urn:op", (projection,), subject="doc", populations=(forbidden,)),
    )
    assert result.status == "not-applicable"
    assert result.roles[1].members[0].member == "m2"


def test_empty_conjunction_is_subject_unit_without_synthetic_product(storage):
    connection, _, _ = storage
    product = model(BindingExpression("all"), names=())
    compiled = compile_binding(product, "urn:op", (), subject="doc")
    result = execute_binding(connection, compiled)
    assert result.sufficient and result.roles == () and compiled.queries == ()
    raw = declaration()
    raw["roles"] = [role for role in raw["roles"] if role["direction"] == "output"]
    raw["binding"] = {"operator": "all", "children": []}
    compiled_model = compile_data_operations(
        declarations=(
            SourceArtifact(
                "unit.json", canonical_bytes({"version": MODEL_VERSION, "operations": [raw]})
            ),
        )
    )
    assert compiled_model.bindings[0].expression.children == ()


def test_decoder_refuses_null_identity_and_every_required_support_dimension(storage):
    from corpus_structure.semantic.data_operation_bindings import decode_binding_rows

    connection, _, projection = storage
    product = model(BindingExpression("scan", roles=("items",)))
    compiled = compile_binding(product, "urn:op", (projection,), subject="doc")
    rows = {
        name: tuple(dict(row) for row in connection.execute(query).mappings())
        for name, query in compiled.queries
    }
    checks = tuple(connection.execute(check.query).scalar_one() for check in compiled.checks)
    corrupted = {"items": tuple({**row, "original_source": None} for row in rows["items"])}
    assert decode_binding_rows(compiled, corrupted, checks).status == "invalid"
    operation = product.operations[0]
    role = operation.roles[0]
    assert role.support is not None
    strengthened = replace(
        product,
        operations=(
            replace(
                operation,
                roles=(
                    replace(
                        role,
                        support=replace(
                            role.support,
                            identity_requirements=("episode", "provider", "alternative"),
                        ),
                    ),
                ),
            ),
        ),
    )
    compiled = compile_binding(strengthened, "urn:op", (projection,), subject="doc")
    assert decode_binding_rows(compiled, rows, checks).status == "invalid"


def test_shared_roles_remain_active_in_selected_branch_and_conflicting_populations_refuse(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "choice",
        choice_parameter="producer",
        children=(
            BindingExpression(
                "all",
                roles=("left", "shared"),
                children=(BindingExpression("scan", roles=("left", "shared")),),
            ),
            BindingExpression(
                "all",
                roles=("right", "shared"),
                children=(BindingExpression("scan", roles=("right", "shared")),),
            ),
        ),
    )
    product = model(expression, names=("left", "right", "shared"), presence="optional", minimum=0)
    result = execute_binding(
        connection,
        compile_binding(
            product, "urn:op", (projection,), subject="doc", choices={"producer": "left"}
        ),
    )
    assert result.sufficient and result.roles[2].members and result.roles[1].state == "known-absent"
    conflict = replace(
        product,
        bindings=(
            replace(
                product.bindings[0],
                expression=BindingExpression(
                    "all",
                    children=(
                        BindingExpression(
                            "forall",
                            roles=("left",),
                            population="one",
                            children=(BindingExpression("scan", roles=("left",)),),
                        ),
                        BindingExpression(
                            "forall",
                            roles=("left",),
                            population="two",
                            children=(BindingExpression("scan", roles=("left",)),),
                        ),
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="two population scopes"):
        compile_binding(conflict, "urn:op", (projection,), subject="doc")
