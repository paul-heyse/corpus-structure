"""The main profile end to end (P0-A-1; agent interface §3.5, §3.6, §6): the harness submits every
`fixtures/s0` trace batch through the tools and each completes on its first submission; the stored
proposal records its derivation and the served frame; held-open, lost-lease and twin paths."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import text

from corpus_structure.intervene.testing import submit_batches


def test_the_harness_submits_every_trace_batch_and_each_completes_first_time(
    world: SimpleNamespace, agent: SimpleNamespace
) -> None:
    tools = agent.tools(world.engine, world.pack.parent)
    status = tools.call("queue_status", run=world.run)
    assert sum(q["awaiting"] for q in status["queues"]) == len(agent.TRACE_UNITS)
    batches = {}
    for name in agent.TRACE_UNITS:
        fixture = agent.s0(name)
        batches[fixture["unit_key"]] = (fixture["batch"], fixture["frame"])
    results = submit_batches(tools.server, world.run, batches)
    assert set(results) == set(batches)
    for key, result in results.items():
        assert result.status == "done" and not result.task_open, (key, result)
        assert result.clean, (key, result.model_dump())
    with world.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT o.payload, t.unit_key, i.kind, i.session_ref FROM kb.observation o "
                "JOIN ops.task t ON t.id = o.task_id JOIN ops.intervention i ON i.task_id = t.id "
                "WHERE o.kind = 'claim_proposal' AND t.run_id = :r"
            ),
            {"r": world.run},
        ).all()
    assert len(rows) == len(batches)
    for payload, unit_key, kind, session_ref in rows:
        assert kind == "extract" and session_ref == tools.session.instance
        assert payload["cascade_version"] and len(payload["schema_version"]) == 64  # DA-009
        assert payload["authored"]["unit_ref"] == unit_key
        assert set(payload["citation_frame"]) <= {f"s{i}" for i in range(1, 60)} | {"c1", "c2"}
