"""Bounded diagnostic projection of existing SQL batch receipts; no outcome authority."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def _artifact(directory: Path, event: dict[str, Any]) -> tuple[Path | None, str | None]:
    raw = event.get("directory")
    if not isinstance(raw, str):
        return None, None
    path = Path(raw).resolve()
    root = directory.resolve()
    if not path.is_relative_to(root):
        return None, None
    return path, path.relative_to(root).as_posix()


def _small_json(directory: Path | None, name: str) -> dict[str, Any]:
    if directory is None:
        return {}
    path = directory / name
    try:
        if path.stat().st_size > 65536:
            return {}
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except OSError, ValueError:
        return {}


def batch_summary(directory: Path, event: dict[str, Any], limit: int, after: int) -> dict[str, Any]:
    artifact, relative = _artifact(directory, event)
    report = event.get("report", {})
    if not isinstance(report, dict):
        report = {}
    expected = report.get("expected")
    if not isinstance(expected, list):
        expected = _small_json(artifact, "manifest.json").get("cases", [])
    expected = (
        [row for row in expected if isinstance(row, dict)] if isinstance(expected, list) else []
    )
    observed = report.get("observed", {})
    observed = observed if isinstance(observed, dict) else {}
    counts = Counter(row.get("status") for row in observed.values() if isinstance(row, dict))
    members = []
    for row in expected[after : after + limit]:
        result = observed.get(row.get("name"), {})
        result = result if isinstance(result, dict) else {}
        members.append(
            {
                "nodeid": str(row.get("nodeid", "unavailable")),
                "name": str(row.get("name", "unavailable")),
                "expected_assertions": row.get("assertions"),
                "observed_assertions": result.get("assertions"),
                "status": result.get("status", "not_run"),
            }
        )
    context = report.get("context")
    context = context if isinstance(context, dict) else {}
    keys = (
        "database",
        "database_oid",
        "host",
        "port",
        "current_user",
        "session_user",
        "server_started",
        "server_version",
    )
    process = report.get("process")
    process = process if isinstance(process, dict) else {}
    returncode = report.get(
        "pg_prove_returncode", _small_json(artifact, "process.json").get("returncode")
    )
    valid = report.get("valid") if isinstance(report.get("valid"), bool) else None
    return {
        "artifact_directory": relative,
        "worker": event.get("worker"),
        "pid": event.get("pid"),
        "valid": valid,
        "status": "passed" if valid else "failed" if observed or process else "incomplete",
        "expected_cases": len(expected) if expected else None,
        "expected_assertions": sum(row["assertions"] for row in expected)
        if expected and all(type(row.get("assertions")) is int for row in expected)
        else None,
        "observed_cases": len(observed),
        "passed_cases": counts["passed"],
        "failed_cases": counts["failed"],
        "pg_prove_returncode": returncode,
        "psql_exit": process.get("exit"),
        "psql_wait": process.get("wait"),
        "context": {key: context[key] for key in keys if key in context},
        "members": members,
        "members_available": len(expected),
        "members_omitted": max(0, len(expected) - len(members)),
        "next_member_after": after + len(members) if after + len(members) < len(expected) else None,
    }


def sql_batches(
    receipt: dict[str, Any], limit: int, after: int, group: str | None
) -> dict[str, Any]:
    events = receipt.get("sql_batches", [])
    if group is not None:
        nodes = {
            row["nodeid"]
            for row in receipt["scheduling"]["items"]
            if group in (row["affinity_groups"] or [])
        }
        events = [event for event in events if nodes.intersection(event.get("nodeids", []))]
    return {
        "sql_batches": [
            batch_summary(Path(receipt["directory"]), event, limit, after)
            for event in events[:limit]
        ],
        "sql_batches_available": len(events),
        "sql_batches_omitted": max(0, len(events) - limit),
    }
