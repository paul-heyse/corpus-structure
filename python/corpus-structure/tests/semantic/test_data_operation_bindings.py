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
    CoverageContract,
    CoverageResultOwner,
    EffectiveDataOperationModel,
    EffectiveIdentity,
    EffectiveKind,
    EffectiveOperation,
    ImplementationCapabilities,
    InputCoverage,
    InputSupport,
    OperationRole,
    RelationalBinding,
    ResolvedRoleBinding,
    SemanticEdge,
    SubjectContext,
    SubjectDefinition,
    read_effective_data_operations,
)
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence
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
            InputSupport(
                "exact",
                "original",
                InputCoverage(name, "complete"),
                identity_requirements=("episode",),
            ),
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
        CoverageContract(
            "urn:binding",
            b"{}",
            b"{}",
            (
                CoverageResultOwner(
                    "declared-contract",
                    "urn:op",
                    "authored-result-contract-v1",
                    b'{"behavior":"revision-1"}',
                ),
            ),
            "complete",
        ),
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
        discovery_relation="role-associated",
    )
    return EffectiveDataOperationModel(
        MODEL_VERSION,
        (EffectiveKind("urn:item", "Item", "class", b"{}"),),
        (operation,),
        (RelationalBinding("urn:binding", "urn:op", expression),),
        (),
        (),
        subject_definitions=(SubjectDefinition("document", "urn:item", "project"),),
        identities=(
            EffectiveIdentity("urn:op", "definition", "definition:fixed"),
            EffectiveIdentity("urn:op", "eligibility", "eligibility:fixed"),
            EffectiveIdentity("urn:item", "kind", "kind:fixed"),
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
                "subject_definition",
                "original_source",
                "member",
                "provider_identity",
                "alternative_identity",
            )
        ),
        *(
            Column(name, JSONB)
            for name in (
                "analyzed_scope",
                "coverage",
                "support_episodes",
                "support_evidence",
                "support_references",
            )
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
                subject_definition="document",
                original_source="source",
                member=f"m{value}",
                provider_identity=None,
                alternative_identity=None,
                analyzed_scope={"page": 1},
                coverage={"complete": True},
                support_episodes=[f"ep{value}"],
                support_references=[
                    {"kind": "computation", "derivation_id": f"ep{value}", "admission_use_id": None}
                ],
                support_evidence={
                    "trust": "pinned",
                    "producer_output": {
                        "member_id": None,
                        "role": "result",
                        "position": 0,
                        "multiplicity": 1,
                    },
                },
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
                EffectiveIdentity(kind, "kind", contract)
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
        subject_context=SubjectContext(
            "project:test", result.subject, "source:test", b"{}", subject_definition="document"
        ),
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
        (
            "support_evidence",
            {
                "witness": "selected-witness",
                "producer_output": {
                    "member_id": None,
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                },
            },
        ),
    ],
)
def test_postgresql_full_binding_result_preserves_selected_facts(storage, facet, value):
    connection, relation, projection = storage
    selected = {facet: value}
    if facet == "support_episodes":
        selected["support_references"] = [
            {"kind": "computation", "derivation_id": "selected-episode", "admission_use_id": None}
        ]
    connection.execute(relation.update().where(relation.c.value == 2).values(selected))
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
        support_evidence=b'{"producer_output":{"member_id":null,"multiplicity":1,"position":0,"role":"result"},"witness":"selected-witness"}'
        if facet == "support_evidence"
        else b'{"producer_output":{"member_id":null,"multiplicity":1,"position":0,"role":"result"},"trust":"pinned"}',
        position=17 if facet == "position" else 1,
        multiplicity=1,
        member="selected-member" if facet == "member" else "m2",
        support_references=(
            ComputationalSupportReference(
                derivation_id="selected-episode" if facet == "support_episodes" else "ep2",
            ),
        ),
        subject_definition="document",
        producer_output=ProducerOutputOccurrence(
            member_id=None, role="result", position=0, multiplicity=1
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
        replicate=None,
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
    raw["coverage"]["result_owners"] = [{"kind": "implementation", "reference": "self"}]
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


@pytest.mark.parametrize("change", ["complete", "null", "empty", "global-refusal"])
def test_independent_optional_bundles_keep_selection_coverage_and_null_meaning(storage, change):
    connection, relation, projection = storage
    names = ("left", "right", "empty")
    filters = tuple(
        BindingExpression(
            "optional",
            roles=(name,),
            children=(
                BindingExpression(
                    "membership",
                    operands=(field(role=name), BindingOperand("parameter", "integer", name=name)),
                ),
            ),
        )
        for name in names
    )
    expression = BindingExpression(
        "all",
        children=(
            *filters,
            *(BindingExpression("collection", roles=(name,), collection="set") for name in names),
            BindingExpression(
                "covers",
                operands=(field(role="left"), BindingOperand("parameter", "integer", name="left")),
            ),
            BindingExpression(
                "membership",
                operands=(
                    BindingOperand("parameter", "string", name="profile"),
                    BindingOperand("literal", "string", value=b'["sequence",[["string","complete"]]]'),
                ),
            ),
        ),
    )
    product = model(expression, names=names, minimum=0, presence="optional")
    parameters = dict(left=[1, 2], right=[2, 3], empty=[99], profile="complete")
    if change == "null":
        connection.execute(relation.update().where(relation.c.value == 1).values(value=None))
    elif change == "empty":
        connection.execute(relation.delete())
    elif change == "global-refusal":
        parameters["profile"] = "other"

    compiled = compile_binding(product, "urn:op", (projection,), subject="doc", parameters=parameters)
    # An extra conjunction preserves the predicate but selects the general
    # relational lowering, providing a bounded comparison of the two SQL paths.
    relational_model = replace(
        product,
        bindings=(replace(product.bindings[0], expression=BindingExpression("all", children=(expression,))),),
    )
    relational = compile_binding(
        relational_model, "urn:op", (projection,), subject="doc", parameters=parameters
    )
    result = execute_binding(connection, compiled)
    assert result == execute_binding(connection, relational)
    assert result.status == {
        "complete": "ready", "null": "unknown", "empty": "not-applicable", "global-refusal": "not-applicable"
    }[change]
    selected = {role.role: {member.product for member in role.members} for role in result.roles}
    if change == "complete":
        assert selected == {"left": {"p1", "p2"}, "right": {"p2", "p3"}, "empty": set()}
    elif change == "null":
        assert selected == {"left": {"p2"}, "right": {"p2", "p3"}, "empty": set()}
        assert any(reason.code == "unknown-comparison" for reason in result.reasons)
    else:
        assert selected == {name: set() for name in names}
    for name, query in compiled.queries:
        rendered = str(query)
        assert "role_" + name in rendered
        assert all("role_" + peer not in rendered for peer in names if peer != name)
    assert all(all("role_" + peer in str(query) for peer in names) for _, query in relational.queries)


def test_required_role_keeps_relational_selection_for_independent_optional_filters(storage):
    connection, _, projection = storage
    expression = BindingExpression(
        "all",
        children=tuple(
            BindingExpression(
                "optional",
                roles=(name,),
                children=(BindingExpression("literal", fields=(BindingField(name, "urn:item", "value"),), value=b'["integer","2"]'),),
            )
            for name in ("left", "right")
        ),
    )
    product = model(expression, names=("left", "right"))
    compiled = compile_binding(product, "urn:op", (projection,), subject="doc")
    result = execute_binding(connection, compiled)
    assert result.sufficient
    assert all({member.product for member in role.members} == {"p2"} for role in result.roles)
    assert all("role_left" in str(query) and "role_right" in str(query) for _, query in compiled.queries)


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
    product = replace(
        product,
        subject_definitions=(replace(product.subject_definitions[0], scope="original-source"),),
    )
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
        subject_context=SubjectContext(
            "project:test", result.subject, "source:test", b"{}", subject_definition="document"
        ),
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
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, SourceSetEntry
    from corpus_structure.semantic.data_product_reference import (
        DataProductMemberReference,
        DataProductReference,
    )

    connection, table, projection = storage

    connection.execute(
        table.update()
        .where(table.c.product == "p2")
        .values(original_source="foreign-source", base="opaque-unrelated-value")
    )
    frozen = SourceSetEntry.from_semantic_source(
        DataProductMemberReference(DataProductReference("p2"), "m2"),
        context=SubjectContext(
            "project", "doc", "foreign-source", b'{"page":1}', subject_definition="document"
        ),
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
        ),
    )
    schema = replace(schema, operations=(replace(operation, roles=(role,)),))
    compiled = compile_binding(
        schema,
        "urn:op",
        (projection,),
        subject="doc",
        original_source="root-source",
        source_sets=(FrozenSourceSet.unqualified("inputs", (frozen,)),),
    )
    result = execute_binding(connection, compiled)
    assert result.status == "ready"
    assert [
        (member.product, member.member, member.original_source)
        for member in result.roles[0].members
    ] == [("p2", "m2", "foreign-source")]
    assert (
        json.loads(result.source_sets)["inputs"]["entries"][0]["source_reference"]
        == DataProductMemberReference(DataProductReference("p2"), "m2").identity
    )
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
                source_sets=(FrozenSourceSet.unqualified("inputs", (wrong,)),),
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


def test_explicit_discovery_input_filters_parent_before_scalar_cardinality(storage):
    connection, table, projection = storage
    row = dict(connection.execute(table.select().where(table.c.product == "p2")).mappings().one())
    row["support_references"] = [
        {"kind": "computation", "derivation_id": "ep2", "admission_use_id": "use:current"}
    ]
    connection.execute(table.update().where(table.c.product == "p2").values(**row))
    connection.execute(table.insert(), {**row, "product": "same-context-other-parent"})
    connection.execute(
        table.insert(), {**row, "member": "m2-other-scope", "analyzed_scope": {"page": 2}}
    )
    # Both are genuine competing headers for the same address/context. Matching
    # only the episode would still admit the earlier use of that same episode.
    for episode, use in (("episode:earlier", "use:earlier"), ("ep2", "use:earlier")):
        connection.execute(
            table.insert(),
            {
                **row,
                "support_episodes": [episode],
                "support_references": [
                    {"kind": "computation", "derivation_id": episode, "admission_use_id": use}
                ],
            },
        )
    context = SubjectContext(
        "project", "doc", "source", b'{"page":1}', subject_definition="document"
    )
    schema = model(BindingExpression("scan", roles=("items",)), collection="scalar", maximum=1)
    population = PopulationBinding(
        "discovered",
        "population:exact-parent",
        False,
        ("m2", "m2-other-scope"),
        b'{"product_id":"p2","derivation_id":"ep2","admission_use_id":"use:current"}',
    )
    associated = compile_binding(
        schema,
        "urn:op",
        (projection,),
        subject="doc",
        subject_context=context,
        populations=(population,),
        discovery_roles=(("items", "discovered"),),
    )
    result = execute_binding(connection, associated)
    assert result.status == "ready"
    assert [(member.product, member.member) for member in result.roles[0].members] == [("p2", "m2")]
    assert result.roles[0].members[0].support_references == (
        ComputationalSupportReference(derivation_id="ep2", admission_use_id="use:current"),
    )
    assert result.roles[0].population_witness is not None
    missing = compile_binding(
        schema,
        "urn:op",
        (projection,),
        subject="doc",
        subject_context=context,
        discovery_roles=(("items", "discovered"),),
    )
    assert execute_binding(connection, missing).status == "awaiting-population"


@pytest.mark.parametrize(
    "evidence",
    [
        {},
        {"product_id": "p2"},
        {"product_id": "p2", "derivation_id": "ep2"},
        {"product_id": "p2", "derivation_id": "ep2", "admission_use_id": None},
        {"product_id": "p2", "derivation_id": "ep2", "admission_use_id": ""},
        {"product_id": "p2", "derivation_id": 2, "admission_use_id": "use:current"},
        {"product_id": "p2", "derivation_id": "ep2", "admission_use_id": ["use:current"]},
        [],
    ],
)
def test_discovery_input_requires_complete_typed_producing_support(evidence):
    from corpus_structure.semantic.data_operation_projections import binding_row_contract

    projection = ProjectionBinding("urn:item", binding_row_contract().subquery(), (), b"{}")
    schema = model(BindingExpression("scan", roles=("items",)), collection="scalar", maximum=1)
    with pytest.raises(ValueError, match="exact parent product and support"):
        compile_binding(
            schema,
            "urn:op",
            (projection,),
            subject="doc",
            subject_context=SubjectContext(
                "project", "doc", "source", b'{"page":1}', subject_definition="document"
            ),
            populations=(
                PopulationBinding("discovered", "closed", True, ("m2",), canonical_bytes(evidence)),
            ),
            discovery_roles=(("items", "discovered"),),
        )


@pytest.mark.parametrize("duplicate", ["distinct-slot", "multiplicity"])
def test_discovery_proof_selection_preserves_real_output_cardinality(storage, duplicate):
    connection, table, projection = storage
    row = dict(connection.execute(table.select().where(table.c.product == "p2")).mappings().one())
    row["support_references"] = [
        {"kind": "computation", "derivation_id": "ep2", "admission_use_id": "use:current"}
    ]
    if duplicate == "multiplicity":
        row["multiplicity"] = 2
        row["support_evidence"]["producer_output"]["multiplicity"] = 2
    connection.execute(table.update().where(table.c.product == "p2").values(**row))
    if duplicate == "distinct-slot":
        connection.execute(
            table.insert(),
            {
                **row,
                "position": 2,
                "support_evidence": {
                    "trust": "pinned",
                    "producer_output": {
                        "member_id": None,
                        "role": "result",
                        "position": 1,
                        "multiplicity": 1,
                    },
                },
            },
        )
    result = execute_binding(
        connection,
        compile_binding(
            model(BindingExpression("scan", roles=("items",)), collection="scalar", maximum=1),
            "urn:op",
            (projection,),
            subject="doc",
            subject_context=SubjectContext(
                "project", "doc", "source", b'{"page":1}', subject_definition="document"
            ),
            populations=(
                PopulationBinding(
                    "discovered",
                    "closed",
                    True,
                    ("m2",),
                    b'{"product_id":"p2","derivation_id":"ep2","admission_use_id":"use:current"}',
                ),
            ),
            discovery_roles=(("items", "discovered"),),
        ),
    )
    assert result.status != "ready"


def test_discovery_does_not_override_conflicting_selected_source_proof(storage):
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from semantic.test_data_operation_source_sets import selected_entry

    connection, table, projection = storage
    row = dict(connection.execute(table.select().where(table.c.product == "p2")).mappings().one())
    row["support_references"] = [
        {"kind": "computation", "derivation_id": "ep2", "admission_use_id": "use:current"}
    ]
    connection.execute(table.update().where(table.c.product == "p2").values(**row))
    connection.execute(
        table.insert(),
        {
            **row,
            "support_references": [
                {"kind": "computation", "derivation_id": "ep2", "admission_use_id": "use:earlier"}
            ],
        },
    )
    selected = selected_entry(product="p2", member="m2", episode="ep2", use="use:earlier")
    selected = replace(
        selected, entry=replace(selected.entry, subject="doc", original_source="source")
    )
    base = model(BindingExpression("scan", roles=("items",)), collection="scalar", maximum=1)
    role = base.operations[0].roles[0]
    assert role.support is not None
    role = replace(
        role, support=replace(role.support, source="frozen-source-set", source_set="inputs")
    )
    schema = replace(base, operations=(replace(base.operations[0], roles=(role,)),))

    def bind(scope):
        return execute_binding(
            connection,
            compile_binding(
                schema,
                "urn:op",
                (projection,),
                subject="doc",
                subject_context=SubjectContext(
                    "project", "doc", "source", b'{"page":1}', subject_definition="document"
                ),
                populations=(
                    PopulationBinding(
                        "discovered",
                        "closed",
                        True,
                        ("m2",),
                        b'{"product_id":"p2","derivation_id":"ep2","admission_use_id":"use:current"}',
                    ),
                ),
                discovery_roles=(("items", "discovered"),),
                source_sets=(scope,),
            ),
        )

    assert bind(FrozenSourceSet.from_selected("inputs", (selected,))).status == "awaiting-inputs"
    current = bind(FrozenSourceSet.unqualified("inputs", (selected.entry,)))
    assert current.status == "ready"
    assert current.roles[0].members[0].support_references == (
        ComputationalSupportReference(derivation_id="ep2", admission_use_id="use:current"),
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
    context = SubjectContext(
        "project:test", "doc", "source", b'{"page":1}', subject_definition="document"
    )
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
        subject_context=SubjectContext(
            "project:test", "doc", "source", b'{"page":1.0}', subject_definition="document"
        ),
        authorization=b"{}",
        trust_evidence=b"{}",
        execution_profile="native",
    )
    assert equivalent.subject_context == context
    with pytest.raises(ValueError, match="differs"):
        result.resolved(
            inference="exact",
            subject_context=SubjectContext(
                "other", "doc", "source", b'{"page":1}', subject_definition="document"
            ),
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

    current = model(BindingExpression("scan", roles=("items",)))
    assert b"population_projection" not in current.content
    assert read_effective_data_operations(current.content).content == current.content
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
    with pytest.raises(ValueError, match="unsupported"):
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
    root = SubjectContext(
        "project", "doc", "source", b'{"root":true}', subject_definition="document"
    )
    contexts = tuple(
        SubjectContext(
            "project", "doc", "source", json_bytes({"page": page}), subject_definition="document"
        )
        for page in (1, 2)
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
    assert ready.roles[0].population_witness is not None
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
        subject_context=SubjectContext(
            "project", "hashed:document", "source", b"{}", subject_definition="document"
        ),
    )
    result = execute_binding(connection, compiled)
    assert result.status == "ready"
    assert [
        (member.product, member.subject, member.original_source)
        for member in result.roles[0].members
    ] == [("p1", "doc", "source")]
    assert b'"subject_target":"original-source"' in schema.content
    assert read_effective_data_operations(schema.content).content == schema.content


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
    field = compiled.bindings[-1].expression.operands[0].field
    assert field is not None and field.field == "@product"
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


def test_zero_minimum_selected_producer_preserves_other_roles_and_requires_closed_absence(storage):
    connection, table, projection = storage
    connection.execute(
        table.update().where(table.c.product == "p1").values(alternative_identity="producer:a")
    )
    operands = (
        BindingOperand("field", "subject-context", BindingField("right", "urn:item", "@context")),
        BindingOperand(
            "population",
            "subject-context",
            name="right-contexts",
            population_projection="qualified-context",
        ),
    )
    expression = BindingExpression(
        "all",
        children=(
            BindingExpression("scan", roles=("left",)),
            BindingExpression(
                "optional",
                roles=("right",),
                children=(BindingExpression("membership", operands=operands),),
            ),
            BindingExpression("covers", operands=operands),
        ),
    )
    schema = model(expression, names=("left", "right"))
    roles = tuple(
        replace(
            role,
            presence="alternative",
            alternatives=("producer:a" if role.name == "left" else "producer:b",),
            selected="producer:a" if role.name == "left" else "producer:b",
            minimum=1 if role.name == "left" else 0,
        )
        for role in schema.operations[0].roles
    )
    schema = replace(schema, operations=(replace(schema.operations[0], roles=roles),))

    def bind(complete):
        return execute_binding(
            connection,
            compile_binding(
                schema,
                "urn:op",
                (projection,),
                subject="doc",
                subject_context=SubjectContext(
                    "project", "doc", "source", b"{}", subject_definition="document"
                ),
                populations=(
                    PopulationBinding(
                        "right-contexts",
                        "closed",
                        complete,
                        (),
                        b'{"derivation_id":"closure"}',
                        projection="qualified-context",
                    ),
                ),
            ),
        )

    ready = bind(True)
    assert ready.status == "ready"
    assert [(role.role, role.state, len(role.members)) for role in ready.roles] == [
        ("left", "present", 1),
        ("right", "known-absent", 0),
    ]
    assert bind(False).status == "awaiting-population"


def test_semantic_source_set_pins_cross_source_context_without_legacy_reference(storage):
    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        SourceSetEntry,
        read_source_sets,
        source_sets_record,
    )
    from corpus_structure.semantic.data_product_reference import (
        DataProductMemberReference,
        DataProductReference,
    )

    connection, table, projection = storage
    connection.execute(
        table.update()
        .where(table.c.product == "p2")
        .values(
            subject="foreign:subject", original_source="foreign:source", analyzed_scope={"page": 2}
        )
    )
    context = SubjectContext(
        "project",
        "foreign:subject",
        "foreign:source",
        b'{"page":2.0}',
        subject_definition="document",
    )
    entry = SourceSetEntry.from_semantic_source(
        DataProductMemberReference(DataProductReference("p2"), "m2"), context=context
    )
    sources = (FrozenSourceSet.unqualified("selected", (entry,)),)
    assert read_source_sets(source_sets_record(sources)) == sources
    base = model(BindingExpression("scan", roles=("items",)))
    assert base.operations[0].roles[0].support is not None
    role = replace(
        base.operations[0].roles[0],
        subject_target="source-set",
        support=replace(
            base.operations[0].roles[0].support, source="frozen-source-set", source_set="selected"
        ),
    )
    schema = replace(base, operations=(replace(base.operations[0], roles=(role,)),))
    result = execute_binding(
        connection,
        compile_binding(
            schema,
            "urn:op",
            (projection,),
            subject="authored:input",
            original_source="local:source",
            source_sets=sources,
        ),
    )
    assert result.status == "ready"
    assert [
        (member.product, member.member, member.subject, member.original_source)
        for member in result.roles[0].members
    ] == [("p2", "m2", "foreign:subject", "foreign:source")]
    for altered in (
        replace(context, analyzed_scope=b'{"page":true}'),
        replace(context, subject="other"),
        replace(context, original_source="other"),
    ):
        wrong = SourceSetEntry.from_semantic_source(
            DataProductMemberReference(DataProductReference("p2"), "m2"), context=altered
        )
        invalid = execute_binding(
            connection,
            compile_binding(
                schema,
                "urn:op",
                (projection,),
                subject="authored:input",
                original_source="local:source",
                source_sets=(FrozenSourceSet.unqualified("selected", (wrong,)),),
            ),
        )
        assert invalid.status != "ready"


def test_semantic_source_set_association_compiles_without_fabricated_body_reference():
    operation = declaration()
    role = operation["roles"][0]
    role["support"].update(source="frozen-source-set", source_set="selected")
    role["subject_target"] = "source-set"
    compiled = compile_data_operations(
        declarations=(
            SourceArtifact(
                "semantic-source-set",
                canonical_bytes({"version": MODEL_VERSION, "operations": [operation]}),
            ),
        )
    )
    actual = next(op for op in compiled.operations if op.semantic_id == "urn:op").roles[0]
    assert actual.subject_target == "source-set"
    assert actual.support is not None
    assert actual.subject_field is None and actual.support.source_set == "selected"
    assert read_effective_data_operations(compiled.content).content == compiled.content
    role["subject_field"] = "fabricated"
    with pytest.raises(ValueError, match="source-set association"):
        compile_data_operations(
            declarations=(
                SourceArtifact(
                    "semantic-source-set",
                    canonical_bytes({"version": MODEL_VERSION, "operations": [operation]}),
                ),
            )
        )


def test_project_source_filters_distinguish_unqualified_null_and_actual_source(storage):
    connection, table, projection = storage
    product = model(BindingExpression("scan", roles=("items",)))
    connection.execute(table.update().where(table.c.product == "p1").values(original_source=None))
    connection.execute(
        table.update().where(table.c.product == "p2").values(original_source="other-source")
    )

    def selected(**scope):
        return execute_binding(
            connection, compile_binding(product, "urn:op", (projection,), subject="doc", **scope)
        )

    unqualified, absent, exact = (
        selected(),
        selected(original_source=None),
        selected(original_source="other-source"),
    )
    assert {member.product for member in unqualified.roles[0].members} == {"p1", "p2", "p3"}
    assert {member.product for member in absent.roles[0].members} == {"p1"}
    assert {member.product for member in exact.roles[0].members} == {"p2"}
    context = SubjectContext("project", "doc", None, b"{}", subject_definition="document")
    assert {member.product for member in selected(subject_context=context).roles[0].members} == {
        "p1"
    }
    source_scoped = replace(
        product,
        subject_definitions=(replace(product.subject_definitions[0], scope="original-source"),),
    )
    with pytest.raises(ValueError, match="only a checked project-scoped"):
        compile_binding(source_scoped, "urn:op", (projection,), subject="doc", original_source=None)


def test_explicit_empty_source_set_is_closed_absence_and_never_an_unbounded_scan(storage):
    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        read_source_sets,
        source_sets_record,
    )

    connection, _table, projection = storage
    sources = (FrozenSourceSet.unqualified("selected", ()),)
    assert source_sets_record(sources) == {
        "selected": {"entries": [], "acquisition": {"kind": "all-admissible-support-v1"}}
    }
    assert read_source_sets(source_sets_record(sources)) == sources
    base = model(BindingExpression("scan", roles=("items",)), minimum=0, presence="optional")
    original = base.operations[0].roles[0]
    assert original.support is not None
    role = replace(
        original,
        subject_target="source-set",
        support=replace(original.support, source="frozen-source-set", source_set="selected"),
    )
    schema = replace(base, operations=(replace(base.operations[0], roles=(role,)),))

    def bind(selected):
        return execute_binding(
            connection,
            compile_binding(schema, "urn:op", (projection,), subject="doc", source_sets=selected),
        )

    result = bind(sources)
    assert result.status == "ready"
    # A collection can be present and exactly empty; unknown/missing is separate.
    assert [(role.state, role.members) for role in result.roles] == [("present", ())]
    with pytest.raises(ValueError, match="declared frozen source set"):
        bind(())
    required = replace(role, minimum=1, presence="required")
    required_schema = replace(
        schema, operations=(replace(schema.operations[0], roles=(required,)),)
    )
    refused = execute_binding(
        connection,
        compile_binding(
            required_schema, "urn:op", (projection,), subject="doc", source_sets=sources
        ),
    )
    assert refused.status != "ready"
    assert not refused.roles[0].members


def test_binding_transport_preserves_exact_context_checks_and_empty_role(storage):
    from decimal import Decimal

    from sqlalchemy import Boolean, event, literal, select, text

    from corpus_structure.semantic.data_operation_bindings import BindingCheck, BindingReason
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads

    connection, _table, projection = storage
    exact = Decimal("0.123456789012345678901234567890123456789")
    connection.execute(
        text(
            "UPDATE admitted SET analyzed_scope = CAST(:scope AS jsonb), "
            "support_evidence = CAST(:support AS jsonb)"
        ),
        {
            "scope": '{"fraction":' + str(exact) + "}",
            "support": json_bytes(
                {
                    "fraction": exact,
                    "producer_output": {
                        "member_id": None,
                        "role": "result",
                        "position": 0,
                        "multiplicity": 1,
                    },
                }
            ).decode(),
        },
    )
    target = model(
        BindingExpression("scan", roles=("items", "empty")),
        names=("items", "empty"),
        minimum=0,
        presence="optional",
        collection="sequence",
    )
    operation = target.operations[0]
    target = replace(
        target,
        operations=(
            replace(
                operation,
                roles=(operation.roles[0], replace(operation.roles[1], subject_field="base")),
            ),
        ),
    )
    compiled = compile_binding(target, "urn:op", (projection,), subject="doc")
    compiled = replace(
        compiled,
        checks=compiled.checks
        + tuple(
            BindingCheck(
                BindingReason(code, "transport-control", code),
                select(literal(value, type_=Boolean())),
                "awaiting-inputs",
            )
            for code, value in (
                ("true-control", True),
                ("false-control", False),
                ("null-control", None),
            )
        ),
    )
    statements = []

    def executed(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", executed)
    try:
        result = execute_binding(connection, compiled)
    finally:
        event.remove(connection, "before_cursor_execute", executed)
    assert len(statements) == 1
    assert result.status == "unknown"
    assert {reason.code for reason in result.reasons} == {"false-control", "null-control"}
    assert result.roles[1].members == ()
    assert [member.position for member in result.roles[0].members] == [0, 1, 2]
    assert [member.product for member in result.roles[0].members] == ["p3", "p2", "p1"]
    for member in result.roles[0].members:
        assert json_loads(member.analyzed_scope) == {"fraction": exact}
        assert json_loads(member.support_evidence) == {
            "fraction": exact,
            "producer_output": {
                "member_id": None,
                "role": "result",
                "position": 0,
                "multiplicity": 1,
            },
        }


@pytest.mark.parametrize("values", [(), (True, False), (None, None)])
def test_binding_transport_refuses_missing_or_duplicate_check_rows(storage, values):
    from sqlalchemy import Boolean, false, literal, select, union_all

    from corpus_structure.semantic.data_operation_bindings import BindingCheck, BindingReason

    connection, _, projection = storage
    compiled = compile_binding(
        model(BindingExpression("scan", roles=("items",))),
        "urn:op",
        (projection,),
        subject="doc",
    )
    if values:
        records = union_all(
            *(select(literal(value, type_=Boolean()).label("valid")) for value in values)
        ).subquery()
        query = select(records.c.valid)
    else:
        query = select(literal(None, type_=Boolean())).where(false())
    compiled = replace(
        compiled,
        checks=(
            BindingCheck(
                BindingReason("control", "transport-control", "control"), query, "invalid"
            ),
        ),
    )
    message = "duplicate or unexpected" if values else "incomplete"
    with pytest.raises(ValueError, match=message + " SQL binding check"):
        execute_binding(connection, compiled)


def test_binding_decoder_refuses_missing_or_forged_emitting_occurrence(storage):
    connection, relation, projection = storage
    compiled = compile_binding(
        model(BindingExpression("scan", roles=("items",))), "urn:op", (projection,), subject="doc"
    )
    for evidence in (
        {"trust": "pinned"},
        {
            "producer_output": {
                "member_id": "foreign",
                "role": "result",
                "position": 0,
                "multiplicity": 1,
            }
        },
        {
            "producer_output": {
                "member_id": None,
                "role": "result",
                "position": -1,
                "multiplicity": 1,
            }
        },
    ):
        connection.execute(relation.update().values(support_evidence=evidence))
        assert execute_binding(connection, compiled).status == "invalid"
