"""Independent PostgreSQL vectors for the shared frozen binding AST interpreter."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pglast
import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_binding_native import (
    binding_native_sources,
    binding_native_sql,
)
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_native_binding_source_closure_and_helper_syntax():
    sources = {source.name: source.content for source in binding_native_sources()}
    assert set(sources) == {
        "native/data-operation-bindings.sql",
        "native/data-operation-binding-native.py",
    }
    prepared = prepare_sql(binding_native_sql(), source="binding-test")
    names = []
    for index, raw in enumerate(prepared.statements):
        assert isinstance(raw.stmt, ast.CreateFunctionStmt)
        name = (raw.stmt.funcname or ())[-1].sval
        names.append(name)
        if name != "ddo_require_binding":
            # The isolated PL/pgSQL parser cannot resolve application table rowtypes.
            pglast.parse_plpgsql(prepared.excerpt(index))
    assert "ddo_require_binding" in names
    assert {"ddo_binding_test", "ddo_binding_values", "ddo_binding_population_refs"} <= set(names)


@pytest.fixture
def binding_native_connection(semantic_db_engine):
    with semantic_db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            kernel_path = (
                Path(__file__).resolve().parents[2]
                / "src/corpus_structure/semantic/sql/data_operations.sql"
            )
            kernel = prepare_sql(kernel_path.read_text(), source="binding-codecs")
            for index, raw in enumerate(kernel.statements):
                if isinstance(raw.stmt, ast.CreateFunctionStmt) and (raw.stmt.funcname or ())[
                    -1
                ].sval in {
                    "ddo_normalize",
                    "ddo_field",
                    "ddo_json",
                }:
                    connection.exec_driver_sql(
                        kernel.excerpt(index), execution_options={"no_parameters": True}
                    )
            helpers = prepare_sql(binding_native_sql(), source="binding-helpers")
            for index, raw in enumerate(helpers.statements):
                assert isinstance(raw.stmt, ast.CreateFunctionStmt)
                if (raw.stmt.funcname or ())[-1].sval != "ddo_require_binding":
                    connection.exec_driver_sql(
                        helpers.excerpt(index), execution_options={"no_parameters": True}
                    )
            yield connection
        finally:
            transaction.rollback()


def row(value: Any, *, product=None, member=None, kind="integer") -> dict[str, Any]:
    value_tag = [kind, str(value)] if kind != "string" else [kind, value]
    return {
        "product": product or f"p{value}",
        "member": member or f"m{value}",
        "kind_contract": "kind:item",
        "subject": "doc",
        "original_source": "source",
        "position": value if isinstance(value, int) else 0,
        "multiplicity": 1,
        "body": {"value": value, "base": "b", "member": member or f"m{value}"},
        "meaning_body": [
            "mapping",
            [
                ["base", ["string", "b"]],
                ["member", ["string", member or f"m{value}"]],
                ["value", value_tag],
            ],
        ],
    }


def context(*values: Any) -> dict[str, Any]:
    members = [row(value) for value in values]
    population = {
        "identity": "population:fixed",
        "complete": True,
        "members": [item["member"] for item in members],
        "evidence": {"authentic": True},
    }
    return {
        "model": {
            "kinds": [
                {
                    "semantic_id": "primitive:integer",
                    "name": "integer",
                    "category": "primitive",
                    "facts": {"json": {"primitive": "integer"}},
                },
                {
                    "semantic_id": "primitive:string",
                    "name": "string",
                    "category": "primitive",
                    "facts": {"json": {"primitive": "string"}},
                },
                {
                    "semantic_id": "primitive:float",
                    "name": "float",
                    "category": "primitive",
                    "facts": {"json": {"primitive": "float"}},
                },
                {
                    "semantic_id": "urn:item",
                    "name": "Item",
                    "category": "class",
                    "facts": {"json": {}},
                },
                {
                    "semantic_id": "urn:item/property/value",
                    "category": "property",
                    "facts": {"json": {"range": "primitive:integer"}},
                },
                {
                    "semantic_id": "urn:item/property/base",
                    "category": "property",
                    "facts": {"json": {"range": "primitive:string"}},
                },
                {
                    "semantic_id": "urn:item/property/member",
                    "category": "property",
                    "facts": {"json": {"range": "primitive:string"}},
                },
            ]
        },
        "roledefs": [
            {
                "name": name,
                "kind": "urn:item",
                "kind_contract": "kind:item",
                "accepted_kind_contracts": ["kind:item"],
                "collection": "set",
            }
            for name in ("items", "left", "right", "shared")
        ],
        "roles": {"items": members, "left": [], "right": [], "shared": []},
        "universe": members,
        "populations": {"retained": population},
        "witnesses": {"items": population},
        "parameters": {"allowed": [2, 3]},
        "parameterdefs": {},
        "choices": {},
        "subject": "doc",
        "original_source": "source",
    }


def field(role="items", name="value", value_type="integer"):
    return {
        "kind": "field",
        "value_type": value_type,
        "field": {"role": role, "projection": "urn:item", "field": name},
    }


def literal(value):
    return {"kind": "literal", "value_type": "integer", "value": {"json": ["integer", str(value)]}}


def evaluate(connection, node, facts):
    return connection.scalar(
        text("SELECT ops.ddo_binding_test(CAST(:node AS jsonb),CAST(:facts AS jsonb))"),
        {"node": json.dumps(node), "facts": json.dumps(facts)},
    )


@pytest.mark.db
def test_native_ranges_membership_literal_and_field_equality(binding_native_connection):
    connection = binding_native_connection
    facts = context(2, 3)
    assert (
        evaluate(
            connection, {"operator": "range", "operands": [field(), literal(2), literal(3)]}, facts
        )
        is True
    )
    assert (
        evaluate(
            connection, {"operator": "range", "operands": [field(), literal(3), literal(4)]}, facts
        )
        is False
    )
    assert (
        evaluate(
            connection,
            {
                "operator": "membership",
                "operands": [
                    field(),
                    {"kind": "parameter", "name": "allowed", "value_type": "integer"},
                ],
            },
            facts,
        )
        is True
    )
    assert (
        evaluate(
            connection,
            {
                "operator": "literal",
                "fields": [field()["field"]],
                "value": {"json": ["integer", "2"]},
            },
            facts,
        )
        is False
    )
    facts["roles"].update(left=[row(2)], right=[row(3)])
    node = {"operator": "equal", "operands": [field("left"), field("right")]}
    assert evaluate(connection, node, facts) is False
    facts["roles"]["right"] = [row(2)]
    assert evaluate(connection, node, facts) is True


@pytest.mark.db
def test_native_role_bundles_identity_collection_and_cardinality(binding_native_connection):
    connection = binding_native_connection
    facts = context(2, 3)
    facts["roles"].update(left=[row(2)], right=[row(3)])
    assert evaluate(connection, {"operator": "distinct", "roles": ["left", "right"]}, facts) is True
    facts["roles"]["right"] = [row(2), row(3)]
    assert (
        evaluate(connection, {"operator": "distinct", "roles": ["left", "right"]}, facts) is False
    )
    facts["roles"]["right"] = [row(2)]
    assert evaluate(connection, {"operator": "same", "roles": ["left", "right"]}, facts) is True
    assert (
        evaluate(
            connection,
            {"operator": "cardinality", "roles": ["items"], "minimum": 2, "maximum": 2},
            facts,
        )
        is True
    )
    assert (
        evaluate(connection, {"operator": "cardinality", "roles": ["items"], "maximum": 1}, facts)
        is False
    )
    assert (
        evaluate(
            connection, {"operator": "collection", "roles": ["items"], "collection": "set"}, facts
        )
        is True
    )


@pytest.mark.db
def test_native_closed_population_and_current_universe_negation(binding_native_connection):
    connection = binding_native_connection
    facts = context(2, 3)
    node = {
        "operator": "forall",
        "roles": ["items"],
        "population": "retained",
        "children": [{"operator": "scan", "roles": ["items"]}],
    }
    assert evaluate(connection, node, facts) is True
    facts["roles"]["items"] = [row(2)]
    assert evaluate(connection, node, facts) is False
    absent = {"operator": "absent", "roles": ["items"], "population": "retained"}
    facts["roles"]["items"] = []
    assert (
        evaluate(connection, absent, facts) is False
    )  # Selected emptiness is not a negative proof.
    filtered_absence = {
        **absent,
        "children": [
            {
                "operator": "literal",
                "fields": [field()["field"]],
                "value": {"json": ["integer", "99"]},
            }
        ],
    }
    assert evaluate(connection, filtered_absence, facts) is True
    facts["universe"] = []
    with connection.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match="lacks admitted candidate facts"):
            evaluate(connection, absent, facts)
        savepoint.rollback()
    facts["populations"]["retained"]["members"] = []
    assert evaluate(connection, absent, facts) is True
    facts["witnesses"]["items"] = {**facts["witnesses"]["items"], "identity": "forged"}
    with connection.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match="witness differs"):
            evaluate(connection, absent, facts)
        savepoint.rollback()


@pytest.mark.db
def test_native_optional_filter_and_shared_selected_branch(binding_native_connection):
    connection = binding_native_connection
    facts = context(2)
    facts["parameterdefs"]["optional"] = {"required": False}
    optional = {
        "operator": "optional",
        "children": [
            {
                "operator": "equal",
                "operands": [
                    field(),
                    {"kind": "parameter", "value_type": "integer", "name": "optional"},
                ],
            }
        ],
    }
    assert evaluate(connection, optional, facts) is True
    facts["parameters"]["optional"] = 9
    assert evaluate(connection, optional, facts) is False
    facts["roles"].update(left=[row(2)], right=[], shared=[row(2)])
    facts["choices"] = {"producer": "left"}
    choice = {
        "operator": "choice",
        "choice_parameter": "producer",
        "children": [
            {"operator": "scan", "roles": ["left", "shared"]},
            {"operator": "scan", "roles": ["right", "shared"]},
        ],
    }
    assert evaluate(connection, choice, facts) is True
    facts["roles"]["right"] = [row(2)]
    assert evaluate(connection, choice, facts) is False


@pytest.mark.db
def test_native_float_lexical_and_null_operands_remain_exact(binding_native_connection):
    connection = binding_native_connection
    for lexical in (
        "0x0.0000000000001p-1022",
        "0x1.fffffffffffffp+1023",
        "-0x1.0000000000000p-1022",
    ):
        actual = connection.scalar(
            text("SELECT ops.ddo_binding_float(:lexical)=CAST(:expected AS numeric)"),
            {"lexical": lexical, "expected": str(Decimal.from_float(float.fromhex(lexical)))},
        )
        assert actual is True
    facts = context(2)
    value_entry = next(
        entry for entry in facts["roles"]["items"][0]["meaning_body"][1] if entry[0] == "value"
    )
    value_entry[1] = ["null"]
    with connection.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match="unknown or null"):
            evaluate(
                connection,
                {"operator": "range", "operands": [field(), literal(1), literal(3)]},
                facts,
            )
        savepoint.rollback()


@pytest.mark.db
def test_native_population_projection_separates_semantics_and_receipt(binding_native_connection):
    connection = binding_native_connection
    witness = {
        "identity": "population:stable",
        "complete": True,
        "members": ["m2"],
        "evidence": {
            "population_id": "receipt:one",
            "derivation_id": "episode:one",
            "trust_snapshot": {"scope": 1},
        },
    }
    query = text("SELECT ops.ddo_binding_population_meaning(CAST(:w AS jsonb),:exact)")
    plain = connection.scalar(query, {"w": json.dumps(witness), "exact": False})
    exact = connection.scalar(query, {"w": json.dumps(witness), "exact": True})
    assert plain == {"identity": "population:stable", "complete": True, "members": ["m2"]}
    assert exact == {**plain, "support_episodes": ["episode:one"]}


@pytest.mark.db
def test_native_declared_property_wins_over_physical_header_and_typed_parameters(
    binding_native_connection,
):
    connection = binding_native_connection
    facts = context(2)
    facts["model"]["kinds"].append(
        {
            "semantic_id": "urn:item/property/subject",
            "category": "property",
            "facts": {"json": {"range": "primitive:string"}},
        }
    )
    facts["roles"]["items"][0]["meaning_body"][1].append(
        ["subject", ["string", "linguistic-subject"]]
    )
    node = {
        "operator": "literal",
        "fields": [field(name="subject", value_type="string")["field"]],
        "value": {"json": ["string", "linguistic-subject"]},
    }
    assert facts["roles"]["items"][0]["subject"] == "doc"
    assert evaluate(connection, node, facts) is True
    facts["parameters"] = {"sign": 0.0}
    facts["parameter_meaning"] = ["mapping", [["sign", ["float", "-0x0.0p+0"]]]]
    values = connection.scalar(
        text("SELECT ops.ddo_binding_values(CAST(:operand AS jsonb),CAST(:facts AS jsonb))"),
        {
            "operand": json.dumps({"kind": "parameter", "name": "sign", "value_type": "float"}),
            "facts": json.dumps(facts),
        },
    )
    assert values == [["float", "-0x0.0p+0"]]


@pytest.mark.db
def test_native_subject_association_preserves_original_subject(binding_native_connection):
    connection = binding_native_connection
    value = row(2)
    value["subject"] = "view:original"
    role = {"subject_field": "base"}

    def matches(definition, subject):
        return connection.scalar(
            text(
                "SELECT ops.ddo_binding_subject(CAST(:role AS jsonb),CAST(:row AS jsonb),:subject)"
            ),
            {"role": json.dumps(definition), "row": json.dumps(value), "subject": subject},
        )

    assert matches(role, "b") is True
    assert matches(role, "foreign") is False
    assert matches({}, "view:original") is True
    assert matches({}, "b") is False
    assert value["subject"] == "view:original"


def test_native_covers_requires_every_requested_value(binding_native_connection):
    node = {
        "operator": "covers",
        "operands": [field(), {"kind": "parameter", "name": "allowed", "value_type": "integer"}],
    }
    assert evaluate(binding_native_connection, node, context(1, 2, 3)) is True
    assert evaluate(binding_native_connection, node, context(1, 2)) is False
    facts = context(1, 2)
    facts["parameters"]["allowed"] = []
    assert evaluate(binding_native_connection, node, facts) is True
    facts["parameters"]["allowed"] = [2, 2]
    assert evaluate(binding_native_connection, node, facts) is True
    facts["parameters"]["allowed"] = [True]
    with pytest.raises(DBAPIError, match=r"type|boolean|integer"):
        evaluate(binding_native_connection, node, facts)


def test_native_source_set_authenticates_exact_original_pins(binding_native_connection):
    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        SourceSetEntry,
        source_sets_record,
    )
    from corpus_structure.semantic.structural_products import ExternalSourceRef

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
    pin = SourceSetEntry.from_structural_source(
        reference,
        original_source="foreign-source",
        subject="view:original",
        analyzed_scope=b'{"page":1}',
        product="product:original",
        member="member:original",
    )
    scopes = source_sets_record((FrozenSourceSet("inputs", (pin,)),))
    binding_native_connection.execute(
        text("SELECT ops.ddo_validate_source_sets(CAST(:sets AS jsonb),'project')"),
        {"sets": json.dumps(scopes)},
    )
    actual = {
        "product": pin.product,
        "member": pin.member,
        "subject": pin.subject,
        "original_source": pin.original_source,
        "analyzed_scope": {"page": 1},
        "meaning_body": ["mapping", [["source_ref", ["string", reference.identity]]]],
    }
    roledef = {"support": {"source_set": "inputs", "source_reference_field": "source_ref"}}
    query = text(
        "SELECT ops.ddo_binding_source(CAST(:role AS jsonb),CAST(:row AS jsonb),"
        "'analysis-root',CAST(:sets AS jsonb))"
    )

    def admitted(row):
        return binding_native_connection.execute(
            query, {"role": json.dumps(roledef), "row": json.dumps(row), "sets": json.dumps(scopes)}
        ).scalar_one()

    assert admitted(actual) is True
    for key, value in (
        ("original_source", "analysis-root"),
        ("member", "other"),
        ("subject", "relabeled"),
        ("analyzed_scope", {"page": 2}),
    ):
        assert admitted({**actual, key: value}) is False
    forged = json.loads(json.dumps(scopes))
    forged["inputs"][0]["source_reference"] = "0" * 64
    with pytest.raises(DBAPIError, match="original qualified reference"):
        binding_native_connection.execute(
            text("SELECT ops.ddo_validate_source_sets(CAST(:sets AS jsonb),'project')"),
            {"sets": json.dumps(forged)},
        )


def test_native_population_local_member_collision_cannot_satisfy_closed_scope(
    binding_native_connection,
):
    facts = context(2)
    facts["populations"]["retained"]["evidence"]["product_id"] = "actual-container"
    population = facts["populations"]["retained"]
    facts["witnesses"]["items"] = population
    node = {
        "operator": "forall",
        "roles": ["items"],
        "population": "retained",
        "children": [{"operator": "scan", "roles": ["items"]}],
    }
    assert evaluate(binding_native_connection, node, facts) is False
    facts["roles"]["items"][0]["product"] = "actual-container"
    assert evaluate(binding_native_connection, node, facts) is True
    facts["roles"]["items"][0]["product"] = "different-container"
    membership = {
        "operator": "membership",
        "operands": [
            field(name="member", value_type="string"),
            {"kind": "population", "name": "retained", "value_type": "string"},
        ],
    }
    assert evaluate(binding_native_connection, membership, facts) is False
    facts["roles"]["items"] = []
    absent = {
        "operator": "absent",
        "roles": ["items"],
        "population": "retained",
        "children": [{"operator": "scan", "roles": ["items"]}],
    }
    with pytest.raises(DBAPIError, match="lacks admitted candidate facts"):
        evaluate(binding_native_connection, absent, facts)
