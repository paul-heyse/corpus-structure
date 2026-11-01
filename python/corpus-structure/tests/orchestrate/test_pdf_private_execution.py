"""Parent ownership controls; these are not native-provider qualification."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import psycopg
import pyarrow as pa
import pytest
from sqlalchemy import Engine

from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.orchestrate import pdf_streaming as execution
from corpus_structure.semantic import pdf_staging
from corpus_structure.semantic.operation_results import ClaimedTask


def claim():
    return ClaimedTask(
        task_id=1,
        run_id=1,
        release_id="r",
        method_config_id=1,
        unit_type=TaskUnitType.DOCUMENT,
        unit_id=1,
        unit_key=None,
        packet_hash=None,
        attempt=1,
        holder="owner",
        deadline=datetime.now(UTC) + timedelta(minutes=10),
        invocation_key="i",
        held_progress=None,
    )


class Transactions:
    active = 0
    commits = 0

    def __init__(self):
        self.driver = MagicMock(spec=psycopg.Connection)
        self.driver.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
        self.connection = SimpleNamespace(driver_connection=self.driver)

    @contextmanager
    def connect(self):
        yield self

    @contextmanager
    def begin(self):
        self.active += 1
        try:
            yield self
        except BaseException:
            raise
        else:
            self.commits += 1
        finally:
            self.active -= 1


@pytest.mark.parametrize("fail_after_adoption", [False, True])
def test_private_parent_owns_transactions_and_settles_producer(monkeypatch, fail_after_adoption):
    engine = Transactions()
    build = pdf_staging.PdfBuildRef("b", 1, 1, "owner", "r", "a" * 64, "b" * 64, "c" * 64)
    events = []
    schema = pa.schema([("value", pa.int64())])
    reader = pa.RecordBatchReader.from_batches(schema, [pa.record_batch([[7]], schema=schema)])

    @contextmanager
    def maintained(*args):
        events.append("claim")
        try:
            yield lambda: events.append("check")
        finally:
            events.append("claim_closed")

    def begin(connection, **kwargs):
        assert engine.active == 1
        assert kwargs["attempt"] == 1 and kwargs["source_digest"] == "a" * 64
        return build

    def adopt(connection, actual, key, relations, *, cancellation):
        assert cancellation is not None
        assert cancellation._driver is engine.driver
        assert engine.active == 1 and actual is build and key == "batch-1"
        assert next(iter(relations["native"])).column(0).to_pylist() == [7]
        return pdf_staging.PdfStageReceipt("b", key, "d" * 64, 1)

    @contextmanager
    def producer(actual, check_active):
        assert actual is build and engine.active == 0
        try:
            yield iter([execution.PdfStageBatch("batch-1", {"native": reader})])
        finally:
            assert engine.active == 0
            events.append("producer_closed")

    def adopted(receipt):
        assert engine.active == 0 and engine.commits == 2
        events.append("adopted")
        if fail_after_adoption:
            raise RuntimeError("consumer failed after durable adoption")

    from corpus_structure.semantic import contracts

    def guard(connection, release_id, operation):
        assert engine.active == 1 and release_id == "r" and operation == "stage_pdf_producer"

    monkeypatch.setattr(contracts, "require_database_operation", guard)
    monkeypatch.setattr(execution, "maintained_claims", maintained)
    monkeypatch.setattr(pdf_staging, "begin_pdf_build", begin)
    monkeypatch.setattr(pdf_staging, "adopt_pdf_batch", adopt)

    def run():
        return execution.run_private_pdf_build(
            cast(Engine, engine),
            claim(),
            "owner",
            source_digest="a" * 64,
            recipe_digest="b" * 64,
            schema_digest="c" * 64,
            replay_key="start",
            producer=producer,
            on_adopted=adopted,
        )

    if fail_after_adoption:
        with pytest.raises(RuntimeError, match="consumer failed"):
            run()
    else:
        assert run() is build
    assert events[-1] == "claim_closed"
    assert events.index("producer_closed") < events.index("claim_closed")
    assert engine.active == 0 and engine.commits == 2


def test_ipc_replay_uses_physical_retry_keys_and_preserves_batch_order(tmp_path):
    from hashlib import sha256

    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef

    schema = pa.schema([("value", pa.int64())])
    path = tmp_path / "records.arrow"
    with pa.ipc.new_file(str(path), schema) as writer:
        writer.write_batch(pa.record_batch([[3]], schema=schema))
        writer.write_batch(pa.record_batch([[4]], schema=schema))
    digest = sha256(path.read_bytes()).hexdigest()
    replay = PdfReplayRef(path, digest, path.stat().st_size, "native", 2)
    checks = []
    batches = execution.ipc_replay_batches([replay], lambda: checks.append(True))
    with __import__("contextlib").closing(batches):
        for ordinal, value in enumerate((3, 4)):
            batch = next(batches)
            assert batch.replay_key == f"ipc:native:{digest}:{ordinal}"
            assert next(iter(batch.relations["native"])).column(0).to_pylist() == [value]
    assert len(checks) == 3
    path.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="changed"):
        next(execution.ipc_replay_batches([replay], lambda: None))


def test_native_parent_settles_borrowers_before_claim_maintenance_ends(monkeypatch, tmp_path):
    from corpus_structure.ingest import pdf_stream_types, pdf_worker
    from corpus_structure.semantic import contracts

    engine = Transactions()
    events = []
    active = [False]
    build = pdf_staging.PdfBuildRef("b", 1, 1, "owner", "r", "a" * 64, "b" * 64, "c" * 64)

    @contextmanager
    def maintained(*args):
        active[0] = True
        try:
            yield lambda: None
        finally:
            active[0] = False
            events.append("claim_closed")

    class Owner:
        reference = None

        def close(self):
            assert active[0]
            events.append("source_closed")

    class Worker:
        def __init__(self, *args, **kwargs):
            pass

        def stream(self, *args, **kwargs):
            assert active[0] and engine.active == 0
            return SimpleNamespace(conversion_status="success", errors=())

        def close(self):
            assert active[0]
            events.append("worker_closed")

    monkeypatch.setattr(execution, "maintained_claims", maintained)
    monkeypatch.setattr(pdf_stream_types.OwnedPdfSource, "acquire", lambda *args, **kwargs: Owner())
    monkeypatch.setattr(pdf_worker, "PdfWorker", Worker)
    monkeypatch.setattr(pdf_staging, "begin_pdf_build", lambda *args, **kwargs: build)
    monkeypatch.setattr(contracts, "require_database_operation", lambda *args: None)
    from corpus_structure.semantic import pdf_publication

    def adopt_health(connection, actual, family, records, *, replay_key, cancellation):
        assert engine.active == 1 and family == "health" and actual is build
        assert cancellation._driver is engine.driver
        assert next(iter(records))["conversion"] == "success"

    monkeypatch.setattr(pdf_publication, "adopt_pdf_companion_batch", adopt_health)
    from corpus_structure.ingest.pdf import PdfRecipe

    recipe = PdfRecipe("a" * 40, "b" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assert (
        execution.run_private_native_pdf_build(
            cast(Engine, engine),
            claim(),
            "owner",
            original=tmp_path / "source.pdf",
            recipe=recipe,
            assets=None,
            directory=tmp_path,
            source_digest="a" * 64,
            schema_digest="c" * 64,
            replay_key="start",
        )
        is build
    )
    assert events == ["worker_closed", "source_closed", "claim_closed"]


def test_pdf_transaction_owns_handle_until_commit_and_returns_it_afterward():
    from corpus_structure.core.db.lifetime import BorrowerCancellation

    engine = Transactions()
    cancellation = BorrowerCancellation()
    original_begin = engine.begin

    @contextmanager
    def during_commit():
        with original_begin() as connection:
            yield connection
            cancellation.request_cancel()

    engine.begin = during_commit
    with execution._pdf_transaction(cast(Engine, engine), cancellation):
        pass
    assert engine.commits == 1
    engine.driver.cancel_safe.assert_called_once()
    cancellation.request_cancel()
    engine.driver.cancel_safe.assert_called_once()


def test_pdf_transaction_cancellation_before_commit_rolls_back_and_clears_handle():
    from corpus_structure.core.db.lifetime import BorrowerCancellation, DatabaseOperationCancelled

    engine = Transactions()
    cancellation = BorrowerCancellation()
    with (
        pytest.raises(DatabaseOperationCancelled),
        execution._pdf_transaction(cast(Engine, engine), cancellation),
    ):
        cancellation.request_cancel()
    assert engine.commits == 0 and engine.active == 0
    engine.driver.cancel_safe.assert_called_once()
    cancellation.request_cancel()
    engine.driver.cancel_safe.assert_called_once()
