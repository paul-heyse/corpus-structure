"""Owned native selection with disk-backed companions, not a publication envelope.

The native graph is the explicitly materialized finalization state. Journal rows are
private replay evidence; they never claim frozen-union validation or public visibility.
"""

from __future__ import annotations

import json
from collections.abc import Generator, Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa

from .pdf_reconciliation import _PrivateSelection, _select_pdf_integration

_NAMES = frozenset(
    {
        "input",
        "native_metadata",
        "coverage",
        "rejected",
        "mapping_report",
        "correspondences",
        "mapped_inputs",
        "occurrence",
        "relation",
    }
)
_PUBLIC = ("input", "occurrence", "relation", "mapping_report", "coverage")
_SCHEMA = pa.schema(
    [
        pa.field("ordinal", pa.int64(), nullable=False),
        pa.field("body", pa.large_string(), nullable=False),
        pa.field("raw", pa.binary()),
    ],
    metadata={"profile": "pdf-reconciliation-journal-v1"},
)


class _Rows:
    def __init__(self, journal: ReconciliationJournal, name: str):
        self.journal, self.name = journal, name
        self.count = 0
        self.paths: dict[int, Path] = {}
        self.writers: dict[int, Any] = {}
        self.buffers: dict[int, list[tuple[int, str, bytes | None]]] = {}
        self.buffer_bytes: dict[int, int] = {}
        self.sealed = False

    def append(self, value: Any) -> None:
        if self.sealed:
            raise ValueError("reconciliation collection is already being read")
        phase, raw = 0, None
        if self.name == "mapped_inputs":
            index, observation, raw = value
            phase = int(observation["observation"]["pass_role"] == "C")
            value = [index, observation]
        body = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if phase not in self.writers:
            path = self.journal.directory / f"{self.name}-{phase}.arrow"
            # The owner directory is new and exclusively created for this operation.
            self.paths[phase] = path
            self.writers[phase] = pa.ipc.new_file(str(path), _SCHEMA)
            self.buffers[phase] = []
            self.buffer_bytes[phase] = 0
        size = len(body.encode("utf-8")) + (len(raw) if raw else 0)
        if self.buffers[phase] and self.buffer_bytes[phase] + size > 8 * 1024**2:
            self._flush(phase)
        self.buffers[phase].append((self.count, body, raw))
        self.buffer_bytes[phase] += size
        self.count += 1
        if len(self.buffers[phase]) >= 1024:
            self._flush(phase)

    def _flush(self, phase: int) -> None:
        rows = self.buffers[phase]
        if not rows:
            return
        self.writers[phase].write_batch(
            pa.RecordBatch.from_arrays(
                [
                    pa.array([row[0] for row in rows], type=pa.int64()),
                    pa.array([row[1] for row in rows], type=pa.large_string()),
                    pa.array([row[2] for row in rows], type=pa.binary()),
                ],
                schema=_SCHEMA,
            )
        )
        rows.clear()
        self.buffer_bytes[phase] = 0

    def seal(self) -> None:
        if self.sealed:
            return
        errors: list[BaseException] = []
        for phase, writer in self.writers.items():
            try:
                self._flush(phase)
            except BaseException as error:
                errors.append(error)
            try:
                writer.close()
            except BaseException as error:
                errors.append(error)
        self.sealed = True
        if errors:
            raise BaseExceptionGroup("reconciliation writer settlement failed", errors)

    def extend(self, values: Iterable[Any]) -> None:
        for value in values:
            self.append(value)

    def __iter__(self) -> Iterator[Any]:
        self.seal()
        # Stable phase partition replaces the materialized A/B-before-C sort.
        # Per-phase append order is the original observation order.
        for phase in sorted(self.paths):
            with pa.memory_map(str(self.paths[phase]), "r") as source:
                reader = pa.ipc.open_file(source)
                for number in range(reader.num_record_batches):
                    batch = reader.get_batch(number)
                    for index in range(batch.num_rows):
                        value = json.loads(batch.column(1)[index].as_py())
                        if self.name == "mapped_inputs":
                            value = (value[0], value[1], batch.column(2)[index].as_py())
                        yield value

    def __len__(self) -> int:
        return self.count

    def sort(self, *, key) -> None:
        if self.name != "mapped_inputs":
            raise ValueError("only recognition phase ordering is supported")
        self.seal()


class ReconciliationJournal:
    def __init__(self, path: Path):
        path.mkdir(parents=True, exist_ok=False)
        self.directory = path
        self.rows: dict[str, _Rows] = {}

    def collection(self, name: str) -> _Rows:
        if name not in _NAMES:
            raise ValueError("unknown reconciliation collection")
        if name not in self.rows:
            self.rows[name] = _Rows(self, name)
        return self.rows[name]

    def seal(self) -> None:
        errors: list[BaseException] = []
        for rows in self.rows.values():
            try:
                rows.seal()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise BaseExceptionGroup("reconciliation journal settlement failed", errors)

    def close(self) -> None:
        self.seal()


class ReconciledPdfStream:
    """Own graph and journal until companion consumers finish or explicitly close."""

    def __init__(self, document: Any, journal: ReconciliationJournal, health: Mapping[str, Any]):
        self.document, self.journal, self.health = document, journal, dict(health)
        self.closed = False

    def iter_companions(self) -> Iterator[tuple[str, dict[str, Any]]]:
        if self.closed:
            raise ValueError("reconciliation replay is closed")
        for family in _PUBLIC:
            for row in self.journal.collection(family):
                yield family, row
        yield "health", self.health

    def close(self) -> None:
        if not self.closed:
            self.journal.close()
            self.closed = True

    def __enter__(self) -> ReconciledPdfStream:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


_OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("input_key", pa.string(), nullable=False),
        pa.field("pin_json", pa.string(), nullable=False),
        pa.field("observation_json", pa.large_string(), nullable=False),
        pa.field("raw", pa.binary(), nullable=False),
    ],
    metadata={"profile": "pdf-recognition-replay-v1"},
)


def write_recognition_replay(
    path: Path,
    observations: Iterable[tuple[Mapping[str, Any], Mapping[str, Any], bytes]],
) -> None:
    """Write bounded recognition input replay; callers own its immutable custody."""
    with path.open("xb") as output, pa.ipc.new_file(output, _OBSERVATION_SCHEMA) as writer:
        rows: list[tuple[str, str, bytes]] = []
        retained = 0

        def flush() -> None:
            if rows:
                writer.write_batch(
                    pa.RecordBatch.from_arrays(
                        [
                            pa.array([row[0] for row in rows]),
                            pa.array([row[0] for row in rows]),
                            pa.array([row[1] for row in rows], type=pa.large_string()),
                            pa.array([row[2] for row in rows], type=pa.binary()),
                        ],
                        schema=_OBSERVATION_SCHEMA,
                    )
                )
                rows.clear()

        for pin, observation, raw in observations:
            key = json.dumps(
                dict(pin),
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            body = json.dumps(
                dict(observation), ensure_ascii=False, allow_nan=False, separators=(",", ":")
            )
            size = len(key.encode()) + len(body.encode()) + len(raw)
            if rows and (retained + size > 8 * 1024**2 or len(rows) >= 1024):
                flush()
                retained = 0
            rows.append((key, body, raw))
            retained += size
        flush()


def iter_recognition_replay(
    path: Path,
) -> Generator[tuple[Mapping[str, Any], Mapping[str, Any], bytes]]:
    """Canonical pin order using an external SQL sort over Arrow, not Python lists."""
    with pa.memory_map(str(path), "r") as source:
        file = pa.ipc.open_file(source)
        if not file.schema.equals(_OBSERVATION_SCHEMA, check_metadata=True):
            raise ValueError("recognition replay schema differs from its contract")
        reader = pa.RecordBatchReader.from_batches(
            file.schema, (file.get_batch(i) for i in range(file.num_record_batches))
        )
        connection = duckdb.connect(
            config={
                "memory_limit": "2GB",
                "temp_directory": str(path.parent / "sort-scratch"),
                "threads": 1,
            }
        )
        try:
            connection.register("observations", reader)
            result = connection.sql(
                "SELECT input_key,pin_json,observation_json,raw FROM observations "
                "ORDER BY input_key"
            ).to_arrow_reader(batch_size=1024)
            previous: str | None = None
            try:
                for batch in result:
                    for i in range(batch.num_rows):
                        key = batch.column(0)[i].as_py()
                        if previous == key:
                            raise ValueError("duplicate qualified recognition input")
                        previous = key
                        yield (
                            json.loads(batch.column(1)[i].as_py()),
                            json.loads(batch.column(2)[i].as_py()),
                            batch.column(3)[i].as_py(),
                        )
            finally:
                result.close()
        finally:
            reader.close()
            connection.close()


def reconcile_pdf_stream(
    document: Any,
    structural_pin: Mapping[str, Any],
    observations: Iterable[tuple[Mapping[str, Any], Mapping[str, Any], bytes]],
    artifact_digest: str,
    *,
    directory: Path,
    policy: Mapping[str, Any] | None = None,
    context: Any = None,
) -> ReconciledPdfStream:
    """Mutate one private native graph and retain companions incrementally.

    ``document`` must be owned privately: callers cannot reuse a cited/admitted
    mutable instance. Raw observations are consumed once into phase-partitioned Arrow replay,
    preserving the existing A-before-specialized-C policy without retaining input
    bodies or all companion dictionaries in memory.
    """
    journal = ReconciliationJournal(directory / "reconciliation")
    ordered = None
    try:
        replay = journal.directory / "observations.arrow"
        write_recognition_replay(replay, observations)
        ordered = iter_recognition_replay(replay)
        selected = _select_pdf_integration(
            {"artifact_digest": artifact_digest},
            structural_pin,
            ordered,
            b"",
            b"",
            b"",
            policy=policy,
            context=context,
            native_document=document,
            journal=journal,
        )
        ordered.close()
        assert isinstance(selected, _PrivateSelection)
        journal.seal()
        return ReconciledPdfStream(selected.document, journal, selected.health)
    except BaseException as error:
        # Keep prior evidence in the authenticated owner directory, never expose
        # an interrupted journal as a completed stream.
        try:
            if ordered is not None:
                ordered.close()
            journal.close()
        except BaseException as cleanup:
            error.add_note(f"journal settlement also failed: {cleanup!r}")
        raise


def read_observation_replay(replay: Any):
    """Verify parent-owned input bytes before opening the typed recognition replay."""
    replay.verify()
    yield from iter_recognition_replay(replay.path)


def write_companion_artifacts(
    result: ReconciledPdfStream,
    root: Path,
    *,
    build_id: str,
    on_batch: Any = None,
):
    """Emit exact per-family JSONL through the modeled private artifact-part route."""
    import os
    from hashlib import file_digest, sha256

    from corpus_structure.semantic.pdf_record_identity import IdentityFold, emit_parts
    from corpus_structure.semantic.pdf_staging import (
        MAX_BATCH_BYTES,
        MAX_BATCH_ROWS,
        companion_profile,
        stage_schema,
    )

    from .pdf_stream_types import PdfReplayRef

    root.mkdir(parents=True, exist_ok=False)
    files: list[PdfReplayRef] = []
    pending: list[dict[str, Any]] = []
    pending_bytes = 0

    def flush(family: str) -> None:
        nonlocal pending_bytes
        if not pending:
            return
        batch = pa.RecordBatch.from_pylist(pending, schema=stage_schema(family))
        if batch.nbytes > MAX_BATCH_BYTES:
            raise ValueError("companion replay exceeds staged batch limit")
        path = root / f"{len(files):08d}-{family}.arrow"
        temporary = path.with_suffix(".tmp")
        with temporary.open("xb") as output:
            with pa.ipc.new_file(output, batch.schema) as writer:
                writer.write_batch(batch)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
        with path.open("rb") as stream:
            digest = file_digest(stream, "sha256").hexdigest()
        replay = PdfReplayRef(path, digest, path.stat().st_size, family, batch.num_rows)
        if on_batch is not None:
            on_batch(replay)
        files.append(replay)
        pending.clear()
        pending_bytes = 0

    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    for family in (*_PUBLIC, "health"):
        if result.closed:
            raise ValueError("reconciliation replay is closed")
        rows = (result.health,) if family == "health" else result.journal.collection(family)

        def chunks(rows=rows):
            for row in rows:
                for text in encoder.iterencode(row):
                    for offset in range(0, len(text), 16384):
                        yield text[offset : offset + 16384].encode("utf-8")
                yield b"\n"

        stream_id = "companion:" + family
        common = {"product_id": build_id, "revision_id": build_id, "stream_id": stream_id}
        digest = sha256()
        folded = IdentityFold("bytes")
        for part in emit_parts(stream_id, chunks()):
            if pending and (
                pending_bytes + part.byte_length + 512 > MAX_BATCH_BYTES // 2
                or len(pending) >= MAX_BATCH_ROWS
            ):
                flush("artifact_part")
            pending.append(
                {
                    **common,
                    "ordinal": part.ordinal,
                    "byte_offset": part.offset,
                    "byte_length": part.byte_length,
                    "body": part.body,
                    "sha256_digest": part.sha256_digest,
                }
            )
            pending_bytes += part.byte_length + 512
            digest.update(part.body)
            folded.add(part.body)
        flush("artifact_part")
        pending.append(
            {
                **common,
                "byte_length": folded.byte_length,
                "serialization_sha256": digest.hexdigest(),
                "byte_root": folded.digest().hex(),
                "encoding_profile": companion_profile(family),
            }
        )
        flush("artifact_stream")
    return tuple(files)
