"""Exact same-session selected result export with disk-backed witness deduplication."""

from __future__ import annotations

from contextlib import contextmanager
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import Column, LargeBinary, MetaData, Table, Text, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.demand_results import stream_demand_result, stream_selected_support
from corpus_structure.semantic.sqlite_scratch import open_scratch

from .demand_export_manifest import checked_export_manifest, decode_export_manifest

_SPOOL = MetaData()
_RECORDS = Table(
    "records",
    _SPOOL,
    Column("key", Text, primary_key=True),
    Column("relation", Text, nullable=False),
    Column("payload", LargeBinary, nullable=False),
)

_EXECUTION_JSON_FIELDS = {"producer", "selected_completion", "cpu_receipt"}
_EXECUTION_INTEGER_FIELDS = {"output_position", "member_ordinal", "cohort_size"}


def _pack(row):
    binary = [key for key, value in row.items() if isinstance(value, (bytes, memoryview))]
    return dict(
        binary=binary,
        values={key: bytes(value).hex() if key in binary else value for key, value in row.items()},
    )


def _unpack(row):
    return {
        key: bytes.fromhex(value) if key in row["binary"] else value
        for key, value in row["values"].items()
    }


def _checksum(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def _relation_schema(relation, names, cut_id):
    """Physical rows and the explicit virtual authority form retain typed export columns."""
    from typing import get_args

    import pyarrow as pa

    from corpus_structure.semantic.arrow_types import sql_arrow_type
    from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf
    from corpus_structure.semantic.execution_evidence_leaf import NativeExecutionEvidenceLeaf
    from corpus_structure.semantic.metadata import table

    if relation == "ops.data_authority_leaf":
        if names != set(NativeAuthorityLeaf.model_fields):
            raise ValueError("authority export differs from its closed disclosure fields")
        columns = ()
        fields = [
            pa.field(name, pa.string(), nullable=type(None) in get_args(field.annotation))
            for name, field in NativeAuthorityLeaf.model_fields.items()
        ]
    elif relation == "ops.data_execution_evidence_leaf":
        if names != set(NativeExecutionEvidenceLeaf.model_fields):
            raise ValueError("execution export differs from its closed disclosure fields")
        columns = ()
        fields = [
            pa.field(
                name,
                pa.int64() if name in _EXECUTION_INTEGER_FIELDS else pa.string(),
                nullable=type(None) in get_args(field.annotation),
            )
            for name, field in NativeExecutionEvidenceLeaf.model_fields.items()
        ]
    else:
        columns = tuple(column for column in table(relation).c if column.name in names)
        fields = [
            pa.field(column.name, sql_arrow_type(column.type), nullable=column.nullable)
            for column in columns
        ]
    return pa.schema(
        fields,
        metadata={
            b"cs.cut": cut_id.encode(),
            b"cs.relation": relation.encode(),
            b"cs.json": b"exact canonical JSON; tagged semantic bodies retain their exact value kinds",
        },
    ), columns


def _capture_release(connection, release_id):
    from sqlalchemy import select

    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.metadata import table

    release, inputs, artifacts = (
        table(name) for name in ("sem.release", "sem.input", "sem.artifact")
    )
    row = dict(
        connection.execute(
            select(
                release.c.release_id,
                release.c.profile,
                release.c.content_digest,
                release.c.prepared_bytes,
                release.c.manifest_bytes,
            ).where(release.c.release_id == release_id)
        )
        .mappings()
        .one()
    )
    input_rows = [
        dict(item)
        for item in connection.execute(
            select(inputs).where(inputs.c.release_id == release_id)
        ).mappings()
    ]
    artifact_rows = [
        dict(item)
        for item in connection.execute(
            select(artifacts).where(artifacts.c.release_id == release_id)
        ).mappings()
    ]
    prepared = open_release_parts(release_id, row, input_rows, artifact_rows)
    return prepared, dict(
        row=_pack(row),
        inputs=[_pack(item) for item in input_rows],
        artifacts=[_pack(item) for item in artifact_rows],
    )


def export_demand_result(
    connection,
    demand_id,
    *,
    project_id,
    destination: Path,
    format="parquet",
    page_rows=100,
    page_bytes=8388608,
    scope=None,
    read_id=None,
    expected_cut=None,
):
    """Acquire and stream every page before releasing native read/trust ownership.

    Parquet conversion consumes the same-session native rows already read under
    their pins. There is no second database connection or imported snapshot.
    """
    from corpus_structure.semantic.data_operation_wire import wire_contracts
    from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release

    if format not in {"jsonl", "parquet"}:
        raise ValueError("selected export encoding must be jsonl or parquet")
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        TemporaryDirectory(prefix=".demand-export-", dir=destination.parent) as scratch,
        open_scratch(Path(scratch) / "closure.sqlite") as spool,
    ):
        root = Path(scratch) / "export"
        root.mkdir()
        _SPOOL.create_all(spool)
        files, pages, releases, runtimes = {}, [], set(), set()
        source_digests = set()
        cut = None

        def write(name, content):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            files[name] = dict(sha256=sha256(content).hexdigest(), bytes=len(content))

        for ordinal, page in enumerate(
            stream_demand_result(
                connection,
                demand_id,
                project_id=project_id,
                limit=page_rows,
                max_bytes=page_bytes,
                scope=scope,
                read_id=read_id,
                expected_cut=expected_cut,
            )
        ):
            cut = page.cut
            release = cut.record["release_id"]
            releases.add(release)
            runtimes.add((release, cut.record["runtime_id"]))
            name = f"pages/{ordinal:08}.json"
            write(name, page.content)
            pages.append(name)
        if cut is None:
            raise ValueError("native result did not produce its empty frontier page")
        for record in stream_selected_support(connection, page, whole_read=True):
            # Current validity explanations belong to live trust inspection.
            if record["relation"] == "ops.data_support_explanation":
                continue
            payload = json_bytes(record)
            previous = spool.execute(
                select(_RECORDS.c.payload).where(_RECORDS.c.key == record["key"])
            ).fetchone()
            if previous is not None and previous[0] != payload:
                raise ValueError("same selected witness key acquired different exact bytes")
            spool.execute(
                sqlite_insert(_RECORDS)
                .values(key=record["key"], relation=record["relation"], payload=payload)
                .on_conflict_do_nothing(index_elements=[_RECORDS.c.key])
            )
            if record["relation"] == "ops.original_source_admission":
                reference = record["record"]["reference"]
                if reference.get("kind") == "original-document":
                    source_digests.add(reference["content_hash"])
            if (
                record["relation"] == "kb.data_product"
                and record["record"]["artifact_digest"] is not None
            ):
                source_digests.add(record["record"]["artifact_digest"])
            if record["relation"] in {
                "ops.data_derivation",
                "ops.data_authority_leaf",
                "ops.data_execution_evidence_leaf",
            }:
                producing = record["record"]
                releases.add(producing["release_id"])
                runtimes.add((producing["release_id"], producing["runtime_id"]))
        source_files = {}
        from sqlalchemy import func

        from corpus_structure.semantic.metadata import table

        artifacts = table("kb.source_artifact")
        for digest in sorted(source_digests):
            name = "source-artifacts/" + digest + ".bin"
            path = root / name
            path.parent.mkdir(exist_ok=True)
            size = connection.scalar(
                select(func.octet_length(artifacts.c.content)).where(
                    artifacts.c.artifact_digest == digest
                )
            )
            if type(size) is not int:
                raise ValueError("selected original source artifact is unavailable")
            with path.open("wb") as stream:
                for start in range(0, size, 1024 * 1024):
                    chunk = connection.scalar(
                        select(
                            func.substring(
                                artifacts.c.content, start + 1, min(size - start, 1024 * 1024)
                            )
                        ).where(artifacts.c.artifact_digest == digest)
                    )
                    if not isinstance(chunk, bytes):
                        raise ValueError("selected source artifact chunk is unavailable")
                    stream.write(chunk)
            if _checksum(path) != digest:
                raise ValueError("selected original source bytes differ from their identity")
            files[name] = dict(sha256=digest, bytes=size)
            source_files[digest] = name
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
            write(
                name,
                json_bytes(
                    dict(
                        release_id=release,
                        runtime_id=runtime,
                        manifest=acquired.manifest.hex(),
                        archive=acquired.archive.hex(),
                    )
                ),
            )
            runtime_files.append(name)
        # The read protocol belongs to the acquiring reader, independently of each
        # historical producer's release and exact archived body/kind contracts.
        write(
            "reader-contract.json",
            json_bytes(wire_contracts()["read_demand_result"]["output"]),
        )
        from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf

        write("authority-contract.json", json_bytes(NativeAuthorityLeaf.model_json_schema()))
        from corpus_structure.semantic.execution_evidence_leaf import (
            NativeExecutionEvidenceLeaf,
            execution_evidence_leaf_schema,
        )

        write("execution-evidence-contract.json", json_bytes(execution_evidence_leaf_schema()))
        closure_path = root / "closure.jsonl"
        with closure_path.open("wb") as output:
            for (payload,) in spool.execute(select(_RECORDS.c.payload).order_by(_RECORDS.c.key)):
                output.write(payload + b"\n")
        files[closure_path.name] = dict(
            sha256=_checksum(closure_path), bytes=closure_path.stat().st_size
        )
        relations = {}
        if format == "parquet":
            from datetime import datetime
            from itertools import batched

            import pyarrow as pa
            import pyarrow.parquet as pq
            from sqlalchemy import DateTime
            from sqlalchemy.dialects.postgresql import JSONB

            for (relation,) in spool.execute(
                select(_RECORDS.c.relation).distinct().order_by(_RECORDS.c.relation)
            ):
                authority = relation == "ops.data_authority_leaf"
                execution = relation == "ops.data_execution_evidence_leaf"
                first = spool.execute(
                    select(_RECORDS.c.payload)
                    .where(_RECORDS.c.relation == relation)
                    .order_by(_RECORDS.c.key)
                    .limit(1)
                ).scalar_one()
                names = set(wire_json_loads(first)["record"])
                schema, columns = _relation_schema(relation, names, cut.identity)
                name = relation.replace(".", "_") + ".parquet"
                count = 0
                with pq.ParquetWriter(root / name, schema) as writer:
                    rows = spool.execute(
                        select(_RECORDS.c.payload)
                        .where(_RECORDS.c.relation == relation)
                        .order_by(_RECORDS.c.key)
                    )
                    for batch in batched(rows, 64, strict=False):
                        values = []
                        for (payload,) in batch:
                            record = wire_json_loads(payload)["record"]
                            if authority:
                                values.append(
                                    NativeAuthorityLeaf.model_validate(record).model_dump(
                                        mode="json"
                                    )
                                )
                                continue
                            if execution:
                                checked = NativeExecutionEvidenceLeaf.model_validate_json(
                                    json_bytes(record)
                                ).model_dump(mode="json")
                                values.append(
                                    {
                                        name: json_bytes(value).decode()
                                        if name in _EXECUTION_JSON_FIELDS
                                        else value
                                        for name, value in checked.items()
                                    }
                                )
                                continue
                            values.append(
                                {
                                    column.name: json_bytes(record[column.name]).decode()
                                    if isinstance(column.type, JSONB)
                                    and record[column.name] is not None
                                    else datetime.fromisoformat(record[column.name])
                                    if isinstance(column.type, DateTime)
                                    and record[column.name] is not None
                                    else record[column.name]
                                    for column in columns
                                }
                            )
                        writer.write_batch(pa.RecordBatch.from_pylist(values, schema=schema))
                        count += len(values)
                files[name] = dict(
                    sha256=_checksum(root / name), bytes=(root / name).stat().st_size
                )
                relations[relation] = dict(file=name, rows=count)
        support_disclosure = (
            "bounded"
            if spool.execute(
                select(
                    select(_RECORDS.c.key)
                    .where(_RECORDS.c.relation == "ops.data_authority_leaf")
                    .exists()
                )
            ).scalar_one()
            else "complete"
        )
        execution_disclosure = (
            "bounded"
            if spool.execute(
                select(
                    select(_RECORDS.c.key)
                    .where(_RECORDS.c.relation == "ops.data_execution_evidence_leaf")
                    .exists()
                )
            ).scalar_one()
            else "complete"
        )
        manifest = dict(
            format="demand-result-export-v3",
            encoding=format,
            cut_id=cut.identity,
            cut=cut.record,
            pages=pages,
            closure="closure.jsonl",
            reader_contract="reader-contract.json",
            authority_contract="authority-contract.json",
            execution_evidence_contract="execution-evidence-contract.json",
            support_disclosure=support_disclosure,
            execution_evidence_disclosure=execution_disclosure,
            releases=release_files,
            runtimes=runtime_files,
            source_artifacts=source_files,
            relations=relations,
            files=files,
            trust="selected historical acquisition; current trust requires native reassessment",
        )
        manifest = checked_export_manifest(manifest)
        manifest_bytes = json_bytes(manifest)
        (root / "manifest.json").write_bytes(manifest_bytes)
        root.rename(destination)
        return dict(manifest, manifest_digest=sha256(manifest_bytes).hexdigest())


@contextmanager
def verified_demand_export(root: Path, *, manifest_digest: str):
    """Own an authenticated archive and exact witness index for detached consumers.

    Verification establishes captured custody only; it acquires no current native trust.
    """
    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.data_operation_runtime import (
        RuntimeBinding,
        validate_data_operation_runtime,
    )
    from corpus_structure.semantic.demand_results import verify_detached_result

    manifest_bytes = (root / "manifest.json").read_bytes()
    if sha256(manifest_bytes).hexdigest() != manifest_digest:
        raise ValueError("export manifest differs from the explicit trusted digest")
    manifest = decode_export_manifest(manifest_bytes)
    for name, descriptor in manifest["files"].items():
        path = root / name
        if (
            not path.resolve().is_relative_to(root.resolve())
            or path.stat().st_size != descriptor["bytes"]
            or _checksum(path) != descriptor["sha256"]
        ):
            raise ValueError("detached file differs from its pinned manifest: " + name)
    prepared, kinds, definitions, models = {}, {}, {}, {}
    for release_id, name in manifest["releases"].items():
        captured = wire_json_loads((root / name).read_bytes())
        acquired = open_release_parts(
            release_id,
            _unpack(captured["row"]),
            [_unpack(row) for row in captured["inputs"]],
            [_unpack(row) for row in captured["artifacts"]],
        )
        prepared[release_id] = acquired
        from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
        from corpus_structure.semantic.native_definition_projection import (
            read_native_definition_projection,
        )

        models[release_id] = bound_data_operation_model(acquired)
        projection = read_native_definition_projection(acquired, model=models[release_id])
        parameters = {
            operation.semantic_id: operation.parameters
            for operation in models[release_id].operations
        }
        for operation in projection["operations"]:
            definitions[release_id, operation["operation_id"]] = dict(
                operation,
                release_id=release_id,
                parameter_definitions=wire_json_loads(parameters[operation["operation_id"]]),
            )
        for kind in projection["kinds"]:
            if kind["kind_contract"] in kinds and kinds[kind["kind_contract"]] != kind:
                raise ValueError("captured releases disagree on nominal kind meaning")
            kinds[kind["kind_contract"]] = kind
    runtime_ids = set()
    for digest, name in manifest["source_artifacts"].items():
        if _checksum(root / name) != digest:
            raise ValueError("detached original source bytes differ from their content identity")
    for name in manifest["runtimes"]:
        captured = wire_json_loads((root / name).read_bytes())
        binding = RuntimeBinding(
            captured["release_id"],
            captured["runtime_id"],
            bytes.fromhex(captured["manifest"]),
            bytes.fromhex(captured["archive"]),
        )
        validate_data_operation_runtime(binding, prepared[binding.release_id])
        runtime_ids.add((binding.release_id, binding.runtime_id))
    wire_schema = wire_json_loads((root / manifest["reader_contract"]).read_bytes())
    authority_schema = wire_json_loads((root / manifest["authority_contract"]).read_bytes())
    execution_schema = wire_json_loads(
        (root / manifest["execution_evidence_contract"]).read_bytes()
    )
    with TemporaryDirectory(prefix="demand-verify-") as scratch:
        index = SelectedRecordIndex(Path(scratch) / "closure.sqlite")
        try:
            with (root / manifest["closure"]).open("rb") as stream:
                for line in stream:
                    index.append(line.rstrip(b"\n"))
            actual_disclosure = (
                "bounded"
                if next(index.rows("ops.data_authority_leaf"), None) is not None
                else "complete"
            )
            if manifest["support_disclosure"] != actual_disclosure:
                raise ValueError("detached manifest misstates its protected support disclosure")
            actual_execution = (
                "bounded"
                if next(index.rows("ops.data_execution_evidence_leaf"), None) is not None
                else "complete"
            )
            if manifest["execution_evidence_disclosure"] != actual_execution:
                raise ValueError("detached manifest misstates its physical execution disclosure")
            for ordinal, name in enumerate(manifest["pages"]):
                page = verify_detached_result(
                    wire_json_loads((root / name).read_bytes()),
                    index=index,
                    wire_schema=wire_schema,
                    kinds=kinds,
                    definitions=definitions,
                    models=models,
                    runtimes=runtime_ids,
                    source_artifacts=manifest["source_artifacts"],
                    authority_schema=authority_schema,
                    execution_evidence_schema=execution_schema,
                    validate_closure=ordinal == 0,
                )
                if page.cut.identity != manifest["cut_id"]:
                    raise ValueError("detached page belongs to another selected cut")
                index.append_page(page.record)
                pins = page.cut.record
                if (pins["release_id"], pins["runtime_id"]) not in runtime_ids:
                    raise ValueError("detached selected runtime archive is missing")
                effective = next(
                    item
                    for item in prepared[pins["release_id"]].artifacts
                    if item.kind == "data_operations.json"
                )
                if pins["selection"]["model"] != effective.digest:
                    raise ValueError(
                        "detached demand selection differs from captured effective model"
                    )
            yield manifest, prepared, models, index
        finally:
            index.close()


def verify_demand_export(root: Path, *, manifest_digest: str):
    """Verify a detached export relative to its explicitly trusted manifest digest."""
    with verified_demand_export(root, manifest_digest=manifest_digest) as (manifest, _, _, _):
        return dict(
            outcome="passed",
            cut_id=manifest["cut_id"],
            pages=len(manifest["pages"]),
            current_trust="not_assessed",
            support_disclosure=manifest["support_disclosure"],
            protected_dependencies="undisclosed"
            if manifest["support_disclosure"] == "bounded"
            else "not_encountered",
            execution_evidence_disclosure=manifest["execution_evidence_disclosure"],
            physical_cpu_cohort="undisclosed"
            if manifest["execution_evidence_disclosure"] == "bounded"
            else "not_encountered",
            whole_cpu_reply_verification="native-member-assertion-only"
            if manifest["execution_evidence_disclosure"] == "bounded"
            else "not_encountered",
            inference="not_run",
        )
