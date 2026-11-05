"""Actual CLI/external MCP parity over completed mixed public/private contributions."""
import argparse
import asyncio
import json
import subprocess
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def same_business_page(actual, expected):
    # Each independently owned read receives a new capture resource identity.
    # Release/realization/revision/cut, selection, rows and all standing stay exact.
    def normalized(page):
        assert page["binding"]["capture_id"]
        return dict(page, binding={key: value for key, value in page["binding"].items()
                                   if key != "capture_id"})
    return normalized(actual) == normalized(expected)


def cli(run, *, cursor=None, limit=1000):
    command = ["uv", "run", "ci", "contributions", "list", "--run", str(run),
               "--include-details", "--include-publication", "--include-support", "--limit", str(limit),
               "--page-bytes", "8000000", "--max-bytes", "32000000", "--json"]
    if cursor:
        command.extend(("--cursor", cursor))
    return json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout)


async def main(args):
    target = Path(__file__).with_name("raw") / (args.receipt + ".json")
    if target.exists():
        raise FileExistsError(target)
    base = dict(run_id=args.run, include_details=True, include_publication=True, include_support=True,
                limit=1000, page_bytes=8_000_000, max_bytes=32_000_000)
    expected = cli(args.run)
    async with Client(StdioTransport(command="uv", args=[
        "run", "ci", "mcp", "serve", "--semantic-run", str(args.run),
    ])) as client:
        response = await client.call_tool("contributions", {"request": base})
        assert not response.is_error and response.structured_content is not None
        actual = response.structured_content
        for suffix, value in (("-cli.json", expected), ("-mcp.json", actual)):
            with target.with_name(target.stem + suffix).open("x") as stream:
                json.dump(value, stream, indent=2)
                stream.write("\n")
        assert same_business_page(actual, expected)
        counts = actual["inventory_counts"]
        assert counts["admitted_source_claims"] > 0
        assert counts["admitted_semantic_claims"] > 0
        assert actual["standing"] == "mixed_private_and_local_semantic_claims"
        assert actual["scientific_support"] == "unmodeled"
        assert actual["source_coverage"] == "not_established_by_contribution_inventory"
        assert actual["population_paging_complete"]
        small = await client.call_tool("contributions", {"request": dict(base, limit=2)})
        assert not small.is_error and small.structured_content is not None
        cursor = small.structured_content["next_cursor"]
        assert cursor
        following = await client.call_tool("contributions", {"request": dict(base, limit=2, cursor=cursor)})
        assert not following.is_error
        assert same_business_page(following.structured_content, cli(args.run, cursor=cursor, limit=2))
        changed = await client.call_tool("contributions", {"request": dict(base, cursor=cursor, include_support=False)}, raise_on_error=False)
        assert changed.is_error
        limited = await client.call_tool("contributions", {"request": dict(base, max_bytes=1)}, raise_on_error=False)
        assert limited.is_error
        private = await client.call_tool("contributions", {"request": dict(base, include_publication=False, include_support=False)})
        assert not private.is_error and private.structured_content is not None
        assert private.structured_content["standing"] == "retained_private"
        assert private.structured_content["inventory_counts"]["admitted_semantic_claims"] == 0
    report = dict(outcome="passed", run_id=args.run, cut_id=actual["cut_id"],
                  inventory_counts=counts, standing=actual["standing"],
                  controls=["actual CLI/MCP exact parity", "public source and semantic support", "private facet separation",
                            "continuation", "changed facet refusal", "byte refusal"],
                  parity="Exact semantic page equality; independently owned capture IDs retained separately",
                  cli_capture_id=expected["binding"]["capture_id"], mcp_capture_id=actual["binding"]["capture_id"],
                  provider_execution=False, source_coverage=actual["source_coverage"], scientific_support="unmodeled")
    with target.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--receipt", required=True)
    asyncio.run(main(parser.parse_args()))
