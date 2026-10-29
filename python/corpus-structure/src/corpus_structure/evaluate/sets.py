"""Golden sets: the source run, the sampler, the golden run and its settlement, the unit list and
the status (D7 §3.1; D3 §7, §8; D8 §2.2; evaluation §3.2, §3.4, P0-E-1).

**The source run** (`--from-run`, default the latest finished run whose `scope` stage covered every
first-pass page) supplies the renditions (`kb.run_rendition`), the annotation units, the author
markup hints and M02's math shares (`segment.math_share`, read through reuse); its M13 output is
what the golden packets read, so an `ingest` run (no M13) is refused. A page's locator page and its
corpus-index columns come from the source profile its rendition was built with.

**The pool** is the claim-bearing annotation units of the split's first-pass pages on the source
run's renditions: the statement kind is the unit's markup hint, else `narrative`; kinds outside
`claim_bearing` (proof, solution) and hints marked not claim-bearing are left out. **Forced units**
(dev only) are the units the pack's forced slices select (`ops.debug_slice`, includes expanded),
resolved with I0 on the source run's renditions; a refusal, or a unit outside the pool, fails.

**The sampler** (`sample`, pure): strata are statement kind x math-share tercile, cut at the pool's
1/3 and 2/3 order statistics; each stratum gets N x its share floored, at least one place, the rest
by largest remainder; forced units count towards their strata, and where they exceed a quota the
excess comes from the stratum furthest above its exact share, never below max(1, its forced
count). Within a stratum units follow `sha256(unit_key + str(seed))`, forced units skipped.

**`create_golden_set`** writes, in one transaction: the set with its frozen schema and guideline
versions (the source run's) and `sampling`; its `draft` units; the golden run (kind `golden`, parent
the source run, its `scope` option naming the set and its units with their hash) moved to
`awaiting_agent`; and one `golden.pass/a` and one `golden.pass/b` task per unit through
orchestration's task creation, stage `evaluate`, unit type `golden_unit`.

**`settle_golden_run`** finishes a golden run through orchestration's `finish_run` once every unit
of its set that is not retired is `adjudicated`. **`golden_units`** is the dev set's unit list and
its hash, the `{golden_set}` include's input.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Connection, text

from corpus_structure.core.evidence import segment_key
from corpus_structure.core.locators import (
    LocatorIndex,
    LocatorRefused,
    LocatorSyntaxError,
    page_of,
)
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.vocab import (
    CLAIM_BEARING,
    DocumentSplit,
    GoldenUnitStatus,
    RunKind,
    RunStatus,
    Stage,
    StatementKind,
    TaskUnitType,
)
from corpus_structure.evaluate import goldens
from corpus_structure.evaluate.split import EvalConfig, split_of
from corpus_structure.orchestrate import context, runs, tasks
from corpus_structure.orchestrate.project import PackVersions
from corpus_structure.orchestrate.registry import MethodRegistry, RegistryError

SAMPLER_VERSION = "1"
GOLDEN_METHOD = "golden.pass"
M02, MATH_SHARE = "profile.segments", "segment.math_share"
TRUE = frozenset({"yes", "true", "1"})
DONE = ("done", "empty", "reused")


class GoldenSetError(ValueError):
    """A golden set that cannot be created, settled or listed as asked."""


# --- The sampler ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolUnit:
    key: str
    kind: str
    math_share: float
    document_id: int = 0
    rendition_id: int = 0


def _order(key: str, seed: int) -> str:
    return hashlib.sha256((key + str(seed)).encode("utf-8")).hexdigest()


def cut_points(shares: Sequence[float]) -> tuple[float, float]:
    """The pool's 1/3 and 2/3 order statistics (the ceil(n p)-th smallest)."""
    s = sorted(shares)
    n = len(s)
    return s[math.ceil(n / 3) - 1], s[math.ceil(2 * n / 3) - 1]


def stratum(unit: PoolUnit, cuts: tuple[float, float]) -> str:
    tercile = 0 if unit.math_share <= cuts[0] else 1 if unit.math_share <= cuts[1] else 2
    return f"{unit.kind}/t{tercile}"


def allocate(
    pool: Mapping[str, int], forced: Mapping[str, int], size: int
) -> dict[str, dict[str, float]]:
    """Places per stratum (module doc): pool, exact share, quota and forced count each."""
    total = sum(pool.values())
    exact = {s: size * n / total for s, n in pool.items()}
    quota = {s: max(1, math.floor(x)) for s, x in exact.items()}
    by_remainder = sorted(pool, key=lambda s: (-(exact[s] - math.floor(exact[s])), s))
    for s in by_remainder:
        if sum(quota.values()) >= size:
            break
        if quota[s] < pool[s]:
            quota[s] += 1
    for s, f in forced.items():
        quota[s] = max(quota[s], f)
    while sum(quota.values()) > size:
        shrinkable = [s for s in pool if quota[s] > max(1, forced.get(s, 0))]
        if not shrinkable:
            raise GoldenSetError(
                f"{size} places cannot hold one unit per stratum and the forced units"
            )
        quota[max(shrinkable, key=lambda s: (quota[s] - exact[s], s))] -= 1
    return {
        s: {"pool": pool[s], "exact": exact[s], "quota": quota[s], "forced": forced.get(s, 0)}
        for s in sorted(pool)
    }


@dataclass(frozen=True)
class Sample:
    units: tuple[str, ...]  # sorted
    sampling: dict[str, Any]


def sample(pool: Sequence[PoolUnit], size: int, seed: int, forced: Collection[str] = ()) -> Sample:
    """The sample (module doc); input order is irrelevant."""
    by_key = {u.key: u for u in pool}
    forced = set(forced)
    if missing := sorted(forced - set(by_key)):
        raise GoldenSetError(f"forced units outside the pool: {missing}")
    if len(forced) > size:
        raise GoldenSetError(f"{len(forced)} forced units exceed the set size {size}")
    if size > len(by_key):
        raise GoldenSetError(f"the pool holds {len(by_key)} units, fewer than {size}")
    cuts = cut_points([u.math_share for u in by_key.values()])
    strata: dict[str, list[str]] = {}
    for key in sorted(by_key):
        strata.setdefault(stratum(by_key[key], cuts), []).append(key)
    forced_by = {s: sum(k in forced for k in keys) for s, keys in strata.items()}
    allocation = allocate({s: len(k) for s, k in strata.items()}, forced_by, size)
    chosen = set(forced)
    for s, keys in strata.items():
        free = sorted((k for k in keys if k not in forced), key=lambda k: (_order(k, seed), k))
        chosen |= set(free[: int(allocation[s]["quota"]) - forced_by[s]])
    return Sample(
        tuple(sorted(chosen)),
        {
            "sampler_version": SAMPLER_VERSION,
            "seed": seed,
            "size": size,
            "cut_points": list(cuts),
            "allocation": allocation,
            "forced": sorted(forced),
        },
    )


# --- The source run and its pool ----------------------------------------------------------------


@dataclass(frozen=True)
class RunDocument:
    document_id: int
    key: str
    content_hash: str
    source_uri: str
    rendition_id: int
    rendition_key: str
    page: str
    first_pass: bool
    first_pass_column: str | None


_RUN_DOCUMENTS = text("""
SELECT DISTINCT ON (rr.document_id) rr.document_id, d.key, d.content_hash, d.source_uri, d.meta,
       rr.rendition_id, r.key AS rkey, c.params->'source_profile' AS profile
FROM kb.run_rendition rr
JOIN kb.document d ON d.id = rr.document_id
JOIN kb.rendition r ON r.id = rr.rendition_id
JOIN kb.rendition_build b ON b.rendition_id = rr.rendition_id AND b.document_id = rr.document_id
JOIN ops.method_config c ON c.id = b.method_config_id
WHERE rr.run_id = :run
ORDER BY rr.document_id, b.method_config_id
""")


def run_documents(conn: Connection, run_id: int) -> list[RunDocument]:
    """The run's documents with their renditions, locator pages and first-pass marks."""
    out = []
    for r in conn.execute(_RUN_DOCUMENTS, {"run": run_id}):
        profile = r.profile or {}
        if "root" not in profile:
            raise GoldenSetError(f"rendition {r.rendition_id} was built without a source profile")
        column = (profile.get("index") or {}).get("first_pass")
        flag = str((r.meta or {}).get(column, "")).strip().lower() if column else ""
        out.append(
            RunDocument(
                int(r.document_id), str(r.key), str(r.content_hash), str(r.source_uri),
                int(r.rendition_id), str(r.rkey), page_of(str(r.source_uri), profile["root"]),
                flag in TRUE, column,
            )
        )  # fmt: skip
    return out


def _covers(conn: Connection, run_id: int, project_id: int) -> bool:
    """Whether the run's scope stage covered every first-pass page of the project."""
    docs = run_documents(conn, run_id)
    columns = {d.first_pass_column for d in docs if d.first_pass_column}
    pages: set[str] = set()
    for column in columns:
        pages |= set(
            conn.execute(
                text(
                    "SELECT DISTINCT source_uri FROM kb.document WHERE project_id = :p AND "
                    "lower(trim(meta->>CAST(:c AS text))) = ANY(:t)"
                ),
                {"p": project_id, "c": column, "t": sorted(TRUE)},
            ).scalars()
        )
    scoped = {
        int(r[0])
        for r in conn.execute(
            text(
                "SELECT unit_id FROM ops.task WHERE run_id = :r AND stage = 'scope' AND "
                "unit_type = 'rendition' AND status = ANY(:done)"
            ),
            {"r": run_id, "done": list(DONE)},
        )
    }
    covered = {d.source_uri for d in docs if d.rendition_id in scoped}
    return bool(pages) and pages <= covered


def source_run(conn: Connection, project_id: int, run_id: int | None = None) -> int:
    """The named run, checked, or the latest finished run that covers the first pass."""
    rows = conn.execute(
        text(
            "SELECT id, kind, status FROM ops.run WHERE project_id = :p AND (CAST(:r AS bigint) "
            "IS NULL OR id = :r) ORDER BY id DESC"
        ),
        {"p": project_id, "r": run_id},
    ).all()
    for row in rows:
        why = None
        if row.kind in (RunKind.INGEST.value, RunKind.GOLDEN.value):
            why = f"a {row.kind} run has no M13 output"
        elif row.status != RunStatus.FINISHED.value:
            why = f"it is {row.status}, not finished"
        elif not _covers(conn, int(row.id), project_id):
            why = "its scope stage did not cover every first-pass page"
        if why is None:
            return int(row.id)
        if run_id is not None:
            raise GoldenSetError(f"run {run_id} cannot be the golden source run: {why}")
    raise GoldenSetError(
        "no finished run covers every first-pass page" if run_id is None else f"no run {run_id}"
    )


def _hint(segment: Any) -> Mapping[str, Any]:
    hint = segment.attrs.get("hint")
    return hint if isinstance(hint, Mapping) else {}


def build_pool(
    conn: Connection, run_id: int, documents: Sequence[RunDocument]
) -> tuple[list[PoolUnit], dict[int, LocatorIndex]]:
    """The claim-bearing annotation units of `documents` on the run's renditions (module doc)."""
    reader = context.DbReader(conn, run_id)
    shares = {m.scope_key: m.value for m in reader.measurements(M02, MATH_SHARE)}
    bearing = {k.value for k in CLAIM_BEARING}
    pool, indexes = [], {}
    for d in documents:
        index = LocatorIndex(reader.content(d.rendition_id), d.page)
        indexes[d.rendition_id] = index
        for unit in index.annotation_units().units:
            hint = _hint(unit.segment)
            kind = str(hint.get("statement_kind") or StatementKind.NARRATIVE.value)
            if kind not in bearing or hint.get("claim_bearing") is False:
                continue
            seg = unit.segment
            share = shares.get(segment_key(d.rendition_key, seg.kind, seg.start, seg.end))
            if share is None:
                raise GoldenSetError(f"run {run_id} has no M02 math share for unit {unit.key}")
            pool.append(PoolUnit(unit.key, kind, float(share), d.document_id, d.rendition_id))
    return pool, indexes


def _slice_locators(conn: Connection, project_id: int, name: str, seen: tuple[str, ...]) -> list:
    if name in seen:
        raise GoldenSetError(f"slice include cycle: {' -> '.join((*seen, name))}")
    selector = conn.execute(
        text("SELECT selector FROM ops.debug_slice WHERE project_id = :p AND name = :n"),
        {"p": project_id, "n": name},
    ).scalar()
    if selector is None:
        raise GoldenSetError(f"no declared slice {name!r}")
    entries = selector if isinstance(selector, list) else selector.get("selections", [])
    out: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, Mapping) and set(entry) == {"include"}:
            out += _slice_locators(conn, project_id, str(entry["include"]), (*seen, name))
        else:
            raise GoldenSetError(f"slice {name!r}: {entry!r} selects no unit by locator")
    return out


def forced_units(
    conn: Connection,
    project_id: int,
    slices: Sequence[str],
    pool: Sequence[PoolUnit],
    documents: Sequence[RunDocument],
    indexes: Mapping[int, LocatorIndex],
) -> list[str]:
    """The pool units the forced slices' locators select (module doc)."""
    by_page = {d.page: d.rendition_id for d in documents}
    in_pool = {(u.rendition_id, u.key) for u in pool}
    out: list[str] = []
    for name in slices:
        for locator in _slice_locators(conn, project_id, name, ()):
            try:
                page = parse_locator(locator).page
                if page not in by_page:
                    raise GoldenSetError(f"forced unit {locator!r}: page not in the split's pool")
                index = indexes[by_page[page]]
                key = str(index.generate(index.resolve(locator)))
            except (LocatorRefused, LocatorSyntaxError) as error:
                raise GoldenSetError(f"forced unit {locator!r}: {error}") from None
            if (by_page[page], key) not in in_pool:
                raise GoldenSetError(f"forced unit {locator!r} ({key}) is not a pool unit")
            if key not in out:
                out.append(key)
    return out


# --- Creating a set -----------------------------------------------------------------------------


class CreatedSet(BaseModel):
    set_id: int
    label: str
    split: DocumentSplit
    source_run_id: int
    golden_run_id: int
    units: int
    forced: int
    tasks: int


def _versions(conn: Connection, run_id: int) -> PackVersions:
    r = conn.execute(
        text(
            "SELECT r.schema_version_id, s.content_hash AS sv, r.model_revision_id, "
            "m.content_hash AS mr, r.guideline_version_id, r.policy_version_id FROM ops.run r "
            "JOIN meta.schema_version s ON s.id = r.schema_version_id JOIN meta.model_revision m "
            "ON m.id = r.model_revision_id WHERE r.id = :r"
        ),
        {"r": run_id},
    ).one()
    if r.guideline_version_id is None:
        raise GoldenSetError(f"run {run_id} records no guideline version to freeze")
    return PackVersions(r.schema_version_id, r.sv, r.model_revision_id, r.mr,
                        r.guideline_version_id, r.policy_version_id)  # fmt: skip


def unit_list_hash(keys: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def create_golden_set(
    conn: Connection,
    *,
    project_id: int,
    split: DocumentSplit,
    label: str,
    config: EvalConfig,
    registry: MethodRegistry,
    size: int | None = None,
    seed: int | None = None,
    from_run: int | None = None,
    commit: str | None = None,
) -> CreatedSet:
    """`ci golden create` (module doc), in the caller's transaction."""
    if split is DocumentSplit.RESERVED:
        raise GoldenSetError("reserved pages are in no golden set")
    taken = conn.execute(
        text("SELECT 1 FROM eval.golden_set WHERE project_id = :p AND label = :l AND split = :s"),
        {"p": project_id, "l": label, "s": split.value},
    ).first()
    if taken is not None:
        raise GoldenSetError(f"golden set {label!r} ({split.value}) exists; labels are not reused")
    size = config.golden.sizes.get(split.value, 40) if size is None else size
    seed = config.split.seed if seed is None else seed
    run_id = source_run(conn, project_id, from_run)
    splits = split_of(conn, project_id)
    documents = [
        d
        for d in run_documents(conn, run_id)
        if d.first_pass and splits.get(d.document_id) is split
    ]
    pool, indexes = build_pool(conn, run_id, documents)
    forced = (
        forced_units(conn, project_id, config.golden.forced_slices, pool, documents, indexes)
        if split is DocumentSplit.DEV
        else []
    )
    drawn = sample(pool, size, seed, forced)
    versions = _versions(conn, run_id)
    set_id = goldens.insert_set(
        conn,
        {
            "project_id": project_id,
            "label": label,
            "split": split.value,
            "schema_version_id": versions.schema_version_id,
            "guideline_version_id": versions.guideline_version_id,
            "sampling": {**drawn.sampling, "source_run": run_id},
        },
    )
    by_key = {u.key: u for u in pool}
    ids = goldens.insert_units(conn, set_id, [(k, by_key[k].rendition_id) for k in drawn.units])
    scope = {
        "golden_set": {"id": set_id, "label": label, "split": split.value},
        "entries": list(drawn.units),
        "hash": unit_list_hash(drawn.units),
    }
    docs = {by_key[k].document_id for k in drawn.units}
    created = runs.create_run(
        conn,
        project_id=project_id,
        kind=RunKind.GOLDEN,
        versions=versions,
        registry=registry,
        documents=[(d.key, d.content_hash) for d in documents if d.document_id in docs],
        explicit={"scope": scope},
        parent_run_id=run_id,
        commit=commit,
    )
    runs.transition(conn, created.id, [RunStatus.CREATED], RunStatus.AWAITING_AGENT)
    view = context.run_view(conn, created.id)
    units = [
        UnitView(UnitRef(TaskUnitType.GOLDEN_UNIT, ids[k], k), view, by_key[k].document_id,
                 by_key[k].rendition_id)
        for k in drawn.units
    ]  # fmt: skip
    made = 0
    for name in ("a", "b"):
        rc = created.configs.get(f"{GOLDEN_METHOD}/{name}")
        if rc is None:
            raise RegistryError([f"{GOLDEN_METHOD}/{name}: no such configuration"])
        method = registry.method(GOLDEN_METHOD)
        made += len(tasks.create_tasks(conn, created.id, Stage.EVALUATE, rc, method, units))
    return CreatedSet(
        set_id=set_id, label=label, split=split, source_run_id=run_id,
        golden_run_id=created.id, units=len(drawn.units), forced=len(forced), tasks=made,
    )  # fmt: skip


# --- Settlement, the unit list and the status ---------------------------------------------------


def golden_run_of(conn: Connection, set_id: int) -> int | None:
    return conn.execute(
        text(
            "SELECT id FROM ops.run WHERE kind = 'golden' AND "
            "(options->'scope'->'golden_set'->>'id')::bigint = :s ORDER BY id DESC LIMIT 1"
        ),
        {"s": set_id},
    ).scalar()


def _statuses(conn: Connection, set_id: int) -> dict[str, int]:
    rows = conn.execute(
        text(
            "SELECT status, count(*) FROM eval.golden_unit WHERE golden_set_id = :s GROUP BY status"
        ),
        {"s": set_id},
    )
    return {str(s): int(n) for s, n in rows}


def settle_golden_run(conn: Connection, run_id: int) -> bool:
    """Finish the golden run when every unit of its set that is not retired is adjudicated."""
    row = conn.execute(
        text(
            "SELECT kind, status, (options->'scope'->'golden_set'->>'id')::bigint AS set_id "
            "FROM ops.run WHERE id = :r"
        ),
        {"r": run_id},
    ).one()
    if row.kind != RunKind.GOLDEN.value or row.set_id is None:
        raise GoldenSetError(f"run {run_id} is not a golden run")
    if row.status == RunStatus.FINISHED.value:
        return True
    counts = _statuses(conn, int(row.set_id))
    live = {s: n for s, n in counts.items() if s != GoldenUnitStatus.RETIRED.value}
    if not live or set(live) != {GoldenUnitStatus.ADJUDICATED.value}:
        return False
    runs.finish_run(conn, run_id)
    return True


@dataclass(frozen=True)
class GoldenUnits:
    keys: tuple[str, ...]
    hash: str


def golden_units(conn: Connection, project_id: int, label: str) -> GoldenUnits:
    """The dev set's unit keys (not retired), sorted, and the sha256 of their newline-joined list;
    every key lies on a dev page."""
    found = conn.execute(
        text(
            "SELECT 1 FROM eval.golden_set WHERE project_id = :p AND label = :l AND split = 'dev'"
        ),
        {"p": project_id, "l": label},
    ).first()
    if found is None:
        raise GoldenSetError(f"no dev golden set {label!r}")
    rows = conn.execute(
        text(
            "SELECT u.unit_key, ds.split FROM eval.golden_set s JOIN eval.golden_unit u ON "
            "u.golden_set_id = s.id JOIN kb.rendition r ON r.id = u.authored_rendition_id LEFT "
            "JOIN eval.document_split ds ON ds.project_id = s.project_id AND ds.document_id = "
            "r.document_id WHERE s.project_id = :p AND s.label = :l AND s.split = 'dev' AND "
            "u.status <> 'retired' ORDER BY u.unit_key"
        ),
        {"p": project_id, "l": label},
    ).all()
    off = [k for k, s in rows if s != DocumentSplit.DEV.value]
    if off:
        raise GoldenSetError(f"golden set {label!r} holds units off dev pages: {off}")
    keys = tuple(str(k) for k, _ in rows)
    return GoldenUnits(keys, unit_list_hash(keys))


class SetStatus(BaseModel):
    set_id: int
    label: str
    split: str
    units: dict[str, int]  # status -> count
    golden_run_id: int | None
    golden_run_status: str | None
    stale: list[str]
    coarse: dict[str, int]  # unit key -> coarse spans in its newest pass C's items


class GoldenStatus(BaseModel):
    project_id: int
    sets: list[SetStatus]


def golden_status(
    conn: Connection, project_id: int, label: str, split: DocumentSplit | None = None
) -> GoldenStatus:
    """`ci golden status`: per set, unit counts, the golden run (settled first), stale units and
    coarse spans per unit. Counts only: no item is shown."""
    sets = conn.execute(
        text(
            "SELECT id, label, split FROM eval.golden_set WHERE project_id = :p AND label = :l "
            "AND (CAST(:s AS text) IS NULL OR split = :s) ORDER BY split"
        ),
        {"p": project_id, "l": label, "s": split.value if split else None},
    ).all()
    if not sets:
        raise GoldenSetError(f"no golden set {label!r}")
    out = []
    for s in sets:
        run_id = golden_run_of(conn, int(s.id))
        status = None
        if run_id is not None:
            settle_golden_run(conn, run_id)
            status = conn.execute(
                text("SELECT status FROM ops.run WHERE id = :r"), {"r": run_id}
            ).scalar()
        units = conn.execute(
            text(
                "SELECT id, unit_key, status FROM eval.golden_unit WHERE golden_set_id = :s "
                "ORDER BY unit_key"
            ),
            {"s": s.id},
        ).all()
        coarse: dict[str, int] = {}
        for u in units:
            pass_c = goldens.latest_pass_c(conn, int(u.id))
            if pass_c is None:
                continue
            payloads = conn.execute(
                text("SELECT payload FROM eval.golden_item WHERE golden_pass_id = :c"),
                {"c": pass_c},
            ).scalars()
            n = sum(goldens.coarse_spans(p) for p in payloads)
            if n:
                coarse[str(u.unit_key)] = n
        out.append(
            SetStatus(
                set_id=int(s.id), label=str(s.label), split=str(s.split),
                units=_statuses(conn, int(s.id)), golden_run_id=run_id,
                golden_run_status=status,
                stale=[str(u.unit_key) for u in units if u.status == GoldenUnitStatus.STALE.value],
                coarse=coarse,
            )
        )  # fmt: skip
    return GoldenStatus(project_id=project_id, sets=out)
