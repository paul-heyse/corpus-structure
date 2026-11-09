"""Read a native textbook condition with the same private Reader over CLI and MCP."""

import json
import shutil
import subprocess
from pathlib import Path

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.serve.contributions import ContributionPage, ContributionRequest

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "2026-11-07_nce-source-linguistics/qualifier-scope.json"


async def run():
    release_evidence = json.loads(REFERENCE.read_bytes())
    (expected,) = release_evidence["cases"]["131"]
    origin = release_evidence["run"]
    request = ContributionRequest(
        run_id=origin["run_id"],
        source_view_id=131,
        selected_task_id=1232,
        method="structure.scoped_relations",
        operation_version="3",
        include_interpretation=True,
        limit=500,
        max_bytes=16_777_216,
        page_bytes=16_000_000,
    )
    cli = shutil.which("ci")
    if cli is None:
        raise ValueError("run the probe with the installed ci command")
    command = [
        cli,
        "contributions",
        "list",
        "--run",
        str(request.run_id),
        "--source-view",
        str(request.source_view_id),
        "--selected-task-id",
        str(request.selected_task_id),
        "--method",
        str(request.method),
        "--operation-version",
        str(request.operation_version),
        "--include-interpretation",
        "--limit",
        str(request.limit),
        "--max-bytes",
        str(request.max_bytes),
        "--page-bytes",
        str(request.page_bytes),
        "--json",
    ]
    page = ContributionPage.model_validate_json(subprocess.check_output(command))
    transport = StdioTransport(
        command=cli,
        args=["mcp", "serve", "--semantic-run", str(request.run_id)],
        cwd=str(Path.cwd()),
        env={"PYTHONPATH": str(HERE.parents[3] / "python/corpus-structure/src")},
    )
    async with Client(transport, timeout=120) as client:
        result = await client.call_tool(
            "contributions",
            {"request": request.model_dump(mode="json", exclude_none=True)},
        )
    if result.is_error or not isinstance(result.structured_content, dict):
        raise ValueError("fresh MCP did not deliver the exact retained selection")
    mcp = ContributionPage.model_validate(result.structured_content)

    # Each transport opens its own snapshot. Compare the immutable result
    # binding and all rows, leaving only the per-read capture UUID distinct.
    def result_binding(result):
        return {key: value for key, value in result.binding.items() if key != "capture_id"}

    assert result_binding(mcp) == result_binding(page)
    assert mcp.model_dump(exclude={"binding"}) == page.model_dump(exclude={"binding"})
    assert page.cut_id == origin["cut_id"] and page.population_paging_complete
    assert page.standing == "retained_private" and page.publication == "not_included"

    composed = {
        item["row"]["contribution_id"]: item["row"]["composition"]
        for item in page.items
        if item["population"] == "interpretation" and "composition" in item["row"]
    }
    ((attachment_id, attachment),) = (
        (identity, facet)
        for identity, facet in composed.items()
        if facet.get("qualifier_kind") == expected["kind"]
        and [(part["role"], part.get("contribution_id")) for part in facet["roles"][:2]]
        == [("qualifier", expected["cue"]), ("host", expected["host"])]
    )
    assert attachment["condition"]["text"] == expected["text"]
    assert [part["state"] for part in attachment["roles"][:2]] == ["source_located", "retained"]
    cue = composed[expected["cue"]]
    assert [
        part["reference"]["contribution_id"]
        for part in cue["roles"]
        if part["role"] == "candidate_host"
    ] == [expected["host"]]
    return {
        "source": {
            "run_id": page.run_id,
            "cut_id": page.cut_id,
            "release_id": origin["release_id"],
            "source_view_id": request.source_view_id,
            "selected_task_id": request.selected_task_id,
        },
        "scope": "retained textbook Event F condition only; no database writes",
        "cli_and_fresh_mcp": "passed",
        "attachment_id": attachment_id,
        "attachment": attachment,
        "cue": cue,
        "public_semantic_admission": "not_run",
    }


if __name__ == "__main__":
    print(json.dumps(anyio.run(run), indent=2, ensure_ascii=False))
