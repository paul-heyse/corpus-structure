"""Declared-scope portable review over pinned retained products.

The bundle is a detached reading, not admission or original-document completeness.
Public capture never opens an evaluator connection. Authorized assessment owners may
supply separately captured relations; callers retain responsibility for exposure.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.semantic.capture_storage import LogicalRows
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view, selected_source_views
from corpus_structure.serve.companion_export import _publish_directory
from corpus_structure.serve.contributions import ContributionRequest, _contributions
from corpus_structure.settings import Settings

FORMAT = "progressive-review-bundle-1"
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class ReviewSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    selections: tuple[ContributionRequest, ...] = Field(min_length=1)
    completeness: Literal["selected_source_closure", "inventory"] = "selected_source_closure"
    max_bytes: int = Field(default=134_217_728, strict=True, gt=0)
    max_source_rows: int = Field(default=100_000, strict=True, gt=0)

    @model_validator(mode="after")
    def full_selections(self):
        if any(item.cursor is not None for item in self.selections):
            raise ValueError("review selection cannot begin at a continuation")
        identities = [canonical_bytes(item.selection()) for item in self.selections]
        if len(identities) != len(set(identities)):
            raise ValueError("review selections must be distinct")
        return self


def _json(value: Any) -> Any:
    from pydantic_core import to_jsonable_python

    return json.loads(canonical_bytes(to_jsonable_python(value)))


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def capture_review_relations(conn, selection: ReviewSelection, cancellation: OperationCancellation):
    """One caller-owned snapshot; shared source and report objects captured once.

    Existing inventory admission is bounded before hydration. Source closure has a
    separate cumulative native-read budget and never initializes analytical layout.
    """
    seen_reports: set[int] = set()
    seen_sources: set[int] = set()
    seen_releases: set[str] = set()
    seen_documents: set[int] = set()
    seen_producers: set[int] = set()
    budget = PublishedReadBudget(selection.max_source_rows, selection.max_bytes)
    for index, original in enumerate(selection.selections):
        cancellation.check_active()
        request = original.model_copy(update={"include_details": True})
        page = _contributions(conn, request, paginate=False)
        yield "selections", {"selection_index": index, **page.model_dump(exclude={"items"})}
        session = bind_completed_result(conn, original.run_id)
        if session.binding.release_id not in seen_releases:
            seen_releases.add(session.binding.release_id)
            yield "contracts", {
                "release_id": session.binding.release_id,
                "definitions": [asdict(value) for value in session.prepared.definitions],
                "registry_rows": [{"kind": value.kind, "name": value.name,
                    "body_base64": base64.b64encode(value.body).decode()}
                    for value in session.prepared.registry_rows],
            }
        source_ids: set[int] = set()
        report_ids: set[int] = set()
        for item in page.items:
            yield "inventory", {"selection_index": index, **item}
            row = item["row"]
            if not isinstance(row, dict):
                raise SemanticRefusal("review inventory row must be an object")
            if isinstance(row.get("source_view_id"), int):
                source_ids.add(row["source_view_id"])
            if item["population"] == "report" and isinstance(row.get("origin_task_id"), int):
                report_ids.add(row["origin_task_id"])
        if original.source_view_id is not None:
            source_ids.add(original.source_view_id)
        elif not any((original.method, original.operation_key, original.operation_version,
                      original.contribution_id, original.occurrence_id, original.kind)):
            # Empty source regions still belong to an unfiltered run inventory.
            source_ids.update(ref.id for ref in selected_source_views(conn, original.run_id))
        if selection.completeness == "inventory":
            continue
        permitted = {ref.id for ref in selected_source_views(conn, original.run_id)}
        if not source_ids <= permitted:
            raise SemanticRefusal("review source is outside selected run membership")
        reports = table("ops.task_result")
        task, cfg = table("ops.task"), table("ops.method_config")
        for report_id in sorted(report_ids - seen_reports):
            cancellation.check_active()
            statement = (select(reports.c.body, task.c.input_hash, task.c.method_config_id,
                                cfg.c.params.label("configuration"), cfg.c.config_hash,
                                task.c.run_id.label("origin_run_id"))
                         .join(task, task.c.id == reports.c.task_id)
                         .join(cfg, cfg.c.id == task.c.method_config_id)
                         .where(reports.c.task_id == report_id))
            budget.preflight(conn, statement)
            report = conn.execute(statement).mappings().one_or_none()
            if report is None:
                yield "omissions", {"origin_task_id": report_id,
                                    "reason": "no_retained_report_for_terminal_task"}
                continue
            budget.value(dict(report))
            seen_reports.add(report_id)
            source_ids.update(_source_ids(report["body"]))
            permitted.update(ref.id for ref in selected_source_views(conn, report["origin_run_id"]))
            yield "reports", {"origin_task_id": report_id, **dict(report)}
        if not source_ids <= permitted:
            raise SemanticRefusal("raw report source is outside selected/original run membership")
        for source_id in sorted(source_ids - seen_sources):
            cancellation.check_active()
            source = load_source_view(conn, source_id, analysis=False, read_budget=budget)
            seen_sources.add(source_id)
            producer_id = source.ref.native_product.task_id
            if producer_id not in seen_producers:
                run = table("ops.run")
                statement = (select(task.c.id, task.c.run_id, task.c.release_id,
                                    task.c.input_hash, task.c.packet_hash, task.c.result_digest,
                                    cfg.c.params.label("configuration"), cfg.c.config_hash,
                                    run.c.runtime_id, run.c.dependencies)
                             .join(cfg, cfg.c.id == task.c.method_config_id)
                             .join(run, run.c.id == task.c.run_id)
                             .where(task.c.id == producer_id))
                budget.preflight(conn, statement)
                row = dict(conn.execute(statement).mappings().one())
                budget.value(row)
                seen_producers.add(producer_id)
                yield "source_producers", row
            if source.ref.document_id not in seen_documents:
                document = table("kb.document")
                statement = select(document).where(document.c.id == source.ref.document_id)
                budget.preflight(conn, statement)
                row = dict(conn.execute(statement).mappings().one())
                budget.value(row)
                seen_documents.add(source.ref.document_id)
                yield "documents", row
            yield "sources", {
                "source_view_id": source_id,
                "ref": asdict(source.ref),
                "text": source.text,
                "context": source.context(),
                "source_coverage": "selected_projection_only",
                "original_page_map": "unknown_unless_retained_in_native_items",
            }



def _source_ids(value: Any) -> set[int]:
    if isinstance(value, dict):
        found = {value["source_view_id"]} if type(value.get("source_view_id")) is int else set()
        for item in value.values():
            found.update(_source_ids(item))
        return found
    if isinstance(value, (list, tuple)):
        return set().union(*(_source_ids(item) for item in value)) if value else set()
    return set()


def _validate_source(value: dict[str, Any]) -> None:
    # Reuse the production projection/piece validator rather than a parallel checker.
    from corpus_structure.core.method import SourceViewDraft
    from corpus_structure.semantic.product_reference import ProductReference

    ref, context = value["ref"], value["context"]
    draft = SourceViewDraft(
        key=ref["key"], document_id=ref["document_id"],
        native_product=ProductReference(**ref["native_product"]),
        section_pointer=ref["section_pointer"], membership=ref["membership"],
        text=value["text"], pieces=tuple(context["pieces"]),
        items=tuple(item["self_ref"] for item in context["items"]),
        ancestors=tuple(item["self_ref"] for item in context["ancestors"]),
        health=context["health"], recipe_bytes=b"", analysis_eligible=ref["analysis_eligible"],
    )
    if draft.projection_digest != ref["projection_digest"] or value["source_view_id"] != ref["id"]:
        raise ValueError("review source projection digest differs")


def _schema(selection_digest: str, relation: str) -> pa.Schema:
    return pa.schema([pa.field("row_id", pa.int64(), nullable=False),
                      pa.field("payload_json", pa.string(), nullable=False)],
                     metadata={b"cs.review": FORMAT.encode(),
                               b"cs.selection": selection_digest.encode(),
                               b"cs.relation": relation.encode()})


def write_review_bundle(
    selection: ReviewSelection,
    destination: Path,
    rows: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    cancellation: OperationCancellation | None = None,
) -> dict[str, Any]:
    """Spool an owned row stream and publish only after its generator settles.

    JSON payload columns preserve heterogeneous versioned operation fields exactly;
    the two serializations share one Arrow schema and logical row digest.
    """
    cancellation = cancellation or OperationCancellation()
    cancellation.check_active()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    selection_value = selection.model_dump(mode="json")
    selection_digest = sha256(canonical_bytes(selection_value)).hexdigest()
    with TemporaryDirectory(prefix=".review-", dir=destination.parent) as temporary:
        root = Path(temporary) / "bundle"
        root.mkdir()
        sinks: dict[str, Any] = {}
        raw_bytes = 0
        primary: BaseException | None = None
        try:
            for name, value in rows:
                cancellation.check_active()
                if not _NAME.fullmatch(name):
                    raise ValueError("invalid review relation name")
                if name not in sinks:
                    schema = _schema(selection_digest, name)
                    sinks[name] = (schema, LogicalRows(schema),
                                   (root / (name + ".jsonl")).open("wb"),
                                   pq.ParquetWriter(root / (name + ".parquet"), schema), [])
                schema, logical, stream, writer, pending = sinks[name]
                row = {"row_id": logical.rows + len(pending),
                       "payload_json": canonical_bytes(_json(value)).decode()}
                encoded = canonical_bytes(row) + b"\n"
                raw_bytes += len(encoded)
                if raw_bytes > selection.max_bytes:
                    raise SemanticRefusal("review payload exceeds declared byte budget")
                stream.write(encoded)
                pending.append(row)
                if len(pending) >= 128:
                    batch = pa.RecordBatch.from_pylist(pending, schema=schema)
                    logical.write(batch)
                    writer.write_batch(batch)
                    pending.clear()
            for schema, logical, _, writer, pending in sinks.values():
                if pending:
                    batch = pa.RecordBatch.from_pylist(pending, schema=schema)
                    logical.write(batch)
                    writer.write_batch(batch)
        except BaseException as error:
            primary = error
        finally:
            # Settle every independent owner without replacing the primary failure.
            failures: list[BaseException] = []
            close = getattr(rows, "close", None)
            if close is not None:
                try:
                    close()
                except BaseException as error:
                    failures.append(error)
            for _, _, stream, writer, _ in sinks.values():
                for sink in (stream, writer):
                    try:
                        sink.close()
                    except BaseException as error:
                        failures.append(error)
            if primary is not None:
                for failure in failures:
                    primary.add_note(f"Review cleanup also failed: {failure!r}")
                raise primary
            if failures:
                raise BaseExceptionGroup("review owners failed to settle", failures)
        relations = {}
        for name, (schema, logical, _, _, _) in sinks.items():
            relations[name] = {
                "rows": logical.rows,
                "schema_base64": base64.b64encode(schema.serialize().to_pybytes()).decode(),
                "logical_digest": logical.digest,
                "files": {suffix: {"path": name + "." + suffix,
                                   "sha256": _digest(root / (name + "." + suffix)),
                                   "bytes": (root / (name + "." + suffix)).stat().st_size}
                          for suffix in ("jsonl", "parquet")},
            }
        manifest = {
            "format": FORMAT, "selection": selection_value,
            "selection_digest": selection_digest, "relations": relations,
            "completeness": selection.completeness,
            "assessment_scope": (
                "published_admission_witnesses_only_unless_explicit_evaluator_relations"
            ),
            "original_source_completeness": "not_established",
            "scientific_truth": "not_established",
            "protected_cohorts": "excluded_unless_authorized_by_separate_evaluator_capture",
            "raw_serialization": "canonical_retained_values_original_bytes_only_where_retained",
        }
        overview = ("# Progressive corpus review\n\n"
                    f"Declared scope: `{selection.completeness}`.\n\n"
                    "Inspect `manifest.json`; each relation has matching JSONL and Parquet. "
                    "Decode payload_json for the versioned source/operation object. "
                    "Sources retain projected text, ordered pieces, native items and health.\n\n"
                    "This package establishes neither original-corpus completeness "
                    "nor scientific truth. "
                    "Unassessed contributions remain unassessed. "
                    "Protected labels require a separate "
                    "authorized evaluator capture.\n\n" +
                    "\n".join(f"- [{name}]({name}.jsonl): {spec['rows']} rows"
                              for name, spec in relations.items()) + "\n")
        (root / "README.md").write_text(overview)
        manifest["overview"] = {"path": "README.md", "sha256": _digest(root / "README.md")}
        (root / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
        total = sum(path.stat().st_size for path in root.iterdir())
        if total > selection.max_bytes:
            raise SemanticRefusal("review serializations exceed declared total byte budget")
        verify_review_bundle(root)
        with cancellation.publication():
            _publish_directory(root, destination)
        return manifest


def export_review_bundle(
    selection: ReviewSelection,
    destination: Path,
    settings: Settings,
    *,
    cancellation: OperationCancellation | None = None,
    extra_relations: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    evaluator_capture: Callable[[Any], Mapping[str, Iterable[Mapping[str, Any]]]] | None = None,
) -> dict[str, Any]:
    cancellation = cancellation or OperationCancellation()

    def rows():
        with (open_runtime_engine(
                settings, "review-export", purpose="evaluate" if evaluator_capture else "read"
              ) as engine,
              read_snapshot(engine, cancellation=cancellation.postgresql) as conn):
            yield from capture_review_relations(conn, selection, cancellation)
            if evaluator_capture is not None:
                for name, values in evaluator_capture(conn).items():
                    for value in values:
                        yield name, value
        for name, values in (extra_relations or {}).items():
            for value in values:
                yield name, value

    return write_review_bundle(selection, destination, rows(), cancellation=cancellation)


def _member(root: Path, name: str) -> Path:
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("invalid review member path")
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError("review member missing or not an ordinary file")
    return path


def verify_review_bundle(root: Path) -> dict[str, Any]:
    """Offline integrity and JSONL/Parquet equivalence; no database or model access."""
    manifest = json.loads(_member(root, "manifest.json").read_bytes())
    if manifest.get("format") != FORMAT:
        raise ValueError("unsupported review format")
    selection = ReviewSelection.model_validate(manifest["selection"])
    digest = sha256(canonical_bytes(selection.model_dump(mode="json"))).hexdigest()
    if digest != manifest["selection_digest"] or manifest["completeness"] != selection.completeness:
        raise ValueError("review selection differs")
    expected = {"manifest.json", manifest["overview"]["path"]}
    overview = _member(root, manifest["overview"]["path"])
    if _digest(overview) != manifest["overview"]["sha256"]:
        raise ValueError("review overview differs")
    present_sources: set[int] = set()
    needed_sources: set[int] = set()
    needed_reports: set[int] = set()
    present_reports: set[int] = set()
    omitted_reports: set[int] = set()
    bound_selections: set[int] = set()
    for name, spec in manifest["relations"].items():
        if not _NAME.fullmatch(name):
            raise ValueError("invalid review relation")
        schema = pa.ipc.read_schema(pa.BufferReader(base64.b64decode(spec["schema_base64"])))
        if not schema.equals(_schema(digest, name), check_metadata=True):
            raise ValueError("review schema binding differs")
        logicals = {}
        for suffix in ("jsonl", "parquet"):
            file = spec["files"][suffix]
            expected.add(file["path"])
            path = _member(root, file["path"])
            if _digest(path) != file["sha256"] or path.stat().st_size != file["bytes"]:
                raise ValueError("review file integrity differs")
            logical = LogicalRows(schema, ("row_id",))
            if suffix == "parquet":
                parquet = pq.ParquetFile(path)
                if not parquet.schema_arrow.equals(schema, check_metadata=True):
                    raise ValueError("review parquet schema differs")
                for batch in parquet.iter_batches(batch_size=128):
                    logical.write(batch)
            else:
                with path.open("rb") as stream:
                    pending = []
                    for line in stream:
                        row = json.loads(line)
                        if row["row_id"] != logical.rows + len(pending):
                            raise ValueError("review row ordering differs")
                        payload = json.loads(row["payload_json"])
                        if name == "selections":
                            index = payload["selection_index"]
                            if (index in bound_selections
                                    or not 0 <= index < len(selection.selections)):
                                raise ValueError("review selection population differs")
                            if (payload["run_id"] != selection.selections[index].run_id
                                    or not payload["cut_id"]):
                                raise ValueError("review selected run/cut differs")
                            bound_selections.add(index)
                        if name == "sources":
                            _validate_source(payload)
                            present_sources.add(payload["source_view_id"])
                        elif name in {"inventory", "reports"}:
                            needed_sources.update(_source_ids(payload))
                            if name == "reports":
                                present_reports.add(payload["origin_task_id"])
                            elif payload.get("population") == "report":
                                needed_reports.add(payload["row"]["origin_task_id"])
                        elif name == "omissions" and "origin_task_id" in payload:
                            omitted_reports.add(payload["origin_task_id"])
                        if canonical_bytes(payload).decode() != row["payload_json"]:
                            raise ValueError("review payload is not canonical")
                        pending.append(row)
                        if len(pending) >= 128:
                            logical.write(pa.RecordBatch.from_pylist(pending, schema=schema))
                            pending.clear()
                    if pending:
                        logical.write(pa.RecordBatch.from_pylist(pending, schema=schema))
            if logical.rows != spec["rows"] or logical.digest != spec["logical_digest"]:
                raise ValueError("review row count/logical digest differs")
            logicals[suffix] = logical.digest
        if len(set(logicals.values())) != 1:
            raise ValueError("review serializations disagree")
    if selection.completeness == "selected_source_closure":
        if bound_selections != set(range(len(selection.selections))):
            raise ValueError("review selected snapshot members are missing")
        if not needed_sources <= present_sources:
            raise ValueError("review required source members are missing")
        if not needed_reports <= present_reports | omitted_reports:
            raise ValueError("review required report members are missing")
    if {path.name for path in root.iterdir()} != expected:
        raise ValueError("review package has undeclared or missing members")
    return manifest


def inspect_review_bundle(root: Path) -> dict[str, Any]:
    manifest = verify_review_bundle(root)
    return {"format": FORMAT, "selection": manifest["selection"],
            "completeness": manifest["completeness"],
            "relations": {name: spec["rows"] for name, spec in manifest["relations"].items()},
            "assessment_scope": manifest["assessment_scope"],
            "original_source_completeness": manifest["original_source_completeness"]}
