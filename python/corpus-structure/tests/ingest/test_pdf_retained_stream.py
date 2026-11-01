import json
from hashlib import sha256
from io import BytesIO

import pytest

from corpus_structure.ingest.pdf_retained_stream import iter_retained_pdf_values


def test_companions_stream_separately_and_native_numbers_are_lossless():
    huge = 2**100
    body = json.dumps(
        {
            "content": {
                "document": {"integer": huge, "negative_zero": -0.0},
                "health": {"conversion": "success"},
            },
            "inputs": [{"input_index": 0}],
            "relations": [{"relation_id": "a"}, {"relation_id": "b"}],
            "health": {"execution_outcome": "succeeded"},
        }
    ).encode()
    values = list(iter_retained_pdf_values(BytesIO(body), expected_sha256=sha256(body).hexdigest()))
    assert [row for family, row in values if family == "relation"] == [
        {"relation_id": "a"},
        {"relation_id": "b"},
    ]
    document = next(row for family, row in values if family == "document")
    assert document["integer"] == huge
    import math

    assert math.copysign(1, document["negative_zero"]) == -1
    assert ("native_health", {"conversion": "success"}) in values
    assert ("health", {"execution_outcome": "succeeded"}) in values


def test_exact_historical_bytes_must_match_even_for_equivalent_json():
    body = b'{ "document": {"name": "x"}, "health": {}}'
    other = json.dumps(json.loads(body), separators=(",", ":")).encode()
    with pytest.raises(ValueError, match="exact serialization digest"):
        list(iter_retained_pdf_values(BytesIO(body), expected_sha256=sha256(other).hexdigest()))


def test_retained_candidates_encode_once_then_keep_exact_typed_ipc(tmp_path, monkeypatch):
    import math

    from corpus_structure.ingest.pdf_retained_stream import retained_pdf_draft
    from corpus_structure.semantic.pdf_payloads import (
        EncodedPagePayload,
        PreparedPayloadFamily,
        prepare_payload_family,
    )

    family = prepare_payload_family()
    page = dict(
        page_no=1,
        has_words=True,
        has_chars=False,
        candidates=[
            dict(
                page_no=1,
                text="x",
                left=1,
                top=-0.0,
                right=2.5,
                bottom=4,
                origin="TOPLEFT",
                basis="native-math-token-v1",
            )
        ],
    )
    expected = family.encode(page)
    original_encode = PreparedPayloadFamily.encode
    original_decode = family.decode
    calls = []

    def encode(self, value, **kwargs):
        calls.append(value["page_no"])
        return original_encode(self, value, **kwargs)

    def refuse(*args, **kwargs):
        raise AssertionError("retained journal must never decode the candidate IPC")

    monkeypatch.setattr(PreparedPayloadFamily, "encode", encode)
    monkeypatch.setattr(PreparedPayloadFamily, "decode", refuse)
    payload = json.dumps(
        dict(
            document={},
            health={"conversion": "success"},
            source_scope="whole_document",
            inline_candidate_pages=[page],
        )
    ).encode()
    path = tmp_path / "retained.json"
    path.write_bytes(payload)
    with retained_pdf_draft(
        path,
        expected_sha256=sha256(payload).hexdigest(),
        product_key="native",
        original=b"original",
        schema_bytes=b"{}",
        recipe_bytes=b"{}",
        directory=tmp_path / "journal",
        kind="native",
        payload_family=family,
    ) as draft:
        rows = list(draft.companions["native_metadata"])
        assert rows == list(draft.companions["native_metadata"])
        value = rows[0]["value"]
        assert isinstance(value, EncodedPagePayload)
        assert value.content == expected
        assert calls == [1]
        decoded = original_decode(value.content)
        assert "font" not in decoded["candidates"][0]
        assert type(decoded["candidates"][0]["left"]) is int
        assert math.copysign(1, decoded["candidates"][0]["top"]) == -1
    assert path.read_bytes() == payload


@pytest.mark.parametrize("body", [b'{"document": {"x": NaN}}', b'{"document": {"x": 1e999}}'])
def test_nonfinite_or_invalid_numeric_input_refuses(body):
    from ijson.common import JSONError

    with pytest.raises(JSONError):
        list(iter_retained_pdf_values(BytesIO(body), expected_sha256=sha256(body).hexdigest()))


def test_missing_or_ambiguous_document_refuses():
    for body in (b'{"relations":[]}', b'{"document":{},"content":{"document":{}}}'):
        with pytest.raises(ValueError, match="native document"):
            list(iter_retained_pdf_values(BytesIO(body), expected_sha256=sha256(body).hexdigest()))


def test_native_draft_preserves_attributable_health_without_publication_envelope(monkeypatch):
    from docling_core.types.doc import DocItemLabel, DoclingDocument

    from corpus_structure.ingest import pdf
    from corpus_structure.ingest.pdf import PdfConversion
    from corpus_structure.ingest.pdf_health import FormulaOutcome
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.ingest.pdf_record_product import native_publication_draft

    document = DoclingDocument(name="Formula source")
    formula = document.add_text(label=DocItemLabel.FORMULA, text="x+1")
    conversion = PdfConversion(
        "a" * 64,
        b"{}",
        snapshot(document),
        "success",
        (),
        (FormulaOutcome(formula.self_ref, "succeeded"),),
        (),
        None,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("record draft must not build a canonical envelope")

    monkeypatch.setattr(pdf, "publication_payload", forbidden)
    draft = native_publication_draft(
        conversion,
        product_key="native",
        original=b"%PDF-1.7",
        schema_bytes=b"{}",
    )
    assert isinstance(draft.document, DoclingDocument)
    assert draft.document.texts[0].text == "x+1"
    assert draft.health["display_coverage"] == "complete"
    assert draft.health["formula_outcomes"] == [
        {"pointer": formula.self_ref, "outcome": "succeeded"}
    ]
    assert "document" not in draft.health


def test_native_occurrence_index_keeps_region_identity_without_copying_large_text():
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest.pdf_record_product import native_occurrence_rows

    document = DoclingDocument(name="Native large field")
    document.add_page(page_no=1, size=Size(width=100, height=200))
    text = "x" * 100000
    item = document.add_text(
        label=DocItemLabel.TEXT,
        text=text,
        prov=ProvenanceItem(
            page_no=1, bbox=BoundingBox(l=1, t=2, r=50, b=20), charspan=(0, len(text))
        ),
    )
    rows = {row["occurrence_id"]: row for row in native_occurrence_rows(document)}
    assert set(rows) == {"#/body", "#/furniture", item.self_ref, item.self_ref + "/prov/0"}
    assert rows[item.self_ref]["address_space"] == "native_item"
    assert rows[item.self_ref + "/prov/0"]["region_index"] == 0
    assert rows[item.self_ref + "/prov/0"]["page_no"] == 1
    assert "text" not in rows[item.self_ref]
    assert document.texts[0].text == text


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

    from corpus_structure.ingest.pdf_retained_stream import derive_retained_native_projection

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
    from corpus_structure.ingest.pdf_retained_stream import derive_retained_native_projection

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

    from corpus_structure.ingest.pdf_retained_stream import derive_retained_native_projection

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


def test_native_rebuild_requires_and_records_current_structural_parent(tmp_path):
    from corpus_structure.ingest.pdf_retained_stream import retained_pdf_draft
    from corpus_structure.semantic.product_reference import ProductReference

    original = b"%PDF-1.7 retained"
    source = dict(
        document={},
        health={},
        source_scope="whole_document",
        artifact_digest=sha256(original).hexdigest(),
        parent_task_id=2,
        parent_product_key="native",
        parent_digest="a" * 64,
    )
    payload = json.dumps(source).encode()
    path = tmp_path / "retained.json"
    path.write_bytes(payload)
    args = dict(
        path=path,
        expected_sha256=sha256(payload).hexdigest(),
        product_key="organized",
        original=original,
        schema_bytes=b"{}",
        recipe_bytes=b"{}",
    )
    with (
        pytest.raises(ValueError, match="explicit current structural mapping"),
        retained_pdf_draft(**args, kind="native", directory=tmp_path / "missing"),
    ):
        pass
    parent = ProductReference(42, "native", "b" * 64)
    with retained_pdf_draft(
        **args, kind="native", directory=tmp_path / "mapped", structural_parent=parent
    ) as draft:
        from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

        inputs = list(draft.companions["input"])
        assert inputs == [dict(role="structural", **parent.values())]
        trusted_pdf_context().boundary.validate_json("PdfProductInput", json.dumps(inputs[0]))
        assert "occurrence" not in draft.companions
        recipe = json.loads(draft.recipe_bytes)
        assert recipe["retained_parent"]["parent_task_id"] == 2
        assert recipe["structural_parent"] == parent.values()
        assert path.read_bytes() == payload
