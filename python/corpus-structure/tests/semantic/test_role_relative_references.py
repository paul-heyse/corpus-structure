"""Declared reference controls at the Python and generated native boundaries."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_completion_settlement_native import (
    completion_settlement_native_programs,
)
from corpus_structure.semantic.data_operation_partitions import partition_packet
from corpus_structure.semantic.data_operation_read_native import read_native_programs
from corpus_structure.semantic.data_operation_reference_native import reference_native_programs
from corpus_structure.semantic.data_product_reference import (
    SemanticReference,
    read_semantic_reference,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.reference_resolution import (
    AcquiredReferencePartition,
    ProducingReferenceBindings,
    ProducingReferenceInput,
    ReferenceResolver,
    ReferenceTarget,
)
from semantic.test_data_product_admission_programs import partition_fixture, product_packet, realize
from semantic.test_data_product_admission_programs import product_connection as product_connection


@pytest.mark.parametrize(
    "value",
    [
        SemanticReference.whole("inventory"),
        SemanticReference.member("inventory", "token"),
        SemanticReference.item("inventory", "rows", "block", ("sentence", 2), occurrence="source"),
    ],
)
def test_reference_carrier_preserves_address_without_product_identity(value):
    record = json.loads(json.dumps(value.values()))
    assert read_semantic_reference(record) == value
    with pytest.raises(ValueError):
        read_semantic_reference({**record, "product_id": "wrong"})


def test_reference_item_key_requires_nominal_atoms_and_exact_python_scalar_types():
    reference = SemanticReference.item("inventory", "rows", "block", ("sentence", 2))
    assert reference.values()["item_key"] == [
        {"kind": "text", "text": "sentence"},
        {"kind": "integer", "integer": 2},
    ]
    for invalid in (
        "sentence",
        {"kind": "text", "text": ""},
        {"kind": "text", "text": "sentence", "integer": 2},
        {"kind": "integer", "integer": True},
        {"kind": "integer", "integer": 2.0},
    ):
        with pytest.raises(ValueError, match="exact text or integer"):
            read_semantic_reference({**reference.values(), "item_key": [invalid]})


def test_resolve_exact_producing_occurrence_and_authorize_even_on_cache_hit(monkeypatch):
    from corpus_structure.semantic import reference_resolution

    admitted = ProducingReferenceInput(
        "inventory", "producing-parent", "kind", occurrence="origin", occurrence_field="/key"
    )
    sibling = replace(admitted, product_id="same-content", occurrence="sibling")
    target = ReferenceTarget("inventory", "partition-item", "kind", "rows", occurrence_field="/key")
    ref = SemanticReference.item("inventory", "rows", "block", ("sentence", 2), occurrence="origin")
    packet = partition_packet("rows", "block", 0, 0, 3, [{"kind": "sentence", "index": 2}])
    decoder = reference_resolution.decode_semantic_value
    decoded = []

    def decode(meaning):
        decoded.append(meaning)
        return decoder(meaning)

    monkeypatch.setattr(reference_resolution, "decode_semantic_value", decode)

    class Access:
        allowed = True
        lookups = 0

        def authorize(self, binding):
            if binding not in (admitted, sibling) or not self.allowed:
                raise PermissionError("target denied")

        def product(self, product_id: str) -> object:
            raise AssertionError("unexpected product read")

        def member(self, product_id: str, member_id: str) -> object:
            raise AssertionError("unexpected member read")

        def partition(
            self, product_id: str, collection: str, partition_key: str
        ) -> AcquiredReferencePartition:
            assert product_id in ("producing-parent", "same-content")
            assert (collection, partition_key) == ("rows", "block")
            self.lookups += 1
            return AcquiredReferencePartition(
                packet["partition_digest"], packet["body"], ("kind", "index")
            )

    access = Access()
    resolver = ReferenceResolver(ProducingReferenceBindings("actual", (admitted, sibling)), access)
    first = resolver.resolve(ref, target)
    assert isinstance(first, dict) and first == {"kind": "sentence", "index": 2}
    first["index"] = 4
    assert resolver.resolve(replace(ref, occurrence="sibling"), target) == {
        "kind": "sentence",
        "index": 2,
    }
    with pytest.raises(ValueError, match="does not resolve"):
        resolver.resolve(replace(ref, item_key=("sentence", 3)), target)
    with pytest.raises(ValueError, match="declared slot target"):
        resolver.resolve(replace(ref, occurrence=None), target)
    access.allowed = False
    with pytest.raises(PermissionError):
        resolver.resolve(ref, target)
    assert access.lookups == 2
    assert decoded == [packet["body"]]


def test_native_declared_partition_reference_requires_actual_bound_item(product_connection):
    conn = product_connection
    metadata = get_metadata()
    context, product, _, _ = partition_fixture(conn)
    admitted = realize(conn, context, product)
    conn.execute(
        CreateTable(metadata.tables["ops.data_request"], include_foreign_key_constraints=[])
    )
    conn.exec_driver_sql(
        "CREATE TABLE sem.data_operation_definition "
        "(release_id text, operation_id text, support_contract jsonb, input_roles jsonb)"
    )
    native = (
        *completion_settlement_native_programs(metadata),
        *(item.routine for item in read_native_programs(metadata)),
        *reference_native_programs(metadata),
    )
    for name in (
        "ddo_witness_path",
        "ddo_witness_records",
        "ddo_binding_body_access",
        "ddo_assert_output_references",
    ):
        execute_native_sql(
            conn, next(program for program in native if program.name == name).render()
        )
    contract = {
        "reference_targets": [
            {
                "output_role": "result",
                "output_collection": "rows",
                "path": "/annotation",
                "input_role": "inventory",
                "input_kind": "urn:partitioned",
                "variant": "partition-item",
                "collection": "tokens",
            }
        ]
    }

    def roles(kind, kind_contract):
        return [{"name": "inventory", "kind": kind, "accepted_kind_contracts": [kind_contract]}]

    conn.execute(
        text(
            "INSERT INTO sem.data_operation_definition VALUES ('release', 'derive', :contract, :roles)"
        ).bindparams(bindparam("contract", type_=JSONB()), bindparam("roles", type_=JSONB())),
        {
            "contract": contract,
            "roles": roles("urn:partitioned", product["kind_contract"]),
        },
    )
    request = {
        "project_id": context["project_id"],
        "release_id": "release",
        "operation_id": "derive",
        "binding": {"inputs": [{"role": "inventory", "product_id": admitted}]},
    }

    def check(reference, *, original=request):
        value = reference.values() if isinstance(reference, SemanticReference) else reference
        packet = partition_packet("rows", "output", 0, 0, 5, [{"annotation": value}])
        conn.execute(
            text(
                "SELECT ops.ddo_assert_output_references("
                "jsonb_populate_record(NULL::ops.data_request,:request),:completion)"
            ).bindparams(
                bindparam("request", type_=JSONB()), bindparam("completion", type_=JSONB())
            ),
            {
                "request": original,
                "completion": {
                    "outputs": [{"role": "result", "product": {"partitions": [packet]}}]
                },
            },
        )

    ref = SemanticReference.item("inventory", "tokens", "b", (0, 2))
    check(ref)
    for bad in (
        replace(ref, item_key=(0, 3)),
        replace(ref, role="other"),
        replace(ref, collection="other"),
        {**ref.values(), "item_key": [0, 2]},
        {**ref.values(), "item_key": [{"kind": "integer", "integer": False}]},
    ):
        with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
            check(bad)
    with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
        check(ref, original={**request, "project_id": "foreign"})

    context, container = product_packet()
    existing_parent = realize(conn, context, container)
    for variant, ref, bad_ref in (
        ("product", SemanticReference.whole("inventory"), SemanticReference.whole("unknown")),
        (
            "member",
            SemanticReference.member("inventory", "one"),
            SemanticReference.member("inventory", "unknown"),
        ),
    ):
        (target,) = contract["reference_targets"]
        target = {**target, "input_kind": "urn:admitted-container-family", "variant": variant}
        target.pop("collection")
        conn.execute(
            text(
                "UPDATE sem.data_operation_definition SET support_contract=:contract, input_roles=:roles"
            ).bindparams(bindparam("contract", type_=JSONB()), bindparam("roles", type_=JSONB())),
            {
                "contract": {"reference_targets": [target]},
                "roles": roles(target["input_kind"], container["kind_contract"]),
            },
        )
        related = {
            **request,
            "binding": {
                "inputs": [
                    {"role": "inventory", "product_id": existing_parent},
                ]
            },
        }
        check(ref, original=related)
        with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
            check(bad_ref, original=related)
        with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
            conn.execute(
                text("UPDATE sem.data_operation_definition SET input_roles=:roles").bindparams(
                    bindparam("roles", type_=JSONB())
                ),
                {"roles": roles(target["input_kind"], "wrong-concrete-kind")},
            )
            check(ref, original=related)

    # An input already occupying a concrete member is checked using that
    # member's kind, independently from the containing product's kind.
    occupied = {
        **request,
        "binding": {
            "inputs": [{"role": "inventory", "product_id": existing_parent, "member_id": "one"}],
        },
    }
    ref = SemanticReference.member("inventory", "one")
    with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
        check(ref, original=occupied)
    conn.execute(
        text("UPDATE sem.data_operation_definition SET input_roles=:roles").bindparams(
            bindparam("roles", type_=JSONB())
        ),
        {"roles": roles("urn:admitted-container-family", container["members"][0]["kind_contract"])},
    )
    check(ref, original=occupied)


def test_nominal_occurrence_member_compiles_only_with_its_declared_required_input_field():
    from pydantic import BaseModel, ConfigDict, TypeAdapter

    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_version import MODEL_VERSION
    from corpus_structure.semantic.data_product_reference import SemanticOccurrenceMemberReference
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
    from corpus_structure.semantic.types import PreparationError, SourceArtifact
    from semantic.data_operation_declaration_support import contract, declarations

    class CandidateInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        observation_set_digest: str

    class FunctionReport(BaseModel):
        model_config = ConfigDict(extra="forbid")
        functions: tuple[SemanticOccurrenceMemberReference, ...]

    artifact = SourceArtifact(
        "function-reference-kinds.json",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": nominal_schema_kinds(
                    TypeAdapter(CandidateInput | FunctionReport).json_schema(),
                    namespace="urn:function-reference:",
                    root_name="FunctionKinds",
                ),
            }
        ),
    )
    value = contract()
    value["roles"][0].update(
        kind="urn:function-reference:CandidateInput", maximum=None, collection="sequence"
    )
    value["roles"][1]["kind"] = "urn:function-reference:FunctionReport"
    value["reference_targets"] = [
        {
            "output_role": "result",
            "input_role": "source",
            "path": "/functions/*",
            "variant": "member",
            "occurrence_field": "/observation_set_digest",
        }
    ]
    model = compile_data_operations(declarations=(*declarations(value), artifact))
    (target,) = model.operations[0].reference_targets
    assert target.occurrence_field == "/observation_set_digest"
    reference = SemanticReference.member("source", "actual-answer", occurrence="actual-reply-set")
    assert TypeAdapter(SemanticOccurrenceMemberReference).validate_python(
        reference.occurrence_member_value()
    ) == {
        "variant": "member",
        "role": "source",
        "occurrence": "actual-reply-set",
        "member_id": "actual-answer",
    }
    value["reference_targets"][0].pop("occurrence_field")
    with pytest.raises(PreparationError, match="requires its declared occurrence field"):
        compile_data_operations(declarations=(*declarations(value), artifact))
