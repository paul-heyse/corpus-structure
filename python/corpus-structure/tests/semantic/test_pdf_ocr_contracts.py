"""Independent OCR inventory vectors and the native public publication boundary."""

import json
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError, create_model

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_ocr_contracts import (
    validate_pdf_cell_coverage,
    validate_pdf_ocr_pages,
    validate_pdf_page_payloads,
)
from corpus_structure.semantic.pdf_payloads import PayloadContractError, prepare_payload_family

from .operation_scenario_support import prepare_operation_scenario


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


def inventory():
    words = []
    for index, (spelling, start, left, right) in enumerate(
        (("x", 0, 3, 12), ("=", 2, 15, 24), ("2", 4, 27, 36))
    ):
        words.append(
            dict(
                word_index=index,
                text=spelling,
                confidence=0.9,
                start=start,
                end=start + 1,
                raster_left=left,
                raster_top=6,
                raster_right=right,
                raster_bottom=21,
                left=26 + left / 3,
                top=42,
                right=26 + right / 3,
                bottom=47,
            )
        )
    region = dict(
        region_index=0,
        engine="rapidocr",
        raster_width=120,
        raster_height=60,
        scale=3.0,
        orientation=0,
        left=26,
        top=40,
        right=66,
        bottom=60,
        outcome="complete",
        lines=[dict(line_index=0, text="x = 2", words=words)],
    )
    word = words[0]
    candidate = {key: word[key] for key in ("text", "left", "top", "right", "bottom")}
    candidate.update(
        page_no=1,
        origin="TOPLEFT",
        basis="ocr-word-token-v1",
        ocr_region_index=0,
        ocr_line_index=0,
        ocr_word_index=0,
    )
    return dict(
        page_no=1,
        has_words=False,
        has_chars=False,
        has_vectors=True,
        native_text_quality="broken",
        ocr_regions=[region],
        candidates=[candidate],
    )


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


def test_public_native_writer_checks_word_custody_and_retains_partial(
    semantic_db_engine,
    semantic_writer_engine,
    tmp_path,
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        GroupLabel,
        PageItem,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
        create_run,
        create_task,
        record_method,
        register_document,
    )
    from corpus_structure.semantic.pdf_contracts import (
        prepare_pdf_product,
        store_pdf_original,
    )

    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, composed=True)
    original = b"%PDF-1.7\nindependent OCR custody fixture"
    recipe = b'{"fixture":"estimated-word"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    doc = DoclingDocument(name="Estimated words")
    doc.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    section = doc.add_group(label=GroupLabel.SECTION, name="1.1: Sets")
    doc.add_text(
        label=DocItemLabel.TEXT,
        text="x = 2",
        orig="x = 2",
        parent=section,
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=26, t=40, r=66, b=60, coord_origin="TOPLEFT"),
            charspan=(0, 5),
        ),
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
    )
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        section_refs=frozenset({section.self_ref}),
    )
    payload["inline_candidate_pages"] = [inventory()]
    payload["recognition_coverage"] = [
        dict(
            section_pointer=section.self_ref,
            membership="direct",
            universe="inline",
            outcome="complete",
            policy="native-font-token-vector-ocr-word-v3",
        )
    ]
    product = prepare_pdf_product(payload, original, schema, recipe)
    path = tmp_path / "source.pdf"
    path.write_bytes(original)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options={},
            code_commit="ocr-word-test",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="pdf.ocr-fixture",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="document",
                Config=create_model("OcrFixture"),
            ),
            "default",
            {},
            "ocr-fixture",
        )
        document = register_document(
            conn,
            project_id="p",
            source_uri="file:ocr-fixture",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="ocr-source",
            input_hash="ocr-fixture",
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="ocr-fixture")[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="ocr-fixture",
            original=original,
            recipe_bytes=recipe,
        )
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.product_reference import ProductReference

    from .native_record_fixtures import publish_native_record_fixture

    published = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "native-records",
        task_id=task,
        attempt=claim.attempt,
        holder="ocr-fixture",
        product=product,
        document=doc,
    )
    for mutation, diagnostic in [
        ("transform", "raster-to-PDF"),
        ("address", "estimated-word address"),
        ("partial", "complete word inventory"),
    ]:
        bad = deepcopy(payload)
        bad["product_key"] = "bad-" + mutation
        if mutation == "transform":
            bad["inline_candidate_pages"][0]["ocr_regions"][0]["lines"][0]["words"][0]["left"] += 1
        elif mutation == "address":
            bad["inline_candidate_pages"][0]["candidates"][0].pop("ocr_word_index")
        else:
            bad["inline_candidate_pages"][0]["ocr_regions"][0]["outcome"] = "partial"
        with pytest.raises(ValueError, match=diagnostic):
            malformed = prepare_pdf_product(bad, original, schema, recipe)
            publish_native_record_fixture(
                semantic_writer_engine,
                tmp_path / ("bad-" + mutation),
                task_id=task,
                attempt=claim.attempt,
                holder="ocr-fixture",
                product=malformed,
                document=doc,
            )
    partial = deepcopy(payload)
    partial["product_key"] = "partial"
    partial["inline_candidate_pages"][0]["ocr_regions"][0]["outcome"] = "partial"
    partial["inline_candidate_pages"][0]["ocr_regions"][0]["lines"][0]["words"].pop()
    partial["recognition_coverage"][0]["outcome"] = "partial"
    kept = prepare_pdf_product(partial, original, schema, recipe)
    partial_pin = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "partial-records",
        task_id=task,
        attempt=claim.attempt,
        holder="ocr-fixture",
        product=kept,
        document=doc,
    )
    with semantic_writer_engine.connect() as conn:
        for key, retained, expected in (
            ("native", published, payload),
            ("partial", partial_pin, partial),
        ):
            reader = published_record_reader(
                conn, ProductReference(task, key, retained.logical_digest)
            )
            assert reader is not None
            assert (
                list(reader.native_metadata("inline_candidate_pages"))
                == expected["inline_candidate_pages"]
            )


def test_display_only_page_is_outside_the_declared_inline_prose_universe():
    product = example()
    product["document"]["texts"][0]["label"] = "formula"
    product["inline_candidate_pages"] = []
    validate_pdf_ocr_pages(product)
