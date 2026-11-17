"""Bare-schema SQL basis controls; synthetic metadata grants no native admission."""

from typing import Literal, TypedDict

import pytest
from pglast import ast
from sqlalchemy import cast, literal, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_cpu_basis import (
    CPUInputRole,
    cpu_authority_reply,
    cpu_authority_value,
    cpu_basis_values,
    cpu_input_basis,
    cpu_input_basis_native_sql,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_json import DdoJsonValue
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence


class _Context(TypedDict):
    project_id: str
    subject: str
    subject_definition: str
    original_source: str | None
    analyzed_scope: DdoJsonValue


class _Support(TypedDict):
    kind: Literal["computation"]
    derivation_id: str


class _ProducerOutput(TypedDict):
    member_id: str | None
    role: str
    position: int
    multiplicity: int


class _Role(TypedDict):
    role: str
    position: int | None
    multiplicity: int
    product_id: str
    member_id: str | None
    kind_contract: str
    context: _Context
    body: DdoJsonValue
    support: list[_Support]
    producer_output: _ProducerOutput


@pytest.fixture
def cpu_basis_connection(semantic_bare_engine):
    from importlib.resources import files

    from corpus_structure.semantic.data_operation_binding_native import binding_native_sql
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    root = files("corpus_structure.semantic").joinpath("sql")
    closure = root.joinpath("closure.sql").read_text()
    with semantic_bare_engine.begin() as connection:
        for schema in ("ops", "sem", "data", "kb"):
            connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        for name in (
            "ops.data_request",
            "sem.data_operation_definition",
            "kb.data_product",
            "kb.data_product_member",
            "ops.data_derivation_output",
            "ops.original_source_admission",
        ):
            connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
        for source, names in (
            (root.joinpath("identity.sql").read_text(), {"canonical_json", "decimal_canonical"}),
            (closure, {"require_float_lexical"}),
            (
                native_sql(native_protocol_sources()),
                {
                    "ddo_normalize",
                    "ddo_json_meaning",
                    "ddo_field",
                    "ddo_operation_subject",
                    "ddo_digest",
                    "ddo_cpu_reply_value",
                },
            ),
            (binding_native_sql(), {"ddo_input_support_selection", "ddo_input_support_refs"}),
            (cpu_input_basis_native_sql(), {"ddo_cpu_input_basis", "ddo_cpu_reply_output"}),
        ):
            parsed = prepare_sql(source, source="cpu-actual-input-basis-control")
            for index, statement in enumerate(parsed.statements):
                node = statement.stmt
                if (
                    isinstance(node, ast.CreateFunctionStmt)
                    and node.funcname
                    and node.funcname[-1].sval in names
                ):
                    connection.exec_driver_sql(
                        parsed.excerpt(index), execution_options={"no_parameters": True}
                    )
        yield connection


def test_basis_reads_exact_products_contexts_and_origin_support_sets(cpu_basis_connection):
    from decimal import Decimal

    from corpus_structure.semantic.data_operation_json import json_bytes

    connection = cpu_basis_connection
    connection.execute(
        table("sem.data_operation_definition")
        .insert()
        .values(
            release_id="release:actual",
            operation_id="rich.admit",
            subject_definition="subject:knowledge",
            recipe="recipe:actual",
            profile="command",
            implementation_revision="implementation-slice:controlled",
            input_roles=[],
            output_roles=[],
            support_contract={},
        )
    )
    rows: list[_Role] = []
    for product, episode, value in (
        ("product:b", "episode:b", 0.0),
        ("product:a", "episode:a", -0.0),
    ):
        body: DdoJsonValue = {"members": [], "potential": value}
        context: _Context = {
            "project_id": "project:actual",
            "subject": "source:" + product,
            "subject_definition": "subject:record",
            "original_source": "original:" + product,
            "analyzed_scope": {"fraction": Decimal("0.123456789123456789")},
        }
        connection.execute(
            table("kb.data_product")
            .insert()
            .values(
                id=product,
                kind_contract="kind:record-report",
                **{
                    **context,
                    "analyzed_scope": cast(
                        literal(json_bytes(context["analyzed_scope"]).decode()), JSONB
                    ),
                },
                canonical_body=semantic_value(body),
                body_digest="a" * 64,
            )
        )
        connection.execute(
            table("ops.data_derivation_output")
            .insert()
            .values(
                derivation_id=episode,
                role="result",
                position=0,
                multiplicity=1,
                product_id=product,
            )
        )
        rows.append(
            {
                "role": "records",
                "position": None,
                "multiplicity": 1,
                "product_id": product,
                "member_id": None,
                "kind_contract": "kind:record-report",
                "context": context,
                "body": body,
                "support": [{"kind": "computation", "derivation_id": episode}],
                "producer_output": {
                    "member_id": None,
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                },
            }
        )
    context = {
        "project_id": "project:actual",
        "subject": "knowledge:actual",
        "subject_definition": "subject:knowledge",
        "original_source": None,
        "analyzed_scope": {"number": Decimal("1")},
    }
    # Null set positions are genuine. The flat binding repeats a support when
    # several rows share it; exact product correspondence keeps unrelated
    # episodes out and support-set normalization removes repeated references.
    inputs = [
        {
            **{
                key: row[key]
                for key in (
                    "role",
                    "position",
                    "multiplicity",
                    "product_id",
                    "member_id",
                    "producer_output",
                )
            },
            "support_derivation_ids": sorted(
                reference["derivation_id"] for reference in row["support"]
            ),
        }
        for row in rows
    ]
    supports = [
        {**reference, "role": "records", "position": None}
        for row in rows
        for reference in row["support"]
    ]
    parameters = {"selected": Decimal("0.1234567890123456789"), "present_null": None}
    request = {
        **context,
        "release_id": "release:actual",
        "operation_id": "rich.admit",
        "recipe": "recipe:actual",
        "binding": {
            "inputs": inputs,
            "support": [*supports, supports[0]],
            "parameters": semantic_value({"parameters": parameters, "replicate": None}),
        },
    }
    expected = {
        "version": "cpu-input-basis-3",
        "recipe": "recipe:actual",
        "context": context,
        "roles": sorted(rows, key=lambda row: row["product_id"]),
        "parameters": {"selected": Decimal("0.1234567890123456789"), "present_null": None},
        "replicate": None,
    }
    actual = connection.scalar(
        text(
            "SELECT ops.ddo_cpu_input_basis(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)))"
        ),
        {"r": json_bytes(request).decode()},
    )
    assert actual == semantic_value(expected)

    def subject(value: _Context):
        return SubjectContext(
            value["project_id"],
            value["subject"],
            value["original_source"],
            json_bytes(value["analyzed_scope"]),
            subject_definition=value["subject_definition"],
        )

    processed = tuple(
        CPUInputRole(
            row["role"],
            row["position"],
            row["multiplicity"],
            row["product_id"],
            row["member_id"],
            row["kind_contract"],
            subject(row["context"]),
            row["body"],
            tuple(
                ComputationalSupportReference(**ref) for ref in (*row["support"], *row["support"])
            ),
            producer_output=ProducerOutputOccurrence(**row["producer_output"]),
        )
        for row in rows
    )
    assert cpu_input_basis(
        "recipe:actual",
        subject(context),
        processed,
        parameters=json_bytes(semantic_value(parameters)),
        replicate=None,
    ) == semantic_value(expected)


def test_cpu_basis_preserves_emitting_occurrence_for_projected_members():
    from dataclasses import replace

    from corpus_structure.semantic.data_operation_json import json_bytes

    context = SubjectContext(
        "project:controlled",
        "source:selected",
        None,
        b"{}",
        subject_definition="subject:controlled",
    )
    role = CPUInputRole(
        "selected",
        None,
        1,
        "product:controlled",
        "member:selected",
        "kind:controlled",
        context,
        {"value": 7},
        (
            ComputationalSupportReference(
                derivation_id="episode:chosen", admission_use_id="use:chosen"
            ),
        ),
        producer_output=ProducerOutputOccurrence(
            member_id=None,
            role="emitted",
            position=7,
            multiplicity=2,
        ),
    )

    def basis(value):
        return cpu_input_basis(
            "recipe:controlled",
            context,
            (value,),
            parameters=json_bytes(semantic_value({})),
            replicate=None,
        )

    actual = basis(role)
    meaning = decode_semantic_value(actual)
    assert meaning["version"] == "cpu-input-basis-3"
    assert meaning["roles"][0]["member_id"] == "member:selected"
    assert meaning["roles"][0]["position"] is None
    assert meaning["roles"][0]["multiplicity"] == 1
    assert meaning["roles"][0]["producer_output"] == {
        "member_id": None,
        "role": "emitted",
        "position": 7,
        "multiplicity": 2,
    }
    values, observed_context = cpu_basis_values(actual, scalar_roles=("selected",), set_roles=())
    assert observed_context == context
    assert values["selected"][0].producer_output == role.producer_output

    # Equal values/support do not make emitting output slots interchangeable.
    reply = json_bytes(cpu_authority_reply(actual, {"accepted": True}))
    for changed in (
        ProducerOutputOccurrence(
            member_id="member:selected", role="emitted", position=7, multiplicity=2
        ),
        ProducerOutputOccurrence(member_id=None, role="other", position=7, multiplicity=2),
        ProducerOutputOccurrence(member_id=None, role="emitted", position=8, multiplicity=2),
        ProducerOutputOccurrence(member_id=None, role="emitted", position=7, multiplicity=1),
    ):
        other = basis(replace(role, producer_output=changed))
        assert other != actual
        with pytest.raises(ValueError, match="processed input basis"):
            cpu_authority_value(reply, expected_basis=other)

    meaning["version"] = "cpu-input-basis-2"
    with pytest.raises(ValueError, match="current exact input basis"):
        cpu_basis_values(semantic_value(meaning), scalar_roles=("selected",), set_roles=())


def test_cpu_computational_headers_require_corresponding_output():
    context = SubjectContext(
        "project:controlled",
        "source:selected",
        None,
        b"{}",
        subject_definition="subject:controlled",
    )
    base = (
        "selected",
        None,
        1,
        "product:controlled",
        "member:selected",
        "kind:controlled",
        context,
        {"value": 7},
    )
    support = (ComputationalSupportReference(derivation_id="episode:chosen"),)
    with pytest.raises(ValueError, match="exact emitting occurrence"):
        CPUInputRole(*base, support, producer_output=None)
    with pytest.raises(ValueError, match="selected member"):
        CPUInputRole(
            *base,
            support,
            producer_output=ProducerOutputOccurrence(
                member_id="member:sibling",
                role="result",
                position=0,
                multiplicity=1,
            ),
        )
    with pytest.raises(ValueError, match="exact emitting occurrence"):
        CPUInputRole(
            *base,
            (),
            producer_output=ProducerOutputOccurrence(
                member_id=None,
                role="result",
                position=0,
                multiplicity=1,
            ),
        )
    assert CPUInputRole(*base, (), producer_output=None).producer_output is None
