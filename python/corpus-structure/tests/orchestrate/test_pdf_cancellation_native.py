"""Actual PDF owner cancellation across prepare/COPY/rollback on the private database."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import psycopg
import pytest
from semantic import conftest as semantic_fixtures
from semantic import test_pdf_staging as staging_fixtures
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import BorrowerCancellation, DatabaseOperationCancelled
from corpus_structure.orchestrate.pdf_streaming import _pdf_transaction
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, inspect_pdf_progress

semantic_db_engine = semantic_fixtures.semantic_db_engine
semantic_writer_engine = semantic_fixtures.semantic_writer_engine
private_build = staging_fixtures.private_build


def test_actual_pdf_owner_cancels_inflight_copy_and_retains_no_adopted_rows(
    private_build, semantic_writer_engine, semantic_db_engine
):
    cancellation = BorrowerCancellation(timeout=2)
    producing, release = Event(), Event()

    def batches():
        yield staging_fixtures.native_batch(private_build)
        producing.set()
        assert release.wait(5)

    def write():
        with _pdf_transaction(semantic_writer_engine, cancellation) as conn:
            adopt_pdf_batch(
                conn,
                private_build,
                "cancelled-copy",
                {"native": batches()},
                cancellation=cancellation,
            )

    with ThreadPoolExecutor(max_workers=1) as threads:
        writing = threads.submit(write)
        try:
            assert producing.wait(5)
            cancellation.request_cancel()
        finally:
            release.set()
        with pytest.raises((DatabaseOperationCancelled, psycopg.errors.QueryCanceled, DBAPIError)):
            writing.result(timeout=5)
    with semantic_writer_engine.begin() as conn:
        assert inspect_pdf_progress(conn, private_build) == ()
        cancellation.request_cancel()  # no registered old borrower remains
        assert conn.scalar(text("SELECT 71")) == 71
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.pdf_stage_native WHERE product_id=:build"),
                {"build": private_build.build_id},
            )
            == 0
        )
