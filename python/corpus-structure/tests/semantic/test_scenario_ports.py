"""Actual scenario consumers preserve domain IDs while malformed wire data stays raw."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]


@pytest.mark.skipif(shutil.which("pyrefly") is None, reason="blocked: pyrefly not on PATH")
def test_scenario_consumer_refuses_exchanged_ids_and_wrong_resources(tmp_path: Path) -> None:
    source = tmp_path / "scenario_consumer.py"
    source.write_text(
        "from pathlib import Path\n"
        "from fastmcp import Client\n"
        "from sqlalchemy import Engine\n"
        "from corpus_structure.semantic._operation_ids import RunId, TaskId, CutId\n"
        "from corpus_structure.semantic.types import PreparedRelease\n"
        "from semantic.agent_scenarios import build_resubmission_case, lease_and_read\n"
        "from semantic.domain_scenarios import build_domain_case\n"
        "from semantic.operation_scenario_support import prepare_operation_scenario\n"
        "from semantic.reference_scenarios import publish_reference_case\n"
        "def good(engine: Engine, path: Path) -> None:\n"
        "    prepared: PreparedRelease = prepare_operation_scenario(engine)\n"
        "    p, run, task, locator = build_resubmission_case(engine, engine, path)\n"
        "    run_id: RunId = run\n"
        "    task_id: TaskId = task\n"
        "    p2, run2, cut = build_domain_case(engine, engine, path)\n"
        "    cut_id: CutId = cut\n"
        "    publish_reference_case(engine, engine, path, 'toy', [('source', {})])\n"
        "async def good_lease(client: Client, run: RunId, task: TaskId) -> None:\n"
        "    await lease_and_read(client, run, task)\n"
    )
    executable = shutil.which("pyrefly")
    assert executable is not None
    command = [executable, "check", "--config", str(REPO / "pyproject.toml"), str(source)]
    good = subprocess.run(command, capture_output=True, text=True, check=False)
    assert good.returncode == 0, good.stdout + good.stderr
    with source.open("a") as stream:
        stream.write(
            "def bad(engine: Engine, path: Path) -> None:\n"
            "    prepare_operation_scenario(path)\n"
            "    build_resubmission_case(engine, path, engine)\n"
            "    _, run, cut = build_domain_case(engine, engine, path)\n"
            "    task: TaskId = run\n"
            "    wrong_run: RunId = cut\n"
            "async def bad_lease(client: Client, run: RunId, task: TaskId) -> None:\n"
            "    await lease_and_read(client, task, run)\n"
        )
    bad = subprocess.run(command, capture_output=True, text=True, check=False)
    output = bad.stdout + bad.stderr
    assert bad.returncode != 0
    for distinction in ("Engine", "Path", "RunId", "TaskId", "CutId"):
        assert distinction in output, output
