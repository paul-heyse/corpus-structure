"""Actual v3 CLI, fresh stdio MCP and atomic selected export on completed public run45."""
import asyncio
import json
import subprocess
from hashlib import sha256
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"

def cli(args):
    result = subprocess.run(["uv", "run", "ci", "contributions", *args],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)

async def main():
    prefix = "contribution-v3-transport-002"
    target = RAW / (prefix + ".json")
    if target.exists():
        raise FileExistsError(target)
    pages = json.loads((RAW / "contextual-local-publication-003-common-pages.json").read_bytes())
    public = next(item["row"] for page in pages for item in page["items"]
                  if item["population"] == "local_semantic_assertion")
    cid = public["contribution_id"]
    request = dict(run_id=45, method="retrieve.contextual", operation_version="1",
        contribution_id=cid, include_interpretation=True, include_assessment=True,
        include_publication=True, limit=1000)
    args = ["--run", "45", "--method", "retrieve.contextual", "--operation-version", "1",
            "--contribution-id", cid, "--include-interpretation", "--include-assessment",
            "--include-publication"]
    expected = cli(["list", *args, "--limit", "1000", "--json"])
    assert expected["inventory_counts"]["contributions"] == 1
    assessments = [item["row"] for item in expected["items"] if item["population"] == "assessment"]
    assert len(assessments) == 1 and assessments[0]["outcome"] == "supported"
    async with Client(StdioTransport(command="uv", args=["run", "ci", "mcp", "serve", "--semantic-run", "45"])) as client:
        result = await client.call_tool("contributions", {"request":request})
        assert not result.is_error and result.structured_content is not None
        actual = result.structured_content
        for key in ("version", "items", "selection", "inventory_counts", "assessment_scope", "cut_id"):
            assert actual[key] == expected[key], key
        first = await client.call_tool("contributions", {"request":dict(request, limit=1)})
        assert first.structured_content is not None
        rejected = await client.call_tool("contributions", {"request":dict(request,
            include_assessment=False, cursor=first.structured_content["next_cursor"])}, raise_on_error=False)
        assert rejected.is_error
    destination = RAW / (prefix + "-export")
    manifest = cli(["export", str(destination), *args, "--json"])
    content = (destination / "items.jsonl").read_bytes()
    assert sha256(content).hexdigest() == manifest["sha256"]
    detached = [json.loads(line) for line in content.splitlines()]
    assert detached == expected["items"]
    assert manifest["assessment_scope"] == "published_admission_witnesses_only"
    assert "not a self-contained PCE09" in manifest["scope"]
    report = dict(outcome="passed", run_id=45, cut_id=expected["cut_id"], contribution_id=cid,
        inventory_counts=expected["inventory_counts"], export_manifest=manifest,
        controls=["actual CLI/MCP v3 agreement", "changedfacet continuation refusal", "atomic JSONL manifest hash and exactitems"],
        source_or_model_execution=False, private_grade_access=False)
    with target.open("x") as stream:
        json.dump(report, stream, indent=2); stream.write("\n")
    print(json.dumps(report))

if __name__ == "__main__":
    asyncio.run(main())
