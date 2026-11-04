"""Run the configured automated extractor against a fresh, run-bound stdio MCP server."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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
    receipt_dir: str


_RAW_LIMIT = 32 * 1024 * 1024


def _provider_environment():
    return {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("CORPUS_", "PG", "DATABASE", "UV"))
        and key.upper() not in {"BASH_ENV", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "PWD", "OLDPWD"}
    }


def _capture_pipe(pipe, path, state):
    """Drain a provider pipe while bounding retained raw bytes independently of output size."""
    count = 0
    try:
        with pipe, path.open("xb") as target:
            while chunk := pipe.read(65536):
                remaining = max(0, _RAW_LIMIT - count)
                target.write(chunk[:remaining])
                count += len(chunk)
        state.update(
            bytes=count, retained_bytes=min(count, _RAW_LIMIT), truncated=count > _RAW_LIMIT
        )
    except BaseException as error:
        state.update(bytes=count, capture_error=repr(error))


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
    from corpus_structure.methods.llm.producer import SUPPORTED_PRODUCERS, producer_binding

    tasks, configs, methods = table("ops.task"), table("ops.method_config"), table("ops.method")
    with engine.connect() as conn:
        states = list(
            conn.execute(select(tasks.c.status).where(tasks.c.run_id == run_id)).scalars()
        )
        if not any(state in {"pending", "running", "awaiting_agent"} for state in states):
            return None
        bindings = [
            producer_binding(row["method"], row["params"], method_version=row.get("method_version"))
            for row in conn.execute(
                select(
                    configs.c.params,
                    methods.c.name.label("method"),
                    methods.c.version.label("method_version"),
                )
                .join(tasks, tasks.c.method_config_id == configs.c.id)
                .join(methods, configs.c.method_id == methods.c.id)
                .where(
                    tasks.c.run_id == run_id,
                    methods.c.name.in_(SUPPORTED_PRODUCERS),
                    tasks.c.status != "skipped",
                )
            ).mappings()
        ]
        models = [binding.configured_model for binding in bindings]
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
            "find",
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
        "item, table/cell, formula and region identities. Cite a supplied "
        "native_evidence handle for "
        "exact item, formula or cell text; its offsets are projection coordinates. "
        "Inspect pinned native_source evidence when needed and optionally render_source_region "
        "for a cited figure or formula. "
        "For supplied ancestor context, cite its native_context:<source_view_id>:<local_id> handle "
        "and exact source text; those offsets and locators belong to that "
        "ancestor, never the child unit. "
        "Recognition health and inferred domain labels are observations, not "
        "established mathematical facts. "
        "Do not invent facts or read reference answers. "
        "Continue until queue_next returns no tasks; report any refusal honestly."
    )
    with tempfile.TemporaryDirectory(prefix="corpus-semantic-agent-") as directory:
        receipt = (
            settings.paths.data_dir
            / "automated-extraction"
            / f"run-{run_id}"
            / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:12])
        )
        receipt.mkdir(parents=True, mode=0o700, exist_ok=False)
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
                            "env": {
                                "CORPUS_DATABASE__URL": settings.database.url,
                                "CORPUS_AGENT_INVOCATION_ID": receipt.name,
                                "CORPUS_AGENT_RECEIPTS": str(receipt.resolve()),
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        config.chmod(0o600)
        environment = _provider_environment()
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
            start_new_session=True,
        )
        stdout_state, stderr_state = {}, {}
        readers = [
            threading.Thread(
                target=_capture_pipe, args=(process.stdout, receipt / "stdout.json", stdout_state)
            ),
            threading.Thread(
                target=_capture_pipe, args=(process.stderr, receipt / "stderr.log", stderr_state)
            ),
        ]
        for reader in readers:
            reader.start()
        failure = None
        try:
            process.wait(timeout=timeout)
        except BaseException as error:
            failure = error
        finally:
            # All provider and stdio MCP descendants belong to this owned process group.
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            for reader in readers:
                reader.join()
            (receipt / "invocation.json").write_text(
                json.dumps(
                    dict(
                        run_id=run_id,
                        configured_model=model,
                        model=model,
                        assurance="provider_reported",
                        producer_bindings=[binding.values() for binding in bindings],
                        invocation_id=receipt.name,
                        returncode=process.returncode,
                        process_outcome="interrupted"
                        if failure is not None
                        else "completed"
                        if process.returncode == 0
                        else "failed",
                        error=None if failure is None else repr(failure),
                        stdout=stdout_state,
                        stderr=stderr_state,
                    ),
                    indent=2,
                )
                + "\n"
            )
        if failure is not None:
            if isinstance(failure, subprocess.TimeoutExpired):
                raise OperationConflict(
                    f"automated provider timed out for run {run_id}; resume this run; "
                    f"raw receipts: {receipt}"
                ) from failure
            failure.add_note(f"automated extraction raw receipts: {receipt}")
            raise failure
        if any(
            state.get("truncated") or "capture_error" in state
            for state in (stdout_state, stderr_state)
        ):
            raise OperationConflict(
                "automated provider output exceeded its raw receipt bound "
                "or could not be captured; "
                f"raw receipts: {receipt}"
            )
        stdout = (receipt / "stdout.json").read_text()
        stderr = (receipt / "stderr.log").read_text()
    if process.returncode:
        raise OperationConflict(
            f"automated provider failed for run {run_id}: {stderr[-2000:] or stdout[-2000:]}; "
            f"raw receipts: {receipt}"
        )
    try:
        response = json.loads(stdout)
    except ValueError as error:
        raise OperationConflict(
            f"automated provider returned invalid JSON; raw receipts: {receipt}"
        ) from error
    if not isinstance(response, dict):
        raise OperationConflict(
            f"automated provider JSON must be an object; raw receipts: {receipt}"
        )
    if response.get("is_error"):
        raise OperationConflict(
            f"automated provider refused run {run_id}: {response.get('result')}; "
            f"raw receipts: {receipt}"
        )
    metadata = json.loads((receipt / "invocation.json").read_text())
    metadata.update(
        provider_session=response.get("session_id"),
        provider_reported_model=response.get("model"),
        provider_reported_model_usage=response.get("modelUsage"),
        reported_identity_available=(
            isinstance(response.get("model"), str) or isinstance(response.get("modelUsage"), dict)
        ),
    )
    (receipt / "invocation.json").write_text(json.dumps(metadata, indent=2) + "\n")
    with engine.connect() as conn:
        states = list(
            conn.execute(
                select(tasks.c.status)
                .join(configs, tasks.c.method_config_id == configs.c.id)
                .join(methods, configs.c.method_id == methods.c.id)
                .where(tasks.c.run_id == run_id, methods.c.name.in_(SUPPORTED_PRODUCERS))
            ).scalars()
        )
    if any(state in {"pending", "running", "awaiting_agent"} for state in states):
        raise OperationConflict(
            f"automated provider left tasks open in run {run_id}; resume this run; "
            f"raw receipts: {receipt}"
        )
    if not any(state in {"done", "empty", "reused"} for state in states):
        raise OperationConflict(
            f"automated provider completed no source task; raw receipts: {receipt}"
        )
    return AutomatedExtraction(
        run_id=run_id,
        model=model,
        provider_session=response.get("session_id"),
        terminal_tasks=sum(state in {"done", "empty", "reused"} for state in states),
        receipt_dir=str(receipt),
    )
