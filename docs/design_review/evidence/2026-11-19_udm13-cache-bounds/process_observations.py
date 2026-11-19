"""Observe the fresh worker and the retained MCP owner without starting providers."""

from __future__ import annotations

import asyncio
import json
from multiprocessing import get_context
from time import perf_counter

from corpus_structure.caches import snapshot
from corpus_structure.model.compiled import model_request_scope, running_model


def spawned(queue):
    queue.put(snapshot(owner="spawned clean worker").model_dump(mode="json"))


async def mcp():
    from fastmcp import Client

    from corpus_structure.intervene.semantic_server import build_retained_reader_server

    async with Client(build_retained_reader_server()) as client:
        first = await client.call_tool("inspect_cache", {})
        second = await client.call_tool("inspect_cache", {})
    assert first.structured_content is not None and second.structured_content is not None
    assert first.structured_content["pid"] == second.structured_content["pid"]
    assert first.structured_content["started_at"] == second.structured_content["started_at"]
    return second.structured_content


if __name__ == "__main__":
    start = perf_counter()
    with model_request_scope():
        running_model().physical()
    compiled_seconds = perf_counter() - start
    context = get_context("spawn")
    queue = context.Queue()
    start = perf_counter()
    worker = context.Process(target=spawned, args=(queue,))
    worker.start()
    observation = queue.get(timeout=45)
    worker.join(timeout=45)
    assert worker.exitcode == 0
    start_seconds = perf_counter() - start
    print(
        json.dumps(
            dict(
                model_compile_seconds=compiled_seconds,
                worker_start_seconds=start_seconds,
                worker=observation,
                mcp=asyncio.run(mcp()),
            )
        )
    )
