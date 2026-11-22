"""Available producer facts stay behind the existing authenticated binding reader."""

from types import SimpleNamespace
from typing import cast

import pytest
from pglast import ast
from psycopg.errors import CheckViolation, InsufficientPrivilege
from sqlalchemy import Integer, Text, column, literal, select, text, values
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_json import json_bytes, native_json_loads
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    admitted_data_read,
)
from corpus_structure.semantic.demand_results import read_demand_result
from corpus_structure.semantic.metadata import get_metadata, table
from corpus_structure.semantic.native_objects import native_owner
from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.declared_scenarios import declared_serving_case as declared_serving_case
from semantic.declared_scenarios import declared_serving_seed as declared_serving_seed


def _install_binding_projection(connection):
    from corpus_structure.semantic.data_operation_read_native import read_native_sql

    statements = prepare_sql(read_native_sql(get_metadata()), source="producer-observation-test")
    with native_owner(connection, "corpus_sem_publisher"):
        for index, statement in enumerate(statements.statements):
            node = statement.stmt
            if (
                isinstance(node, ast.CreateFunctionStmt)
                and node.funcname
                and node.funcname[-1].sval == "ddo_binding_rows"
            ):
                connection.exec_driver_sql(
                    statements.excerpt(index), execution_options={"no_parameters": True}
                )


def test_authorized_binding_observes_producer_without_disclosing_protected_support(
    declared_serving_case,
):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.producer_requirements import SelectedProducerContract

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    model = bound_data_operation_model(stage.prepared)
    with clone.reader.begin() as connection:
        page = read_demand_result(
            connection, stage.demand_id, project_id=stage.project_id, view="frontier"
        )
        pins = page.cut.record
        read = admitted_data_read(
            connection,
            stage.demand_id,
            "urn:ddo-test:source",
            pins["trust_snapshot"],
            model,
            read_id=pins["read_id"],
        )
        evidence = connection.execute(select(read.relation.c.support_evidence)).scalars().all()
    assert len(evidence) == 2
    observations = [
        SelectedProducerContract.model_validate_json(json_bytes(value["producer_contract"]))
        for value in evidence
    ]
    expected = native_json_loads(stage.source_receipt)["derivation_id"]
    assert {item.derivation_id for item in observations} == {expected}
    assert {item.release_id for item in observations} == {stage.prepared.release_id}
    assert all(item.publication_receipt for item in observations)
    assert all(item.cpu_receipt is False for item in observations)
    assert all(item.reference_inputs == () for item in observations)
    assert all(
        set(value["producer_contract"])
        == {
            "version",
            "derivation_id",
            "release_id",
            "runtime_id",
            "publication_receipt",
            "cpu_receipt",
            "admitted_effects",
            "validity_families",
            "reference_inputs",
        }
        for value in evidence
    )
    with pytest.raises(DBAPIError) as denied, clone.reader.begin() as connection:
        connection.execute(select(table("ops.data_completion_intent")))
    assert isinstance(denied.value.orig, InsufficientPrivilege)
    with clone.writer.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": stage.project_id,
                    "original_source": stage.original_source,
                    "selector_kind": "derivation",
                    "selector": expected,
                    "reason": "independent producer observation authority refusal",
                },
            )
        )
    with pytest.raises(DBAPIError) as stale, clone.reader.begin() as connection:
        read = admitted_data_read(
            connection,
            stage.demand_id,
            "urn:ddo-test:source",
            pins["trust_snapshot"],
            model,
            read_id=pins["read_id"],
        )
        connection.execute(select(read.relation.c.support_evidence)).all()

    assert isinstance(stale.value.orig, CheckViolation)


def test_updated_binding_producer_projection_compiles_in_native_rollback(native_rollback):
    connection = native_rollback.connection
    connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    _install_binding_projection(connection)
    signature = "ops.ddo_binding_rows(text,text,jsonb,text,text,jsonb,jsonb,boolean,jsonb,boolean)"
    errors = (
        connection.execute(
            text(
                "SELECT message FROM public.plpgsql_check_function_tb(CAST(:signature AS regprocedure),fatal_errors=>false) WHERE level='error'"
            ),
            {"signature": signature},
        )
        .scalars()
        .all()
    )
    assert errors == []


def test_reference_metadata_requires_exact_original_edge_in_the_selected_use(native_rollback):
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.producer_correspondence_native import _selected_reference_inputs
    from corpus_structure.semantic.producer_requirements import SelectedProducerContract
    from corpus_structure.semantic.reference_resolution import ProducingReferenceBindings

    def relation(name, fields, rows):
        return values(*(column(field, kind) for field, kind in fields)).data(rows).cte(name)

    def pin(role, product, *, position=0, member=None, multiplicity=1):
        return {
            "role": role,
            "position": position,
            "product_id": product,
            "member_id": member,
            "multiplicity": multiplicity,
        }

    hidden_and_unrelated = [pin("protected", "protected-parent"), pin("other", "unrelated-parent")]
    left = pin("reports", "left-report")
    right = pin("reports", "right-report", position=1, member="right-member")
    hidden = pin("reports", "hidden-report", position=2)
    unmatched = pin("reports", "unmatched-report", position=3, multiplicity=2)
    repeated = pin("reports", "repeated-report", position=4)
    uses = relation(
        "actual_uses",
        (("id", Text), ("derivation_id", Text), ("fate", Text), ("selection", JSONB)),
        [
            (
                "authentic-use",
                "historical-derivation",
                "fulfilled",
                {
                    "inputs": [
                        pin("source", "original-parent"),
                        *hidden_and_unrelated,
                        left,
                        right,
                        hidden,
                        unmatched,
                    ],
                },
            ),
            (
                "substituted-use",
                "historical-derivation",
                "fulfilled",
                {
                    "inputs": [pin("source", "equal-content-replacement"), *hidden_and_unrelated],
                },
            ),
            (
                "duplicate-use",
                "historical-derivation",
                "fulfilled",
                {"inputs": [left, repeated]},
            ),
        ],
    )
    inputs = relation(
        "actual_original_edges",
        (
            ("derivation_id", Text),
            ("role", Text),
            ("position", Integer),
            ("multiplicity", Integer),
            ("product_id", Text),
            ("member_id", Text),
        ),
        [
            ("historical-derivation", "source", 0, 1, "original-parent", None),
            ("historical-derivation", "protected", 0, 1, "protected-parent", None),
            ("historical-derivation", "other", 0, 1, "unrelated-parent", None),
            ("historical-derivation", "reports", 0, 1, "left-report", None),
            ("historical-derivation", "reports", 1, 1, "right-report", "right-member"),
            ("historical-derivation", "reports", 2, 1, "hidden-report", None),
            ("historical-derivation", "reports", 3, 1, "unmatched-report", None),
            ("historical-derivation", "reports", 4, 1, "repeated-report", None),
        ],
    )
    products = relation(
        "actual_products",
        (("id", Text), ("project_id", Text), ("kind_contract", Text), ("canonical_body", JSONB)),
        [
            ("original-parent", "project", "source-kind", {"private": "original body"}),
            ("equal-content-replacement", "project", "source-kind", {"private": "original body"}),
            ("protected-parent", "project", "evaluator-kind", {"private": "concealed body"}),
            ("unrelated-parent", "project", "source-kind", {"private": "unrelated body"}),
            (
                "left-report",
                "project",
                "source-kind",
                semantic_value({"local": "left", "source": {"key": "L"}}),
            ),
            ("right-report", "project", "source-kind", semantic_value({"local": "wrong parent"})),
            # These values are deliberately untagged. Reading their fields
            # before exact support and disclosure would fail native decoding.
            ("hidden-report", "project", "evaluator-kind", {"private": "hidden"}),
            ("unmatched-report", "project", "source-kind", {"private": "unmatched"}),
            ("repeated-report", "project", "source-kind", semantic_value({"local": "left"})),
        ],
    )
    members = relation(
        "actual_members",
        (("product_id", Text), ("member_id", Text), ("kind_contract", Text), ("body", JSONB)),
        [
            (
                "right-report",
                "right-member",
                "source-kind",
                semantic_value({"local": "right", "source": {"key": "R"}}),
            )
        ],
    )
    selected = relation(
        "selected_producer_use",
        (("use_id", Text), ("output_role", Text)),
        [("authentic-use", "result"), ("substituted-use", "result"), ("duplicate-use", "result")],
    )
    episodes = relation("actual_episode", (("id", Text),), [("historical-derivation",)])
    requests = relation("actual_request", (("project_id", Text),), [("project",)])
    definitions = relation(
        "actual_definition",
        (("support_contract", JSONB),),
        [
            (
                {
                    "reference_targets": [
                        {"output_role": "result", "input_role": "source"},
                        {"output_role": "result", "input_role": "protected"},
                        {
                            "output_role": "result",
                            "input_role": "reports",
                            "occurrence_field": "/local",
                        },
                        {
                            "output_role": "result",
                            "input_role": "reports",
                            "occurrence_field": "/source/key",
                        },
                        {
                            "output_role": "result",
                            "input_role": "reports",
                            "occurrence_field": "/local",
                            "path": "/other",
                        },
                        {
                            "output_role": "different",
                            "input_role": "reports",
                            "occurrence_field": "/hidden",
                        },
                    ]
                },
            )
        ],
    )
    metadata = SimpleNamespace(
        tables={
            "ops.data_derivation_input": inputs,
            "ops.demand_use": uses,
            "kb.data_product": products,
            "kb.data_product_member": members,
        }
    )
    projection = _selected_reference_inputs(
        metadata,
        selected,
        episodes,
        requests,
        definitions,
        body_eligible=lambda kind, _body: kind == "source-kind",
        body_access=lambda _kind, _body: literal(True),
    )
    rows = native_rollback.connection.execute(
        select(selected.c.use_id, projection).select_from(
            selected.join(episodes, literal(True))
            .join(requests, literal(True))
            .join(
                definitions,
                literal(True),
            )
        )
    ).all()
    observations = dict(rows)
    authentic = observations["authentic-use"]
    assert len(authentic) == 5
    assert authentic[-1] == {
        "role": "source",
        "product_id": "original-parent",
        "kind_contract": "source-kind",
        "member_id": None,
        "multiplicity": 1,
    }
    assert observations["substituted-use"] == []
    assert [
        (row["product_id"], row["member_id"], row["occurrence_field"], row["occurrence"])
        for row in authentic[:-1]
    ] == [
        ("left-report", None, "/local", "left"),
        ("left-report", None, "/source/key", "L"),
        ("right-report", "right-member", "/local", "right"),
        ("right-report", "right-member", "/source/key", "R"),
    ]

    def producing(use):
        contract = SelectedProducerContract.model_validate_json(
            json_bytes(
                {
                    "version": "selected-producer-contract-v1",
                    "derivation_id": "historical-derivation",
                    "release_id": "release",
                    "runtime_id": "runtime",
                    "publication_receipt": True,
                    "cpu_receipt": False,
                    "admitted_effects": [],
                    "validity_families": [],
                    "reference_inputs": observations[use],
                }
            )
        )
        return ProducingReferenceBindings(contract.derivation_id, contract.reference_inputs)

    assert (
        producing("authentic-use")
        .resolve(SemanticReference.whole("reports", occurrence="L"), occurrence_field="/source/key")
        .product_id
        == "left-report"
    )
    with pytest.raises(ValueError, match="exactly one producing input occurrence"):
        producing("duplicate-use").resolve(
            SemanticReference.whole("reports", occurrence="left"), occurrence_field="/local"
        )
    with pytest.raises(ValueError, match="lacks its declared reference occurrence"):
        producing("duplicate-use").resolve(
            SemanticReference.whole("reports", occurrence="L"), occurrence_field="/source/key"
        )
