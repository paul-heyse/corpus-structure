"""Check actual CLI and fresh stdio MCP against retained run28; no model execution."""

import asyncio
import json
import subprocess
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def main():
    cli = subprocess.run(
        ["uv", "run", "ci", "contributions", "list", "--run", "28", "--limit", "2", "--json"],
        check=True, capture_output=True, text=True,
    )
    expected = json.loads(cli.stdout)
    async with Client(StdioTransport(command="uv", args=[
        "run", "ci", "mcp", "serve", "--semantic-run", "28",
    ])) as client:
        result = await client.call_tool("contributions", {"request": {"run_id": 28, "limit": 2}})
        assert not result.is_error
        actual = result.structured_content
        assert actual is not None
        for key in ("items", "inventory_counts", "selection", "cut_id", "standing",
                    "assessment", "scientific_support", "source_coverage", "next_cursor"):
            assert actual[key] == expected[key], key
        following = await client.call_tool("contributions", {"request": {
            "run_id": 28, "limit": 2, "cursor": actual["next_cursor"],
        }})
        assert not following.is_error and following.structured_content is not None
        assert all(item["population"] == "operation" for item in following.structured_content["items"])
        changed = await client.call_tool("contributions", {"request": {
            "run_id": 28, "kind": "occurrence", "cursor": actual["next_cursor"],
        }}, raise_on_error=False)
        assert changed.is_error
    report = dict(outcome="passed", scope="retained private contribution CLI/external stdio MCP",
                  run=28, cut=33, inventory_counts=expected["inventory_counts"],
                  controls=["CLI/MCP agreement", "continuation", "changed selection refusal"],
                  public_admission="not_run", provider_execution=False)
    target = Path(__file__).with_name("raw") / "contribution-transport-001.json"
    with target.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
