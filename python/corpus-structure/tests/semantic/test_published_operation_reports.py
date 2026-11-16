"""Actual CLI/MCP observations distinguish frozen demand from completed projection."""

import json

import anyio
from fastmcp import Client
from sqlalchemy import text

from corpus_structure.intervene.semantic_server import build_retained_reader_server
from corpus_structure.settings import Settings
from semantic.pdf_staging_support import create_private_build as create_private_build
from semantic.selected_source_native_support import publish_selected


def test_cli_mcp_current_projection_observations_are_read_only_and_preserve_unknown(
    create_private_build,
    commit_db_engine,
    commit_writer_engine,
    commit_reader_engine,
    tmp_path,
    cli,
):
    factory = create_private_build
    build = factory()
    publication = publish_selected(commit_writer_engine, build, tmp_path / "publication")
    factory.complete(build, publication)
    demand = factory.register_sources(build, sections=("Selected chapter",))
    operation = "source.pdf_views/discovery"
    settings = Settings(
        database={
            "url": commit_reader_engine.url.set(drivername="postgresql").render_as_string(
                hide_password=False
            )
        }
    )

    def counts():
        with commit_db_engine.connect() as connection:
            return connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM ops.task),"
                    "(SELECT count(*) FROM ops.data_completion_intent),"
                    "(SELECT count(*) FROM ops.pdf_published_revision)"
                )
            ).one()

    def inspect():
        result = cli(
            "schema",
            "explain-operation",
            operation,
            "--release",
            build.release_id,
            "--demand",
            demand,
            "--project",
            factory.project_id,
            "--json",
            settings=lambda: settings,
        )
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        observed = json.loads(report["observation_json"])
        assert report["authority"] == "declaration_and_observation_only"
        assert report["observation_status"] == "observed"
        assert report["operation"] == operation and report["release_id"] == build.release_id
        assert observed["cut"]["project_id"] == factory.project_id
        assert observed["cut"]["demand_id"] == demand
        return report, observed

    baseline = counts()
    before, pending = inspect()
    assert pending["items"] and all(
        row["obligation"]["fate"] != "fulfilled" for row in pending["items"]
    )
    assert counts() == baseline
    # The read itself cannot prepare a source or create a computation. The
    # explicit declared execution is the only change between these observations.
    rows = factory.selected_sources(build, sections=("Selected chapter",))
    assert {row["body"]["source"]["section_pointer"] for row in rows} == {
        "#/groups/1",
        "#/groups/2",
    }
    after, fulfilled = inspect()
    assert all(row["obligation"]["fate"] == "fulfilled" for row in fulfilled["items"])
    assert after["definition"] == before["definition"] and after["recipe"] == before["recipe"]
    completed = counts()
    assert completed[0] > baseline[0] and completed[1] > baseline[1]
    assert completed[2] == baseline[2] == 1

    async def journey():
        server = build_retained_reader_server(
            read_engine=commit_reader_engine, project=factory.project_id
        )
        async with Client(server) as client:
            answer = await client.call_tool(
                "explain_operation",
                dict(
                    release=build.release_id,
                    operation=operation,
                    demand_id=demand,
                    project_id=factory.project_id,
                ),
            )
            assert answer.structured_content is not None
            report = answer.structured_content
            assert (
                report["definition"] == after["definition"] and report["recipe"] == after["recipe"]
            )
            observed = json.loads(report["observation_json"])
            assert all(row["obligation"]["fate"] == "fulfilled" for row in observed["items"])
            missing = await client.call_tool(
                "inspect_characterization",
                {
                    "request": dict(
                        project_id=factory.project_id,
                        demand_id=demand,
                        product_id="outside-selection",
                        inventory="annotations",
                    )
                },
            )
            assert missing.structured_content is not None
            empty = json.loads(missing.structured_content["exact_json"])
            assert empty["items"] == [] and empty["knowledge"] == "unknown"
            refused = await client.call_tool(
                "explain_operation",
                dict(
                    release=build.release_id,
                    operation=operation,
                    demand_id=demand,
                    project_id="another-project",
                ),
                raise_on_error=False,
            )
            assert refused.is_error
            malformed = await client.call_tool(
                "explain_operation",
                dict(
                    release=build.release_id,
                    operation=operation,
                    demand_id=demand,
                    project_id=factory.project_id,
                    limit=0,
                ),
                raise_on_error=False,
            )
            assert malformed.is_error

    anyio.run(journey)
    assert counts() == completed
    invalid = cli(
        "schema",
        "explain-operation",
        operation,
        "--release",
        build.release_id,
        "--demand",
        demand,
        "--project",
        factory.project_id,
        "--limit",
        "0",
        "--json",
        settings=lambda: settings,
    )
    assert invalid.exit_code != 0 and "limit" in invalid.output.lower()
    assert counts() == completed
