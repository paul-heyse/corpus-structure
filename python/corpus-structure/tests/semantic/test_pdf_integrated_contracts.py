"""Independent integrated-PDF payload and contract examples, without database fixtures."""

import pytest

from corpus_structure.semantic.pdf_integrated import prepare_integrated_pdf_product
from semantic.pdf_native_source_support import (
    CELL_IDS,
    IMAGE,
    ITEM_IDS,
    RESPONSE,
    mutate_selected,
    observation,
    prepare,
)
from semantic.pdf_native_source_support import independent_integrated as independent_integrated
from semantic.pdf_native_source_support import native_source as native_source
from semantic.pdf_native_source_support import pdf13_context as pdf13_context


def test_integrated_roundtrip_preserves_full_distinct_inventory(
    native_source,
    independent_integrated,
    pdf13_context,
):
    product = prepare(independent_integrated, native_source, context=pdf13_context)
    actual = product.values()
    assert {row["occurrence_id"] for row in actual["occurrences"]} == ITEM_IDS | CELL_IDS
    assert actual["content"]["document"] == native_source.payload["document"]
    repeated = [row for row in actual["occurrences"] if row["kind"] == "cell"]
    assert [row["text"] for row in repeated] == ["equal", "equal"]
    assert [row["cell_index"] for row in repeated] == [0, 1]
    ambiguity = next(row for row in actual["relations"] if row["kind"] == "correspondence")
    assert ambiguity["relation_id"] == "ambiguous-equal-spelling"
    assert ambiguity["outcome"] == "ambiguous"
    assert [(row["input_index"], row["occurrence_id"]) for row in ambiguity["endpoints"]] == [
        (1, "block-0"),
        (1, "block-1"),
        (2, "block-0"),
        (2, "block-1"),
    ]
    assert actual["health"]["source_fidelity"] == "unassessed"


def test_materialized_integrated_content_enforces_released_metadata_affinity(
    independent_integrated, native_source, pdf13_context
):
    # Valid native runtime metadata remains input-qualified after integration. The
    # outer product owns kind; its content envelope deliberately has no kind field.
    independent_integrated["content"]["runtime_report"] = {
        "packages": [],
        "bindings": [],
        "effective_options": "{}",
    }
    with pytest.raises(ValueError, match="qualified input graph"):
        prepare(independent_integrated, native_source, context=pdf13_context)


def test_retained_observation_preserves_partial_and_no_response(native_source, pdf13_context):
    partial = observation(native_source, outcome="partial")
    product = prepare(partial, native_source, context=pdf13_context)
    assert [o["occurrence_id"] for o in product.values()["occurrences"]] == ["block-0", "block-1"]
    assert product.values()["coverage"][0]["outcome"] == "partial"
    assert product.values()["health"]["source_fidelity"] == "unassessed"
    assert native_source.original not in product.artifacts
    assert {IMAGE, RESPONSE, native_source.recipe} <= set(product.artifacts)
    failed = observation(native_source, outcome="failed")
    failed["occurrences"] = []
    failed["coverage"][0]["outcome"] = "unknown"
    for name in ("raw_response_digest", "finish_reason", "usage_json"):
        del failed["observation"][name]
    failed["observation"].update(
        usage_availability="unavailable", diagnostic="provider disconnected"
    )
    retained = prepare_integrated_pdf_product(
        failed,
        native_source.original,
        native_source.recipe,
        artifacts=(IMAGE,),
        context=pdf13_context,
    )
    assert "raw_response_digest" not in retained.values()["observation"]
    assert retained.values()["observation"]["diagnostic"] == "provider disconnected"


@pytest.mark.parametrize(
    "change",
    [
        "empty_companions",
        "missing_coverage",
        "missing_decision",
        "wrong_kind",
        "exact_glyph",
        "opaque_region",
        "out_of_bounds_region",
        "wrong_region_page",
        "missing_region_page",
        "forged_text",
        "missing_local_endpoint",
        "duplicate_occurrence",
        "duplicate_endpoint",
        "missing_structural",
        "missing_recognition",
    ],
)
def test_invalid_selected_meaning_refuses(
    native_source,
    independent_integrated,
    pdf13_context,
    change,
):
    mutate_selected(independent_integrated, change)
    with pytest.raises(ValueError):
        prepare(independent_integrated, native_source, context=pdf13_context)


@pytest.mark.parametrize(
    "change",
    [
        "complete_partial",
        "fine_image",
        "exact_range",
        "image_bytes",
        "unknown_health",
        "unknown_transform",
        "no_response_success",
        "wrong_observation_page",
    ],
)
def test_invalid_recognition_refuses(native_source, pdf13_context, change):
    value = observation(native_source, outcome="partial")
    if change == "complete_partial":
        value["coverage"][0]["outcome"] = "complete"
    elif change == "fine_image":
        value["observation"]["image"]["precision"] = "cell"
    elif change == "exact_range":
        value["occurrences"][0].update(start=0, end=5)
    elif change == "image_bytes":
        value["observation"]["image"]["artifact_digest"] = "0" * 64
    elif change == "unknown_health":
        value["health"]["magic_complete"] = True
    elif change == "unknown_transform":
        value["observation"]["image"]["transform"]["magic_exact"] = True
    elif change == "wrong_observation_page":
        value["occurrences"][0]["page_no"] = 2
    elif change == "no_response_success":
        value["observation"]["outcome"] = "succeeded"
        del value["observation"]["raw_response_digest"]
    with pytest.raises(ValueError):
        prepare(value, native_source, context=pdf13_context)


def test_reconciliation_operations_are_qualified(pdf13_context):
    for operation in ("map_pdf_observation", "compare_pdf_occurrences", "select_pdf_integration"):
        bound = pdf13_context.require_operation(operation)
        assert bound["implementation"]["symbol"] == operation
        assert "partial" in bound["contract"]["outcomes"]


def test_decomposed_cardinality_is_derived_from_effective_model(
    independent_integrated, pdf13_context, native_rollback
):
    from dataclasses import replace

    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.native_shapes import decomposed_record_guards

    value = independent_integrated
    boundary = pdf13_context.boundary
    conn = native_rollback.connection
    definitions = tuple(
        replace(
            definition,
            properties=tuple(
                replace(prop, minimum_cardinality=1, maximum_cardinality=1)
                if prop.name == "coverage"
                else prop
                for prop in definition.properties
            ),
        )
        if definition.name == "PdfIntegratedProduct"
        else definition
        for definition in boundary.definitions
    )
    boundary = replace(boundary, definitions=definitions)
    collections = {
        "inputs": ("input_rows", "input"),
        "occurrences": ("occurrence_rows", "occurrence"),
        "relations": ("relation_rows", "relation"),
        "coverage": ("coverage_rows", "coverage"),
        "mapping_reports": ("mapping_rows", "mapping_report"),
    }
    plan = decomposed_record_guards(
        boundary,
        "PdfIntegratedProduct",
        "product",
        field_names="envelope_fields",
        collections=collections,
        records={"content": "parsing_item"},
    )
    compact = {k: v for k, v in value.items() if k not in {"content", *collections}}
    content = dict(value["content"])
    content["document_json"] = canonical_bytes(content.pop("document")).decode()

    def literal(item):
        return "'" + canonical_bytes(item).decode().replace("'", "''") + "'"

    for count in (0, 1, 2):
        declarations = [
            "product jsonb:=" + literal(compact) + "::jsonb",
            "parsing_item jsonb:=" + literal(content) + "::jsonb",
            "envelope_fields text[]:=ARRAY[" + ",".join("'" + k + "'" for k in value) + "]",
        ]
        for name, (variable, _) in collections.items():
            rows = value.get(name, [])
            if name == "coverage":
                rows = rows * count
            declarations.append(variable + " json:=" + literal(rows) + "::json")
        sql = (
            "DO $shape$ DECLARE "
            + ";".join(declarations)
            + "; BEGIN "
            + plan.envelope
            + " END $shape$"
        )
        if count == 1:
            conn.exec_driver_sql(sql)
        else:
            with (
                pytest.raises(DBAPIError, match="record shape differs"),
                conn.begin_nested(),
            ):
                conn.exec_driver_sql(sql)
