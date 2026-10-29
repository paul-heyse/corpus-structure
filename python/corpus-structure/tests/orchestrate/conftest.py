"""Orchestration test support (orchestration §6): a test pack over the vendored trace pages and a
stub registry of deterministic methods for the phase 0 steps.

The stubs' digests are pure functions of their unit and configuration (and, where a step has
upstream methods, of the upstream observations read through the run's reader), so reuse and twins
occur exactly when the plan says they must. `importlib` import mode leaves this module unimportable
from tests, so its parts are served by the `orch` fixture.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any

import pytest
import yaml
from pydantic import BaseModel, ConfigDict

from corpus_structure.core.evidence import RenditionContent, Segment
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
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    ObservationOutcome,
    TaskUnitType,
)
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods

REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "fixtures" / "trace" / "corpus"
MINIMAL = REPO / "fixtures" / "packs" / "minimal"


class Empty(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    variant: str = "default"


class IngestConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_profile: Annotated[Any, SourceProfileRef()] = "siegrist"


@dataclass
class Stub:
    """A deterministic method; `digest` and `result` are its behaviour."""

    name: str
    unit_type: TaskUnitType
    family: MethodFamily = MethodFamily.NORMALIZE
    tier: MethodTier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config: type[BaseModel] = Empty
    version: str = "1"
    resources: Resources = field(default_factory=Resources)
    units: Callable[[Any, Any], Iterable[UnitRef]] = lambda run, cfg: ()
    digest: Callable[[UnitView, Any], bytes] = lambda unit, cfg: (unit.ref.unit_key or "").encode()
    result: Callable[[UnitView, Any, MethodContext], UnitResult] | None = None
    calls: list[Any] = field(default_factory=list)

    def select(self, run: Any, cfg: Any) -> Iterable[UnitRef]:
        return self.units(run, cfg)

    def input_digest(self, unit: UnitView, cfg: Any) -> Digest:
        data = self.digest(unit, cfg)
        packet = None if self.tier is not MethodTier.AGENT else f"packet:{data.hex()[:16]}"
        return Digest(data, packet)

    def run(self, units: Sequence[UnitView], cfg: Any, ctx: MethodContext) -> Sequence[UnitResult]:
        self.calls.append([u.ref for u in units])
        if self.result is not None:
            return [self.result(u, cfg, ctx) for u in units]
        return [UnitResult(ref=u.ref, outcome=ObservationOutcome.EMPTY) for u in units]


def page_content(page: str) -> RenditionContent:
    """A small rendition per page: one unit holding one paragraph of two sentences."""
    text = f"{page} defines X. Then Y holds."
    first = len(f"{page} defines X.")
    sentences = (
        Segment(kind="sentence", start=0, end=first),
        Segment(kind="sentence", start=first + 1, end=len(text)),
    )
    paragraph = Segment(kind="paragraph", start=0, end=len(text), children=sentences)
    unit = Segment(kind="unit", start=0, end=len(text), attrs={"id": "u1"}, children=(paragraph,))
    return RenditionContent(
        canonical_text=text,
        document=Segment(kind="document", start=0, end=len(text), children=(unit,)),
    )


def write_pack(
    root: Path, methods: dict[str, Any] | None = None, guideline: str | None = None
) -> Path:
    """A test pack under `root/minimal`: the minimal pack, a `methods.yaml` and a guideline."""
    pack = root / "minimal"
    shutil.copytree(MINIMAL, pack)
    data = methods or {"version": "0.1.0", "configs": {"ingest.html": {"default": {}}}}
    (pack / "methods.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    (pack / "guideline.md").write_text(
        guideline or "# Annotation guideline v1 (test)\n\nRules.\n", encoding="utf-8"
    )
    return pack


def ingest_stub(**kw: Any) -> Stub:
    return Stub(
        "ingest.html", TaskUnitType.DOCUMENT, MethodFamily.INGEST, Config=IngestConfig, **kw
    )


def setup_project(
    db: Any,
    tmp_path: Path,
    methods: Sequence[Any] | None = None,
    pack_methods: dict[str, Any] | None = None,
    sources: Path | None = None,
) -> SimpleNamespace:
    """A project over the trace pages: its pack, registry, versions and documents."""
    from sqlalchemy import text

    from corpus_structure.orchestrate import project

    pack = write_pack(tmp_path / "domains", pack_methods)
    methods_file = load_methods(pack / "methods.yaml")
    registry = MethodRegistry(methods or [ingest_stub()], methods_file, sources)
    report = project.init_project(
        db, domain="minimal", corpus=CORPUS, registry=registry, domains=pack.parent
    )
    versions = project.ensure_pack_versions(db, report.project_id, pack, "human:test")
    rows = db.execute(
        text("SELECT key, content_hash FROM kb.document WHERE project_id = :p ORDER BY key"),
        {"p": report.project_id},
    )
    return SimpleNamespace(
        pack=pack,
        registry=registry,
        project_id=report.project_id,
        versions=versions,
        documents=[tuple(r) for r in rows],
    )


@pytest.fixture
def orch() -> SimpleNamespace:
    return SimpleNamespace(
        Stub=Stub,
        Empty=Empty,
        IngestConfig=IngestConfig,
        ingest_stub=ingest_stub,
        page_content=page_content,
        write_pack=write_pack,
        CORPUS=CORPUS,
        MINIMAL=MINIMAL,
        MethodRegistry=MethodRegistry,
        load_methods=load_methods,
        setup_project=setup_project,
    )
