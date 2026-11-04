"""Restore the retained intake dump into a fresh owned database, then read exact source pins.

No provider, extraction, reference operation or persistent default is invoked.
The original intake artifacts remain immutable; this operation writes a separate receipt.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from provider_canary import HERE, ROOT, digest, retain

sys.path.insert(0, str(ROOT / "scripts"))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intake", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.intake.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    from intake_populations import target_settings
    from native_test_support import PgAdmin, server_url
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.migrations import current_revision, upgrade
    from corpus_structure.semantic.releases import load_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.source_views import load_source_view, selected_source_views
    from corpus_structure.settings import Settings

    manifest = json.loads((source / "dump-manifest.json").read_text())
    intake = json.loads((source / "result.json").read_text())
    dump = source / manifest["dump"]
    if digest(dump) != manifest["sha256"] or dump.stat().st_size != manifest["bytes"]:
        raise ValueError("Retained dump differs")
    baseline = Settings()
    server = PgAdmin(server_url(baseline), baseline.database.template, settings=baseline)
    name = f"cs_m1_restore_{os.getpid()}_{uuid4().hex[:8]}"
    settings = target_settings(name)
    report = {"outcome": "failed", "source_dump": str(dump.relative_to(HERE)), "source_dump_sha256": manifest["sha256"], "database": name,
              "providers": "not_run", "references_or_predictions": "not_read", "runs": [], "filesystem_free_before": shutil.disk_usage(ROOT).free}
    # pg_dump without --create excludes database-level ACL/settings. Intake used
    # only the standard explicit migration bootstrap, with no additional policy
    # mutations. Reconstruct that exact bootstrap posture through the same owner,
    # then replay it with the existing database-policy owner before restoration.
    policy_name = f"cs_m1_restore_policy_{os.getpid()}_{uuid4().hex[:8]}"
    with server.database(policy_name, server.template) as policy_engine:
        with policy_engine.begin() as conn:
            upgrade(conn, manifest["native_revision"])
        policy = server.policy(policy_name)
        retain(output / "database-policy.json", {"policy": asdict(policy), "source": "Reconstructed from the same explicit native106 bootstrap and owner used by intake; original dump excludes database-level policy", "policy_database": policy_name, "native_revision": manifest["native_revision"]})
    report["policy_database_exists_after_owned_context"] = server.exists(policy_name)
    try:
        with server.database(name, server.template, policy=policy) as administrative:
            # A faithful restore replays original SECURITY DEFINER owners and ACLs.
            # The existing postgres native-maintenance identity supplies that authority
            # only inside this newly acknowledged, disposable database. No cluster role,
            # authentication row, persistent default or unrelated database is changed.
            command = ["sudo", "-n", "-u", "postgres", "env", "PGAPPNAME=m1_owned_source_restore",
                       "/usr/lib/postgresql/18/bin/pg_restore", "--exit-on-error",
                       "--host", "/var/run/postgresql", "--port", "5434", "--dbname", name, str(dump)]
            result = subprocess.run(command, text=True, capture_output=True)
            retain(output / "restore-command.json", {"argv": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            result.check_returncode()
            with administrative.connect() as conn:
                revision = current_revision(conn)
                if revision != manifest["native_revision"]:
                    raise ValueError("Restored native revision differs")
                report["native_revision"] = revision
            with open_runtime_engine(settings, "m1-restore-source-read", purpose="read") as engine, engine.connect() as conn:
                from sqlalchemy import text

                conn.execute(text("SET TRANSACTION READ ONLY"))
                report["read_only"] = conn.execute(text("SHOW transaction_read_only")).scalar_one()
                for original in intake["sources"]:
                    run = original["run"]
                    prepared = load_release(conn, run["release_id"])
                    if prepared.release_id != run["release_id"]:
                        raise ValueError("Restored release differs")
                    rt, ct = table("ops.run"), table("ops.input_cut")
                    stored_run = conn.execute(select(rt).where(rt.c.id == run["run_id"])).mappings().one()
                    cut = conn.execute(select(ct).where(ct.c.id == run["cut_id"])).mappings().one()
                    if stored_run["release_id"] != run["release_id"] or cut["run_id"] != run["run_id"]:
                        raise ValueError("Restored run/cut binding differs")
                    snapshots = []
                    for pin in selected_source_views(conn, run["run_id"]):
                        view = load_source_view(conn, pin.id, analysis=False)
                        snapshots.append({"pin": asdict(pin), "text": view.text, "pieces": view.pieces, "items": view.items, "ancestors": view.ancestors, "health": view.health})
                    expected = json.loads(gzip.decompress((source / original["origin_group"] / "selected-sources.json.gz").read_bytes()))
                    actual_hash, expected_hash = sha256(encoded(snapshots)).hexdigest(), sha256(encoded(expected)).hexdigest()
                    if actual_hash != expected_hash:
                        raise ValueError("Restored complete detached source frame differs")
                    report["runs"].append({"origin_group": original["origin_group"], "release_id": prepared.release_id,
                        "run_id": run["run_id"], "cut_id": run["cut_id"], "run_status": stored_run["status"],
                        "source_view_pins": [snapshot["pin"] for snapshot in snapshots], "source_frames_sha256": actual_hash,
                        "expected_source_frames_sha256": expected_hash, "source_views": len(snapshots), "source_frame_identity": "passed"})
            report["outcome"] = "passed"
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report["database_exists_after_owned_context"] = server.exists(name)
        report["filesystem_free_after"] = shutil.disk_usage(ROOT).free
        retain(output / "result.json", report)
    print(json.dumps({"outcome": report["outcome"], "runs": len(report["runs"]), "source_views": sum(run["source_views"] for run in report["runs"]), "database_disposed": not report["database_exists_after_owned_context"]}), flush=True)


if __name__ == "__main__":
    main()
