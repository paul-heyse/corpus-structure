"""Current MCP requests preserve exact task fences without fabricated provider success."""

from typing import cast as typing_cast
from corpus_structure.semantic._data_operation_wire import (
    WireRetainExternalDataPacketRequest,
)

from contextlib import contextmanager

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import text

from corpus_structure.cli.managed import ResultStore
from corpus_structure.cli.observation_logging import INVOCATION_ENV
from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.data_operation_external import ExternalDataSession
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_demand_support import attach, claim
from semantic.external_scenarios import EXTERNAL


@pytest.mark.parametrize("ddo_kernel", [EXTERNAL], indirect=True, ids=["external"])
def test_external_mcp_disconnect_preserves_native_attempt_and_scoped_observations(
    ddo_kernel, tmp_path, monkeypatch
):
    demand, _, _, attached = attach(ddo_kernel)
    fence = claim(ddo_kernel, attached)
    with ddo_kernel["engine"].begin() as connection:
        packet = DataOperationStorage(connection).retain_external_data_packet(typing_cast(WireRetainExternalDataPacketRequest, {**fence, "runtime_id": ddo_kernel["runtime"], "max_bytes": 100000}))
    session = ExternalDataSession(ddo_kernel["engine"], "ddo-test", demand_id=demand["demand_id"])
    store = ResultStore(tmp_path / "results")
    with store.operation("demands.external.transport", observations=True) as invocation:
        monkeypatch.setenv(INVOCATION_ENV, invocation.id)

        @contextmanager
        def observation_endpoint(**_):
            yield invocation.observation_writer

        monkeypatch.setattr(
            "corpus_structure.cli.observation_logging.child_capture", observation_endpoint
        )

        async def exchange():
            async with Client(build_server(session)) as client:
                response = await client.call_tool("queue_next", {})
                assert response.structured_content is not None
                assert response.structured_content["packets"][0]["packet_id"] == packet["packet_id"]
                leased = await client.call_tool("claim_packet", {"packet_id": packet["packet_id"]})
                assert leased.structured_content is not None
                actual = leased.structured_content
                assert actual is not None
                assert actual["attempt"] == fence["attempt"] + 1
                read = await client.call_tool(
                    "read_packet", {"packet_id": packet["packet_id"], "claim": actual}
                )
                assert read.structured_content is not None
                assert (
                    read.structured_content["packet"]["protocol"]["requested_actor"]
                    == "controlled-external"
                )

                async def refused(task):
                    bad = {**actual, "task_id": task}
                    response = await client.call_tool(
                        "read_packet",
                        {"packet_id": packet["packet_id"], "claim": bad},
                        raise_on_error=False,
                    )
                    assert response.is_error

                async with anyio.create_task_group() as group:
                    group.start_soon(refused, actual["task_id"] + 1000000)
                    group.start_soon(refused, actual["task_id"] + 2000000)
                return actual

        actual = anyio.run(exchange)
        # Closing transport does not invent cancellation, retirement or success.
        invocation.settle("passed", packet_id=packet["packet_id"])
    observations = store.read_observations(invocation.id).rows
    failures = [row for row in observations if row.kind == "mcp_tool_failed"]
    assert len(failures) == 2
    assert {row.bindings.task_id for row in failures} == {
        actual["task_id"] + 1000000,
        actual["task_id"] + 2000000,
    }
    assert len({row.bindings.request_id for row in failures}) == 2
    assert all(row.bindings.invocation_id == invocation.id for row in failures)
    assert not any(row.kind == "provider_finished" for row in observations)
    with ddo_kernel["engine"].connect() as connection:
        task = connection.execute(
            text("SELECT attempt,status FROM ops.task WHERE id=:task"), {"task": actual["task_id"]}
        ).one()
        assert task.attempt == actual["attempt"] and task.status == "running"
    assert session.inspect(packet["packet_id"])["state"] == "awaiting-external"
