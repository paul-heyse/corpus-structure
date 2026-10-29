"""FastMCP 4.1.3: how tool exceptions surface through built-in and custom middleware.

In-process `Client`; no network, no database. Questions:
1. A tool raising a domain refusal with no middleware: what does the client receive?
2. With the built-in `ErrorHandlingMiddleware()` (defaults): is it still an `isError` tool result or
   a protocol error?
3. With a small custom `on_call_tool` middleware mapping the wrapped cause to `ToolError(str(cause))`.
4. Does `ResponseLimitingMiddleware()` (tools=None) remove `outputSchema` from listings, and does a
   truncated response keep `structuredContent`?
"""

from __future__ import annotations

import asyncio
import json

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from pydantic import BaseModel


class Refused(ValueError):
    """Stands in for a domain refusal (several of the real ones subclass ValueError/RuntimeError)."""


class Page(BaseModel):
    text: str


class RefusalMapping(Middleware):
    REFUSALS = (Refused,)

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            return await call_next(context)
        except ToolError as error:
            cause = error.__cause__
            if isinstance(cause, self.REFUSALS):
                raise ToolError(str(cause)) from None
            raise


def build(middleware: list[Middleware]) -> FastMCP:
    mcp = FastMCP("probe", middleware=middleware)

    @mcp.tool
    def refuse() -> Page:
        raise Refused("task is not leased by this session")

    @mcp.tool
    def big() -> Page:
        return Page(text="x" * 5000)

    return mcp


async def call(mcp: FastMCP, name: str) -> dict[str, object]:
    async with Client(mcp) as client:
        try:
            result = await client.call_tool(name, {}, raise_on_error=False)
            text = [getattr(b, "text", "") for b in result.content]
            return {
                "is_error": result.is_error,
                "text": [t[:80] for t in text],
                "structured": result.structured_content is not None,
            }
        except Exception as error:
            return {"raised": type(error).__name__, "message": str(error)[:120]}


async def schemas(mcp: FastMCP) -> dict[str, bool]:
    async with Client(mcp) as client:
        return {t.name: t.output_schema is not None for t in await client.list_tools()}


async def main() -> dict[str, object]:
    return {
        "no_middleware": await call(build([]), "refuse"),
        "error_handling_default": await call(build([ErrorHandlingMiddleware()]), "refuse"),
        "custom_refusal_mapping": await call(build([RefusalMapping()]), "refuse"),
        "list_output_schema_without_limit": await schemas(build([])),
        "list_output_schema_with_limit": await schemas(build([ResponseLimitingMiddleware(max_size=1000)])),
        "list_output_schema_with_limit_scoped": await schemas(
            build([ResponseLimitingMiddleware(max_size=1000, tools=["big"])])
        ),
        "big_under_limit": await call(build([ResponseLimitingMiddleware(max_size=1000)]), "big"),
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(main()), indent=2, default=str))
