"""Compare installed gap CLI and fresh MCP with the exact Reader result."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.structural_gaps import GapRequest, serve_structural_gap
from corpus_structure.settings import Settings


async def fresh_mcp(request):
    cli = str(Path(sys.executable).with_name("ci"))
    transport = StdioTransport(
        command=cli, args=["mcp", "serve", "--semantic-run", str(request.run_id)]
    )
    async with Client(transport, timeout=120) as client:
        response = await client.call_tool(
            "structural_gap",
            {"request": request.model_dump(mode="json", exclude_none=True)},
        )
    return response.structured_content


def main():
    settings = Settings()
    controls = (
        ("unresolved_binding", 207, 287, 1190),
        ("unknown_applicability_premise", 130, 164, 319),
        ("unconnected_supported_comparison", 197, 263, 1129),
    )
    for report, run, cut, task in controls:
        request = GapRequest(run_id=run, cut_id=cut, task_id=task, report=report, limit=2)
        with (
            open_runtime_engine(settings, "nce-structural-gap-reader", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            expected = serve_structural_gap(conn, request).model_dump(mode="json")
        installed = subprocess.run(
            [str(Path(sys.executable).with_name("ci")), "structure", "gap", report,
             "--run", str(run), "--cut", str(cut), "--task", str(task), "--limit", "2", "--json"],
            capture_output=True, text=True, check=True,
        )
        if json.loads(installed.stdout) != expected or asyncio.run(fresh_mcp(request)) != expected:
            raise ValueError("ordinary gap transports differ from the exact selected Reader")
        print(json.dumps(dict(report=report, run=run, cut=cut, status=expected["status"])))


if __name__ == "__main__":
    main()
