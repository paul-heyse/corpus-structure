"""Frozen metadata must share source/recognition closure with draft preparation."""

import json

import pytest

from .test_pdf_ocr_contracts import inventory
from .test_pdf_payload_validation import captured


def replace_health(store, health):
    store.db.execute(
        "UPDATE entry SET body=? WHERE family='companion' AND key=?",
        (
            json.dumps(dict(family="health", local_id="health", body=health)),
            json.dumps(["health", "health"]),
        ),
    )


@pytest.mark.parametrize(
    "scope,start,end,diagnostic",
    [
        ("page_range", 2, 3, "outside declared source scope"),
        ("page_range", 2, 1, "ordered physical page bounds"),
        ("page_range", 1, None, "ordered physical page bounds"),
        ("whole_document", 1, 1, "cannot carry page-range bounds"),
    ],
)
def test_frozen_source_bounds_are_not_omitted(tmp_path, scope, start, end, diagnostic):
    store, _, document, projection = captured(tmp_path, inventory())
    replace_health(store, dict(source_scope=scope, page_start=start, page_end=end))
    try:
        with pytest.raises(ValueError, match=diagnostic):
            store.validate(document, projection)
    finally:
        store.close()


def test_frozen_complete_display_coverage_requires_actual_formula_outcomes(tmp_path):
    store, _, document, projection = captured(tmp_path, inventory())
    native = {**document, "texts": [dict(self_ref="#/texts/0", label="formula")]}
    projection.write_text(
        json.dumps(dict(family="access", body=dict(pointer="#/texts/0", label="formula"))) + "\n"
    )
    replace_health(store, dict(source_scope="whole_document", display_coverage="complete"))
    try:
        with pytest.raises(ValueError, match="lacks attributable recognition"):
            store.validate(native, projection)
    finally:
        store.close()
