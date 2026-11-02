"""Public PDF reads settle cursors, decoding and output before a borrower can be reused."""

import io
import json
from unittest.mock import MagicMock

import psycopg
import pytest
from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation, DatabaseOperationCancelled
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.serve import native_source


def borrower():
    driver = MagicMock(spec=psycopg.Connection)
    driver.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
    conn = MagicMock(spec=Connection)
    conn.connection.driver_connection = driver
    conn.__enter__.return_value = conn
    conn.execution_options.return_value = conn
    return conn, driver


def request():
    return native_source.NativeSourceRequest(
        run_id=1, task_id=2, product_key="native", content_digest="a" * 64
    )


def test_snapshot_keeps_cancel_registration_until_rollback_and_not_next_borrower():
    conn, driver = borrower()
    engine = MagicMock(spec=Engine)
    engine.connect.return_value = conn
    cancellation = BorrowerCancellation()
    settled = []

    def rollback(*args):
        # The transaction exits while this borrower remains registered.
        cancellation.request_cancel()
        settled.append(args[0])

    conn.begin.return_value.__exit__.side_effect = rollback
    with (
        pytest.raises(DatabaseOperationCancelled),
        read_snapshot(engine, cancellation=cancellation),
    ):
        cancellation.request_cancel()
    assert settled == [DatabaseOperationCancelled]
    assert driver.cancel_safe.call_count == 2
    cancellation.request_cancel()
    assert driver.cancel_safe.call_count == 2


def test_abandoned_native_event_iterator_closes_result_and_unregisters():
    conn, driver = borrower()
    cancellation = BorrowerCancellation()
    result = conn.execute.return_value.__enter__.return_value
    result.__iter__.return_value = iter([(json.dumps({"kind": "literal", "value": "{"}),)])
    reader = PublishedPdfReader(
        conn, ProductReference(2, "native", "a" * 64), revision={}, cancellation=cancellation
    )
    events = reader.iter_native_events()
    assert next(events) == {"kind": "literal", "value": "{"}
    events.close()
    conn.execute.return_value.__exit__.assert_called_once()
    cancellation.request_cancel()
    driver.cancel_safe.assert_not_called()


@pytest.mark.parametrize("integrated", [False, True])
def test_sink_cancellation_closes_chunks_and_never_returns_success_receipt(integrated):
    cancellation = BorrowerCancellation()
    closed = []

    class Reader(PublishedPdfReader):
        def __init__(self):
            self.cancellation = cancellation
            self.reference = ProductReference(2, "integrated", "a" * 64)
            self.revision = {}

        def product_kind(self):
            return "integrated"

        def iter_native_json(self, events=None):
            try:
                yield b"{}"
            finally:
                closed.append(True)

    class Sink(io.BytesIO):
        def write(self, chunk):
            result = super().write(chunk)
            if chunk == b"{}":
                cancellation.request_cancel()
            return result

    reader = Reader()
    with pytest.raises(DatabaseOperationCancelled):
        if integrated:
            reader.write_integrated_json(Sink())
        else:
            reader.write_native_json(Sink())
    assert closed == [True]


def test_companion_decode_cancellation_refuses_decoded_value(monkeypatch):
    from corpus_structure.semantic import pdf_payloads

    cancellation = BorrowerCancellation()
    reader = object.__new__(PublishedPdfReader)
    reader.cancellation = cancellation
    monkeypatch.setattr(reader, "scalar", lambda stream: iter([b"payload"]))
    monkeypatch.setattr(reader, "_payload_context", lambda: None)

    def decode(*args, **kwargs):
        cancellation.request_cancel()
        return {"page_no": 1}

    monkeypatch.setattr(pdf_payloads, "decode_page_payload", decode)
    row = {
        "body": {
            "payload_codec": pdf_payloads.PROFILE,
            "payload_schema_digest": "b" * 64,
            "payload_logical_digest": "c" * 64,
        },
        "_fields": [
            {
                "field_name": "value",
                "scalar_kind": "y",
                "stream_id": "page1",
                "encoding_profile": pdf_payloads.PROFILE,
            }
        ],
    }
    with pytest.raises(DatabaseOperationCancelled):
        reader.decode_companion_row(row)


@pytest.mark.parametrize("failure", ["cancel", "sink", "final_link"])
def test_failed_export_leaves_no_data_manifest_or_scratch(tmp_path, monkeypatch, failure):
    conn, driver = borrower()
    cancellation = BorrowerCancellation()
    output = tmp_path / "native.json"

    def staged(conn, request, destination, **kwargs):
        assert kwargs["cancellation"] is cancellation
        destination.write_bytes(b'{"exact":-0.0}')
        destination.with_name(destination.name + ".manifest.json").write_text("{}")
        if failure == "cancel":
            cancellation.request_cancel()
        elif failure == "sink":
            raise OSError("sink unavailable")

    monkeypatch.setattr(native_source, "_export_native_source", staged)
    if failure == "final_link":
        import os

        link = os.link

        def failing_link(source, destination):
            if destination == output:
                raise OSError("destination unavailable")
            return link(source, destination)

        monkeypatch.setattr(os, "link", failing_link)
    with pytest.raises(DatabaseOperationCancelled if failure == "cancel" else OSError):
        native_source.export_native_source(conn, request(), output, cancellation=cancellation)
    assert list(tmp_path.iterdir()) == []
    dispatched = driver.cancel_safe.call_count
    cancellation.request_cancel()
    assert driver.cancel_safe.call_count == dispatched


def test_export_preserves_exact_bytes_and_existing_destination(tmp_path, monkeypatch):
    conn, _ = borrower()
    output = tmp_path / "native.json"
    exact = b'{"negative_zero":-0.0,"ordered":[3,1,3],"empty":[]}'

    def staged(conn, request, destination, **kwargs):
        destination.write_bytes(exact)
        destination.with_name(destination.name + ".manifest.json").write_text('{"ready":true}')

    monkeypatch.setattr(native_source, "_export_native_source", staged)
    native_source.export_native_source(conn, request(), output)
    assert output.read_bytes() == exact
    assert output.with_name(output.name + ".manifest.json").read_text() == '{"ready":true}'
    with pytest.raises(FileExistsError):
        native_source.export_native_source(conn, request(), output)
    assert output.read_bytes() == exact
    assert not any(path.is_dir() for path in tmp_path.iterdir())


@pytest.mark.parametrize("settlement_failure", [False, True])
def test_cli_publishes_only_after_snapshot_settlement(
    cli, tmp_path, monkeypatch, settlement_failure
):
    from contextlib import contextmanager

    from corpus_structure.semantic import query, runtime

    output = tmp_path / "native.json"
    settled = []

    @contextmanager
    def engine(*args, **kwargs):
        yield object()

    @contextmanager
    def snapshot(*args, **kwargs):
        yield object()
        assert not output.exists()
        assert not output.with_name(output.name + ".manifest.json").exists()
        if settlement_failure:
            raise OSError("read snapshot settlement failed")
        settled.append(True)

    def export(conn, request, destination, **kwargs):
        assert not settled
        destination.write_bytes(b'{"exact":-0.0}')
        destination.with_name(destination.name + ".manifest.json").write_text("{}")

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(query, "read_snapshot", snapshot)
    monkeypatch.setattr(native_source, "export_native_source", export)
    result = cli(
        "source",
        "native-export",
        "--run",
        "1",
        "--producing-task",
        "2",
        "--product",
        "native",
        "--digest",
        "a" * 64,
        "--output",
        str(output),
        "--format",
        "docling-json",
    )
    if settlement_failure:
        assert result.exit_code != 0
        assert not output.exists()
        assert not output.with_name(output.name + ".manifest.json").exists()
    else:
        assert result.exit_code == 0, result.output
        assert settled == [True]
        assert output.read_bytes() == b'{"exact":-0.0}'
        assert output.with_name(output.name + ".manifest.json").read_text() == "{}"
    assert not any(path.is_dir() for path in tmp_path.iterdir())
