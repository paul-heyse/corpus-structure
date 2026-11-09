"""Compare the exact retained native formula through CLI and a fresh MCP process."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def verify(cli_result):
    request = dict(cli_result["selection"], max_bytes=8 * 1024 * 1024)
    process = StdioServerParameters(
        command=str(Path(sys.executable).with_name("ci")),
        args=["mcp", "serve", "--semantic-run", str(request["run_id"])],
    )
    async with (
        stdio_client(process) as (reader, writer),
        ClientSession(reader, writer) as session,
    ):
        await session.initialize()
        reply = await session.call_tool("inspect_source", {"request": request})
        if reply.is_error or reply.structured_content is None:
            raise RuntimeError(str(reply.content)[:2000])
        result = reply.structured_content
        if result != cli_result:
            raise ValueError(
                f"source Reader/CLI/MCP disagree on: {sorted(set(result) ^ set(cli_result))}"
            )
        bad_request = dict(request, content_digest="f" * 64)
        refused = await session.call_tool("inspect_source", {"request": bad_request})
        if not refused.is_error:
            raise ValueError("changed native product digest was not refused")
        return dict(
            selection=cli_result["selection"],
            release_id=result["release_id"],
            outcome=result["outcome"],
            row_count=len(result["rows"]),
            wrong_digest_refused=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cli_result", type=Path)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(verify(json.loads(args.cli_result.read_bytes())))))
