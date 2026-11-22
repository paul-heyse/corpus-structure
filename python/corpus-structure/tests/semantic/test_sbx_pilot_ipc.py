"""Real spawned raw IPC transport under the existing sealed request owner."""

import json
import multiprocessing
import os
import threading
import time
from hashlib import sha256

import pyarrow as pa
import pytest

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    CPUExecutionScope,
    CPUReply,
    CPURequestCancelled,
)
from corpus_structure.semantic.identity import canonical_bytes
from semantic.cpu_execution_support import prepared as prepared
from semantic.sbx_pilot_arrow import ArrowProjection, canonical_values
from semantic.sbx_pilot_ipc import decode_arrow_frame, encode_arrow_frame

_PROJECTION = "sbx-pilot-local-spans-v1"
_SCHEMA = pa.schema(
    [pa.field("ordinal", pa.int64(), nullable=False), pa.field("text", pa.string())]
)


def _table():
    return pa.Table.from_pylist(
        [{"ordinal": 0, "text": "Ada acts."}, {"ordinal": 1, "text": None}], schema=_SCHEMA
    )


def _dispatch_ipc(packet, max_reply_bytes, slot, generation, *_, started=None, release=None):
    from corpus_structure.semantic.cpu_execution import _worker_active

    try:
        if started is not None:
            assert release is not None
            started.set()
            while not release.is_set():
                _worker_active(slot, generation)
                time.sleep(0.01)
        _worker_active(slot, generation)
        decode_arrow_frame(packet.content, expected_projection=_PROJECTION, expected_schema=_SCHEMA)
        if len(packet.content) > max_reply_bytes:
            raise CapacityExceeded("IPC reply exceeds admitted capacity")
        return CPUReply(
            packet.digest,
            packet.content,
            os.getpid(),
            threading.current_thread() is threading.main_thread(),
        )
    except Exception as error:
        return CPUReply(packet.digest, b"", os.getpid(), True, type(error).__name__, str(error))


def _install_dispatch(execution, monkeypatch, *, dispatch=_dispatch_ipc, **kwargs):
    pool = execution._executor()
    submit = pool.submit

    def submit_ipc(_production_dispatch, *args):
        return submit(dispatch, *args, **kwargs)

    monkeypatch.setattr(pool, "submit", submit_ipc)


def _submit(execution, content):
    permit = execution.try_admit(packet_bytes=len(content))
    assert permit is not None
    return execution.submit_closed_python(permit, content)


def _dispatch_canonical(packet, max_reply_bytes, slot, generation, *_, schema, projection):
    from corpus_structure.semantic.cpu_execution import _worker_active

    try:
        _worker_active(slot, generation)
        header_end = 4 + int.from_bytes(packet.content[:4], "big")
        header = json.loads(packet.content[4:header_end])
        projected = ArrowProjection(
            projection,
            header["header"],
            tuple(header["partitions"]),
            tuple(header["fields"]),
            decode_arrow_frame(
                packet.content[header_end:], expected_projection=projection, expected_schema=schema
            ),
        )
        reply = canonical_bytes(canonical_values(projected, header["spec"]))
        _worker_active(slot, generation)
        if len(reply) > max_reply_bytes:
            raise CapacityExceeded("canonical reply exceeds admitted capacity")
        return CPUReply(packet.digest, reply, os.getpid(), True)
    except Exception as error:
        return CPUReply(packet.digest, b"", os.getpid(), True, type(error).__name__, str(error))


def spawned_canonical_values(prepared, projected, spec, monkeypatch):
    header = canonical_bytes(
        {
            "header": projected.header,
            "partitions": projected.partitions,
            "fields": projected.fields,
            "spec": spec,
        }
    )
    content = (
        len(header).to_bytes(4, "big")
        + header
        + encode_arrow_frame(projected.table, projected.fingerprint)
    )
    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    try:
        _install_dispatch(
            execution,
            monkeypatch,
            dispatch=_dispatch_canonical,
            schema=projected.table.schema,
            projection=projected.fingerprint,
        )
        handle = _submit(execution, content)
        handle.future.result(timeout=30)
        reply = handle.collect()
        assert reply.pid != os.getpid() and handle.retire()
        return json.loads(reply.content)
    finally:
        execution.close()


def test_spawned_ipc_preserves_raw_frame_and_reuses_owned_worker(prepared, monkeypatch):
    content = encode_arrow_frame(_table(), _PROJECTION)
    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    try:
        _install_dispatch(execution, monkeypatch)
        pid = None
        for _ in range(2):
            handle = _submit(execution, content)
            assert handle.admission.reserved == len(content) + execution.policy.max_reply_bytes
            handle.future.result(timeout=30)
            reply = handle.collect()
            assert reply.pid != os.getpid()
            if pid is not None:
                assert reply.pid == pid
            pid = reply.pid
            assert reply.content == content
            assert reply.execution_receipt.result_digest == sha256(content).hexdigest()
            restored = decode_arrow_frame(
                reply.content, expected_projection=_PROJECTION, expected_schema=_SCHEMA
            )
            assert restored.to_pylist() == [
                {"ordinal": 0, "text": "Ada acts."},
                {"ordinal": 1, "text": None},
            ]
            assert handle.retire()
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


@pytest.mark.parametrize("mutation", ["truncated", "payload", "projection", "schema"])
def test_spawned_ipc_refuses_changed_frame_and_next_request_succeeds(
    prepared, monkeypatch, mutation
):
    content = encode_arrow_frame(_table(), _PROJECTION)
    if mutation == "truncated":
        malformed = content[:-1]
    elif mutation == "payload":
        malformed = content[:-1] + bytes([content[-1] ^ 1])
    elif mutation == "projection":
        malformed = encode_arrow_frame(_table(), "different-projection")
    else:
        malformed = encode_arrow_frame(_table().rename_columns(["ordinal", "other"]), _PROJECTION)
    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    try:
        _install_dispatch(execution, monkeypatch)
        handle = _submit(execution, malformed)
        handle.future.result(timeout=30)
        with pytest.raises(ValueError, match="IPC"):
            handle.collect()
        assert handle.retire()
        sibling = _submit(execution, content)
        sibling.future.result(timeout=30)
        assert sibling.collect().content == content
        assert sibling.retire()
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0


def test_ipc_full_frame_capacity_and_real_cancellation_retire_credit(prepared, monkeypatch):
    content = encode_arrow_frame(_table(), _PROJECTION)
    execution = CPUExecutionScope(
        prepared, CharacterizationExecutionPolicy(workers=1, max_packet_bytes=len(content) - 1)
    )
    try:
        with pytest.raises(CapacityExceeded):
            execution.try_admit(packet_bytes=len(content))
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0

    execution = CPUExecutionScope(prepared, CharacterizationExecutionPolicy(workers=1))
    try:
        with multiprocessing.get_context("spawn").Manager() as manager:
            started, release = manager.Event(), manager.Event()
            _install_dispatch(execution, monkeypatch, started=started, release=release)
            handle = _submit(execution, content)
            assert started.wait(30)
            handle.cancel()
            handle.future.result(timeout=30)
            with pytest.raises(CPURequestCancelled):
                handle.collect()
            assert handle.retire()
            release.set()
            sibling = _submit(execution, content)
            sibling.future.result(timeout=30)
            assert sibling.collect().content == content
            assert sibling.retire()
    finally:
        execution.close()
    assert execution.budget.used_bytes == 0
