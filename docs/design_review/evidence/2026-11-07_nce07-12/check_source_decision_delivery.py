"""Trace the recovered Table 6.1 caption from exact artifact source to retained witness."""

import argparse
import asyncio
import json
import re
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import text

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contextual_navigation import (
    SourceDecisionRequest,
    capture_source_decision,
    source_decision_from_capture,
)
from corpus_structure.settings import Settings
from check_neighborhood_delivery import CLI, PROJECT, ci

async def fresh_mcp(request):
    transport = StdioTransport(command=CLI, args=["mcp", "serve", "--semantic-run", str(request["run_id"])])
    async with Client(transport, timeout=180) as client:
        result = await client.call_tool("source_decision_diagnosis", {"request": request})
        return result.structured_content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    saved = json.loads(args.receipt.read_text())
    run = saved["selected"]["run_id"]
    cut = saved["selected"]["cut_id"]
    with (
        open_runtime_engine(Settings(), "nce-table-reference-diagnosis", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        task, product = conn.execute(
            text("""
            SELECT ct.task_id,r.body->'structural_product'->'artifact_identity'
            FROM ops.completed_result cr JOIN ops.cut_task ct ON ct.cut_id=cr.cut_id
            JOIN ops.task_result r ON r.task_id=ct.origin_task_id
            WHERE cr.run_id=:run AND cr.cut_id=:cut AND r.body->'structural_product' ? 'artifact_identity'
            """),
            {"run": run, "cut": cut},
        ).one()
        endpoints = {
            row["artifact"]["occurrence_role"]: row["contribution_id"]
            for row in product["records"]
            if row["artifact"]["artifact_kind"] == "table"
            and row["artifact"]["controlled_code"] == "6.1"
        }
        request = SourceDecisionRequest(
            run_id=run, cut_id=cut, task_id=task,
            occurrence_id=endpoints["reference"], target_id=endpoints["caption"],
        )
        evidence = capture_source_decision(conn, request, cut)
        expected = source_decision_from_capture(request, evidence).model_dump(mode="json")
    if not any(d["kind"] == "directed_artifact_nomination" for d in expected["decisions"]):
        raise ValueError("Table 6.1 diagnosis omitted the exact retained reference witness")
    actual, _ = ci(
        "query", "source_decision_diagnosis", "--run", str(run), "--project", PROJECT,
        "--param", f"task_id={task}", "--param", f"occurrence_id={request.occurrence_id}",
        "--param", f"target_id={request.target_id}", "--json",
    )
    if actual["rows"] != [expected] or asyncio.run(fresh_mcp(request.model_dump())) != expected:
        raise ValueError("Table 6.1 diagnosis transport differs from Reader")
    selection = saved["delivery"]["detached"]["selection"]
    selection["structural_selections"][0]["selected_task_id"] = task
    selection["source_decision_selections"] = [request.model_dump()]
    _, stderr = ci("review", "export", "-", "--exact-closure", "--json", stdin=json.dumps(selection))
    (identifier,) = re.findall(r"Review ([a-f0-9]{32}) · published", stderr)
    ci("review", "verify", f"build/ci/{identifier}/bundle", "--json")
    print(json.dumps(dict(run=run, cut=cut, task=task, bundle=identifier, outcome="passed")))


if __name__ == "__main__":
    main()
