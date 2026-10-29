"""Which thread runs a FastMCP 4.1.3 tool body, and does a SIGALRM deadline work there?

Pure Python, in-process `fastmcp.Client` (no network, no database). Uses the repository's own
math-grammar deadline (`grammar.deadline`, `grammar.require_main_thread`) so the result speaks to
the actual constraint, not a re-implementation.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time

import fastmcp
from fastmcp import Client, FastMCP

from corpus_structure.methods.math import grammar

mcp = FastMCP("probe")


def _where() -> dict[str, object]:
    return {
        "thread": threading.current_thread().name,
        "is_main": threading.current_thread() is threading.main_thread(),
    }


def _deadline_outcome() -> str:
    try:
        with grammar.deadline(0.2):
            end = time.monotonic() + 5.0
            while time.monotonic() < end:  # busy pure-Python work, interruptible between bytecodes
                pass
        return "not_expired"
    except grammar.OffMainThread:
        return "OffMainThread"
    except grammar.Expired:
        return "Expired"


@mcp.tool
def sync_default() -> dict[str, object]:
    return {**_where(), "deadline": _deadline_outcome()}


@mcp.tool(run_in_thread=False)
def sync_inline() -> dict[str, object]:
    return {**_where(), "deadline": _deadline_outcome()}


@mcp.tool
async def async_tool() -> dict[str, object]:
    return {**_where(), "deadline": _deadline_outcome()}


def inline_with_timeout_registration() -> str:
    try:
        FastMCP("x").tool(run_in_thread=False, timeout=1.0)(lambda: 1)
        return "accepted"
    except Exception as error:  # documented: rejected at registration
        return f"rejected: {type(error).__name__}"


async def main() -> dict[str, object]:
    out: dict[str, object] = {
        "fastmcp": fastmcp.__version__,
        "loop_thread": _where(),
    }
    async with Client(mcp) as client:
        for name in ("sync_default", "sync_inline", "async_tool"):
            result = await client.call_tool(name, {})
            out[name] = result.data if result.data is not None else result.structured_content
    out["inline_plus_timeout"] = inline_with_timeout_registration()
    return out


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), indent=2, default=str))
