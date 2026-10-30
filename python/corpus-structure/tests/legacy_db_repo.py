"""Historical database oracle; not part of product persistence.

The repository (foundations §3.8; D3 §5 "Writers", §7): the one writer of evidence, observation,
intervention and golden rows, and the primitives other writers use.

Every function takes the caller's SQLAlchemy `Connection` and runs inside its transaction; none
commits. Values arrive validated (the validation boundary is where JSONB enters); the repository
dumps models with defaults omitted and never validates again. An absent value is SQL NULL, never
JSON `null`.

- `get_or_create(conn, table, values, unique)`: insert, or return the existing row's id, with
  whether it was new (PostgreSQL 18's `RETURNING old`).
- `store_rendition(conn, document, content, build)`: the rendition once per `(document_id,
  content_digest)`, its segments only when it is new (ids pre-allocated, one COPY), and the build
  row every time; a build that names another rendition for the same configuration and bytes is
  refused (`NondeterministicIngest`).
- `read_rendition(conn, rendition_id)`: a rendition's content rebuilt from its stored row and
  segments (canonical text, segment tree with attributes and parse status, macro table), and
  `segment_ids(conn, rendition_id)`: its segment ids by key; the one read of stored renditions
  (consolidation, the method reader).
- `upsert_spans(conn, rendition_id, ranges)`: one `INSERT … SELECT … FROM unnest(…) ON CONFLICT DO
  NOTHING RETURNING`, the text cut from the canonical text and the smallest containing segment found
  in SQL; a range outside the text is refused before any write (`SpanOutOfText`, INV-10).
- `write_observations(conn, task_id, attempt, rows)`: after the fencing check (`FencingLost`
  when the task's attempt moved on), binary COPY with the generated column types; each row's
  `payload_schema_id` is the registry's for the payload's kind, and a kind with none is refused
  before any write (`UnregisteredPayload`).
- `record_intervention`, `store_golden_pass`, `set_golden_unit`, `insert_artifact`: typed
  primitives over the generated columns; the payload-bearing ones take a registered
  `payload_schema_id` (the foreign key refuses any other).
- `copy_rows`, `allocate_ids`, `insert_returning`: the bulk primitives.
- `payload_readers(conn)` and `read_payload`: reader dispatch by recorded schema (M4), refusing an
  unknown id with `UnknownPayloadSchema`.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from psycopg.types.json import Jsonb
from pydantic import BaseModel
from sqlalchemy import (
    BigInteger,
    Boolean,
    Connection,
    Double,
    Integer,
    SmallInteger,
    Table,
    Text,
    insert,
    literal_column,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, REAL, REGCONFIG, TIMESTAMP
from sqlalchemy.dialects.postgresql import insert as pg_insert

from corpus_structure.core.db.legacy_metadata import metadata
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    content_digest,
    segment_key,
)
from corpus_structure.core.evidence import rendition_key as make_rendition_key
from corpus_structure.core.payload_schemas import PayloadReaders, PayloadSchemaRow

T = metadata.tables


class RepositoryError(ValueError):
    """A write the repository refuses before touching the database."""


class NondeterministicIngest(RepositoryError):
    """A build names another rendition for the same document bytes and configuration."""


class SpanOutOfText(RepositoryError):
    """A span range lies outside its rendition's canonical text (INV-10)."""


class FencingLost(RepositoryError):
    """The task's attempt moved on: this worker's lease was lost, so it writes nothing."""


class UnregisteredPayload(RepositoryError):
    """A payload's kind has no registered payload schema."""


# --- Bulk primitives ---------------------------------------------------------------------------


def _pg_type(typ: Any) -> str:
    """The PostgreSQL type name COPY's `set_types` takes for a generated column type."""
    if isinstance(typ, ARRAY):
        return _pg_type(typ.item_type) + "[]"
    names: list[tuple[type, str]] = [
        (BigInteger, "int8"),
        (SmallInteger, "int2"),
        (Integer, "int4"),
        (REAL, "float4"),
        (Double, "float8"),
        (Boolean, "bool"),
        (TIMESTAMP, "timestamptz"),
        (JSONB, "jsonb"),
        (BYTEA, "bytea"),
        (REGCONFIG, "regconfig"),
        (Text, "text"),
    ]
    for cls, name in names:
        if isinstance(typ, cls):
            return name
    raise TypeError(f"no COPY type for {typ!r}")


def copy_rows(
    conn: Connection, table: Table, columns: Sequence[str], rows: Iterable[Sequence[Any]]
) -> int:
    """Binary COPY of `rows` into `table`'s `columns`, typed from the generated columns, inside
    the caller's transaction (through `driver_connection`, never its own commit). JSONB values are
    dumped; None is NULL, and a JSON null is passed as `Jsonb(None)`. Explicit identity values are
    written as given (COPY overrides them)."""
    cols = [table.c[c] for c in columns]
    types = [_pg_type(c.type) for c in cols]
    json_at = [i for i, c in enumerate(cols) if isinstance(c.type, JSONB)]
    # regconfig has no binary dumper; its binary form is its oid, so send the oid typed `oid`
    reg_at = [i for i, c in enumerate(cols) if isinstance(c.type, REGCONFIG)]
    for i in reg_at:
        types[i] = "oid"
    prepared = [list(row) for row in rows]
    oids = {
        name: _regconfig_oid(conn, name)  # resolved before the COPY holds the connection
        for name in {r[i] for r in prepared for i in reg_at if r[i] is not None}
    }
    raw = conn.connection.driver_connection
    assert raw is not None
    names = ", ".join(f'"{c}"' for c in columns)
    n = 0
    statement = f"COPY {table.fullname} ({names}) FROM STDIN (FORMAT BINARY)"
    with raw.cursor() as cursor, cursor.copy(statement) as copy:
        copy.set_types(types)
        for values in prepared:
            for i in json_at:  # a value already wrapped (a JSON null as `Jsonb(None)`) is kept
                if values[i] is not None and not isinstance(values[i], Jsonb):
                    values[i] = Jsonb(values[i])
            for i in reg_at:
                if values[i] is not None:
                    values[i] = oids[values[i]]
            copy.write_row(values)
            n += 1
    return n


def _regconfig_oid(conn: Connection, name: str) -> int:
    query = text("SELECT CAST(CAST(:n AS regconfig) AS oid)")
    return int(conn.execute(query, {"n": name}).scalar_one())


def allocate_ids(conn: Connection, table: Table, n: int) -> list[int]:
    """`n` ids from the table's identity sequence, in order."""
    if n == 0:
        return []
    rows = conn.execute(
        text("SELECT nextval(pg_get_serial_sequence(:t, 'id')) FROM generate_series(1, :n)"),
        {"t": table.fullname, "n": n},
    )
    return [int(r[0]) for r in rows]


def insert_returning(
    conn: Connection, table: Table, rows: Sequence[Mapping[str, Any]]
) -> list[int]:
    """Insert `rows` and return their ids in row order (`insertmanyvalues`)."""
    if not rows:
        return []
    stmt = insert(table).returning(table.c.id, sort_by_parameter_order=True)
    return [int(r[0]) for r in conn.execute(stmt, list(rows))]


def get_or_create(
    conn: Connection, table: Table, values: Mapping[str, Any], unique: Sequence[str]
) -> tuple[int, bool]:
    """The id of the row with `values`' unique columns, inserted if absent, and whether it was
    new. The conflict update rewrites one unique column to itself, so `RETURNING` sees the row."""
    stmt = pg_insert(table).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=list(unique), set_={unique[0]: stmt.excluded[unique[0]]}
    ).returning(table.c.id, literal_column("old.id IS NULL").label("created"))
    row = conn.execute(stmt).one()
    return int(row.id), bool(row.created)


# --- Renditions and spans ----------------------------------------------------------------------


@dataclass(frozen=True)
class Build:
    """One adapter configuration's build of a document (`kb.rendition_build`)."""

    method_config_id: int
    task_id: int
    payload_schema_id: int
    parse_detail: Mapping[str, Any] = field(default_factory=dict)
    ts_config: str = "english"


@dataclass(frozen=True)
class StoredRendition:
    id: int
    key: str
    created: bool


def _segment_rows(
    ren_id: int, ren_key: str, content: RenditionContent, ids: Iterator[int], ts_config: str
) -> list[tuple[Any, ...]]:
    out: list[tuple[Any, ...]] = []

    def walk(segment: Segment, parent: int | None, ordinal: int, depth: int) -> None:
        own = next(ids)
        out.append(
            (
                own,
                ren_id,
                segment_key(ren_key, segment.kind, segment.start, segment.end),
                parent,
                segment.kind.value,
                ordinal,
                depth,
                segment.start,
                segment.end,
                content.text(segment),
                ts_config,
                dict(segment.attrs),
                segment.parse_status.value,
                segment.parse_reason,
            )
        )
        for i, child in enumerate(segment.children):
            walk(child, own, i, depth + 1)

    walk(content.document, None, 0, 0)
    return out


SEGMENT_COLUMNS = (
    "id",
    "rendition_id",
    "key",
    "parent_id",
    "kind",
    "ordinal",
    "depth",
    "start_offset",
    "end_offset",
    "text",
    "ts_config",
    "attrs",
    "parse_status",
    "parse_reason",
)


def store_rendition(
    conn: Connection, document_id: int, document_key: str, content: RenditionContent, build: Build
) -> StoredRendition:
    """The rendition of `content` for the document, written once; the build recorded every time."""
    rendition, builds = T["kb.rendition"], T["kb.rendition_build"]
    digest = content_digest(content)
    key = make_rendition_key(document_key, digest)
    inserted = conn.execute(
        pg_insert(rendition)
        .values(
            document_id=document_id,
            key=key,
            content_digest=digest,
            canonical_text=content.canonical_text,
            macros={
                k: v.model_dump(mode="json", exclude_defaults=True)
                for k, v in content.macros.items()
            },
            parse_status=content.parse_status.value,
        )
        .on_conflict_do_nothing(index_elements=["document_id", "content_digest"])
        .returning(rendition.c.id)
    ).first()
    created = inserted is not None
    if inserted is not None:
        ren_id = int(inserted[0])
        segments = list(content.document.walk())
        ids = iter(allocate_ids(conn, T["kb.segment"], len(segments)))
        rows = _segment_rows(ren_id, key, content, ids, build.ts_config)
        copy_rows(conn, T["kb.segment"], SEGMENT_COLUMNS, rows)
    else:
        ren_id = int(
            conn.execute(
                select(rendition.c.id).where(
                    rendition.c.document_id == document_id, rendition.c.content_digest == digest
                )
            ).scalar_one()
        )
    conn.execute(
        pg_insert(builds)
        .values(
            document_id=document_id,
            method_config_id=build.method_config_id,
            rendition_id=ren_id,
            task_id=build.task_id,
            parse_detail=dict(build.parse_detail),
            payload_schema_id=build.payload_schema_id,
        )
        .on_conflict_do_nothing(index_elements=["document_id", "method_config_id"])
    )
    recorded = conn.execute(
        select(builds.c.rendition_id).where(
            builds.c.document_id == document_id, builds.c.method_config_id == build.method_config_id
        )
    ).scalar_one()
    if recorded != ren_id:
        raise NondeterministicIngest(
            f"document {document_id} under configuration {build.method_config_id} built rendition "
            f"{recorded} before and {ren_id} now: the ingest is not deterministic"
        )
    return StoredRendition(ren_id, key, created)


_SPANS = text("""
WITH r(s, e) AS (SELECT * FROM unnest(CAST(:starts AS integer[]), CAST(:ends AS integer[])))
INSERT INTO kb.span (rendition_id, start_offset, end_offset, segment_id, text)
SELECT ren.id, r.s, r.e,
       (SELECT seg.id FROM kb.segment seg
        WHERE seg.rendition_id = ren.id AND seg.start_offset <= r.s AND r.e <= seg.end_offset
        ORDER BY seg.end_offset - seg.start_offset, seg.depth DESC LIMIT 1),
       substr(ren.canonical_text, r.s + 1, r.e - r.s)
FROM r CROSS JOIN kb.rendition ren
WHERE ren.id = :rendition
ON CONFLICT (rendition_id, start_offset, end_offset) DO NOTHING
RETURNING id, start_offset, end_offset
""")
_EXISTING = text("""
SELECT s.id, s.start_offset, s.end_offset
FROM kb.span s JOIN unnest(CAST(:starts AS integer[]), CAST(:ends AS integer[])) AS r(s, e)
  ON s.start_offset = r.s AND s.end_offset = r.e
WHERE s.rendition_id = :rendition
""")


def read_rendition(conn: Connection, rendition_id: int) -> RenditionContent:
    """A rendition's content rebuilt from its stored row and segments (module doc)."""
    ren, seg = T["kb.rendition"], T["kb.segment"]
    row = conn.execute(
        select(ren.c.canonical_text, ren.c.macros).where(ren.c.id == rendition_id)
    ).one()
    rows = conn.execute(
        select(seg.c.id, seg.c.parent_id, seg.c.kind, seg.c.start_offset, seg.c.end_offset,
               seg.c.attrs, seg.c.parse_status, seg.c.parse_reason)
        .where(seg.c.rendition_id == rendition_id)
        .order_by(seg.c.depth.desc(), seg.c.ordinal)
    ).all()  # fmt: skip
    children: dict[int | None, list[Segment]] = {}
    root = None
    for r in rows:  # deepest first, so children exist before their parents
        segment = Segment(kind=r.kind, start=r.start_offset, end=r.end_offset,
                          parse_status=r.parse_status, parse_reason=r.parse_reason,
                          attrs=r.attrs, children=tuple(children.pop(r.id, [])))  # fmt: skip
        if r.parent_id is None:
            root = segment
        children.setdefault(r.parent_id, []).append(segment)
    if root is None:
        raise LookupError(f"rendition {rendition_id} has no segments")
    macros = {k: MacroDef.model_validate(v) for k, v in (row.macros or {}).items()}
    return RenditionContent(canonical_text=row.canonical_text, document=root, macros=macros)


def segment_ids(conn: Connection, rendition_id: int) -> dict[str, int]:
    """A rendition's stored segment ids by segment key."""
    seg = T["kb.segment"]
    rows = conn.execute(select(seg.c.key, seg.c.id).where(seg.c.rendition_id == rendition_id))
    return {str(k): int(i) for k, i in rows}


def upsert_spans(
    conn: Connection, rendition_id: int, ranges: Sequence[tuple[int, int]]
) -> list[int]:
    """The span id of each `(start, end)` range, inserting the new ones (module doc)."""
    if not ranges:
        return []
    length = conn.execute(
        text("SELECT char_length(canonical_text) FROM kb.rendition WHERE id = :r"),
        {"r": rendition_id},
    ).scalar_one()
    bad = [(s, e) for s, e in ranges if not 0 <= s < e <= length]
    if bad:
        raise SpanOutOfText(
            f"rendition {rendition_id} has {length} characters; ranges {bad} lie "
            "outside it or are empty"
        )
    params = {
        "rendition": rendition_id,
        "starts": [s for s, _ in ranges],
        "ends": [e for _, e in ranges],
    }
    ids = {(r.start_offset, r.end_offset): int(r.id) for r in conn.execute(_SPANS, params)}
    missing = [r for r in ranges if r not in ids]
    if missing:  # existing rows, and keys a concurrent writer took
        for r in conn.execute(_EXISTING, params):
            ids[(r.start_offset, r.end_offset)] = int(r.id)
    return [ids[r] for r in ranges]


# --- Observations and the payload registry -----------------------------------------------------


@dataclass(frozen=True)
class ObservationRow:
    """One observation, its references resolved and its payload the validated model of its kind."""

    ordinal: int
    kind: str
    payload: BaseModel
    outcome: str = "produced"
    rendition_id: int | None = None
    segment_id: int | None = None
    span_id: int | None = None
    score: float | None = None


OBSERVATION_COLUMNS = (
    "task_id",
    "ordinal",
    "kind",
    "rendition_id",
    "segment_id",
    "span_id",
    "payload",
    "payload_schema_id",
    "score",
    "outcome",
)


def registered_ids(conn: Connection, kinds: Iterable[str]) -> dict[str, int]:
    """Each kind's registered payload schema: the newest version's row id."""
    ps = T["meta.payload_schema"]
    rows = conn.execute(
        select(ps.c.kind, ps.c.id)
        .where(ps.c.kind.in_(sorted(set(kinds))))
        .order_by(ps.c.kind, ps.c.version.desc())
    )
    out: dict[str, int] = {}
    for kind, id_ in rows:
        out.setdefault(str(kind), int(id_))
    return out


def fence(conn: Connection, task_id: int, attempt: int) -> None:
    """Lock the task row at this attempt, or refuse: the lease was lost (D3 §8 fencing)."""
    task = T["ops.task"]
    found = conn.execute(
        select(task.c.id).where(task.c.id == task_id, task.c.attempt == attempt).with_for_update()
    ).first()
    if found is None:
        raise FencingLost(f"task {task_id} is no longer at attempt {attempt}: nothing is written")


def write_observations(
    conn: Connection, task_id: int, attempt: int, rows: Sequence[ObservationRow]
) -> int:
    """The task's observations by binary COPY, after the fencing check (module doc)."""
    ids = registered_ids(conn, (r.kind for r in rows))
    unregistered = sorted({r.kind for r in rows} - set(ids))
    if unregistered:
        raise UnregisteredPayload(f"no registered payload schema for {unregistered}")
    fence(conn, task_id, attempt)
    return copy_rows(
        conn,
        T["kb.observation"],
        OBSERVATION_COLUMNS,
        (
            (
                task_id,
                r.ordinal,
                r.kind,
                r.rendition_id,
                r.segment_id,
                r.span_id,
                r.payload.model_dump(mode="json"),
                ids[r.kind],
                r.score,
                r.outcome,
            )
            for r in rows
        ),
    )


def payload_readers(conn: Connection) -> PayloadReaders:
    """Reader dispatch over the registry's rows."""
    ps = T["meta.payload_schema"]
    rows = conn.execute(
        select(ps.c.id, ps.c["class"], ps.c.kind, ps.c.version, ps.c.parent_id, ps.c.upcaster)
    )
    return PayloadReaders(
        PayloadSchemaRow(int(r[0]), str(r[1]), str(r[2]), int(r[3]), r[4], r[5]) for r in rows
    )


def read_payload(readers: PayloadReaders, payload_schema_id: int, payload: Any) -> Any:
    """A stored payload read under its recorded schema; an unknown id is refused."""
    return readers.read(payload_schema_id, payload)


# --- Typed primitives --------------------------------------------------------------------------


def record_intervention(conn: Connection, values: Mapping[str, Any]) -> int:
    """An `ops.intervention` row (its `payload_schema_id` names its refs' schema)."""
    return insert_returning(conn, T["ops.intervention"], [dict(values)])[0]


def store_golden_pass(conn: Connection, values: Mapping[str, Any]) -> int:
    """An `eval.golden_pass` row: the authored batch as written, never rewritten."""
    return insert_returning(conn, T["eval.golden_pass"], [dict(values)])[0]


def set_golden_unit(
    conn: Connection, unit_id: int, status: str, agreement: Mapping[str, Any]
) -> None:
    """A golden unit's status and evaluation's agreement result."""
    unit = T["eval.golden_unit"]
    done = conn.execute(
        update(unit).where(unit.c.id == unit_id).values(status=status, agreement=dict(agreement))
    )
    if done.rowcount != 1:
        raise RepositoryError(f"no golden unit {unit_id}")


def insert_artifact(conn: Connection, values: Mapping[str, Any]) -> int | None:
    """A `meta.compiled_artifact` row, or None when its identity (schema version, compiler,
    compiler version, kind) exists: artifacts are added, never updated (P0CL-15)."""
    table = T["meta.compiled_artifact"]
    identity = ["schema_version_id", "compiler", "compiler_version", "kind"]
    stmt = (pg_insert(table).values(**values).on_conflict_do_nothing(index_elements=identity)
            .returning(table.c.id))  # fmt: skip
    row = conn.execute(stmt).first()
    return None if row is None else int(row[0])
