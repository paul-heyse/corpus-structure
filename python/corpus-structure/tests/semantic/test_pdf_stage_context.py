"""Native stage ownership keeps actual Run and DataRequest contexts distinct."""

from dataclasses import asdict

import pytest
from pydantic import TypeAdapter
from sqlalchemy import text

from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt, PublishedPdfDocumentRef
from semantic.pdf_staging_support import private_build as private_build


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
    private_build, commit_db_engine
):
    with commit_db_engine.connect() as connection:
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


def _unapproved_pdf_preparation_recipe():
    from dataclasses import replace

    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import MODEL_VERSION
    from semantic.data_operation_declaration_support import source_declaration
    from semantic.data_operation_kernel_support import STORAGE
    from semantic.data_operation_original_support import OriginalSeedRecipe
    from semantic.native_record_fixtures import RecordSourceRecipe

    declaration = source_declaration()
    # An otherwise valid derivation may name preparation, but preparation does
    # not authorize a native side effect or substitute for its captured factory.
    declaration["capabilities"]["preparation"] = "pdf-native"
    return OriginalSeedRecipe(
        RecordSourceRecipe(),
        replace(
            STORAGE,
            name="unapproved-pdf-preparation",
            declaration_content=json_bytes(
                {"version": MODEL_VERSION, "operations": [declaration]}
            ),
        ),
    )


@pytest.mark.parametrize(
    "ddo_original_source",
    [_unapproved_pdf_preparation_recipe()],
    indirect=True,
    ids=["derivation-without-pdf-effect"],
)
def test_native_pdf_preparation_does_not_authorize_private_original_writes(ddo_original_source):
    from native_refusals import native_refusal

    from semantic.data_operation_demand_support import attach, claim

    case = ddo_original_source
    with case.admin.connect() as connection:
        original = connection.execute(
            text(
                "SELECT d.key,a.content FROM kb.document d "
                "JOIN kb.source_artifact a ON a.artifact_digest=d.content_hash WHERE d.id=:document"
            ),
            {"document": case.source.document},
        ).one()
    _, _, _, attached = attach(
        case.kernel,
        subject="original:" + original.key,
        original_source=original.key,
        analyzed_scope={},
        project_id=case.source.project_id,
    )
    fence = claim(case.kernel, attached)
    params = {"task": fence["task_id"], "attempt": fence["attempt"], "holder": fence["holder"]}
    with case.admin.begin() as connection:
        # Admission, demand, request and claimed task are genuine. The native
        # private boundary must independently refuse the missing effect authority.
        before = connection.execute(
            text(
                "SELECT (SELECT count(*) FROM ops.source_build),"
                "(SELECT count(*) FROM kb.source_artifact)"
            )
        ).one()
    with (
        case.writer.begin() as connection, native_refusal(
            "P0004",
            message="stale private PDF build owner/capability/support",
            context="ops.require_pdf_stage_owner",
        ),
        connection.begin_nested(),
    ):
        connection.execute(
            text("SELECT ops.retain_pdf_original(:task,:attempt,:holder,:original,:recipe)"),
            {
                **params,
                "original": bytes(original.content),
                "recipe": b'{"recipe":"forbidden"}',
            },
        )
    with case.admin.connect() as connection:
        after = connection.execute(
            text(
                "SELECT (SELECT count(*) FROM ops.source_build),"
                "(SELECT count(*) FROM kb.source_artifact)"
            )
        ).one()
        assert after == before
        assert connection.scalar(
            text("SELECT count(*) FROM ops.source_build WHERE task_id=:task"), params
        ) == 0
