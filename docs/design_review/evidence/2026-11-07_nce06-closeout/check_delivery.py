"""Compare the exact witnessed relationship rows from installed CLI and fresh MCP."""

import json
import shutil
import sys

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.serve.contributions import ContributionPage


def selected_rows(page, populations):
    return [item for item in page.items if item["population"] in populations]


async def verify(wire, populations):
    cli = ContributionPage.model_validate_json(wire)
    command = shutil.which("ci")
    if command is None:
        raise ValueError("installed ci command is unavailable")
    transport = StdioTransport(command=command, args=["mcp", "serve", "--semantic-run", str(cli.run_id)])
    async with Client(transport, timeout=180) as client:
        response = await client.call_tool(
            "contributions",
            {"request": {"run_id": cli.run_id, **cli.selection, "limit": 1000, "page_bytes": 16_000_000}},
        )
    if response.is_error:
        raise ValueError("fresh MCP refused the installed CLI selection")
    mcp = ContributionPage.model_validate(response.structured_content)
    rows = selected_rows(cli, populations)
    if (
        not rows
        or (mcp.run_id, mcp.cut_id) != (cli.run_id, cli.cut_id)
        or selected_rows(mcp, populations) != rows
    ):
        raise ValueError("selected projection differs across CLI and MCP")
    print(json.dumps({"run_id": cli.run_id, "cut_id": cli.cut_id, "rows": len(rows)}))


if __name__ == "__main__":
    populations = {"contribution", "operation"} if sys.argv[1:] == ["--contextual"] else {"relationship"}
    anyio.run(verify, sys.stdin.buffer.read(), populations)
