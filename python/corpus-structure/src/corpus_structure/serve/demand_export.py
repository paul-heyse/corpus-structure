"""Exact same-session selected result export with disk-backed witness deduplication."""
from __future__ import annotations

from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3

from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.demand_results import stream_demand_result, stream_selected_support


def _pack(row):
    binary = [key for key, value in row.items() if isinstance(value, (bytes, memoryview))]
    return dict(binary=binary, values={key: bytes(value).hex() if key in binary else value for key, value in row.items()})


def _unpack(row):
    return {key: bytes.fromhex(value) if key in row["binary"] else value for key, value in row["values"].items()}


def _checksum(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def _capture_release(connection, release_id):
    from sqlalchemy import select
    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.metadata import table
    release, inputs, artifacts = (table(name) for name in ("sem.release", "sem.input", "sem.artifact"))
    row = dict(connection.execute(select(release.c.release_id, release.c.profile, release.c.content_digest, release.c.prepared_bytes, release.c.manifest_bytes).where(release.c.release_id == release_id)).mappings().one())
    input_rows = [dict(item) for item in connection.execute(select(inputs).where(inputs.c.release_id == release_id)).mappings()]
    artifact_rows = [dict(item) for item in connection.execute(select(artifacts).where(artifacts.c.release_id == release_id)).mappings()]
    prepared = open_release_parts(release_id, row, input_rows, artifact_rows)
    return prepared, dict(row=_pack(row), inputs=[_pack(item) for item in input_rows], artifacts=[_pack(item) for item in artifact_rows])


def export_demand_result(connection, demand_id, *, project_id, destination: Path,
                         format="parquet", page_rows=100, page_bytes=8388608):
    """Acquire and stream every page before releasing native read/trust ownership.

    Parquet conversion consumes the same-session native rows already read under
    their pins. There is no second database connection or imported snapshot.
    """
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources
    from corpus_structure.semantic.data_operation_wire import wire_contracts
    from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release
    if format not in {"jsonl", "parquet"}:
        raise ValueError("selected export encoding must be jsonl or parquet")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".demand-export-", dir=destination.parent) as scratch:
        root = Path(scratch) / "export"
        root.mkdir()
        spool = sqlite3.connect(Path(scratch) / "closure.sqlite")
        spool.execute("CREATE TABLE records (key TEXT PRIMARY KEY, relation TEXT NOT NULL, payload BLOB NOT NULL)")
        files, pages, releases, runtimes = {}, [], set(), set()
        cut = None
        def write(name, content):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            files[name] = dict(sha256=sha256(content).hexdigest(), bytes=len(content))
        for ordinal, page in enumerate(stream_demand_result(connection, demand_id, project_id=project_id, limit=page_rows, max_bytes=page_bytes)):
            cut = page.cut
            release = cut.record["release_id"]
            releases.add(release)
            runtimes.add((release, cut.record["runtime_id"]))
            name = f"pages/{ordinal:08}.json"
            write(name, page.content)
            pages.append(name)
            for record in stream_selected_support(connection, page):
                payload = json_bytes(record)
                previous = spool.execute("SELECT payload FROM records WHERE key=?", (record["key"],)).fetchone()
                if previous is not None and previous[0] != payload:
                    raise ValueError("same selected witness key acquired different exact bytes")
                spool.execute("INSERT OR IGNORE INTO records VALUES (?,?,?)", (record["key"], record["relation"], payload))
                if record["relation"] == "ops.data_derivation":
                    producing = record["record"]
                    releases.add(producing["release_id"])
                    runtimes.add((producing["release_id"], producing["runtime_id"]))
        if cut is None:
            raise ValueError("native result did not produce its empty frontier page")
        release_files, runtime_files = {}, []
        prepared = {}
        for ordinal, release in enumerate(sorted(releases)):
            acquired, captured = _capture_release(connection, release)
            prepared[release] = acquired
            name = f"releases/{ordinal:08}.json"
            write(name, json_bytes(captured))
            release_files[release] = name
        for ordinal, (release, runtime) in enumerate(sorted(runtimes)):
            acquired = runtime_binding_for_release(connection, prepared[release], runtime)
            name = f"runtimes/{ordinal:08}.json"
            write(name, json_bytes(dict(release_id=release, runtime_id=runtime, manifest=acquired.manifest.hex(), archive=acquired.archive.hex())))
            runtime_files.append(name)
        # The read protocol belongs to the acquiring reader, independently of each
        # historical producer's release and exact archived body/kind contracts.
        write("reader-contract.json", json_bytes(wire_contracts(native_protocol_sources())["read_demand_result"]["output"]))
        closure_path = root / "closure.jsonl"
        with closure_path.open("wb") as output:
            for (payload,) in spool.execute("SELECT payload FROM records ORDER BY key"):
                output.write(payload + b"\n")
        files[closure_path.name] = dict(sha256=_checksum(closure_path), bytes=closure_path.stat().st_size)
        relations = {}
        if format == "parquet":
            import pyarrow as pa
            import pyarrow.parquet as pq
            from corpus_structure.semantic.arrow_types import sql_arrow_type
            from corpus_structure.semantic.metadata import table
            from sqlalchemy.dialects.postgresql import JSONB
            from sqlalchemy import DateTime
            from datetime import datetime
            from itertools import batched
            for (relation,) in spool.execute("SELECT DISTINCT relation FROM records ORDER BY relation"):
                native = table(relation)
                first = spool.execute("SELECT payload FROM records WHERE relation=? ORDER BY key LIMIT 1", (relation,)).fetchone()
                names = set(wire_json_loads(first[0])["record"])
                columns = tuple(column for column in native.c if column.name in names)
                schema = pa.schema([pa.field(column.name, sql_arrow_type(column.type), nullable=column.nullable) for column in columns], metadata={b"cs.cut": cut.identity.encode(), b"cs.relation": relation.encode(), b"cs.json": b"exact canonical JSON; tagged semantic bodies retain their exact value kinds"})
                name = relation.replace(".", "_") + ".parquet"
                count = 0
                with pq.ParquetWriter(root / name, schema) as writer:
                    rows = spool.execute("SELECT payload FROM records WHERE relation=? ORDER BY key", (relation,))
                    for batch in batched(rows, 64):
                        values = []
                        for (payload,) in batch:
                            record = wire_json_loads(payload)["record"]
                            values.append({column.name: json_bytes(record[column.name]).decode() if isinstance(column.type, JSONB) and record[column.name] is not None else datetime.fromisoformat(record[column.name]) if isinstance(column.type, DateTime) and record[column.name] is not None else record[column.name] for column in columns})
                        writer.write_batch(pa.RecordBatch.from_pylist(values, schema=schema))
                        count += len(values)
                files[name] = dict(sha256=_checksum(root / name), bytes=(root / name).stat().st_size)
                relations[relation] = dict(file=name, rows=count)
        spool.close()
        manifest = dict(format="demand-result-export-v1", encoding=format, cut_id=cut.identity,
                        cut=cut.record, pages=pages, closure="closure.jsonl",
                        reader_contract="reader-contract.json", releases=release_files,
                        runtimes=runtime_files, relations=relations, files=files,
                        trust="selected historical acquisition; current trust requires native reassessment")
        manifest_bytes = json_bytes(manifest)
        (root / "manifest.json").write_bytes(manifest_bytes)
        root.rename(destination)
        return dict(manifest, manifest_digest=sha256(manifest_bytes).hexdigest())


def verify_demand_export(root: Path, *, manifest_digest: str):
    """Verify a detached export relative to its explicitly trusted manifest digest."""
    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.runtime_bindings import RuntimeBinding, validate_runtime_binding
    from corpus_structure.semantic.demand_results import verify_detached_result
    manifest_bytes = (root / "manifest.json").read_bytes()
    if sha256(manifest_bytes).hexdigest() != manifest_digest:
        raise ValueError("export manifest differs from the explicit trusted digest")
    manifest = wire_json_loads(manifest_bytes)
    if manifest["format"] != "demand-result-export-v1":
        raise ValueError("unsupported selected result export")
    for name, descriptor in manifest["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or path.stat().st_size != descriptor["bytes"] or _checksum(path) != descriptor["sha256"]:
            raise ValueError("detached file differs from its pinned manifest: " + name)
    prepared, kinds = {}, {}
    for release_id, name in manifest["releases"].items():
        captured = wire_json_loads((root / name).read_bytes())
        acquired = open_release_parts(release_id, _unpack(captured["row"]), [_unpack(row) for row in captured["inputs"]], [_unpack(row) for row in captured["artifacts"]])
        prepared[release_id] = acquired
        definitions = next(item for item in acquired.artifacts if item.kind == "data_operation_native_definitions.json")
        for kind in wire_json_loads(definitions.content)["kinds"]:
            if kind["kind_contract"] in kinds and kinds[kind["kind_contract"]] != kind:
                raise ValueError("captured releases disagree on nominal kind meaning")
            kinds[kind["kind_contract"]] = kind
    for name in manifest["runtimes"]:
        captured = wire_json_loads((root / name).read_bytes())
        binding = RuntimeBinding(captured["release_id"], captured["runtime_id"], bytes.fromhex(captured["manifest"]), bytes.fromhex(captured["archive"]))
        validate_runtime_binding(binding, prepared[binding.release_id])
    wire_schema = wire_json_loads((root / manifest["reader_contract"]).read_bytes())
    # The managed export's closure is disk-backed during capture; verification
    # consumes this explicit immutable record stream rather than a live DB query.
    records = tuple(wire_json_loads(line) for line in (root / manifest["closure"]).open("rb"))
    for name in manifest["pages"]:
        page = verify_detached_result(wire_json_loads((root / name).read_bytes()), records=records, wire_schema=wire_schema, kinds=kinds)
        if page.cut.identity != manifest["cut_id"]:
            raise ValueError("detached page belongs to another selected cut")
    return dict(outcome="passed", cut_id=manifest["cut_id"], pages=len(manifest["pages"]), current_trust="not_assessed", inference="not_run")
