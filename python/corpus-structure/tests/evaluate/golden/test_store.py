"""The golden store: passes and their payload schema, agreement, items keyed by derivation with
`context` flags, and staleness and re-location across renditions (P0-E-1; evaluation §3.3).

The unit is S0's U12 (`special/Gamma.html#mom1`, forced into the dev set by `core12`), whose
fixture batch records a context premise: the assumption `st0` anchored at `c1` and its premise
claim `c_X_stdgamma` citing only `c1` (D2 §10.2). Edited renditions are new bytes of the page.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from corpus_structure.core.db import repo
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.payload_schemas import PayloadReaders, UnknownPayloadSchema
from corpus_structure.core.vocab import DocumentSplit, GoldenPass
from corpus_structure.evaluate import goldens, sets
from corpus_structure.evaluate.agreement import AgreementResult
from corpus_structure.evaluate.split import load_eval, split_documents
from corpus_structure.methods.llm import parse as A0

UNIT = "special/Gamma.html#mom1"
PAGE = "special/Gamma.html"
UNIT_DIV = b'<div class="unit" id="mom1">'
NEW_PARAGRAPH = b"<p>A new paragraph appears here before the unit.</p>\n"
# a sentence sharing c1's locator prefix ("Suppose that \( X \) has the standard"), unlike its text
SAME_PREFIX = b"<p>Suppose that \\( X \\) has the standard normal distribution instead.</p>\n"
CITED_S2 = (b"<li>\\(\\E(X) = k\\)</li>", b"<li>\\(\\E(X) = k + 0\\)</li>")


@pytest.fixture
def world(db: Connection, gw: SimpleNamespace, env: Any, tmp_path: Path) -> SimpleNamespace:
    w = gw.setup_world(db, tmp_path)
    w.source = gw.ingest_run(db, w, gw.spike_contents(w))
    w.config = load_eval(w.pack)
    split_documents(db, w.project_id, w.config.split)
    w.made = sets.create_golden_set(
        db, project_id=w.project_id, split=DocumentSplit.DEV, label="p0", config=w.config,
        registry=w.registry, commit="test",
    )  # fmt: skip
    w.unit = db.execute(
        text("SELECT id FROM eval.golden_unit WHERE golden_set_id = :s AND unit_key = :k"),
        {"s": w.made.set_id, "k": UNIT},
    ).scalar_one()
    w.fixture = env.s0("U12")
    w.guideline = w.versions.guideline_version_id
    w.macros = {k: MacroDef(body=v) for k, v in w.methods.sections["math"]["macros"].items()}
    w.rendition = db.execute(
        text("SELECT authored_rendition_id FROM eval.golden_unit WHERE id = :u"), {"u": w.unit}
    ).scalar_one()
    return w


def record(db: Connection, w: SimpleNamespace, p: GoldenPass, session: str = "") -> int:
    return goldens.record_pass(
        db, w.unit, p, guideline_version_id=w.guideline, batch=w.fixture.batch,
        frame=w.fixture.frame, session_ref=session or f"server-{p.value}",
        model="claude-sonnet-5-5", inputs={"guideline": w.guideline, "inputs": "v1"},
        decisions=[{"item": "c_X_mean", "decision": "keep both"}] if p is GoldenPass.C else None,
    )  # fmt: skip


def all_passes(db: Connection, w: SimpleNamespace) -> dict[GoldenPass, int]:
    return {p: record(db, w, p) for p in GoldenPass}


def items(db: Connection, w: SimpleNamespace, pass_c: int, rendition: int) -> goldens.Items:
    return goldens.ensure_items(
        db, pass_c, rendition, w.versions.schema_version_id, macros=w.macros
    )


def rows(db: Connection, sql: str, **params: Any) -> Any:
    return db.execute(text(sql), params).scalar()


# --- Passes ---------------------------------------------------------------------------------------


def test_a_pass_stores_its_batch_its_frame_as_version_1_and_its_payload_schema(
    db: Connection, world: SimpleNamespace
) -> None:
    pass_a = record(db, world, GoldenPass.A)
    stored = goldens.read_pass(db, pass_a)
    assert (stored.batch, stored.newest.frame) == (world.fixture.batch, world.fixture.frame)
    v1 = stored.frames[0]
    assert (len(stored.frames), v1.version, v1.parent_id, v1.reason) == (1, 1, None, "authored")
    assert stored.payload_schema_id == repo.registered_ids(db, ["golden_batch"])["golden_batch"]
    with pytest.raises(goldens.GoldenStoreError, match="model and inputs"):
        goldens.record_pass(db, world.unit, GoldenPass.B, guideline_version_id=world.guideline,
                            batch=world.fixture.batch, frame=world.fixture.frame,
                            session_ref="s", model="", inputs={})  # fmt: skip
    with pytest.raises(goldens.GoldenStoreError, match="decisions"):
        goldens.record_pass(db, world.unit, GoldenPass.C, guideline_version_id=world.guideline,
                            batch=world.fixture.batch, frame=world.fixture.frame,
                            session_ref="s", model="m", inputs={"x": 1})  # fmt: skip
    with pytest.raises(IntegrityError, match="duplicate key"), db.begin_nested():
        record(db, world, GoldenPass.A, session="another")


def test_a_pass_whose_payload_schema_is_unknown_is_refused_on_read(
    db: Connection, world: SimpleNamespace
) -> None:
    pass_a = record(db, world, GoldenPass.A)
    with pytest.raises(UnknownPayloadSchema):
        goldens.read_pass(db, pass_a, readers=PayloadReaders([]))
    frame_schema = repo.registered_ids(db, ["citation_frame"])["citation_frame"]
    other = repo.store_golden_pass(
        db,
        {"golden_unit_id": world.unit, "pass": "b", "guideline_version_id": world.guideline,
         "batch": {"unit_ref": UNIT}, "session_ref": "s", "model": "m", "inputs": {"x": 1},
         "payload_schema_id": frame_schema},
    )  # fmt: skip
    with pytest.raises(goldens.GoldenStoreError, match="of kind 'citation_frame'"):
        goldens.read_pass(db, other)


def test_the_agreement_is_validated_against_e2a_model_and_stored_whole(
    db: Connection, world: SimpleNamespace
) -> None:
    result = AgreementResult(
        unit=UNIT, tiers={}, per_predicate={}, matched=(), differing=(), a_only=(), b_only=(),
        undecided=1,
    )  # fmt: skip
    goldens.record_agreement(db, world.unit, result)
    stored = rows(db, "SELECT agreement FROM eval.golden_unit WHERE id = :u", u=world.unit)
    assert AgreementResult.model_validate(stored) == result
    with pytest.raises(ValidationError):
        goldens.record_agreement(db, world.unit, {"unit": UNIT, "tiers": "none"})
    with pytest.raises(goldens.GoldenStoreError, match="no pass c"):
        goldens.mark_adjudicated(db, world.unit)
    record(db, world, GoldenPass.C)
    goldens.mark_adjudicated(db, world.unit)
    assert rows(db, "SELECT status FROM eval.golden_unit WHERE id = :u", u=world.unit) == (
        "adjudicated"
    )


# --- Items ----------------------------------------------------------------------------------------


def test_items_carry_context_flags_and_are_keyed_by_their_derivation(
    db: Connection, world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    passes = all_passes(db, world)
    got = items(db, world, passes[GoldenPass.C], world.rendition)
    assert (got.state, got.relocated, got.dropped) == ("derived", False, 0)
    found = db.execute(
        text("SELECT item_type, local_ref, context, citation_frame_id, cascade_version FROM "
             "eval.golden_item WHERE golden_pass_id = :c"), {"c": passes[GoldenPass.C]}
    ).all()  # fmt: skip
    b = world.fixture.batch
    expected = (
        {("entity", e.local_ref) for e in b.entities}
        | {("statement", s.local_ref) for s in b.statements}
        | {("claim", c.local_ref) for c in b.claims}
        | {("alternative", f"alt{i}") for i in range(len(b.alternatives))}
        | {("unsupported", u.local_ref) for u in b.unsupported}
    )
    assert {(r.item_type, r.local_ref) for r in found} == expected and got.count == len(expected)
    assert {r.local_ref for r in found if r.context} == {"st0", "c_X_stdgamma"}
    v1 = goldens.read_pass(db, passes[GoldenPass.C]).frames[0].id
    assert {(r.citation_frame_id, r.cascade_version) for r in found} == {(v1, A0.CASCADE_VERSION)}
    assert items(db, world, passes[GoldenPass.C], world.rendition).state == "existing"
    original = A0.CASCADE_VERSION
    monkeypatch.setattr(A0, "CASCADE_VERSION", "cascade-test-2")
    again = items(db, world, passes[GoldenPass.C], world.rendition)
    assert (again.state, again.count) == ("derived", got.count)
    by_version = db.execute(
        text("SELECT cascade_version, count(*) FROM eval.golden_item WHERE golden_pass_id = :c "
             "GROUP BY 1 ORDER BY 1"), {"c": passes[GoldenPass.C]}
    ).all()  # fmt: skip
    assert sorted(tuple(r) for r in by_version) == sorted(
        [(original, got.count), ("cascade-test-2", got.count)]
    )


def _edited(gw: SimpleNamespace, db: Connection, w: SimpleNamespace, raw: bytes) -> int:
    """A rendition of new bytes of the page, ingested by a later run; its id."""
    doc = gw.add_document(db, w, PAGE, raw)
    gw.ingest_run(db, w, {doc: gw.rendition_of(raw, PAGE)}, finish=False)
    return int(
        rows(db, "SELECT rendition_id FROM kb.rendition_build WHERE document_id = :d", d=doc)
    )


def _snapshot(db: Connection, sql: str, **params: Any) -> Any:
    return rows(db, f"SELECT jsonb_agg(to_jsonb(x) ORDER BY x.id) FROM ({sql}) x", **params)


def test_relocation_adds_frame_versions_and_leaves_what_scored_the_old_ones(
    db: Connection, gw: SimpleNamespace, world: SimpleNamespace
) -> None:
    passes = all_passes(db, world)
    pass_c = passes[GoldenPass.C]
    goldens.mark_adjudicated(db, world.unit)
    first = items(db, world, pass_c, world.rendition)
    raw = gw.raw_page(PAGE)
    assert raw.count(UNIT_DIV) == 1 and raw.count(CITED_S2[0]) == 1

    # an edit elsewhere: a new paragraph before the unit; the frame resolves as recorded
    shifted = _edited(gw, db, world, raw.replace(UNIT_DIV, NEW_PARAGRAPH + UNIT_DIV))
    moved = items(db, world, pass_c, shifted)
    assert (moved.state, moved.relocated, moved.frame_version_id) == (
        "derived", False, first.frame_version_id
    )  # fmt: skip
    starts = db.execute(
        text("SELECT rendition_id, (payload->'evidence'->0->>'start')::int FROM eval.golden_item "
             "WHERE golden_pass_id = :c AND local_ref = 'c_X_mean'"), {"c": pass_c}
    ).all()  # fmt: skip
    by_rendition = dict(starts)
    assert by_rendition[shifted] > by_rendition[world.rendition]

    # what a result scored through version 1, before the re-location
    result_run = sets.source_run(db, world.project_id)
    claim_item = rows(db, "SELECT id FROM eval.golden_item WHERE golden_pass_id = :c AND "
                      "rendition_id = :r AND local_ref = 'c_X_mean'", c=pass_c,
                      r=world.rendition)  # fmt: skip
    db.execute(text(
        "INSERT INTO eval.alignment (run_id, golden_item_id, target_type, tier, score) VALUES "
        "(:r, :i, 'claim', 'full', 1)"), {"r": result_run, "i": claim_item})  # fmt: skip
    db.execute(text(
        "INSERT INTO eval.result (run_id, golden_set_id, scope_type, metric, tier, value, n, "
        "golden_snapshot) VALUES (:r, :s, 'all', 'f1', 'full', 1, 1, ARRAY[:c]::bigint[])"),
        {"r": result_run, "s": world.made.set_id, "c": pass_c})  # fmt: skip
    before = {
        "frames": _snapshot(db, "SELECT * FROM eval.citation_frame"),
        "items": _snapshot(db, "SELECT * FROM eval.golden_item"),
        "result": _snapshot(db, "SELECT * FROM eval.result"),
        "alignment": _snapshot(db, "SELECT * FROM eval.alignment"),
    }

    # a sentence that shares c1's locator prefix: c1 is re-located by its recorded text
    longer = _edited(gw, db, world, raw.replace(UNIT_DIV, SAME_PREFIX + UNIT_DIV))
    relocated = items(db, world, pass_c, longer)
    assert (relocated.state, relocated.relocated) == ("derived", True)
    for p, pid in passes.items():
        stored = goldens.read_pass(db, pid)
        v1, v2 = stored.frames
        assert (v2.version, v2.parent_id, v2.reason.startswith("relocated onto")) == (
            2, v1.id, True
        ), p  # fmt: skip
        assert {s: e.text for s, e in v2.frame.root.items()} == {
            s: e.text for s, e in v1.frame.root.items()
        }
        assert v2.frame["c1"].locator != v1.frame["c1"].locator
        assert {s for s in v1.frame if v2.frame[s] != v1.frame[s]} == {"c1"}
    assert relocated.frame_version_id == goldens.read_pass(db, pass_c).frames[1].id
    assert rows(db, "SELECT status FROM eval.golden_unit WHERE id = :u", u=world.unit) == (
        "adjudicated"
    )
    after_frames = _snapshot(db, "SELECT * FROM eval.citation_frame WHERE version = 1")
    assert after_frames == before["frames"]
    assert _snapshot(db, "SELECT * FROM eval.golden_item WHERE rendition_id <> :r",
                     r=longer) == before["items"]  # fmt: skip
    assert _snapshot(db, "SELECT * FROM eval.result") == before["result"]
    assert _snapshot(db, "SELECT * FROM eval.alignment") == before["alignment"]

    # an edit to a cited sentence: no sentence carries its recorded text, so the unit is stale
    edited = _edited(gw, db, world, raw.replace(*CITED_S2))
    stale = items(db, world, pass_c, edited)
    assert stale.state == "stale"
    assert rows(db, "SELECT count(*) FROM eval.golden_item WHERE rendition_id = :r", r=edited) == 0
    assert rows(db, "SELECT status FROM eval.golden_unit WHERE id = :u", u=world.unit) == "stale"
    status = sets.golden_status(db, world.project_id, "p0")
    assert status.sets[0].stale == [UNIT]
