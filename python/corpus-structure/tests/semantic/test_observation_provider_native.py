"""Controlled interrupted provider, genuine fresh stdio MCP, and native reader joins."""

from __future__ import annotations

import _thread
import json
import shutil
import sys
import threading
from pathlib import Path

import pytest
import typer
from sqlalchemy import select

from corpus_structure.cli.app import app
from corpus_structure.cli.managed import ResultStore
from corpus_structure.cli.observations import ObservationSelection
from corpus_structure.cli.output import CliState
from corpus_structure.cli.result_inspection import inspect_result
from corpus_structure.intervene import automated
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.storage_target import acquired_target
from semantic.agent_scenarios import ResubmissionRecipe


@pytest.mark.parametrize("resubmission_case", [ResubmissionRecipe(composed=True)], indirect=True)
def test_interrupted_provider_actual_stdio_native_receipt_and_read_purpose_join(
    resubmission_case, tmp_path, monkeypatch, resubmission_application_settings
):
    commit_db_engine = resubmission_case.admin
    commit_writer_engine = resubmission_case.writer
    commit_application_settings = resubmission_application_settings
    prepared, run_id, task_id, _locator = resubmission_case.stage.result
    script = tmp_path / "controlled-provider"
    ready = tmp_path / "concurrent-requests-ready"
    script.write_text(
        f"#!{sys.executable}\n"
        "import sys,json,anyio\n"
        "from pathlib import Path\n"
        "from fastmcp import Client\n"
        "from fastmcp.client.transports import StdioTransport\n"
        "configuration=json.load(open(sys.argv[sys.argv.index('--mcp-config')+1]))['mcpServers']['corpus']\n"
        "async def main():\n"
        " transport=StdioTransport(command=configuration['command'],\n"
        "  args=configuration['args'],env=configuration['env'],keep_alive=False)\n"
        " async with Client(transport) as client:\n"
        f"  response=await client.call_tool('queue_next',{{'run':{run_id}}})\n"
        f"  assert response.structured_content['tasks'][0]['task_id']=={task_id}\n"
        "  async def refused(selected):\n"
        "   response=await client.call_tool('read_unit',\n"
        "    {'task_id':selected},raise_on_error=False)\n"
        "   assert response.is_error\n"
        "  async with anyio.create_task_group() as group:\n"
        f"   group.start_soon(refused,{task_id + 1000000})\n"
        f"   group.start_soon(refused,{task_id + 2000000})\n"
        f"  Path({str(ready)!r}).write_text('ready')\n"
        "  print('native lease and concurrent requests completed',file=sys.stderr,flush=True)\n"
        "  await anyio.sleep(60)\n"
        "anyio.run(main)\n"
    )
    script.chmod(0o700)
    original_which = shutil.which
    monkeypatch.setattr(
        automated.shutil,
        "which",
        lambda command: str(script) if command == "claude" else original_which(command),
    )
    settings = commit_application_settings.model_copy(
        update={
            "paths": commit_application_settings.paths.model_copy(
                update={"data_dir": tmp_path / "data"}
            )
        }
    )
    store = ResultStore(tmp_path / "results")
    stop_controller = threading.Event()

    def interrupt_after_requests():
        while not stop_controller.wait(0.02):
            if ready.is_file():
                _thread.interrupt_main()
                return

    controller = threading.Thread(target=interrupt_after_requests)
    controller.start()
    try:
        with (
            pytest.raises(KeyboardInterrupt),
            store.operation("regenerate", observations=True) as invocation,
        ):
            invocation.bind_observations(
                run_id=run_id, release_id=prepared.release_id, project="resubmit"
            )
            with commit_writer_engine.connect() as conn:
                target = acquired_target(conn, purpose="write")
            invocation.manifest.details["observation_target"] = target.model_dump(mode="json")
            invocation._write()
            automated.extract_run(commit_writer_engine, settings, run_id, timeout=60)
    finally:
        stop_controller.set()
        controller.join(timeout=2)
    assert not controller.is_alive() and ready.is_file()
    page = store.read_observations(invocation.id)
    leased = [row for row in page.rows if row.kind == "mcp_attempt_leased"]
    assert len(leased) == 1, [row.model_dump(mode="json") for row in page.rows]
    row = leased[0]
    assert row.bindings.invocation_id == invocation.id
    assert (
        row.bindings.run_id == run_id
        and row.bindings.task_id == task_id
        and row.bindings.attempt == 1
    )
    assert row.assurance == "provider_reported" and row.producer_sequence > 0
    receipt_path = row.fields["provider_receipt"]
    assert isinstance(receipt_path, str)
    raw = json.loads(Path(receipt_path).read_text())
    assert raw["task_id"] == task_id and raw["attempt"] == 1
    assert raw["invocation_id"] == row.bindings.provider_invocation
    requests = [
        item
        for item in page.rows
        if item.kind == "mcp_tool_started"
        and item.bindings.task_id in {task_id + 1000000, task_id + 2000000}
    ]
    assert len(requests) == 2
    expected = {(item.bindings.task_id, item.bindings.request_id) for item in requests}
    assert {item.bindings.task_id for item in requests} == {task_id + 1000000, task_id + 2000000}
    assert len({item.bindings.request_id for item in requests}) == 2
    assert all(item.bindings.request_id is not None for item in requests)
    failures = [
        item
        for item in page.rows
        if item.kind == "mcp_tool_failed"
        and item.bindings.task_id in {task_id + 1000000, task_id + 2000000}
    ]
    assert {(item.bindings.task_id, item.bindings.request_id) for item in failures} == expected
    finished = next(item for item in page.rows if item.kind == "provider_finished")
    assert finished.bindings.task_id is None and finished.bindings.request_id is None
    assert finished.bindings.attempt is None
    assert finished.fields["process_outcome"] == "interrupted"
    assert finished.bindings.provider_invocation == row.bindings.provider_invocation
    with commit_db_engine.connect() as conn:
        task = conn.execute(
            select(table("ops.task").c.attempt, table("ops.task").c.status).where(
                table("ops.task").c.id == task_id
            )
        ).one()
    assert task.attempt == 1 and task.status != "done"
    selection = ObservationSelection(
        provider_invocation=row.bindings.provider_invocation, task=task_id, attempt=1
    )
    ctx = typer.Context(
        typer.main.get_command(app), obj=CliState(settings_factory=lambda: settings)
    )
    report = inspect_result(ctx, store, invocation.id, selection, view="timeline")
    assert report.native.availability == "available", report.native.reason
    assert report.native.run is not None and report.native.task is not None
    assert report.native.denominator is not None
    assert report.native.run["run_id"] == run_id
    assert report.native.task["id"] == task_id and report.native.task["attempt"] == 1
    assert report.native.denominator >= 1 and report.native.counts is not None
    assert any(
        action.kind == "native_status" and action.command == f"ci status {run_id}"
        for action in report.next_actions
    )
    # Native run/attempt authority survives the observational wrapper's failure.
    assert report.outcome == "interrupted" and report.custody == "settled"
