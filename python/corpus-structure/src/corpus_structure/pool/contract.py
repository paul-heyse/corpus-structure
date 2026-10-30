"""The pool contract (pool and interchange §3.1; ADR-0021; coordinator decision 22): model-typed
Arrow relations of one run as of its cut, built by `build` from what the loader reads.

`build(run, registry, observations, reference_entities, reference_aliases, kinds)` is a pure
function: the historical database-test loader supplies its inputs from PostgreSQL; tests supply
Arrow fixtures. The result is the same `Pool`. No relation schema is written here: each one is
M3's (`schema/interchange.py`) or a selection of M3's fields by name, failing on a missing name
(`PoolSchemaError`), so a model change moves the pool with it.

**Inputs** (`raw_schema()`): the rows of `kb.run_observation` (the view carries the cut predicate,
`core/db/overlay.py`), conformed to `run_id` plus M3's `kb.observation` schema; the registry's rows
(`meta.payload_schema`); and, when the run records a reference run, that run's global `kb.entity`
rows and their `kb.entity_alias` rows, under M3's table schemas. Another run's observation, a kind
outside the selection, a reference row of another run or a non-global one is refused
(`PoolInputError`); an unregistered payload schema id, by the readers (`UnknownPayloadSchema`).

**Relations** (`Pool.relations`, by name; each a set, held in its canonical order, given last):
- `observations`, the observation index: every loaded observation without its payload; `run_id`
  plus `kb.observation`'s fields but `payload`; by `id`.
- `payload_<kind>`, one per selected kind: each observation's payload read under its recorded
  schema and upcast to the newest registered version; `observation_id` plus M3's payload class
  fields; by `observation_id`.
- `batches`: one row per `claim_proposal`, its stored batch's envelope; `observation_id` plus
  `core:Batch`'s `unit_ref` and `rendition`; by `observation_id`.
- `entities`, `statements`, `references`, `claims`, `unsupported`: one row per stored batch item
  (an `outside` statement item is a `references` row, an `ExternalReference` candidate);
  `observation_id`, the item class's typed fields (`LIFTED`) and `item`; by `observation_id`,
  `local_ref`.
- `alternatives`: one row per batch `alternatives[]` item; `observation_id`, `ordinal` (its place
  in the batch), `core:AlternativeItem`'s fields and `item`; by `observation_id`, `ordinal`.
- `reference_entities`, `reference_aliases`: the reference run's global entities and their aliases,
  empty without a reference run; `kb.entity` and `kb.entity_alias`; by `id`, and by `entity_id`,
  `normalized`, `alias_kind`.

- **Typed fields** are lifted from the stored item with defaults as values (`establishment` is
  `stated` when the item leaves it out) and `MISSING` as null (T5). `item` is the stored item's
  JSON (`arrow.json`, `cs.class` the item class), the writer's dump, from which T3 hydrates
  (`pool/hydrate.py`). Identity and qualifiers stay in it: their model slots have no Arrow type
  that holds the stored form yet.
- **Supports.** Every candidate row carries the observation it came from (`observation_id`), its
  one support before fusion; fusion unions them (`pool/steps.py`).
- **Metadata** (DA-009). Every relation keeps M3's `cs.*` metadata and adds `cs.relation`,
  `cs.run_id` and, once the run is sealed, `cs.cut_at`. A relation read from payloads also carries
  `cs.payload_schema_id`: the registry id of the payload class version its fields follow. The
  observation index carries each row's recorded `payload_schema_id`; `PoolMeta.payload_schema_ids`
  holds the ids by kind.

**Determinism** (TM §10): every relation is a set held in its canonical order by key, JSON text is
the dump's (compact, in the dump's key order), so equal inputs in any row order give byte-equal
relations. Steps over the pool keep the rules: results are sets, every ordered output has an
explicit key order, aggregates are ordered by key, ties break by key.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import cache
from typing import Any

import pyarrow as pa
from pydantic import MISSING, BaseModel

from corpus_structure.core.batch import StoredBatch, StoredOutside
from corpus_structure.core.payload_schemas import PayloadReaders, PayloadSchemaRow
from corpus_structure.core.payloads import ClaimProposalPayload
from corpus_structure.core.vocab import ObservationKind
from corpus_structure.schema import interchange
from corpus_structure.schema.model import Model, load

OBSERVATIONS = "observations"
BATCHES = "batches"
ENTITIES = "entities"
STATEMENTS = "statements"
REFERENCES = "references"
CLAIMS = "claims"
ALTERNATIVES = "alternatives"
UNSUPPORTED = "unsupported"
REFERENCE_ENTITIES = "reference_entities"
REFERENCE_ALIASES = "reference_aliases"
CANDIDATES = (ENTITIES, STATEMENTS, REFERENCES, CLAIMS, ALTERNATIVES, UNSUPPORTED)
ALL_KINDS: tuple[str, ...] = tuple(sorted(k.value for k in ObservationKind))

# Candidate relations: the item class and the fields lifted from it, by model name.
LIFTED: Mapping[str, tuple[str, tuple[str, ...]]] = {
    ENTITIES: ("EntityItem", ("local_ref", "type", "label", "scope", "extent", "symbol",
                              "scope_segment", "aliases")),
    STATEMENTS: ("StatementItem", ("local_ref", "kind", "anchor")),
    REFERENCES: ("OutsideItem", ("local_ref", "descriptor")),
    CLAIMS: ("ClaimItem", ("local_ref", "predicate", "subject", "statement", "statement_role",
                           "object", "evidence", "establishment", "derived_from", "rule")),
    ALTERNATIVES: ("AlternativeItem", ("refs", "reason")),
    UNSUPPORTED: ("UnsupportedItem", ("local_ref", "reason", "start", "end", "coarse")),
}  # fmt: skip
SORT_KEYS: Mapping[str, tuple[str, ...]] = {
    OBSERVATIONS: ("id",),
    BATCHES: ("observation_id",),
    ALTERNATIVES: ("observation_id", "ordinal"),
    REFERENCE_ENTITIES: ("id",),
    REFERENCE_ALIASES: ("entity_id", "normalized", "alias_kind"),
    **{name: ("observation_id", "local_ref") for name in CANDIDATES if name != ALTERNATIVES},
}


class PoolSchemaError(ValueError):
    """An input relation does not conform to its M3 schema, or the model lacks a field the pool
    contract names."""


class PoolInputError(ValueError):
    """An input row the pool refuses: another run's observation, a kind outside the selection."""


@dataclass(frozen=True)
class RunRow:
    """The facts of the `ops.run` row the pool is loaded for."""

    id: int
    cut_at: datetime | None
    schema_version_id: int
    model_revision_id: int
    key_scheme: int
    reference_run_id: int | None = None


@dataclass(frozen=True)
class PoolMeta:
    run: RunRow
    model_revision: str  # the content hash of the model the relation schemas come from
    kinds: tuple[str, ...]
    payload_schema_ids: Mapping[str, int] = field(default_factory=dict)  # kind -> registry id


@dataclass(frozen=True)
class Pool:
    meta: PoolMeta
    relations: Mapping[str, pa.Table]

    def __getitem__(self, name: str) -> pa.Table:
        return self.relations[name]

    def payload(self, kind: str) -> pa.Table:
        return self.relations[payload_relation(kind)]


def payload_relation(kind: str) -> str:
    return f"payload_{kind}"


# --- Schemas, all from M3 ----------------------------------------------------------------------


@cache
def _model() -> Model:
    return load()


def _field(schema: pa.Schema, name: str, rename: str | None = None) -> pa.Field:
    if name not in schema.names:
        cls = (schema.metadata or {}).get(b"cs.class", b"?").decode()
        raise PoolSchemaError(f"pool: {cls} has no field {name!r}")
    f = schema.field(name)
    return f if rename is None else f.with_name(rename)


def _schema(fields: Iterable[pa.Field], source: pa.Schema, relation: str) -> pa.Schema:
    meta = dict(source.metadata or {})
    meta[b"cs.relation"] = relation.encode()
    return pa.schema(list(fields), metadata=meta)


def _observation() -> pa.Schema:
    return interchange.installed().tables["kb.observation"]


def _run_id() -> pa.Field:
    return _field(interchange.installed().tables["ops.task"], "run_id")


def _observation_id() -> pa.Field:
    return _field(_observation(), "id", "observation_id")


def raw_schema() -> pa.Schema:
    """The loader's observation input: `kb.run_observation`'s columns under M3's types."""
    obs = _observation()
    return _schema([_run_id(), *obs], obs, "run_observation")


def index_schema() -> pa.Schema:
    obs = _observation()
    return _schema([_run_id(), *(f for f in obs if f.name != "payload")], obs, OBSERVATIONS)


def payload_schema(kind: str) -> pa.Schema:
    source = interchange.installed().payload(kind)
    if b"cs.root" in (source.metadata or {}):
        raise PoolSchemaError(f"pool: payload kind {kind!r} is a root class, which has no columns")
    if "observation_id" in source.names:
        raise PoolSchemaError(f"pool: payload kind {kind!r} has a field named observation_id")
    return _schema([_observation_id(), *source], source, payload_relation(kind))


def _class_schema(cls: str) -> pa.Schema:
    return interchange.payload_schema(_model(), cls, interchange.installed().model_revision)


def batches_schema() -> pa.Schema:
    batch = _class_schema("Batch")
    return _schema(
        [_observation_id(), _field(batch, "unit_ref"), _field(batch, "rendition")], batch, BATCHES
    )


def candidate_schema(relation: str) -> pa.Schema:
    cls, names = LIFTED[relation]
    source = _class_schema(cls)
    item = pa.field("item", interchange.JSON, nullable=False, metadata={
        b"cs.class": interchange.prefixed(_model(), cls).encode()})  # fmt: skip
    head = [_observation_id()]
    if relation == ALTERNATIVES:
        head.append(_field(_observation(), "ordinal"))
    return _schema([*head, *(_field(source, n) for n in names), item], source, relation)


def reference_schema(relation: str) -> pa.Schema:
    table = {REFERENCE_ENTITIES: "kb.entity", REFERENCE_ALIASES: "kb.entity_alias"}[relation]
    source = interchange.installed().tables[table]
    return _schema(source, source, relation)


# --- Conformance and ordering ------------------------------------------------------------------


def conform(table: pa.Table, schema: pa.Schema) -> pa.Table:
    """`table` under `schema`: its columns by name in the schema's order, each of the schema's type
    (the loader's field metadata, such as ADBC's `POSTGRESQL:type`, is replaced by M3's)."""
    columns = []
    for f in schema:
        if f.name not in table.column_names:
            relation = schema.metadata[b"cs.relation"].decode()
            raise PoolSchemaError(f"pool: {relation} lacks {f.name}")
        column = table.column(f.name)
        if column.type != f.type:
            raise PoolSchemaError(
                f"pool: {schema.metadata[b'cs.relation'].decode()}.{f.name} is {column.type}, "
                f"the model's type is {f.type}"
            )
        if not f.nullable and column.null_count:
            raise PoolSchemaError(f"pool: {f.name} holds a null where the model forbids one")
        columns.append(column)
    return pa.Table.from_arrays(columns, schema=schema)


def _ordered(table: pa.Table, relation: str) -> pa.Table:
    if table.num_rows < 2:
        return table.combine_chunks()
    return table.sort_by([(k, "ascending") for k in SORT_KEYS[relation]]).combine_chunks()


def _stamp(schema: pa.Schema, items: Mapping[str, str]) -> pa.Schema:
    meta = dict(schema.metadata or {})
    meta |= {k.encode(): v.encode() for k, v in items.items()}
    return schema.with_metadata(meta)


def _cut_text(cut_at: datetime | None) -> dict[str, str]:
    return {} if cut_at is None else {"cs.cut_at": cut_at.astimezone(UTC).isoformat()}


# --- Payload records ---------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _lift(item: BaseModel, names: Sequence[str]) -> dict[str, Any]:
    """The item's fields by name, defaults as values, `MISSING` left out (absent is null)."""
    out = {}
    for name in names:
        value = getattr(item, name)
        if value is not MISSING:
            out[name] = _jsonable(value)
    return out


def _encode(schema: pa.Schema, records: list[dict[str, Any]], relation: str) -> pa.Table:
    records.sort(key=lambda r: tuple(r[k] for k in SORT_KEYS.get(relation, ("observation_id",))))
    return interchange.encode(schema, records)


def _newest(readers: PayloadReaders) -> dict[str, int]:
    """The registry id of each kind's newest registered version: the one readers upcast to."""
    out: dict[str, PayloadSchemaRow] = {}
    for row in readers.rows.values():
        if row.kind not in out or row.version > out[row.kind].version:
            out[row.kind] = row
    return {kind: row.id for kind, row in out.items()}


def _candidate_records(
    oid: int, batch: StoredBatch, records: dict[str, list[dict[str, Any]]]
) -> None:
    def add(relation: str, item: BaseModel, **head: Any) -> None:
        row = {"observation_id": oid, **head, **_lift(item, LIFTED[relation][1])}
        row["item"] = item.model_dump(mode="json")
        records[relation].append(row)

    for entity in batch.entities:
        add(ENTITIES, entity)
    for statement in batch.statements:
        add(REFERENCES if isinstance(statement, StoredOutside) else STATEMENTS, statement)
    for claim in batch.claims:
        add(CLAIMS, claim)
    for ordinal, alternative in enumerate(batch.alternatives):
        add(ALTERNATIVES, alternative, ordinal=ordinal)
    for unsupported in batch.unsupported:
        add(UNSUPPORTED, unsupported)


def _check_reference(run: RunRow, entities: pa.Table, aliases: pa.Table) -> None:
    runs = set(entities.column("run_id").to_pylist())
    if runs - ({run.reference_run_id} - {None}):
        raise PoolInputError(
            f"pool of run {run.id} (reference run {run.reference_run_id}): reference entities "
            f"of runs {sorted(runs)}"
        )
    if set(entities.column("scope").to_pylist()) - {"global"}:
        raise PoolInputError("pool: a reference entity that is not global")
    orphans = set(aliases.column("entity_id").to_pylist()) - set(entities.column("id").to_pylist())
    if orphans:
        raise PoolInputError(f"pool: reference aliases of entities {sorted(orphans)} not loaded")


# --- Building the pool -------------------------------------------------------------------------


def build(
    run: RunRow,
    registry: Iterable[PayloadSchemaRow],
    observations: pa.Table,
    reference_entities: pa.Table | None = None,
    reference_aliases: pa.Table | None = None,
    kinds: Iterable[str] = ALL_KINDS,
) -> Pool:
    """The pool of `run` from its effective observations (module doc). Every payload is read under
    its recorded schema; an unregistered id is refused (`UnknownPayloadSchema`)."""
    selected = tuple(sorted({ObservationKind(k).value for k in kinds}))
    readers = PayloadReaders(registry)
    newest = _newest(readers)
    raw = conform(observations, raw_schema())
    run_ids = set(raw.column("run_id").to_pylist())
    if run_ids - {run.id}:
        raise PoolInputError(f"pool of run {run.id}: observations of runs {sorted(run_ids)}")
    found = set(raw.column("kind").to_pylist())
    if found - set(selected):
        unselected = sorted(found - set(selected))
        raise PoolInputError(f"pool: observations of unselected kinds {unselected}")
    common = {"cs.run_id": str(run.id), **_cut_text(run.cut_at)}

    relations: dict[str, pa.Table] = {}
    index = raw.drop_columns(["payload"])
    relations[OBSERVATIONS] = conform(index, _stamp(index_schema(), common))

    by_kind: dict[str, list[dict[str, Any]]] = {kind: [] for kind in selected}
    candidates: dict[str, list[dict[str, Any]]] = {name: [] for name in CANDIDATES}
    envelopes: list[dict[str, Any]] = []
    rows = zip(
        raw.column("id").to_pylist(),
        raw.column("kind").to_pylist(),
        raw.column("payload_schema_id").to_pylist(),
        raw.column("payload").to_pylist(),
        strict=True,
    )
    for oid, kind, schema_id, text in rows:
        payload = readers.read(schema_id, json.loads(text))
        by_kind[kind].append({"observation_id": oid, **payload.model_dump(mode="json")})
        if isinstance(payload, ClaimProposalPayload):
            batch = payload.batch
            envelopes.append(
                {"observation_id": oid, "unit_ref": batch.unit_ref, "rendition": batch.rendition}
            )
            _candidate_records(oid, batch, candidates)

    ids: dict[str, int] = {}
    for kind, records in by_kind.items():
        stamp = dict(common)
        if kind in newest:
            ids[kind] = newest[kind]
            stamp["cs.payload_schema_id"] = str(newest[kind])
        name = payload_relation(kind)
        relations[name] = _encode(_stamp(payload_schema(kind), stamp), records, name)
    proposal = {}
    if "claim_proposal" in ids:
        proposal = {"cs.payload_schema_id": str(ids["claim_proposal"])}
    relations[BATCHES] = _encode(_stamp(batches_schema(), common | proposal), envelopes, BATCHES)
    for name, records in candidates.items():
        relations[name] = _encode(_stamp(candidate_schema(name), common | proposal), records, name)

    for name, table in ((REFERENCE_ENTITIES, reference_entities),
                        (REFERENCE_ALIASES, reference_aliases)):  # fmt: skip
        schema = _stamp(reference_schema(name), common)
        given = schema.empty_table() if table is None else table
        relations[name] = _ordered(conform(given, schema), name)
    _check_reference(run, relations[REFERENCE_ENTITIES], relations[REFERENCE_ALIASES])
    relations[OBSERVATIONS] = _ordered(relations[OBSERVATIONS], OBSERVATIONS)

    meta = PoolMeta(run, interchange.installed().model_revision, selected, ids)
    return Pool(meta, relations)
