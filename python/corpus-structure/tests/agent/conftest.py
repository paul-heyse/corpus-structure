"""Agent-interface test support (agent interface §6, P0-A-1).

**The world** (on a committing clone): a project over the vendored trace pages with the
statistics pack; phase 0's real `ingest.html` and M24, and the test-registered `extract.math` and
`resolve.symbol_scope` (M09's mentions and M13's scopes from I2a's in-memory functions, written as
their stored payloads, as I2b will); a
run with renditions, those observations and M24 tasks for the five trace units of `fixtures/s0`.
The stage runner creates every task, so M24's tasks carry their packet hashes exactly as in
production.

**The tools** are called through an in-process `Client(server)` on a `Session` the test holds, so
the lease, the served record and the caches persist across calls (`Tools.call`).

`importlib` import mode leaves this module unimportable from the tests; its parts are served by the
`agent` fixture.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import pytest
import yaml
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection, Engine, text

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef, RenditionContent, segment_key
from corpus_structure.core.method import (
    Digest,
    MethodContext,
    MethodSettings,
    ObservationDraft,
    Resources,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.payloads import MentionPayload, ScopePayload
from corpus_structure.core.vocab import (
    MethodFamily,
    MethodTier,
    ObservationKind,
    ObservationOutcome,
    RunKind,
    RunStatus,
    Stage,
    TaskUnitType,
)

REPO = Path(__file__).resolve().parents[4]
TRACE_CORPUS = REPO / "fixtures" / "trace" / "corpus"
S0 = REPO / "fixtures" / "s0"
STATISTICS = REPO / "domains" / "statistics"
ROOT = "siegrist_random/random"
TRACE_UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")
STATS_METHODS = yaml.safe_load((STATISTICS / "methods.yaml").read_text(encoding="utf-8"))
PACK_MACROS = {k: MacroDef(body=v) for k, v in STATS_METHODS["math"]["macros"].items()}


def s0(name: str) -> dict[str, Any]:
    return json.loads((S0 / f"{name}.json").read_text(encoding="utf-8"))


# --- In-memory analysis (the grammar runs here, in the test process's main thread) ---------------


@dataclass(frozen=True)
class Analysis:
    content: RenditionContent
    macros: dict[str, MacroDef]
    mentions: list[Any]
    scopes: list[Any]


_ANALYSES: dict[str, Analysis] = {}


def analyse(content: RenditionContent) -> Analysis:
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.math.scope import Binders, resolve_scopes
    from corpus_structure.methods.math.spans import extract, formula_values, read_spans

    key = content.canonical_text
    if key not in _ANALYSES:
        macros = tex.effective_macros(content.macros, PACK_MACROS)
        readings = read_spans(content, macros, tuple(STATS_METHODS["math"]["constants"]))
        extraction = extract(readings)
        scopes = resolve_scopes(
            content, formula_values(readings), extraction.mentions, extraction.relations,
            macros, Binders(**STATS_METHODS["binders"]), SentenceConfig(),
        )  # fmt: skip
        _ANALYSES[key] = Analysis(content, dict(macros), list(extraction.mentions), scopes)
    return _ANALYSES[key]


@cache
def page_content(page: str) -> RenditionContent:
    from corpus_structure.ingest.html import build_rendition
    from corpus_structure.ingest.profile import compile_profile, load_profile
    from corpus_structure.ingest.sentences import SentenceConfig

    source = f"{ROOT}/{page}"
    corpus = (
        TRACE_CORPUS if (TRACE_CORPUS / source).exists() else REPO / "docs/statistics_corpus/corpus"
    )
    raw = (corpus / source).read_bytes()
    profile = compile_profile(load_profile("siegrist"))
    return build_rendition(raw, profile, SentenceConfig(), source_uri=source).content


def mention_payloads(content: RenditionContent, rendition_key: str) -> list[MentionPayload]:
    """M09's stored form of the in-memory mentions (ingest and math §3.8)."""
    out = []
    for m in sorted(analyse(content).mentions, key=lambda m: (m.segment.start, m.start)):
        out.append(
            MentionPayload.model_validate(
                {
                    "start": m.start, "end": m.end, "label": "symbol",
                    "text": content.canonical_text[m.start : m.end],
                    "math_ref": segment_key(rendition_key, m.segment.kind, m.segment.start,
                                            m.segment.end),
                    "math": {"name": m.name, "base": m.base, "sub": m.sub, "sup": m.sup,
                             "constant": m.constant, "in_subscript_of": m.in_subscript_of},
                }
            )
        )  # fmt: skip
    return out


def scope_payloads(
    content: RenditionContent, rendition_key: str, m09_task: int | None, ordinals: dict[Any, int]
) -> list[ScopePayload]:
    """M13's stored form of the in-memory scopes; `ordinals` maps a mention's (start, end) to its
    M09 ordinal. Unresolved scopes are not written."""

    def ref(start: int, end: int) -> dict[str, Any]:
        out: dict[str, Any] = {"ordinal": ordinals[(start, end)]}
        if m09_task is not None:
            out["task"] = m09_task
        return out

    out = []
    for s in analyse(content).scopes:
        if s.site is None:
            continue
        site = s.site
        body: dict[str, Any] = {
            "start": s.mention.start, "end": s.mention.end,
            "mention_ref": ref(s.mention.start, s.mention.end),
            "binding_site": {"start": site.mention.start, "end": site.mention.end,
                             "mention_ref": ref(site.mention.start, site.mention.end)},
            "scope_segment": segment_key(rendition_key, site.scope.kind, site.scope.start,
                                         site.scope.end),
            "extent": site.extent.value,
        }  # fmt: skip
        if site.reopens is not None:
            r = site.reopens.mention
            body["reopens"] = {"start": r.start, "end": r.end, "mention_ref": ref(r.start, r.end)}
        out.append(ScopePayload.model_validate(body))
    return out


# --- Test-registered methods -----------------------------------------------------------------


class Empty(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str = "default"


def _rendition_units(run: Any) -> list[UnitRef]:
    return [UnitRef(TaskUnitType.RENDITION, r.rendition_id, r.rendition_key)
            for r in run.reader.renditions()]  # fmt: skip


def _rendition_key(view: UnitView) -> str:
    return next(r.rendition_key for r in view.run.reader.renditions()
                if r.rendition_id == view.rendition_id)  # fmt: skip


@dataclass
class MathStub:
    """`extract.math` or `resolve.symbol_scope` from the in-memory analysis (module doc)."""

    name: str
    family: MethodFamily
    version: str = "test"
    unit_type: TaskUnitType = TaskUnitType.RENDITION
    tier: MethodTier = MethodTier.DETERMINISTIC
    confidence_source: Any = None
    Config: type[BaseModel] = Empty
    resources: Resources = field(default_factory=Resources)

    def select(self, run: Any, cfg: Any) -> Iterable[UnitRef]:
        return _rendition_units(run)

    def input_digest(self, unit: UnitView, cfg: Any) -> Digest:
        return Digest(f"{unit.ref.unit_key}|{self.name}|{self.version}".encode())

    def run(self, units: Sequence[UnitView], cfg: Any, ctx: MethodContext) -> list[UnitResult]:
        return [self.one(u, ctx) for u in units]

    def one(self, unit: UnitView, ctx: MethodContext) -> UnitResult:
        assert unit.rendition_id is not None
        content = ctx.reader.content(unit.rendition_id)
        key = _rendition_key(unit)
        if self.name == "extract.math":
            payloads: list[BaseModel] = list(mention_payloads(content, key))
            kind, cls = ObservationKind.MENTION, MentionPayload
        else:
            m09 = ctx.reader.observations(
                unit.rendition_id, "extract.math", ObservationKind.MENTION
            )
            ordinals = {(o.payload["start"], o.payload["end"]): i for i, o in enumerate(m09)}
            task = m09[0].task_id if m09 else None
            payloads = list(scope_payloads(content, key, task, ordinals))
            kind, cls = ObservationKind.SCOPE, ScopePayload
        drafts = tuple(
            ObservationDraft(
                kind=kind,
                payload=p,
                payload_class=cls,
                payload_version="1",
                rendition_id=unit.rendition_id,
            )
            for p in payloads  # fmt: skip
        )
        outcome = ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY
        return UnitResult(ref=unit.ref, outcome=outcome, observations=drafts)


# --- The world ---------------------------------------------------------------------------------


def write_pack(root: Path, guideline: str | None = None) -> Path:
    """A copy of the statistics pack, its guideline optionally replaced."""
    pack = root / "statistics"
    shutil.copytree(STATISTICS, pack)
    if guideline is not None:
        (pack / "guideline.md").write_text(guideline, encoding="utf-8")
    return pack


def methods() -> list[Any]:
    """Phase 0's registered methods (the real ingest, M24, consolidation, M19 and the evaluate
    stand-in), with a fresh M24 (its caches are per instance), and the M09/M13 stand-ins."""
    from corpus_structure.methods.llm.agent_opus import AgentOpus
    from corpus_structure.orchestrate.phase0 import METHODS

    return [
        *(AgentOpus() if m.name == "agent.opus" else m for m in METHODS),
        MathStub("extract.math", MethodFamily.EXTRACT),
        MathStub("resolve.symbol_scope", MethodFamily.RESOLVE),
    ]


def registry_for(pack: Path, registered: Sequence[Any] | None = None) -> Any:
    from corpus_structure.orchestrate.registry import MethodRegistry, load_methods

    return MethodRegistry(list(registered or methods()), load_methods(pack / "methods.yaml"))


def trace_unit_keys() -> list[str]:
    return [s0(name)["unit_key"] for name in TRACE_UNITS]


def build_world(
    engine: Engine, tmp: Path, guideline: str | None = None, units: Sequence[str] | None = None
) -> SimpleNamespace:
    from corpus_structure.orchestrate import project

    pack = write_pack(tmp / "domains", guideline)
    registry = registry_for(pack)
    with engine.begin() as conn:
        report = project.init_project(conn, domain="statistics", corpus=TRACE_CORPUS,
                                      registry=registry, domains=pack.parent)  # fmt: skip
        documents = [tuple(r) for r in conn.execute(text(
            "SELECT key, content_hash FROM kb.document WHERE project_id = :p ORDER BY key"),
            {"p": report.project_id})]  # fmt: skip
    w = SimpleNamespace(engine=engine, pack=pack, registry=registry, project_id=report.project_id,
                        documents=documents, units=list(units or trace_unit_keys()), tmp=tmp)  # fmt: skip
    w.url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return w


def start_run(w: SimpleNamespace, **explicit: Any) -> int:
    """A run through ingest, M09, M13 and M24's task creation (not sealed)."""
    from corpus_structure.orchestrate import phase0, project, runs
    from corpus_structure.orchestrate.runner import Graph, Runner, Step

    with w.engine.begin() as conn:
        versions = project.ensure_pack_versions(conn, w.project_id, w.pack, "human:test")
        run = runs.create_run(conn, project_id=w.project_id, kind=RunKind.FULL, versions=versions,
                              registry=w.registry, documents=w.documents, commit="t",
                              explicit=explicit or None).id  # fmt: skip
        runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)

    def m24_units(conn: Connection, view: Any, cfg: Any) -> list[UnitRef]:
        method = w.registry.method("agent.opus")
        return [u for u in method.select(view, cfg) if u.unit_key in w.units]

    runner = Runner(w.engine, w.registry, Graph(()), phase0.stub_pass, None,
                    MethodSettings(data_dir=w.tmp, model_cache=w.tmp))  # fmt: skip
    for stage, step in (
        (Stage.INGEST, Step("ingest.html/default")),
        (Stage.NORMALIZE, Step("extract.math/default", upstream=("ingest.html",))),
        (Stage.SCOPE, Step("resolve.symbol_scope/default", upstream=("extract.math",))),
        (Stage.PROPOSE, Step("agent.opus/extract", upstream=("ingest.html",), units=m24_units)),
    ):
        runner.step(run, stage, step)
    return run


@pytest.fixture(scope="module")
def world_engine(db_server: Any) -> Iterator[Engine]:
    with db_server.clone(f"ci_test_{os.getpid()}_agent_{id(object())}") as engine:
        yield engine


@pytest.fixture(scope="module")
def world(world_engine: Engine, tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    """A project with one run whose M24 tasks are the five trace units, per test module."""
    w = build_world(world_engine, tmp_path_factory.mktemp("agent"))
    w.run = start_run(w)
    return w


# --- The tools ---------------------------------------------------------------------------------


@dataclass
class Tools:
    """Calls the main profile's tools through an in-process client on one session."""

    server: Any
    session: Any

    def raw(self, name: str, **args: Any) -> Any:
        from fastmcp import Client

        async def main() -> Any:
            async with Client(self.server) as client:
                return await client.call_tool(name, args, raise_on_error=False)

        return anyio.run(main)

    def call(self, name: str, **args: Any) -> Any:
        result = self.raw(name, **args)
        if result.is_error:
            raise AssertionError(f"{name}: {result.content[0].text}")
        return result.structured_content if result.structured_content is not None else result.data

    def error(self, name: str, **args: Any) -> str:
        result = self.raw(name, **args)
        assert result.is_error, f"{name} succeeded: {result.structured_content}"
        return str(result.content[0].text)


def tools(engine: Engine, domains: Path | None = None) -> Tools:
    from corpus_structure.intervene.server import build_server
    from corpus_structure.intervene.service import Session

    session = Session(engine, domains=domains)
    return Tools(build_server(session), session)


@pytest.fixture
def agent() -> SimpleNamespace:
    return SimpleNamespace(
        s0=s0, TRACE_UNITS=TRACE_UNITS, page_content=page_content, analyse=analyse,
        mention_payloads=mention_payloads, scope_payloads=scope_payloads, build_world=build_world,
        start_run=start_run, tools=tools, write_pack=write_pack, registry_for=registry_for,
        methods=methods, PACK_MACROS=PACK_MACROS, STATISTICS=STATISTICS, REPO=REPO,
    )  # fmt: skip
