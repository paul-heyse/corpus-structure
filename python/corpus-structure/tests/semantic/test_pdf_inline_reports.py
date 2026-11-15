"""Unresolved candidates retain source custody and bounded actionable diagnostics."""

from copy import deepcopy

import pytest

from corpus_structure.semantic.pdf_ocr_contracts import (
    validate_pdf_inline_reports,
    validate_pdf_page_payloads,
)
from semantic.pdf_inline_reports_support import example as example


def test_unresolved_report_has_no_fabricated_range_and_does_not_mutate_native():
    product = example()
    before = deepcopy(product)
    validate_pdf_inline_reports(product)
    assert product == before
    assert set(product["inline_alignment_reports"][0]) == {
        "page_no",
        "candidate_index",
        "item_pointers",
        "outcome",
        "basis",
        "detail",
    }


def test_fused_page_pass_preserves_all_merged_regions_and_original_candidate_indices():
    product = example()
    matching = deepcopy(product["regions"][0])
    product["regions"][0].update(left=0, top=0, right=10, bottom=10)
    product["regions"].append(matching)
    page = product["inline_candidate_pages"][0]
    page["candidates"].append(deepcopy(page["candidates"][0]))
    second = deepcopy(product["inline_alignment_reports"][0])
    second["candidate_index"] = 1
    product["inline_alignment_reports"].append(second)
    before = deepcopy(product)
    validate_pdf_page_payloads(product)
    assert product == before
    product["regions"].pop()
    with pytest.raises(ValueError, match="page geometry"):
        validate_pdf_page_payloads(product)


@pytest.mark.parametrize(
    "mutation,diagnostic",
    [
        ("candidate", "unavailable candidate"),
        ("parent", "original parent product"),
        ("ambiguous", "cardinality"),
        ("duplicate", "distinct items"),
        ("geometry", "page geometry"),
        ("item", "retained body prose"),
    ],
)
def test_report_cannot_detach_from_candidate_and_original_items(mutation, diagnostic):
    product = example()
    report = product["inline_alignment_reports"][0]
    if mutation == "candidate":
        report["candidate_index"] = 9
    elif mutation == "parent":
        product.pop("parent_digest")
    elif mutation == "ambiguous":
        report["basis"] = "ambiguous-native-items"
    elif mutation == "duplicate":
        report["item_pointers"] *= 2
    elif mutation == "geometry":
        product["regions"][0]["left"] = 100
    else:
        product["items"][1]["label"] = "table"
    with pytest.raises(ValueError, match=diagnostic):
        validate_pdf_inline_reports(product)


@pytest.mark.parametrize("membership", ["direct", "descendants"])
def test_known_unresolved_candidate_cannot_close_affected_inline_scope(membership):
    product = example()
    product["recognition_coverage"][0].update(outcome="complete", membership=membership)
    with pytest.raises(ValueError, match="unresolved source correspondence"):
        validate_pdf_inline_reports(product)
    product["recognition_coverage"][0]["section_pointer"] = "#/groups/unrelated"
    validate_pdf_inline_reports(product)
