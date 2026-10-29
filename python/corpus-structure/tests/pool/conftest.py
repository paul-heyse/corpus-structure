"""Arrow fixtures of the pool (P0-P-1): hand-made inputs of `pool.build`, no database server.

`arrow_pool` returns a namespace with:
- `run`: the `RunRow` (sealed, with a reference run);
- `registry`: `PayloadSchemaRow`s for every registered payload class (ids from 1 in the registry
  entries' order) plus a second `claim_proposal` version (`absent` upcast), so the pool reads one
  observation under the older id;
- `observations`: `kb.run_observation` rows under M3's types, each payload the writer's dump of a
  validated core payload (`ClaimProposalPayload`, `AuthorMarkupPayload`, `JudgmentPayload`);
- `reference_entities`, `reference_aliases`: the reference run's `kb.entity` and `kb.entity_alias`
  rows;
- `stored`: the stored batches by observation id; `build(**changes)`: `pool.build` over them.

Other packages' tests (P0-P-2's harness, C1's `arrow_pool` cases) build on the same shapes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pyarrow as pa
import pytest

from corpus_structure.core.batch import StoredBatch
from corpus_structure.core.db.store import dumps
from corpus_structure.core.payload_schemas import PayloadSchemaRow
from corpus_structure.core.payloads import validate_payload
from corpus_structure.pool import contract
from corpus_structure.schema import model, registry

RUN = 7
REFERENCE_RUN = 3
CUT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
REN = "ren:" + "1" * 32
SCHEMA_VERSION = "5" * 64

BATCH_A = {
    "unit_ref": "special/Normal.html#rel1",
    "rendition": REN,
    "entities": [
        {"local_ref": "X", "type": "stat:RandomVariable", "label": "X", "scope": "local",
         "extent": "statement", "symbol": "X", "scope_segment": "seg:1"},
        {"local_ref": "N", "type": "stat:DistributionFamily", "label": "normal distribution",
         "scope": "global", "aliases": ["normally distributed"]},
    ],
    "statements": [
        {"local_ref": "st1", "kind": "theorem", "anchor": ["seg:2"]},
        {"local_ref": "last", "anchor": "outside",
         "descriptor": {"start": 3, "end": 18, "target": "special/Normal.html#thm3"}},
    ],
    "claims": [
        {"local_ref": "c1", "predicate": "stat:has_distribution", "subject": "X",
         "object": {"ref": "N"}, "qualifiers": {"core:modality": "supposed"},
         "statement": "st1", "statement_role": "premise",
         "evidence": [{"start": 10, "end": 40, "role": "primary"}]},
        {"local_ref": "c0", "predicate": "stat:has_distribution", "subject": "X",
         "object": {"ref": "N"}, "statement": "st1",
         "evidence": [{"start": 41, "end": 60, "role": "primary", "coarse": True}]},
    ],
    "alternatives": [{"refs": ["c1", "c0"], "reason": "two readings"}],
    "unsupported": [{"local_ref": "u1", "start": 61, "end": 70, "reason": "r", "coarse": True}],
}  # fmt: skip
BATCH_B = {
    "unit_ref": "special/Normal.html#rel2",
    "rendition": REN,
    "entities": [{"local_ref": "N", "type": "stat:DistributionFamily", "label": "normal",
                  "scope": "global"}],
}  # fmt: skip
BATCH_EMPTY = {"unit_ref": "special/Normal.html#rel3", "rendition": REN}


def registry_rows() -> list[PayloadSchemaRow]:
    rows = [
        PayloadSchemaRow(i, e.class_, e.kind, e.version, None, None)
        for i, e in enumerate(registry.payload_schema_entries(model.load()), start=1)
    ]
    first = next(r for r in rows if r.kind == "claim_proposal")
    rows.append(PayloadSchemaRow(100, first.class_, "claim_proposal", 2, first.id, "absent"))
    return rows


def _proposal(batch: dict[str, Any]) -> Any:
    return validate_payload("claim_proposal", {"batch": batch, "schema_version": SCHEMA_VERSION})


def observation_rows(rows: list[PayloadSchemaRow]) -> list[dict[str, Any]]:
    """The observation rows: (id, kind, payload, recorded schema id)."""
    first = next(r.id for r in rows if r.kind == "claim_proposal" and r.version == 1)
    ids = {r.kind: r.id for r in rows if r.version == 1}
    markup = validate_payload("author_markup", {"markup": "dfn", "value": None})
    judgment = validate_payload("judgment", {
        "target": {"kind": "claim", "ref": "clm:" + "a" * 32, "key_scheme": 1},
        "decision": "accept",
        "rationale": "fine", "guideline_version": "g1"})  # fmt: skip
    payloads = [
        (101, "claim_proposal", _proposal(BATCH_A), 100),
        (102, "claim_proposal", _proposal(BATCH_B), first),
        (103, "author_markup", markup, ids["author_markup"]),
        (104, "judgment", judgment, ids["judgment"]),
        (105, "claim_proposal", _proposal(BATCH_EMPTY), first),
    ]
    return [
        {"run_id": RUN, "id": oid, "task_id": 900 + n, "ordinal": 0, "kind": kind,
         "rendition_id": 5, "segment_id": None, "span_id": None,
         "payload": dumps(payload.model_dump(mode="json")), "payload_schema_id": schema_id,
         "score": None, "outcome": "produced", "created_at": CUT}
        for n, (oid, kind, payload, schema_id) in enumerate(payloads)
    ]  # fmt: skip


ENTITY_ROWS = [
    {"id": 51, "run_id": REFERENCE_RUN, "key": "ent:" + "b" * 32, "schema_version_id": 1,
     "type": "stat:DistributionFamily", "label": "normal distribution", "scope": "global",
     "scope_segment_id": None, "attrs": "{}", "kind": None, "resolved_to_id": None,
     "confidence": None},
    {"id": 52, "run_id": REFERENCE_RUN, "key": "ent:" + "c" * 32, "schema_version_id": 1,
     "type": "stat:DistributionFamily", "label": "gaussian", "scope": "global",
     "scope_segment_id": None, "attrs": "{}", "kind": None, "resolved_to_id": None,
     "confidence": None},
]  # fmt: skip
ALIAS_ROWS = [
    {"entity_id": 51, "alias": "normal distribution", "normalized": "normal distribution",
     "alias_kind": "label"},
    {"entity_id": 51, "alias": "Normal", "normalized": "normal", "alias_kind": "label"},
    {"entity_id": 52, "alias": "normal", "normalized": "normal", "alias_kind": "term"},
]  # fmt: skip


def table(rows: list[dict[str, Any]], schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pylist(rows, schema=schema)


@pytest.fixture
def arrow_pool() -> SimpleNamespace:
    rows = registry_rows()
    ns = SimpleNamespace(
        run=contract.RunRow(RUN, CUT, 1, 1, 1, REFERENCE_RUN),
        registry=rows,
        observations=table(observation_rows(rows), contract.raw_schema()),
        reference_entities=table(ENTITY_ROWS, contract.reference_schema("reference_entities")),
        reference_aliases=table(ALIAS_ROWS, contract.reference_schema("reference_aliases")),
        stored={101: StoredBatch.model_validate(BATCH_A), 102: StoredBatch.model_validate(BATCH_B),
                105: StoredBatch.model_validate(BATCH_EMPTY)},
    )  # fmt: skip

    def build(**changes: Any) -> contract.Pool:
        names = ("run", "registry", "observations", "reference_entities", "reference_aliases")
        args = {k: getattr(ns, k) for k in names}
        return contract.build(**(args | changes))

    ns.build = build
    return ns
