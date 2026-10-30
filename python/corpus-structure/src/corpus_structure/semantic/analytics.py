"""Release-bound Core → shared PostgreSQL snapshot → Arrow → scoped DuckDB.

The packet is replayable columnar input. Database transactions finish before analytical
compute; only explicitly owned result readers extend a local scope's lifetime.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import adbc_driver_manager.dbapi as adbc_manager
import adbc_driver_postgresql.dbapi as adbc
import duckdb
import pyarrow as pa
import pyarrow.compute as pc
from sqlalchemy import (
    Boolean,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    case,
    cast,
    func,
    literal,
    select,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Select

from .analytical_kernels import (
    ALTERNATIVE_OF,
    DISAGREEMENTS_SQL,
    FUSE_SQL,
    SAME_SLOT,
    VIEW_APPLIES,
    VIEW_SPECS,
    VIEWS_INPUTS,
    VIEWS_MACRO_NAME,
    VIEWS_MACRO_SQL,
    ViewSpec,
)
from .analytical_profile import AnalyticalProfile
from .identity import canonical_bytes
from .metadata import PHYSICAL_MODEL_ID, table
from .types import PreparedRelease

if TYPE_CHECKING:
    from .analysis_contracts import OwnedAnalysisInput
    from .domain_operations import CutInput
    from .query import ReadSession, SnapshotBinding

COMPILER_VERSION = "analytical-5"
SPINE = (
    "entity",
    "entity_input",
    "entity_source",
    "identity_exclusion",
    "identity_exclusion_evidence",
    "membership",
    "membership_support",
    "typed_value",
    "value_role",
    "fact",
    "fact_input",
    "alternative_group",
    "alternative_member",
    "occurrence",
    "support",
    "selection",
    "evidence",
    "occurrence_evidence",
    "occurrence_context",
    "occurrence_evidence_role",
    "derivation",
    "derivation_premise",
    "coverage",
    "occurrence_establishment",
    "assessment",
    "evidence_source",
)
CANDIDATE_SCHEMA = pa.schema(
    [
        pa.field("fact_id", pa.string()),
        pa.field("occurrence_id", pa.string()),
        pa.field("evidence", pa.list_(pa.struct([pa.field("evidence_id", pa.string())]))),
    ]
)


def _derived(scale: int) -> tuple[pa.Field, ...]:
    return (
        pa.field("decimal_value", pa.decimal128(38, scale)),
        pa.field("decimal_rounded", pa.bool_(), nullable=False),
        pa.field("integer64_value", pa.int64()),
        pa.field("datetime_value", pa.timestamp("ns", tz="UTC")),
        pa.field("date_value", pa.date32()),
        pa.field("float64_value", pa.float64()),
    )


@dataclass(frozen=True)
class Projection:
    name: str
    statement: Select
    schema: pa.Schema
    output_mapping: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CompiledProjection:
    binding: SnapshotBinding
    projection_id: str
    profile: AnalyticalProfile
    relations: tuple[Projection, ...]


@dataclass(frozen=True)
class CapturedPacket:
    binding: SnapshotBinding
    projection_id: str
    profile_digest: str
    relations: Mapping[str, pa.Table]
    property_ids: tuple[str, ...] = ()
    scale: int = 12
    execution_model_id: str | None = None
    execution_contract: bytes | None = None
    input_contract: OwnedAnalysisInput | None = dataclass_field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        object.__setattr__(self, "relations", MappingProxyType(dict(self.relations)))


# Existing capture callers retain their import while the two provenance types stay disjoint.
AnalyticalPacket = CapturedPacket


@dataclass(frozen=True)
class CandidateInput:
    binding: SnapshotBinding
    projection_id: str
    profile_digest: str
    cut_id: str
    decision_universe: str
    relations: Mapping[str, pa.Table]
    property_ids: tuple[str, ...] = ()
    scale: int = 12
    operation_id: str = "evaluate"
    run_id: int | None = None
    target_realization_id: str | None = None
    decision_occurrence_ids: tuple[str, ...] = ()

    execution_model_id: str | None = None
    execution_contract: bytes | None = None
    input_contract: OwnedAnalysisInput | None = dataclass_field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        if not self.cut_id or not self.decision_universe:
            raise ValueError("candidate input requires cut and decision universe")
        if set(self.relations) != {"candidate_input"}:
            raise ValueError("candidate input requires its actual candidate_input relation")
        relation = self.relations["candidate_input"]
        if not relation.schema.remove_metadata().equals(CANDIDATE_SCHEMA):
            raise ValueError("candidate relation has wrong compiled shape")
        if any(relation[name].null_count for name in ("fact_id", "occurrence_id", "evidence")):
            raise ValueError("candidate relation contains missing identifiers/support sets")
        if len(set(relation["occurrence_id"].to_pylist())) != relation.num_rows:
            raise ValueError("candidate relation repeats an occurrence identity")
        object.__setattr__(self, "relations", MappingProxyType(dict(self.relations)))

    @classmethod
    def from_cut(
        cls,
        prepared: PreparedRelease,
        cut: CutInput,
        *,
        candidates: pa.Table,
        decision_universe: str,
    ) -> CandidateInput:
        if (
            prepared.release_id != cut.prepared.release_id
            or prepared.release_id != cut.source_binding.release_id
        ):
            raise ValueError("candidate cut release differs from source")
        if (
            cut.batch.release_id != prepared.release_id
            or cut.batch.realization_id != cut.output_realization_id
        ):
            raise ValueError("candidate output differs from cut batch")
        if (
            cut.source_binding.realization_id == cut.output_realization_id
            or cut.cut_id < 1
            or cut.run_id < 1
            or cut.source_binding.capture_id != "cut:" + str(cut.cut_id)
        ):
            raise ValueError("candidate cut requires a distinct bound output and run")
        contract = _projection_contract(prepared, "candidate", operation_id="evaluate")
        compiled = compile_projection(prepared, cut.source_binding, kind="candidate")
        evidence: dict[str, list[dict[str, str]]] = {
            row.occurrence_id: [] for row in cut.batch.occurrence
        }
        for link in cut.batch.occurrence_evidence:
            evidence[link.occurrence_id].append({"evidence_id": link.evidence_id})
        expected = [
            {
                "fact_id": row.fact_id,
                "occurrence_id": row.occurrence_id,
                "evidence": evidence[row.occurrence_id],
            }
            for row in cut.batch.occurrence
        ]
        if (
            not candidates.schema.remove_metadata().equals(CANDIDATE_SCHEMA)
            or candidates.to_pylist() != expected
        ):
            raise ValueError(
                "candidate relation differs from complete cut occurrence/evidence universe"
            )
        if not contract or not decision_universe:
            raise ValueError("candidate decision universe is missing")
        decisions = tuple(sorted({row.occurrence_id for row in cut.candidates}))
        if not set(decisions) <= set(evidence):
            raise ValueError("decision candidate is outside cut source occurrence universe")
        rows = candidates.replace_schema_metadata(
            _metadata(
                cut.source_binding,
                compiled.projection_id,
                compiled.profile.digest,
                "candidate_input",
            )
        )
        from .contracts import execution_payload

        return cls(
            cut.source_binding,
            compiled.projection_id,
            compiled.profile.digest,
            str(cut.cut_id),
            decision_universe,
            {"candidate_input": rows},
            tuple(sorted({p.iri for d in prepared.definitions for p in d.properties})),
            compiled.profile.scale,
            "evaluate",
            cut.run_id,
            cut.output_realization_id,
            decisions,
            execution_model_id=prepared.execution_model_id,
            execution_contract=execution_payload(prepared),
            input_contract=_owned_input(
                prepared,
                "comparison",
                release=prepared.release_id,
                snapshot=asdict(cut.source_binding),
                universe=decision_universe,
                policy=compiled.projection_id,
            ),
        )


class BorrowedHandle:
    """DuckDB objects borrow the scope; materialized Arrow/Python results detach."""

    def __init__(
        self, owner: AnalysisScope, native: Any, connection: duckdb.DuckDBPyConnection | None = None
    ):
        self._owner, self._native = owner, native
        self._connection_owner = connection if connection is not None else owner._connection
        self._input_name: str | None = None

    def __getattr__(self, name: str) -> Any:
        self._owner._ensure_open()
        if name == "close" and self._native is self._owner._connection:
            return self._owner.close
        attribute = getattr(self._native, name)
        if not callable(attribute):
            return self._owner._borrow(attribute, self._connection_owner)

        def invoke(*args: Any, **kwargs: Any) -> Any:
            self._owner._ensure_open()

            def unwrap(value: Any) -> Any:
                if isinstance(value, BorrowedHandle):
                    value._owner._ensure_open()
                    if value._owner is not self._owner:
                        raise ValueError("analytical handle belongs to another scope")
                    return value._native
                return value

            result = attribute(
                *(unwrap(v) for v in args), **{k: unwrap(v) for k, v in kwargs.items()}
            )
            return self._owner._borrow(result, self._connection_owner)

        return invoke


class BorrowedReader(BorrowedHandle):
    def __iter__(self):
        return self

    def __next__(self):
        self._owner._ensure_open()
        return self._native.read_next_batch()

    def close(self) -> None:
        self._native.close()


def _scalar_type(sql_type: Any) -> pa.DataType:
    if isinstance(sql_type, Boolean):
        return pa.bool_()
    if isinstance(sql_type, Integer):
        return pa.int64()
    if isinstance(sql_type, LargeBinary):
        return pa.binary()
    # Unbounded NUMERIC and opaque JSON are preserved as lexical columns.
    if isinstance(sql_type, (String, Numeric)) or str(sql_type) == "JSONB":
        return pa.string()
    raise ValueError(f"unsupported physical projection type {sql_type}")


def _metadata(
    binding: SnapshotBinding, projection_id: str, profile: str, name: str
) -> dict[bytes, bytes]:
    return {
        f"cs.{key}".encode(): str(value).encode()
        for key, value in {
            "release": binding.release_id,
            "realization": binding.realization_id,
            "data_revision": binding.data_revision,
            "capture": binding.capture_id,
            "projection": projection_id,
            "profile": profile,
            "relation": name,
        }.items()
    }


def _fields(name: str, scale: int) -> list[pa.Field]:
    fields = [
        pa.field(c.name, _scalar_type(c.type), nullable=c.nullable)
        for c in table("data." + name).columns
    ]
    if name == "typed_value":
        fields += list(_derived(scale))
    if name == "fact":
        fields += [pa.field("qualification_key", pa.string(), nullable=False)]
    return fields


def _projection_contract(
    prepared: PreparedRelease, kind: str, *, operation_id: str | None = None
) -> dict[str, Any]:
    """Resolve finite projection behavior from the admitted semantic descriptor."""
    from .contracts import bound_execution_model, compile_execution_model, trusted_execution_inputs

    if prepared.execution_model_id is None:
        if operation_id is not None:
            raise ValueError("candidate operation requires a composed execution model")
        # The explicit base protocol uses the same normalized trusted companion;
        # never reparse YAML or invent a second projection-policy translation.
        model = compile_execution_model(trusted_execution_inputs())
    else:
        model = bound_execution_model(prepared)
    projection = next((row for row in model.projections if row.id == kind), None)
    if projection is None:
        raise ValueError("missing named analytical projection contract")
    if operation_id is not None:
        operation = model.require_operation(operation_id)
        if kind not in operation.projections:
            raise ValueError("operation does not admit the analytical projection")
    contract: dict[str, Any] = asdict(projection)
    # Existing physical recipe JSON represents ordered declarations as lists.
    contract["omissions"] = list(projection.omissions)
    expected = {
        "input_kind": kind,
        "universe": {
            "captured": "full_spine",
            "candidate": "cut_candidates",
            "accepted": "eligible_positive_accepted",
        }[kind],
        "collections": "positions_and_multiplicity",
        "completeness": "declared_universe",
        "values": "exact" if kind == "accepted" else "exact_with_separate_bounded_projection",
        "arithmetic_profile": None if kind == "accepted" else "analytical-profile.json",
    }
    if contract.get("analytical_policy") != expected:
        raise ValueError("analytical projection policy is not supported by this compiler")
    expected_omissions = ["negative_hypothetical_premises"] if kind == "accepted" else []
    if contract.get("omissions") != expected_omissions:
        raise ValueError("analytical projection omissions are unsupported")
    implementation, lifetime = {
        "captured": ("capture", "detached"),
        "candidate": ("analysis", "scope"),
        "accepted": ("query", "snapshot"),
    }[kind]
    if (contract["implementation"], contract["lifetime"]) != (implementation, lifetime):
        raise ValueError("analytical projection has incompatible implementation/lifetime")
    return contract


def _projection_recipe(prepared: PreparedRelease, kind: str) -> tuple[Any, str]:
    """Historical capture retains its archived projection ABI; it admits no new work."""
    import json

    compiler = str(json.loads(prepared.manifest)["profile"]["compiler_version"])
    if compiler not in {"10", "11"}:
        return _projection_contract(prepared, kind), COMPILER_VERSION
    if kind != "captured":
        raise ValueError("historical analytical recipe supports retained capture reads only")
    if prepared.execution_model_id is None:
        return kind, "analytical-4"
    model = next(
        row
        for row in prepared.registry_rows
        if row.kind == "execution_model" and row.name == prepared.execution_model_id
    )
    contract = next(row for row in json.loads(model.body)["projections"] if row["id"] == kind)
    if (contract["implementation"], contract["lifetime"]) != ("capture", "detached"):
        raise ValueError("historical analytical projection recipe is unsupported")
    return contract, "analytical-4"


def compile_projection(
    prepared: PreparedRelease, binding: SnapshotBinding, *, kind: str = "captured"
) -> CompiledProjection:
    """One trusted physical mapping produces Core selections and their exact Arrow schemas."""
    from corpus_structure.semantic.contracts import require_bound_operation

    require_bound_operation(prepared, "compile_projection")
    if prepared.release_id != binding.release_id:
        raise ValueError("projection release differs from snapshot")
    if kind not in {"captured", "candidate"}:
        raise ValueError("unknown analytical projection contract")
    contract, compiler = _projection_recipe(prepared, kind)
    profile = AnalyticalProfile.from_release(prepared)
    identity = (
        "projection:"
        + sha256(
            canonical_bytes(
                [
                    prepared.release_id,
                    PHYSICAL_MODEL_ID,
                    compiler,
                    profile.digest,
                    contract,
                ]
            )
        ).hexdigest()
    )
    if kind == "candidate":
        # Candidates are private cut rows supplied by from_cut, never a PostgreSQL
        # full-spine capture. Their fixed shape is CANDIDATE_SCHEMA.
        return CompiledProjection(binding, identity, profile, ())
    projections = []
    for name in SPINE:
        source = table("data." + name)
        fields, columns = [], []
        for column in source.columns:
            arrow_type = _scalar_type(column.type)
            fields.append(pa.field(column.name, arrow_type, nullable=column.nullable))
            columns.append(
                cast(column, Text).label(column.name)
                if isinstance(column.type, Numeric) or str(column.type) == "JSONB"
                else column
            )
        statement = select(*columns).where(
            source.c.release_id == binding.release_id,
            source.c.realization_id == binding.realization_id,
        )
        if name == "fact":
            qualification = func.data.canonical_json(
                func.data.value_meaning(
                    source.c.release_id,
                    source.c.realization_id,
                    source.c.qualification_value_id,
                    cast(literal("{}"), postgresql.ARRAY(Text())),
                    literal(True),
                )
            )
            statement = statement.add_columns(
                case(
                    (source.c.qualification_value_id.is_(None), literal('["mapping",[]]')),
                    else_=qualification,
                ).label("qualification_key")
            )
        fields = _fields(name, profile.scale)
        schema = pa.schema(fields, metadata=_metadata(binding, identity, profile.digest, name))
        derived_sources = {
            "decimal_value": "decimal_lexical",
            "decimal_rounded": "decimal_lexical",
            "integer64_value": "text_value",
            "datetime_value": "text_value",
            "date_value": "text_value",
            "float64_value": "text_value",
        }
        projections.append(
            Projection(
                name,
                statement,
                schema,
                tuple((f.name, derived_sources.get(f.name, f.name)) for f in fields),
            )
        )
    return CompiledProjection(binding, identity, profile, tuple(projections))


def compile_sql(statement: Select) -> str:
    """Literal Core SQL for libpq COPY; named style preserves percent signs verbatim."""
    return str(
        statement.compile(
            dialect=postgresql.dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}
        )
    )


def normalize_relation(
    raw: pa.Table, projection: Projection, profile: AnalyticalProfile
) -> pa.Table:
    """Apply a known compiled projection to raw driver columns; never infer meaning from tags."""
    columns = []
    for field in projection.schema:
        if field.name in {f.name for f in _derived(profile.scale)}:
            continue
        column = raw[field.name]
        if isinstance(column.type, pa.ExtensionType):
            column = pa.chunked_array([chunk.storage for chunk in column.chunks])
        if column.type != field.type:
            column = column.cast(field.type, safe=True)
        if not field.nullable and column.null_count:
            raise ValueError(f"unexpected null in {projection.name}.{field.name}")
        columns.append(column)
    if projection.name == "typed_value":
        # This is the single decimal boundary: Arrow's cast refuses rescaling, while
        # DuckDB's cast has a different tie policy. Preserve exact lexical/source columns.
        values, rounded = [], []
        for lexical in raw["decimal_lexical"].to_pylist():
            value, changed = (None, False) if lexical is None else profile.decimal(lexical)
            values.append(value)
            rounded.append(changed)
        columns.extend(
            (
                pa.array(values, type=pa.decimal128(38, profile.scale)),
                pa.array(rounded, type=pa.bool_()),
            )
        )
        # Native safe casts enforce bounded integer/time precision and timezone support.
        # Explicit kind columns distinguish missing/null states from these nullable projections.
        for kind, field in zip(
            ("integer", "datetime", "date"), _derived(profile.scale)[2:5], strict=True
        ):
            source = (
                pc.call_function("coalesce", [raw["text_value"], raw["integer_value"]])
                if kind == "integer"
                else raw["text_value"]
            )
            lexical = pc.call_function(
                "if_else",
                [
                    pc.call_function("equal", [raw["kind"], pa.scalar(kind)]),
                    source,
                    pa.scalar(None, pa.string()),
                ],
            )
            columns.append(lexical.cast(field.type, safe=True))
        # Canonical float source uses Python's exact hexadecimal spelling, which Arrow's
        # decimal-text cast does not parse. This scalar representation boundary preserves
        # subnormals and signed zero; statistics remain explicitly float64.
        float_lexical = pc.call_function(
            "if_else",
            [
                pc.call_function("equal", [raw["kind"], pa.scalar("float")]),
                raw["text_value"],
                pa.scalar(None, pa.string()),
            ],
        )
        columns.append(
            pa.array(
                [
                    None if value is None else float.fromhex(value)
                    for value in float_lexical.to_pylist()
                ],
                type=pa.float64(),
            )
        )
    return pa.Table.from_arrays(columns, schema=projection.schema)


def _owned_input(prepared: PreparedRelease, family: str, **dependencies: Any):
    """Bind current preparation; historical analytical reads keep their archived ABI."""
    import json

    from .analysis_contracts import bind_analysis_family
    from .contracts import execution_payload

    payload = execution_payload(prepared)
    if payload is None or json.loads(payload)["inputs"]["compiler_version"] != "7":
        return None
    return bind_analysis_family(prepared, family).prepare(**dependencies)


def load_packet(
    session: ReadSession, uri: str, *, driver_path: str | None = None
) -> AnalyticalPacket:
    """Capture all mutable relations through an imported snapshot, consuming readers once.

    Caller owns the exporting ReadSession and must close it before long local computation.
    A fresh bulk connection has no data query before SET TRANSACTION SNAPSHOT. It is never pooled.
    """
    from .contracts import execution_payload, require_bound_operation

    require_bound_operation(session.prepared, "capture_analytics")
    compiled = compile_projection(session.prepared, session.binding)
    snapshot = session.connection.execute(select(text("pg_export_snapshot()"))).scalar_one()
    # Exported ids are server-generated; SQLAlchemy renders their SQL literal safely.
    snapshot_sql = (
        postgresql.dialect(paramstyle="named")
        .statement_compiler(postgresql.dialect(paramstyle="named"), None)
        .render_literal_value(snapshot, String())
    )
    connection = (
        adbc.connect(uri, db_kwargs={"adbc.postgresql.type_resolver_mode": "builtin"})
        if driver_path is None
        else adbc_manager.connect(
            driver=driver_path,
            entrypoint="AdbcDriverPostgresqlInit",
            db_kwargs={"uri": uri, "adbc.postgresql.type_resolver_mode": "builtin"},
        )
    )
    with connection as bulk:
        try:
            with bulk.cursor() as cursor:
                cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                cursor.execute("SET TRANSACTION SNAPSHOT " + snapshot_sql)
                cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "true"})
                relations = {}
                for projection in compiled.relations:
                    cursor.execute(compile_sql(projection.statement))
                    with cursor.fetch_record_batch() as reader:
                        relations[projection.name] = normalize_relation(
                            reader.read_all(), projection, compiled.profile
                        )
        finally:
            bulk.rollback()
    return AnalyticalPacket(
        compiled.binding,
        compiled.projection_id,
        compiled.profile.digest,
        MappingProxyType(relations),
        tuple(sorted({p.iri for d in session.prepared.definitions for p in d.properties})),
        compiled.profile.scale,
        execution_model_id=session.prepared.execution_model_id,
        execution_contract=execution_payload(session.prepared),
        input_contract=_owned_input(
            session.prepared,
            "capture",
            release=session.prepared.release_id,
            snapshot=asdict(compiled.binding),
            projection=compiled.projection_id,
            content={"exported_snapshot": snapshot, "projection": compiled.projection_id},
        ),
    )


def capture_packet(
    engine: Any,
    realization_id: str,
    uri: str,
    *,
    release_id: str | None = None,
    driver_path: str | None = None,
) -> AnalyticalPacket:
    """Own both database scopes and end them before returning replayable analytical inputs."""
    from .query import read_session

    with read_session(engine, realization_id, release_id=release_id) as session:
        return load_packet(session, uri, driver_path=driver_path)


def _cleanup_after_failure(error: BaseException, cleanup: Callable[[], None]) -> None:
    try:
        cleanup()
    except BaseException as failure:
        if not isinstance(error, Exception):
            error.add_note(f"analysis cleanup also failed: {failure!r}")
            raise error from None
        if not isinstance(failure, Exception):
            failure.add_note(f"analysis also failed: {error!r}")
            raise failure from error
        raise BaseExceptionGroup("analysis and cleanup failed", [error, failure]) from None


class AnalysisScope:
    """One local relation graph and deterministic ownership of its Arrow inputs/readers."""

    def __init__(
        self,
        packet: CapturedPacket | CandidateInput,
        *,
        threads: int = 4,
        memory_limit: str = "2GB",
        scratch_path: str | Path | None = None,
    ):
        from .contracts import require_payload_operation

        require_payload_operation(
            packet.execution_contract, packet.execution_model_id, "open_analysis"
        )
        require_payload_operation(
            packet.execution_contract, packet.execution_model_id, "close_analysis"
        )
        if packet.input_contract is not None and (
            packet.input_contract.release_id != packet.binding.release_id
            or packet.input_contract.model_id != packet.execution_model_id
            or packet.input_contract.family
            != ("comparison" if isinstance(packet, CandidateInput) else "capture")
        ):
            raise ValueError("analytical input differs from its prepared ownership binding")
        if threads < 1:
            raise ValueError("threads must be positive")
        self.packet = packet
        self._closed = False
        self._readers: list[pa.RecordBatchReader] = []
        self._connections: list[duckdb.DuckDBPyConnection] = []
        self._registered: list[str] = []
        self._views: list[str] = []
        self._operation_id = 0
        config: dict[str, bool | float | int | list[str] | str] = {
            "threads": str(threads),
            "memory_limit": memory_limit,
            "TimeZone": "UTC",
        }
        if scratch_path is not None:
            Path(scratch_path).mkdir(parents=True, exist_ok=True)
        self._scratch = TemporaryDirectory(prefix="corpus-analysis-", dir=scratch_path)
        config["temp_directory"] = self._scratch.name
        try:
            self._connection = duckdb.connect(":memory:", config=config)
            self.connection = BorrowedHandle(self, self._connection)
        except BaseException as error:
            _cleanup_after_failure(error, self._scratch.cleanup)
            raise
        try:
            if isinstance(packet, CapturedPacket) and set(packet.relations) != set(SPINE):
                raise ValueError("packet does not contain the complete normalized spine")
            for name, rows in packet.relations.items():
                if isinstance(packet, CandidateInput):
                    if name != "candidate_input" or rows.schema.metadata != _metadata(
                        packet.binding, packet.projection_id, packet.profile_digest, name
                    ):
                        raise ValueError("candidate relation has wrong bound identity")
                    if rows.column_names != ["fact_id", "occurrence_id", "evidence"]:
                        raise ValueError("candidate relation has wrong compiled shape")
                    self.connection.register(name, rows)
                    self._registered.append(name)
                    continue
                if name not in SPINE:
                    raise ValueError(f"undeclared analytical input {name}")
                expected = _metadata(
                    packet.binding, packet.projection_id, packet.profile_digest, name
                )
                if rows.schema.metadata != expected:
                    raise ValueError(f"wrong release/snapshot/projection metadata for {name}")
                if not rows.schema.equals(
                    pa.schema(_fields(name, packet.scale), metadata=expected), check_metadata=True
                ):
                    raise ValueError(f"wrong compiled shape for {name}")
                for field in rows.schema:
                    if not field.nullable and rows[field.name].null_count:
                        raise ValueError(f"unexpected null in {name}.{field.name}")
                for column, value in (
                    ("release_id", packet.binding.release_id),
                    ("realization_id", packet.binding.realization_id),
                ):
                    matches = pc.call_function("equal", [rows[column], pa.scalar(value)])
                    if pc.call_function("all", [matches]).as_py() is False:
                        raise ValueError(f"wrong row scope in {name}.{column}")
                self.connection.register(name, rows)
                self._registered.append(name)
            self.connection.sql(VIEWS_MACRO_SQL)
        except BaseException as error:
            _cleanup_after_failure(error, self.close)
            raise

    def __enter__(self) -> AnalysisScope:
        return self

    def __exit__(self, kind: object, error: BaseException | None, traceback: object) -> None:
        if error is None:
            self.close()
        else:
            _cleanup_after_failure(error, self.close)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("analysis scope is closed")

    def _borrow(self, value: Any, connection: duckdb.DuckDBPyConnection | None = None) -> Any:
        if isinstance(value, pa.RecordBatchReader):
            if all(reader is not value for reader in self._readers):
                self._readers.append(value)
            return BorrowedReader(self, value, connection)
        if isinstance(value, duckdb.DuckDBPyConnection):
            if value is not self._connection and all(
                connection is not value for connection in self._connections
            ):
                self._connections.append(value)
            return BorrowedHandle(self, value, value)
        if isinstance(value, duckdb.DuckDBPyRelation):
            return BorrowedHandle(self, value, connection)
        return value

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        failures: list[BaseException] = []
        actions = [reader.close for reader in self._readers]
        actions += [
            lambda name=name: self._connection.sql(f'DROP VIEW IF EXISTS "{name}"')
            for name in self._views
        ]
        actions += [
            lambda name=name: self._connection.unregister(name) for name in self._registered
        ]
        actions += [connection.close for connection in self._connections]
        actions += [self._connection.close, self._scratch.cleanup]
        for action in actions:
            try:
                action()
            except BaseException as exc:
                failures.append(exc)
        self.cleanup_failures = tuple(failures)
        # Cancellation remains primary, after every independent teardown has settled.
        for failure in failures:
            if not isinstance(failure, Exception):
                for other in failures:
                    if other is not failure:
                        failure.add_note(f"cleanup also failed: {other!r}")
                raise failure
        if failures:
            raise BaseExceptionGroup("analysis cleanup failed", failures)

    def relation(self, name: str) -> duckdb.DuckDBPyRelation:
        if self._closed:
            raise RuntimeError("analysis scope is closed")
        if name not in self._registered:
            raise KeyError(name)
        relation = self.connection.table(name)
        relation._input_name = name if name in self.packet.relations else None
        return relation

    def fact_support(self) -> duckdb.DuckDBPyRelation:
        """Occurrences retain identity; empty evidence/support is an empty typed list."""
        return self.connection.sql("""
            WITH evidence_items AS (
                SELECT oe.occurrence_id, list(struct_pack(
                    evidence_id := e.evidence_id, source_uri := e.source_uri,
                    locator := e.locator, provider := e.provider,
                    operation_version := e.operation_version) ORDER BY e.evidence_id) AS evidence
                FROM occurrence_evidence oe JOIN evidence e USING (evidence_id)
                GROUP BY oe.occurrence_id
            ), items AS (
                SELECT s.fact_id, list(struct_pack(
                    occurrence_id := o.occurrence_id, source := o.source, item := o.item,
                    report_object_value_id := o.report_object_value_id,
                    report_qualification_value_id := o.report_qualification_value_id,
                    evidence := coalesce(e.evidence, [])) ORDER BY o.occurrence_id) AS supports
                FROM support s JOIN occurrence o USING (occurrence_id, fact_id)
                LEFT JOIN evidence_items e USING (occurrence_id) GROUP BY s.fact_id
            )
            SELECT f.*, coalesce(i.supports, []) AS supports
            FROM fact f LEFT JOIN items i USING (fact_id) ORDER BY f.fact_id
        """)

    def value_roles(self) -> duckdb.DuckDBPyRelation:
        """One-level native Struct/List view preserves recursive child references and ordering."""
        return self.connection.sql("""
            SELECT v.*, coalesce(r.roles, []) AS roles FROM typed_value v LEFT JOIN (
              SELECT parent_value_id, list(struct_pack(role := r.role, position := r.position,
                child_value_id := r.child_value_id, kind := c.kind,
                text_value := c.text_value, decimal_value := c.decimal_value,
                decimal_rounded := c.decimal_rounded, entity_id := c.entity_id)
                ORDER BY r.role, r.position) AS roles
              FROM value_role r JOIN typed_value c ON c.value_id = r.child_value_id
              GROUP BY parent_value_id
            ) r ON r.parent_value_id = v.value_id ORDER BY v.value_id
        """)

    def disagreements(self) -> duckdb.DuckDBPyRelation:
        """Different exact object keys in the same qualified slot; no policy adjudication."""
        return self.connection.sql("""
            WITH slots AS (
              SELECT subject_id, property_id, qualification_key
              FROM fact GROUP BY ALL HAVING count(DISTINCT object_value_id) > 1
            ) SELECT f.* FROM fact f JOIN slots s
              ON f.subject_id = s.subject_id AND f.property_id = s.property_id
              AND f.qualification_key = s.qualification_key
            ORDER BY f.fact_id
        """)

    def operation_disagreements(self, meanings: duckdb.DuckDBPyRelation) -> duckdb.DuckDBPyRelation:
        """Compare explicit operation keys/meaning receipts on this analytical connection.

        Keys identify a declared source-claim projection, not canonical packet facts. Null
        meanings stay unknown variants, matching the existing consolidation set kernel.
        """
        return self._query_input(meanings, "meanings", DISAGREEMENTS_SQL)

    def alias_candidates(
        self, aliases: duckdb.DuckDBPyRelation, references: duckdb.DuckDBPyRelation
    ) -> duckdb.DuckDBPyRelation:
        """Join typed, already normalized (class_id, normalized, entity_id) alias relations."""
        left = self._owned_relation(aliases).set_alias("candidate_alias")
        right = self._owned_relation(references).set_alias("reference_alias")
        return (
            left.join(
                right,
                "candidate_alias.class_id = reference_alias.class_id "
                "AND candidate_alias.normalized = reference_alias.normalized",
            )
            .project(
                "candidate_alias.entity_id AS entity_id, reference_alias.entity_id AS candidate_id"
            )
            .distinct()
            .project("*, count(*) OVER (PARTITION BY entity_id) AS matches")
            .order("entity_id, candidate_id")
        )

    def _owned_relation(self, relation: Any) -> BorrowedHandle:
        self._ensure_open()
        if not isinstance(relation, BorrowedHandle) or relation._owner is not self:
            raise ValueError("operation relation must belong to this analysis scope")
        relation._owner._ensure_open()
        if relation._connection_owner is not self._connection or not isinstance(
            relation._native, duckdb.DuckDBPyRelation
        ):
            raise ValueError("operation relation must use the scope's analytical connection")
        return relation

    def _query_input(self, relation: Any, name: str, sql: str) -> duckdb.DuckDBPyRelation:
        """The native single-input binding owns its name without catalog residue."""
        result = self._owned_relation(relation).query(name, sql)
        if result is None:
            raise RuntimeError("owned analytical kernel did not return a relation")
        return result

    def _view_inputs(self, inputs: Mapping[str, Any]) -> duckdb.DuckDBPyRelation:
        """Bind the fixed six-input macro on this connection; lazy outputs borrow all inputs."""
        self._ensure_open()
        if tuple(inputs) != VIEWS_INPUTS:
            raise ValueError("view kernel requires its six declared inputs")
        # Validate every owner before creating any catalog objects.
        for relation in inputs.values():
            if not isinstance(relation, pa.Table):
                self._owned_relation(relation)
        self._operation_id += 1
        names = []
        for label, relation in inputs.items():
            # Only the counter and code-owned labels contribute identifier text.
            local = f"op{self._operation_id}_{label}"
            names.append(local)
            if isinstance(relation, pa.Table):
                self.connection.register(local, relation)
                self._registered.append(local)
            else:
                self._owned_relation(relation).create_view(local, replace=False)
                self._views.append(local)
        # query_table takes names as values. These generated names contain no quotes;
        # the SQL kernel itself is never rewritten, and the returned SELECT remains lazy.
        arguments = ",".join("'" + name + "'" for name in names)
        return self.connection.sql(f"SELECT * FROM {VIEWS_MACRO_NAME}({arguments})")

    def fuse(self, candidates: duckdb.DuckDBPyRelation) -> duckdb.DuckDBPyRelation:
        """Union typed support/evidence sets without changing occurrence counts."""
        if (
            isinstance(self.packet, CandidateInput)
            and self._owned_relation(candidates)._input_name != "candidate_input"
        ):
            raise ValueError("fusion relation differs from bound candidate universe")
        return self._query_input(candidates, "candidate_input", FUSE_SQL)

    def views(
        self,
        claims: duckdb.DuckDBPyRelation,
        entities: duckdb.DuckDBPyRelation,
        identity: duckdb.DuckDBPyRelation,
        alternatives: duckdb.DuckDBPyRelation,
        specs: Sequence[ViewSpec],
    ) -> duckdb.DuckDBPyRelation:
        """Reuse declared source/match/head/attribute kernels on explicit native projections.

        The caller supplies explicit operation shapes: claim IDs identify the declared operation
        subjects (facts or source occurrences), while the consumer retains their distinct
        canonical fact/occurrence meaning. Statement, entity attributes and identity are
        declared projections; canonical packet relations keep their compiled semantics.
        """
        if isinstance(self.packet, CandidateInput):
            actual = set(
                self._owned_relation(claims).project("claim").to_arrow_table()["claim"].to_pylist()
            )
            expected = set(self.packet.decision_occurrence_ids)
            if actual != expected:
                raise ValueError("operation view claims differ from bound candidate universe")
        names = [spec.name for spec in specs]
        if len(set(names)) != len(names) or {SAME_SLOT, ALTERNATIVE_OF} & set(names):
            raise ValueError("view names repeat or shadow a generic fact")
        declared = set(self.packet.property_ids)
        for spec in specs:
            if spec.source not in declared or not spec.applies_to <= declared:
                raise ValueError("view uses a property outside this release")
        rows = [
            {
                "view": s.name,
                "source": s.source,
                "match_source": s.match_source,
                "match_claim": s.match_claim,
                "head": s.head,
                "attr": s.attr,
                "slot": s.slot,
            }
            for s in specs
        ]
        applies = [{"view": s.name, "predicate": p} for s in specs for p in sorted(s.applies_to)]
        return self._view_inputs(
            {
                "view_claims": claims,
                "view_entities": entities,
                "view_identity": identity,
                "view_alternatives": alternatives,
                "view_specs": pa.Table.from_pylist(rows, schema=VIEW_SPECS),
                "view_applies": pa.Table.from_pylist(applies, schema=VIEW_APPLIES),
            },
        )

    def declared_view(self, property_id: str, *, accepted: bool = False) -> duckdb.DuckDBPyRelation:
        """Filter a release-declared property; retain its typed object and qualification keys."""
        if property_id not in self.packet.property_ids:
            raise ValueError("property is not declared by this release")
        facts = self.relation("fact").filter(duckdb.col("property_id") == duckdb.lit(property_id))
        if accepted:
            facts = facts.join(self.relation("selection").project("fact_id"), "fact_id")
        return facts.order("fact_id")

    @contextmanager
    def reader(
        self, relation: duckdb.DuckDBPyRelation, *, batch_size: int = 65536
    ) -> Generator[pa.RecordBatchReader]:
        """Reader cancellation/exception closes its native result before input teardown."""
        if self._closed:
            raise RuntimeError("analysis scope is closed")
        reader = self._borrow(relation.to_arrow_reader(batch_size))
        try:
            yield reader
        finally:
            reader.close()
            self._readers.remove(reader._native)
