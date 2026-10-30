"""Batch-independent content, detached files and borrowed backing lifetimes."""

from dataclasses import replace
from decimal import Decimal

import pyarrow as pa
import pytest

from corpus_structure.semantic.analytics import AnalysisScope, CapturedPacket
from corpus_structure.semantic.capture_storage import (
    CaptureOwner,
    FileRelation,
    LogicalRows,
    finish_manifest,
    store_relation,
)

from .test_analytics import empty_packet, prepared_inputs


def test_logical_digest_preserves_float_sign_decimal_and_nanosecond_without_batch_identity():
    table = pa.table(
        {
            "id": ["a", "b"],
            "f": [0.0, -0.0],
            "d": pa.array([Decimal("1.00"), Decimal("2.00")], type=pa.decimal128(10, 2)),
            "t": pa.array([1, 2], type=pa.timestamp("ns", tz="UTC")),
        }
    )
    whole = LogicalRows(table.schema, ("id",))
    split = LogicalRows(table.schema, ("id",))
    for batch in table.to_batches():
        whole.write(batch)
    for batch in table.to_batches(max_chunksize=1):
        split.write(batch)
    assert whole.digest == split.digest
    changed = table.set_column(1, "f", pa.array([0.0, 0.0]))
    other = LogicalRows(changed.schema, ("id",))
    for batch in changed.to_batches():
        other.write(batch)
    assert whole.digest != other.digest


def test_spooled_empty_schema_file_integrity_and_lease(tmp_path):
    owner = CaptureOwner(tmp_path)
    schema = pa.schema([pa.field("id", pa.string())], metadata={b"identity": b"bound"})
    relation, _descriptor = store_relation(owner, "empty", schema, [], ("id",), [0], 100)
    assert isinstance(relation, FileRelation)
    relation.verify()
    assert relation.num_rows == 0 and relation.schema.equals(schema, check_metadata=True)
    owner.acquire()
    owner.close()
    assert relation.path.exists()
    with pytest.raises(RuntimeError, match="closed"):
        owner.acquire()
    owner.release()
    assert not relation.path.exists()


def test_resident_limit_refuses_and_corrupt_file_refuses(tmp_path):
    table = pa.table({"id": ["a", "b"]})
    with pytest.raises(ValueError, match="spooled"):
        store_relation(None, "rows", table.schema, table.to_batches(), ("id",), [0], 1)
    owner = CaptureOwner(tmp_path)
    relation, _ = store_relation(owner, "rows", table.schema, table.to_batches(), ("id",), [0], 1)
    assert isinstance(relation, FileRelation)
    relation.path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        relation.verify()
    owner.close()


def test_spooled_scope_consumes_files_without_materializing_and_keeps_active_backing(tmp_path):
    packet = empty_packet(prepared_inputs()[2])
    owner = CaptureOwner(tmp_path)
    relations = {}
    descriptors = {}
    for name, table in packet.relations.items():
        assert isinstance(table, pa.Table)
        relations[name], descriptors[name] = store_relation(
            owner, name, table.schema, table.to_batches(), (), [0], 1
        )
    manifest = finish_manifest(
        owner,
        dict(
            release_id=packet.binding.release_id,
            realization_id=packet.binding.realization_id,
            data_revision=packet.binding.data_revision,
            capture_id=packet.binding.capture_id,
        ),
        packet.projection_id,
        packet.profile_digest,
        descriptors,
    )
    detached = replace(packet, relations=relations, owner=owner, manifest=manifest)
    with AnalysisScope(detached) as scope:
        detached.close()
        assert owner.root.exists()
        assert scope.fact_support().to_arrow_table().num_rows == 0
    assert not owner.root.exists()


def test_capture_closes_packet_when_exporting_context_exit_fails(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from corpus_structure.semantic import analytics, query

    closed = []
    packet = SimpleNamespace(close=lambda: closed.append(True))

    @contextmanager
    def failed_exit(*args, **kwargs):
        yield object()
        raise KeyboardInterrupt("exporting scope exit")

    monkeypatch.setattr(query, "read_session", failed_exit)
    monkeypatch.setattr(analytics, "load_packet", lambda *args, **kwargs: packet)
    with pytest.raises(KeyboardInterrupt, match="scope exit"):
        analytics.capture_packet(None, "z", "unused")
    assert closed == [True]


def test_writer_cleanup_preserves_cancellation(monkeypatch, tmp_path):
    from corpus_structure.semantic import capture_storage

    class BrokenWriter:
        def __init__(self, *args, **kwargs):
            pass

        def write_batch(self, batch):
            raise KeyboardInterrupt("write cancelled")

        def close(self):
            raise ValueError("cleanup failed")

    monkeypatch.setattr(capture_storage.pq, "ParquetWriter", BrokenWriter)
    owner = CaptureOwner(tmp_path)
    rows = pa.table({"id": ["a"]})
    try:
        with pytest.raises(KeyboardInterrupt, match="write cancelled") as failure:
            store_relation(owner, "rows", rows.schema, rows.to_batches(), ("id",), [0], 1)
        assert any("cleanup failed" in note for note in failure.value.__notes__)
    finally:
        owner.close()


def test_manifest_is_immutable_and_public_reads_refuse_corrupt_files(tmp_path):
    from corpus_structure.serve.export import export_packet

    packet = empty_packet(prepared_inputs()[2])
    owner = CaptureOwner(tmp_path)
    relations, descriptors = {}, {}
    for name, rows in packet.relations.items():
        assert isinstance(rows, pa.Table)
        relations[name], descriptors[name] = store_relation(
            owner, name, rows.schema, rows.to_batches(), (), [0], 1
        )
    from dataclasses import asdict

    manifest = finish_manifest(
        owner, asdict(packet.binding), packet.projection_id, packet.profile_digest, descriptors
    )
    detached = replace(packet, relations=relations, owner=owner, manifest=manifest)
    assert detached.manifest is not None
    exposed = detached.manifest["relations"]
    exposed["entity"]["rows"] = 999
    assert detached.manifest["relations"]["entity"]["rows"] == 0
    relations["entity"].path.write_bytes(b"corrupt")
    try:
        with pytest.raises(ValueError, match="integrity"):
            detached.to_table("entity")
        with pytest.raises(ValueError, match="integrity"):
            export_packet(detached, tmp_path / "bad-export")
        assert not (tmp_path / "bad-export").exists()
    finally:
        detached.close()


def test_packet_context_preserves_primary_error_when_disposal_also_fails(monkeypatch):
    packet = empty_packet(prepared_inputs()[2])

    def broken_close(self):
        raise OSError("capture disposal failed")

    monkeypatch.setattr(CapturedPacket, "close", broken_close)
    with pytest.raises(KeyboardInterrupt, match="primary cancellation") as caught, packet:
        raise KeyboardInterrupt("primary cancellation")
    assert any("disposal failed" in note for note in caught.value.__notes__)
    with pytest.raises(OSError, match="disposal failed"), packet:
        pass
