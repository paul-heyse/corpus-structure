"""Check fresh CLI and stdio MCP delivery of one actual R15 occurrence."""

import argparse
import json
from pathlib import Path
from subprocess import run
import sys

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def compare(destination):
    expected = json.loads((destination / "cli.stdout").read_bytes())
    payload = json.loads((destination / "mcp.json").read_bytes())
    captures = {
        "cli": expected["binding"].pop("capture_id"),
        "mcp": payload["binding"].pop("capture_id"),
    }
    assert captures["cli"] and captures["mcp"] and captures["cli"] != captures["mcp"]
    assert canonical_bytes(payload) == canonical_bytes(expected)
    assert payload["items"]
    receipt = {
        "outcome": "passed", "run_id": payload["run_id"], "cut_id": payload["cut_id"],
        "occurrence_id": payload["selection"]["occurrence_id"],
        "items": len(payload["items"]), "fresh_stdio_handshake": True,
        "cli_payload_parity": True, "distinct_read_capture_ids": captures,
        "scope": "Bounded delivery of the actual private contextual occurrence and selection.",
    }
    (destination / "result.json").write_bytes(canonical_bytes(receipt) + b"\n")
    print(json.dumps(receipt))


async def check(attempt):
    result = json.loads((attempt / "result.json").read_bytes())
    assessment = json.loads((attempt / "independent-assessment.json").read_bytes())
    candidate = next(iter(assessment["exact_transform_occurrences"]))
    run_id = result["run"]["run_id"]
    cut_id = result["run"]["cut_id"]
    occurrence_id = candidate["occurrence_id"]
    ci = str(Path(sys.executable).with_name("ci"))
    destination = attempt / "transports-bounded"
    destination.mkdir(exist_ok=False)
    cli = run(
        [ci, "contributions", "list", "--run", str(run_id), "--source-view", "117",
         "--method", "retrieve.contextual", "--occurrence-id", occurrence_id,
         "--include-interpretation", "--json"],
        cwd=ROOT, capture_output=True, timeout=180, check=False,
    )
    (destination / "cli.stdout").write_bytes(cli.stdout)
    (destination / "cli.stderr").write_bytes(cli.stderr)
    cli.check_returncode()
    transport = StdioTransport(
        command=ci, args=["mcp", "serve", "--semantic-run", str(run_id)],
        cwd=str(ROOT), log_file=destination / "server.log",
    )
    async with Client(transport, timeout=180) as client:
        tools = await client.list_tools()
        assert "contributions" in {tool.name for tool in tools}
        call = await client.call_tool(
            "contributions",
            {"request": {"run_id": run_id, "source_view_id": 117, "method": "retrieve.contextual",
                         "occurrence_id": occurrence_id,
                         "include_interpretation": True}},
        )
        assert not call.is_error and isinstance(call.structured_content, dict)
        payload = call.structured_content
    (destination / "mcp.json").write_bytes(canonical_bytes(payload) + b"\n")
    assert payload["run_id"] == run_id and payload["cut_id"] == cut_id and payload["items"]
    compare(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt", choices=("native-retained002", "native-retained003"))
    parser.add_argument("--verify-retained", action="store_true")
    args = parser.parse_args()
    if args.verify_retained:
        compare(HERE / args.attempt / "transports-bounded")
    else:
        anyio.run(check, HERE / args.attempt)
