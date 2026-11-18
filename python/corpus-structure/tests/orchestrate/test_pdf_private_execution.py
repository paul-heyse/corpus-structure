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

from corpus_structure.orchestrate import pdf_streaming as execution
from corpus_structure.semantic import pdf_staging


def claim():
    return SimpleNamespace(
        task_id=1,
        release_id="r",
        runtime_id="runtime",
        attempt=1,
        holder="owner",
        deadline=datetime.now(UTC) + timedelta(minutes=10),
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


@pytest.mark.parametrize(
    ("device", "ocr_device", "required", "failure"),
    [
        ("cpu", "cpu", True, None),
        ("cuda", "cpu", False, None),
        ("cpu", "cuda", True, None),
        ("cuda", "cuda", True, RuntimeError),
        ("cuda", "cuda", True, KeyboardInterrupt),
    ],
)
def test_native_parent_settles_borrowers_before_claim_maintenance_ends(
    monkeypatch, tmp_path, device, ocr_device, required, failure
):
    from corpus_structure.ingest import pdf_capacity, pdf_stream_types, pdf_worker
    from corpus_structure.semantic import pdf_contracts, pdf_domain
    from corpus_structure.semantic.pdf_payloads import prepare_payload_family, schema_load

    engine = Transactions()
    events = []
    active = [False]
    sleeping = [False]
    uses_gpu = device == "cuda" or ocr_device == "cuda"
    endpoint = "http://127.0.0.1:8035/v1"
    payload_family = prepare_payload_family()
    build = pdf_staging.PdfBuildRef(
        "b",
        pdf_staging.TaskId(1),
        pdf_staging.TaskAttempt(1),
        "owner",
        pdf_staging.ReleaseId("r"),
        "a" * 64,
        "b" * 64,
        "c" * 64,
    )

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
        pid = None
        closed = False

        def __init__(self, *args, **kwargs):
            pass

        def stream(self, request, **kwargs):
            assert active[0] and engine.active == 0
            assert sleeping[0] == uses_gpu
            assert schema_load(request.payload_schema) == payload_family.json_schema
            if failure is not None:
                raise failure("native stopped")
            from pdf_controlled_support import controlled_preparation_report

            from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
            from corpus_structure.ingest.pdf_streaming import PdfStreamSpool
            from corpus_structure.semantic.pdf_certification import PdfProducerCertification

            certificate = request.record_root.parent / "controlled-certificate.json"
            access = request.record_root.parent / "controlled-access.jsonl"
            options = controlled_preparation_report(
                recipe, None, PdfStreamSpool(certificate.parent / "prepared")
            )
            for filename, content, family in (
                ("controlled-preparation.json", options, "native_preparation"),
                ("controlled-completion.jsonl", b"{}\n", "native_completion"),
            ):
                path = certificate.parent / filename
                path.write_bytes(content)
                kwargs["on_replay"](PdfReplayRef.from_path(path, family))
            certificate.write_bytes(
                PdfProducerCertification(
                    "d" * 64,
                    "native",
                    "e" * 64,
                    "f" * 64,
                    "1" * 64,
                    build.source_digest,
                    build.recipe_digest,
                    build.schema_digest,
                ).to_bytes()
            )
            access.write_bytes(b"")
            kwargs["on_replay"](PdfReplayRef.from_path(certificate, "producer_certification"))
            kwargs["on_replay"](PdfReplayRef.from_path(access, "producer_access"))
            return pdf_stream_types.PdfStreamReply(
                "success",
                (),
                recipe.to_bytes(),
                (),
                (),
                effective_options=options,
                certification=PdfReplayRef.from_path(certificate, "producer_certification"),
                access_replay=PdfReplayRef.from_path(access, "producer_access"),
            )

        def close(self):
            assert active[0]
            assert sleeping[0] == uses_gpu
            assert not self.closed
            self.closed = True
            events.append("worker_closed")

    @contextmanager
    def handoff(address, *, check_active, policy):
        assert address == endpoint and policy == ("required" if required else "resident")
        assert active[0] and engine.active == 0
        check_active()
        sleeping[0] = True
        events.append("sleep")
        try:
            yield
        finally:
            sleeping[0] = False
            events.append("wake")

    monkeypatch.setattr(
        pdf_capacity,
        "native_before_nemotron",
        lambda *a, **kw: handoff(*a, **kw, policy="required"),
    )
    monkeypatch.setattr(
        pdf_capacity,
        "suspend_resident_nemotron",
        lambda *a, **kw: handoff(*a, **kw, policy="resident"),
    )
    monkeypatch.setattr(pdf_stream_types.OwnedPdfSource, "acquire", lambda *args, **kwargs: Owner())
    monkeypatch.setattr(pdf_worker, "PdfWorker", Worker)
    monkeypatch.setattr(pdf_staging, "begin_pdf_build", lambda *args, **kwargs: build)
    monkeypatch.setattr(pdf_domain, "require_pdf_database_action", lambda *args: None)

    def task_context(connection, task_id):
        assert connection is engine and engine.active == 1 and active[0]
        assert task_id == 1

        # A labelled pure ownership control borrows real captured schema shapes;
        # these test doubles never publish a passed native/provider result.
        return pdf_contracts.trusted_pdf_context()

    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", task_context)
    from corpus_structure.semantic import pdf_publication

    adoptions = []

    def stage_access(actual_engine, actual, path, *, cancellation, check_active):
        assert actual_engine is engine and actual is build and engine.active == 0
        assert not sleeping[0]
        check_active()
        adoptions.append("access")

    def attest(connection, actual, certificate):
        assert connection is engine and actual is build and engine.active == 1
        assert not sleeping[0]
        assert certificate.kind == "native" and certificate.lowering_identity == "d" * 64
        adoptions.append("certified")

    monkeypatch.setattr(pdf_publication, "stage_pdf_access_projection", stage_access)
    monkeypatch.setattr(pdf_publication, "record_pdf_producer_certification", attest)
    monkeypatch.setattr(
        "corpus_structure.semantic.pdf_lowering.require_lowering_identity", lambda context: "d" * 64
    )
    from corpus_structure.semantic import _pdf_native_calls as calls

    basis = dict(
        request_id="request",
        generation=1,
        release_id="r",
        operation="source.pdf/capture",
        definition="definition",
        recipe="recipe",
        implementation="implementation",
        execution_profile="profile",
        runtime_id="runtime",
        runtime_manifest_digest="a" * 64,
        pdf_domain_digest="b" * 64,
    )
    monkeypatch.setattr(
        calls,
        "read_pdf_producer_basis",
        lambda *a, **k: SimpleNamespace(model_dump=lambda **options: basis),
    )
    monkeypatch.setattr(calls, "register_pdf_spool_producer", lambda *a, **k: "7" * 64)
    monkeypatch.setattr(calls, "register_pdf_spool_contributor", lambda *a, **k: None)
    from corpus_structure.ingest.pdf import PdfRecipe

    recipe = PdfRecipe(
        "a" * 40,
        "b" * 40,
        device=device,
        ocr_device=ocr_device,
        recipe_id="docling-standard-pdf-stream-v1",
    )

    def run():
        with maintained() as check_active:
            return execution.run_private_native_pdf_build(
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
                nemotron_endpoint=endpoint,
                require_nemotron_handoff=required,
                owned_check=check_active,
            )

    if failure is None:
        assert run() is build
        assert adoptions == ["access", "certified"]
    else:
        with pytest.raises(failure, match="native stopped"):
            run()
        assert not adoptions
    native_events = ["sleep", "worker_closed", "wake"] if uses_gpu else ["worker_closed"]
    assert events == [*native_events, "source_closed", "claim_closed"]


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
