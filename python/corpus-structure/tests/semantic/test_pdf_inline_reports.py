"""Unresolved candidates retain source custody and bounded actionable diagnostics."""

from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest
from pydantic import create_model
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_ocr_contracts import validate_pdf_inline_reports

from .test_operations import setup


def example():
    return dict(
        document={"pages": {"1": {"size": {"width": 200, "height": 300}}}},
        parent_task_id=2,
        parent_product_key="native",
        parent_digest="a" * 64,
        health={},
        inline_candidate_pages=[
            dict(
                page_no=1,
                has_words=True,
                has_chars=True,
                has_vectors=True,
                candidates=[
                    dict(
                        page_no=1,
                        text="",
                        left=27,
                        top=42,
                        right=30,
                        bottom=47,
                        origin="TOPLEFT",
                        basis="native-vector-gap-v1",
                    )
                ],
            )
        ],
        items=[
            dict(pointer="#/groups/0", label="section", content_layer="body"),
            dict(
                pointer="#/texts/0",
                label="text",
                content_layer="body",
                parent_pointer="#/groups/0",
                section_pointer="#/groups/0",
            ),
        ],
        regions=[
            dict(
                pointer="#/texts/0",
                page_no=1,
                left=26,
                top=40,
                right=66,
                bottom=60,
                origin="top_left",
            )
        ],
        recognition_coverage=[
            dict(
                section_pointer="#/groups/0",
                membership="direct",
                universe="inline",
                outcome="partial",
                policy="native-font-token-vector-ocr-word-v3",
            )
        ],
        inline_alignment_reports=[
            dict(
                page_no=1,
                candidate_index=0,
                item_pointers=["#/texts/0"],
                outcome="unresolved",
                basis="unmatched-native-text",
                detail="Native punctuation leaves correspondence unresolved.",
            )
        ],
    )


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


def test_publication_and_item_inspection_use_fixed_report_relations(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
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
    from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source

    prepared = setup(semantic_db_engine, observations=True, composed=True)
    original = b"%PDF-1.7\nindependent inline correspondence fixture"
    recipe = b'{"fixture":"unresolved-inline"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    document = DoclingDocument(name="Source correspondence")
    document.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    section = document.add_group(label=GroupLabel.SECTION, name="1.1: Sets")
    paragraph = document.add_text(
        label=DocItemLabel.TEXT,
        text="specified set , often called",
        orig="specified set , often called",
        parent=section,
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=26, t=40, r=66, b=60, coord_origin="TOPLEFT"),
            charspan=(0, 27),
        ),
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(), recipe, snapshot(document), "success", (), (), (), None
    )
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        section_refs=frozenset({section.self_ref}),
    )
    payload["inline_candidate_pages"] = example()["inline_candidate_pages"]
    raw = prepare_pdf_product(payload, original, schema, recipe)
    path = tmp_path / "source.pdf"
    path.write_bytes(original)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options={},
            code_commit="inline-report-test",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="pdf.inline-fixture",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="document",
                Config=create_model("InlineFixture"),
            ),
            "default",
            {},
            "inline-fixture",
        )
        identity = register_document(
            conn,
            project_id="p",
            source_uri="file:inline-fixture",
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
            unit_id=identity,
            unit_key="inline-source",
            input_hash="inline-fixture",
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="inline-fixture")[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="inline-fixture",
            original=original,
            recipe_bytes=recipe,
        )
    with semantic_writer_engine.begin() as conn:
        store_pdf_product(
            conn, task_id=task, attempt=claim.attempt, holder="inline-fixture", product=raw
        )
        derived = deepcopy(payload)
        derived.update(
            product_key="partial",
            parent_task_id=task,
            parent_product_key="native",
            parent_digest=raw.digest,
        )
        derived["inline_alignment_reports"] = example()["inline_alignment_reports"]
        derived["inline_alignment_reports"][0]["item_pointers"] = [paragraph.self_ref]
        derived["recognition_coverage"] = example()["recognition_coverage"]
        derived["recognition_coverage"][0]["section_pointer"] = section.self_ref
        partial = prepare_pdf_product(derived, original, schema, recipe)
        for mutation, diagnostic in [
            ("candidate", "candidate is unavailable"),
            ("complete", "unresolved source correspondence"),
        ]:
            bad = deepcopy(derived)
            bad["product_key"] = "bad-" + mutation
            if mutation == "candidate":
                bad["inline_alignment_reports"][0]["candidate_index"] = 9
            else:
                bad["recognition_coverage"][0]["outcome"] = "complete"
            with pytest.raises(DBAPIError, match=diagnostic), conn.begin_nested():
                conn.execute(
                    text(
                        "SELECT ops.publish_native_document(:task,:attempt,:holder,:contract,"
                        ":payload,NULL,:schema,:recipe)"
                    ),
                    dict(
                        task=task,
                        attempt=claim.attempt,
                        holder="inline-fixture",
                        contract=partial.contract_digest,
                        payload=canonical_bytes(bad),
                        schema=schema,
                        recipe=recipe,
                    ),
                )
        store_pdf_product(
            conn, task_id=task, attempt=claim.attempt, holder="inline-fixture", product=partial
        )
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM kb.native_document_inline_alignment_report "
                    "WHERE task_id=:task"
                ),
                dict(task=task),
            )
            == 1
        )
        assert (
            conn.scalar(
                text(
                    "SELECT count(*) FROM kb.native_document_inline_alignment_item "
                    "WHERE task_id=:task"
                ),
                dict(task=task),
            )
            == 1
        )
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(semantic_reader_engine, "before_cursor_execute", capture)
    try:
        with semantic_reader_engine.connect() as conn:
            response = inspect_native_source(
                conn,
                NativeSourceRequest(
                    run_id=run,
                    task_id=task,
                    product_key="partial",
                    content_digest=partial.digest,
                    view="item",
                    pointer=paragraph.self_ref,
                ),
            )
            alignment = response.rows[0]["inline_alignment_reports"]
            assert isinstance(alignment, list)
            report = alignment[0]
            assert isinstance(report, dict)
            assert report["outcome"] == "unresolved"
            assert report["candidate_basis"] == "native-vector-gap-v1"
            assert report["item_pointers"] == [paragraph.self_ref]
            assert report["source_product"] == dict(
                task_id=task, product_key="native", content_digest=raw.digest
            )
            before = len(statements)
            legacy = inspect_native_source(
                conn,
                NativeSourceRequest(
                    run_id=run,
                    task_id=task,
                    product_key="native",
                    content_digest=raw.digest,
                    view="item",
                    pointer=paragraph.self_ref,
                ),
            )
            assert legacy.rows[0]["inline_alignment_reports"] == []
            assert legacy.health["inline_coverage"] == "unknown"
    finally:
        event.remove(semantic_reader_engine, "before_cursor_execute", capture)
    assert any(
        "native_document_inline_alignment_report" in statement for statement in statements[:before]
    )
    assert not any(
        "native_document_product" in statement and "payload" in statement
        for statement in statements
    )
