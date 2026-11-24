"""Exact same-session selected result export and authenticated typed replay."""

from __future__ import annotations

from contextlib import contextmanager
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import DateTime, select
from sqlalchemy.dialects.postgresql import BYTEA, JSONB

from corpus_structure.semantic.data_operation_json import (
    finite_json_loads,
    json_bytes,
    native_json_loads,
    wire_json_loads,
)
from corpus_structure.semantic.demand_results import stream_demand_result, stream_selected_archive
from corpus_structure.semantic.selected_support_contract import (
    SUPPORT_EXTENSION,
    SelectedSupportReader,
    omitted_support_fields,
)

from .archive_custody import acquire_demand_archive, publish_archive_directory
from .demand_export_manifest import (
    PublishedDemandExport,
    checked_export_manifest,
    decode_export_manifest,
)
from .selected_archive_relations import (
    ARCHIVE_KEY,
    FRONTIER_SCHEMA,
    ArchivedSelectedRelations,
    ChargedArchivePopulations,
    append_frontier_page,
    seal_frontier,
    with_archive_key,
    write_support_fragments,
)

_EXECUTION_JSON_FIELDS = {"producer", "selected_completion", "cpu_receipt"}
_EXECUTION_INTEGER_FIELDS = {"output_position", "member_ordinal", "cohort_size"}
_PROOF_RELATIONS = ("sem.data_rule", "kb.data_validity", "kb.data_validity_establishment")


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
        columns = tuple(
            column
            for column in table(relation).c
            if column.name not in omitted_support_fields(relation)
        )
        if names != {column.name for column in columns}:
            raise ValueError("selected export columns differ from the captured relation shape")
        fields = [
            pa.field(column.name, sql_arrow_type(column.type), nullable=column.nullable)
            for column in columns
        ]
    schema = pa.schema(
        fields,
        metadata={
            b"cs.cut": cut_id.encode(),
            b"cs.relation": relation.encode(),
            b"cs.json": b"exact canonical JSON; tagged semantic bodies retain their exact value kinds",
        },
    )
    encodings = (
        {
            name: "json"
            if name in _EXECUTION_JSON_FIELDS and relation == "ops.data_execution_evidence_leaf"
            else "native"
            for name in names
        }
        if not columns
        else {
            column.name: "json"
            if isinstance(column.type, JSONB)
            else "timestamp"
            if isinstance(column.type, DateTime)
            else "binary"
            if isinstance(column.type, BYTEA)
            else "native"
            for column in columns
        }
    )
    return with_archive_key(schema), encodings


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
) -> PublishedDemandExport:
    """Acquire and stream every page before releasing native read/trust ownership.

    Parquet conversion consumes the same-session native rows already read under
    their pins. There is no second database connection or imported snapshot.
    """
    from corpus_structure.semantic.data_operation_wire import wire_contextual_fields, wire_contracts
    from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_release
    from corpus_structure.semantic.selected_population_archive import write_population_fragments

    if format != "parquet":
        raise ValueError("new selected exports require Parquet")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".demand-export-", dir=destination.parent) as scratch:
        root = Path(scratch) / "export"
        root.mkdir()
        files, relations, pages, releases, runtimes = {}, {}, [], set(), set()
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

        def capture_populations(handle):
            for relation, name, count in write_population_fragments(
                connection, handle, root, cut.identity
            ):
                path = root / name
                files[name] = dict(sha256=_checksum(path), bytes=path.stat().st_size)
                relations[relation] = dict(file=name, rows=count)

        support_reader = SelectedSupportReader()
        support_contracts = {}

        def codec(relation):
            contract = support_reader.capture((relation,))[relation]
            schema, encodings = _relation_schema(
                relation, set(contract["schema"]["properties"]), cut.identity
            )
            contract["arrow_schema"] = schema.serialize().to_pybytes().hex()
            contract["encodings"] = encodings
            support_contracts[relation] = contract
            return schema, encodings

        def selected_records():
            for record in stream_selected_archive(
                connection, cut, max_bytes=page_bytes, consume_populations=capture_populations
            ):
                relation = record["relation"]
                body = record["record"]
                if relation == "ops.original_source_admission":
                    reference = body["reference"]
                    if reference.get("kind") == "original-document":
                        source_digests.add(reference["content_hash"])
                if relation == "kb.data_product" and body["artifact_digest"] is not None:
                    source_digests.add(body["artifact_digest"])
                if relation in {
                    "ops.data_derivation",
                    "ops.data_authority_leaf",
                    "ops.data_execution_evidence_leaf",
                }:
                    releases.add(body["release_id"])
                    runtimes.add((body["release_id"], body["runtime_id"]))
                yield record

        for relation, path, count in write_support_fragments(
            root, selected_records(), codec, batch_bytes=page_bytes
        ):
            files[path.name] = dict(sha256=_checksum(path), bytes=path.stat().st_size)
            relations[relation] = dict(file=path.name, rows=count)
        for relation in _PROOF_RELATIONS:
            if relation in relations:
                continue
            schema, _ = codec(relation)
            name = relation.replace(".", "_") + ".parquet"
            path = root / name
            pq.ParquetWriter(path, schema).close()
            files[name] = dict(sha256=_checksum(path), bytes=path.stat().st_size)
            relations[relation] = dict(file=name, rows=0)
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
        reader_schema = wire_contracts()["read_demand_result"]["output"]
        reader_schema[SUPPORT_EXTENSION] = support_contracts
        reader_schema["x-corpus-contextual-fields"] = list(wire_contextual_fields())
        # The read protocol belongs to the acquiring reader, independently of each
        # historical producer's release and exact archived body/kind contracts.
        write(
            "reader-contract.json",
            json_bytes(reader_schema),
        )
        from corpus_structure.semantic.authority_leaf import NativeAuthorityLeaf

        write("authority-contract.json", json_bytes(NativeAuthorityLeaf.model_json_schema()))
        from corpus_structure.semantic.execution_evidence_leaf import execution_evidence_leaf_schema

        write("execution-evidence-contract.json", json_bytes(execution_evidence_leaf_schema()))
        support_disclosure = "bounded" if "ops.data_authority_leaf" in relations else "complete"
        execution_disclosure = (
            "bounded" if "ops.data_execution_evidence_leaf" in relations else "complete"
        )
        manifest = checked_export_manifest(
            dict(
                format="demand-result-export-v4",
                encoding=format,
                cut_id=cut.identity,
                pages=pages,
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
            ),
            cut=cut,
        )
        manifest_bytes = manifest.to_bytes()
        (root / "manifest.json").write_bytes(manifest_bytes)
        publish_archive_directory(root, destination)
        return PublishedDemandExport(manifest, sha256(manifest_bytes).hexdigest())


@contextmanager
def verified_demand_export(
    root: Path, *, manifest_digest: str, max_graph_bytes=None, max_graph_records=None
):
    """Own an authenticated archive through its lazy scans and exact replay."""
    with (
        acquire_demand_archive(root, manifest_digest, decode_export_manifest) as (owned, manifest),
        _verify_acquired_export(
            owned, manifest, max_graph_bytes=max_graph_bytes, max_graph_records=max_graph_records
        ) as acquired,
    ):
        yield acquired


@contextmanager
def _verify_acquired_export(root, manifest, *, max_graph_bytes, max_graph_records):
    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.data_operation_runtime import (
        RuntimeBinding,
        validate_data_operation_runtime,
    )
    from corpus_structure.semantic.demand_results import verify_detached_result
    from corpus_structure.semantic.selected_population_archive import open_population_fragments

    prepared, kinds, definitions, models = {}, {}, {}, {}
    for release_id, name in manifest.releases.items():
        captured = finite_json_loads((root / name).read_bytes())
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
            stored_kind = {"collections": {}, **kind}
            key = kind["kind_contract"]
            if key in kinds and kinds[key] != stored_kind:
                raise ValueError("captured releases disagree on nominal kind meaning")
            kinds[key] = stored_kind
    runtime_ids = set()
    for digest, name in manifest.source_artifacts.items():
        if manifest.files[name].sha256 != digest:
            raise ValueError("detached original source bytes differ from their content identity")
    for name in manifest.runtimes:
        captured = finite_json_loads((root / name).read_bytes())
        binding = RuntimeBinding(
            captured["release_id"],
            captured["runtime_id"],
            bytes.fromhex(captured["manifest"]),
            bytes.fromhex(captured["archive"]),
        )
        validate_data_operation_runtime(binding, prepared[binding.release_id])
        runtime_ids.add((binding.release_id, binding.runtime_id))
    wire_schema = native_json_loads((root / manifest.reader_contract).read_bytes())
    if SUPPORT_EXTENSION not in wire_schema:
        raise ValueError(
            "detached reader has no captured support interpretation; regenerate export"
        )
    support_reader = SelectedSupportReader(
        wire_schema[SUPPORT_EXTENSION], kinds=kinds, wire_schema=wire_schema
    )
    authority_schema = finite_json_loads((root / manifest.authority_contract).read_bytes())
    execution_schema = finite_json_loads((root / manifest.execution_evidence_contract).read_bytes())
    if (
        max_graph_records is not None
        and sum(relation.rows for relation in manifest.relations.values()) > max_graph_records
    ):
        raise ValueError("detached structural closure exceeds its examined bound")

    with (
        TemporaryDirectory(prefix="demand-verify-") as scratch_name,
        open_population_fragments(root, manifest) as populations,
    ):
        scratch = Path(scratch_name)
        fragments = _support_fragments(root, manifest, wire_schema[SUPPORT_EXTENSION], scratch)
        index = ArchivedSelectedRelations(
            fragments, support_reader, max_bytes=max_graph_bytes, max_records=max_graph_records
        )
        if populations is not None:
            index.population_archive = ChargedArchivePopulations(populations, index.charge)
        index.validate_support()
        _verify_proof_records(index, models)
        actual_disclosure = (
            "bounded"
            if next(index.rows("ops.data_authority_leaf"), None) is not None
            else "complete"
        )
        if manifest.support_disclosure != actual_disclosure:
            raise ValueError("detached manifest misstates its protected support disclosure")
        actual_execution = (
            "bounded"
            if next(index.rows("ops.data_execution_evidence_leaf"), None) is not None
            else "complete"
        )
        if manifest.execution_evidence_disclosure != actual_execution:
            raise ValueError("detached manifest misstates its physical execution disclosure")
        frontier = scratch / "frontier-unordered.parquet"
        after = None
        with pq.ParquetWriter(frontier, FRONTIER_SCHEMA) as writer:
            for ordinal, name in enumerate(manifest.pages):
                page = verify_detached_result(
                    native_json_loads((root / name).read_bytes()),
                    index=index,
                    wire_schema=wire_schema,
                    kinds=kinds,
                    definitions=definitions,
                    models=models,
                    runtimes=runtime_ids,
                    source_artifacts=manifest.source_artifacts,
                    authority_schema=authority_schema,
                    execution_evidence_schema=execution_schema,
                    validate_closure=ordinal == 0,
                )
                if page.cut.content != manifest.cut_selection.content:
                    raise ValueError("detached page belongs to another selected cut")
                record = page.record
                if manifest.closure is None:
                    after = _validate_page_position(
                        record, after, terminal=ordinal == len(manifest.pages) - 1
                    )
                append_frontier_page(writer, record)
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
        ordered_frontier = scratch / "frontier.parquet"
        seal_frontier(frontier, ordered_frontier, charge=index.charge)
        index.population_archive = populations
        index.attach_frontier(ordered_frontier, manifest.cut_selection)
        yield manifest, prepared, models, index


def _validate_page_position(record, previous, *, terminal):
    """Check the archived native frontier before merging it into the detached index."""
    obligations = [row["obligation_id"] for row in record["obligations"]]
    if previous is not None and not obligations:
        raise ValueError("detached native page did not advance its continuation")
    for obligation in obligations:
        if previous is not None and obligation <= previous:
            raise ValueError("detached native pages do not advance in obligation order")
        previous = obligation

    continuation = record["continuation"]
    if terminal:
        if continuation is not None:
            raise ValueError("detached archive ends before its native terminal page")
    elif continuation is None or not obligations or continuation["after"] != obligations[-1]:
        raise ValueError("detached archive has an invalid native page continuation")
    if continuation is not None:
        fields = (
            "demand_id",
            "scope",
            "selection",
            "trust_snapshot",
            "read_id",
            "read_snapshot",
            "frontier_at",
        )
        if any(continuation[name] != record[name] for name in fields) or continuation[
            "view"
        ] != record.get("view", "frontier"):
            raise ValueError("detached archive continuation differs from its native read")
    return previous


def _support_fragments(root, manifest, contracts, scratch):
    from corpus_structure.semantic.selected_population_archive import (
        POPULATION_HEADERS,
        POPULATION_ITEMS,
    )

    def codec(relation):
        contract = contracts[relation]
        if "arrow_schema" not in contract:
            return _relation_schema(
                relation, set(contract["schema"]["properties"]), manifest.cut_id
            )
        schema = pa.ipc.read_schema(pa.BufferReader(bytes.fromhex(contract["arrow_schema"])))
        encodings = dict(contract["encodings"])
        if ARCHIVE_KEY not in schema.names:
            schema = with_archive_key(schema)
        for field in schema:
            if field.name == ARCHIVE_KEY:
                continue
            if pa.types.is_binary(field.type):
                encodings[field.name] = "binary"
            else:
                encodings.setdefault(
                    field.name,
                    "json"
                    if relation == "ops.data_execution_evidence_leaf"
                    and field.name in _EXECUTION_JSON_FIELDS
                    else "native",
                )
        if set(encodings) != set(schema.names) - {ARCHIVE_KEY}:
            raise ValueError("captured support codec differs from its physical schema")
        return schema, encodings

    if manifest.closure is not None:
        # Legacy v3 produced one sorted canonical JSONL stream. Decode the authenticated
        # original into the common typed reader under this invocation's owned scratch.
        with (root / manifest.closure).open("rb") as original:
            return {
                relation: (path, rows, *codec(relation))
                for relation, path, rows in write_support_fragments(
                    scratch,
                    (native_json_loads(line) for line in original),
                    codec,
                    batch_bytes=8 * 1024 * 1024,
                )
            }

    support = manifest.relations.keys() - {POPULATION_HEADERS, POPULATION_ITEMS}
    if support != contracts.keys():
        raise ValueError("selected support files differ from the captured relation contract")
    return {
        relation: (
            root / manifest.relations[relation].file,
            manifest.relations[relation].rows,
            *codec(relation),
        )
        for relation in support
    }


def _verify_proof_records(index, models):
    """Check captured proof identity and visible establishing outputs without replaying a rule."""
    captured_rules = {}
    rules_by_fingerprint = {}
    for row in index.rows("sem.data_rule"):
        release = row["release_id"]
        if release not in models:
            raise ValueError("detached rule lacks its captured release")
        rule = next((rule for rule in models[release].rules if rule.id == row["rule_id"]), None)
        if (
            rule is None
            or rule.kind_contract != row["kind_contract"]
            or rule.fingerprint != row["fingerprint"]
            or native_json_loads(json_bytes(rule.record)) != row["specification"]
        ):
            raise ValueError("detached rule differs from its captured release contract")
        captured_rules[release, rule.kind_contract, rule.fingerprint] = rule
        rules_by_fingerprint[rule.fingerprint] = rule

    conclusions = {
        (row["rule_fingerprint"], row["premise"]) for row in index.rows("kb.data_validity")
    }
    established = set()
    outputs = index.mapping("ops.data_derivation_output", ("derivation_id", "role", "position"))
    episodes = index.mapping("ops.data_derivation", ("id",))
    products = index.mapping("kb.data_product", ("id",))
    for row in index.rows("kb.data_validity_establishment"):
        key = row["rule_fingerprint"], row["premise"]
        output = outputs.get((row["derivation_id"], row["role"], row["position"]))
        episode = episodes.get(row["derivation_id"])
        if (
            key not in conclusions
            or output is None
            or episode is None
            or output["member_id"] is not None
        ):
            raise ValueError("detached proof establishment lacks its selected producing output")
        product = products.get(output["product_id"])
        rule = (
            None
            if product is None
            else captured_rules.get(
                (episode["release_id"], product["kind_contract"], row["rule_fingerprint"])
            )
        )
        if rule is None or rule.checker != "producer":
            raise ValueError("detached proof establishment differs from its captured rule")
        established.add(key)
    for key in conclusions:
        rule = rules_by_fingerprint.get(key[0])
        if rule is None or (rule.checker == "producer" and key not in established):
            raise ValueError("detached proof conclusion lacks its rule or required establishment")


def verify_demand_export(root: Path, *, manifest_digest: str):
    """Verify a detached export relative to its explicitly trusted manifest digest."""
    with verified_demand_export(root, manifest_digest=manifest_digest) as (manifest, _, _, _):
        return dict(
            outcome="passed",
            cut_id=manifest.cut_id,
            pages=len(manifest.pages),
            current_trust="not_assessed",
            support_disclosure=manifest.support_disclosure,
            protected_dependencies="undisclosed"
            if manifest.support_disclosure == "bounded"
            else "not_encountered",
            execution_evidence_disclosure=manifest.execution_evidence_disclosure,
            physical_cpu_cohort="undisclosed"
            if manifest.execution_evidence_disclosure == "bounded"
            else "not_encountered",
            whole_cpu_reply_verification="native-member-assertion-only"
            if manifest.execution_evidence_disclosure == "bounded"
            else "not_encountered",
            inference="not_run",
        )
