"""Actual authenticated extraction -> protected knowledge -> pinned CLI/MCP/export.

The PDF and Person/name release are controlled fixtures. Actual provider extraction,
native admission/consolidation, generic query adapters and export are not mocked.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

DEFAULT_CHECKOUT = Path(__file__).resolve().parents[5]


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
                    from corpus_structure.schema.pack import DOMAINS
                    from corpus_structure.semantic.query_compatibility import (
                        acquire_query_inputs, open_query_registry,
                    )

                    prepared, run_id, task_id, locator = build_resubmission_case(
                        admin, writer, receipt_root / "source.pdf", model="opus",
                        domain="statistics", query_inputs=acquire_query_inputs(DOMAINS / "statistics"),
                    )
                    # Only generic release-relative queries are exercised. This is not a
                    # statistics-schema extraction or a scientific-accuracy claim.
                    for name in ("claims", "evidence"):
                        query = open_query_registry(prepared, DOMAINS / "statistics", query_name=name)[name]
                        assert query.release_id == prepared.release_id
                        assert query.implementation == query.producing_implementation
                    result["fixture_scope"] = {
                        "schema": "https://example.org/resubmit; Person/name",
                        "controlled_source": "Alice is here.",
                        "query_pack": "statistics",
                        "query_semantics": "generic release-relative claims/evidence",
                        "source_intake": "controlled PDF publication, not managed recognition",
                    }
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
                    from dataclasses import asdict
                    from corpus_structure.orchestrate.commands import finalize_bound_run

                    finalized = finalize_bound_run(writer, run_id, "ac14-provider-knowledge")
                    result["finalization"] = asdict(finalized)
                    result["consumers"] = exercise_consumers(
                        admin, writer, target, prepared, run_id, task_id, receipt_root
                    )
                    result["outcome"] = "passed"
                finally:
                    writer.dispose()
    except BaseException as error:
        result["error"] = repr(error)
        raise
    finally:
        (receipt_root / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
        print(json.dumps({key:result[key] for key in ("outcome", "run_id", "task_id", "error") if key in result}))


def exercise_consumers(admin, writer, settings, prepared, run_id, task_id, receipts):
    """Use real CLI adapters and the registered MCP source tool on one native result."""
    import anyio
    from fastmcp import Client
    from sqlalchemy import text
    from typer.testing import CliRunner

    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState
    from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server

    def cli(label, arguments):
        call = CliRunner().invoke(app, arguments, obj=CliState(lambda: settings))
        (receipts / f"{label}.stdout").write_text(call.stdout)
        (receipts / f"{label}.stderr").write_text(call.stderr)
        (receipts / f"{label}.command.json").write_text(json.dumps({
            "argv": ["ci", *arguments], "exit_code": call.exit_code,
            "exception": repr(call.exception) if call.exception else None,
            "entrypoint": "actual Typer app via CliRunner; real purpose-authenticated database",
        }, indent=2) + "\n")
        assert call.exit_code == 0, (label, call.stdout, call.stderr, repr(call.exception))
        return json.loads(call.stdout)

    def semantic_pin(binding):
        # Independent read_snapshot captures get distinct UUIDs by contract. Their
        # immutable completed-result identity remains release/realization/revision.
        assert binding["capture_id"]
        return tuple(binding[key] for key in ("release_id", "realization_id", "data_revision"))

    common = ["--run", str(run_id), "--project", "resubmit", "--json"]
    claims = cli("claims", ["query", "claims", "--projection", "occurrence", *common])
    accepted = cli("accepted", ["query", "claims", "--projection", "accepted", *common])
    assert claims["rows"], "provider produced no admitted source claim"
    assert accepted["rows"], "no governed accepted knowledge was published"
    assert claims["run_id"] == accepted["run_id"] == run_id
    assert semantic_pin(claims["binding"]) == semantic_pin(accepted["binding"])
    assert claims["cut_id"] == accepted["cut_id"]
    for response in (claims, accepted):
        assert all(row["fact"]["standing"]["release_id"] == response["binding"]["release_id"]
                   for row in response["rows"])
    # Structural assignments can legitimately lack source assertion evidence. Select an
    # actual provider-backed accepted assertion rather than treating structural metadata
    # as extracted support. Keep every attempted evidence query for inspection.
    selected = None
    for index, row in enumerate(accepted["rows"]):
        fact_id = row["fact"]["fact_id"]
        evidence = cli(f"evidence-{index}", ["query", "evidence", "--param", f"key={fact_id}", *common])
        assert semantic_pin(evidence["binding"]) == semantic_pin(claims["binding"])
        assert evidence["run_id"] == run_id and evidence["cut_id"] == claims["cut_id"]
        for item in evidence["rows"]:
            source = item["evidence"]["source"]
            if source is not None and source["task_id"] == task_id:
                selected = fact_id, evidence, source
                break
        if selected is not None:
            break
    assert selected is not None, "no accepted provider assertion resolves to source evidence"
    fact_id, evidence, source = selected
    assert source["task_id"] == task_id and source["run_id"] == run_id
    assert source["native_address"].startswith("pdf:")
    assert source["source_view_id"] is not None
    with admin.connect() as conn:
        view = dict(conn.execute(text("""
            SELECT native_task_id, native_product_key, native_content_digest,
                   section_pointer, membership, projection_digest
            FROM kb.source_view WHERE id=:view
        """), {"view": source["source_view_id"]}).mappings().one())
        observation_keys = set(conn.execute(text(
            "SELECT observation_key FROM kb.observation WHERE task_id=:task"
        ), {"task": task_id}).scalars())
    assert source["observation_key"] in observation_keys
    request = dict(version=4, run_id=run_id, task_id=view["native_task_id"],
                   product_key=view["native_product_key"],
                   content_digest=view["native_content_digest"], view="items",
                   section_pointer=view["section_pointer"], membership=view["membership"])

    async def inspect():
        async with Client(build_semantic_server(SemanticAgentSession(writer, run_id))) as client:
            response = await client.call_tool("inspect_source", {"request": request})
            assert not response.is_error
            body = response.structured_content
            assert body is not None and body["outcome"] == "source_ready"
            assert all(body["selection"][key] == value for key, value in request.items())
            assert body["release_id"] == prepared.release_id
            assert body["selection"]["content_digest"] == view["native_content_digest"]
            assert body["rows"]
            (receipts / "mcp-inspect-source.json").write_text(json.dumps(body, indent=2) + "\n")
            return body

    inspected = anyio.run(inspect)
    exported = cli("export", ["export", "--out", str(receipts / "export"),
                              "--format", "jsonl", *common])
    manifest = exported["manifest"]
    assert semantic_pin(manifest["binding"]) == semantic_pin(claims["binding"])
    facts = [json.loads(line) for line in (receipts / "export" /
             manifest["relations"]["fact"]["file"]).read_text().splitlines()]
    assert fact_id in {row["fact_id"] for row in facts}
    return dict(binding=claims["binding"], captures={
                    "occurrence": claims["binding"], "accepted": accepted["binding"],
                    "evidence": evidence["binding"], "export": manifest["binding"],
                }, run_id=run_id, cut_id=claims["cut_id"],
                fact_id=fact_id, observation_key=source["observation_key"],
                source_view_id=source["source_view_id"], native_product=request,
                projection_digest=view["projection_digest"],
                claim_count=len(claims["rows"]), accepted_count=len(accepted["rows"]),
                evidence_count=len(evidence["rows"]), inspected_rows=len(inspected["rows"]),
                exported_fact_count=len(facts), export_format=manifest["format"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=DEFAULT_CHECKOUT)
    parser.add_argument("--receipts", type=Path)
    arguments = parser.parse_args()
    run(arguments.checkout, arguments.receipts)
