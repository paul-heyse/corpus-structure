"""Check one completed parser worklist through the installed CLI and fresh MCP."""

import json
import os
import sys
from pathlib import Path
from subprocess import check_output

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def main():
    evidence = Path(__file__).resolve().parent
    run = json.loads((evidence / "raw/book-run.json").read_bytes())
    project = json.loads((evidence / "raw/book-request.json").read_bytes())["project"]
    run_id = run["run_id"]
    command = str(Path(sys.executable).with_name("ci"))
    request = {"run_id": run_id, "include_scope_coverage": True, "limit": 32}
    cli = json.loads(
        check_output(
            [
                command,
                "contributions",
                "list",
                "--run",
                str(run_id),
                "--include-scope-coverage",
                "--limit",
                "32",
                "--json",
            ],
        )
    )

    async def read_mcp():
        transport = StdioTransport(
            command=command,
            args=["mcp", "serve", "--semantic-run", str(run_id)],
            env={
                **{name: value for name, value in os.environ.items() if name.startswith("CORPUS_")},
                "CORPUS_RUNTIME__DEFAULT_PROJECT": project,
            },
            cwd=str(evidence.parents[3]),
            keep_alive=False,
        )
        async with Client(transport) as client:
            response = await client.call_tool("contributions", {"request": request})
            return response.structured_content

    mcp = anyio.run(read_mcp)
    status = json.loads(
        check_output([command, "run", "status", str(run_id), "--project", project, "--json"])
    )

    def coverage(page):
        return [item["row"] for item in page["items"] if item["population"] == "scope_coverage"]

    expected = run["scope_coverage"]
    assert (
        coverage(cli)
        == coverage(mcp)
        == status["progress"]["run"]["pm2_scope_coverage"]
        == expected
    )
    assert [row["outcome"] for row in expected[:6]] == [
        "succeeded",
        "unscheduled",
        "empty",
        "ineligible",
        "succeeded",
        "limited",
    ]
    limited = expected[5]
    children = [row for row in expected if row["parent_input_digest"] == limited["input_digest"]]
    assert len(children) == 2
    assert [row["outcome"] for row in children] == ["succeeded", "succeeded"]
    assert children[0]["extent"][0] == limited["extent"][0]
    assert children[0]["extent"][1] == children[1]["extent"][0]
    assert children[1]["extent"][1] == limited["extent"][1]
    print(json.dumps({"run": run_id, "cut": run["cut_id"], "coverage": expected}, indent=2))


if __name__ == "__main__":
    main()
