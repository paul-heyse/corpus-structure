"""P2: FastMCP 4.1.3 over stdio, as Claude Code would launch it from .mcp.json.

Questions:
  a. Does a stray ``print()`` to stdout inside a tool break the JSON-RPC stream?
  b. Is ``ctx.session_id`` stable across calls of one client on stdio (could it identify a
     calling session or subagent)?
  c. Is the lifespan entered once per server process?

Run (scratch venv holding fastmcp==4.1.3):
    $VENV/bin/python -I probes/p2_fastmcp_stdio.py
The script re-launches itself with ``serve`` as the stdio server subprocess.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastmcp import Client, Context, FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.lifespan import lifespan


def serve() -> None:
    entries = {"n": 0}

    @lifespan
    async def ls(server):
        entries["n"] += 1
        yield {}

    mcp = FastMCP("probe-stdio", lifespan=ls)

    @mcp.tool
    def who(ctx: Context) -> dict:
        return {"session_id": ctx.session_id, "lifespan_entries": entries["n"]}

    @mcp.tool
    def noisy() -> str:
        print("stray stdout line from a library")  # what a careless dependency might do
        return "ok"

    @mcp.tool
    def noisy_stderr() -> str:
        print("diagnostic on stderr", file=sys.stderr)
        return "ok"

    mcp.run(show_banner=False)  # stdio is the default transport


async def drive() -> None:
    out: dict = {}
    transport = StdioTransport(command=sys.executable, args=["-I", str(Path(__file__).resolve()), "serve"])
    async with Client(transport) as c:
        a = (await c.call_tool("who", {})).structured_content
        b = (await c.call_tool("who", {})).structured_content
        out["session_id_stable_across_calls"] = a["session_id"] == b["session_id"]
        out["lifespan_entries"] = b["lifespan_entries"]
        out["stderr_print"] = (await c.call_tool("noisy_stderr", {})).data
        try:
            r = await asyncio.wait_for(c.call_tool("noisy", {}, raise_on_error=False), timeout=10)
            out["stdout_print"] = {"is_error": r.is_error, "data": r.data}
            after = await asyncio.wait_for(c.call_tool("who", {}), timeout=10)
            out["call_after_stdout_print"] = "ok" if after.structured_content else "no structured content"
        except Exception as e:  # noqa: BLE001
            out["stdout_print"] = f"{type(e).__name__}: {e}"
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1:] == ["serve"]:
        serve()
    else:
        asyncio.run(drive())
