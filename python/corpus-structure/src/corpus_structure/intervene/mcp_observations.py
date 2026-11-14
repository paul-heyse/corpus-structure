"""Request-scoped observation bindings for both current and sealed MCP readers."""

from __future__ import annotations

import secrets

from fastmcp.server.middleware import Middleware


class ObservationMiddleware(Middleware):
    """Bind/reset each actual request; FastMCP carries this context into sync tool threads."""

    def __init__(self, run_id: int | None = None):
        self.run_id = run_id

    async def on_call_tool(self, context, call_next):
        import os

        from corpus_structure.cli.observation_logging import (
            INVOCATION_ENV,
            PROVIDER_ENV,
            bound,
            capture,
            event,
            logger,
        )

        request = context.fastmcp_context
        request_id = str(request.request_id) if request is not None else secrets.token_hex(12)
        arguments = context.message.arguments or {}
        task_id = arguments.get("task_id", (arguments.get("claim") or {}).get("task_id"))
        bindings = {"request_id": request_id, "stage": context.message.name}
        if type(task_id) is int and task_id > 0:
            bindings["task_id"] = task_id
        endpoint = (
            request.lifespan_context.get("observation_writer") if request is not None else None
        )
        with (
            capture(
                endpoint,
                stream=None,
                invocation_id=os.environ.get(INVOCATION_ENV),
                provider_invocation=os.environ.get(PROVIDER_ENV),
                run_id=self.run_id,
            ),
            bound(**bindings),
        ):
            event("mcp_tool_started", "MCP tool started", tool=context.message.name)
            try:
                result = await call_next(context)
            except Exception as error:
                logger().error(
                    "MCP tool failed",
                    kind="mcp_tool_failed",
                    tool=context.message.name,
                    exc_info=(type(error), error, error.__traceback__),
                )
                raise
            else:
                event("mcp_tool_finished", "MCP tool finished", tool=context.message.name)
                return result
