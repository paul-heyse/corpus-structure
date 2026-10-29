"""The main profile's tools through an in-process client (P0-A-1; agent interface §3.5, §3.6, §6).

Each test that needs open tasks starts its own run with `fresh: agent.opus`, so its M24 tasks are
not reused from another test's completions.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest
from sqlalchemy import text

from corpus_structure.intervene import submission
from corpus_structure.intervene.testing import HarnessError, map_ids, rewrite, submit_batches


def fresh_run(agent: SimpleNamespace, world: SimpleNamespace) -> int:
    """A run with open M24 tasks. Earlier tests' leases are expired first, as abandoned sessions'
    would be: a twin holding an unexpired lease is never leased (P0-O-1)."""
    with world.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE ops.task SET lease_until = now() - interval '1 second' "
                "WHERE status = 'awaiting_agent' AND lease_until > now()"
            )
        )
    return agent.start_run(world, fresh=("agent.opus",))


def fixture_for(agent: SimpleNamespace, unit_key: str) -> dict[str, Any]:
    name = next(n for n in agent.TRACE_UNITS if agent.s0(n)["unit_key"] == unit_key)
    return agent.s0(name)


def lease(tools: Any, run: int) -> dict[str, Any]:
    (task,) = tools.call("queue_next", run=run)["tasks"]
    return task


def read_all(tools: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    served: list[dict[str, Any]] = []
    for part in range(1, task["parts"] + 1):
        served += tools.call("read_unit", task_id=task["task_id"], part=part)["sentences"]
    return served


def served_batch(agent: SimpleNamespace, tools: Any, task: dict[str, Any]) -> dict[str, Any]:
    """The task's fixture batch with its ids mapped onto the served packet (the harness's rule);
    reading every part on the way."""
    return served_with_map(agent, tools, task)[0]


def served_with_map(
    agent: SimpleNamespace, tools: Any, task: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fixture = fixture_for(agent, task["unit_key"])
    served = read_all(tools, task)
    mapping = map_ids(task["unit_key"], fixture["frame"], served)
    return rewrite(fixture["batch"], mapping, task["unit_key"]), served


def task_row(world: SimpleNamespace, task_id: int) -> Any:
    with world.engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT status, attempt, error, claimed_by, reused_task_id, "
                "packet_hash FROM ops.task WHERE id = :t"
            ),
            {"t": task_id},
        ).one()


# --- Leasing, reading, instructions ---------------------------------------------------------------


def test_lease_read_and_instruction_parts(agent: SimpleNamespace, world: SimpleNamespace) -> None:
    from corpus_structure.core._model.revision import CONTENT_HASH

    run = fresh_run(agent, world)
    tools = agent.tools(world.engine)
    task = lease(tools, run)
    raw = tools.raw("read_unit", task_id=task["task_id"], part=1)
    assert raw.content[0].text.startswith(f"# Unit {task['unit_key']}  ·  ")
    unit = raw.structured_content
    assert (
        unit["parts"] == task["parts"]
        and unit["hash"] == task_row(world, task["task_id"]).packet_hash
    )
    assert all({"id", "locator", "text"} <= set(s) for s in unit["sentences"])
    listing = tools.call("read_instructions", task_id=task["task_id"])
    names = [p["name"] for p in listing["parts"]]
    assert names == ["system", "guideline", "reference", "format", "schema"]
    reference = next(p for p in listing["parts"] if p["name"] == "reference")
    assert reference["pages"] >= 2  # about 35,600 characters: paged, never whole
    for p in listing["parts"]:
        for page in range(1, p["pages"] + 1):
            got = tools.call(
                "read_instructions", task_id=task["task_id"], part=p["name"], page=page
            )
            assert len(got["text"]) <= 24_000
    schema = tools.call("read_instructions", task_id=task["task_id"], part="schema")["text"]
    assert f"/{CONTENT_HASH[:12]}/" in schema  # the run's model-revision `$id` (R10)
    error = tools.error("read_unit", task_id=task["task_id"], part=task["parts"] + 1)
    assert "part" in error
    other = agent.tools(world.engine)  # another instance holds no lease on it
    assert "holds no lease" in other.error("read_unit", task_id=task["task_id"])


# --- Submission outcomes --------------------------------------------------------------------------


def test_a_first_unclean_submission_is_held_and_the_second_completes(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    run = fresh_run(agent, world)
    tools = agent.tools(world.engine)
    task = lease(tools, run)
    batch, served = served_with_map(agent, tools, task)
    batch["claims"][0]["predicate"] = "stat:no_such_predicate"  # rejected with its path
    evidence = batch["claims"][-1]["evidence"][0]
    evidence["quote"] = "a quote that is nowhere on the page"  # unlocated: coarse
    first = tools.call("propose_claims", task_id=task["task_id"], batch=batch)
    assert first["status"] == "held" and first["task_open"] is True
    assert any(r["path"].startswith("claims[0]") for r in first["rejected"])
    assert any(q["outcome"] == "coarse" for q in first["quotes"])
    row = task_row(world, task["task_id"])
    assert row.status == "awaiting_agent" and row.error["detail"]["rejected"]  # the first result
    second = tools.call(
        "propose_claims", task_id=task["task_id"], batch=batch, rationale="kept on purpose"
    )
    assert second["status"] == "done" and second["task_open"] is False
    with world.engine.connect() as conn:
        payload = conn.execute(
            text("SELECT payload FROM kb.observation WHERE id = :o"),
            {"o": second["observation_id"]},
        ).scalar_one()
    assert payload["rejected"] and payload["rationale"] == "kept on purpose"
    by_id = {s["id"]: {"locator": s["locator"], "text": s["text"]} for s in served}
    assert payload["citation_frame"]  # the served map's entries for the ids it cites
    assert all(payload["citation_frame"][i] == by_id[i] for i in payload["citation_frame"])


def test_a_unit_ref_mismatch_and_a_stale_schema_hash(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    run = fresh_run(agent, world)
    tools = agent.tools(world.engine)
    task = lease(tools, run)
    batch = served_batch(agent, tools, task)
    stale = tools.error(
        "propose_claims", task_id=task["task_id"], batch=batch, schema_hash="0" * 64
    )
    assert "schema_hash" in stale
    wrong = dict(batch, unit_ref="special/Normal.html#nowhere")
    held = tools.call("propose_claims", task_id=task["task_id"], batch=wrong)
    assert held["status"] == "held" and held["rejected"][0]["path"] == "unit_ref"


def test_unread_parts_and_a_lost_lease_commit_nothing(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    run = fresh_run(agent, world)
    first = agent.tools(world.engine)
    task = lease(first, run)
    fixture = fixture_for(agent, task["unit_key"])
    assert "not read" in first.error(
        "propose_claims", task_id=task["task_id"], batch=fixture["batch"]
    )
    batch = served_batch(agent, first, task)
    with world.engine.begin() as conn:  # the lease expires; another instance leases the unit
        conn.execute(
            text("UPDATE ops.task SET lease_until = now() - interval '1 second' WHERE id = :t"),
            {"t": task["task_id"]},
        )
    second = agent.tools(world.engine)
    again = lease(second, run)
    assert again["task_id"] == task["task_id"]
    error = first.error("propose_claims", task_id=task["task_id"], batch=batch)
    assert "holds no lease" in error
    row = task_row(world, task["task_id"])
    assert (row.status, row.attempt, row.error) == ("awaiting_agent", 2, None)


def test_a_failure_after_the_fence_rolls_back_and_sends_no_notify(
    agent: SimpleNamespace, world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = fresh_run(agent, world)
    tools = agent.tools(world.engine)
    task = lease(tools, run)
    batch = served_batch(agent, tools, task)
    listener = psycopg.connect(world.url, autocommit=True)
    listener.execute("LISTEN cs_agent_task_done")

    def notified() -> list[str]:
        out = []
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if select.select([listener.fileno()], [], [], 0.1)[0]:
                out += [n.payload for n in listener.notifies(timeout=0.1, stop_after=10)]
        return out

    def broken(*args: Any, **kwargs: Any) -> int:
        raise RuntimeError("the observation write failed")

    monkeypatch.setattr(submission, "_write", broken)
    assert tools.raw("propose_claims", task_id=task["task_id"], batch=batch).is_error
    assert notified() == []  # rolled back: never notified
    row = task_row(world, task["task_id"])
    assert (row.status, row.error) == ("awaiting_agent", None)  # still leased; may resubmit
    monkeypatch.undo()
    tools.call("read_unit", task_id=task["task_id"])  # the served record was kept
    done = tools.call("propose_claims", task_id=task["task_id"], batch=batch)
    assert done["status"] == "done"
    assert notified() == [str(run)]  # delivered at commit
    listener.close()


# --- Twins, reuse and packet hashes -------------------------------------------------------------


def test_twins_settle_end_to_end_across_two_complete_runs(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    fresh_run(agent, world)  # expires earlier leases
    # by_unit digests differ from every full-mode task here, so these runs are each other's twins
    first = agent.start_run(world, agent_reuse="by_unit")
    second = agent.start_run(world, agent_reuse="by_unit")
    tools = agent.tools(world.engine)
    unit = agent.s0("T3")
    results = submit_batches(
        tools.server, first, {unit["unit_key"]: (unit["batch"], unit["frame"])}
    )
    assert results[unit["unit_key"]].status == "done"
    with world.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT t.run_id, t.status, t.reused_task_id IS NOT NULL AS reused FROM ops.task t "
                "JOIN ops.method_config c ON c.id = t.method_config_id JOIN ops.method m ON m.id = "
                "c.method_id WHERE m.name = 'agent.opus' AND t.unit_key = :k AND t.run_id IN (:a, "
                ":b)"
            ),
            {"k": unit["unit_key"], "a": first, "b": second},
        ).all()
    assert {(r.run_id, r.status, r.reused) for r in rows} == {
        (first, "done", False),
        (second, "reused", True),
    }
    leased = [lease(tools, second)["unit_key"] for _ in range(len(agent.TRACE_UNITS) - 1)]
    assert unit["unit_key"] not in leased  # the settled twin is never offered
    assert tools.call("queue_next", run=second)["tasks"] == []


def test_packet_hashes_ignore_queue_order_and_a_promotion_during_the_run(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    a, b = fresh_run(agent, world), fresh_run(agent, world)

    def hashes(run: int) -> dict[str, str]:
        with world.engine.connect() as conn:
            return dict(
                conn.execute(
                    text(
                        "SELECT t.unit_key, t.packet_hash FROM ops.task t JOIN ops.method_config "
                        "c ON "
                        "c.id = t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE "
                        "m.name = 'agent.opus' AND t.run_id = :r"
                    ),
                    {"r": run},
                ).all()
            )

    assert hashes(a) == hashes(b) and len(hashes(a)) == len(agent.TRACE_UNITS)
    with world.engine.begin() as conn:  # a promotion after task creation, before serving
        conn.execute(
            text("UPDATE meta.project SET promoted_run_id = :r WHERE id = :p"),
            {"r": a, "p": world.project_id},
        )
    try:
        tools = agent.tools(world.engine)
        served = {}
        for _ in range(len(agent.TRACE_UNITS)):  # worked in the queue's order, run b
            task = lease(tools, b)
            served[task["unit_key"]] = tools.call("read_unit", task_id=task["task_id"])["hash"]
        assert served == hashes(b)
    finally:
        with world.engine.begin() as conn:
            conn.execute(
                text("UPDATE meta.project SET promoted_run_id = NULL WHERE id = :p"),
                {"p": world.project_id},
            )


def test_an_identical_m13_rerun_leaves_m24_tasks_reused(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    """P0CL-02's M24 half: M09 and M13 rerun with identical output (new task ids) do not ask for
    new proposals."""
    done_run = fresh_run(agent, world)
    tools = agent.tools(world.engine)
    batches = {
        agent.s0(n)["unit_key"]: (agent.s0(n)["batch"], agent.s0(n)["frame"])
        for n in agent.TRACE_UNITS
    }
    assert {r.status for r in submit_batches(tools.server, done_run, batches).values()} == {"done"}
    rerun = agent.start_run(world, fresh=("extract.math", "resolve.symbol_scope"))
    with world.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT m.name, t.status FROM ops.task t JOIN ops.method_config c ON c.id = "
                "t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE t.run_id = :r"
            ),
            {"r": rerun},
        ).all()
    by_method: dict[str, set[str]] = {}
    for name, status in rows:
        by_method.setdefault(name, set()).add(status)
    assert by_method["resolve.symbol_scope"] <= {"done", "empty"}  # ran again
    assert by_method["agent.opus"] == {"reused"}


# --- The harness ------------------------------------------------------------------------------


def test_the_harness_maps_by_locator_then_text_and_stops_on_a_misfit() -> None:
    served = [
        {"id": "s1", "locator": "p.html@sentence:Let X", "text": "Let X be normal."},
        {"id": "s2", "locator": "p.html@sentence:Then Y holds", "text": "Then Y holds."},
    ]
    frame = {
        "s1": {"locator": "p.html@sentence:Let X", "text": "Let X be normal."},
        "s4": {"locator": "p.html@sentence:Then", "text": "Then Y holds."},  # shorter locator
    }
    assert map_ids("p.html#u", frame, served) == {"s1": "s1", "s4": "s2"}
    with pytest.raises(HarnessError, match="s9"):
        map_ids(
            "p.html#u", {"s9": {"locator": "p.html@sentence:Nowhere", "text": "Nowhere."}}, served
        )


# --- Directions, the import bound and the stdio smoke test --------------------------------------


def test_record_direction_through_the_tool_and_ci_direct(
    agent: SimpleNamespace, world: SimpleNamespace, cli: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    from corpus_structure.cli import orchestrate as cli_orchestrate
    from corpus_structure.settings import Settings

    tools = agent.tools(world.engine, world.pack.parent)
    recorded = tools.call("record_direction", text="Prefer the family's own name.", scope="10.4")

    @contextmanager
    def engine(settings: Any, timeout: float = 30.0) -> Any:
        yield world.engine

    seams = dict(cli_orchestrate.PHASE0(), domains=world.pack.parent)
    monkeypatch.setattr(cli_orchestrate, "ENGINE", engine)
    monkeypatch.setattr(cli_orchestrate, "PHASE0", lambda: seams)
    result = cli(
        "direct",
        "Keep rationales short.",
        "--json",
        settings=lambda: Settings(database={"url": world.url}),
    )
    assert result.exit_code == 0, result.output
    log = (world.pack / "directions.md").read_text(encoding="utf-8")
    assert "Prefer the family's own name." in log and "Keep rationales short." in log
    with world.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT i.actor, i.body, i.refs, p.kind FROM ops.intervention i JOIN "
                "meta.payload_schema p ON p.id = i.payload_schema_id WHERE i.kind = 'direction' "
                "ORDER BY i.id"
            )
        ).all()
    assert [(r.actor, r.kind, r.refs) for r in rows] == [
        ("agent:session", "intervention_refs", {}),
        ("human:operator", "intervention_refs", {}),
    ]
    assert recorded["intervention_id"] and json.loads(result.stdout)["intervention_id"]


def test_a_pathological_formula_returns_within_its_bound(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    run = fresh_run(agent, world)
    tools = agent.tools(world.engine)
    task = lease(tools, run)
    batch = served_batch(agent, tools, task)
    claim = next(
        c
        for c in batch["claims"]
        if isinstance(c.get("object"), dict) and c["object"].get("t") == "formula"
    )
    claim["object"]["latex"] = "{" * 3000 + "x" + "}" * 3000 + "^" * 2000
    claim["evidence"][0]["quote"] = "(" * 400 + "a" * 400
    started = time.monotonic()
    out = tools.call("propose_claims", task_id=task["task_id"], batch=batch)
    assert time.monotonic() - started < 20 and out["status"] in ("held", "done")


IMPORT_CHECK = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("agent_conftest", {conftest!r})
m = importlib.util.module_from_spec(spec); sys.modules["agent_conftest"] = m
spec.loader.exec_module(m)
from sqlalchemy import create_engine
from corpus_structure.intervene.server import build_server
from corpus_structure.intervene.service import Session
from corpus_structure.intervene.testing import submit_batches
engine = create_engine({url!r})
unit = m.s0("T4")
batches = {{unit["unit_key"]: (unit["batch"], unit["frame"])}}
out = submit_batches(build_server(Session(engine)), {run}, batches)
loaded = [n for n in sys.modules if n.split(".")[0] in ("lark", "sympy")]
loaded += [n for n in sys.modules if n.endswith(("math.grammar", "math.spans", "math.scope"))]
grammar = sorted(loaded)
print(json.dumps({{"status": out[unit["unit_key"]].status, "grammar": grammar}}))
"""


def test_a_fresh_interpreter_serving_a_submission_loads_no_grammar(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    """P0CL-14: the server process imports the server, serves a submission, and has loaded no
    grammar module (the test conftest it loads for the fixture imports none at import time)."""
    run = fresh_run(agent, world)
    url = world.engine.url.render_as_string(hide_password=False)
    script = IMPORT_CHECK.format(
        conftest=str(Path(__file__).with_name("conftest.py")), url=url, run=run
    )
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=300, check=False
    )
    assert out.returncode == 0, out.stderr[-3000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got == {"status": "done", "grammar": []}


def test_ci_mcp_serve_writes_nothing_before_the_handshake(world: SimpleNamespace) -> None:
    env = {**os.environ, "CORPUS_DATABASE__URL": world.url}
    entry = "from corpus_structure.cli.app import main; main()"
    proc = subprocess.Popen(
        [sys.executable, "-c", entry, "mcp", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    try:
        assert proc.stdin is not None and proc.stdout is not None
        hello = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "0"},
            },
        }
        proc.stdin.write(json.dumps(hello) + "\n")
        proc.stdin.flush()
        first = proc.stdout.readline()
        reply = json.loads(first)  # the first thing on stdout is the protocol's reply
        assert reply["id"] == 1 and "result" in reply
    finally:
        proc.kill()
        proc.wait(timeout=10)


def test_a_fresh_run_asks_again_and_settlement_does_not_undo_it(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    """`--fresh agent.opus` creates open tasks although twins finished, and leasing (which
    settles twins first) leaves them open."""
    done = agent.start_run(world, agent_reuse="by_unit", fresh=("agent.opus",))
    tools = agent.tools(world.engine)
    unit = agent.s0("T2")
    submit_batches(tools.server, done, {unit["unit_key"]: (unit["batch"], unit["frame"])})
    again = fresh_run(agent, world)
    del again
    asking = agent.start_run(world, agent_reuse="by_unit", fresh=("agent.opus",))
    keys = {lease(tools, asking)["unit_key"] for _ in range(len(agent.TRACE_UNITS))}
    assert unit["unit_key"] in keys


def test_agent_mode_lists_the_reference_runs_entities_of_the_page(
    agent: SimpleNamespace, world: SimpleNamespace
) -> None:
    """A synthetic reference run (the world's run, promoted): only global entities with a claim
    whose evidence lies on its rendition of the same document are known entities."""
    from corpus_structure.core.db import repo

    ref = world.run

    def ins(conn: Any, table: str, **values: Any) -> int:
        cols = ", ".join(values)
        marks = ", ".join(f":{k}" for k in values)
        return int(
            conn.execute(
                text(f"INSERT INTO {table} ({cols}) VALUES ({marks}) RETURNING id"), values
            ).scalar_one()
        )

    with world.engine.begin() as conn:
        version = conn.execute(
            text("SELECT schema_version_id FROM ops.run WHERE id = :r"), {"r": ref}
        ).scalar_one()
        renditions = dict(
            conn.execute(
                text(
                    "SELECT d.meta->>'page', rr.rendition_id FROM kb.run_rendition rr JOIN "
                    "kb.document d "
                    "ON d.id = rr.document_id WHERE rr.run_id = :r"
                ),
                {"r": ref},
            ).all()
        )
        entity = {"run_id": ref, "schema_version_id": version, "scope": "global"}
        normal = ins(
            conn,
            "kb.entity",
            **entity,
            key="ent:" + "1" * 32,
            type="stat:DistributionFamily",
            label="normal",
        )
        gamma = ins(
            conn,
            "kb.entity",
            **entity,
            key="ent:" + "2" * 32,
            type="stat:DistributionFamily",
            label="gamma",
        )
        ins(
            conn,
            "kb.entity",
            **entity,
            key="ent:" + "3" * 32,
            type="stat:DistributionFamily",
            label="unclaimed",
        )
        conn.execute(
            text(
                "INSERT INTO kb.entity_alias (entity_id, alias, normalized, alias_kind) "
                "VALUES (:e, 'normal distribution', 'normal distribution', 'label')"
            ),
            {"e": normal},
        )
        for i, (subject, page) in enumerate(
            ((normal, "special/Normal.html"), (gamma, "special/Gamma.html"))
        ):
            claim = ins(
                conn,
                "kb.claim",
                run_id=ref,
                key=f"clm:{i:032d}",
                subject_id=subject,
                object_entity_id=subject,
                predicate="stat:has_distribution",
                schema_version_id=version,
                status="accepted",
                establishment="stated",
            )
            span = repo.upsert_spans(conn, renditions[page], [(0, 5)])[0]
            conn.execute(
                text(
                    "INSERT INTO kb.claim_evidence (claim_id, span_id, role) VALUES "
                    "(:c, :s, 'primary')"
                ),
                {"c": claim, "s": span},
            )
        conn.execute(
            text("UPDATE meta.project SET promoted_run_id = :r WHERE id = :p"),
            {"r": ref, "p": world.project_id},
        )
    try:
        run = fresh_run(agent, world)
        with world.engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT reference_run_id FROM ops.run WHERE id = :r"), {"r": run}
                ).scalar_one()
                == ref
            )
        tools = agent.tools(world.engine)
        texts = {}
        for _ in range(len(agent.TRACE_UNITS)):
            task = lease(tools, run)
            texts[task["unit_key"]] = (
                tools.raw("read_unit", task_id=task["task_id"]).content[0].text
            )
    finally:
        with world.engine.begin() as conn:
            conn.execute(
                text("UPDATE meta.project SET promoted_run_id = NULL WHERE id = :p"),
                {"p": world.project_id},
            )
    line = '- stat:DistributionFamily "normal" · aliases: normal distribution'
    for key, packet in texts.items():
        known = packet.split("## Known entities", 1)[1].split("## Text", 1)[0]
        if key.startswith("special/Normal.html"):
            assert line in known and "gamma" not in known and "unclaimed" not in known
        else:
            assert "(none)" in known
