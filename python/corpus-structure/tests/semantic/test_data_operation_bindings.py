"""Independent SQL execution fixtures for the closed binding normal form."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Literal

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.data_operation_bindings import (
    BindingResult,
    PopulationBinding,
    ProjectionBinding,
    ProjectionField,
    compile_binding,
    execute_binding,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    BindingExpression,
    BindingField,
    BindingOperand,
    BoundRoleMember,
    EffectiveDataOperationModel,
    EffectiveIdentity,
    EffectiveKind,
    EffectiveOperation,
    ImplementationCapabilities,
    InputSupport,
    OperationRole,
    RelationalBinding,
    ResolvedRoleBinding,
    SemanticEdge,
    SubjectContext,
    read_effective_data_operations,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact
from semantic.data_operation_binding_support import BINDING_EVIDENCE_CASES
from semantic.data_operation_declaration_support import binding_declaration as declaration


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
def storage(native_rollback):
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
            Column(name, JSONB)
            for name in ("analyzed_scope", "coverage", "support_episodes", "support_evidence")
        ),
        Column("position", Integer),
        Column("multiplicity", Integer),
        Column("value", Integer),
        Column("base", String),
    )
    connection = native_rollback.connection
    table.metadata.create_all(connection)
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


def test_declared_abstract_input_accepts_transitive_concrete_kinds_without_relabeling(storage):
    connection, table, projection = storage
    base = model(BindingExpression("scan", roles=("items",)))
    target = replace(
        base,
        kinds=(
            replace(base.kinds[0], facts=b'{"abstract":true}'),
            EffectiveKind("urn:middle", "Middle", "class", b'{"abstract":true}'),
            EffectiveKind("urn:a", "A", "class", b"{}"),
            EffectiveKind("urn:b", "B", "class", b"{}"),
            EffectiveKind("urn:unrelated", "Unrelated", "class", b"{}"),
        ),
        edges=(
            SemanticEdge("urn:middle", "urn:item", "inherits"),
            SemanticEdge("urn:a", "urn:middle", "inherits"),
            SemanticEdge("urn:b", "urn:item", "inherits"),
        ),
        identities=(
            *base.identities,
            *(
                EffectiveIdentity(kind, "kind", contract, b"{}")
                for kind, contract in (
                    ("urn:middle", "kind:middle"),
                    ("urn:a", "kind:a"),
                    ("urn:b", "kind:b"),
                    ("urn:unrelated", "kind:other"),
                )
            ),
        ),
    )
    for value, contract in ((1, "kind:a"), (2, "kind:b"), (3, "kind:other")):
        connection.execute(
            table.update().where(table.c.value == value).values(kind_contract=contract)
        )
    compiled = compile_binding(target, "urn:op", (projection,), subject="doc")
    result = execute_binding(connection, compiled)
    assert result.sufficient
    assert {member.product: member.kind_contract for member in result.roles[0].members} == {
        "p1": "kind:a",
        "p2": "kind:b",
    }


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
    assert decode_semantic_value(json.loads(result.parameters)) == {"allowed": [2, 3], "maximum": 3}
    resolved = result.resolved(
        subject_context=SubjectContext("project:test", result.subject, "source:test", b"{}"),
        inference="exact",
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="native",
    )
    assert resolved.roles == result.roles


@pytest.mark.parametrize(
    "facet,value",
    [
        ("member", "selected-member"),
        ("position", 17),
        ("original_source", "second-original"),
        ("analyzed_scope", {"page": 9}),
        ("support_episodes", ["selected-episode"]),
        ("support_evidence", {"witness": "selected-witness"}),
    ],
)
def test_postgresql_full_binding_result_preserves_selected_facts(storage, facet, value):
    connection, relation, projection = storage
    connection.execute(relation.update().where(relation.c.value == 2).values({facet: value}))
    expression = BindingExpression(
        "membership", operands=(field(), BindingOperand("parameter", "integer", name="allowed"))
    )
    actual = execute_binding(
        connection,
        compile_binding(
            model(expression),
            "urn:op",
            (projection,),
            subject="doc",
            parameters={"allowed": [2]},
        ),
    )
    # Complete independently authored output, including support references. Each
    # perturbation keeps expression truth unchanged but must change the result.
    expected_member = BoundRoleMember(
        product="p2",
        kind_contract="kind:fixed",
        subject="doc",
        original_source=value if facet == "original_source" else "source",
        analyzed_scope=b'{"page":9}' if facet == "analyzed_scope" else b'{"page":1}',
        coverage=b'{"complete":true}',
        support_episodes=("selected-episode",) if facet == "support_episodes" else ("ep2",),
        support_evidence=b'{"witness":"selected-witness"}'
        if facet == "support_evidence"
        else b'{"trust":"pinned"}',
        position=17 if facet == "position" else 1,
        multiplicity=1,
        member="selected-member" if facet == "member" else "m2",
        support_references=(
            ComputationalSupportReference(
                derivation_id="selected-episode" if facet == "support_episodes" else "ep2",
            ),
        ),
    )
    assert actual == BindingResult(
        operation="urn:op",
        subject="doc",
        roles=(ResolvedRoleBinding("items", "present", (expected_member,)),),
        status="ready",
        reasons=(),
        parameters=b'["mapping",[["allowed",["sequence",[["integer","2"]]]]]]',
        choices=b"{}",
        model_version=MODEL_VERSION,
        definition="definition:fixed",
        eligibility="eligibility:fixed",
        admission_evidence=(b'{"trust":"pinned"}',),
        source_sets=b"{}",
        subject_context=None,
    )


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


def test_archived_v2_is_exact_read_only_and_never_gains_projection_interpretation():
    source = model(BindingExpression("scan", roles=("items",)))
    archived = replace(source, version="data-operation-model-v2", graph_projections=())
    content = archived.content
    assert b'"graph_projections"' not in content
    restored = read_effective_data_operations(content)
    assert restored.content == content
    with pytest.raises(ValueError, match="historical"):
        restored.projection_graph("semantic-reference")
    corrupt = json.loads(content)
    corrupt["graph_projections"] = []
    with pytest.raises(ValueError):
        read_effective_data_operations(canonical_bytes(corrupt))
    corrupt = json.loads(content)
    corrupt["version"] = "data-operation-model-v1"
    with pytest.raises(ValueError, match="unsupported"):
        read_effective_data_operations(canonical_bytes(corrupt))


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


def test_membership_population_identity_is_retained_and_conflicting_operand_scopes_refuse(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "membership",
        operands=(
            BindingOperand("field", "string", BindingField("items", "urn:item", "member")),
            BindingOperand("population", "string", name="retained"),
        ),
    )
    projection = replace(
        projection, fields=(*projection.fields, ProjectionField("member", "member", "string"))
    )
    product = model(expression)
    population = PopulationBinding(
        "retained", "population:membership", True, ("m2",), b'{"closed":true}'
    )
    result = execute_binding(
        connection,
        compile_binding(product, "urn:op", (projection,), subject="doc", populations=(population,)),
    )
    assert result.sufficient and result.roles[0].population_witness is not None
    assert json.loads(result.roles[0].population_witness)["identity"] == "population:membership"
    other = replace(
        expression,
        operands=(expression.operands[0], replace(expression.operands[1], name="another")),
    )
    conflict = replace(
        product,
        bindings=(
            replace(
                product.bindings[0],
                expression=BindingExpression("all", children=(expression, other)),
            ),
        ),
    )
    with pytest.raises(ValueError, match="two population scopes"):
        compile_binding(conflict, "urn:op", (projection,), subject="doc", populations=(population,))


def test_closed_negative_population_without_candidate_facts_remains_awaiting(storage):
    connection, _, projection = storage
    population = PopulationBinding(
        "retained", "population:missing-facts", True, ("not-materialized",), b'{"closed":true}'
    )
    expression = BindingExpression("absent", roles=("items",), population="retained")
    result = execute_binding(
        connection,
        compile_binding(
            model(expression, minimum=0, presence="optional"),
            "urn:op",
            (projection,),
            subject="doc",
            populations=(population,),
        ),
    )
    assert result.status == "awaiting-inputs"
    assert any(reason.code == "negative-candidate-facts" for reason in result.reasons)


def test_runtime_parameter_mapping_preserves_date_decimal_and_signed_zero(storage):
    import math
    from datetime import date
    from decimal import Decimal

    connection, _, _ = storage
    parameters = {"when": date(2026, 11, 13), "amount": Decimal("1.20"), "sign": -0.0}
    product = model(
        BindingExpression("all"),
        names=(),
        parameters={
            "when": {"value_type": "date"},
            "amount": {"value_type": "decimal"},
            "sign": {"value_type": "float"},
        },
    )
    result = execute_binding(
        connection, compile_binding(product, "urn:op", (), subject="doc", parameters=parameters)
    )
    assert result.sufficient
    decoded = decode_semantic_value(json.loads(result.parameters))
    assert decoded["when"] == date(2026, 11, 13) and type(decoded["when"]) is date
    assert decoded["amount"] == Decimal("1.2") and type(decoded["amount"]) is Decimal
    assert math.copysign(1, decoded["sign"]) == -1
    resolved = result.resolved(
        subject_context=SubjectContext("project:test", result.subject, "source:test", b"{}"),
        inference="exact",
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="native",
    )
    assert resolved.parameters == result.parameters


def test_absence_rejects_nested_bundle_aggregate_scope(storage):
    _, _, projection = storage
    expression = BindingExpression(
        "absent",
        roles=("items",),
        population="retained",
        children=(BindingExpression("cardinality", roles=("items",), minimum=1),),
    )
    with pytest.raises(ValueError, match="absence children must be row predicates"):
        compile_binding(
            model(expression, minimum=0, presence="optional"),
            "urn:op",
            (projection,),
            subject="doc",
        )


def test_declared_subject_association_keeps_original_member_subject(storage):
    connection, _, projection = storage
    ordinary = model(BindingExpression("scan", roles=("items",)))
    associated = replace(
        ordinary,
        operations=(
            replace(
                ordinary.operations[0],
                roles=(replace(ordinary.operations[0].roles[0], subject_field="base"),),
            ),
        ),
    )
    result = execute_binding(
        connection, compile_binding(associated, "urn:op", (projection,), subject="b")
    )
    assert result.sufficient
    assert {member.subject for member in result.roles[0].members} == {"doc"}
    assert {member.member for member in result.roles[0].members} == {"m1", "m2", "m3"}
    unmatched = execute_binding(
        connection, compile_binding(associated, "urn:op", (projection,), subject="foreign")
    )
    assert not unmatched.sufficient
    old = execute_binding(
        connection, compile_binding(ordinary, "urn:op", (projection,), subject="b")
    )
    assert not old.sufficient


def test_subject_association_requires_admitted_identifier_projection(storage):
    _, _, projection = storage
    original = model(BindingExpression("scan", roles=("items",)))
    bad = replace(
        original,
        operations=(
            replace(
                original.operations[0],
                roles=(replace(original.operations[0].roles[0], subject_field="value"),),
            ),
        ),
    )
    with pytest.raises(ValueError, match="identifier"):
        compile_binding(bad, "urn:op", (projection,), subject="b")


def test_sql_covers_requires_every_requested_typed_value(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "covers",
        operands=(
            field(),
            BindingOperand("parameter", "integer", name="required"),
        ),
    )
    schema = model(expression, parameters={"required": {"value_type": "integer", "many": True}})
    for required, status in (
        ((1, 3), "ready"),
        ((1, 4), "not-applicable"),
        ((), "ready"),
        ((2, 2), "ready"),
    ):
        compiled = compile_binding(
            schema, "urn:op", (projection,), subject="doc", parameters={"required": required}
        )
        assert execute_binding(connection, compiled).status == status
    with pytest.raises(ValueError, match="integer"):
        compile_binding(
            schema, "urn:op", (projection,), subject="doc", parameters={"required": (True,)}
        )


def test_sql_source_set_selects_exact_product_without_relabelling_source(storage):
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
    from corpus_structure.semantic.structural_products import ExternalSourceRef

    connection, table, projection = storage
    reference = ExternalSourceRef(
        project_id="project",
        run_id=1,
        cut_id=2,
        release_id="release",
        result_revision=0,
        source_view_id=3,
        native_task_id=4,
        native_product_key="native:key",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    connection.execute(
        table.update()
        .where(table.c.product == "p2")
        .values(original_source="foreign-source", base=reference.identity)
    )
    frozen = SourceSetEntry.from_structural_source(
        reference,
        original_source="foreign-source",
        subject="doc",
        analyzed_scope=b'{"page":1}',
        product="p2",
        member="m2",
    )
    schema = model(BindingExpression("scan", roles=("items",)))
    operation = schema.operations[0]
    support = operation.roles[0].support
    assert support is not None
    role = replace(
        operation.roles[0],
        support=replace(
            support,
            source="frozen-source-set",
            source_set="inputs",
            source_reference_field="base",
        ),
    )
    schema = replace(schema, operations=(replace(operation, roles=(role,)),))
    compiled = compile_binding(
        schema,
        "urn:op",
        (projection,),
        subject="doc",
        original_source="root-source",
        source_sets=(FrozenSourceSet("inputs", (frozen,)),),
    )
    result = execute_binding(connection, compiled)
    assert result.status == "ready"
    assert [
        (member.product, member.member, member.original_source)
        for member in result.roles[0].members
    ] == [("p2", "m2", "foreign-source")]
    assert json.loads(result.source_sets)["inputs"][0]["source_reference"] == reference.identity
    with pytest.raises(ValueError, match=r"lacks.*source set"):
        compile_binding(schema, "urn:op", (projection,), subject="doc")
    wrong = replace(frozen, analyzed_scope=b'{"page":2}')
    assert (
        execute_binding(
            connection,
            compile_binding(
                schema,
                "urn:op",
                (projection,),
                subject="doc",
                source_sets=(FrozenSourceSet("inputs", (wrong,)),),
            ),
        ).status
        == "awaiting-inputs"
    )


def test_native_population_member_ids_are_qualified_by_owning_product(storage):
    connection, table, projection = storage
    original = dict(
        connection.execute(table.select().where(table.c.product == "p2")).mappings().one()
    )
    connection.execute(table.insert(), {**original, "product": "foreign-container"})
    population = PopulationBinding("retained", "closed", True, ("m2",), b'{"product_id":"p2"}')
    expression = BindingExpression(
        "forall",
        roles=("items",),
        population="retained",
        children=(BindingExpression("scan", roles=("items",)),),
    )
    schema = model(expression)
    result = execute_binding(
        connection,
        compile_binding(schema, "urn:op", (projection,), subject="doc", populations=(population,)),
    )
    assert result.status == "ready"
    assert [member.product for member in result.roles[0].members] == ["p2"]
    connection.execute(table.delete().where(table.c.product == "p2"))
    assert (
        execute_binding(
            connection,
            compile_binding(
                schema, "urn:op", (projection,), subject="doc", populations=(population,)
            ),
        ).status
        != "ready"
    )


def test_native_membership_and_absence_cannot_use_another_containers_local_member(storage):
    connection, table, projection = storage
    population = PopulationBinding("retained", "closed", True, ("b",), b'{"product_id":"p2"}')
    membership = BindingExpression(
        "membership",
        operands=(
            BindingOperand("field", "string", BindingField("items", "urn:item", "base")),
            BindingOperand("population", "string", name="retained"),
        ),
    )
    result = execute_binding(
        connection,
        compile_binding(
            model(membership), "urn:op", (projection,), subject="doc", populations=(population,)
        ),
    )
    assert [member.product for member in result.roles[0].members] == ["p2"]
    original = dict(
        connection.execute(table.select().where(table.c.product == "p2")).mappings().one()
    )
    connection.execute(table.insert(), {**original, "product": "foreign-container"})
    connection.execute(table.delete().where(table.c.product == "p2"))
    population = PopulationBinding("retained", "closed", True, ("m2",), b'{"product_id":"p2"}')
    absent = BindingExpression(
        "absent",
        roles=("items",),
        population="retained",
        children=(BindingExpression("scan", roles=("items",)),),
    )
    result = execute_binding(
        connection,
        compile_binding(
            model(absent, minimum=0, presence="optional"),
            "urn:op",
            (projection,),
            subject="doc",
            populations=(population,),
        ),
    )
    assert result.status == "awaiting-inputs"


def test_acquired_subject_context_survives_binding_and_cannot_be_replaced(storage):
    connection, _, projection = storage
    context = SubjectContext("project:test", "doc", "source", b'{"page":1}')
    compiled = compile_binding(
        model(BindingExpression("scan", roles=("items",))),
        "urn:op",
        (projection,),
        subject="doc",
        original_source="source",
        subject_context=context,
    )
    result = execute_binding(connection, compiled)
    assert result.subject_context == context
    resolved = result.resolved(
        inference="exact",
        subject_context=context,
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="native",
    )
    assert resolved.subject_context == context
    equivalent = result.resolved(
        inference="exact",
        subject_context=SubjectContext("project:test", "doc", "source", b'{"page":1.0}'),
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="native",
    )
    assert equivalent.subject_context == context
    with pytest.raises(ValueError, match="differs"):
        result.resolved(
            inference="exact",
            subject_context=SubjectContext("other", "doc", "source", b'{"page":1}'),
            authorization=b"{}",
            trust_evidence=b"{}",
            execution_profile="native",
        )


@pytest.mark.parametrize("case", BINDING_EVIDENCE_CASES, ids=lambda case: case.name)
def test_postgresql_authored_complete_binding_meanings(storage, case):
    connection, relation, projection = storage
    expression = BindingExpression("scan", roles=("items",))
    options: dict[str, Any] = {}
    arguments: dict[str, Any] = {}
    populations: tuple[PopulationBinding, ...] = ()
    if case.name in {"range-ready", "range-outside"}:
        connection.execute(relation.delete().where(relation.c.product != "p2"))
        connection.execute(relation.update().values(value=case.sample_value))
        expression = BindingExpression(
            "range",
            operands=(
                field(),
                BindingOperand("literal", "integer", value=b'["integer","10"]'),
                BindingOperand("literal", "integer", value=b'["integer","20"]'),
            ),
        )
        options = dict(collection="scalar", maximum=1)
    elif case.name in {"role-too-few", "role-too-many"}:
        options = dict(minimum=2, maximum=2)
        if case.name == "role-too-few":
            connection.execute(relation.delete().where(relation.c.product != "p2"))
    elif case.name in {"optional-unknown", "optional-present-empty"}:
        options = dict(minimum=0, presence="optional")
        if case.name == "optional-unknown":
            expression = BindingExpression(
                "literal",
                fields=(BindingField("items", "urn:item", "value"),),
                value=b'["integer","2"]',
            )
            connection.execute(relation.update().values(value=None))
        else:
            connection.execute(relation.delete())
    elif case.name == "negative-incomplete":
        options = dict(minimum=0, presence="optional")
        expression = BindingExpression("absent", roles=("items",), population="retained")
        populations = (
            PopulationBinding(
                "retained",
                "population:missing-facts",
                True,
                ("not-materialized",),
                b'{"closed":true}',
            ),
        )
    elif case.name in {"member-added", "member-removed"}:
        expression = BindingExpression(
            "forall",
            roles=("items",),
            population="retained",
            children=(BindingExpression("scan", roles=("items",)),),
        )
        populations = (
            PopulationBinding(
                "retained",
                "population:selected",
                True,
                ("m1", "m2") if case.name == "member-added" else ("m2",),
                b'{"closed":true}',
            ),
        )
        if case.name == "member-removed":
            connection.execute(relation.delete().where(relation.c.product == "p2"))
    elif case.name == "unselected-alternative":
        options = dict(names=("left", "right"), minimum=0, presence="optional")
        expression = BindingExpression(
            "choice",
            choice_parameter="producer",
            children=(
                BindingExpression("scan", roles=("left",)),
                BindingExpression(
                    "literal",
                    fields=(BindingField("right", "urn:item", "value"),),
                    value=b'["integer","2"]',
                ),
            ),
        )
        arguments = dict(choices={"producer": "right"})
    elif case.name in {"wrong-source-join", "distinct-same-text"}:
        options = dict(names=("left", "right"))
        # Both passages carry the same text. The selected identity must still bind
        # its exact product, member, original source and support episode.
        connection.execute(relation.update().values(base="identical passage text"))
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
                BindingExpression(
                    "literal",
                    fields=(BindingField("right", "urn:item", "value"),),
                    value=b'["integer","2"]',
                ),
            ),
        )
        if case.name == "wrong-source-join":
            connection.execute(
                relation.update()
                .where(relation.c.product == "p2")
                .values(original_source="other-original")
            )
            arguments = dict(original_source="source")
        else:
            connection.execute(
                relation.update()
                .where(relation.c.product == "p1")
                .values(original_source="original:left")
            )
            connection.execute(
                relation.update()
                .where(relation.c.product == "p2")
                .values(original_source="original:right")
            )
    actual = execute_binding(
        connection,
        compile_binding(
            model(expression, **options),
            "urn:op",
            (projection,),
            subject="doc",
            populations=populations,
            **arguments,
        ),
    )
    # These cases declare set/scalar collections, whose member order is immaterial.
    # Preserve every member field and every other result field for full equality.
    actual = replace(
        actual,
        roles=tuple(
            replace(role, members=tuple(sorted(role.members, key=lambda member: member.product)))
            for role in actual.roles
        ),
    )
    assert actual == case.expected


def _qualified_context_expression():
    operands = (
        BindingOperand("field", "subject-context", BindingField("items", "urn:item", "@context")),
        BindingOperand(
            "population",
            "subject-context",
            name="children",
            population_projection="qualified-context",
        ),
    )
    return BindingExpression(
        "all",
        children=(
            BindingExpression("membership", operands=operands),
            BindingExpression("covers", operands=operands),
        ),
    )


def test_population_projection_preserves_historical_bytes_and_is_explicit():
    from corpus_structure.semantic.data_operation_compilation import _expression

    historical = model(BindingExpression("scan", roles=("items",)))
    for version in ("data-operation-model-v2", "data-operation-model-v3", MODEL_VERSION):
        archived = replace(historical, version=version)
        assert b"population_projection" not in archived.content
        assert read_effective_data_operations(archived.content).content == archived.content
    parsed = _expression(
        {
            "operator": "covers",
            "operands": [
                {
                    "kind": "field",
                    "value_type": "subject-context",
                    "field": {"role": "items", "projection": "urn:item", "field": "@context"},
                },
                {
                    "kind": "population",
                    "name": "children",
                    "value_type": "subject-context",
                    "population_projection": "qualified-context",
                },
            ],
        },
        "urn:op",
        {"items"},
    )
    current = model(parsed)
    assert b'"population_projection":"qualified-context"' in current.content
    assert read_effective_data_operations(current.content).content == current.content
    with pytest.raises(ValueError, match="historical"):
        _ = replace(current, version="data-operation-model-v3").content


def test_sql_qualified_context_fanin_requires_all_contexts_without_parent_product_pin(storage):
    from corpus_structure.semantic.data_operation_json import json_bytes

    connection, table, projection = storage
    connection.execute(
        table.update().where(table.c.product == "p2").values(analyzed_scope={"page": 2})
    )
    connection.execute(
        table.update().where(table.c.product == "p3").values(analyzed_scope={"page": 3})
    )
    schema = model(_qualified_context_expression(), minimum=0, presence="optional")
    root = SubjectContext("project", "doc", "source", b'{"root":true}')
    contexts = tuple(
        SubjectContext("project", "doc", "source", json_bytes({"page": page})) for page in (1, 2)
    )

    def bind(required=contexts, complete=True):
        population = PopulationBinding(
            "children",
            "authentic-discovery-closure",
            complete,
            ("source-member-a", "source-member-b"),
            b'{"product_id":"discovery-product","derivation_id":"discovery-episode"}',
            projection="qualified-context",
            contexts=required,
        )
        return execute_binding(
            connection,
            compile_binding(
                schema,
                "urn:op",
                (projection,),
                subject="doc",
                subject_context=root,
                populations=(population,),
            ),
        )

    ready = bind()
    assert ready.status == "ready"
    assert {member.product for member in ready.roles[0].members} == {"p1", "p2"}
    assert json.loads(ready.roles[0].population_witness)["projection"] == "qualified-context"
    # Same local subject does not collapse two scope occurrences. JSONB numeric
    # spelling shares meaning; Boolean, source, and project remain distinct.
    assert (
        bind((replace(contexts[0], analyzed_scope=b'{"page":1.0}'), contexts[1])).status == "ready"
    )
    for altered in (
        replace(contexts[1], analyzed_scope=b'{"page":true}'),
        replace(contexts[1], original_source="other"),
        replace(contexts[1], project_id="other"),
    ):
        assert bind((contexts[0], altered)).status == "not-applicable"
    assert bind(complete=False).status == "awaiting-population"
    connection.execute(table.delete().where(table.c.product == "p2"))
    assert bind().status == "not-applicable"
    empty = bind(())
    assert empty.status == "ready" and empty.roles[0].members == ()
    assert empty.roles[0].state == "known-absent"


def test_sql_subject_field_can_target_original_source_without_relabeling_context(storage):
    connection, table, projection = storage
    connection.execute(table.update().where(table.c.product == "p1").values(base="source"))
    connection.execute(table.update().where(table.c.product == "p2").values(base="hashed:document"))
    base = model(BindingExpression("scan", roles=("items",)))
    op = base.operations[0]
    schema = replace(
        base,
        operations=(
            replace(
                op,
                roles=(
                    replace(op.roles[0], subject_field="base", subject_target="original-source"),
                ),
            ),
        ),
    )
    compiled = compile_binding(
        schema,
        "urn:op",
        (projection,),
        subject="hashed:document",
        original_source="source",
        subject_context=SubjectContext("project", "hashed:document", "source", b"{}"),
    )
    result = execute_binding(connection, compiled)
    assert result.status == "ready"
    assert [
        (member.product, member.subject, member.original_source)
        for member in result.roles[0].members
    ] == [("p1", "doc", "source")]
    assert b'"subject_target":"original-source"' in schema.content
    assert read_effective_data_operations(schema.content).content == schema.content
    for version in ("data-operation-model-v2", "data-operation-model-v3"):
        archived = replace(base, version=version)
        assert b"subject_target" not in archived.content
        assert read_effective_data_operations(archived.content).content == archived.content
        with pytest.raises(ValueError, match="historical"):
            _ = replace(schema, version=version).content


@pytest.mark.parametrize("header,selected", [("@product", "p2"), ("@member", "m2")])
def test_frozen_header_pin_selects_authentic_native_identity_before_hydration(
    storage, header, selected
):
    connection, _, projection = storage
    expression = BindingExpression(
        "equal",
        operands=(
            BindingOperand("field", "string", BindingField("items", "urn:item", header)),
            BindingOperand("parameter", "string", name="selected"),
        ),
    )
    schema = model(expression, maximum=1, parameters={"selected": {"value_type": "string"}})
    compiled = compile_binding(
        schema, "urn:op", (projection,), subject="doc", parameters={"selected": selected}
    )
    result = execute_binding(connection, compiled)
    assert result.status == "ready"
    assert [(row.product, row.member) for row in result.roles[0].members] == [("p2", "m2")]
    assert result.operation == "urn:op"


def test_header_binding_field_is_compiled_as_reserved_typed_identity():
    operation = declaration(
        binding={
            "operator": "equal",
            "operands": [
                {
                    "kind": "field",
                    "value_type": "string",
                    "field": {"role": "items", "projection": "integer", "field": "@product"},
                },
                {"kind": "parameter", "name": "selected", "value_type": "string"},
            ],
        },
        parameters={"selected": {"value_type": "string"}},
    )
    artifact = SourceArtifact(
        "headers", canonical_bytes({"version": MODEL_VERSION, "operations": [operation]})
    )
    compiled = compile_data_operations(declarations=(artifact,))
    assert compiled.bindings[-1].expression.operands[0].field.field == "@product"
    operation["binding"]["operands"][0]["value_type"] = "integer"
    with pytest.raises(ValueError, match="header binding fields"):
        compile_data_operations(
            declarations=(
                SourceArtifact(
                    "headers",
                    canonical_bytes({"version": MODEL_VERSION, "operations": [operation]}),
                ),
            )
        )
