"""Independent OCR inventory vectors and the native public publication boundary."""

import json
from copy import deepcopy
from typing import Any

import pytest
from pdf_acceptance_support import inventory as inventory
from pydantic import ValidationError

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_ocr_contracts import (
    validate_pdf_cell_coverage,
    validate_pdf_ocr_pages,
    validate_pdf_page_payloads,
)
from corpus_structure.semantic.pdf_payloads import PayloadContractError, prepare_payload_family


@pytest.mark.parametrize("declaration", ["scoped", "health"])
@pytest.mark.parametrize("failure", ["unknown", "failed_math", "missing"])
def test_complete_cell_scope_requires_resolved_assessment(declaration, failure):
    value: dict[str, Any] = dict(
        document={"tables": [{"data": {"table_cells": [{"text": "x"}]}}]},
        items=[
            dict(pointer="#/groups/0", label="section"),
            dict(pointer="#/groups/1", label="section", parent_pointer="#/groups/0"),
            dict(
                pointer="#/tables/0",
                label="table",
                parent_pointer="#/groups/1",
                section_pointer="#/groups/1",
            ),
        ],
        health={},
        cell_reports=[
            dict(
                table_pointer="#/tables/0",
                cell_index=0,
                classification="prose",
                outcome="not_requested",
            )
        ],
    )
    if declaration == "scoped":
        value["recognition_coverage"] = [
            dict(
                section_pointer="#/groups/0",
                membership="descendants",
                universe="cell",
                outcome="complete",
            )
        ]
    else:
        value["health"] = dict(
            cell_coverage="complete", cell_scope=["#/groups/0"], cell_membership="descendants"
        )
    validate_pdf_cell_coverage(value)
    if failure == "missing":
        value["cell_reports"] = []
        diagnostic = "omits a native cell assessment"
    else:
        value["cell_reports"][0].update(
            classification="unknown" if failure == "unknown" else "math", outcome="failed"
        )
        diagnostic = "unresolved recognition/classification"
    with pytest.raises(ValueError, match=diagnostic):
        validate_pdf_cell_coverage(value)
    # A direct scope does not silently include a child section's table.
    if declaration == "scoped":
        value["recognition_coverage"][0]["membership"] = "direct"
    else:
        value["health"]["cell_membership"] = "direct"
    validate_pdf_cell_coverage(value)


def example():
    return dict(
        document={
            "pages": {"1": {"size": {"width": 200, "height": 300}}},
            "texts": [
                dict(self_ref="#/texts/0", label="text", text="x = 2", orig="x = 2", children=[])
            ],
        },
        inline_candidate_pages=[inventory()],
        health={},
        recognition_coverage=[
            dict(
                section_pointer="#/groups/0",
                membership="direct",
                universe="inline",
                outcome="complete",
                policy="native-font-token-vector-ocr-word-v3",
            )
        ],
        items=[
            dict(pointer="#/groups/0", section_pointer="#/groups/0"),
            dict(pointer="#/texts/0", parent_pointer="#/groups/0", section_pointer="#/groups/0"),
        ],
        regions=[dict(pointer="#/texts/0", page_no=1)],
    )


def test_word_inventory_retains_its_estimated_coordinate_frames():
    product = example()
    before = deepcopy(product)
    validate_pdf_ocr_pages(product)
    assert product == before
    word = product["inline_candidate_pages"][0]["ocr_regions"][0]["lines"][0]["words"][0]
    assert (word["left"], word["top"], word["right"], word["bottom"]) == (27, 42, 30, 47)
    assert word["text"] == "x" and (word["start"], word["end"]) == (0, 1)
    typed = trusted_pdf_context().boundary.validate_json(
        "PdfInlineCandidatePage", json.dumps(inventory())
    )
    assert (
        typed.model_dump(mode="json", exclude_none=True)["ocr_regions"]
        == inventory()["ocr_regions"]
    )


@pytest.mark.parametrize(
    "mutation,diagnostic",
    [
        ("transform", "raster-to-PDF"),
        ("range", "recognized line range"),
        ("address", "complete estimated-word address"),
        ("native", "relabel OCR"),
        ("partial", "complete word inventory"),
        ("vectors", "native vector inventory"),
        ("gap", "omits recognized line content"),
    ],
)
def test_misaligned_word_or_coverage_refuses(mutation, diagnostic):
    product = example()
    page = product["inline_candidate_pages"][0]
    region = page["ocr_regions"][0]
    line = region["lines"][0]
    if mutation == "transform":
        line["words"][0]["left"] += 1
    elif mutation == "range":
        line["words"][0]["start"] = 1
    elif mutation == "address":
        page["candidates"][0].pop("ocr_word_index")
    elif mutation == "native":
        page["candidates"][0]["basis"] = "native-math-token-v1"
    elif mutation == "partial":
        region["outcome"] = "partial"
    elif mutation == "vectors":
        page["has_vectors"] = False
    else:
        line["words"].pop()
    with pytest.raises(ValueError, match=diagnostic):
        validate_pdf_ocr_pages(product)


def test_partial_inventory_preserves_native_output_and_old_pages_remain_accepted():
    product = example()
    region = product["inline_candidate_pages"][0]["ocr_regions"][0]
    region["outcome"] = "partial"
    region["lines"][0]["words"].pop()
    product["recognition_coverage"][0]["outcome"] = "partial"
    validate_pdf_ocr_pages(product)
    old = example()
    page = old["inline_candidate_pages"][0]
    page.pop("ocr_regions")
    page.pop("native_text_quality")
    page["has_words"] = True
    page["candidates"] = []
    old["recognition_coverage"][0]["policy"] = "native-font-token-vector-v2"
    before = deepcopy(old)
    validate_pdf_ocr_pages(old)
    assert old == before


@pytest.fixture(scope="module")
def ocr_payload_family():
    return prepare_payload_family()


def test_current_candidate_font_omission_is_distinct_from_explicit_null():
    page: dict[str, Any] = inventory()
    assert "font" not in page["candidates"][0]
    boundary = trusted_pdf_context().boundary
    boundary.validate_json("PdfInlineCandidatePage", json.dumps(page))
    page["candidates"][0]["font"] = None
    with pytest.raises(ValidationError) as invalid:
        boundary.validate_json("PdfInlineCandidatePage", json.dumps(page))
    assert any(tuple(error["loc"]) == ("candidates", 0, "font") for error in invalid.value.errors())


@pytest.mark.parametrize(
    "collection,outcome,text",
    [
        ("lines", "unknown", None),
        ("lines", "complete", None),
        ("words", "partial", "x = 2"),
        ("words", "unknown", "x = 2"),
        ("words", "complete", ""),
    ],
)
def test_observed_empty_ocr_inventory_retains_outcome_and_ipc_metadata(
    ocr_payload_family, collection, outcome, text
):
    product = example()
    page = product["inline_candidate_pages"][0]
    page["candidates"] = []
    region = page["ocr_regions"][0]
    region["outcome"] = outcome
    if collection == "lines":
        region["lines"] = []
    else:
        region["lines"][0].update(text=text, words=[])
    product["recognition_coverage"][0]["outcome"] = "partial"
    before = deepcopy(product)

    typed = trusted_pdf_context().boundary.validate_json("PdfInlineCandidatePage", json.dumps(page))
    assert typed.model_dump(mode="json", exclude_none=True) == page
    encoded = ocr_payload_family.encode(page)
    restored = ocr_payload_family.decode(encoded)
    assert restored == page
    assert restored["ocr_regions"][0]["outcome"] == outcome
    assert len(restored["ocr_regions"]) == 1
    for validate in (validate_pdf_ocr_pages, validate_pdf_page_payloads):
        validate(product)
    assert product == before

    product["recognition_coverage"][0]["outcome"] = "complete"
    for validate in (validate_pdf_ocr_pages, validate_pdf_page_payloads):
        if outcome == "complete":
            validate(product)
        else:
            with pytest.raises(ValueError, match="complete word inventory"):
                validate(product)


@pytest.mark.parametrize("collection", ["lines", "words"])
def test_unavailable_ocr_inventory_is_distinct_from_empty_and_refuses_publication(
    ocr_payload_family, collection
):
    product = example()
    page = product["inline_candidate_pages"][0]
    page["candidates"] = []
    region = page["ocr_regions"][0]
    region["outcome"] = "unknown"
    target: dict[str, Any] = region if collection == "lines" else region["lines"][0]
    target[collection] = []
    empty = deepcopy(page)
    empty_digest = ocr_payload_family.logical_digest(empty)
    del target[collection]
    absent = deepcopy(page)
    assert ocr_payload_family.decode(ocr_payload_family.encode(absent)) == absent
    assert ocr_payload_family.logical_digest(absent) != empty_digest
    typed = trusted_pdf_context().boundary.validate_json(
        "PdfInlineCandidatePage", json.dumps(absent)
    )
    assert typed.model_dump(mode="json", exclude_none=True) == absent
    product["recognition_coverage"][0]["outcome"] = "partial"
    for validate in (validate_pdf_ocr_pages, validate_pdf_page_payloads):
        with pytest.raises(ValueError, match="inventory metadata is unavailable"):
            validate(product)

    # A null inventory is neither absence nor an observed empty list.
    target[collection] = None
    with pytest.raises(PayloadContractError):
        ocr_payload_family.encode(page)
    with pytest.raises(ValidationError):
        trusted_pdf_context().boundary.validate_json("PdfInlineCandidatePage", json.dumps(page))
    for validate in (validate_pdf_ocr_pages, validate_pdf_page_payloads):
        with pytest.raises(ValueError, match="inventory metadata is unavailable"):
            validate(product)


def test_empty_word_list_does_not_establish_complete_recognized_text(ocr_payload_family):
    product = example()
    page = product["inline_candidate_pages"][0]
    page["candidates"] = []
    page["ocr_regions"][0]["lines"][0]["words"] = []
    assert ocr_payload_family.decode(ocr_payload_family.encode(page)) == page
    for validate in (validate_pdf_ocr_pages, validate_pdf_page_payloads):
        with pytest.raises(ValueError, match="omits recognized line content"):
            validate(product)


@pytest.mark.parametrize("validate", [validate_pdf_ocr_pages, validate_pdf_page_payloads])
def test_complete_scope_requires_all_descendant_pages_but_not_an_unrelated_page(validate):
    product = example()
    product["items"][1].update(parent_pointer="#/groups/1", section_pointer="#/groups/1")
    product["items"].extend(
        [
            dict(pointer="#/groups/1", parent_pointer="#/groups/0", section_pointer="#/groups/1"),
            dict(pointer="#/texts/1", parent_pointer="#/body"),
        ]
    )
    product["document"]["pages"]["2"] = {"size": {"width": 200, "height": 300}}
    product["document"]["texts"].append(
        dict(self_ref="#/texts/1", label="text", text="outside scope", children=[])
    )
    product["regions"].append(dict(pointer="#/texts/1", page_no=2))
    product["recognition_coverage"][0]["membership"] = "descendants"
    direct = deepcopy(product["recognition_coverage"][0])
    direct.update(section_pointer="#/groups/1", membership="direct")
    product["recognition_coverage"].append(direct)
    before = deepcopy(product)
    validate(product)
    assert product == before
    product["items"][-1].update(parent_pointer="#/groups/1", section_pointer="#/groups/1")
    with pytest.raises(ValueError, match="native vector inventory"):
        validate(product)


def test_word_shape_does_not_admit_rotation_or_unbounded_confidence():
    boundary = trusted_pdf_context().boundary
    page = inventory()
    page["ocr_regions"][0]["orientation"] = 90
    with pytest.raises(ValidationError):
        boundary.validate_json("PdfInlineCandidatePage", json.dumps(page))
    page = inventory()
    page["ocr_regions"][0]["lines"][0]["words"][0]["confidence"] = 2
    with pytest.raises(ValidationError):
        boundary.validate_json("PdfInlineCandidatePage", json.dumps(page))


def current_candidate_page(value):
    from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate

    return CandidatePage(page_no=value["page_no"], has_words=value["has_words"],
        has_chars=value["has_chars"], has_vectors=value["has_vectors"],
        native_text_quality=value["native_text_quality"],
        candidates=tuple(InlineCandidate.from_wire(row) for row in value["candidates"]),
        ocr_regions=tuple(value["ocr_regions"]))


@pytest.mark.parametrize("partial", [False, True])
def test_public_native_writer_checks_word_custody_and_retains_partial(
    scenario_seeds, tmp_path, monkeypatch, native_settings, partial,
):
    from dataclasses import replace
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from semantic.current_pdf_integration_support import current_integration_journey

    supplied = inventory()
    # These are the actual declared candidate defaults, independently specified.
    supplied["candidates"][0].update(before="", after="")
    if partial:
        supplied["ocr_regions"][0]["outcome"] = "partial"
        supplied["ocr_regions"][0]["lines"][0]["words"].pop()
    refused = []

    def complete_scope_probe(case, engine, claim, holder, draft, arguments, publish):
        if not partial or draft.product_key != "organized":
            return
        assert draft.metadata["inline_candidate_pages"]
        malformed = replace(draft, product_key="invalid-complete-word-coverage", metadata={
            **draft.metadata, "recognition_coverage": (dict(section_pointer="#/body",
                membership="descendants", universe="inline", outcome="complete",
                policy="native-font-token-vector-ocr-word-v3"),),
        })
        # One finite invalid publication under the actual organization claim.
        # Its writer/validation transaction settles before ordinary publication;
        # no caller-wide transaction holds support locks across other probes.
        with pytest.raises(ValueError, match="complete word inventory"):
            publish(engine, claim, holder, malformed, **arguments)
        refused.append("complete-word-inventory")

    with current_integration_journey(scenario_seeds, tmp_path, monkeypatch, native_settings,
        candidate_pages=(current_candidate_page(supplied),), before_draft=complete_scope_probe) as case:
        assert refused == (["complete-word-inventory"] if partial else [])
        with case.reader().connect() as connection:
            for key in ("native", "organized", "integrated"):
                reader = published_record_reader(connection, case.publications[key],
                    projection_context=case.prepared)
                assert reader is not None
                assert list(reader.native_metadata("inline_candidate_pages")) == [supplied]
                retained = reader.product_descriptor()
                assert retained["revision"]["source_digest"] == case.original.content_hash
        if partial:
            from sqlalchemy import text
            with case.clone.admin.connect() as connection:
                assert connection.scalar(text(
                    "SELECT count(*) FROM ops.pdf_published_revision WHERE task_id=:task AND product_key='invalid-complete-word-coverage'"
                ), {"task": case.claims["organized"].task_id}) == 0


@pytest.mark.parametrize("mutation,diagnostic", [("transform", "raster-to-PDF"), ("address", "estimated-word address")])
def test_actual_capture_refuses_forged_ocr_word_geometry_and_address(
    scenario_seeds, tmp_path, monkeypatch, native_settings, mutation, diagnostic,
):
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from semantic.current_pdf_integration_support import current_integration_journey

    malformed = inventory()
    if mutation == "transform":
        malformed["ocr_regions"][0]["lines"][0]["words"][0]["left"] += 1
    else:
        malformed["candidates"][0].pop("ocr_word_index")
    with pytest.raises(NativeDemandExecutionError) as refused:
        with current_integration_journey(scenario_seeds, tmp_path, monkeypatch, native_settings,
                candidate_pages=(current_candidate_page(malformed),)):
            pytest.fail("invalid captured word custody unexpectedly published")
    assert any(diagnostic in str(failure) for failure in refused.value.failures)


def test_display_only_page_is_outside_the_declared_inline_prose_universe():
    product = example()
    product["document"]["texts"][0]["label"] = "formula"
    product["inline_candidate_pages"] = []
    validate_pdf_ocr_pages(product)
