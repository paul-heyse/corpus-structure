"""Selected native inspection preserves custody without preparing a partial source view."""

from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import Text, column, select, table

from corpus_structure.core.method import SourceViewDraft, SourceViewRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_analysis import (
    NativeAnalysisUnavailable,
    _resolve_native_analysis,
    stored_native_analysis,
)
from corpus_structure.semantic.operations import BoundReader, OperationConflict
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.pdf_storage import NativeDocumentUnavailable
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import source_formula_metadata
from corpus_structure.serve.native_source import NativeSourceRequest, _cell_companion

POINTER = "#/texts/0"


@pytest.fixture
def source():
    draft = SourceViewDraft(
        key="retained-formulas",
        document_id=2,
        native_product=ProductReference(3, "integrated", "a" * 64),
        section_pointer="#/body",
        membership="descendants",
        text="x",
        pieces=({"kind": "native_text", "item_ref": POINTER, "start": 0, "end": 1},),
        items=(POINTER, "#/texts/1"),
        ancestors=("#/body",),
        health={
            "formula_outcomes": [
                {"pointer": POINTER, "outcome": "unknown"},
                {"pointer": "#/texts/1", "outcome": "succeeded"},
            ]
        },
        recipe_bytes=b'{"recipe":"retained-independent-scope"}',
    )
    reference = SourceViewRef(
        7,
        draft.key,
        draft.document_id,
        draft.native_product,
        draft.section_pointer,
        draft.membership,
        draft.projection_digest,
        draft.recipe_digest,
    )
    return draft, reference


def metadata_reader(monkeypatch, source, *, change=None):
    draft, reference = source
    row = dict(
        release_id="archived-release",
        native_build_id="build",
        native_revision_id="build",
        projection=deepcopy(draft.projection()),
        recipe=draft.recipe_bytes,
    )
    if change == "projection-bytes":
        row["projection"]["health"]["formula_outcomes"][0]["outcome"] = "succeeded"
    elif change == "recipe-bytes":
        row["recipe"] += b" "
    elif change == "matching-projection-column":
        reference = replace(reference, projection_digest="c" * 64)
    elif change == "matching-recipe-column":
        reference = replace(reference, recipe_digest="c" * 64)
    elif change == "placement":
        row["native_revision_id"] = "other-build"
    elif change == "missing-recipe":
        row["recipe"] = None
    conn = Mock()
    conn.execute.return_value.mappings.return_value.one_or_none.return_value = row
    native = Mock()
    native.revision = dict(
        task_id=3,
        product_key="integrated",
        logical_digest="a" * 64,
        build_id="build",
        release_id="producer-release",
    )
    native.selected_native_items.return_value = {
        POINTER: {"label": "text" if change == "kind" else "formula"}
    }
    factory = Mock(return_value=native)
    monkeypatch.setattr(
        "corpus_structure.semantic.pdf_record_reader.published_record_reader", factory
    )
    monkeypatch.setattr("corpus_structure.semantic.releases.open_release", lambda *args: "archived")
    return reference, conn, native, factory


def test_formula_metadata_hashes_retained_projection_recipe_and_reads_only_selected_node(
    monkeypatch, source
):
    reference, conn, native, factory = metadata_reader(monkeypatch, source)
    budget = Mock()
    assert source_formula_metadata(conn, reference, POINTER, read_budget=budget) == {
        POINTER: "unknown"
    }
    native.selected_native_items.assert_called_once_with((POINTER,))
    native.require_native_item_inventory.assert_called_once_with(
        (*source[0].items, *source[0].ancestors)
    )
    factory.assert_called_once_with(
        conn, reference.native_product, projection_context="archived", read_budget=budget
    )
    budget.preflight.assert_called_once()
    assert budget.value.call_args.args[0]["projection"] == source[0].projection()
    budget.reserve.assert_called_once_with(len(source[0].recipe_bytes))
    statement = conn.execute.call_args.args[0]
    assert "projection" in statement.selected_columns and "recipe" in statement.selected_columns


@pytest.mark.parametrize(
    "change,match",
    [
        ("projection-bytes", "projection.*digest"),
        ("recipe-bytes", "recipe.*digest"),
        ("matching-projection-column", "projection.*digest"),
        ("matching-recipe-column", "recipe.*digest"),
        ("placement", "placement"),
        ("missing-recipe", "recipe is unavailable"),
        ("kind", "native formula"),
    ],
)
def test_formula_metadata_refuses_corrupt_matching_columns_and_native_binding(
    monkeypatch, source, change, match
):
    reference, conn, _, _ = metadata_reader(monkeypatch, source, change=change)
    with pytest.raises(ValueError, match=match):
        source_formula_metadata(conn, reference, POINTER)


def test_formula_metadata_refuses_missing_projection_membership(monkeypatch, source):
    reference, conn, _, _ = metadata_reader(monkeypatch, source)
    conn.execute.return_value.mappings.return_value.one_or_none.return_value = None
    with pytest.raises(ValueError, match="outside the pinned"):
        source_formula_metadata(conn, reference, "#/texts/99")


def test_formula_metadata_reuses_projection_validator_even_with_matching_corrupt_hash(
    monkeypatch, source
):
    reference, conn, _, _ = metadata_reader(monkeypatch, source)
    row = conn.execute.return_value.mappings.return_value.one_or_none.return_value
    row["projection"]["pieces"][0]["end"] = 2
    reference = replace(
        reference, projection_digest=sha256(canonical_bytes(row["projection"])).hexdigest()
    )
    with pytest.raises(ValueError, match="exceeds projected text"):
        source_formula_metadata(conn, reference, POINTER)


def test_compact_observation_port_rechecks_selected_reference_without_hydration(source):
    reference = source[1]
    reader = BoundReader(Mock(), 11, Mock())
    reader.source_view_ref = Mock(return_value=reference)
    reader.source_view = Mock(side_effect=AssertionError("must not hydrate a partial view"))
    reader._observations = Mock(return_value=["owned observation"])
    assert reader.source_observations_for_ref(reference, "extract.math", "record") == [
        "owned observation"
    ]
    with pytest.raises(OperationConflict, match="differs from bound run"):
        reader.source_observations_for_ref(
            replace(reference, recipe_digest="b" * 64), "extract.math", "record"
        )
    reader._observations.assert_called_once_with(reference.id, "extract.math", "record")


def test_compact_reference_rejects_superseded_or_other_run_selection(monkeypatch, source):
    from corpus_structure.semantic import source_views

    budget = Mock()
    reader = BoundReader(Mock(), 11, Mock(), read_budget=budget)
    selected = Mock(return_value=())
    monkeypatch.setattr(source_views, "selected_source_views", selected)
    with pytest.raises(OperationConflict, match="outside bound run"):
        reader.source_view_ref(source[1].id)
    assert selected.call_args.kwargs == dict(read_budget=budget, source_view_id=source[1].id)


def observation(reference, key, **updates):
    payload = dict(
        source_view_id=reference.id,
        native_product=reference.native_product.values(),
        projection_digest=reference.projection_digest,
        recipe_digest=reference.recipe_digest,
        demand="occurrences",
        items=[dict(pointer=POINTER, meaning="retained meaning")],
    )
    payload.update(updates)
    return SimpleNamespace(payload=payload, observation_key=key, task_id=23, payload_hash="d" * 64)


def test_occurrence_analysis_preserves_unknown_health_without_source_view(source):
    reference = source[1]
    reader = SimpleNamespace(
        source_formula_metadata=Mock(return_value=(reference, {POINTER: "unknown"})),
        source_observations_for_ref=Mock(return_value=[]),
        source_view=Mock(side_effect=AssertionError("whole source view is not needed")),
    )
    answer = stored_native_analysis(reader, reference.id, POINTER)[POINTER]
    assert answer["recognition_health"] == "unknown"
    assert answer["availability"] == "unavailable"
    assert answer["observations"] == [] and answer["interpretation"] is None
    assert answer["native_product"] == reference.native_product.values()


def test_bulk_analysis_keeps_existing_complete_source_view_port(source):
    reference = source[1]
    view = SimpleNamespace(
        ref=reference,
        items=[dict(self_ref=POINTER, label="formula")],
        health={"formula_outcomes": [dict(pointer=POINTER, outcome="unknown")]},
    )
    reader = SimpleNamespace(
        source_view=Mock(return_value=view),
        source_observations=Mock(return_value=[]),
        source_formula_metadata=Mock(side_effect=AssertionError("bulk must retain full view")),
    )
    answer = stored_native_analysis(reader, reference.id)
    reader.source_view.assert_called_once_with(reference.id)
    assert set(answer) == {POINTER}
    assert answer[POINTER]["recognition_health"] == "unknown"


def test_recorded_formula_resolution_retains_meaning_and_named_observation(source):
    reference = source[1]
    row = observation(reference, "weak")
    answer = _resolve_native_analysis(
        reference,
        [POINTER],
        {POINTER: "succeeded"},
        {"extract.math": [row], "normalize.formula": []},
    )[POINTER]
    assert answer["availability"] == "available"
    assert answer["interpretation"] == {"pointer": POINTER, "meaning": "retained meaning"}
    assert answer["normalization"] is None
    assert answer["observations"] == [
        dict(observation_key="weak", task_id=23, payload_hash="d" * 64, method="extract.math")
    ]
    absent = _resolve_native_analysis(
        reference, [POINTER], {POINTER: "succeeded"}, {"extract.math": [], "normalize.formula": []}
    )[POINTER]
    assert absent["availability"] == "not_requested"


@pytest.mark.parametrize(
    "defect",
    [
        "view",
        "product",
        "projection",
        "recipe",
        "abi",
        "duplicate",
        "competing",
        "cycle",
        "missing",
        "ambiguous-item",
        "foreign-pointer",
        "missing-weak",
    ],
)
def test_recorded_resolution_keeps_binding_ambiguity_and_reference_refusals(source, defect):
    reference = source[1]
    row = observation(reference, "weak")
    by_method = {"extract.math": [row], "normalize.formula": []}
    if defect in {"view", "product", "projection", "recipe", "abi"}:
        field = {
            "view": "source_view_id",
            "product": "native_product",
            "projection": "projection_digest",
            "recipe": "recipe_digest",
            "abi": "demand",
        }[defect]
        row.payload[field] = "different"
    elif defect == "duplicate":
        by_method["normalize.formula"] = [observation(reference, "weak")]
    elif defect == "competing":
        by_method["extract.math"].append(observation(reference, "other"))
    elif defect in {"cycle", "missing"}:
        row.payload["source_record"] = "weak" if defect == "cycle" else "outside-cut"
    elif defect == "ambiguous-item":
        row.payload["items"] *= 2
    elif defect == "foreign-pointer":
        row.payload["items"][0]["interpretation_ref"] = dict(
            pointer="#/texts/99", observation_key="weak"
        )
    else:
        row.payload["demand"] = "symbolic"
    with pytest.raises(NativeAnalysisUnavailable):
        _resolve_native_analysis(reference, [POINTER], {POINTER: "succeeded"}, by_method)


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
        run_id=14,
        task_id=1,
        product_key="integrated",
        content_digest="a" * 64,
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
    reference = source[1]
    reader = object.__new__(PublishedPdfReader)
    reader.reference = reference.native_product
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
        "corpus_structure.semantic._operation_calls.prepare_read_published_items",
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
    pointers = (*source[0].items, *source[0].ancestors)
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


@pytest.mark.parametrize("field", ["items", "ancestors"])
def test_formula_refuses_extra_missing_inventory_with_recomputed_matching_digest(
    monkeypatch, source, field
):
    reference, conn, native, _ = metadata_reader(monkeypatch, source)
    row = conn.execute.return_value.mappings.return_value.one_or_none.return_value
    row["projection"][field].append("#/groups/nonexistent")
    reference = replace(
        reference, projection_digest=sha256(canonical_bytes(row["projection"])).hexdigest()
    )
    existing = [("build", "build", pointer) for pointer in (*source[0].items, *source[0].ancestors)]
    inventory, _, _ = inventory_reader(monkeypatch, source, existing)
    native.require_native_item_inventory = inventory.require_native_item_inventory
    with pytest.raises(ValueError, match="inventory is absent"):
        source_formula_metadata(conn, reference, POINTER)
    native.selected_native_items.assert_not_called()


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
