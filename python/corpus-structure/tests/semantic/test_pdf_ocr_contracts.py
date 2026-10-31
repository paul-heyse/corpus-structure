"""Independent OCR inventory vectors and the native public publication boundary."""

import json
from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest
from pydantic import ValidationError, create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
from corpus_structure.semantic.pdf_ocr_contracts import validate_pdf_ocr_pages

from .test_operations import setup


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
    from corpus_structure.semantic.identity import canonical_bytes
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
        store_pdf_product,
    )

    prepared = setup(semantic_db_engine, observations=True, composed=True)
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
    with semantic_writer_engine.begin() as conn:
        store_pdf_product(
            conn, task_id=task, attempt=claim.attempt, holder="ocr-fixture", product=product
        )
        for mutation, diagnostic in [
            ("transform", "raster-to-PDF"),
            ("address", "estimated-word address"),
            ("partial", "complete word inventory"),
        ]:
            bad = deepcopy(payload)
            bad["product_key"] = "bad-" + mutation
            if mutation == "transform":
                bad["inline_candidate_pages"][0]["ocr_regions"][0]["lines"][0]["words"][0][
                    "left"
                ] += 1
            elif mutation == "address":
                bad["inline_candidate_pages"][0]["candidates"][0].pop("ocr_word_index")
            else:
                bad["inline_candidate_pages"][0]["ocr_regions"][0]["outcome"] = "partial"
            with pytest.raises(DBAPIError, match=diagnostic), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT ops.publish_native_document(:task,:attempt,:holder,:contract,"
                        ":payload,NULL,:schema,:recipe)"
                    ),
                    dict(
                        task=task,
                        attempt=claim.attempt,
                        holder="ocr-fixture",
                        contract=product.contract_digest,
                        payload=canonical_bytes(bad),
                        schema=schema,
                        recipe=recipe,
                    ),
                )
        partial = deepcopy(payload)
        partial["product_key"] = "partial"
        partial["inline_candidate_pages"][0]["ocr_regions"][0]["outcome"] = "partial"
        partial["inline_candidate_pages"][0]["ocr_regions"][0]["lines"][0]["words"].pop()
        partial["recognition_coverage"][0]["outcome"] = "partial"
        kept = prepare_pdf_product(partial, original, schema, recipe)
        store_pdf_product(
            conn, task_id=task, attempt=claim.attempt, holder="ocr-fixture", product=kept
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.native_document_product WHERE task_id=:task"),
                dict(task=task),
            )
            == 2
        )


def test_display_only_page_is_outside_the_declared_inline_prose_universe():
    product = example()
    product["document"]["texts"][0]["label"] = "formula"
    product["inline_candidate_pages"] = []
    validate_pdf_ocr_pages(product)
