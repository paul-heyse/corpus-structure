"""Verify current neighborhood query, fresh MCP, and exact detached report closure."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import text

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contextual_navigation import ContextualNeighborhoodQuery, NeighborhoodParams
from corpus_structure.serve.protocol import QueryContext
from corpus_structure.settings import Settings

PROJECT = "wce-gs120-method-development-20261106"
CLI = str(Path(sys.executable).with_name("ci"))


async def fresh_mcp(request):
    transport = StdioTransport(
        command=CLI, args=["mcp", "serve", "--semantic-run", str(request["run_id"])]
    )
    async with Client(transport, timeout=180) as client:
        reply = await client.call_tool("contextual_neighborhood", {"request": request})
        return reply.structured_content


def ci(*args, stdin=None):
    process = subprocess.run([CLI, *args], capture_output=True, text=True, input=stdin)
    if process.returncode:
        raise ValueError(process.stdout[:600] or process.stderr[-600:])
    return json.loads(process.stdout), process.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    args = parser.parse_args()
    with (
        open_runtime_engine(Settings(), "nce-neighborhood-reader", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        cut, task, report = conn.execute(
            text("""
            SELECT cr.cut_id,ct.task_id,op->'contextual_enrichment'
            FROM ops.completed_result cr JOIN ops.cut_task ct ON ct.cut_id=cr.cut_id
            JOIN ops.task_result t ON t.task_id=ct.origin_task_id
            CROSS JOIN LATERAL jsonb_array_elements(t.body->'contribution_operations') op
            WHERE cr.run_id=:run AND op->'contextual_enrichment' ? 'neighborhood'
            """), {"run": args.run},
        ).one()
        target = next(
            edge["target_id"]
            for decision in report["relationship_decisions"]
            for edge in decision["selected_edges"]
        )
        params = NeighborhoodParams(task_id=task, target_id=target)
        (page,) = ContextualNeighborhoodQuery().rows(QueryContext(args.run, conn), params)
        expected = page.row.model_dump(mode="json")
    if expected["status"] != "completed" or not expected["witnessed_relationships"]:
        raise ValueError("retained neighborhood did not preserve its witnessed relation")
    actual, _ = ci(
        "query", "contextual_neighborhood", "--run", str(args.run), "--project", PROJECT,
        "--param", f"task_id={task}", "--param", f"target_id={target}", "--json",
    )
    if actual["rows"] != [expected]:
        raise ValueError("CLI and Reader neighborhoods differ")
    if asyncio.run(fresh_mcp(dict(run_id=args.run, cut_id=cut, **params.model_dump()))) != expected:
        raise ValueError("MCP and Reader neighborhoods differ")
    _, stderr = ci(
        "review", "export", "-", "--exact-closure", "--json",
        stdin=json.dumps(dict(selections=[dict(run_id=args.run, selected_task_id=task)])),
    )
    (identifier,) = re.findall(r"Review ([a-f0-9]{32}) · published", stderr)
    ci("review", "verify", f"build/ci/{identifier}/bundle", "--json")
    print(json.dumps(dict(
        run=args.run, cut=cut, task=task, target=target,
        neighbor_edges=len(report["neighborhood"]["edges"]), selected_neighbors=len(expected["neighbors"]),
        witnessed=len(expected["witnessed_relationships"]), bundle=identifier,
    )))


if __name__ == "__main__":
    main()
