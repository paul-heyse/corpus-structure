"""The pool loader against PostgreSQL (P0-P-1; pool and interchange §6 "Loader"): ADBC reads the
run's effective observations as of its cut, through `kb.run_observation`; repeated loads are
equal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import legacy_db_repo as repo
import pyarrow as pa
import pytest
from sqlalchemy import Engine, update

from corpus_structure.core.db import legacy_metadata as store
from corpus_structure.core.payloads import validate_payload
from corpus_structure.pool import contract, hydrate

from .legacy_pool import CutMismatch, RunNotFound, connect, load

T = store.metadata.tables
CUT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
REN = "ren:" + "1" * 32


def proposal(unit: str, label: str) -> repo.ObservationRow:
    batch = {"unit_ref": unit, "rendition": REN,
             "entities": [{"local_ref": "N", "type": "stat:DistributionFamily", "label": label,
                           "scope": "global"}]}  # fmt: skip
    payload = validate_payload("claim_proposal", {"batch": batch, "schema_version": "5" * 64})
    return repo.ObservationRow(0, "claim_proposal", payload)


def ipc(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue().to_pybytes()


@pytest.fixture
def sealed(committing_db: Engine, helpers: SimpleNamespace) -> SimpleNamespace:
    """A run sealed at CUT with a proposal finished before the cut and one after, and a reference
    run with a global and a local entity and their aliases."""
    with committing_db.begin() as conn:
        w = helpers.build_world(conn)
        reference = helpers.new_run(conn, w)
        run = helpers.new_run(conn, w, reference_run_id=reference)
        minute = timedelta(minutes=1)
        for finished, unit, label in ((CUT - minute, "u:before", "normal"),
                                      (CUT + minute, "u:after", "gamma")):  # fmt: skip
            task = helpers.new_task(conn, w, run, stage="propose", unit_type="segment")
            repo.write_observations(conn, task, 0, [proposal(unit, label)])
            conn.execute(
                update(T["ops.task"])
                .where(T["ops.task"].c.id == task)
                .values(status="done", finished_at=finished)
            )
        conn.execute(update(T["ops.run"]).where(T["ops.run"].c.id == run).values(cut_at=CUT))
        ent = {"run_id": reference, "schema_version_id": w.schema_version,
               "type": "stat:DistributionFamily"}  # fmt: skip
        normal = helpers.ins(conn, "kb.entity", **ent, key="ent:" + "b" * 32, label="normal",
                             scope="global")  # fmt: skip
        rendition = helpers.ins(conn, "kb.rendition", document_id=w.document, key=REN,
                                content_digest="d", canonical_text="x",
                                parse_status="ok")  # fmt: skip
        seg = helpers.ins(conn, "kb.segment", rendition_id=rendition, key="seg:" + "0" * 32,
                          kind="unit", start_offset=0, end_offset=1, depth=0, ordinal=0,
                          text="x")  # fmt: skip
        local = helpers.ins(conn, "kb.entity", **ent, key="ent:" + "d" * 32, label="X",
                            scope="local", scope_segment_id=seg)  # fmt: skip
        for entity_id, alias in ((normal, "normal"), (local, "x")):
            conn.execute(
                T["kb.entity_alias"]
                .insert()
                .values(entity_id=entity_id, alias=alias, normalized=alias, alias_kind="label")
            )
    url = committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return SimpleNamespace(url=url, run=run, reference=reference, normal=normal)


def test_the_pool_is_as_of_the_cut_and_repeated_loads_are_equal(sealed: SimpleNamespace) -> None:
    with connect(sealed.url) as conn:
        pool = load(conn, sealed.run, CUT, kinds=["claim_proposal"])
        again = load(conn, sealed.run, CUT, kinds=["claim_proposal"])
    units = pool[contract.BATCHES].column("unit_ref").to_pylist()
    assert units == ["u:before"]  # the proposal finished after the cut is absent
    assert pool[contract.OBSERVATIONS].num_rows == 1
    assert [h.candidates.entities[0].label for h in hydrate(pool)] == ["normal"]
    assert pool.meta.run.cut_at == CUT and pool.meta.run.reference_run_id == sealed.reference
    # only the reference run's global entities, with their aliases
    assert pool[contract.REFERENCE_ENTITIES].column("id").to_pylist() == [sealed.normal]
    assert pool[contract.REFERENCE_ALIASES].column("normalized").to_pylist() == ["normal"]
    assert pool.relations.keys() == again.relations.keys()
    for name, table in pool.relations.items():
        assert ipc(again[name]) == ipc(table), name


def test_the_loader_refuses_another_cut_and_an_unknown_run(sealed: SimpleNamespace) -> None:
    with connect(sealed.url) as conn:
        with pytest.raises(CutMismatch):
            load(conn, sealed.run, None)
        with pytest.raises(RunNotFound):
            load(conn, sealed.run + 1000, None)
        unsealed = load(conn, sealed.reference, None)  # the connection is usable after refusals
    assert unsealed[contract.OBSERVATIONS].num_rows == 0
    assert unsealed[contract.REFERENCE_ENTITIES].num_rows == 0
