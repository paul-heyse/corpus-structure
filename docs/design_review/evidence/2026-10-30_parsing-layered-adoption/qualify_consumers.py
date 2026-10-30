"""Actual pinned CLI and stdio source journeys on an explicitly named completed run."""

from __future__ import annotations

import argparse
import json
import os
import select as select_io
import signal
import subprocess
from pathlib import Path

import pyarrow.parquet as pq
from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--default", action="store_true", help="Use the default project MCP session.")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with open_runtime_engine(Settings(), "parsing-consumer-observer", purpose="read") as engine:
        with engine.connect() as conn:
            builds, tasks = table("ops.rendition_build"), table("ops.task")
            root, rendition = conn.execute(
                select(builds.c.task_id, builds.c.rendition_id)
                .join(tasks, tasks.c.id == builds.c.task_id)
                .where(tasks.c.run_id == args.run)
                .order_by(builds.c.task_id)
                .limit(1)
            ).one()
    commands = []

    def cli(name: str, *command: str):
        result = subprocess.run(["uv", "run", "ci", *command], capture_output=True, text=True)
        (args.out / (name + ".stdout")).write_text(result.stdout)
        (args.out / (name + ".stderr")).write_text(result.stderr)
        commands.append({"command": ["ci", *command], "returncode": result.returncode})
        (args.out / "commands.json").write_text(json.dumps(commands, indent=2))
        if result.returncode:
            raise RuntimeError(f"{name} failed; retained output names the refusal")
        return json.loads(result.stdout) if result.stdout.strip() else None

    identity = [str(args.run), str(rendition)]
    products = cli("products", "source", "products", *identity, "--json")
    assert products["outcome"] != "unavailable"
    for product in ("source", "text"):
        pin = ["--product", product, "--producing-task", str(root)]
        inspected = cli(product + "-inspect", "source", "inspect", *identity, *pin,
                        "--start", "0", "--end", "20", "--json")
        assert inspected["rows"] and inspected["product_digest"]
        traced = cli(product + "-trace", "source", "trace", *identity, "0", "20", *pin,
                     "--json")
        assert traced["rows"]
        destination = args.out / (product + ".parquet")
        cli(product + "-export", "source", "export", *identity, str(destination), *pin,
            "--format", "parquet")
        exported = pq.read_table(destination)
        assert exported.num_rows > 0
        assert set(exported.column("task_id").to_pylist()) == {root}
        if product == "text":
            assert set(exported.column("product_key").to_pylist()) == {"text"}
        assert exported.schema.metadata[b"source_selection"]

    requested = cli("lexical-request", "source", "request", *identity, "lexical",
                    "--source-task", str(root), "--json")
    assert requested["status"] == "source_ready"
    assert requested["inputs"] and requested["products"]
    repeated = cli("lexical-replay", "source", "request", *identity, "lexical",
                   "--source-task", str(root), "--json")
    assert repeated["status"] == "source_ready"
    assert repeated["products"] == requested["products"]

    responses = []
    with (args.out / "stdio.stderr").open("w") as log:
        command = ["uv", "run", "ci", "mcp", "serve"]
        if not args.default:
            command.extend(["--semantic-run", str(args.run)])
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True,
            start_new_session=True,
        )
        assert process.stdin is not None and process.stdout is not None

        def rpc(number, method, params):
            process.stdin.write(json.dumps(dict(jsonrpc="2.0", id=number,
                                                method=method, params=params)) + "\n")
            process.stdin.flush()
            if not select_io.select([process.stdout], [], [], 60)[0]:
                raise TimeoutError(method)
            response = json.loads(process.stdout.readline())
            responses.append(response)
            (args.out / "stdio.json").write_text(json.dumps(responses, indent=2))
            assert response["id"] == number and "result" in response, response
            assert not response["result"].get("isError"), response
            return response["result"]

        try:
            rpc(1, "initialize", dict(protocolVersion="2025-06-18", capabilities={},
                                     clientInfo=dict(name="parsing-adoption", version="1")))
            process.stdin.write(json.dumps(dict(jsonrpc="2.0",
                                               method="notifications/initialized")) + "\n")
            process.stdin.flush()
            discovered = rpc(2, "tools/list", {})
            tool = next(t for t in discovered["tools"] if t["name"] == "inspect_source")
            assert tool["annotations"]["readOnlyHint"]
            for number, view in enumerate(("products", "components", "trace"), 3):
                request = dict(run_id=args.run, rendition_id=rendition,
                               producing_task_id=root, product_key="text", view=view,
                               representation_id="canonical", start=0, end=20, limit=1000)
                result = rpc(number, "tools/call", dict(name="inspect_source",
                                                      arguments=dict(request=request)))
                value = result.get("structuredContent")
                if value is None:
                    value = json.loads(next(c["text"] for c in result["content"]
                                            if c["type"] == "text"))
                assert value["rows"] and value["product_digest"]
            rpc(6, "tools/call", dict(name="queue_status", arguments={}))
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    print(json.dumps(dict(run_id=args.run, rendition_id=rendition, root_task=root,
                          cli_commands=len(commands), stdio_responses=len(responses))))


if __name__ == "__main__":
    main()
