"""The pass (consolidation §3.1, §3.2; D5 §1; D6 §2): `run_pass(conn, run, pass_, m19_task)`.

Inside the caller's transaction (orchestration fences the stage's task first and commits the
result with the task's terminal status), the pass:
1. reads the run row, its schema version's compiled schema (`schema.registry.compiled_for`), the
   pass task's `consolidate.claims` configuration (engine, `use_markup_hints`, the pack's `aliases`
   and `math` sections; the method's defaults when the run has no such task), and the run's
   renditions (`kb.run_rendition`) with their content rebuilt from the stored segments, their page
   (the source URI under the ingest configuration's profile root) and effective macro table;
2. loads the pool as of the run's cut (`pool.load`, on its own ADBC connection: it reads committed
   data, so the seal must have committed before the final pass) with the kinds phase 0 reads,
   `claim_proposal` and `author_markup`;
3. assembles (`consolidate.assemble`) on the configured engine; at finalize reads the values,
   runs M19 and sets statuses (`consolidate.finalize`);
4. asserts the invariants and rewrites the run's knowledge (`consolidate.write`), with the edge and
   identity rows and M19's failing outcomes at the final pass only.

Consolidation sits below orchestration: nothing here imports `orchestrate`. The returned
`PassReport` carries the fields the runner reads (`rule_counts`, `consumed`).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Annotated, Any, Literal

from psycopg.conninfo import make_conninfo
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, text

from corpus_structure.consolidate import finalize as F
from corpus_structure.consolidate.assemble import Inputs, Page, assemble
from corpus_structure.consolidate.report import PassReport, Tally
from corpus_structure.consolidate.write import check_invariants, statuses_of, write, write_findings
from corpus_structure.core import tex
from corpus_structure.core.db import repo
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.keys import LabelRules
from corpus_structure.core.locators import page_of
from corpus_structure.core.method import (
    Digest,
    MethodContext,
    PackSection,
    Resources,
    RunView,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    ObservationKind,
    TaskUnitType,
)
from corpus_structure.pool import load as pool_load
from corpus_structure.pool.harness import engine as make_engine
from corpus_structure.schema import registry

PASSES = ("assemble", "finalize")
KINDS = (ObservationKind.CLAIM_PROPOSAL.value, ObservationKind.AUTHOR_MARKUP.value)
METHOD = "consolidate.claims"
VERSION = "1"


class ConsolidateConfig(BaseModel):
    """`consolidate.claims`'s configuration: the set-step engine, markup hints, and the pack's
    `aliases` (label normalization, D5 §3.3) and `math` (the fallback macro map) sections."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    engine: Literal["duckdb", "python"] = "duckdb"
    use_markup_hints: bool = True
    aliases: Annotated[dict[str, Any], PackSection("aliases")] = Field(default_factory=dict)
    math: Annotated[dict[str, Any], PackSection("math")] = Field(default_factory=dict)

    def labels(self, to_prefixed: Mapping[str, str]) -> LabelRules:
        """The label rules, head words keyed by prefixed class (the pack writes local names)."""
        heads = {
            to_prefixed.get(k, k): tuple(v)
            for k, v in (self.aliases.get("head_words") or {}).items()
        }
        return LabelRules.model_validate({**self.aliases, "head_words": heads})

    def macros(self) -> dict[str, MacroDef]:
        return {
            k: MacroDef(body=v) if isinstance(v, str) else MacroDef.model_validate(v)
            for k, v in (self.math.get("macros") or {}).items()
        }


class ConsolidateMethod:
    """`consolidate.claims` (D4 M17/M18), a run-unit method the stage runner calls as `run_pass`;
    no worker runs it."""

    name = METHOD
    version = VERSION
    family = MethodFamily.CONSOLIDATE
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config = ConsolidateConfig
    resources = Resources()

    def select(self, run: RunView, cfg: ConsolidateConfig) -> Iterable[UnitRef]:
        return [UnitRef(TaskUnitType.RUN)]

    def input_digest(self, unit: UnitView, cfg: ConsolidateConfig) -> Digest:
        return Digest(f"{self.name}|{self.version}".encode())

    def run(
        self, units: Sequence[UnitView], cfg: ConsolidateConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError("consolidate.claims runs as the stage runner's pass (run_pass)")


# --- Reading the run ---------------------------------------------------------------------------


def config_of(conn: Connection, run_id: int, pass_: str) -> ConsolidateConfig:
    params = conn.execute(
        text(
            "SELECT c.params FROM ops.task t JOIN ops.method_config c ON c.id = t.method_config_id "
            "JOIN ops.method m ON m.id = c.method_id WHERE t.run_id = :r AND t.stage = :s AND "
            "t.unit_type = 'run' AND m.name = :m ORDER BY t.id DESC LIMIT 1"
        ),
        {"r": run_id, "s": pass_, "m": METHOD},
    ).scalar()
    return ConsolidateConfig.model_validate(params or {})


def pages_of(conn: Connection, run_id: int, pack_macros: dict[str, MacroDef]) -> dict[int, Page]:
    rows = conn.execute(
        text(
            "SELECT DISTINCT rr.document_id, d.key, d.source_uri, d.title, rr.rendition_id, "
            "c.params -> 'source_profile' ->> 'root' AS root FROM kb.run_rendition rr "
            "JOIN kb.document d ON d.id = rr.document_id JOIN kb.rendition_build b ON "
            "b.rendition_id = rr.rendition_id AND b.document_id = rr.document_id "
            "JOIN ops.method_config c ON c.id = b.method_config_id WHERE rr.run_id = :r"
        ),
        {"r": run_id},
    ).all()
    out = {}
    for document_id, document_key, uri, title, rendition_id, root in rows:
        content = repo.read_rendition(conn, rendition_id)
        out[int(rendition_id)] = Page(
            int(rendition_id),
            int(document_id),
            str(document_key),
            page_of(str(uri), str(root)) if root else str(uri),
            content,
            tex.effective_macros(content.macros, pack_macros),
            repo.segment_ids(conn, rendition_id),
            title,
        )
    return out


def documents_of(conn: Connection, run_id: int) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT DISTINCT r.id, r.document_id FROM kb.run_observation o JOIN kb.rendition r "
            "ON r.id = o.rendition_id WHERE o.run_id = :run"
        ),
        {"run": run_id},
    )
    return {int(a): int(b) for a, b in rows}


def adbc_url(conn: Connection) -> str:
    """The libpq connection string of the caller's connection, for the pool's ADBC reader."""
    info = conn.connection.dbapi_connection.info  # type: ignore[union-attr]
    return make_conninfo(info.dsn, password=info.password) if info.password else info.dsn


@contextmanager
def _engine(name: Any) -> Iterator[Any]:
    e = make_engine(name)
    try:
        yield e
    finally:
        close = getattr(e, "close", None)
        if close is not None:
            close()


# --- The pass ----------------------------------------------------------------------------------


def run_pass(conn: Connection, run_id: int, pass_: str, m19_task_id: int | None) -> PassReport:
    """One consolidation pass over the run's pool (module doc)."""
    if pass_ not in PASSES:
        raise ValueError(f"pass {pass_!r} is not one of {PASSES}")
    run = conn.execute(
        text("SELECT schema_version_id, cut_at FROM ops.run WHERE id = :r"), {"r": run_id}
    ).one()
    if pass_ == "finalize" and (run.cut_at is None or m19_task_id is None):
        raise ValueError(f"run {run_id}: the final pass needs the seal's cut and M19 task")
    config = config_of(conn, run_id, pass_)
    compiled = registry.compiled_for(conn, run.schema_version_id)
    inputs = Inputs(
        pages_of(conn, run_id, config.macros()),
        documents_of(conn, run_id),
        compiled,
        config.labels(compiled.names.to_prefixed),
        config.use_markup_hints,
    )
    with pool_load.connect(adbc_url(conn)) as adbc:
        pool = pool_load.load(adbc, run_id, run.cut_at, KINDS)
    return consolidate(
        conn, run_id, run.schema_version_id, pass_, m19_task_id, pool, inputs, config.engine
    )


def consolidate(
    conn: Connection,
    run_id: int,
    schema_version_id: int,
    pass_: str,
    m19_task_id: int | None,
    pool: Any,
    inputs: Inputs,
    engine_name: Any = "duckdb",
) -> PassReport:
    """Assemble, finalize and write a loaded pool (the pass after its reads)."""
    tally = Tally()
    with _engine(engine_name) as engine:
        knowledge = assemble(pool, inputs, engine, tally)
    findings: tuple[F.Finding, ...] = ()
    rule_counts: dict[str, int] = {}
    if pass_ == "finalize":
        readings = F.read_values(knowledge, inputs)
        with _engine(engine_name) as engine:
            outcome = F.run_m19(knowledge, inputs, readings, engine)
        findings, rule_counts = outcome.findings, dict(outcome.evaluated)
    F.set_statuses(knowledge, pass_, findings)
    check_invariants(knowledge, inputs)
    write(
        conn,
        run_id,
        schema_version_id,
        knowledge,
        F.edges(knowledge) if pass_ == "finalize" else None,
    )
    if pass_ == "finalize" and m19_task_id is not None:
        write_findings(conn, m19_task_id, findings)
    index = {r["id"]: r["task_id"] for r in pool["observations"].to_pylist()}
    consumed = tuple(sorted({index[o] for o in knowledge.consumed}))
    return PassReport.of(
        pass_, tally, statuses_of(knowledge), tuple(sorted(knowledge.groups)), rule_counts, consumed
    )
