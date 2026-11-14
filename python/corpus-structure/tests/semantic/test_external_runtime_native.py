"""Actual stdio and lazy settings custody for the ordinary native external executor."""

from pathlib import Path
import sys

import anyio
import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import text

from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from semantic.data_operation_demand_support import attach, claim
from semantic.external_scenarios import EXTERNAL

pytestmark = pytest.mark.parametrize("ddo_kernel", [EXTERNAL], indirect=True, ids=["external"])


def environment(settings):
    database = settings.database
    return {"CORPUS_DATABASE__URL": database.url,
            "CORPUS_DATABASE__MAINTENANCE_URL": database.maintenance_url,
            "CORPUS_DATABASE__READER_URL": database.reader_url or "",
            "CORPUS_DATABASE__EVALUATOR_URL": database.evaluator_url or "",
            "CORPUS_DATABASE__ADMISSION_URL": database.admission_url or "",
            "CORPUS_RUNTIME__DEFAULT_PROJECT": "ddo-test"}


def create_packet(kernel):
    demand, _, _, attached = attach(kernel)
    fence = claim(kernel, attached)
    with kernel["engine"].begin() as connection:
        packet = DataOperationStorage(connection).invoke("retain_external_data_packet", {
            **fence, "runtime_id": kernel["runtime"], "max_bytes": 100000})
    return demand, fence, packet


@pytest.mark.parametrize("mode", ["early_exit", "tool_failure", "complete", "cancelled"])
def test_current_cli_external_stdio_preserves_exact_native_custody_and_closes_pool(
    ddo_kernel, ddo_application_settings, tmp_path, mode
):
    demand, initial, packet = create_packet(ddo_kernel)
    transport = StdioTransport(command=str(Path(sys.executable).with_name("ci")),
        args=["mcp", "serve", "--project", "ddo-test", "--demand", demand["demand_id"]],
        env=environment(ddo_application_settings), cwd=str(Path(__file__).resolve().parents[4]),
        keep_alive=False, log_file=tmp_path / "external-stdio.log")
    selected = {}

    def principals():
        with ddo_kernel["engine"].connect() as connection:
            return connection.execute(text("SELECT usename FROM pg_stat_activity WHERE datname=current_database() AND application_name='ci-mcp-external'")).scalars().all()

    async def exchange():
        with anyio.CancelScope() as cancellation:
            async with Client(transport) as client:
                names = {tool.name for tool in await client.list_tools()}
                assert {"queue_next", "claim_packet", "read_packet", "submit_result", "inspect_result"} <= names
                assert not {"propose_claims", "read_unit", "read_instructions", "record_direction"} & names
                assert principals() == []
                if mode == "early_exit":
                    return
                headers = await client.call_tool("queue_next", {})
                assert headers.structured_content["packets"][0]["packet_id"] == packet["packet_id"]
                assert set(principals()) == {"corpus_sem_writer"}
                response = await client.call_tool("claim_packet", {"packet_id": packet["packet_id"]})
                selected.update(response.structured_content)
                if mode == "cancelled":
                    cancellation.cancel()
                    await anyio.sleep(0)
                    return
                if mode == "tool_failure":
                    failed = await client.call_tool("read_packet", {"packet_id": "absent:packet", "claim": selected}, raise_on_error=False)
                    assert failed.is_error
                    return
                actual = await client.call_tool("read_packet", {"packet_id": packet["packet_id"], "claim": selected})
                assert actual.structured_content["packet_digest"] == packet["packet_digest"]
                completed = await client.call_tool("submit_result", {"packet_id": packet["packet_id"], "claim": selected,
                    "actor_assertion": "controlled-external", "model_assertion": None,
                    "result": {"outcome": "success", "outputs": [{"role": "result", "body": 7}]}})
                assert completed.structured_content["state"] == "committed"
                assert completed.structured_content["receipt"]["admitting_principal"] == "corpus_sem_writer"

    anyio.run(exchange)
    assert principals() == []
    with ddo_kernel["engine"].connect() as connection:
        task = connection.execute(text("SELECT status,attempt FROM ops.task WHERE id=:task"), {"task": initial["task_id"]}).one()
        if mode == "early_exit":
            assert task.status == "awaiting_agent" and task.attempt == initial["attempt"]
        elif mode == "complete":
            assert task.status == "done" and task.attempt == selected["attempt"]
        else:
            assert task.status == "running" and task.attempt == selected["attempt"]
        assert connection.scalar(text("SELECT count(*) FROM ops.data_external_receipt")) == (1 if mode == "complete" else 0)


def test_lazy_default_external_session_freezes_settings_and_observes_later_native_packet(
    ddo_kernel, ddo_application_settings, monkeypatch
):
    for key, value in environment(ddo_application_settings).items():
        monkeypatch.setenv(key, value)

    async def exchange():
        async with Client(build_server()) as client:
            await client.list_tools()
            monkeypatch.setenv("CORPUS_RUNTIME__DEFAULT_PROJECT", "changed-after-lifespan")
            assert (await client.call_tool("queue_next", {})).structured_content == {"packets": []}
            _, _, packet = create_packet(ddo_kernel)
            headers = await client.call_tool("queue_next", {})
            assert headers.structured_content["packets"][0]["packet_id"] == packet["packet_id"]

    anyio.run(exchange)
