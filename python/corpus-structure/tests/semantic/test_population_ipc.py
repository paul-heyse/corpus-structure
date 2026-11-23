"""Exact process binding and mutation refusal for sealed population IPC."""

import multiprocessing
import os
from typing import TypedDict, cast

import pyarrow as pa
import pytest

from corpus_structure.semantic.population_ipc import SealedPopulationIpc

_SCHEMA = pa.schema([pa.field("ordinal", pa.int32()), pa.field("label", pa.string())])


class _IpcBinding(TypedDict):
    schema: pa.Schema
    request_digest: str
    projection_digest: str
    max_bytes: int


_BINDING: _IpcBinding = {
    "schema": _SCHEMA,
    "request_digest": "request-a",
    "projection_digest": "projection-a",
    "max_bytes": 65536,
}


def population():
    return pa.table({"ordinal": [0, 1], "label": ["\u03b1", None]}, schema=_SCHEMA)


def _consume(transferred, queue):
    try:
        with transferred, transferred.open(**_BINDING) as table:
            queue.put(
                (
                    os.getpid(),
                    table.to_pydict(),
                    all(
                        not buffer.is_mutable
                        for buffer in table.column(0).chunk(0).buffers()
                        if buffer
                    ),
                )
            )
    except BaseException as error:
        queue.put((type(error).__name__, str(error)))


def test_sealed_population_crosses_spawn_and_rejects_write_alias():
    with SealedPopulationIpc.write(population(), **_BINDING) as owned:
        descriptor = owned._descriptor
        assert descriptor is not None
        with pytest.raises(OSError):
            os.pwrite(descriptor, b"changed", 0)
        with pytest.raises(OSError):
            os.ftruncate(descriptor, 1)
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        process = context.Process(target=_consume, args=(owned, queue))
        try:
            process.start()
            result = queue.get(timeout=20)
            process.join(timeout=20)
            assert process.exitcode == 0
            pid, values, immutable = result
            assert pid != os.getpid()
            assert values == {"ordinal": [0, 1], "label": ["\u03b1", None]}
            assert immutable
            with owned.open(**_BINDING) as table:
                assert table.equals(population(), check_metadata=True)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)
            queue.close()
            queue.join_thread()
    owned.close()
    with pytest.raises(OSError):
        os.fstat(descriptor)
    with pytest.raises(ValueError, match="closed"), owned.open(**_BINDING):
        pytest.fail("closed descriptor accepted")


@pytest.mark.parametrize("field", ["request_digest", "projection_digest", "schema", "max_bytes"])
def test_ingress_rejects_wrong_binding_or_byte_bound(field):
    value = {
        "request_digest": "request-b",
        "projection_digest": "projection-b",
        "schema": pa.schema([("ordinal", pa.int64()), ("label", pa.string())]),
        "max_bytes": 1,
    }[field]
    with (
        SealedPopulationIpc.write(population(), **_BINDING) as owned,
        pytest.raises(ValueError),
        owned.open(**cast(_IpcBinding, _BINDING | {field: value})),
    ):
        pytest.fail("wrong binding accepted")


def test_ingress_authenticates_seal_and_refuses_unsealed_input():
    with SealedPopulationIpc.write(population(), **_BINDING) as owned:
        owned.digest = "0" * 64
        with pytest.raises(ValueError, match="transfer seal"), owned.open(**_BINDING):
            pytest.fail("changed descriptor accepted")
    descriptor = os.memfd_create("unsealed", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    with (
        SealedPopulationIpc(descriptor, 1, "0" * 64) as unsealed,
        pytest.raises(ValueError, match="not sealed"),
        unsealed.open(**_BINDING),
    ):
        pytest.fail("unsealed input accepted")
    with pytest.raises(ValueError, match="byte bound"):
        SealedPopulationIpc.write(population(), **cast(_IpcBinding, _BINDING | {"max_bytes": 1}))
