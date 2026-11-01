"""Independent frozen visibility, reference and replay controls on actual PostgreSQL."""

import pyarrow as pa
import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    published_pdf_revision,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch

from .test_pdf_staging import private_build as private_build


def stage_complete_native(engine, build, directory):
    document = DoclingDocument(name="frozen fixture")
    document.add_text(label=DocItemLabel.TEXT, text="independent expected text")
    result = StreamingPdfResult(
        document, PdfStreamSpool(directory / "pages"), "success", (), b"{}", ()
    )
    for replay in result.write_record_batches(
        directory / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
    ):
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                with engine.begin() as conn:
                    adopt_pdf_batch(
                        conn,
                        build,
                        f"{replay.family}:{index}",
                        {replay.family: (reader.get_batch(index),)},
                    )
    with engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "health",
            [
                {
                    "conversion": "success",
                    "display_coverage": "unknown",
                    "inline_coverage": "unknown",
                    "cell_coverage": "unknown",
                    "source_scope": "whole_document",
                }
            ],
            "health",
        )
    return document


def test_freeze_prepare_validate_seal_and_replay(
    private_build, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        assert len(frozen.frozen_digest) == 64
        assert freeze_pdf_build(conn, build, kind="native") == frozen
        prepare_pdf_build(conn, frozen)
    with semantic_reader_engine.connect() as conn:
        assert published_pdf_revision(conn, build.task_id, "native", "0" * 64) is None
    outcome = validate_pdf_build(semantic_writer_engine, frozen)
    assert len(outcome.logical_digest) == 64
    with semantic_writer_engine.begin() as conn:
        published = seal_pdf_build(conn, frozen, "native")
        assert seal_pdf_build(conn, frozen, "native") == published
    with semantic_reader_engine.connect() as conn:
        assert (
            published_pdf_revision(conn, build.task_id, "native", published.logical_digest)
            == published
        )
        assert conn.execute(
            text(
                "SELECT text FROM ops.pdf_published_item WHERE task_id=:task AND text IS NOT NULL"
            ),
            dict(task=build.task_id),
        ).scalars().all() == ["independent expected text"]
    with pytest.raises(DBAPIError), semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(conn, build, "health", [{"conversion_status": "failed"}], "late")


def test_seal_requires_validation_and_preserves_private_progress(
    private_build, semantic_writer_engine, tmp_path
):
    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    with pytest.raises(DBAPIError), semantic_writer_engine.begin() as conn:
        seal_pdf_build(conn, frozen, "native")
    with semantic_writer_engine.connect() as conn:
        assert published_pdf_revision(conn, build.task_id, "native", "0" * 64) is None


def test_large_metadata_field_preserves_bytes_and_typed_reader(
    private_build, semantic_writer_engine, semantic_reader_engine, semantic_db_engine, tmp_path
):
    from corpus_structure.semantic.identity import canonical_bytes

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    candidate = dict(
        page_no=1,
        text="\u03b1" * 100 + "\x00",
        left=1e-5,
        top=1.5,
        right=2.0,
        bottom=3.0,
        origin="top_left",
        basis="native-font",
    )
    value = dict(page_no=1, has_words=True, has_chars=True, candidates=[candidate] * 1000)
    original = canonical_bytes(value)
    assert len(original) > 65536
    with semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "native_metadata",
            [dict(kind="inline_candidate_pages", ordinal=0, value=value)],
            "large-metadata",
        )
        # Exact replay reuses parts and typed row; it must not append a second value.
        adopt_pdf_companion_batch(
            conn,
            build,
            "native_metadata",
            [dict(kind="inline_candidate_pages", ordinal=0, value=value)],
            "large-metadata",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(semantic_writer_engine, frozen)
    with semantic_writer_engine.begin() as conn:
        published = seal_pdf_build(conn, frozen, "native")
    with semantic_reader_engine.connect() as conn:
        from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
        from corpus_structure.semantic.product_reference import ProductReference

        reader = PublishedPdfReader(
            conn, ProductReference(build.task_id, "native", published.logical_digest)
        )
        assert list(reader.native_metadata("inline_candidate_pages")) == [value]
    from corpus_structure.semantic.pdf_record_identity import byte_root

    with semantic_db_engine.connect() as conn:
        body, stream, expected_length, expected_root = conn.execute(
            text("""
            SELECT c.body,f.stream_id,s.byte_length,s.byte_root FROM kb.pdf_record_companion c
            JOIN kb.pdf_record_companion_field f USING(product_id,revision_id,family,local_id)
            JOIN ops.pdf_artifact_stream s USING(product_id,revision_id,stream_id)
            WHERE c.product_id=:build AND c.family='native_metadata'"""),
            dict(build=build.build_id),
        ).one()
        actual = b"".join(
            conn.execute(
                text(
                    "SELECT body FROM ops.pdf_artifact_part WHERE product_id=:build AND "
                    "stream_id=:stream ORDER BY ordinal"
                ),
                dict(build=build.build_id, stream=stream),
            ).scalars()
        )
        assert actual == original
        assert "value" not in body and len(str(body)) < 1024
        length, root = byte_root((actual,))
        assert (expected_length, expected_root) == (length, root.hex())


def test_metadata_parts_do_not_replace_semantic_schema_validation(
    private_build, semantic_writer_engine
):
    with pytest.raises(DBAPIError), semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            private_build,
            "native_metadata",
            [dict(kind="inline_candidate_pages", ordinal=0, value={"page_no": "not-a-page"})],
            "invalid-metadata",
        )


def test_preparation_does_not_hold_task_lease_lock(private_build, semantic_writer_engine, tmp_path):
    from corpus_structure.semantic.operations import renew_claim

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    with semantic_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
    with semantic_writer_engine.begin() as preparing:
        prepare_pdf_build(preparing, frozen)
        # The preparation transaction is deliberately still open. A heartbeat
        # must proceed on its own connection rather than wait for publication.
        with semantic_writer_engine.begin() as heartbeat:
            heartbeat.exec_driver_sql("SET LOCAL lock_timeout='500ms'")
            renew_claim(
                heartbeat, task_id=build.task_id, attempt=build.attempt, holder=build.holder
            )
