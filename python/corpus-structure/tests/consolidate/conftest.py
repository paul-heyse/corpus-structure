"""Shared fixtures of the consolidation tests (P0-C-1; consolidation §6).

- `world`: the statistics pack compiled, its `methods.yaml` configuration (label rules, fallback
  macros), and retained historical renditions of the four
  vendored spike pages as `Page`s, segment ids assigned in key order;
- `world.stored(name)`: a `fixtures/s0` batch located on its page by A0's `parse`;
- `world.pool(units, …)`: an Arrow pool (`pool.build`, no server) holding one `claim_proposal`
  observation per unit, plus any extra observation rows; `world.inputs()` the pass inputs.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from archived_source import archived_rendition, archived_title
import yaml

from corpus_structure.consolidate.assemble import Inputs, Page
from corpus_structure.consolidate.pass_ import ConsolidateConfig
from corpus_structure.core import tex
from corpus_structure.core.batch import AuthoredBatch, CitationFrame, StoredBatch
from corpus_structure.core.db.store import dumps
from corpus_structure.core.evidence import (
    content_digest,
    document_key,
    rendition_key,
    segment_key,
)
from corpus_structure.core.payload_schemas import PayloadSchemaRow
from corpus_structure.core.payloads import validate_payload
from corpus_structure.methods.llm.parse import parse
from corpus_structure.pool import contract
from corpus_structure.schema import model, registry
from corpus_structure.schema.compile import compile_schema
from corpus_structure.schema.pack import load_pack

REPO = Path(__file__).resolve().parents[4]
ROOT = "siegrist_random/random"
PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)
SCHEMA_VERSION = "5" * 64
CUT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
RUN = 7


@functools.cache
def compiled() -> Any:
    return compile_schema([load_pack(REPO / "domains/statistics")])


@functools.cache
def config() -> ConsolidateConfig:
    raw = yaml.safe_load((REPO / "domains/statistics/methods.yaml").read_text(encoding="utf-8"))
    return ConsolidateConfig(aliases=raw["aliases"], math=raw["math"])


@functools.cache
def page(name: str, rendition_id: int) -> Page:
    uri = f"{ROOT}/{name}"
    raw = (REPO / "fixtures/trace/corpus" / uri).read_bytes()
    content = archived_rendition(name, raw)
    doc = document_key("statistics", uri, hashlib.sha256(raw).hexdigest())
    ren = rendition_key(doc, content_digest(content))
    keys = sorted(segment_key(ren, s.kind, s.start, s.end) for s in content.document.walk())
    ids = {k: rendition_id * 100_000 + i for i, k in enumerate(keys)}
    macros = tex.effective_macros(content.macros, config().macros())
    return Page(rendition_id, rendition_id, doc, name, content, macros, ids, archived_title(name))


def pages() -> dict[int, Page]:
    return {i: page(name, i) for i, name in enumerate(PAGES, start=1)}


@functools.cache
def s0(name: str) -> dict[str, Any]:
    return json.loads((REPO / "fixtures/s0" / f"{name}.json").read_text(encoding="utf-8"))


def page_of_unit(name: str) -> Page:
    wanted = s0(name)["provenance"]["rendition"]["page"]
    return next(p for p in pages().values() if p.page == wanted)


@functools.cache
def stored(name: str) -> StoredBatch:
    raw = s0(name)
    p = page_of_unit(name)
    return parse(
        p.view,
        AuthoredBatch.model_validate(raw["batch"]),
        CitationFrame.model_validate(raw["frame"]),
        compiled().names.to_prefixed,
    ).stored


@functools.cache
def registry_rows() -> tuple[PayloadSchemaRow, ...]:
    return tuple(
        PayloadSchemaRow(i, e.class_, e.kind, e.version, None, None)
        for i, e in enumerate(registry.payload_schema_entries(model.load()), start=1)
    )


def proposal_row(
    oid: int,
    name: str,
    rendition_id: int | None = None,
    batch: StoredBatch | None = None,
    task: int | None = None,
) -> dict[str, Any]:
    raw = s0(name)
    payload = validate_payload(
        "claim_proposal",
        {
            "batch": (batch or stored(name)).model_dump(mode="json", by_alias=True),
            "schema_version": SCHEMA_VERSION,
            "authored": raw["batch"],
            "citation_frame": raw["frame"],
            "cascade_version": "quote-cascade/1",
        },
    )
    return observation(
        oid,
        "claim_proposal",
        payload,
        page_of_unit(name).rendition_id if rendition_id is None else rendition_id,
        task,
    )


def observation(
    oid: int, kind: str, payload: Any, rendition_id: int | None, task: int | None = None
) -> dict[str, Any]:
    ids = {r.kind: r.id for r in registry_rows()}
    return {
        "run_id": RUN,
        "id": oid,
        "task_id": task or 1000 + oid,
        "ordinal": 0,
        "kind": kind,
        "rendition_id": rendition_id,
        "segment_id": None,
        "span_id": None,
        "payload": dumps(payload.model_dump(mode="json", by_alias=True)),
        "payload_schema_id": ids[kind],
        "score": None,
        "outcome": "produced",
        "created_at": CUT,
    }


def build_pool(
    rows: Sequence[dict[str, Any]],
    reference: tuple[list, list] | None = None,
) -> contract.Pool:
    import pyarrow as pa

    obs = pa.Table.from_pylist(list(rows), schema=contract.raw_schema())
    entities = aliases = None
    if reference is not None:
        entities = pa.Table.from_pylist(
            reference[0], schema=contract.reference_schema(contract.REFERENCE_ENTITIES)
        )
        aliases = pa.Table.from_pylist(
            reference[1], schema=contract.reference_schema(contract.REFERENCE_ALIASES)
        )
    run = contract.RunRow(RUN, CUT, 1, 1, 1, 3 if reference is not None else None)
    return contract.build(
        run, registry_rows(), obs, entities, aliases, ["claim_proposal", "author_markup"]
    )


def inputs(**changes: Any) -> Inputs:
    ps = pages()
    c = compiled()
    args: dict[str, Any] = {
        "pages": ps,
        "documents": {i: i for i in ps},
        "compiled": c,
        "labels": config().labels(c.names.to_prefixed),
    }
    return Inputs(**(args | changes))


@pytest.fixture(scope="session")
def world() -> SimpleNamespace:
    return SimpleNamespace(
        repo=REPO,
        compiled=compiled,
        config=config,
        page=page,
        pages=pages,
        s0=s0,
        stored=stored,
        proposal=proposal_row,
        observation=observation,
        pool=build_pool,
        inputs=inputs,
        page_of_unit=page_of_unit,
        registry_rows=registry_rows,
    )
