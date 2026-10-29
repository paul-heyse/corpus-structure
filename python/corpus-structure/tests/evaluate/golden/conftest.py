"""E1 test support (evaluation §6, P0-E-1): a statistics project over the vendored spike pages, a
source run that ingests them with production renditions and records M02's math shares and M13's
tasks, and the declared `trace` and `core12` slices.

The methods are deterministic stubs and a test-registered `golden.pass`, never real agents: the
ingest stub returns the rendition `build_rendition` makes of the page's bytes, M02's stub returns
`profile_segments.measurements` of it, and M13's stub returns nothing. Tasks go through
orchestration's task creation, claim and terminal write, so `kb.run_rendition` and
`ops.run_measurement` read them as they read a real run. `importlib` import mode leaves this
module unimportable from tests, so its parts are served by the `gw` fixture.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection, text

from corpus_structure.core.evidence import RenditionContent, document_key, segment_key
from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    SourceProfileRef,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    MethodFamily,
    MethodTier,
    ObservationOutcome,
    RunKind,
    Stage,
    TaskUnitType,
)
from corpus_structure.ingest import profile_segments
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.orchestrate import context, project, queue, runs, tasks
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods

REPO = Path(__file__).resolve().parents[5]
CORPUS = REPO / "fixtures" / "trace" / "corpus"
ROOT = "siegrist_random/random"
STATISTICS = REPO / "domains" / "statistics"
SLICES = {
    "trace": [
        "special/LocationScale.html@p:As usual, our starting point",
        "special/LocationScale.html#dfn1",
        "special/Normal.html@p:Suppose again that \\( X \\) has the normal distribution with "
        "location parameter",
        "special/Normal.html#rel1",
        "special/LogNormal.html#dfn",
    ],
    "core12": [
        {"include": "trace"},
        "special/Normal.html#rel2",
        "special/Normal.html@p:Recall that in general, if \\(X\\) is a random variable with mean",
        "special/Normal.html@p:In some settings, it's convenient to consider a constant",
        "special/Normal.html@u:A metal rod is designed",
        "special/LogNormal.html@u:Suppose that \\(n \\in \\N_+\\) and that",
        "special/Gamma.html#dfn4",
        "special/Gamma.html#rel2",
        "special/Gamma.html#mom1",
    ],
}


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str = "default"


class IngestConfig(_Config):
    source_profile: Annotated[Any, SourceProfileRef()] = "siegrist"


class GoldenPassConfig(_Config):
    """The test `golden.pass`: the declared model and inputs version come from the configuration
    (ADR-0011: Sonnet 5.5, annotator inputs v1)."""

    model: str = "claude-sonnet-5-5"
    inputs: str = "v1"


@dataclass
class Stub:
    name: str
    unit_type: TaskUnitType
    family: MethodFamily
    tier: MethodTier = MethodTier.DETERMINISTIC
    confidence_source: Any = None
    Config: type[BaseModel] = _Config
    version: str = "1"
    resources: Resources = field(default_factory=Resources)
    result: Callable[[UnitView], UnitResult] | None = None

    def select(self, run: Any, cfg: Any) -> Iterable[UnitRef]:
        return ()

    def input_digest(self, unit: UnitView, cfg: Any) -> Digest:
        data = f"{unit.ref.unit_key}|{cfg.model_dump_json()}".encode()
        packet = f"packet:{hashlib.sha256(data).hexdigest()[:16]}"
        return Digest(data, packet if self.tier is MethodTier.AGENT else None)

    def run(self, units: Sequence[UnitView], cfg: Any, ctx: MethodContext) -> Sequence[UnitResult]:
        raise AssertionError("tests write results through the queue")


def golden_pass() -> Stub:
    return Stub(
        "golden.pass",
        TaskUnitType.GOLDEN_UNIT,
        MethodFamily.EVAL,
        MethodTier.AGENT,
        Config=GoldenPassConfig,
    )


METHODS = (
    Stub("ingest.html", TaskUnitType.DOCUMENT, MethodFamily.INGEST, Config=IngestConfig),
    Stub("profile.segments", TaskUnitType.RENDITION, MethodFamily.PROFILE),
    Stub("resolve.symbol_scope", TaskUnitType.RENDITION, MethodFamily.RESOLVE),
)


def write_pack(root: Path, methods: Sequence[Stub]) -> Path:
    """A copy of the statistics pack (its `eval/split.yaml` included) whose `methods.yaml` keeps
    its sections (`math`, `aliases`, ...) and configures the stub methods, `golden.pass` with `a`,
    `b` and `c`."""
    pack = root / "statistics"
    shutil.copytree(STATISTICS, pack)
    data = yaml.safe_load((STATISTICS / "methods.yaml").read_text(encoding="utf-8"))
    data["configs"] = {"ingest.html": {"default": {}}}
    if any(m.name == "golden.pass" for m in methods):
        data["configs"]["golden.pass"] = {p: {"variant": p} for p in ("a", "b", "c")}
    (pack / "methods.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return pack


def raw_page(page: str) -> bytes:
    return (CORPUS / ROOT / page).read_bytes()


_PROFILE = None


def rendition_of(raw: bytes, page: str) -> RenditionContent:
    global _PROFILE
    if _PROFILE is None:
        _PROFILE = compile_profile(load_profile("siegrist"))
    return build_rendition(raw, _PROFILE, SentenceConfig(), source_uri=f"{ROOT}/{page}").content


def setup_world(conn: Connection, tmp_path: Path, golden: bool = True) -> SimpleNamespace:
    """The project, its pack's versions and registry, its documents and declared slices."""
    methods = [*METHODS, golden_pass()] if golden else list(METHODS)
    pack = write_pack(tmp_path / "domains", methods)
    methods_file = load_methods(pack / "methods.yaml")
    registry = MethodRegistry(methods, methods_file)
    report = project.init_project(
        conn, domain="statistics", corpus=CORPUS, registry=registry, domains=pack.parent
    )
    versions = project.ensure_pack_versions(conn, report.project_id, pack, "human:test")
    for name, selector in SLICES.items():
        conn.execute(
            text(
                "INSERT INTO ops.debug_slice (project_id, name, selector) VALUES (:p, :n, "
                "CAST(:s AS jsonb))"
            ),
            {"p": report.project_id, "n": name, "s": _json(selector)},
        )
    docs = conn.execute(
        text(
            "SELECT id, key, content_hash, source_uri FROM kb.document WHERE project_id = :p "
            "ORDER BY source_uri"
        ),
        {"p": report.project_id},
    ).all()
    return SimpleNamespace(
        pack=pack,
        methods=methods_file,
        registry=registry,
        stubs={m.name: m for m in methods},
        project_id=report.project_id,
        versions=versions,
        documents={str(d.source_uri).removeprefix(ROOT + "/"): d for d in docs},
    )


def _json(value: Any) -> str:
    import json

    return json.dumps(value)


def add_document(conn: Connection, w: SimpleNamespace, page: str, raw: bytes) -> int:
    """New bytes at a known page: a new document (D1 §3.1), first-pass like its page."""
    uri = f"{ROOT}/{page}"
    content_hash = hashlib.sha256(raw).hexdigest()
    meta = conn.execute(
        text("SELECT meta FROM kb.document WHERE id = :d"), {"d": w.documents[page].id}
    ).scalar_one()
    return int(
        conn.execute(
            text(
                "INSERT INTO kb.document (project_id, key, source_uri, content_hash, "
                "original_path, mime, meta) VALUES (:p, :k, :u, :h, 'edited', 'text/html', "
                "CAST(:m AS jsonb)) RETURNING id"
            ),
            {"p": w.project_id, "k": document_key("statistics", uri, content_hash), "u": uri,
             "h": content_hash, "m": _json(meta)},
        ).scalar_one()
    )  # fmt: skip


def _work(
    conn: Connection,
    run_id: int,
    stage: Stage,
    config: Any,
    stub: Stub,
    units: Sequence[UnitView],
    result: Callable[[UnitView], UnitResult],
) -> None:
    made = tasks.create_tasks(conn, run_id, stage, config, stub, units)
    by_id = {t.id: u for t, u in zip(made, units, strict=True)}
    for c in queue.claim(conn, run_id, stage, config.method_config_id, "test", n=len(units)):
        queue.write_result(conn, c.id, c.attempt, result(by_id[c.id]))


def ingest_run(
    conn: Connection,
    w: SimpleNamespace,
    contents: Mapping[int, RenditionContent],
    *,
    scope: bool = True,
    finish: bool = True,
) -> int:
    """A `full` run over `contents` (document id -> rendition): ingest, M02 and, with `scope`,
    M13 tasks; finished with `finish`."""
    created = runs.create_run(
        conn,
        project_id=w.project_id,
        kind=RunKind.FULL,
        versions=w.versions,
        registry=w.registry,
        documents=[(d.key, d.content_hash) for d in w.documents.values()],
        commit="test",
    )
    view = context.run_view(conn, created.id)
    keys = dict(
        conn.execute(text("SELECT id, key FROM kb.document WHERE id = ANY(:i)"),
                     {"i": list(contents)}).all()
    )  # fmt: skip
    units = [
        UnitView(UnitRef(TaskUnitType.DOCUMENT, doc, keys[doc]), view, doc) for doc in contents
    ]

    def ingest(u: UnitView) -> UnitResult:
        return UnitResult(
            ref=u.ref,
            outcome=ObservationOutcome.EMPTY,
            rendition=contents[int(u.ref.unit_id or 0)],
            parse_detail={"data_loss_warnings": 0},
        )

    _work(conn, created.id, Stage.INGEST, created.configs["ingest.html/default"],
          w.stubs["ingest.html"], units, ingest)  # fmt: skip
    rendered = view.reader.renditions()
    ren_units = [
        UnitView(UnitRef(TaskUnitType.RENDITION, r.rendition_id, r.rendition_key), view,
                 r.document_id, r.rendition_id)
        for r in rendered
        if r.document_id in contents
    ]  # fmt: skip

    def m02(u: UnitView) -> UnitResult:
        content = contents[int(u.document_id or 0)]
        key = str(u.ref.unit_key)
        drafts = profile_segments.measurements(
            content, lambda s: segment_key(key, s.kind, s.start, s.end)
        )
        return UnitResult(ref=u.ref, outcome=ObservationOutcome.EMPTY, measurements=tuple(drafts))

    def empty(u: UnitView) -> UnitResult:
        return UnitResult(ref=u.ref, outcome=ObservationOutcome.EMPTY)

    _work(conn, created.id, Stage.INGEST, created.configs["profile.segments/default"],
          w.stubs["profile.segments"], ren_units, m02)  # fmt: skip
    if scope:
        _work(conn, created.id, Stage.SCOPE, created.configs["resolve.symbol_scope/default"],
              w.stubs["resolve.symbol_scope"], ren_units, empty)  # fmt: skip
    if finish:
        runs.finish_run(conn, created.id)
    return created.id


def spike_contents(w: SimpleNamespace) -> dict[int, RenditionContent]:
    return {d.id: rendition_of(raw_page(page), page) for page, d in w.documents.items()}


@pytest.fixture
def gw() -> SimpleNamespace:
    return SimpleNamespace(
        setup_world=setup_world,
        ingest_run=ingest_run,
        spike_contents=spike_contents,
        add_document=add_document,
        rendition_of=rendition_of,
        raw_page=raw_page,
        golden_pass=golden_pass,
        Stub=Stub,
        ROOT=ROOT,
        REPO=REPO,
        SLICES=SLICES,
    )
