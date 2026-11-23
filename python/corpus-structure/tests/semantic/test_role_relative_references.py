"""Declared reference controls at the Python and generated native boundaries."""

import json
from dataclasses import replace
from typing import cast

import pytest
from sqlalchemy import bindparam, insert, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireOutputMember
from corpus_structure.semantic.data_completion_settlement_native import (
    completion_settlement_native_programs,
)
from corpus_structure.semantic.data_operation_partitions import partition_packet
from corpus_structure.semantic.data_operation_read_native import read_native_programs
from corpus_structure.semantic.data_operation_reference_native import reference_native_programs
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_product_reference import (
    SemanticReference,
    read_semantic_reference,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.reference_resolution import (
    AcquiredReferencePartition,
    CapturedPartitionItems,
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
        items = CapturedPartitionItems()

        def authorize(self, binding):
            if binding not in (admitted, sibling) or not self.allowed:
                raise PermissionError("target denied")

        def product(self, product_id: str) -> object:
            raise AssertionError("unexpected product read")

        def member(self, product_id: str, member_id: str) -> object:
            raise AssertionError("unexpected member read")

        def item(self, product_id, collection, partition_key, item_key):
            return self.items.item(
                (product_id, collection, partition_key), item_key, self.partition
            )

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
    from corpus_structure.semantic.binding_support_native import binding_support_native_programs

    conn = product_connection
    metadata = get_metadata()
    context, product, _, _ = partition_fixture(conn)
    admitted = realize(conn, context, product)
    conn.exec_driver_sql(
        "CREATE TABLE sem.data_operation_definition "
        "(release_id text, operation_id text, support_contract jsonb, input_roles jsonb)"
    )
    native = (
        *(item.routine for item in binding_support_native_programs(metadata)),
        *completion_settlement_native_programs(metadata),
        *(item.routine for item in read_native_programs(metadata)),
        *reference_native_programs(metadata),
    )
    for name in (
        "ddo_witness_path",
        "ddo_witness_records",
        "ddo_binding_body_access",
        "ddo_derivation_input_positions",
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

    def check(*references, original=request):
        from uuid import uuid4

        from corpus_structure.semantic.data_operation_json import json_bytes

        output_intent = "reference:" + uuid4().hex
        owner = dict(
            intent_id=output_intent,
            output_role="result",
            output_position=0,
            collection="rows",
            partition_key="output",
        )
        conn.execute(
            insert(metadata.tables["ops.data_retained_population"]).values(
                **owner,
                product_id="pending-reference-output",
                ordinal=0,
                partition_digest="fixture-partition",
                item_count=len(references),
                group_digests={},
                placement={"start": 0, "end": 5},
            )
        )
        conn.execute(
            insert(metadata.tables["ops.data_retained_population_item"]),
            [
                {
                    **owner,
                    "item_ordinal": position,
                    "address_key": str(position),
                    "canonical_text": json_bytes(semantic_value({
                        "annotation": ref.values() if isinstance(ref, SemanticReference) else ref
                    })).decode(),
                    "declared_projection": {},
                }
                for position, ref in enumerate(references)
            ],
        )
        conn.execute(
            text(
                "SELECT ops.ddo_assert_output_references("
                "jsonb_populate_record(NULL::ops.data_request,:request),:completion,:intent)"
            ).bindparams(
                bindparam("request", type_=JSONB()), bindparam("completion", type_=JSONB())
            ),
            {
                "request": original,
                "completion": {"outputs": [{"role": "result", "position": 0, "product": {}}]},
                "intent": output_intent,
            },
        )

    ref = SemanticReference.item("inventory", "tokens", "b", (0, 2))
    check(ref)
    # Independent selected addresses may recur in non-consecutive output rows.
    other = SemanticReference.item("inventory", "tokens", "a", (0, 1))
    check(ref, other, ref)
    with (
        pytest.raises(DBAPIError, match='"integer": 777'),
        conn.begin_nested(),
    ):
        check(ref, other, replace(ref, item_key=(0, 777)), replace(other, item_key=(0, 999)))

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

    # Scoped reports can carry an overlapping member and a member unique to one report.
    context, sibling_packet = product_packet(("one", "two"))
    sibling_parent = realize(conn, context, sibling_packet)
    target = {
        "output_role": "result",
        "output_collection": "rows",
        "path": "/annotation",
        "input_role": "inventory",
        "input_kind": "urn:admitted-container-family",
        "variant": "member",
        "occurrence_binding": True,
    }
    admitted_roles = roles(target["input_kind"], container["kind_contract"])
    conn.execute(
        text(
            "UPDATE sem.data_operation_definition SET support_contract=:contract, input_roles=:roles"
        ).bindparams(bindparam("contract", type_=JSONB()), bindparam("roles", type_=JSONB())),
        {"contract": {"reference_targets": [target]}, "roles": admitted_roles},
    )
    inputs = [
        dict(
            role="inventory", product_id=existing_parent, occurrence_label="first", multiplicity=1
        ),
        dict(
            role="inventory", product_id=sibling_parent, occurrence_label="second", multiplicity=1
        ),
    ]
    labelled = {**request, "binding": {"inputs": inputs}}
    first = SemanticReference.member("inventory", "one", occurrence="first")
    second = SemanticReference.member("inventory", "two", occurrence="second")
    wrong = replace(second, occurrence="first")
    check(first, original=labelled)
    check(second, original=labelled)
    with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
        check(wrong, original=labelled)
    ambiguous = {
        **labelled,
        "binding": {"inputs": [inputs[0], {**inputs[1], "occurrence_label": "first"}]},
    }
    with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
        check(first, original=ambiguous)

    from corpus_structure.semantic.detached_reference_resolution import (
        require_detached_output_references,
    )

    def row_map(relation, *columns):
        if relation not in metadata.tables:
            return {}
        return {
            (
                row[columns[0]] if len(columns) == 1 else tuple(row[column] for column in columns)
            ): row
            for row in conn.execute(select(metadata.tables[relation])).mappings()
        }

    def replay(reference, captured=inputs):
        require_detached_output_references(
            row_map=row_map,
            rows_for=lambda *_args, **_keys: captured,
            derivation_id="captured-artifact",
            project_id=context["project_id"],
            targets=[target],
            input_roles=admitted_roles,
            outputs=[
                cast(
                    WireOutputMember,
                    {
                        "role": "result",
                        "position": 0,
                        "multiplicity": 1,
                        "product": {
                            **container,
                            "partitions": [
                                partition_packet(
                                    "rows", "output", 0, 0, 5, [{"annotation": reference.values()}]
                                )
                            ],
                        },
                    },
                )
            ],
        )

    replay(first)
    replay(second)
    with pytest.raises(ValueError, match="does not resolve"):
        replay(wrong)
    with pytest.raises(ValueError, match="exactly one producing input occurrence"):
        replay(first, ambiguous["binding"]["inputs"])

    target = {key: value for key, value in target.items() if key != "occurrence_binding"}
    target.update(occurrence_position=True)
    admitted_roles = [{**admitted_roles[0], "collection": "set"}]
    conn.execute(
        text(
            "UPDATE sem.data_operation_definition SET support_contract=:contract, input_roles=:roles"
        ).bindparams(bindparam("contract", type_=JSONB()), bindparam("roles", type_=JSONB())),
        {"contract": {"reference_targets": [target]}, "roles": admitted_roles},
    )
    persisted = dict.fromkeys((existing_parent, sibling_parent))
    expected = {product: position for position, product in enumerate(sorted(persisted))}
    pins = [
        dict(role="inventory", product_id=product, position=0, multiplicity=1)
        for product in (sibling_parent, existing_parent)
    ]
    captured = [
        {**pin, "position": expected[pin["product_id"]], "derivation_id": "captured-artifact"}
        for pin in pins
    ]
    left = SemanticReference.member("inventory", "one", occurrence=str(expected[existing_parent]))
    right = SemanticReference.member("inventory", "one", occurrence=str(expected[sibling_parent]))
    only_sibling = replace(right, member_id="two")
    wrong_parent = replace(left, member_id="two")
    for ordered in (pins, pins[::-1]):
        frozen = {**request, "binding": {"inputs": ordered}}
        check(left, right, only_sibling, original=frozen)
        with pytest.raises(DBAPIError, match="does not resolve address"), conn.begin_nested():
            check(wrong_parent, original=frozen)
    replay(left, captured)
    replay(right, captured[::-1])
    with pytest.raises(ValueError, match="does not resolve"):
        replay(wrong_parent, captured)

    from types import SimpleNamespace

    from corpus_structure.semantic.live_reference_resolution import (
        require_selected_output_reference,
    )

    header_target = {key: value for key, value in target.items() if key != "output_collection"}
    current: dict[str, object] = dict(
        id="current", fate="fulfilled", derivation_id="captured-artifact"
    )
    output = dict(role="result")
    selected = SimpleNamespace(
        use_id="current", derivation_id="captured-artifact", operation_id="derive", output=output
    )
    records = {
        "ops.data_derivation": {"captured-artifact": {"release_id": "release"}},
        "ops.demand_use": {"current": current},
        "sem.data_operation_definition": {
            ("release", "derive"): dict(
                input_roles=admitted_roles, support_contract={"reference_targets": [header_target]}
            )
        },
    }
    index = SimpleNamespace(
        mapping=lambda relation, columns: (
            records[relation] if relation in records else row_map(relation, *columns)
        ),
        rows_for=lambda _relation, **_keys: captured,
    )
    scope = SimpleNamespace(
        index=index, cut=SimpleNamespace(record={"project_id": context["project_id"]})
    )
    unrelated = {**pins[0], "product_id": admitted}
    for input_order in (pins, pins[::-1], [unrelated, *pins]):
        current["selection"] = {"inputs": input_order}
        for reference, parent in ((left, existing_parent), (right, sibling_parent)):
            binding, _ = require_selected_output_reference(
                scope, selected, reference, path="/annotation", with_binding=True
            )
            assert binding.product_id == parent
    current["selection"] = {"inputs": [unrelated, pins[0]]}
    with pytest.raises(ValueError, match="exactly one producing input occurrence"):
        require_selected_output_reference(scope, selected, left, path="/annotation")


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
    value["reference_targets"] = [{**value["reference_targets"][0], "occurrence_binding": True}]
    with pytest.raises(PreparationError, match="requires a frozen source-set input"):
        compile_data_operations(declarations=(*declarations(value), artifact))
    value["roles"][0]["support"].update(source="frozen-source-set", source_set="frozen-candidates")
    value["roles"][0]["subject_target"] = "source-set"
    model = compile_data_operations(declarations=(*declarations(value), artifact))
    assert model.operations[0].reference_targets[0].occurrence_binding is True
