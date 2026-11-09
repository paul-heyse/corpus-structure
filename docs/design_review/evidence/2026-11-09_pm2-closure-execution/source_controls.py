"""Verify retained-source preservation through Reader, CLI and fresh MCP."""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.native_source import (
    NativeSourceRequest,
    NativeSourceResponse,
    inspect_native_source,
)
from corpus_structure.settings import Settings

RUN = 478
COMMAND = str(Path(sys.executable).with_name("ci"))
ENV = os.environ | {"CORPUS_RUNTIME__DEFAULT_PROJECT": "nce-grinstead-snell-full-book"}
PIN = {
    "run_id": RUN,
    "task_id": 1627,
    "product_key": "integrated",
    "content_digest": "35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb",
    "max_bytes": 8_388_608,
}
SCOPES = {
    416: {"view": "formula", "pointer": "#/texts/2341", "section_pointer": "#/groups/617"},
    418: {"view": "formula", "pointer": "#/texts/2355", "section_pointer": "#/groups/618"},
    151: {"view": "manifest", "collection": "coverage"},
}


def command(request):
    args = [
        COMMAND,
        "source",
        "inspect",
        str(request.run_id),
        "--json",
        "--producing-task",
        str(request.task_id),
        "--product",
        request.product_key,
        "--native-digest",
        request.content_digest,
        "--native-view",
        request.view,
        "--max-bytes",
        str(request.max_bytes),
    ]
    for flag, value in (
        ("--pointer", request.pointer),
        ("--section", request.section_pointer),
        ("--collection", request.collection),
    ):
        if value is not None:
            args.extend((flag, value))
    return NativeSourceResponse.model_validate_json(
        subprocess.run(args, env=ENV, check=True, capture_output=True, timeout=180).stdout
    )


async def mcp(requests):
    with TemporaryDirectory(prefix="pm2-source-read-") as temp:
        transport = StdioTransport(
            command=COMMAND,
            args=["mcp", "serve", "--semantic-run", str(RUN)],
            env=ENV,
            keep_alive=False,
            log_file=Path(temp) / "stdio.log",
        )
        async with Client(transport, timeout=120) as client:
            result = {}
            for page, request in requests.items():
                reply = await client.call_tool(
                    "inspect_source", {"request": request.model_dump(mode="json")}
                )
                if reply.is_error:
                    raise RuntimeError(reply.content)
                result[page] = NativeSourceResponse.model_validate(reply.structured_content)
            return result


def formula_content(response):
    # Current interpretation custody identifies the selected run and view. Compare
    # source fields, location, and all other meaning under the unchanged native pin.
    rows = response.model_dump(mode="json")["rows"]
    for row in rows:
        row["interpretation"].pop("run_id")
        for state in row["interpretation"]["results"]:
            state.pop("source_view_id")
    return rows


def main():
    requests = {
        page: NativeSourceRequest.model_validate(PIN | scope) for page, scope in SCOPES.items()
    }
    with (
        ThreadPoolExecutor(max_workers=4) as pool,
        open_runtime_engine(Settings(), "pm2-source-controls", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        cli = {page: pool.submit(command, req) for page, req in requests.items()}
        remote = pool.submit(anyio.run, mcp, requests)
        results = {}
        for page, request in requests.items():
            reader = inspect_native_source(conn, request)
            assert reader == cli[page].result() == remote.result()[page], page
            assert reader.outcome == "source_ready", page
            rows = reader.model_dump(mode="json")["rows"]
            if page == 151:
                coverage = [
                    row
                    for row in rows[0]["rows"]
                    if row["scope"] == "page:151" and row["family"] == "nemotron-pass-C"
                ]
                assert len(coverage) == 1 and coverage[0]["outcome"] == "partial"
                results[page] = {
                    "coverage": coverage[0],
                    "whole_manifest": reader.population_complete,
                }
            else:
                original = inspect_native_source(conn, request.model_copy(update={"run_id": 404}))
                assert formula_content(original) == formula_content(reader), page
                assert {region["page_no"] for region in rows[0]["regions"]} == {page}
                results[page] = {"pointer": request.pointer, "preserved": True}
    print(canonical_bytes({str(page): value for page, value in results.items()}).decode())


if __name__ == "__main__":
    main()
