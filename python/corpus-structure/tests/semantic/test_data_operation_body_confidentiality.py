"""Actual nominal mixed-universe containers retain body confidentiality at native readers."""

import json
from dataclasses import replace
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic._data_operation_wire import WireReadDemandResultRequest
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
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
                    coverage="selected-scope",
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
                subject="subject:one", original_source="source:test", analyzed_scope={"page": 1}
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
                    subject="subject:one", original_source="source:test", analyzed_scope={"page": 1}
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


def test_captured_member_contract_excludes_abstract_nominal_union():
    prepared = prepare_kernel(mixed_recipe())
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
    with reader.begin() as connection:
        frontier = DataOperationStorage(connection).read_demand_result(
            cast(
                WireReadDemandResultRequest, {"demand_id": demand["demand_id"], "view": "frontier"}
            )
        )
        assert all("body" not in product for use in frontier["uses"] for product in use["products"])
    # Full product pages and support pages must refuse before returning any body,
    # even when the support cursor skips the separately exported product rows.
    for view in ("products", "support"):
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
    with reader.begin() as connection:
        storage = DataOperationStorage(connection)
        pins = storage.read_demand_result(
            cast(WireReadDemandResultRequest, {"demand_id": demand["demand_id"]})
        )
        args = dict(
            d=demand["demand_id"],
            o="urn:body-privacy:container-consumer",
            t=json.dumps(pins["trust_snapshot"]),
            r=pins["read_id"],
            scope=json.dumps({"page": 1}),
        )
        statement = text(
            "SELECT meaning_body FROM ops.data_binding_rows(:d,:o,CAST(:t AS jsonb),:r,'subject:one','source:test',CAST(:scope AS jsonb))"
        )
        if protected:
            with pytest.raises(DBAPIError, match="evaluator"), connection.begin_nested():
                connection.execute(statement, args).all()
        else:
            assert connection.execute(statement, args).all()
        # An individually selected ordinary member remains readable even though
        # its declared parent kind could contain evaluator members.
        args["o"] = "urn:body-privacy:ordinary-consumer"
        rows = connection.execute(statement, args).all()
        assert rows
        assert all("918273" not in json.dumps(row[0]) for row in rows)
    with ddo_kernel.purpose("evaluate").begin() as connection:
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
