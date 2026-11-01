"""Actual external stdio journey over caller-selected retained integrated PDF evidence."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
from hashlib import sha256
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError


async def exercise(selection: dict, database: str, root: Path, output: Path) -> None:
    # Run the installed application entry point without changing the shared environment.
    command = shutil.which("uv")
    if command is None:
        raise RuntimeError("uv is required for the actual application entry point")
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(".partial.json")
    server_log = output.with_suffix(".server.log")
    image_path = output.with_suffix(".render.png")
    raw_path = output.with_suffix(".raw-response.bin")
    for path in (output, partial, server_log, image_path, raw_path):
        if path.exists():
            raise FileExistsError(f"retain the existing journey: {path}")
    transport = StdioTransport(
        command=str(command),
        args=["run", "ci", "mcp", "serve", "--semantic-run", str(selection["run_id"])],
        cwd=str(root),
        keep_alive=False,
        env={
            "CORPUS_DATABASE__URL": database,
            "PYTHONPATH": str(root / "python/corpus-structure/src"),
        },
        log_file=server_log,
    )
    receipts = []

    def checkpoint() -> None:
        partial.write_text(
            json.dumps(
                {
                    "outcome": "partial",
                    "selection": selection,
                    "calls": receipts,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )

    checkpoint()
    pin = {
        key: selection[key]
        for key in ("run_id", "task_id", "product_key", "content_digest")
    }
    async with Client(transport, timeout=120, init_timeout=120) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert {
            "inspect_source",
            "render_source_region",
            "queue_status",
            "find",
        } <= tools.keys()
        receipts.append(
            {
                "operation": "list_tools",
                "tools": sorted(tools),
                "schemas": {
                    name: tools[name].inputSchema
                    for name in ("inspect_source", "render_source_region", "find")
                },
            }
        )
        checkpoint()
        found = await client.call_tool(
            "find",
            {
                "request": {
                    "run_id": selection["run_id"],
                    "text": "normal distribution",
                    "limit": 2,
                }
            },
            timeout=120,
        )
        value = found.structured_content
        assert value and value["rows"]
        assert all(
            row["selection"]["content_digest"] == selection["content_digest"]
            for row in value["rows"]
        )
        receipts.append({"operation": "find", "result": value})
        checkpoint()
        requests = [
            dict(pin, version=3, view="sections", limit=5),
            dict(pin, version=3, view="formula", pointer=selection["formula_pointer"]),
            dict(
                pin,
                version=3,
                view="cell",
                pointer=selection["table_pointer"],
                cell_index=selection["cell_index"],
            ),
            dict(pin, version=3, view="trace", pointer=selection["formula_pointer"]),
            dict(
                pin, version=3, view="companion", pointer=selection["formula_pointer"]
            ),
            dict(
                pin,
                version=3,
                view="trace",
                occurrence_id=selection["formula_occurrence_id"],
            ),
            dict(pin, version=3, view="manifest", collection="coverage", limit=5),
        ]
        for request in requests:
            response = await client.call_tool(
                "inspect_source", {"request": request}, timeout=120
            )
            value = response.structured_content
            assert value is not None and value["outcome"] == "source_ready"
            assert value["selection"]["content_digest"] == selection["content_digest"]
            assert value["rows"], request
            receipts.append(
                {"operation": "inspect_source", "request": request, "result": value}
            )
            checkpoint()
        # Fetch every bounded artifact chunk and verify the actual retained failed-response bytes.
        request = dict(
            pin,
            version=3,
            view="artifact",
            artifact_digest=selection["artifact_digest"],
        )
        chunks = []
        while True:
            response = await client.call_tool(
                "inspect_source", {"request": request}, timeout=120
            )
            value = response.structured_content
            assert value is not None and len(value["rows"]) == 1
            row = value["rows"][0]
            content = base64.b64decode(row["data"], validate=True)
            assert len(content) == row["length"]
            chunks.append(content)
            receipts.append(
                {
                    "operation": "artifact_chunk",
                    "request": request,
                    "result": {k: v for k, v in row.items() if k != "data"},
                }
            )
            checkpoint()
            if value["next_cursor"] is None:
                break
            request = dict(request, cursor=value["next_cursor"])
        raw = b"".join(chunks)
        assert sha256(raw).hexdigest() == selection["artifact_digest"]
        raw_path.write_bytes(raw)
        image = await client.call_tool(
            "render_source_region",
            {
                "run_id": selection["run_id"],
                "source_view_id": selection["source_view_id"],
                "pointer": selection["formula_pointer"],
                "region_index": 0,
            },
            timeout=180,
        )
        images = [part for part in image.content if part.type == "image"]
        assert len(images) == 1
        png = base64.b64decode(images[0].data, validate=True)
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        image_path.write_bytes(png)
        receipts.append(
            {
                "operation": "render_source_region",
                "result": image.structured_content,
                "image": image_path.name,
                "image_sha256": sha256(png).hexdigest(),
                "content_types": [part.type for part in image.content],
            }
        )
        checkpoint()
        wrong = dict(pin, version=3, view="items", content_digest="0" * 64)
        try:
            await client.call_tool("inspect_source", {"request": wrong}, timeout=120)
        except ToolError as error:
            assert "digest" in str(error) or "pin" in str(error), str(error)
            receipts.append(
                {
                    "operation": "wrong_digest",
                    "outcome": "refused",
                    "detail": str(error),
                }
            )
            checkpoint()
        else:
            raise AssertionError("wrong integrated product digest was accepted")
        queue = await client.call_tool("queue_status", {}, timeout=120)
        receipts.append(
            {"operation": "queue_status", "result": queue.structured_content}
        )
        checkpoint()
    with output.open("x") as target:
        json.dump(
            {"outcome": "passed", "selection": selection, "calls": receipts},
            target,
            ensure_ascii=False,
            indent=2,
        )
        target.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    asyncio.run(
        exercise(
            json.loads(arguments.selection.read_bytes()),
            arguments.database,
            Path(__file__).resolve().parents[4],
            arguments.output,
        )
    )
