"""Independent frozen visibility, reference and replay controls on actual PostgreSQL."""

import psycopg
import pyarrow as pa
import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument, Size
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

from .pdf_staging_support import private_build as private_build


def stage_complete_native(engine, build, directory):
    document = DoclingDocument(name="frozen fixture")
    document.add_page(page_no=1, size=Size(width=200, height=300))
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
        from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

        # The shared product view exposes the semantic PDF schema identity;
        # validation/projection identities remain separate publication bindings.
        assert (
            conn.execute(
                text(
                    "SELECT contract_digest FROM ops.pdf_selected_product "
                    "WHERE task_id=:task AND product_key='native'"
                ),
                {"task": build.task_id},
            ).scalar_one()
            == trusted_pdf_context().contract_digest
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
    from corpus_structure.semantic.pdf_payloads import prepare_payload_family

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    candidate = dict(
        page_no=1,
        text="\u03b1" * 100 + "\x00",
        left=1e-5,
        top=1.5,
        right=2.0,
        bottom=3.0,
        origin="TOPLEFT",
        basis="native-math-font-v1",
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
        codec = prepare_payload_family()
        assert actual != original
        assert codec.decode(actual, logical_digest=body["payload_logical_digest"]) == value
        assert "value" not in body and len(str(body)) < 1024
        length, root = byte_root((actual,))
        assert (expected_length, expected_root) == (length, root.hex())


def test_metadata_parts_do_not_replace_semantic_schema_validation(
    private_build, semantic_writer_engine
):
    from corpus_structure.semantic.pdf_payloads import PayloadContractError

    with pytest.raises(PayloadContractError), semantic_writer_engine.begin() as conn:
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


@pytest.mark.parametrize("concurrent_append", [False, True])
def test_freeze_hashing_releases_task_lease_and_rechecks_append_inventory(
    private_build, semantic_writer_engine, semantic_db_engine, tmp_path, concurrent_append
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic, sleep

    from corpus_structure.semantic.operations import renew_claim

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    entered = Event()
    backend = []
    # The family list orders artifact parts first and references last. Blocking the
    # final read permits a committed append to an already captured earlier family.
    relation = "ops.pdf_stage_reference" if concurrent_append else "ops.pdf_stage_artifact_part"

    def freeze():
        with semantic_writer_engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout='15s'")
            backend.append(conn.scalar(text("SELECT pg_backend_pid()")))
            entered.set()
            return freeze_pdf_build(conn, build, kind="native")

    with ThreadPoolExecutor(max_workers=1) as executor:
        with semantic_db_engine.begin() as blocker:
            blocker.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            blocker.exec_driver_sql("LOCK TABLE " + relation + " IN ACCESS EXCLUSIVE MODE")
            future = executor.submit(freeze)
            assert entered.wait(5)
            deadline = monotonic() + 5
            while True:
                if future.done():
                    future.result()
                    pytest.fail("freeze completed while its inventory table was locked")
                with semantic_db_engine.connect() as observer:
                    waiting = observer.scalar(text(
                        "SELECT count(*) FROM pg_locks WHERE pid=:pid "
                        "AND locktype='relation' AND relation=to_regclass(:relation) "
                        "AND NOT granted"
                    ), {"pid": backend[0], "relation": relation})
                if waiting:
                    break
                assert monotonic() < deadline, "freeze did not reach the inventory read"
                sleep(0.01)
            with semantic_writer_engine.begin() as heartbeat:
                heartbeat.exec_driver_sql("SET LOCAL lock_timeout='500ms'")
                renew_claim(
                    heartbeat, task_id=build.task_id, attempt=build.attempt, holder=build.holder
                )
            if concurrent_append:
                with semantic_writer_engine.begin() as appender:
                    adopt_pdf_companion_batch(
                        appender, build, "health",
                        [{"conversion": "success", "source_scope": "whole_document",
                          "display_coverage": "unknown", "inline_coverage": "unknown",
                          "cell_coverage": "unknown"}],
                        "concurrent-health", start_ordinal=1,
                    )
        if concurrent_append:
            with pytest.raises(DBAPIError, match="freeze inventory changed") as caught:
                future.result(timeout=10)
            assert isinstance(caught.value.orig, psycopg.Error)
            assert caught.value.orig.sqlstate == "40001"
            with semantic_db_engine.connect() as conn:
                conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
                assert conn.scalar(text(
                    "SELECT state FROM ops.pdf_stage_build WHERE build_id=:build"
                ), {"build": build.build_id}) == "open"
                assert conn.scalar(text(
                    "SELECT count(*) FROM ops.pdf_frozen_build WHERE build_id=:build"
                ), {"build": build.build_id}) == 0
        else:
            assert len(future.result(timeout=10).frozen_digest) == 64


def test_freeze_refuses_stale_transaction_snapshots(
    private_build, semantic_writer_engine, tmp_path
):
    stage_complete_native(semantic_writer_engine, private_build, tmp_path)
    connection = semantic_writer_engine.connect().execution_options(
        isolation_level="REPEATABLE READ"
    )
    with (
        connection as conn,
        conn.begin(),
        pytest.raises(DBAPIError, match="freeze requires READ COMMITTED") as caught,
    ):
        freeze_pdf_build(conn, private_build, kind="native")
    assert isinstance(caught.value.orig, psycopg.Error)
    assert caught.value.orig.sqlstate == "25000"


def test_freeze_count_witness_relies_on_protected_append_only_stage_rows(
    private_build, semantic_writer_engine
):
    # Independent expected inventory: ordinary writers cannot replace/delete rows
    # while the freeze candidate is being hashed without holding the task fence.
    relations = (
        "ops.pdf_stage_document", "ops.pdf_stage_native", "ops.pdf_stage_membership",
        "ops.pdf_stage_reference", "ops.pdf_stage_artifact_stream", "ops.pdf_stage_artifact_part",
        "ops.pdf_stage_companion", "ops.pdf_stage_endpoint", "ops.pdf_stage_companion_field",
    )
    with semantic_writer_engine.connect() as conn:
        for relation in relations:
            assert conn.execute(text(
                "SELECT has_table_privilege(current_user,:relation,'UPDATE'), "
                "has_table_privilege(current_user,:relation,'DELETE')"
            ), {"relation": relation}).one() == (False, False)
    with (
        semantic_writer_engine.begin() as conn,
        pytest.raises(DBAPIError) as caught,
    ):
        conn.execute(text(
            "UPDATE ops.pdf_stage_companion SET body='{}'::jsonb WHERE product_id=:build"
        ), {"build": private_build.build_id})
    assert isinstance(caught.value.orig, psycopg.Error)
    assert caught.value.orig.sqlstate == "42501"


def test_encoded_page_adoption_retains_original_ipc_bytes(
    private_build, semantic_writer_engine, semantic_db_engine, tmp_path, monkeypatch
):
    from corpus_structure.semantic.pdf_payloads import (
        EncodedPagePayload,
        PreparedPayloadFamily,
        prepare_payload_family,
    )

    build = private_build
    stage_complete_native(semantic_writer_engine, build, tmp_path)
    codec = prepare_payload_family()
    value = dict(page_no=1, has_words=False, has_chars=False)
    payload = codec.encode(value, compression="zstd")
    encoded = EncodedPagePayload(payload, codec.schema_digest, codec.logical_digest(value), 1)

    def no_reencoding(*args, **kwargs):
        raise AssertionError("already encoded payload must retain its original bytes")

    monkeypatch.setattr(PreparedPayloadFamily, "encode", no_reencoding)
    with semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "native_metadata",
            [dict(kind="inline_candidate_pages", ordinal=0, value=encoded)],
            "direct-ipc",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    with semantic_db_engine.connect() as conn:
        actual = (
            conn.execute(
                text("""
            SELECT p.body FROM ops.pdf_artifact_stream s
            JOIN ops.pdf_artifact_part p USING(product_id,revision_id,stream_id)
            WHERE s.product_id=:build
            AND s.encoding_profile='pdf-ocr-candidate-ipc-v1'
            ORDER BY p.ordinal
        """),
                dict(build=build.build_id),
            )
            .scalars()
            .all()
        )
    assert b"".join(actual) == payload
