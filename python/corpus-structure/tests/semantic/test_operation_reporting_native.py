"""Actual archived DDO CLI/MCP observations and independent native effect fences."""

import json
from dataclasses import replace
from typing import cast

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.intervene.semantic_server import build_retained_reader_server
from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.demand_queries import DemandQueryRequest
from corpus_structure.semantic.operation_reporting import explain_operation
from corpus_structure.semantic.releases import persist_release
from corpus_structure.settings import Settings
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import STORAGE, prepare_kernel


def reader_settings(engine):
    url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return Settings(database={"url": url, "reader_url": url})


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_actual_cli_and_mcp_reports_share_current_archived_declaration_and_frontier(
    ddo_kernel, cli
):
    demand, _, _, _ = attach(ddo_kernel)
    reader = ddo_kernel.purpose("read")
    settings = reader_settings(reader)
    release = ddo_kernel.prepared.release_id
    operation = "urn:ddo-test:source"
    try:
        explained = cli(
            "schema",
            "explain-operation",
            operation,
            "--release",
            release,
            "--demand",
            demand["demand_id"],
            "--project",
            "ddo-test",
            "--json",
            settings=lambda: settings,
        )
        assert explained.exit_code == 0, explained.output
        observation = json.loads(explained.stdout)
        assert observation["report_version"] == 3
        assert observation["operation"] == operation
        assert observation["authority"] == "declaration_and_observation_only"
        assert observation["observation_status"] == "observed"
        frontier = json.loads(observation["observation_json"])
        assert frontier["cut"]["release_id"] == release
        assert frontier["items"][0]["obligation"]["operation_id"] == operation
        assert frontier["items"][0]["uses"][0]["fate"] == "attached"
        compared = cli("schema", "diff", release, release, "--json", settings=lambda: settings)
        assert compared.exit_code == 0, compared.output
        impact = json.loads(compared.stdout)
        assert impact["report_version"] == 5 and impact["changes"] == []
        invalid = cli(
            "schema",
            "explain-operation",
            "not_declared",
            "--release",
            release,
            "--json",
            settings=lambda: settings,
        )
        assert invalid.exit_code == 1, invalid.output
        assert json.loads(invalid.stdout)["error"]["code"] == "SemanticRefusal"

        async def journey():
            server = build_retained_reader_server(read_engine=reader, project="ddo-test")
            async with Client(server) as client:
                answer = await client.call_tool(
                    "explain_operation",
                    {
                        "release": release,
                        "operation": operation,
                        "demand_id": demand["demand_id"],
                        "project_id": "ddo-test",
                    },
                )
                result = answer.structured_content
                assert result is not None
                assert {k: v for k, v in result.items() if k != "observation_json"} == {
                    k: v for k, v in observation.items() if k != "observation_json"
                }
                selected = json.loads(result["observation_json"])
                assert selected["items"] == frontier["items"]
                # Separate fresh reads own separate read/snapshot pins. Compare the
                # actual demand/release and frontier rather than relabelling cuts.
                for field in ("release_id", "project_id", "demand_id"):
                    assert selected["cut"][field] == frontier["cut"][field]
                assert selected["cut"]["read_id"]
                assert frontier["cut"]["read_id"]
                difference = await client.call_tool(
                    "compare_semantic_releases",
                    {
                        "before": release,
                        "after": release,
                    },
                )
                assert difference.structured_content == impact

        anyio.run(journey)
    finally:
        reader.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_frontier_observation_never_authorizes_publication_after_producer_revocation(ddo_kernel):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    intent = retain(ddo_kernel, fence)
    reader = ddo_kernel.purpose("read")
    try:
        with reader.begin() as connection:
            observed = explain_operation(
                ddo_kernel.prepared,
                "urn:ddo-test:source",
                connection=connection,
                observation=DemandQueryRequest(
                    demand_id=demand["demand_id"],
                    project_id="ddo-test",
                    view="operations",
                    operation_id="urn:ddo-test:source",
                ),
            ).model_dump(mode="json")
        assert observed["observation_status"] == "observed"
        assert observed["authority"] == "declaration_and_observation_only"
        with ddo_kernel.engine.begin() as connection:
            assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 0
            DataOperationStorage(connection).revoke_data_support(
                cast(
                    WireRevokeDataSupportRequest,
                    {
                        "project_id": "ddo-test",
                        "original_source": "source:test",
                        "selector_kind": "recipe",
                        "selector": ddo_kernel.identities["urn:ddo-test:source", "recipe"],
                        "reason": "producer defect discovered after observation",
                    },
                )
            )
        with pytest.raises(DBAPIError, match="revoked"):
            publish(ddo_kernel, fence, intent)
        with ddo_kernel.engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM ops.data_publication_receipt")) == 0
            assert connection.scalar(text("SELECT count(*) FROM ops.data_derivation")) == 0
    finally:
        reader.dispose()


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_actual_archived_kind_change_reaches_cli_mcp_with_declared_consumers(ddo_kernel, cli):
    changed = prepare_kernel(
        replace(
            STORAGE,
            name="report-optional-sample",
            schema_text=STORAGE.schema_text.replace(
                "value: {range: integer, required: true}",
                "value: {range: integer, required: false}",
            ),
        )
    )
    with ddo_kernel.engine.begin() as connection:
        persist_release(
            connection, changed.bundle, changed.dependencies, changed.profile, changed.prepared
        )
    reader = ddo_kernel.purpose("read")
    settings = reader_settings(reader)
    before, after = ddo_kernel.prepared.release_id, changed.prepared.release_id
    try:
        result = cli("schema", "diff", before, after, "--json", settings=lambda: settings)
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        semantic = [
            row
            for row in report["changes"]
            if row["aspect"] == "semantic-node"
            and row["model_ref"] == "urn:ddo-test:Sample/property/value"
        ]
        assert len(semantic) == 1
        assert "urn:ddo-test:sample" in semantic[0]["consumers"]
        assert any(member["model_path"].endswith("/required") for member in semantic[0]["members"])
        assert report["before_release"] == before and report["after_release"] == after
        assert any("retained query analysis unavailable" in value for value in report["unknowns"])

        async def journey():
            server = build_retained_reader_server(read_engine=reader, project="ddo-test")
            async with Client(server) as client:
                answer = await client.call_tool(
                    "compare_semantic_releases", {"before": before, "after": after}
                )
                assert answer.structured_content == report

        anyio.run(journey)
    finally:
        reader.dispose()
