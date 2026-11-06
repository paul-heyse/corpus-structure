"""Fresh stdio MCP handshake and actual completed-cut structural delivery."""
from pathlib import Path
import argparse
import json
import sys

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent


def retain(path, data):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(data) + b"\n")


async def check(args):
    folder = HERE / args.attempt
    folder.mkdir(exist_ok=False)
    root = HERE.parents[4]
    transport = StdioTransport(
        command=str(Path(sys.executable).with_name("ci")),
        args=["mcp", "serve", "--semantic-run", str(args.run)],
        cwd=str(root), log_file=folder / "server.log",
    )
    try:
        async with Client(transport, timeout=180) as client:
            tools = await client.list_tools()
            retain(folder / "tools.json", [tool.model_dump(mode="json") for tool in tools])
            result = await client.call_tool("structural_products", {"request": dict(
                run_id=args.run, kind=args.kind, max_bytes=8_000_000,
                include_publication=args.include_publication, include_support=args.include_support,
            )})
            if result.is_error or not isinstance(result.structured_content, dict):
                raise ValueError("Fresh MCP failed structural delivery")
            payload = result.structured_content
            retain(folder / "structural-products.json", payload)
            if payload["run_id"] != args.run or not payload["reports"]:
                raise ValueError("MCP completed-cut selection differs or is empty")
            if args.cli:
                expected = json.loads(args.cli.read_bytes())
                if canonical_bytes(payload) != canonical_bytes(expected):
                    raise ValueError("CLI and fresh MCP structural payloads differ")
            retain(folder / "result.json", dict(outcome="passed", run_id=args.run,
                cut_id=payload["cut_id"], release_id=payload["release_id"],
                reports=len(payload["reports"]), fresh_stdio_handshake=True,
                cli_exact_parity=bool(args.cli),
                scope="Actual completed-cut transport/read parity; no semantic correctness claim"))
    except BaseException as error:
        retain(folder / "failure.json", dict(outcome="failed", type=type(error).__name__, message=str(error)))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt")
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--kind", required=True)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--include-publication", action="store_true")
    parser.add_argument("--include-support", action="store_true")
    args = parser.parse_args()
    anyio.run(check, args)
