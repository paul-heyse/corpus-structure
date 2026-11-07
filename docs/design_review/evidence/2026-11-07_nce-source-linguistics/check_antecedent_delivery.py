"""Check the retained named operation and its CLI, MCP and detached deliveries."""

import argparse
import json
import shutil
from pathlib import Path

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.serve.structural_products import StructuralPage


def rows(path):
    with path.open() as lines:
        return [json.loads(json.loads(line)["payload_json"]) for line in lines]


async def check(destination, bundle):
    expected = json.loads((destination / "antecedent.json").read_bytes())
    view = expected["source"]["source_view_id"]
    component = expected["component"]
    cli = StructuralPage.model_validate_json((destination / "cli.json").read_bytes())
    assert (cli.run_id, cli.cut_id) == (expected["run_id"], expected["cut_id"])
    (report,) = cli.reports
    assert report.definition_components is not None
    assert component in [c.model_dump(mode="json") for c in report.definition_components.components]

    manifest = json.loads((destination / "review-verify.json").read_bytes())
    assert manifest["completeness"] == "selected_source_closure"
    (source,) = [row["text"] for row in rows(bundle / "sources.jsonl") if row["source_view_id"] == view]
    for name in ("term", "content"):
        extent = component[name]
        assert source[extent["start"] : extent["end"]] == extent["text"]

    (retained,) = [
        row for row in rows(bundle / "reports.jsonl")
        if row["body"].get("method") == "structure.definition_components"
    ]
    assert retained["origin_run_id"] == cli.run_id
    assert retained["body"]["operation_version"] == "7"
    detail = source_python(retained["body"]["parse_detail"])
    (naming,) = [
        operation for operation in detail["named_rule_operations"]
        if operation["passage_id"] == component["term"]["passage_id"]
        and operation["variant"] == "passive_called_term"
        and operation["matched_count"]
    ]
    (match,) = naming["matches"]
    (mention,) = [role for role in match["roles"] if role["role"] == "defining_content"]
    begin, end = mention["extents"][0][0], mention["extents"][-1][1]
    assert (begin, end, source[begin:end]) == (296, 314, "This set of points")
    assert match["content_antecedent"] == component["content"]
    assert naming["block_id"] == "#/texts/3" and naming["annotation_task_id"] == 594

    command = shutil.which("ci")
    if command is None:
        raise ValueError("the installed ci executable is unavailable")
    transport = StdioTransport(
        command=command,
        args=["mcp", "serve", "--semantic-run", str(cli.run_id)],
        cwd=str(Path.cwd()),
        log_file=destination / "mcp-server.log",
    )
    async with Client(transport, timeout=180) as client:
        reply = await client.call_tool(
            "structural_products",
            {"request": {"run_id": cli.run_id, "cut_id": cli.cut_id, "kind": "definition_components"}},
        )
    if reply.is_error or not isinstance(reply.structured_content, dict):
        raise ValueError("MCP did not deliver the pinned definition page")
    assert StructuralPage.model_validate(reply.structured_content) == cli
    receipt = {
        "outcome": "passed", "run_id": cli.run_id, "cut_id": cli.cut_id,
        "source_view_id": view, "component_id": component["component_id"],
        "annotation_task_id": naming["annotation_task_id"], "native_block": naming["block_id"],
        "local_mention": {"start": begin, "end": end, "text": source[begin:end]},
        "bundle": bundle.parent.name,
        "selection_digest": manifest["selection_digest"],
        "completeness": manifest["completeness"],
    }
    (destination / "delivery.json").write_bytes(canonical_bytes(receipt) + b"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    anyio.run(check, args.destination, args.bundle)
