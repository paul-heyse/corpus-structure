"""Native stage ownership keeps actual Run and DataRequest contexts distinct."""

from dataclasses import asdict

import pytest
from pydantic import TypeAdapter
from sqlalchemy import text

from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt, PublishedPdfDocumentRef

from .pdf_staging_support import private_build as private_build


def test_pdf_sealed_publisher_receipt_retains_original_physical_custody():
    publication = PublishedPdfDocumentRef(
        "build:one",
        123,
        "native",
        "a" * 64,
        "release:one",
        "b" * 64,
        "c" * 64,
        "d" * 64,
        "e" * 64,
        "native",
    )
    receipt = PdfExecutionReceipt(publication, 2, "sealed-publisher")
    adapter = TypeAdapter(PdfExecutionReceipt)
    assert adapter.validate_json(adapter.dump_json(receipt), strict=True) == receipt
    assert asdict(receipt)["publication"]["task_id"] == 123
    assert set(asdict(receipt)) == {"publication", "publisher_attempt", "publisher_holder"}
    for attempt, holder in ((0, "owner"), (True, "owner"), (1, "")):
        with pytest.raises(ValueError, match="sealed publisher fence"):
            PdfExecutionReceipt(publication, attempt, holder)


def test_native_legacy_stage_context_authenticates_real_original_and_owner(
    private_build, semantic_db_engine
):
    with semantic_db_engine.connect() as connection:
        context = (
            connection.execute(
                text("SELECT * FROM ops.pdf_task_context(:task)"), {"task": private_build.task_id}
            )
            .mappings()
            .one()
        )
        assert context["project_id"] == "p" and context["release_id"] == private_build.release_id
        assert context["run_id"] > 0
        assert context["request_id"] is None and context["generation"] is None
        assert context["document_id"] > 0
        assert context["source_digest"] == private_build.source_digest
        assert (
            connection.scalar(
                text("SELECT ops.pdf_stage_owner_current(:task,:attempt,:holder)"),
                {
                    "task": private_build.task_id,
                    "attempt": private_build.attempt,
                    "holder": private_build.holder,
                },
            )
            is True
        )
        assert (
            connection.scalar(
                text("SELECT ops.pdf_stage_owner_current(:task,:attempt,:holder)"),
                {
                    "task": private_build.task_id,
                    "attempt": private_build.attempt,
                    "holder": "wrong-owner",
                },
            )
            is False
        )
