"""Independent native-envelope custody and geometry examples, without inference."""

from copy import deepcopy
from hashlib import sha256
from importlib.resources import files

import pytest
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from corpus_structure.semantic.pdf_contracts import (
    pdf_shape_guard_sql,
    prepare_pdf_product,
    require_pdf_coverage,
    trusted_pdf_context,
)


@pytest.fixture(scope="module")
def context():
    return trusted_pdf_context()


@pytest.fixture
def source():
    original, recipe = b"%PDF-1.7\nindependent boundary fixture", b'{"recipe":"test"}'
    schema = files("corpus_structure").joinpath(
        "model", "semantic", "docling-validation.schema.json"
    ).read_bytes()
    document = {
        "schema_name": "DoclingDocument", "version": "1.10.0", "name": "Independent",
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}],
                 "content_layer": "body", "name": "_root_", "label": "unspecified"},
        "furniture": {"self_ref": "#/furniture", "children": [],
                      "content_layer": "furniture", "name": "_root_", "label": "unspecified"},
        "texts": [{"self_ref": "#/texts/0", "parent": {"$ref": "#/body"}, "children": [],
                   "content_layer": "body", "label": "formula", "orig": "x²", "text": "x^2",
                   "prov": [{"page_no": 1, "bbox": {"l": 20.0, "t": 30.0, "r": 150.0,
                              "b": 60.0, "coord_origin": "TOPLEFT"}, "charspan": [0, 3]}]}],
        "pages": {"1": {"page_no": 1, "size": {"width": 200.0, "height": 300.0}}},
    }
    payload = {
        "recipe": "pdf-native-v1", "artifact_digest": sha256(original).hexdigest(),
        "product_key": "native", "schema_digest": sha256(schema).hexdigest(),
        "recipe_digest": sha256(recipe).hexdigest(), "native_schema_version": "1.10.0",
        "document": document,
        "health": {"conversion": "success", "display_coverage": "complete",
                   "inline_coverage": "unknown", "cell_coverage": "partial",
                   "formula_outcomes": [{"pointer": "#/texts/0", "outcome": "succeeded"}]},
        "items": [{"pointer": "#/body", "ordinal": 0, "label": "unspecified", "content_layer": "body"},
                  {"pointer": "#/furniture", "ordinal": 1, "label": "unspecified", "content_layer": "furniture"},
                  {"pointer": "#/texts/0", "ordinal": 2, "parent_pointer": "#/body",
                   "label": "formula", "content_layer": "body", "text": "x^2"}],
        "regions": [{"pointer": "#/texts/0", "region_index": 0, "page_no": 1,
                     "page_width": 200.0, "page_height": 300.0, "left": 20.0, "top": 30.0,
                     "right": 150.0, "bottom": 60.0, "origin": "top_left"}],
    }
    return payload, original, schema, recipe


def test_native_roundtrip_preserves_recognition_and_independent_coverage(source, context):
    product = prepare_pdf_product(*source, context=context)
    values = product.values()
    assert values["document"]["texts"][0]["orig"] == "x²"
    assert values["items"][2]["text"] == "x^2"
    assert values["health"]["formula_outcomes"][0]["outcome"] == "succeeded"
    require_pdf_coverage(product, "display")
    with pytest.raises(ValueError, match="coverage"):
        require_pdf_coverage(product, "inline")
    assert prepare_pdf_product(values, *source[1:], context=context) == product


@pytest.mark.parametrize("field", ["artifact_digest", "recipe_digest", "schema_digest"])
def test_retained_bytes_are_not_substitutable(source, context, field):
    source[0][field] = "0" * 64
    with pytest.raises(ValueError, match="retained bytes"):
        prepare_pdf_product(*source, context=context)


@pytest.mark.parametrize("change", ["unknown_header", "unknown_health", "invalid_origin",
                                  "negative_page", "forged_text", "dangling_pointer",
                                  "incomplete_parent", "forged_box", "invented_native_label"])
def test_independent_invalid_inputs_refuse(source, context, change):
    p = source[0]
    if change == "unknown_header": p["extra"] = True
    elif change == "unknown_health": p["health"]["magic_complete"] = True
    elif change == "invalid_origin": p["regions"][0]["origin"] = "pixels"
    elif change == "negative_page": p["regions"][0]["page_no"] = -1
    elif change == "forged_text": p["items"][2]["text"] = "different"
    elif change == "dangling_pointer": p["items"][2]["pointer"] = "#/texts/99"
    elif change == "incomplete_parent": p["parent_task_id"] = 123
    elif change == "forged_box": p["regions"][0]["left"] = 21.0
    elif change == "invented_native_label": p["document"]["texts"][0]["label"] = "invented"
    with pytest.raises((ValueError, JsonSchemaValidationError)):
        prepare_pdf_product(*source, context=context)


def test_equal_formulas_keep_distinct_occurrences(source, context):
    p = source[0]
    second = deepcopy(p["document"]["texts"][0])
    second["self_ref"] = "#/texts/1"
    p["document"]["texts"].append(second)
    p["document"]["body"]["children"].append({"$ref": "#/texts/1"})
    second_projection = deepcopy(p["items"][2])
    second_projection.update(pointer="#/texts/1", ordinal=3)
    p["items"].append(second_projection)
    p["health"]["formula_outcomes"].append({"pointer": "#/texts/1", "outcome": "succeeded"})
    assert len(prepare_pdf_product(*source, context=context).values()["items"]) == 4


def test_native_guard_derives_nested_fields_and_coverage_from_model(context):
    sql = pdf_shape_guard_sql()
    assert "display_coverage" in sql
    assert "formula_outcomes" in sql
    assert "region_index" in sql
    assert "coord_origin" not in sql  # Application field is origin, not an untyped bbox.
    assert "23514" in sql


def test_complete_coverage_cannot_hide_unattributed_recognition(source, context):
    source[0]["health"]["formula_outcomes"][0]["outcome"] = "unknown"
    with pytest.raises(ValueError, match="attributable recognition"):
        prepare_pdf_product(*source, context=context)
