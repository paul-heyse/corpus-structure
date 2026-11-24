"""Frozen metadata must share source/recognition closure with draft preparation."""

import json

import pytest
from pdf_acceptance_support import inventory

from semantic.pdf_payload_validation_support import captured, validate_projection_fixture


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
    store, _, document, projection = captured(
        tmp_path, inventory(), health=dict(source_scope=scope, page_start=start, page_end=end)
    )
    try:
        with pytest.raises(ValueError, match=diagnostic):
            validate_projection_fixture(store, document, projection)
    finally:
        store.close()


def test_frozen_complete_display_coverage_requires_actual_formula_outcomes(tmp_path):
    store, _, document, projection = captured(
        tmp_path,
        inventory(),
        health=dict(source_scope="whole_document", display_coverage="complete"),
    )
    native = {**document, "texts": [dict(self_ref="#/texts/0", label="formula")]}
    projection.write_text(
        json.dumps(dict(family="access", body=dict(pointer="#/texts/0", label="formula"))) + "\n"
    )
    try:
        with pytest.raises(ValueError, match="lacks attributable recognition"):
            validate_projection_fixture(store, native, projection)
    finally:
        store.close()
