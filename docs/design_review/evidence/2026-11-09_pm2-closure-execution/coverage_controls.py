"""Compare native run worklist settlement with ordinary Reader, CLI and fresh MCP."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import (
    ContributionPage,
    ContributionRequest,
    serve_contributions,
)
from corpus_structure.settings import Settings

COMMAND = str(Path(sys.executable).with_name("ci"))
ENV = os.environ | {"CORPUS_RUNTIME__DEFAULT_PROJECT": "nce-grinstead-snell-full-book"}


async def mcp(request):
    with TemporaryDirectory(prefix="pm2-coverage-read-") as temp:
        transport = StdioTransport(
            command=COMMAND,
            args=["mcp", "serve", "--semantic-run", str(request.run_id)],
            env=ENV,
            keep_alive=False,
            log_file=Path(temp) / "stdio.log",
        )
        async with Client(transport, timeout=120) as client:
            reply = await client.call_tool(
                "contributions", {"request": request.model_dump(mode="json")}
            )
            if reply.is_error:
                raise RuntimeError(reply.content)
            return ContributionPage.model_validate(reply.structured_content)


def comparable(page):
    result = page.model_dump(mode="json")
    result["binding"].pop("capture_id")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("view", type=int)
    args = parser.parse_args()
    native = json.loads(args.receipt.read_bytes())
    request = ContributionRequest(
        run_id=native["run_id"],
        source_view_id=args.view,
        include_scope_coverage=True,
        limit=100,
        page_bytes=8_000_000,
    )
    with (
        open_runtime_engine(Settings(), "pm2-coverage-controls", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        reader = serve_contributions(conn, request)
    by_cli = ContributionPage.model_validate_json(
        subprocess.run(
            [
                COMMAND,
                "contributions",
                "list",
                "--run",
                str(request.run_id),
                "--source-view",
                str(args.view),
                "--include-scope-coverage",
                "--limit",
                "100",
                "--page-bytes",
                "8000000",
                "--json",
            ],
            env=ENV,
            capture_output=True,
            check=True,
            timeout=180,
        ).stdout
    )
    assert comparable(reader) == comparable(by_cli) == comparable(anyio.run(mcp, request))
    expected = [item for item in native["scope_coverage"] if item["source_view_id"] == args.view]
    actual = [item["row"] for item in reader.items if item["population"] == "scope_coverage"]
    assert expected and actual == expected
    assert reader.cut_id == native["cut_id"]
    print(
        canonical_bytes(
            {
                "run": reader.run_id,
                "cut": reader.cut_id,
                "view": args.view,
                "coverage": actual,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
