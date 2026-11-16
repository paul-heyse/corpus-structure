"""Snapshot consumers share strict native validation across serialization profiles."""

import copy
import json
from dataclasses import replace
from hashlib import sha256
from typing import Any

import pytest
from docling_core.types.doc import DoclingDocument, TableCell, TableData

from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot, load_snapshot, snapshot
from corpus_structure.semantic.pdf_records import NativeMappingError


def captured(value, version=None):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    schema_version = version or DoclingDocument(name="v").version
    return NativeSnapshot(payload, sha256(payload).hexdigest(), schema_version)


def table_document():
    document = DoclingDocument(name="computed serialization boundary")
    document.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="expected",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                )
            ],
        )
    )
    return document


@pytest.mark.parametrize("computed", [False, True])
def test_snapshot_accepts_verified_native_and_export_profiles(computed):
    document = table_document()
    value = document.model_dump(
        mode="json", by_alias=True, exclude_none=True, exclude_computed_fields=not computed
    )
    assert ("grid" in value["tables"][0]["data"]) is computed
    original = copy.deepcopy(value)
    retained = captured(value, document.version)
    restored = load_snapshot(retained)
    assert isinstance(restored, DoclingDocument)
    assert restored.tables[0].data.table_cells[0].text == "expected"
    assert restored.tables[0].data.grid[0][0].text == "expected"
    assert value == original and retained.payload == captured(original, document.version).payload
    if computed:
        assert snapshot(restored).payload == retained.payload


def test_snapshot_rejects_incorrect_supplied_computed_grid():
    value = table_document().export_to_dict()
    value["tables"][0]["data"]["grid"][0][0]["text"] = "invented"
    original = copy.deepcopy(value)
    with pytest.raises(ValueError, match="retained computed grid differs"):
        load_snapshot(captured(value))
    assert value == original


@pytest.mark.parametrize("mutation", ["bbox", "list", "presence"])
def test_snapshot_refuses_native_mutation(mutation):
    value: dict[str, Any] = {"name": "native mutation"}
    if mutation == "presence":
        value["unexpected_native_field"] = None
    else:
        value["body"] = {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]}
        item: dict[str, Any] = {
            "self_ref": "#/texts/0",
            "parent": {"$ref": "#/body"},
            "label": "list_item" if mutation == "list" else "text",
            "text": "item",
            "orig": "item",
        }
        value["texts"] = [item]
        if mutation == "bbox":
            value["pages"] = {"1": {"page_no": 1, "size": {"width": 100.0, "height": 100.0}}}
            item["prov"] = [
                {
                    "page_no": 1,
                    "bbox": {"l": -4.0, "t": 1.0, "r": 10.0, "b": 11.0, "coord_origin": "TOPLEFT"},
                    "charspan": [0, 4],
                }
            ]
    original = copy.deepcopy(value)
    with pytest.raises(NativeMappingError, match="native callbacks changed"):
        load_snapshot(captured(value))
    assert value == original


def test_snapshot_keeps_explicit_empty_presence_and_integrity_guards():
    value = {"name": "explicit empties", "field_regions": [], "field_items": []}
    retained = captured(value)
    restored = load_snapshot(retained)
    assert {"field_regions", "field_items"} <= restored.model_fields_set
    assert restored.field_regions == restored.field_items == []
    with pytest.raises(ValueError, match="integrity mismatch"):
        load_snapshot(replace(retained, digest="0" * 64))
    with pytest.raises(ValueError, match="schema version differs"):
        load_snapshot(replace(retained, schema_version="wrong"))


@pytest.mark.parametrize("value", [None, [], "native", 7])
def test_snapshot_refuses_non_object_json_root(value):
    with pytest.raises(ValueError, match="native document must be a JSON object"):
        load_snapshot(captured(value))


@pytest.mark.parametrize("number", ["NaN", "Infinity", "1e999"])
def test_snapshot_refuses_nonfinite_json(number):
    payload = (
        '{"name":"nonfinite","pages":{"1":{"page_no":1,"size":{"width":'
        + number
        + ',"height":2.0}}}}'
    ).encode()
    value = NativeSnapshot(payload, sha256(payload).hexdigest(), DoclingDocument(name="v").version)
    with pytest.raises(NativeMappingError, match="native JSON numbers must be finite"):
        load_snapshot(value)


def _retained_table_data():
    from docling_core.types.doc import TableCell, TableData

    native = TableData(
        num_rows=1,
        num_cols=1,
        table_cells=[
            TableCell(
                text="declared cell",
                start_row_offset_idx=0,
                end_row_offset_idx=1,
                start_col_offset_idx=0,
                end_col_offset_idx=1,
            )
        ],
    )
    return native.model_dump(mode="json", by_alias=True, exclude_none=True)


def test_retained_computed_grid_is_verified_then_projected_without_mutating_source():
    from copy import deepcopy

    from corpus_structure.ingest.pdf_hierarchy import derive_retained_native_projection

    data = _retained_table_data()
    source = {"tables": [{"data": data}], "pictures": []}
    original = deepcopy(source)
    projected, count = derive_retained_native_projection(source)
    assert count == 1
    assert source == original
    assert "grid" not in projected["tables"][0]["data"]
    assert projected["tables"][0]["data"] == {k: v for k, v in data.items() if k != "grid"}


@pytest.mark.parametrize("change", ["grid", "unknown", "coercion"])
def test_retained_grid_derivation_refuses_conflict_unknown_fields_and_native_coercion(change):
    from corpus_structure.ingest.pdf_hierarchy import derive_retained_native_projection

    data = _retained_table_data()
    if change == "grid":
        data["grid"][0][0]["text"] = "fabricated cached cell"
    elif change == "unknown":
        data["not_a_native_field"] = "unmodeled"
    else:
        data["num_rows"] = "1"
    with pytest.raises(
        ValueError, match=r"computed grid differs|undeclared TableData|changed supplied data"
    ):
        derive_retained_native_projection({"tables": [{"data": data}]})


def test_retained_projection_accepts_canonical_absent_grid_and_only_declared_chart_paths():
    from copy import deepcopy

    from corpus_structure.ingest.pdf_hierarchy import derive_retained_native_projection

    data = _retained_table_data()
    canonical = {k: v for k, v in data.items() if k != "grid"}
    source = {
        "tables": [{"data": canonical}],
        "pictures": [
            {
                "meta": {
                    "tabular_chart": {"chart_data": deepcopy(data)},
                    "opaque_payload": deepcopy(data),
                },
                "annotations": [{"kind": "tabular_chart_data", "chart_data": deepcopy(data)}],
            }
        ],
    }
    projected, count = derive_retained_native_projection(source)
    assert count == 2
    assert projected["tables"][0]["data"] == canonical
    assert "grid" not in projected["pictures"][0]["meta"]["tabular_chart"]["chart_data"]
    assert "grid" not in projected["pictures"][0]["annotations"][0]["chart_data"]
    assert projected["pictures"][0]["meta"]["opaque_payload"] == data
