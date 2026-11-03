"""Actual authenticated CLI -> run-bound MCP -> native attempt completion probe."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

DEFAULT_CHECKOUT = Path(__file__).resolve().parents[4]


def run(checkout: Path = DEFAULT_CHECKOUT, receipts: Path | None = None):
    checkout = checkout.resolve()
    sys.path[:0] = [str(checkout / "scripts"), str(checkout / "python/corpus-structure/tests")]
    from sqlalchemy import text

    from conftest import settings_for_native_clone
    from native_test_support import PgAdmin, principal_engine, semantic_principals, server_url
    from semantic.agent_scenarios import build_resubmission_case

    from corpus_structure.intervene.automated import extract_run
    from corpus_structure.semantic import operations
    from corpus_structure.settings import Settings

    imported = Path(operations.__file__).resolve()
    if not imported.is_relative_to(checkout):
        raise RuntimeError(f"wrong import provenance: {imported} is outside {checkout}")
    context = {
        "checkout": str(checkout), "operations_import": str(imported),
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
        ).strip(),
    }
    receipts = receipts or Path(__file__).resolve().parent / "runtime"
    receipt_root = (receipts.resolve() /
                    ("attempt-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]))
    receipt_root.mkdir(parents=True, exist_ok=True)
    status = json.loads(subprocess.check_output(["claude", "auth", "status"], text=True))
    readiness = {key: status.get(key) for key in (
        "loggedIn", "authMethod", "apiProvider", "subscriptionType"
    )}
    readiness.update(at=datetime.now(UTC).isoformat(),
                     version=subprocess.check_output(["claude", "--version"], text=True).strip())
    (receipt_root / "readiness.json").write_text(json.dumps(readiness, indent=2) + "\n")
    if not readiness["loggedIn"]:
        raise RuntimeError("actual automated extraction requires authenticated Claude CLI")
    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    server.check()
    server.check_roles(semantic_principals())
    suffix = f"{os.getpid()}_{uuid4().hex[:10]}"
    result = {"outcome": "failed", "at": datetime.now(UTC).isoformat(), "source_context": context}
    try:
        with server.semantic_template("cs_sem_head_" + suffix) as template:
            with server.database("cs_sem_test_" + suffix, template.name, policy=template.policy) as admin:
                writer = principal_engine(settings, "write", admin.url.database)
                try:
                    prepared, run_id, task_id, locator = build_resubmission_case(
                        admin, writer, receipt_root / "source.pdf", model="opus"
                    )
                    target = settings_for_native_clone(settings, admin.url.database)
                    target = target.model_copy(update={"paths": target.paths.model_copy(update={
                        "data_dir": receipt_root / "application"
                    })})
                    result.update(run_id=run_id, task_id=task_id, release_id=prepared.release_id,
                                  source_view=locator, configured_model="opus")
                    automated = extract_run(writer, target, run_id, timeout=480)
                    if automated is None:
                        raise AssertionError("actual provider invocation was not attempted")
                    result["automation"] = automated.model_dump(mode="json")
                    invocation = Path(automated.receipt_dir)
                    leased = [json.loads(path.read_text()) for path in invocation.glob("*leased-*.json")]
                    completed = [json.loads(path.read_text()) for path in invocation.glob("*completed-*.json")]
                    assert len(leased) == len(completed) == 1
                    assert leased[0]["producer_binding"] == completed[0]["producer_binding"]
                    assert completed[0]["producer_binding"]["configured_model"] == "opus"
                    assert completed[0]["receipt"]["task_id"] == task_id
                    assert completed[0]["receipt"]["attempt"] == completed[0]["attempt"]
                    with admin.connect() as conn:
                        result["task"] = dict(conn.execute(text(
                            "SELECT id,attempt,claimed_by,status,result_digest FROM ops.task WHERE id=:id"
                        ), {"id":task_id}).mappings().one())
                        result["observations"] = [dict(row) for row in conn.execute(text(
                            "SELECT observation_key,kind,outcome,payload FROM kb.observation WHERE task_id=:id"
                        ), {"id":task_id}).mappings()]
                    assert result["task"]["status"] in {"done", "empty"}
                    assert result["task"]["attempt"] > 0
                    assert result["task"]["result_digest"]
                    result["outcome"] = "passed"
                finally:
                    writer.dispose()
    except BaseException as error:
        result["error"] = repr(error)
        raise
    finally:
        (receipt_root / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
        print(json.dumps({key:result[key] for key in ("outcome", "run_id", "task_id", "error") if key in result}))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=DEFAULT_CHECKOUT)
    parser.add_argument("--receipts", type=Path)
    arguments = parser.parse_args()
    run(arguments.checkout, arguments.receipts)
