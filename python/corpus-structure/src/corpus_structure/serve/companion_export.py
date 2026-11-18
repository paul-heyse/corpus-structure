"""Detached, pin-bound companion families and local multiset analysis."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from hashlib import file_digest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from duckdb import col, count_all, when
from pglast import ast, enums
from pglast.stream import RawStream
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Text, func, select
from sqlalchemy.dialects import postgresql

from corpus_structure.core.db.adbc_lifetime import (
    open_adbc_connection,
    owned_adbc_child,
    owned_adbc_read,
)
from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.semantic.capture_storage import LogicalRows
from corpus_structure.semantic.demand_results import CutSelection, selected_read_snapshot
from corpus_structure.semantic.identifiers import ReleaseId
from corpus_structure.semantic.pdf_publication import PublishedPdfDocumentRef
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
from corpus_structure.serve.selected_pdf import (
    SelectedPdfSourceReference,
    acquire_selected_pdf_source,
)
from corpus_structure.settings import Settings

Family = Literal["input", "relation", "coverage", "mapping_report"]
FAMILIES: tuple[Family, ...] = ("input", "relation", "coverage", "mapping_report")
PROFILE_ID = "flat-exact-companion-v3"


class CompanionExportRequest(BaseModel):
    pin: SelectedPdfSourceReference
    families: tuple[Family, ...] = FAMILIES
    destination: Path

    @model_validator(mode="after")
    def unique_families(self):
        if not self.families or len(set(self.families)) != len(self.families):
            raise ValueError("families must be nonempty and unique")
        return self


class FamilyFile(BaseModel):
    path: str
    schema_base64: str
    rows: int
    sha256: str
    byte_length: int
    logical_digest: str


class CompanionExportManifest(BaseModel):
    format: Literal["pdf-companion-export-v3"] = "pdf-companion-export-v3"
    pin: SelectedPdfSourceReference
    producer_release_id: ReleaseId = Field(min_length=1)
    cut: dict[str, Any]
    publication: PublishedPdfDocumentRef
    projection_id: str
    profile_id: str
    created_at: datetime
    families: dict[str, FamilyFile]
    not_requested: tuple[str, ...]

    @model_validator(mode="after")
    def consistent_selection(self):
        cut = CutSelection.from_native(self.cut)
        if (cut.record["project_id"], cut.record["demand_id"], cut.record["read_id"]) != (
            self.pin.project_id,
            self.pin.demand_id,
            self.pin.read_id,
        ) or self.publication.release_id != self.producer_release_id:
            raise ValueError("companion manifest selection/cut/publication differ")
        return self


def _literal_statement(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )


def export_companion_parquet(
    request: CompanionExportRequest,
    settings: Settings,
    *,
    cancellation: OperationCancellation | None = None,
) -> CompanionExportManifest:
    from corpus_structure.semantic.companion_projection import projection

    cancellation = cancellation or OperationCancellation()
    cancellation.check_active()
    destination = request.destination
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    projections = {family: projection(family) for family in request.families}
    identities = {item.projection_id for item in projections.values()}
    if len(identities) != 1:
        raise SemanticRefusal("companion projection definitions disagree")
    projection_id = identities.pop()
    files: dict[str, FamilyFile] = {}
    read = connection_settings(settings, "read")
    with TemporaryDirectory(prefix=".companion-", dir=destination.parent) as scratch:
        root = Path(scratch) / "export"
        root.mkdir()
        with (
            open_runtime_engine(settings, "companion-export", purpose="read") as engine,
            selected_read_snapshot(engine, cancellation=cancellation.postgresql) as conn,
        ):
            selected = acquire_selected_pdf_source(conn, request.pin)
            publication = selected.receipt.publication
            producer_release_id = publication.release_id
            # Native family functions independently check every pin component.
            snapshot = conn.execute(
                select(func.pg_catalog.pg_export_snapshot(type_=Text()))
            ).scalar_one()
            cancellation.check_active()
            with (
                owned_adbc_read(
                    open_adbc_connection(
                        read.database.url,
                        driver_path=settings.analytics.adbc_driver_path,
                        resolver_mode="builtin",
                    ),
                    cancellation.adbc,
                ) as bulk,
                owned_adbc_child(bulk.cursor()) as cursor,
            ):
                cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
                cursor.execute(
                    RawStream()(
                        ast.VariableSetStmt(
                            kind=enums.VariableSetKind.VAR_SET_MULTI,
                            name="TRANSACTION",
                            args=(
                                ast.DefElem(
                                    defname="transaction_isolation",
                                    arg=ast.A_Const(val=ast.String(sval="repeatable read")),
                                ),
                                ast.DefElem(
                                    defname="transaction_read_only",
                                    arg=ast.A_Const(val=ast.Integer(ival=0)),
                                ),
                            ),
                        )
                    )
                )
                cursor.execute(
                    RawStream()(
                        ast.VariableSetStmt(
                            kind=enums.VariableSetKind.VAR_SET_MULTI,
                            name="TRANSACTION SNAPSHOT",
                            args=(ast.A_Const(val=ast.String(sval=snapshot)),),
                        )
                    )
                )
                cursor.adbc_statement.set_options(
                    **{
                        "adbc.postgresql.use_copy": "true",
                        "adbc.postgresql.batch_size_hint_bytes": str(
                            settings.analytics.batch_size_hint_bytes
                        ),
                    }
                )
                for family, spec in projections.items():
                    cancellation.check_active()
                    stmt = spec.arrow_statement.params(**request.pin.model_dump())
                    cursor.execute(_literal_statement(stmt))
                    schema = _export_schema(
                        spec,
                        request.pin,
                        producer_release_id=producer_release_id,
                        cut=selected.cut.record,
                        publication=publication,
                    )
                    logical = LogicalRows(schema, spec.keys)
                    path = root / (family + ".parquet")
                    with (
                        owned_adbc_child(cursor.fetch_record_batch()) as reader,
                        owned_adbc_child(pq.ParquetWriter(path, schema)) as writer,
                    ):
                        _admit_schema(family, schema, reader.schema)
                        for batch in reader:
                            cancellation.check_active()
                            # Exact scalar projections refuse lossy conversion.
                            _admit_schema(family, schema, batch.schema)
                            _admit_batch(
                                spec,
                                batch,
                                request.pin,
                                producer_release_id,
                                cut=selected.cut.record,
                                publication=publication,
                            )
                            batch = batch.cast(schema, safe=True)
                            logical.write(batch)
                            writer.write_batch(batch)
                    with path.open("rb") as source:
                        digest = file_digest(source, "sha256").hexdigest()
                    files[family] = FamilyFile(
                        path=path.name,
                        rows=logical.rows,
                        schema_base64=base64.b64encode(schema.serialize().to_pybytes()).decode(),
                        sha256=digest,
                        byte_length=path.stat().st_size,
                        logical_digest=logical.digest,
                    )
        manifest = CompanionExportManifest(
            pin=request.pin,
            cut=selected.cut.record,
            publication=publication,
            producer_release_id=producer_release_id,
            projection_id=projection_id,
            profile_id=PROFILE_ID,
            created_at=datetime.now(UTC),
            families=files,
            not_requested=tuple(name for name in FAMILIES if name not in files),
        )
        (root / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
        with cancellation.publication():
            _publish_directory(root, destination)
        return manifest


def _export_schema(
    spec, pin: SelectedPdfSourceReference, *, producer_release_id: str, cut, publication
) -> pa.Schema:
    from corpus_structure.semantic.metadata import get_physical_model_id

    return spec.arrow_schema.with_metadata(
        {
            b"cs.projection": spec.projection_id.encode(),
            b"cs.pin": pin.model_dump_json().encode(),
            b"cs.profile": PROFILE_ID.encode(),
            b"cs.selection_release": cut["release_id"].encode(),
            b"cs.cut": CutSelection.from_native(cut).content,
            b"cs.producer_release": producer_release_id.encode(),
            b"cs.physical": get_physical_model_id().encode(),
            b"cs.family": spec.family.encode(),
            b"cs.product": publication.logical_digest.encode(),
        }
    )


def _admit_schema(family: str, expected: pa.Schema, actual: pa.Schema) -> None:
    if actual.names != expected.names or any(
        a.type != b.type for a, b in zip(actual, expected, strict=True)
    ):
        raise SemanticRefusal(
            f"{family} projection differs: observed={actual}, expected={expected}"
        )


def _admit_batch(
    spec,
    batch: pa.RecordBatch,
    pin: SelectedPdfSourceReference,
    producer_release_id: str,
    *,
    cut,
    publication,
) -> None:
    """Enforce declared required values and exact publication provenance per batch."""
    for field in spec.arrow_schema:
        if not field.nullable and batch.column(field.name).null_count:
            raise SemanticRefusal(f"{spec.family} required projection field is null: {field.name}")
    bindings = {
        **pin.model_dump(),
        "producer_release_id": producer_release_id,
        "selection_release_id": cut["release_id"],
        "task_id": publication.task_id,
        "product_key": publication.product_key,
        "content_digest": publication.logical_digest,
        "projection_id": spec.projection_id,
    }
    for name, value in bindings.items():
        column = batch.column(name)
        if column.null_count or (
            len(column)
            and pc.call_function(
                "all", [pc.call_function("equal", [column, pa.scalar(value)])]
            ).as_py()
            is not True
        ):
            raise SemanticRefusal(f"{spec.family} projected publication binding differs: {name}")


def _publish_directory(source: Path, destination: Path) -> None:
    """Linux atomic no-replace publication; an unrelated empty directory is protected too."""
    import ctypes
    import os

    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


def _verified(path: Path):
    from corpus_structure.semantic.companion_projection import projection

    try:
        manifest = CompanionExportManifest.model_validate_json(path.read_bytes())
    except ValueError as error:
        raise SemanticRefusal("companion manifest/schema/pin binding differs") from error
    resolved = {}
    for name, entry in manifest.families.items():
        if (
            name not in FAMILIES
            or Path(entry.path).name != entry.path
            or Path(entry.path).is_absolute()
        ):
            raise SemanticRefusal("invalid companion manifest file path")
        file = path.parent / entry.path
        if file.is_symlink() or file.resolve().parent != path.parent.resolve():
            raise SemanticRefusal("companion file escapes manifest directory")
        with file.open("rb") as source:
            digest = file_digest(source, "sha256").hexdigest()
        if digest != entry.sha256 or file.stat().st_size != entry.byte_length:
            raise SemanticRefusal("companion file binding differs")
        expected = pa.ipc.read_schema(pa.BufferReader(base64.b64decode(entry.schema_base64)))
        spec = projection(name)
        bindings = {
            b"cs.pin": manifest.pin.model_dump_json().encode(),
            b"cs.projection": manifest.projection_id.encode(),
            b"cs.profile": manifest.profile_id.encode(),
            b"cs.family": name.encode(),
            b"cs.selection_release": manifest.cut["release_id"].encode(),
            b"cs.cut": CutSelection.from_native(manifest.cut).content,
            b"cs.producer_release": manifest.producer_release_id.encode(),
            b"cs.product": manifest.publication.logical_digest.encode(),
        }
        if any((expected.metadata or {}).get(key) != value for key, value in bindings.items()):
            raise SemanticRefusal("companion projection/schema/pin binding differs")
        if (
            manifest.projection_id == spec.projection_id
            and manifest.profile_id == PROFILE_ID
            and not expected.equals(
                _export_schema(
                    spec,
                    manifest.pin,
                    producer_release_id=manifest.producer_release_id,
                    cut=manifest.cut,
                    publication=manifest.publication,
                ),
                check_metadata=True,
            )
        ):
            raise SemanticRefusal("companion current projection schema differs")
        parquet = pq.ParquetFile(file)
        if (
            not parquet.schema_arrow.equals(expected, check_metadata=True)
            or parquet.metadata.num_rows != entry.rows
        ):
            raise SemanticRefusal("companion schema/row binding differs")
        logical = LogicalRows(expected)
        for batch in parquet.iter_batches():
            if manifest.projection_id == spec.projection_id and manifest.profile_id == PROFILE_ID:
                _admit_batch(
                    spec,
                    batch,
                    manifest.pin,
                    manifest.producer_release_id,
                    cut=manifest.cut,
                    publication=manifest.publication,
                )
            logical.write(batch)
        if logical.digest != entry.logical_digest:
            raise SemanticRefusal("companion logical rows differ")
        resolved[name] = file
    if set(manifest.families) & set(manifest.not_requested) or set(manifest.families) | set(
        manifest.not_requested
    ) != set(FAMILIES):
        raise SemanticRefusal("companion requested-family states disagree")
    return manifest, resolved


def inventory_companion_export(path: Path) -> dict:
    manifest, files = _verified(path)
    return _inventory_verified_export(manifest, files)


def _inventory_verified_export(manifest, files) -> dict:
    from corpus_structure.semantic.companion_projection import installed_projection_id

    supported = (
        manifest.projection_id == installed_projection_id() and manifest.profile_id == PROFILE_ID
    )
    from corpus_structure.model.compiled import running_model

    declared_columns = running_model().companion_columns()
    inventory = {}
    with duckdb.connect() as db:
        for name, file in files.items():
            if not supported:
                inventory[name] = {
                    "rows": manifest.families[name].rows,
                    "semantic_inventory": "unsupported_projection_or_profile",
                }
                continue
            family = db.from_parquet(str(file))
            columns = declared_columns[name]
            group = columns.group
            count = col(columns.distinct).n_unique() if columns.distinct else count_all()
            counts = family.aggregate([col(group), count]).sort(col(group)).fetchall()
            detail: dict[str, Any] = {
                "rows": manifest.families[name].rows,
                "distribution": counts,
            }
            inventory[name] = detail
            if name == "input":
                detail["bindings"] = _inventory_groups(
                    family,
                    (
                        "input_role",
                        "input_task_id",
                        "input_product_key",
                        "input_content_digest",
                    ),
                )
                detail["occurrences"] = (
                    family.select(
                        *(
                            col(column)
                            for column in (
                                "input_ordinal",
                                "input_role",
                                "input_task_id",
                                "input_product_key",
                                "input_content_digest",
                            )
                        )
                    )
                    .sort(col("input_ordinal"))
                    .fetchall()
                )
            elif name == "relation":
                detail["relation_count"] = family.aggregate(
                    [col("relation_id").n_unique()]
                ).fetchall()[0][0]
                detail["endpoints"] = _inventory_groups(
                    family,
                    (
                        "relation_kind",
                        "endpoint_role",
                        "target_task_id",
                        "target_product_key",
                        "target_content_digest",
                        "target_occurrence_id",
                    ),
                )
                # The export selects one whole product. This is product membership,
                # not a claim about an endpoint's membership in any narrower section.
                own_product = (
                    (col("target_task_id") == manifest.publication.task_id)
                    & (col("target_product_key") == manifest.publication.product_key)
                    & (col("target_content_digest") == manifest.publication.logical_digest)
                )
                scope = when(own_product).then("own_product").otherwise("external_product")
                detail["target_scope"] = (
                    family.select(scope.alias("scope"))
                    .aggregate([col("scope"), count_all()])
                    .sort(col("scope"))
                    .fetchall()
                )
            elif name == "coverage":
                detail["scoped_outcomes"] = _inventory_groups(
                    family,
                    (
                        "scope",
                        "coverage_family",
                        "discovery_policy",
                        "outcome",
                    ),
                )
            else:
                detail["scoped_outcomes"] = _inventory_groups(
                    family,
                    (
                        "input_index",
                        "input_task_id",
                        "input_product_key",
                        "input_content_digest",
                        "coordinate_frame",
                        "coordinate_scale",
                        "normalization",
                        "outcome",
                    ),
                )
    return {
        "pin": manifest.pin.model_dump(),
        "cut": manifest.cut,
        "producer_release_id": manifest.producer_release_id,
        "projection_id": manifest.projection_id,
        "families": inventory,
        "not_requested": manifest.not_requested,
    }


def _inventory_groups(family, columns: tuple[str, ...]) -> dict:
    """Fixed model projection dimensions; every repeated use contributes to the count."""
    expressions = [col(name) for name in columns]
    return {
        "columns": (*columns, "count"),
        "rows": family.aggregate([*expressions, count_all()]).sort(*expressions).fetchall(),
    }


def compare_companion_exports(left: Path, right: Path) -> dict:
    lm, lf = _verified(left)
    rm, rf = _verified(right)
    from corpus_structure.semantic.companion_projection import installed_projection_id

    comparable = (
        lm.projection_id == rm.projection_id == installed_projection_id()
        and lm.profile_id == rm.profile_id == PROFILE_ID
        and set(lf) == set(rf)
        and lm.pin.project_id == rm.pin.project_id
        and lm.cut["release_id"] == rm.cut["release_id"]
        and lm.producer_release_id == rm.producer_release_id
    )
    result: dict[str, Any] = {
        "left": _inventory_verified_export(lm, lf),
        "right": _inventory_verified_export(rm, rf),
        "comparable": comparable,
        "differences": {},
    }
    if not comparable:
        result["reason"] = "projection, profile, release, project or selected families differ"
        return result
    with duckdb.connect() as db:
        if lm.pin != rm.pin:
            if "input" not in lf:
                result.update(comparable=False, reason="source comparability requires input family")
                return result
            from corpus_structure.model.compiled import running_model

            source_columns = running_model().companion_columns()["input"].values
            projection = [col(name) for name in source_columns]
            left_input = db.from_parquet(str(lf["input"])).select(*projection)
            right_input = db.from_parquet(str(rf["input"])).select(*projection)
            different = left_input.except_(right_input).limit(1).fetchall()
            reverse = right_input.except_(left_input).limit(1).fetchall()
            if different or reverse:
                result.update(comparable=False, reason="source input bindings differ")
                return result
        for name in lf:
            left_family = db.from_parquet(str(lf[name]))
            right_family = db.from_parquet(str(rf[name]))
            # Provenance differs by product; all projected value columns retain exact multiplicity.
            from corpus_structure.model.compiled import running_model

            excluded = running_model().companion_columns()[name].provenance
            columns = [x for x in left_family.columns if x not in excluded]
            projection = [col(name) for name in columns]
            left_values = left_family.select(*projection)
            right_values = right_family.select(*projection)
            removed = left_values.except_(right_values) if lm.pin == rm.pin else left_values
            added = right_values.except_(left_values) if lm.pin == rm.pin else right_values
            result["differences"][name] = {
                "columns": columns,
                "left_pin": lm.pin.model_dump(),
                "right_pin": rm.pin.model_dump(),
                "correspondence": "same_product" if lm.pin == rm.pin else "none",
                # Local occurrence IDs/ordinals establish no cross-product match.
                # Without a declared correspondence, every record keeps its side's pin.
                "removed": removed.fetchall(),
                "added": added.fetchall(),
            }
    return result
