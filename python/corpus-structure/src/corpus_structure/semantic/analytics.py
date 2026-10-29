"""Release-bound Core → shared PostgreSQL snapshot → Arrow → scoped DuckDB.

The packet is replayable columnar input. Database transactions finish before analytical
compute; only explicitly owned result readers extend a local scope's lifetime.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
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

from corpus_structure.pool.steps import ViewSpec

from .analytical_profile import AnalyticalProfile
from .identity import canonical_bytes
from .metadata import PHYSICAL_MODEL_ID, table
from .types import PreparedRelease

if TYPE_CHECKING:
    from .query import ReadSession, SnapshotBinding

COMPILER_VERSION = "analytical-2"
SPINE = (
    "entity",
    "membership",
    "membership_support",
    "typed_value",
    "value_role",
    "fact",
    "occurrence",
    "support",
    "selection",
    "evidence",
    "occurrence_evidence",
    "derivation",
    "derivation_premise",
    "coverage",
    "occurrence_establishment",
    "assessment",
    "evidence_source",
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
class AnalyticalPacket:
    binding: SnapshotBinding
    projection_id: str
    profile_digest: str
    relations: Mapping[str, pa.Table]
    property_ids: tuple[str, ...] = ()
    scale: int = 12

    def __post_init__(self) -> None:
        object.__setattr__(self, "relations", MappingProxyType(dict(self.relations)))


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


def compile_projection(prepared: PreparedRelease, binding: SnapshotBinding) -> CompiledProjection:
    """One trusted physical mapping produces Core selections and their exact Arrow schemas."""
    if prepared.release_id != binding.release_id:
        raise ValueError("projection release differs from snapshot")
    profile = AnalyticalProfile.from_release(prepared)
    identity = (
        "projection:"
        + sha256(
            canonical_bytes(
                [
                    prepared.release_id,
                    PHYSICAL_MODEL_ID,
                    COMPILER_VERSION,
                    profile.digest,
                ]
            )
        ).hexdigest()
    )
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


def load_packet(
    session: ReadSession, uri: str, *, driver_path: str | None = None
) -> AnalyticalPacket:
    """Capture all mutable relations through an imported snapshot, consuming readers once.

    Caller owns the exporting ReadSession and must close it before long local computation.
    A fresh bulk connection has no data query before SET TRANSACTION SNAPSHOT. It is never pooled.
    """
    compiled = compile_projection(session.prepared, session.binding)
    snapshot = session.connection.execute(select(text("pg_export_snapshot()"))).scalar_one()
    # Exported ids are server-generated; SQLAlchemy renders their SQL literal safely.
    snapshot_sql = str(
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


class AnalysisScope:
    """One local relation graph and deterministic ownership of its Arrow inputs/readers."""

    def __init__(
        self,
        packet: AnalyticalPacket,
        *,
        threads: int = 4,
        memory_limit: str = "2GB",
        scratch_path: str | Path | None = None,
    ):
        if threads < 1:
            raise ValueError("threads must be positive")
        self.packet = packet
        self._closed = False
        self._readers: list[pa.RecordBatchReader] = []
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
            self.connection = duckdb.connect(":memory:", config=config)
        except BaseException:
            self._scratch.cleanup()
            raise
        try:
            if set(packet.relations) != set(SPINE):
                raise ValueError("packet does not contain the complete normalized spine")
            for name, rows in packet.relations.items():
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
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> AnalysisScope:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            for reader in self._readers:
                reader.close()
        finally:
            try:
                for name in self._registered:
                    self.connection.unregister(name)
                for name in self._views:
                    self.connection.sql(f'DROP VIEW IF EXISTS "{name}"')
            finally:
                try:
                    self.connection.close()
                finally:
                    self._scratch.cleanup()

    def relation(self, name: str) -> duckdb.DuckDBPyRelation:
        if self._closed:
            raise RuntimeError("analysis scope is closed")
        if name not in self._registered:
            raise KeyError(name)
        return self.connection.table(name)

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

    def alias_candidates(
        self, aliases: duckdb.DuckDBPyRelation, references: duckdb.DuckDBPyRelation
    ) -> duckdb.DuckDBPyRelation:
        """Join typed, already normalized (class_id, normalized, entity_id) alias relations."""
        left = aliases.set_alias("candidate_alias")
        right = references.set_alias("reference_alias")
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

    def _compose(
        self, sql: str, inputs: Mapping[str, duckdb.DuckDBPyRelation | pa.Table]
    ) -> duckdb.DuckDBPyRelation:
        """Bind operation projections once into this graph; scope owns their lifetime."""
        import re

        self._operation_id += 1
        names = {}
        for name, relation in inputs.items():
            local = f"op{self._operation_id}_{name}"
            names[name] = local
            if isinstance(relation, pa.Table):
                self.connection.register(local, relation)
                self._registered.append(local)
            else:
                relation.create_view(local)
                self._views.append(local)
        sql = re.sub(
            r"\b(" + "|".join(map(re.escape, names)) + r")\b", lambda m: names[m.group()], sql
        )
        return self.connection.sql(sql)

    def fuse(self, candidates: duckdb.DuckDBPyRelation) -> duckdb.DuckDBPyRelation:
        """Union typed evidence/support sets per semantic fact, preserving candidate count.

        Input is an operation-shaped relation (fact_id, occurrence_id, evidence LIST<STRUCT>).
        It may contain repeated candidates; identity is never inferred from rounded values.
        """
        return self._compose(
            """
            WITH evidence_items AS (
                SELECT DISTINCT fact_id, unnest(evidence) AS item FROM candidate_input
            ), evidence_sets AS (
                SELECT fact_id, list(item ORDER BY item) AS evidence
                FROM evidence_items GROUP BY fact_id
            ), support_sets AS (
                SELECT fact_id, coalesce(list(DISTINCT occurrence_id ORDER BY occurrence_id)
                    FILTER (WHERE occurrence_id IS NOT NULL), []) AS supports,
                    count(*) AS candidates FROM candidate_input GROUP BY fact_id
            ) SELECT s.*, coalesce(e.evidence, []) AS evidence
              FROM support_sets s LEFT JOIN evidence_sets e USING (fact_id) ORDER BY fact_id
        """,
            {"candidate_input": candidates},
        )

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
        from corpus_structure.pool.duckdb_engine import _APPLIES, _SPECS, _VIEWS

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
        return self._compose(
            _VIEWS,
            {
                "view_claims": claims,
                "view_entities": entities,
                "view_identity": identity,
                "view_alternatives": alternatives,
                "view_specs": pa.Table.from_pylist(rows, schema=_SPECS),
                "view_applies": pa.Table.from_pylist(applies, schema=_APPLIES),
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
    ) -> Iterator[pa.RecordBatchReader]:
        """Reader cancellation/exception closes its native result before input teardown."""
        if self._closed:
            raise RuntimeError("analysis scope is closed")
        reader = relation.to_arrow_reader(batch_size)
        self._readers.append(reader)
        try:
            yield reader
        finally:
            reader.close()
            self._readers.remove(reader)
