"""Actual nominal mixed-universe containers retain body confidentiality at native readers."""

import json
from dataclasses import replace
from typing import cast

import pyarrow as pa
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireReadDemandResultRequest
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_partitions import (
    PartitionCommitment,
    partition_group_digests,
    partition_header,
    partition_packet,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_version import MODEL_VERSION
from corpus_structure.semantic.demand_results import read_demand_result, read_selected_answer
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.population_transfer import (
    PopulationUploadPartition,
    population_item_write_profile,
    population_upload_batches,
)
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import MANIFEST, KernelRecipe, prepare_kernel


def mixed_recipe():
    declaration = source_declaration()
    declaration["roles"][0]["kind"] = "urn:body-privacy:Container"
    consumers = []
    for name, kind in (("container", "Container"), ("ordinary", "Ordinary")):
        consumer = source_declaration()
        consumer["id"] = "urn:body-privacy:" + name + "-consumer"
        consumer["dependencies"] = [declaration["id"]]
        consumer["roles"].insert(
            0,
            dict(
                name="selected",
                kind="urn:body-privacy:" + kind,
                direction="input",
                minimum=1,
                maximum=1,
                collection="scalar",
                presence="required",
                support=dict(
                    provenance="exact",
                    source="same-original",
                    coverage={"role": "selected", "description": "selected-scope"},
                    identity_requirements=["episode"],
                ),
            ),
        )
        consumer["binding"] = {"operator": "scan", "roles": ["selected"]}
        consumers.append(consumer)
    return KernelRecipe(
        "body-confidentiality",
        """id: urn:body-privacy
name: target
prefixes: {p: 'urn:body-privacy:'}
default_prefix: p
types:
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Scope:
    attributes: {page: {range: integer, required: true}}
  Context:
    attributes:
      subject: {range: string, required: true}
      subject_definition: {range: string, required: true}
      original_source: {range: string, required: true}
      analyzed_scope: {range: Scope, required: true, inlined: true}
  Value:
    abstract: true
    attributes: {value: {range: integer, required: true}, tag: {range: string, required: true}, notes: {range: string}}
  Ordinary:
    is_a: Value
    attributes: {tag: {range: string, required: true, equals_string: ordinary}}
  Reference:
    is_a: Value
    annotations: {cs:data_universe: evaluator}
    attributes: {tag: {range: string, required: true, equals_string: reference}}
  Packet:
    attributes:
      member_id: {range: string, required: true}
      kind_contract: {range: string, required: true}
      context: {range: Context, required: true, inlined: true}
      body: {range: Value, required: true, inlined: true}
  Nested:
    is_a: Value
    attributes:
      tag: {range: string, required: true, equals_string: nested}
      members: {range: Packet, multivalued: true, inlined_as_list: true, minimum_cardinality: 0}
  Container:
    attributes:
      members: {range: Packet, multivalued: true, inlined_as_list: true, minimum_cardinality: 0}
""",
        canonical_bytes({"version": MODEL_VERSION, "operations": [declaration, *consumers]}),
        MANIFEST,
    )


def publish_mixed(kernel, *, protected, nested=False, sibling=False, mislabel=False):
    evaluator = kernel.purpose("evaluate")
    evaluated = replace(kernel, engine=evaluator)
    demand, _, _, attached = attach(
        evaluated,
        targets=("urn:body-privacy:container-consumer", "urn:body-privacy:ordinary-consumer"),
    )
    fence = claim(evaluated, attached)
    contracts = {
        name: kernel.identities["urn:body-privacy:" + name, "kind"]
        for name in ("Ordinary", "Reference", "Nested")
    }
    packets = [
        dict(
            member_id="ordinary",
            kind_contract=contracts["Ordinary"],
            context=dict(
                subject="subject:one",
                subject_definition="original-occurrence",
                original_source="source:test",
                analyzed_scope={"page": 1},
            ),
            body={"value": 7, "tag": "ordinary"},
        )
    ]
    if protected:
        packets.append(
            dict(
                member_id="reference",
                kind_contract=contracts["Reference"],
                context=dict(
                    subject="subject:one",
                    subject_definition="original-occurrence",
                    original_source="source:test",
                    analyzed_scope={"page": 1},
                ),
                body={"value": 918273, "tag": "reference"},
            )
        )
        if mislabel:
            packets[-1]["kind_contract"] = contracts["Ordinary"]
    if nested and protected:
        reference = packets.pop()
        packets.append(
            dict(
                member_id="nested",
                kind_contract=contracts["Nested"],
                context=reference["context"],
                body={"value": 0, "tag": "nested", "members": [reference]},
            )
        )

    def change(completion):
        completion["outputs"][0]["product"]["body"] = semantic_value({"members": packets})
        completion["outputs"][0]["product"]["members"] = [
            {**packet, "body": semantic_value(packet["body"])} for packet in packets
        ]
        if sibling:
            import copy

            large = copy.deepcopy(completion["outputs"][0])
            large["position"] = 1
            packet = {**packets[0], "body": {**packets[0]["body"], "notes": "x" * 200000}}
            large["product"]["body"] = semantic_value({"members": [packet]})
            large["product"]["members"] = [{**packet, "body": semantic_value(packet["body"])}]
            completion["outputs"].append(large)

    receipt = publish(evaluated, fence, retain(evaluated, fence, mutate=change))
    return demand, receipt


def test_captured_member_contract_excludes_abstract_nominal_union(tmp_path):
    prepared = prepare_kernel(mixed_recipe(), directory=tmp_path)
    for owner in ("Container", "Nested"):
        assert derive_member_kinds(prepared.model, "urn:body-privacy:" + owner) == (
            "urn:body-privacy:Nested",
            "urn:body-privacy:Ordinary",
            "urn:body-privacy:Reference",
        )


@pytest.mark.parametrize("ddo_kernel", [mixed_recipe()], indirect=True)
def test_nested_member_cannot_mislabel_protected_body_as_ordinary(ddo_kernel):
    with pytest.raises(
        DBAPIError, match="body member value differs from its captured nominal kind"
    ):
        publish_mixed(ddo_kernel, protected=True, nested=True, mislabel=True)


@pytest.mark.parametrize("ddo_kernel", [mixed_recipe()], indirect=True)
@pytest.mark.parametrize("protected,nested", [(False, False), (True, False), (True, True)])
def test_actual_member_body_closure_guards_native_reads_and_hydration(
    ddo_kernel, protected, nested
):
    demand, _receipt = publish_mixed(ddo_kernel, protected=protected, nested=nested)
    reader = ddo_kernel.purpose("read")
    evaluator = ddo_kernel.purpose("evaluate")
    selected_reader = evaluator if protected else reader
    with selected_reader.begin() as connection:
        frontier = DataOperationStorage(connection).read_demand_result(
            cast(
                WireReadDemandResultRequest, {"demand_id": demand["demand_id"], "view": "frontier"}
            )
        )
        assert all("body" not in product for use in frontier["uses"] for product in use["products"])
    # A demand read requires live authority for every universe in its captured closure.
    for view in ("frontier", "products", "support"):
        request = {"demand_id": demand["demand_id"], "view": view, "limit": 1}
        if view == "support":
            request["support_after"] = "ops.data_completion_intent:"
        if protected:
            with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
                DataOperationStorage(connection).read_demand_result(
                    cast(WireReadDemandResultRequest, request)
                )
        else:
            with reader.begin() as connection:
                value = DataOperationStorage(connection).read_demand_result(
                    cast(WireReadDemandResultRequest, request)
                )
                assert value["view"] == view
    args = dict(
        d=demand["demand_id"],
        o="urn:body-privacy:container-consumer",
        t=json.dumps(frontier["trust_snapshot"]),
        r=frontier["read_id"],
        source=json.dumps("source:test"),
        scope=json.dumps({"page": 1}),
    )
    statement = text(
        "SELECT meaning_body FROM ops.data_binding_rows(:d,:o,CAST(:t AS jsonb),:r,"
        "'subject:one',CAST(:source AS jsonb),CAST(:scope AS jsonb))"
    )
    if protected:
        with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator"):
            connection.execute(statement, args).all()
    with selected_reader.begin() as connection:
        assert connection.execute(statement, args).all()
        args["o"] = "urn:body-privacy:ordinary-consumer"
        rows = connection.execute(statement, args).all()
        assert rows
        assert all("918273" not in json.dumps(row[0]) for row in rows)
    with evaluator.begin() as connection:
        authorized = DataOperationStorage(connection).read_demand_result(
            cast(
                WireReadDemandResultRequest, {"demand_id": demand["demand_id"], "view": "products"}
            )
        )
        assert ("918273" in json.dumps(authorized)) == protected


@pytest.mark.parametrize("ddo_kernel", [mixed_recipe()], indirect=True)
def test_selected_product_scope_avoids_unreturned_large_sibling_body(ddo_kernel):
    demand, _ = publish_mixed(ddo_kernel, protected=False, sibling=True)
    reader = ddo_kernel.purpose("read")
    with reader.begin() as connection:
        frontier = DataOperationStorage(connection).read_demand_result(
            cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"]})
        )
        products = [p for use in frontier["uses"] for p in use["products"]]
        assert len(products) == 2
        selected = next(p["product_id"] for p in products if p["position"] == 0)
    with reader.begin() as connection, pytest.raises(DBAPIError, match="max_bytes"):
        DataOperationStorage(connection).read_demand_result(
            cast(
                WireReadDemandResultRequest,
                {"demand_id": demand["demand_id"], "view": "products", "max_bytes": 65536},
            )
        )
    with reader.begin() as connection:
        scoped = DataOperationStorage(connection).read_demand_result(
            cast(
                WireReadDemandResultRequest,
                {
                    "demand_id": demand["demand_id"],
                    "view": "products",
                    "scope": {"product_ids": [selected]},
                    "max_bytes": 65536,
                },
            )
        )
    returned = [p for use in scoped["uses"] for p in use["products"]]
    assert [p["product_id"] for p in returned] == [selected]
    assert len(json.dumps(scoped)) < 65536


def protected_partition_recipe():
    declaration = source_declaration()
    declaration["roles"][0]["kind"] = "urn:body-privacy:ProtectedPartition"
    return KernelRecipe(
        "protected-partition-read",
        """id: urn:body-privacy
name: target
prefixes: {p: 'urn:body-privacy:'}
default_prefix: p
types:
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
classes:
  ProtectedItem:
    attributes:
      ordinal: {range: integer, required: true}
      value: {range: integer, required: true}
  ProtectedPartition:
    annotations: {cs:data_universe: evaluator}
    attributes:
      rows:
        range: ProtectedItem
        inlined: true
        multivalued: true
        annotations:
          cs:collection: '{"unit":"partitioned","partition_key":"block","item_order":["ordinal"],"address":["ordinal"],"field_groups":{"value":["value"]}}'
""",
        canonical_bytes({"version": MODEL_VERSION, "operations": [declaration]}),
        MANIFEST,
    )


@pytest.mark.parametrize("ddo_kernel", [protected_partition_recipe()], indirect=True)
def test_native_selected_protected_partition_is_available_only_to_evaluator(ddo_kernel):
    evaluated = replace(ddo_kernel, engine=ddo_kernel.purpose("evaluate"))
    demand, _, _, attached = attach(evaluated)
    fence = claim(evaluated, attached)
    rows = [{"ordinal": 0, "value": 918273}, {"ordinal": 1, "value": 17}]
    packets = [
        partition_packet("rows", str(ordinal), ordinal, ordinal, ordinal + 1, [row])
        for ordinal, row in enumerate(rows)
    ]
    partitions = [
        PopulationUploadPartition(
            PartitionCommitment(
                "rows",
                packet["partition_key"],
                ordinal,
                ordinal,
                ordinal + 1,
                packet["partition_digest"],
                1,
            ),
            partition_group_digests([row], {"value": ["value"]}),
            pa.table(
                {
                    "item_ordinal": [0],
                    "canonical_text": [canonical_bytes(semantic_value(row)).decode()],
                }
            ),
        )
        for ordinal, (packet, row) in enumerate(zip(packets, rows, strict=True))
    ]
    profile = population_item_write_profile(release_id=ddo_kernel.prepared.release_id)
    contract = ddo_kernel.identities["urn:body-privacy:ProtectedPartition", "kind"]

    def completion(value):
        value["outputs"][0]["product"].update(
            kind_contract=contract,
            body=semantic_value({"rows": partition_header(packets)}),
            partitions=[partition.manifest() for partition in partitions],
        )

    # Staging COPY is limited to the writer purpose. The administrative fixture
    # supplies the protected upload while publication uses the actual evaluator.
    with ddo_kernel.engine.begin() as connection:
        DataOperationStorage(connection).prepare_population_upload(
            fence,
            profile,
            population_upload_batches(profile, (("result", 0, part) for part in partitions)),
            release_id=ddo_kernel.prepared.release_id,
        )
        intent = retain(evaluated, fence, mutate=completion, connection=connection)
    publish(evaluated, fence, intent)

    def read(connection, **options):
        return read_selected_answer(
            connection, "read_selected_partitions", demand["demand_id"], **options
        )

    with evaluated.engine.begin() as connection:
        page = read_demand_result(connection, demand["demand_id"], project_id="ddo-test")
        (header,) = page.members()
        address = dict(
            project_id="ddo-test",
            use_id=header["use_id"],
            product_id=header["product_id"],
            collection="rows",
        )
        pinned = dict(address, read_id=page.cut.record["read_id"])
        first = read(connection, limit=1, **pinned)
        second = read(connection, limit=1, after=first["answer_after"], **pinned)
        assert first["cut"] == second["cut"] == page.cut.record
        assert [result["rows"][0]["partition_key"] for result in (first, second)] == ["0", "1"]
        assert first["answer_after"] == [0, "0"] and second["answer_after"] is None
        exact = read(connection, partition_key="0", item_key=[0], fields=["value"], **pinned)
        (item,) = exact["rows"]
        assert item["fields"] == {"value": semantic_value(918273)}

    reader = ddo_kernel.purpose("read")
    for requested in (address, pinned):
        with reader.begin() as connection, pytest.raises(DBAPIError, match="evaluator") as caught:
            read(connection, partition_key="0", item_key=[0], fields=["value"], **requested)
        assert getattr(caught.value.orig, "sqlstate", None) == "42501"
