"""Compare installed CLI and fresh MCP on one exact retained Reader selection."""

import json
import shutil
import sys

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.serve.contributions import ContributionPage
from corpus_structure.serve.structural_products import StructuralPage, StructuralRequest


async def read_mcp(run_id, tool, request):
    command = shutil.which("ci")
    if command is None:
        raise ValueError("installed ci command is unavailable")
    transport = StdioTransport(
        command=command, args=["mcp", "serve", "--semantic-run", str(run_id)]
    )
    async with Client(transport, timeout=180) as client:
        response = await client.call_tool(tool, {"request": request})
    if response.is_error or not isinstance(response.structured_content, dict):
        raise ValueError("fresh MCP did not deliver the exact selection")
    return response.structured_content


async def compare(kind, wire):
    if kind == "contributions":
        page = ContributionPage.model_validate_json(wire)
        request = {"run_id": page.run_id, **page.selection}
        fresh = ContributionPage.model_validate(
            await read_mcp(page.run_id, "contributions", request)
        )
        rows = tuple(item["row"] for item in page.items if item["population"] == "contribution")
        other = tuple(item["row"] for item in fresh.items if item["population"] == "contribution")
        if not rows or rows != other or (fresh.run_id, fresh.cut_id) != (page.run_id, page.cut_id):
            raise ValueError("MCP and installed CLI contribution projections differ")
        summary = {"contributions": len(rows)}
    else:
        page = StructuralPage.model_validate_json(wire)
        request = StructuralRequest(
            run_id=page.run_id,
            cut_id=page.cut_id,
            kind=kind,
            max_bytes=8_000_000,
        )
        fresh = await read_mcp(page.run_id, "structural_products", request.model_dump(mode="json"))
        if len(page.reports) != 1 or StructuralPage.model_validate(fresh) != page:
            raise ValueError("MCP and installed CLI structural projections differ")
        summary = {"products": [report.product_id for report in page.reports]}
    print(
        json.dumps(
            {
                "outcome": "passed",
                "kind": kind,
                "run_id": page.run_id,
                "cut_id": page.cut_id,
                **summary,
            }
        )
    )


def main():
    (kind,) = sys.argv[1:]
    anyio.run(compare, kind, sys.stdin.buffer.read())


if __name__ == "__main__":
    main()
