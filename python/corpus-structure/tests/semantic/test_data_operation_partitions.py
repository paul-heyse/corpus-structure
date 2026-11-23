"""Independent controls for declared collections and partition-local identity."""

import json
from decimal import Decimal
from hashlib import sha256

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_partitions import (
    PartitionSpanAddress,
    partition_group_digests,
    partition_header,
    partition_packet,
)
from corpus_structure.semantic.data_operation_wire import (
    interpret_wire_record,
    validate_wire_schema,
)
from corpus_structure.semantic.types import PreparationError, SourceArtifact, SourceBundle
from semantic.test_data_product_admission_programs import product_connection as product_connection


def _bundle(path="start"):
    content = """
id: urn:sbx
name: sbx
prefixes:
  sbx: 'urn:sbx:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: sbx
default_range: string
types:
  string: {base: str, uri: 'xsd:string'}
  integer: {base: int, uri: 'xsd:integer'}
classes:
  Item:
    attributes:
      start: {range: integer, required: true}
      end: {range: integer, required: true}
  BaseCollection:
    attributes:
      tokens:
        range: Item
        multivalued: true
        inlined: true
        required: true
        annotations:
          'cs:collection': '{"unit":"partitioned","partition_key":"block_id","item_order":["start","end"],"address":["start","end"],"field_groups":{"geometry":["PATH","end"]}}'
  Collection:
    is_a: BaseCollection
""".replace('"PATH"', json.dumps(path))
    return SourceBundle("sbx", (SourceArtifact("sbx", content.encode()),))


def test_inherited_collection_compiles_to_effective_kind():
    compiled = compile_data_operations(_bundle())
    child = next(kind for kind in compiled.kinds if kind.name == "Collection")
    assert json.loads(child.facts)["collections"] == {
        "tokens": {
            "unit": "partitioned",
            "partition_key": "block_id",
            "item_order": ["start", "end"],
            "address": ["start", "end"],
            "field_groups": {"geometry": ["end", "start"]},
        }
    }


def test_unknown_collection_field_refuses_during_compilation():
    with pytest.raises(PreparationError, match="unresolved collection field path unknown"):
        compile_data_operations(_bundle("unknown"))


def test_admitted_kind_derives_header_and_item_schemas_from_the_same_slot():
    from corpus_structure.semantic.data_operation_storage import (
        _kind_schema,
        _meaning_schema,
        _partition_contracts,
    )
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.prepare import prepare_release

    bundle = _bundle()
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    kind = next(kind for kind in model.kinds if kind.name == "Collection")
    schema, collection = _partition_contracts(
        prepared, model, kind, _kind_schema(prepared, kind), json.loads(kind.facts)["collections"]
    )
    packet = partition_packet("tokens", "block", 0, 20, 24, [{"start": 0, "end": 4}])
    product = {"tokens": partition_header([packet])}
    assert validate_wire_schema(schema, product) == product
    tagged_header = semantic_value(product)
    meaning_schema = _meaning_schema(prepared, kind, model, partition_headers=collection["schemas"])
    assert validate_wire_schema(meaning_schema, tagged_header) == tagged_header
    items = packet["body"][1]
    assert isinstance(items, list)
    item = items[0]
    assert validate_wire_schema(collection["schemas"]["tokens"]["meaning_schema"], item) == item
    with pytest.raises(ValueError):
        validate_wire_schema(schema, {"tokens": [{"start": 0, "end": 4}]})


def test_typed_content_group_and_placement_have_independent_identity():
    rows = [{"name": "é", "real": 1.5, "decimal": Decimal("0.75"), "optional": None}]
    packet = partition_packet("tokens", "é", 0, 10, 20, rows)
    tagged = b'["sequence",[["mapping",[["decimal",["decimal","0.75"]],["name",["string","\xc3\xa9"]],["optional",["null"]],["real",["float","0x1.8000000000000p+0"]]]]]]'
    encoded = b'["ddo","partition","1",' + tagged + b"]"
    assert packet["partition_digest"] == "partition:" + sha256(encoded).hexdigest()

    from corpus_structure.semantic.data_operation_wire import wire_record_schema

    schema = wire_record_schema("product_partition")
    assert validate_wire_schema(schema, packet) == packet
    assert interpret_wire_record("product_partition", packet) == packet
    moved = partition_packet("tokens", "é", 0, 60, 70, rows)
    assert partition_header([packet])["root"] == partition_header([moved])["root"]
    assert (
        partition_header([packet])["placement_root"] != partition_header([moved])["placement_root"]
    )
    absent = [{key: value for key, value in rows[0].items() if key != "optional"}]
    groups = {"lexical": ["name"], "nullable": ["optional"]}
    before = partition_group_digests(rows, groups)
    after = partition_group_digests(absent, groups)
    assert before["lexical"] == after["lexical"]
    assert before["nullable"] != after["nullable"]
    assert PartitionSpanAddress("tokens", "é", 2, 4).absolute(60) == (62, 64)


def test_compiled_collection_admits_header_and_checks_native_item_schema(product_connection):
    from sqlalchemy import insert, text
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.data_operation_storage import (
        _kind_schema,
        _meaning_schema,
        _partition_contracts,
    )
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.prepare import prepare_release
    from semantic.test_data_product_admission_programs import product_packet, realize

    bundle = _bundle()
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    kind = next(kind for kind in model.kinds if kind.name == "Collection")
    schema, specification = _partition_contracts(
        prepared, model, kind, _kind_schema(prepared, kind), json.loads(kind.facts)["collections"]
    )
    meaning = _meaning_schema(prepared, kind, model, partition_headers=specification["schemas"])
    metadata = get_metadata()
    product_connection.execute(
        insert(metadata.tables["sem.data_kind_contract"]).values(
            kind_contract="compiled-collection",
            kind=kind.semantic_id,
            body_schema=schema,
            meaning_schema=meaning,
            member_schema={"not": {}},
            member_contracts=[],
            universe="ordinary",
            collections=specification,
        )
    )
    product_connection.execute(
        insert(metadata.tables["sem.data_kind_release"]).values(
            release_id="release",
            kind_contract="compiled-collection",
        )
    )
    context, _ = product_packet()

    def completion(items):
        packets = [
            partition_packet("tokens", name, ordinal, 10 * ordinal, 10 * ordinal + 4, rows)
            for ordinal, (name, rows) in enumerate(zip(("b", "a", "é"), items, strict=True))
        ]
        return {
            "kind_contract": "compiled-collection",
            "body": semantic_value({"tokens": partition_header(packets)}),
            "members": [],
            "partitions": packets,
        }

    originals = [[{"start": 0, "end": 4}]] * 3
    key = realize(product_connection, context, completion(originals))
    with (
        pytest.raises(DBAPIError, match="population item is not canonical or violates"),
        product_connection.begin_nested(),
    ):
        realize(
            product_connection, context, completion([originals[0], [{"start": 1}], originals[2]])
        )
    assert (
        product_connection.scalar(
            text("SELECT count(*) FROM kb.data_product_population WHERE product_id=:key"),
            {"key": key},
        )
        == 3
    )
