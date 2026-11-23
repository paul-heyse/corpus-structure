"""Independent state, nominal variant and exact integer controls for Arrow populations."""

from decimal import Decimal
from importlib.resources import files

import pyarrow as pa
import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_population import population_layout
from corpus_structure.semantic.data_operation_values import OptionalValue
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
  Item:
    attributes:
      ordinal: {range: integer, required: true, minimum_value: 0, maximum_value: 100}
      number: {range: integer, required: true}
      label: {range: string, annotations: {"cs:nullable": true}}
      amount: {range: decimal}
      flag: {range: boolean}
      key: {range: Key, inlined: true, multivalued: true}
  Population:
    attributes:
      rows:
        range: Item
        multivalued: true
        inlined: true
        required: true
        annotations:
          'cs:collection': '{"unit":"partitioned","partition_key":"block","item_order":["ordinal"],"address":["ordinal"],"field_groups":{"value":["number"]}}'
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


def test_effective_sentence_and_hanlp_item_layouts_share_exact_reference_values():
    from corpus_structure.semantic.data_product_reference import SemanticReference
    from corpus_structure.semantic.hanlp_products import hanlp_product_inputs
    from corpus_structure.semantic.population_ipc import SealedPopulationIpc

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
            SealedPopulationIpc.write(acquired.table, schema=selected.schema, **binding) as owner,
            selected.open_ipc(owner, **binding) as received,
        ):
            assert list(received.rows()) == [row]
