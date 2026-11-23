"""Independent state, nominal variant and exact integer controls for Arrow populations."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from importlib.resources import files

import pyarrow as pa
import pytest

from corpus_structure.analytics import connection
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_partitions import (
    PartitionCommitment,
    partition_commitment_header,
    partition_group_digests,
    partition_packet,
)
from corpus_structure.semantic.data_operation_population import (
    _ValueShape,
    population_layout,
)
from corpus_structure.semantic.data_operation_values import CollectionValue, OptionalValue
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.population_canonical import canonical_population
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def layout():
    content = b"""
id: urn:population
name: population
prefixes:
  p: 'urn:population:'
  xsd: 'http://www.w3.org/2001/XMLSchema#'
default_prefix: p
default_range: string
types:
  string: {base: str, uri: 'xsd:string'}
  integer: {base: int, uri: 'xsd:integer'}
  boolean: {base: bool, uri: 'xsd:boolean'}
  decimal: {base: Decimal, uri: 'xsd:decimal'}
  date: {base: date, uri: 'xsd:date'}
  datetime: {base: datetime, uri: 'xsd:dateTime'}
  float: {base: float, uri: 'xsd:double'}
classes:
  Key:
    abstract: true
    attributes:
      kind: {required: true}
  TextKey:
    is_a: Key
    attributes:
      kind: {equals_string: text}
      text: {required: true}
  IntegerKey:
    is_a: Key
    attributes:
      kind: {equals_string: integer}
      integer: {range: integer, required: true}
  Context:
    attributes:
      note: {annotations: {"cs:nullable": true}}
  Item:
    attributes:
      ordinal: {range: integer, required: true, minimum_value: 0, maximum_value: 100}
      number: {range: integer, required: true}
      label: {range: string, annotations: {"cs:nullable": true}}
      amount: {range: decimal}
      flag: {range: boolean}
      key: {range: Key, inlined: true, multivalued: true}
      context: {range: Context, inlined: true}
      day: {range: date}
      instant: {range: datetime}
      magnitude: {range: float}
  Population:
    attributes:
      rows:
        range: Item
        multivalued: true
        inlined: true
        required: true
        annotations:
          'cs:collection': '{"unit":"partitioned","partition_key":"block","item_order":["ordinal"],"address":["ordinal"],"field_groups":{"note":["context.note"],"value":["number","label","magnitude"]}}'
"""
    bundle = SourceBundle("population", (SourceArtifact("population", content),))
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    kind = next(kind for kind in model.kinds if kind.name == "Population")
    return population_layout(prepared, kind, "rows")


def test_population_preserves_exact_values_states_and_concrete_key_parts():
    selected = layout()
    huge = 10**102 + 17
    rows = [
        {
            "ordinal": 0,
            "number": huge,
            "key": [
                {"kind": "text", "text": "token"},
                {"kind": "integer", "integer": huge},
            ],
        },
        {"ordinal": 1, "number": -huge, "label": OptionalValue("known-absent")},
        {"ordinal": 2, "number": 0, "label": OptionalValue("unknown")},
        {"ordinal": 3, "number": 1, "label": OptionalValue("unavailable")},
        {
            "ordinal": 4,
            "number": 2,
            "label": OptionalValue("present", "é"),
            "amount": Decimal("0.00000000000000000000000001"),
            "flag": False,
        },
    ]
    acquired = selected.from_rows(rows)
    assert list(acquired.rows()) == rows
    assert acquired.table.schema.field("ordinal").type == pa.int64()
    assert acquired.table.column("number")[0].as_py() == {
        "narrow": None,
        "wide": str(huge),
    }
    assert acquired.table.column("number")[2].as_py() == {"narrow": 0, "wide": None}
    assert acquired.table.column("label").to_pylist() == [
        {"state": 0, "value": None},
        {"state": 3, "value": None},
        {"state": 4, "value": None},
        {"state": 5, "value": None},
        {"state": 6, "value": "é"},
    ]
    assert acquired.project(["ordinal", "number"]).column_names == ["ordinal", "number"]
    assert list(selected.acquire(acquired.table).rows()) == rows


def test_population_refuses_physical_or_declared_value_mismatches():
    selected = layout()
    with pytest.raises(ValueError, match="required field"):
        selected.from_rows([{"number": 0}])
    with pytest.raises(ValueError, match="exact integer"):
        selected.from_rows([{"ordinal": 0, "number": True}])
    with pytest.raises(ValueError, match="undeclared"):
        selected.from_rows([{"ordinal": 0, "number": 0, "extra": 1}])
    with pytest.raises(ValueError, match="one concrete nominal variant"):
        selected.from_rows([{"ordinal": 0, "number": 0, "key": [{"kind": "text", "integer": 1}]}])
    with pytest.raises(ValueError, match="maximum"):
        selected.from_rows([{"ordinal": 101, "number": 0}])
    table = selected.from_rows([{"ordinal": 0, "number": 0}]).table
    with pytest.raises(ValueError, match="release schema"):
        selected.acquire(table.replace_schema_metadata({}))
    rows = table.to_pylist()
    rows[0]["number"] = {"narrow": 0, "wide": "0"}
    with pytest.raises(ValueError, match="exactly one"):
        selected.acquire(pa.Table.from_pylist(rows, schema=selected.schema))


def test_nullable_and_missing_are_distinct():
    selected = layout()
    values = [{"ordinal": 0, "number": 0}, {"ordinal": 1, "number": 1, "label": None}]
    acquired = selected.from_rows(values)
    assert list(acquired.rows()) == values
    assert acquired.table.column("label")[0].as_py() == {"state": 0, "value": None}
    assert acquired.table.column("label")[1].as_py() == {"state": 2, "value": None}


def test_external_acquisition_detaches_mutable_buffers():
    import numpy as np

    selected = layout()
    source = selected.from_rows([{"ordinal": 0, "number": 1}]).table
    ordinal = np.array([1], dtype=np.int64)
    mutable = source.set_column(
        source.schema.get_field_index("ordinal"),
        source.schema.field("ordinal"),
        pa.array(ordinal),
    )
    admitted = selected.acquire(mutable)
    ordinal[0] = 99
    assert list(admitted.rows()) == [{"ordinal": 1, "number": 1}]
    assert all(
        not buffer.is_mutable
        for buffer in admitted.table.column("ordinal").chunk(0).buffers()
        if buffer is not None
    )


def test_engine_item_and_group_commitments_match_the_canonical_reference():
    selected = layout()
    rows = [
        {
            "ordinal": 0,
            "number": 10**102 + 17,
            "label": 'café 😀 漢字\\u000B\x0b\x0b\\\x1fé\x00\u2028"',
            "context": {"note": None},
            "amount": Decimal("0.00000000000000000000000001"),
            "magnitude": -0.0,
            "day": date(2024, 2, 29),
            "instant": datetime(2024, 2, 29, 3, 0, 0, 27, timezone(timedelta(hours=3))),
            "flag": False,
            "key": [{"kind": "text", "text": "\u03b1"}, {"kind": "integer", "integer": -(10**100)}],
        },
        {
            "ordinal": 1,
            "number": -1,
            "label": OptionalValue("present", None),
            "context": OptionalValue("present", {"note": "wrapped mapping"}),
        },
        {"ordinal": 2, "number": 0, "label": OptionalValue("unknown"), "key": []},
        {"ordinal": 3, "number": 0, "label": OptionalValue("known-absent"), "context": {}},
        {"ordinal": 4, "number": 0, "label": OptionalValue("unavailable")},
        {"ordinal": 5, "number": 0, "label": OptionalValue("present", "label")},
        {"ordinal": 6, "number": 0, "label": None},
        {"ordinal": 7, "number": 0},
    ]
    groups = {"note": ["context.note"], "value": ["number", "label", "magnitude"]}
    with connection() as engine:
        for items in (rows, list(reversed(rows)), []):
            acquired = selected.from_rows(items)
            result = canonical_population(acquired, engine=engine, batch_size=2)
            expected = partition_packet("rows", "actual", 0, 0, 3, items)
            tagged_items = expected["body"][1]
            assert isinstance(tagged_items, list)
            assert result.items.column("item_ordinal").to_pylist() == list(range(len(items)))
            assert result.items.column("canonical_text").to_pylist() == [
                canonical_bytes(value).decode() for value in tagged_items
            ]
            assert result.partition_digest == expected["partition_digest"]
            assert result.group_digests == partition_group_digests(items, groups)


def test_engine_preserves_lexical_bag_and_set_payloads_from_typed_acquisition():
    selected = layout()
    prop, _ = next(field for field in selected._shape.fields if field[0].name == "label")
    fields = tuple(
        (field, _ValueShape(pa.string(), "json") if field == prop else shape)
        for field, shape in selected._shape.fields
    )
    selected = replace(selected, _shape=replace(selected._shape, fields=fields))
    rows = [
        {"ordinal": 0, "number": 0, "label": CollectionValue("set", ("b", "a", "a"))},
        {"ordinal": 1, "number": 0, "label": CollectionValue("bag", ("b", "a", "a"))},
        {
            "ordinal": 2,
            "number": 0,
            "label": {"Z": CollectionValue("ordered-bag", (1, 0, 1)), "a": "a", "é": "é"},
        },
    ]
    with connection() as engine:
        result = canonical_population(selected.from_rows(rows), engine=engine)
    expected = partition_packet("rows", "actual", 0, 0, 3, rows)
    tagged_items = expected["body"][1]
    assert isinstance(tagged_items, list)
    assert result.items.column("canonical_text").to_pylist() == [
        canonical_bytes(value).decode() for value in tagged_items
    ]
    assert result.partition_digest == expected["partition_digest"]


def test_effective_sentence_and_hanlp_item_layouts_share_exact_reference_values():
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.declaration_products import _partition_argument
    from corpus_structure.semantic.hanlp_products import hanlp_product_inputs
    from corpus_structure.semantic.population_ipc import SealedPopulationIpc
    from corpus_structure.semantic.sentence_partitions import acquire_sentence_blocks

    core = files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes()
    bundle = hanlp_product_inputs(SourceBundle("core", (SourceArtifact("core", core),)))
    prepared = prepare_release(bundle)
    model = compile_data_operations(
        schema=bundle, definitions=prepared.definitions, vocabularies=prepared.vocabularies
    )
    reference = SemanticReference.item("inventory", "rows", "block", ("token", 0)).values()
    sentence = {"record_type": "token", "ordinal": 0, "start": 0, "end": 3, "extent": 3}
    cases = {
        "DdoSourceAnnotations": {**sentence, "lemma": "café", "morphology": ["Number=Sing"]},
        "DdoCanonicalSentences": {**sentence, "annotation": reference},
        "DdoHanlpInventory": {
            "record_type": "srl_group",
            "sentence_ordinal": 0,
            "ordinal": 0,
            "sentence": reference,
            "roles": [{"label": "ARG0", "start": 0, "end": 3, "tokens": [reference]}],
        },
    }
    with connection() as engine:
        for name, row in cases.items():
            kind = next(kind for kind in model.kinds if kind.name == name)
            selected = population_layout(prepared, kind, "rows")
            acquired = selected.from_rows([row])
            assert list(acquired.rows()) == [row]
            binding = {
                "request_digest": "request:known",
                "projection_digest": "projection:known",
                "max_bytes": 1024**2,
            }
            with (
                SealedPopulationIpc.write(
                    acquired.table, schema=selected.schema, **binding
                ) as owner,
                selected.open_ipc(owner, **binding) as received,
            ):
                assert list(received.rows()) == [row]
                result = canonical_population(received, engine=engine)
            expected = partition_packet("rows", "actual", 0, 0, 3, [row])
            assert result.partition_digest == expected["partition_digest"]
            field_groups = dict(selected._field_groups)
            assert result.group_digests == partition_group_digests([row], field_groups)
            commitment = PartitionCommitment("rows", "actual", 0, 0, 3, result.partition_digest, 1)
            header = partition_commitment_header((commitment,))
            selected_input = _partition_argument(
                {
                    "header": canonical_bytes({"rows": header}).decode(),
                    "packets": [],
                    "populations": [
                        {
                            "commitment": {
                                "collection": "rows",
                                "key": "actual",
                                "ordinal": 0,
                                "start": 0,
                                "end": 3,
                                "digest": result.partition_digest,
                                "item_count": 1,
                            },
                            "group_digests": result.group_digests,
                        }
                    ],
                },
                (acquired,),
            )
            (block,) = acquire_sentence_blocks((), header, populations=selected_input.populations)
            assert block.packet() == expected
