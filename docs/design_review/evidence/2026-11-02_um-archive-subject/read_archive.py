"""Read-only actual retained-release CLI/MCP subject-boundary check (UM-11/14)."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
from fastmcp import Client
from mcp.types import TextContent
from typer.testing import CliRunner

from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState
from corpus_structure.intervene.semantic_server import SemanticProjectSession, build_semantic_server
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.contracts import bound_execution_model
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

RELEASE = "release:143908b452ff569d277197926ddb2f11481a94ea9aca7308340a325ff77b02fa"
PIN = dict(
    task_id=10,
    product_key="integrated",
    content_digest="d3482c7126a5db75d8bb1962bb34cabd1b8f772bc136cd3f5987744dfec7bce0",
)
settings = Settings(
    database={
        "url": "postgresql://corpus_sem_reader@/corpus_pdf_20261101?host=/var/run/postgresql&port=5434"
    }
)


def main():
    runner = CliRunner()
    with open_runtime_engine(settings, "um-archive-subject", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, RELEASE)
            assert prepared.release_id == RELEASE
            compiler = json.loads(bound_execution_model(prepared).content)["inputs"]["compiler_version"]
        static = runner.invoke(
            app,
            ["schema", "explain-operation", "read_source_view", "--release", RELEASE, "--json"],
            obj=CliState(lambda: settings),
        )
        assert static.exit_code == 0, static.output
        static_report = json.loads(static.stdout)
        with TemporaryDirectory(prefix="um-subject-") as directory:
            subject = Path(directory) / "subject.json"
            subject.write_text(json.dumps(PIN))
            result = runner.invoke(
                app,
                [
                    "schema", "explain-operation", "read_source_view", "--release", RELEASE,
                    "--subject", str(subject), "--json",
                ],
                obj=CliState(lambda: settings),
            )
        assert result.exit_code == 1, result.output
        cli_failure = json.loads(result.stdout)
        assert "retained release does not support subject contract PublishedDocumentSubject" in result.stdout

        async def journey():
            server = build_semantic_server(SemanticProjectSession(engine, "pdf-current"))
            async with Client(server) as client:
                response = await client.call_tool(
                    "explain_operation",
                    dict(release=RELEASE, operation="read_source_view", **PIN),
                    raise_on_error=False,
                )
                assert response.is_error
                content = response.content[0]
                assert isinstance(content, TextContent)
                failure = json.loads(content.text)
                assert "retained release does not support subject contract PublishedDocumentSubject" in content.text
                return failure

        mcp_failure = anyio.run(journey)
        print(json.dumps(dict(
            outcome="passed", release=RELEASE, execution_compiler=compiler,
            static_operation=static_report["operation"],
            cli_failure=cli_failure, mcp_failure=mcp_failure,
        ), indent=2))


if __name__ == "__main__":
    main()
