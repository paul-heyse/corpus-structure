"""Run the configured automated extractor against a fresh, run-bound stdio MCP server."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.settings import Settings


class AutomatedExtraction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int
    model: str
    provider: str = "claude-cli"
    provider_session: str | None
    terminal_tasks: int


def extract_run(
    engine: Engine,
    settings: Settings,
    run_id: int,
    *,
    timeout: float = 1800,
) -> AutomatedExtraction | None:
    """No reference credentials, filesystem tools or inherited MCP servers enter extraction.

    Interruption leaves native run/task/attempt identities intact. The caller resumes this run;
    native claim/reclaim owns retries, and this process adds no retry loop.
    """
    tasks, configs, methods = table("ops.task"), table("ops.method_config"), table("ops.method")
    with engine.connect() as conn:
        states = list(
            conn.execute(select(tasks.c.status).where(tasks.c.run_id == run_id)).scalars()
        )
        if not any(state in {"pending", "running", "awaiting_agent"} for state in states):
            return None
        models = [
            row.get("model")
            for row in conn.execute(
                select(configs.c.params)
                .join(tasks, tasks.c.method_config_id == configs.c.id)
                .join(methods, configs.c.method_id == methods.c.id)
                .where(
                    tasks.c.run_id == run_id,
                    methods.c.name == "agent.opus",
                    tasks.c.status != "skipped",
                )
            ).scalars()
        ]
    declared = set(models)
    if len(declared) != 1 or None in declared:
        raise OperationConflict("automated extraction requires one explicitly configured model")
    model = declared.pop()
    assert isinstance(model, str)
    command = shutil.which("claude")
    uv = shutil.which("uv")
    if command is None or uv is None:
        raise OperationConflict("automated extraction requires authenticated claude CLI and uv")
    root = Path(__file__).resolve().parents[5]
    allowed = [
        f"mcp__corpus__{name}"
        for name in (
            "queue_status",
            "queue_next",
            "read_unit",
            "inspect_source",
            "render_source_region",
            "read_instructions",
            "propose_claims",
            "release",
        )
    ]
    prompt = (
        f"Complete all pending extraction work for semantic run {run_id} "
        "using only corpus MCP tools. "
        "Read server instructions, lease one unit at a time, "
        "read ALL instruction pages and unit parts, "
        "and submit a source-grounded authored batch matching the exact supplied schema. "
        "Correct held "
        "submissions from their feedback. "
        "Preserve negative statements, missingness, qualifications, "
        "exact values and cited sentence anchors. For native PDF units, retain supplied section, "
        "item, table/cell, formula and region identities. Cite a supplied native_evidence handle for "
        "exact item, formula or cell text; its offsets are projection coordinates. Inspect pinned native_source evidence when needed "
        "and optionally render_source_region for a cited figure or formula; "
        "recognition health and inferred domain labels are observations, not established mathematical facts. "
        "Do not invent facts or read reference answers. "
        "Continue until queue_next returns no tasks; report any refusal honestly."
    )
    with tempfile.TemporaryDirectory(prefix="corpus-semantic-agent-") as directory:
        config = Path(directory) / "mcp.json"
        config.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "corpus": {
                            "command": uv,
                            "args": [
                                "--directory",
                                str(root),
                                "run",
                                "--no-sync",
                                "--project",
                                str(root / "python/corpus-structure"),
                                "ci",
                                "mcp",
                                "serve",
                                "--semantic-run",
                                str(run_id),
                            ],
                            "env": {"CORPUS_DATABASE__URL": settings.database.url},
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        config.chmod(0o600)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("CORPUS_") and key not in {"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"}
        }
        process = subprocess.Popen(
            [
                command,
                "-p",
                prompt,
                "--model",
                model,
                "--output-format",
                "json",
                "--tools",
                "",
                "--strict-mcp-config",
                "--mcp-config",
                str(config),
                "--permission-mode",
                "dontAsk",
                "--allowedTools",
                *allowed,
                "--no-session-persistence",
                "--max-turns",
                "120",
                "--restricted",
                "--disable-slash-commands",
                "--setting-sources",
                "",
                "--settings",
                json.dumps(
                    {
                        "disableAllHooks": True,
                        "claudeMdExcludes": ["**"],
                        "autoMemoryEnabled": False,
                    }
                ),
            ],
            cwd=directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise OperationConflict(
                f"automated provider timed out for run {run_id}; resume this run"
            ) from error
        finally:
            # The fresh provider and all stdio MCP descendants belong to this process group.
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
    if process.returncode:
        raise OperationConflict(
            f"automated provider failed for run {run_id}: {stderr[-2000:] or stdout[-2000:]}"
        )
    response = json.loads(stdout)
    if response.get("is_error"):
        raise OperationConflict(
            f"automated provider refused run {run_id}: {response.get('result')}"
        )
    with engine.connect() as conn:
        states = list(
            conn.execute(
                select(tasks.c.status)
                .join(configs, tasks.c.method_config_id == configs.c.id)
                .join(methods, configs.c.method_id == methods.c.id)
                .where(tasks.c.run_id == run_id, methods.c.name == "agent.opus")
            ).scalars()
        )
    if any(state in {"pending", "running", "awaiting_agent"} for state in states):
        raise OperationConflict(
            f"automated provider left tasks open in run {run_id}; resume this run"
        )
    if not any(state in {"done", "empty", "reused"} for state in states):
        raise OperationConflict("automated provider completed no source task")
    return AutomatedExtraction(
        run_id=run_id,
        model=model,
        provider_session=response.get("session_id"),
        terminal_tasks=sum(state in {"done", "empty", "reused"} for state in states),
    )
