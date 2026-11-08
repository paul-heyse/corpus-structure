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
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import String, text
from sqlalchemy.dialects import postgresql

from corpus_structure.core.db.adbc_lifetime import owned_adbc_read
from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.semantic.analytics import open_adbc_connection
from corpus_structure.semantic.capture_storage import LogicalRows
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.runtime import connection_settings, open_runtime_engine
from corpus_structure.settings import Settings

Family = Literal["input", "relation", "coverage", "mapping_report"]
FAMILIES: tuple[Family, ...] = ("input", "relation", "coverage", "mapping_report")
PROFILE_ID = "flat-exact-companion-v2"


class PublishedSourcePin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    project_id: str = Field(min_length=1)
    run_id: int = Field(gt=0)
    selection_release_id: str = Field(min_length=1)
    task_id: int = Field(gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class CompanionExportRequest(BaseModel):
    pin: PublishedSourcePin
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
    format: Literal["pdf-companion-export-v2"] = "pdf-companion-export-v2"
    pin: PublishedSourcePin
    producer_release_id: str = Field(min_length=1)
    projection_id: str
    profile_id: str
    created_at: datetime
    families: dict[str, FamilyFile]
    not_requested: tuple[str, ...]


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
    from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source

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
            read_snapshot(engine, cancellation=cancellation.postgresql) as conn,
        ):
            response = inspect_native_source(
                conn,
                NativeSourceRequest(
                    run_id=request.pin.run_id,
                    task_id=request.pin.task_id,
                    product_key=request.pin.product_key,
                    content_digest=request.pin.content_digest,
                    view="products",
                    limit=1,
                ),
                cancellation=cancellation.postgresql,
            )
            producer_release_id = response.release_id
            if not producer_release_id:
                raise SemanticRefusal("published producer release is unavailable")
            # Native family functions independently check every pin component.
            snapshot = conn.execute(text("SELECT pg_export_snapshot()")).scalar_one()
            cancellation.check_active()
            with (
                owned_adbc_read(
                    open_adbc_connection(
                        read.database.url, driver_path=settings.analytics.adbc_driver_path
                    ),
                    cancellation.adbc,
                ) as bulk,
                bulk.cursor() as cursor,
            ):
                cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                dialect = postgresql.dialect(paramstyle="named")
                snapshot_sql = dialect.statement_compiler(dialect, None).render_literal_value(
                    snapshot, String()
                )
                cursor.execute("SET TRANSACTION SNAPSHOT " + snapshot_sql)
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
                        spec, request.pin, producer_release_id=producer_release_id
                    )
                    logical = LogicalRows(schema, spec.keys)
                    path = root / (family + ".parquet")
                    with (
                        cursor.fetch_record_batch() as reader,
                        pq.ParquetWriter(path, schema) as writer,
                    ):
                        _admit_schema(family, schema, reader.schema)
                        for batch in reader:
                            cancellation.check_active()
                            # Exact scalar projections refuse lossy conversion.
                            _admit_schema(family, schema, batch.schema)
                            _admit_batch(spec, batch, request.pin, producer_release_id)
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


def _export_schema(spec, pin: PublishedSourcePin, *, producer_release_id: str) -> pa.Schema:
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID

    return spec.arrow_schema.with_metadata(
        {
            b"cs.projection": spec.projection_id.encode(),
            b"cs.pin": pin.model_dump_json().encode(),
            b"cs.profile": PROFILE_ID.encode(),
            b"cs.selection_release": pin.selection_release_id.encode(),
            b"cs.producer_release": producer_release_id.encode(),
            b"cs.physical": PHYSICAL_MODEL_ID.encode(),
            b"cs.family": spec.family.encode(),
            b"cs.product": pin.content_digest.encode(),
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
    spec, batch: pa.RecordBatch, pin: PublishedSourcePin, producer_release_id: str
) -> None:
    """Enforce declared required values and exact publication provenance per batch."""
    for field in spec.arrow_schema:
        if not field.nullable and batch.column(field.name).null_count:
            raise SemanticRefusal(f"{spec.family} required projection field is null: {field.name}")
    bindings = {
        **pin.model_dump(),
        "producer_release_id": producer_release_id,
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

    manifest = CompanionExportManifest.model_validate_json(path.read_bytes())
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
            b"cs.selection_release": manifest.pin.selection_release_id.encode(),
            b"cs.producer_release": manifest.producer_release_id.encode(),
            b"cs.product": manifest.pin.content_digest.encode(),
        }
        if any((expected.metadata or {}).get(key) != value for key, value in bindings.items()):
            raise SemanticRefusal("companion projection/schema/pin binding differs")
        if (
            manifest.projection_id == spec.projection_id
            and manifest.profile_id == PROFILE_ID
            and not expected.equals(
                _export_schema(
                    spec, manifest.pin, producer_release_id=manifest.producer_release_id
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
                _admit_batch(spec, batch, manifest.pin, manifest.producer_release_id)
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
    from corpus_structure.semantic.companion_projection import installed_projection_id

    supported = (
        manifest.projection_id == installed_projection_id() and manifest.profile_id == PROFILE_ID
    )
    inventory = {}
    with duckdb.connect() as db:
        for name, file in files.items():
            if not supported:
                inventory[name] = {
                    "rows": manifest.families[name].rows,
                    "semantic_inventory": "unsupported_projection_or_profile",
                }
                continue
            db.from_parquet(str(file)).create_view("family", replace=True)
            group = {
                "input": "input_role",
                "relation": "relation_kind",
                "coverage": "outcome",
                "mapping_report": "outcome",
            }[name]
            count = "count(DISTINCT relation_id)" if name == "relation" else "count(*)"
            counts = db.sql(
                f'SELECT "{group}", {count} FROM family GROUP BY "{group}" ORDER BY "{group}"'
            ).fetchall()
            detail: dict[str, Any] = {
                "rows": manifest.families[name].rows,
                "distribution": counts,
            }
            inventory[name] = detail
            if name == "input":
                detail["bindings"] = _inventory_groups(
                    db,
                    (
                        "input_role",
                        "input_task_id",
                        "input_product_key",
                        "input_content_digest",
                    ),
                )
                detail["occurrences"] = db.sql(
                    "SELECT input_ordinal,input_role,input_task_id,input_product_key,"
                    "input_content_digest FROM family ORDER BY input_ordinal"
                ).fetchall()
            elif name == "relation":
                detail["relation_count"] = db.sql(
                    "SELECT count(DISTINCT relation_id) FROM family"
                ).fetchall()[0][0]
                detail["endpoints"] = _inventory_groups(
                    db,
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
                detail["target_scope"] = db.execute(
                    "SELECT CASE WHEN target_task_id=? AND target_product_key=? "
                    "AND target_content_digest=? THEN 'own_product' ELSE 'external_product' END "
                    "AS scope,count(*) FROM family GROUP BY scope ORDER BY scope",
                    [manifest.pin.task_id, manifest.pin.product_key, manifest.pin.content_digest],
                ).fetchall()
            elif name == "coverage":
                detail["scoped_outcomes"] = _inventory_groups(
                    db,
                    (
                        "scope",
                        "coverage_family",
                        "discovery_policy",
                        "outcome",
                    ),
                )
            else:
                detail["scoped_outcomes"] = _inventory_groups(
                    db,
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
        "producer_release_id": manifest.producer_release_id,
        "projection_id": manifest.projection_id,
        "families": inventory,
        "not_requested": manifest.not_requested,
    }


def _inventory_groups(db, columns: tuple[str, ...]) -> dict:
    """Fixed model projection dimensions; every repeated use contributes to the count."""
    selected = ",".join('"' + name + '"' for name in columns)
    return {
        "columns": (*columns, "count"),
        "rows": db.sql(
            f"SELECT {selected},count(*) FROM family GROUP BY {selected} ORDER BY {selected}"
        ).fetchall(),
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
        and lm.pin.selection_release_id == rm.pin.selection_release_id
        and lm.producer_release_id == rm.producer_release_id
    )
    result: dict[str, Any] = {
        "left": inventory_companion_export(left),
        "right": inventory_companion_export(right),
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
            db.from_parquet(str(lf["input"])).create_view("left_input")
            db.from_parquet(str(rf["input"])).create_view("right_input")
            source_columns = (
                "input_ordinal,input_role,input_task_id,input_product_key,input_content_digest"
            )
            different = db.sql(
                f"SELECT {source_columns} FROM left_input "
                f"EXCEPT ALL SELECT {source_columns} FROM right_input"
            ).fetchall()
            reverse = db.sql(
                f"SELECT {source_columns} FROM right_input "
                f"EXCEPT ALL SELECT {source_columns} FROM left_input"
            ).fetchall()
            if different or reverse:
                result.update(comparable=False, reason="source input bindings differ")
                return result
        for name in lf:
            db.from_parquet(str(lf[name])).create_view("left_family", replace=True)
            db.from_parquet(str(rf[name])).create_view("right_family", replace=True)
            # Provenance differs by product; all projected value columns retain exact multiplicity.
            excluded = {
                "project_id",
                "run_id",
                "selection_release_id",
                "producer_release_id",
                "task_id",
                "product_key",
                "content_digest",
                "projection_id",
            }
            columns = [
                x for x in db.sql("SELECT * FROM left_family LIMIT 0").columns if x not in excluded
            ]
            selected = ",".join('"' + x.replace('"', '""') + '"' for x in columns)
            result["differences"][name] = {
                "columns": columns,
                "left_pin": lm.pin.model_dump(),
                "right_pin": rm.pin.model_dump(),
                "correspondence": "same_product" if lm.pin == rm.pin else "none",
                # Local occurrence IDs/ordinals establish no cross-product match.
                # Without a declared correspondence, every record keeps its side's pin.
                "removed": db.sql(
                    f"SELECT {selected} FROM left_family "
                    + (
                        f"EXCEPT ALL SELECT {selected} FROM right_family"
                        if lm.pin == rm.pin
                        else ""
                    )
                ).fetchall(),
                "added": db.sql(
                    f"SELECT {selected} FROM right_family "
                    + (f"EXCEPT ALL SELECT {selected} FROM left_family" if lm.pin == rm.pin else "")
                ).fetchall(),
            }
    return result
