"""P1: FastMCP 4.1.3 tool contract as D8 §2.1 needs it (in-process Client, no network).

Questions:
  a. What do a strict Pydantic input parameter and a loose ``dict`` parameter (with an
     advertised schema via pydantic ``WithJsonSchema``) do with a batch containing one bad item?
  b. Does a Pydantic return type produce ``outputSchema`` and ``structuredContent``, and what
     text block accompanies it?
  c. Does ``ToolResult`` let a packet tool return plain text plus small structured metadata?
  d. Is the lifespan entered once per server even when two ``Client(mcp)`` sessions connect?
  e. Do sync tools run off the event loop thread (so shared sync application functions work)?

Run (scratch venv holding fastmcp==4.1.3; see README):
    $VENV/bin/python -I probes/p1_fastmcp_contract.py
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, WithJsonSchema

from fastmcp import Client, Context, FastMCP
from fastmcp.server.lifespan import lifespan
from fastmcp.tools import ToolResult

LIFESPAN_ENTRIES = 0
LOOP_THREAD: list[int] = []


class Claim(BaseModel):
    local_ref: str
    predicate: Literal["has_parameter", "defined_as"]
    subject: str


class Batch(BaseModel):
    unit_ref: str
    claims: list[Claim]


class ItemError(BaseModel):
    path: str
    message: str


class SubmissionResult(BaseModel):
    accepted: int
    rejected: list[ItemError]
    task_open: bool = Field(description="True when one corrected resubmission is allowed")


# The advertised schema the agent would see; validation inside the tool decides per item.
# Observed on the first run: WithJsonSchema(Batch.model_json_schema()) -- a schema carrying
# "$defs"/"$ref" -- fails at registration with KeyError '#/$defs/Claim' (pydantic 2.14.1 ref
# accounting). Inlining the refs first avoids it.
def _inline(schema: dict) -> dict:
    defs = schema.get("$defs", {})

    def walk(x: Any) -> Any:
        if isinstance(x, dict):
            if "$ref" in x:
                return walk(defs[x["$ref"].rsplit("/", 1)[1]])
            return {k: walk(v) for k, v in x.items() if k != "$defs"}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x

    return walk(schema)


BATCH_SCHEMA = _inline(Batch.model_json_schema())


@lifespan
async def pool_lifespan(server):
    global LIFESPAN_ENTRIES
    LIFESPAN_ENTRIES += 1
    LOOP_THREAD.append(threading.get_ident())
    yield {"pool": f"pool#{LIFESPAN_ENTRIES}"}


mcp = FastMCP("probe", lifespan=pool_lifespan)


@mcp.tool
def propose_strict(task_id: str, batch: Batch) -> SubmissionResult:
    """Strict: FastMCP validates ``batch`` before the body runs."""
    return SubmissionResult(accepted=len(batch.claims), rejected=[], task_open=False)


@mcp.tool
def propose_claims(
    task_id: str,
    batch: Annotated[dict[str, Any], WithJsonSchema(BATCH_SCHEMA)],
    ctx: Context,
) -> SubmissionResult:
    """Loose: the body validates item by item and returns every error at once."""
    accepted, rejected = 0, []
    for i, raw in enumerate(batch.get("claims", [])):
        try:
            Claim.model_validate(raw)
            accepted += 1
        except Exception as e:  # pydantic.ValidationError
            for err in e.errors():  # type: ignore[attr-defined]
                loc = ".".join(str(x) for x in err["loc"])
                rejected.append(ItemError(path=f"claims[{i}].{loc}", message=err["msg"]))
    assert ctx.lifespan_context["pool"].startswith("pool#")
    return SubmissionResult(accepted=accepted, rejected=rejected, task_open=bool(rejected))


@mcp.tool
def read_unit(task_id: str, part: int = 0) -> ToolResult:
    """Packet as plain text, with small structured metadata."""
    text = "Suppose X is normal with mean mu ...\n[c1] Let a, b be real."
    return ToolResult(content=text, structured_content={"task_id": task_id, "part": part, "parts": 1})


@mcp.tool
def which_thread() -> dict:
    return {"tool_thread": threading.get_ident(), "loop_thread": LOOP_THREAD[0]}


GOOD = {"local_ref": "C1", "predicate": "has_parameter", "subject": "N"}
BAD = {"local_ref": "C2", "predicate": "has_parametr", "subject": "N"}


def dump(obj: Any) -> Any:
    return obj.model_dump(by_alias=True, exclude_none=True) if hasattr(obj, "model_dump") else obj


async def main() -> None:
    out: dict[str, Any] = {}
    async with Client(mcp) as c:
        tools = {t.name: dump(t) for t in await c.list_tools()}
        out["schemas"] = {
            n: {k: tools[n].get(k) is not None for k in ("inputSchema", "outputSchema")} for n in tools
        }
        out["propose_claims.inputSchema.batch"] = tools["propose_claims"]["inputSchema"]["properties"]["batch"]
        out["propose_claims.outputSchema"] = tools["propose_claims"].get("outputSchema")

        r = await c.call_tool("propose_strict", {"task_id": "t1", "batch": {"unit_ref": "u", "claims": [GOOD, BAD]}},
                              raise_on_error=False)
        out["strict_bad_item"] = {"is_error": r.is_error, "content": [dump(x) for x in r.content],
                                  "structured": r.structured_content}

        r = await c.call_tool("propose_claims", {"task_id": "t1", "batch": {"unit_ref": "u", "claims": [GOOD, BAD]}})
        out["loose_bad_item"] = {"is_error": r.is_error, "data_type": type(r.data).__name__,
                                 "structured": r.structured_content, "content": [dump(x) for x in r.content]}

        r = await c.call_tool("read_unit", {"task_id": "t1"})
        out["read_unit"] = {"content": [dump(x) for x in r.content], "structured": r.structured_content}

        out["threads"] = (await c.call_tool("which_thread", {})).structured_content
    async with Client(mcp) as c2:
        await c2.call_tool("which_thread", {})
    out["lifespan_entries_after_two_clients"] = LIFESPAN_ENTRIES
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    asyncio.run(main())
