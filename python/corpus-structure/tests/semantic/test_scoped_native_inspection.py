"""Selected native inspection preserves custody without preparing a partial source view."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import Text, column, select, table

from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_storage import NativeDocumentUnavailable
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.native_source import NativeSourceRequest, _cell_companion


@pytest.fixture
def source():
    return ProductReference(3, "integrated", "a" * 64), ("#/texts/0", "#/texts/1", "#/body")


def cell_reader(native_type="table", **changes):
    pointer = "#/tables/0" if native_type == "table" else "#/pictures/0"
    suffix = (
        "/data/table_cells/3"
        if native_type == "table"
        else "/meta/tabular_chart/chart_data/table_cells/3"
    )
    address = pointer + suffix
    cell = dict(kind="cell", pointer=pointer, cell_index=3, occurrence_id=address)
    parent = dict(
        kind="item" if native_type == "table" else "chart", pointer=pointer, occurrence_id=pointer
    )
    cell.update(changes)
    rows = {address: dict(body=cell), pointer: dict(body=parent)}
    reader = SimpleNamespace(
        product_kind=lambda: "integrated",
        _one=Mock(side_effect=lambda family, selector: rows[selector["local_id"]]),
        decode_companion_row=lambda row: row["body"],
        occurrence_context=Mock(return_value="complete owned custody"),
    )
    request = NativeSourceRequest(
        project_id="project:test",
        demand_id="demand:test",
        read_id="read:test",
        use_id="use:test",
        product_id="product:test",
        derivation_id="derivation:test",
        view="cell",
        pointer=pointer,
        cell_index=3,
    )
    return reader, request, rows


@pytest.mark.parametrize("native_type", ["table", "chart"])
def test_cell_companion_selects_exact_cell_and_parent_before_custody_composition(native_type):
    reader, request, rows = cell_reader(native_type)
    assert _cell_companion(reader, request, row_budget=12) == "complete owned custody"
    selected, section = reader.occurrence_context.call_args.args
    assert {row["body"]["occurrence_id"] for row in selected} == set(rows)
    assert section == "#/body"
    assert reader.occurrence_context.call_args.kwargs == {"row_budget": 12}


def test_chart_cell_requires_chart_parent_not_table_item():
    reader, request, rows = cell_reader("chart")
    rows["#/pictures/0"]["body"]["kind"] = "item"
    with pytest.raises(NativeDocumentUnavailable, match="differs from native selector"):
        _cell_companion(reader, request, row_budget=12)
    reader.occurrence_context.assert_not_called()


def inventory_reader(monkeypatch, source, rows):
    reference = source[0]
    reader = object.__new__(PublishedPdfReader)
    reader.reference = reference
    reader.revision = dict(
        task_id=3,
        product_key="integrated",
        logical_digest="a" * 64,
        build_id="build",
        release_id="producer-release",
    )
    reader._projection_scope = Mock(return_value=nullcontext({}))
    access = table(
        "native_access",
        *(
            column(name, Text())
            for name in ("product_id", "revision_id", "pointer", "native_json", "text")
        ),
    )
    monkeypatch.setattr(
        "corpus_structure.semantic._pdf_native_calls.prepare_read_published_items",
        lambda **kwargs: select(access),
    )
    raw = Mock(return_value=rows)
    admit = Mock(side_effect=lambda value: value)
    reader._raw_rows = raw
    reader._admit_value = admit
    return reader, raw, admit


@pytest.mark.parametrize("defect", [None, "missing", "duplicate", "placement"])
def test_complete_native_inventory_uses_only_bounded_scalar_address_rows(
    monkeypatch, source, defect
):
    pointers = source[1]
    rows = [("build", "build", pointer) for pointer in pointers]
    if defect == "missing":
        rows.pop()
    elif defect == "duplicate":
        rows[-1] = rows[0]
    elif defect == "placement":
        rows[-1] = ("other", "other", pointers[-1])
    reader, raw, admit = inventory_reader(monkeypatch, source, rows)
    if defect is None:
        reader.require_native_item_inventory(pointers)
    else:
        with pytest.raises(ValueError, match="inventory"):
            reader.require_native_item_inventory(pointers)
    statement = raw.call_args.args[0]
    assert list(statement.selected_columns.keys()) == ["product_id", "revision_id", "pointer"]
    assert admit.call_count == len(rows)


@pytest.mark.parametrize(
    "changes",
    [
        dict(kind="item"),
        dict(pointer="#/tables/1"),
        dict(cell_index=2),
        dict(occurrence_id="foreign"),
    ],
)
def test_cell_companion_refuses_mismatched_cell_selector(changes):
    reader, request, _ = cell_reader(**changes)
    with pytest.raises(NativeDocumentUnavailable, match="differs from native selector"):
        _cell_companion(reader, request, row_budget=12)
    reader.occurrence_context.assert_not_called()


@pytest.mark.parametrize(
    "changes", [dict(kind="cell"), dict(pointer="#/tables/9"), dict(occurrence_id="foreign")]
)
def test_cell_companion_refuses_mismatched_parent_selector(changes):
    reader, request, rows = cell_reader()
    rows["#/tables/0"]["body"].update(changes)
    with pytest.raises(NativeDocumentUnavailable, match="differs from native selector"):
        _cell_companion(reader, request, row_budget=12)
    reader.occurrence_context.assert_not_called()


def test_native_product_cell_does_not_invent_integrated_companion():
    reader, request, _ = cell_reader()
    reader.product_kind = lambda: "native"
    assert _cell_companion(reader, request, row_budget=12) is None
    reader._one.assert_not_called()
