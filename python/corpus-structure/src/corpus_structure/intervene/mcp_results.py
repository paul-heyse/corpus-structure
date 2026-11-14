"""Bound complete MCP delivery, including SDK metadata, in one shared owner."""

from __future__ import annotations

from fastmcp import __version__ as FASTMCP_VERSION
from fastmcp.tools import ToolResult
from mcp.types import CallToolResult, Implementation
from pydantic import BaseModel

MCP_SERVER_NAME = "corpus-structure"


def _stamp_mcp_result(wire: CallToolResult) -> CallToolResult:
    """Include SDK delivery metadata before admitting any bounded tool result."""
    meta = dict(wire.meta or {})
    key = "io.modelcontextprotocol/serverInfo"
    if meta.get(key) is None:
        meta[key] = Implementation(name=MCP_SERVER_NAME, version=FASTMCP_VERSION).model_dump(
            mode="json", by_alias=True, exclude_none=True
        )
    return wire.model_copy(update={"meta": meta})


def bounded_mcp_result(
    value: BaseModel, max_bytes: int, *, presentation: str | None = None
) -> ToolResult:
    """Admit the actual full text-plus-structured result, retaining its exact wire form."""
    from corpus_structure.semantic.query import ReadLimit

    encoded = ToolResult(
        content=presentation if presentation is not None else value,
        structured_content=value.model_dump(mode="json"),
    )
    # The pinned SDK stamps this identity after dispatch on modern protocols. Author
    # that same SDK-shaped metadata here so admission includes the final stamp, and
    # the runner preserves it. Legacy protocols can carry this optional metadata;
    # their serializer may omit resultType, so this complete-result bound remains safe.
    wire = _stamp_mcp_result(
        CallToolResult(
            content=encoded.content,
            structured_content=encoded.structured_content,
        )
    )
    if len(wire.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")) > max_bytes:
        raise ReadLimit("complete MCP response exceeds byte budget", reason="oversized_item")
    return ToolResult.from_mcp_result(wire)


