from hashlib import sha256
from io import BytesIO
import json

import pytest

from corpus_structure.ingest.pdf_retained_stream import iter_retained_pdf_values


def test_companions_stream_separately_and_native_numbers_are_lossless():
    huge = 2 ** 100
    body = json.dumps({
        "content": {"document": {"integer": huge, "negative_zero": -0.0},
                    "health": {"conversion": "success"}},
        "inputs": [{"input_index": 0}],
        "relations": [{"relation_id": "a"}, {"relation_id": "b"}],
        "health": {"execution_outcome": "succeeded"},
    }).encode()
    values = list(iter_retained_pdf_values(BytesIO(body), expected_sha256=sha256(body).hexdigest()))
    assert [row for family, row in values if family == "relation"] == [
        {"relation_id": "a"}, {"relation_id": "b"},
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
    from docling_core.types.doc import DoclingDocument, DocItemLabel
    from corpus_structure.ingest.pdf import PdfConversion
    from corpus_structure.ingest.pdf_health import FormulaOutcome
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.ingest.pdf_record_product import native_publication_draft
    from corpus_structure.ingest import pdf
    document = DoclingDocument(name="Formula source")
    formula = document.add_text(label=DocItemLabel.FORMULA, text="x+1")
    conversion = PdfConversion(
        "a" * 64, b"{}", snapshot(document), "success", (),
        (FormulaOutcome(formula.self_ref, "succeeded"),), (), None,
    )
    def forbidden(*args, **kwargs):
        raise AssertionError("record draft must not build a canonical envelope")
    monkeypatch.setattr(pdf, "publication_payload", forbidden)
    draft = native_publication_draft(
        conversion, product_key="native", original=b"%PDF-1.7", schema_bytes=b"{}",
    )
    assert isinstance(draft.document, DoclingDocument)
    assert draft.document.texts[0].text == "x+1"
    assert draft.health["display_coverage"] == "complete"
    assert draft.health["formula_outcomes"] == [{"pointer": formula.self_ref, "outcome": "succeeded"}]
    assert "document" not in draft.health
