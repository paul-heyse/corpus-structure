"""Compare an exact qualifier through CLI and fresh MCP and challenge the native witness."""

import argparse
import json
import shutil
import sys
from pathlib import Path

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import text

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import ContributionPage
from corpus_structure.settings import Settings


def native_checks(conn, run_id):
    def stored(view):
        return conn.execute(text("""
            SELECT t.id, cfg.params, r.body, v.projection
            FROM ops.task t JOIN ops.task_result r ON r.task_id=coalesce(t.reused_task_id,t.id)
            JOIN ops.method_config cfg ON cfg.id=t.method_config_id
            JOIN kb.source_view v ON v.id=t.unit_id
            WHERE t.run_id=:run AND v.id=:view AND t.unit_type='source_view'
        """), dict(run=run_id, view=view)).mappings().one()

    def inspect(report, variant):
        body = report["body"]
        population = {row["contribution_id"]: row for row in body["contributions"]}
        cue, = [
            row for row in population.values()
            if row.get("component", {}).get("variant") == variant
        ]
        relation, = [
            row["component"] for row in population.values()
            if row.get("component", {}).get("qualifier_contribution_id") == cue["contribution_id"]
        ]
        operation = next(op for op in body["contribution_operations"]
                         if op["question"] == "source_predicate_frames")
        upstream = conn.scalar(text("SELECT body FROM ops.task_result WHERE task_id=:id"),
                               {"id": operation["annotation_origin_task_id"]})
        annotations = {"annotation:" + a["dependency_digest"]: a
                       for a in source_python(upstream["parse_detail"])["annotations"]}
        return population, cue["component"], relation, annotations

    event = stored(131)
    pop, cue, relation, annotations = inspect(event, "event_compound_then")
    annotation = annotations[cue["annotation"]]
    host = pop[relation["host_contribution_id"]]["component"]["predicate_token"]

    def local_matches(submitted, target):
        return conn.scalar(text("""
            SELECT ops.predicate_cue_recipe_matches(
              CAST(:projection AS jsonb), CAST(:annotation AS jsonb), CAST(:cue AS jsonb), :host)
        """), dict(projection=json.dumps(event["projection"]), annotation=json.dumps(annotation),
                   cue=json.dumps(submitted), host=target))

    wrong = cue["subordinate_token"]
    assert local_matches(cue, host) is True
    assert local_matches({**cue, "candidate_tokens": [wrong]}, wrong) is False
    assert local_matches({**cue, "token_indices": cue["token_indices"][:-1]}, host) is False

    normal = stored(116)
    pop, cue, relation, annotations = inspect(normal, "parameter_positive")
    target = pop[relation["host_contribution_id"]]
    selection = next(p for p in normal["params"]["inputs"]["passages"] if p["passage_id"] == cue["scope"])

    def cross_matches(submitted, passage):
        return conn.scalar(text("""
            SELECT ops.predicate_cross_block_host_matches(v,
                CAST(:population AS jsonb), CAST(:cue AS jsonb), CAST(:host AS jsonb),
                CAST(:relation AS jsonb), CAST(:cue_annotation AS jsonb),
                CAST(:host_annotation AS jsonb), CAST(:passage AS jsonb))
            FROM kb.source_view v WHERE v.id=116
        """), dict(
            population=json.dumps(pop), cue=json.dumps(cue), host=json.dumps(target),
            relation=json.dumps(submitted), cue_annotation=json.dumps(annotations[cue["annotation"]]),
            host_annotation=json.dumps(annotations[target["component"]["annotation"]]),
            passage=json.dumps(passage),
        ))

    assert cross_matches(relation, selection) is True
    assert cross_matches({**relation, "host_witness": {
        "kind": "parameter_note", "parameterization": target["contribution_id"],
    }}, selection) is False
    assert cross_matches(relation, {**selection, "start": 14640}) is False
    return {"event_f_exact": "passed", "event_f_wrong_and_clipped": "refused",
            "sigma_exact": "passed", "sigma_wrong_witness_and_clipped": "refused"}


async def delivery(page):
    command = shutil.which("ci")
    if command is None:
        raise ValueError("installed ci command is unavailable")
    transport = StdioTransport(
        command=command, args=["mcp", "serve", "--semantic-run", str(page.run_id)],
        cwd=str(Path.cwd()),
    )
    async with Client(transport, timeout=180) as client:
        request = {"run_id": page.run_id, **page.selection}
        reply = await client.call_tool("contributions", {"request": request})
    if reply.is_error or not isinstance(reply.structured_content, dict):
        raise ValueError("MCP did not deliver the pinned qualifier selection")
    fresh = ContributionPage.model_validate(reply.structured_content)
    assert fresh.run_id == page.run_id and fresh.cut_id == page.cut_id
    old_rows = tuple(item["row"] for item in page.items if item["population"] == "contribution")
    new_rows = tuple(item["row"] for item in fresh.items if item["population"] == "contribution")
    assert old_rows and new_rows == old_rows
    return [row["contribution_id"] for row in new_rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=int)
    args = parser.parse_args()
    page = ContributionPage.model_validate_json(sys.stdin.buffer.read())
    assert page.run_id == args.run_id
    delivered = anyio.run(delivery, page)
    with open_runtime_engine(Settings(), "nce02-guard-verification", purpose="maintenance") as engine:
        with read_snapshot(engine) as conn:
            guards = native_checks(conn, args.run_id)
    print(json.dumps(dict(
        outcome="passed", run_id=args.run_id, cut_id=page.cut_id,
        cli_mcp_matches=delivered, native=guards,
    )))


if __name__ == "__main__":
    main()
