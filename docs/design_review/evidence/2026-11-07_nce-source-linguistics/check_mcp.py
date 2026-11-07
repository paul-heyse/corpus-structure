"""Compare one exact scoped contribution through installed CLI and fresh MCP."""

import argparse
import json
import shutil
from pathlib import Path

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes


async def check(cli_page: Path, destination: Path):
    page = json.loads(cli_page.read_bytes())
    row = next(
        item["row"] for item in page["items"]
        if item["population"] == "contribution"
        and item["row"]["semantic_type"] == "structural.predicate_frame"
    )
    ci = shutil.which("ci")
    if ci is None:
        raise ValueError("the installed ci executable is unavailable")
    transport = StdioTransport(
        command=ci,
        args=["mcp", "serve", "--semantic-run", str(page["run_id"])],
        cwd=str(Path.cwd()),
        log_file=destination.with_suffix(".server.log"),
    )
    request = {
        "run_id": page["run_id"],
        "source_view_id": row["source_view_id"],
        "method": "structure.scoped_relations",
        "contribution_id": row["contribution_id"],
        "include_details": True,
        "include_interpretation": True,
    }
    async with Client(transport, timeout=180) as client:
        result = await client.call_tool("contributions", {"request": request})
    if result.is_error or not isinstance(result.structured_content, dict):
        raise ValueError("MCP did not deliver a scoped contribution page")
    answer = result.structured_content
    (delivered,) = tuple(
        item["row"] for item in answer["items"] if item["population"] == "contribution"
    )
    if delivered != row or answer["cut_id"] != page["cut_id"]:
        raise ValueError("ordinary CLI and MCP disagree on the exact retained frame")
    destination.write_bytes(canonical_bytes({
        "outcome": "passed",
        "run_id": answer["run_id"],
        "cut_id": answer["cut_id"],
        "contribution_id": delivered["contribution_id"],
        "source_view_id": delivered["source_view_id"],
    }) + b"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cli_page", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    anyio.run(check, args.cli_page, args.destination)
