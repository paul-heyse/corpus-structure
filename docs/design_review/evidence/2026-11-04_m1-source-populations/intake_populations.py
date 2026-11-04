"""Existing ingest-only graph on explicitly targeted storage and a controlled service.

The exact excerpt bytes/page map are frozen before this operation. No extraction,
reference readings, grading, selected-result/default adoption or live database is used.
An owned custom-format PostgreSQL dump is retained before disposable storage closes.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from provider_canary import ENDPOINT, HERE, ROOT, SERVICE, digest, owned_service, retain

sys.path.insert(0, str(ROOT / "scripts"))


def source_context(output):
    roots = [ROOT / "python/corpus-structure/src", ROOT / "python/corpus-structure/semantic_alembic", ROOT / "domains/statistics"]
    paths = {path for root in roots for path in root.rglob("*") if path.is_file() and path.suffix in {".py", ".yaml", ".sql", ".json", ".md"}}
    paths.update(ROOT / path for path in ["pyproject.toml", "uv.lock", "scripts/native_test_support.py", "scripts/test_prerequisites.py", "scripts/native_auth.py", "services/nemotron-parse/launch.py", "services/nemotron-parse/custody.py", "services/nemotron-parse/worker.py"])
    paths.update(HERE.glob("*.py"))
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in sorted(paths)}
    archive = output / "executed-source-context.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        for path in sorted(paths):
            stream.add(path, arcname=str(path.relative_to(ROOT)))
    retain(output / "source-context.json", {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
        "clean_commit_claim": False, "file_hashes": hashes,
        "source_archive": archive.name, "source_archive_sha256": digest(archive),
    })
    (output / "working-tree.patch").write_bytes(subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT))
    return hashes


def storage_receipt(server, name, output, stage):
    from sqlalchemy import text

    with server.connect(name) as conn:
        size = conn.execute(text("SELECT pg_database_size(current_database())")).scalar_one()
    row = {"stage": stage, "database_bytes": size, "output_bytes": sum(path.stat().st_size for path in output.rglob("*") if path.is_file()), "filesystem_free_bytes": shutil.disk_usage(ROOT).free}
    retain(output / ("storage-" + stage + ".json"), row)
    print(json.dumps({"storage": row}), flush=True)


def target_settings(name):
    from corpus_structure.settings import Settings

    settings = Settings()
    return settings.model_copy(
        update={
            "database": settings.database.model_copy(
                update={"url": f"postgresql://corpus_sem_writer@/{name}?host=/var/run/postgresql&port=5434"}
            ),
            "nemotron": settings.nemotron.model_copy(update={"endpoint": ENDPOINT}),
        }
    )


def archive_database(server, name, output, native_revision):
    from sqlalchemy.engine import make_url

    path = output / "source-populations.dump"
    url = make_url(server.url_of(name)).set(drivername="postgresql").render_as_string(hide_password=False)
    command = ["pg_dump", "--dbname", url, "--format=custom", "--file", str(path)]
    result = subprocess.run(command, text=True, capture_output=True)
    retain(output / "dump-command.json", {"argv": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    result.check_returncode()
    listing = subprocess.run(["pg_restore", "--list", str(path)], text=True, capture_output=True, check=True)
    (output / "dump-contents.txt").write_text(listing.stdout)
    retain(output / "dump-manifest.json", {
        "outcome": "passed", "dump": path.name, "sha256": digest(path), "bytes": path.stat().st_size,
        "source_database": name, "native_revision": native_revision,
        "restore": ["pg_restore", "--exit-on-error", "--dbname", "<fresh-owned-empty-database-with-existing-cluster-roles>", str(path)],
        "restore_prerequisites": "Existing dedicated18/corpus roles/extensions; fresh owned empty database; do not migrate live99 or overwrite an existing project. This full dump includes schema, releases, native/source artifacts and frozen source cuts.",
        "restore_execution": "not_run; custom archive listing passed", "global_role_creation": "not included; existing cluster role owner retains authority",
    })


def detached_sources(settings, run_id, output):
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.source_views import load_source_view, selected_source_views
    from sqlalchemy import text

    sources = []
    with open_runtime_engine(settings, "m1-intake-source-freeze", purpose="read") as engine, engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        for ref in selected_source_views(conn, run_id):
            view = load_source_view(conn, ref.id, analysis=False)
            sources.append({"pin": asdict(ref), "text": view.text, "pieces": view.pieces, "items": view.items, "ancestors": view.ancestors, "health": view.health})
    encoded = json.dumps(sources, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    path = output / "selected-sources.json.gz"
    with path.open("xb") as stream:
        stream.write(gzip.compress(encoded, mtime=0))
    return {"source_views": len(sources), "analysis_views": sum(source["pin"]["analysis_eligible"] for source in sources), "path": path.name, "sha256": digest(path), "pins": [source["pin"] for source in sources]}


def execute(output, native_revision):
    initial_hashes = source_context(output)
    from native_test_support import PgAdmin, server_url
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.core.vocab import Stage
    from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated
    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.orchestrate.runner import Graph, Step
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.orchestrate.slices import records
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.migrations import current_revision, upgrade
    from corpus_structure.semantic.operations import OperationBinding
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings
    from sqlalchemy import select

    population = json.loads((HERE / "source-population.json").read_text())
    for source in population["sources"]:
        if digest(ROOT / source["excerpt"]["path"]) != source["excerpt"]["sha256"]:
            raise ValueError("Frozen excerpt differs")
    baseline = Settings()
    server = PgAdmin(server_url(baseline), baseline.database.template, settings=baseline)
    server.check()
    name = f"cs_m1_source_{os.getpid()}_{uuid4().hex[:8]}"
    settings = target_settings(name)
    report = {"scope": "Real27page source intake only; no GLiNER, reference labels, grading, knowledge-result/default adoption", "database": name, "sources": [], "outcome": "failed"}
    bundle, dependencies, profile, prepared = prepare_pack(DOMAINS / "statistics")
    retain(output / "release.json", {"release_id": prepared.release_id, "native_revision": native_revision})
    with server.database(name, server.template) as administrative:
        try:
            with administrative.begin() as conn:
                upgrade(conn, native_revision)
                if current_revision(conn) != native_revision:
                    raise RuntimeError("Fresh database differs from explicitly selected native revision")
            storage_receipt(server, name, output, "bootstrap")
            with open_runtime_engine(settings, "m1-source-archive", purpose="admit") as engine, engine.begin() as conn:
                persist_release(conn, bundle, dependencies, profile, prepared)
            analyzed = {}
            if has_authored_sql(prepared):
                with open_runtime_engine(settings, "m1-source-sql", purpose="read") as engine, engine.connect() as conn:
                    analyzed = analyze_archived_sql(conn, prepared.release_id)
            with open_runtime_engine(settings, "m1-source-admit", purpose="admit") as engine, engine.begin() as conn:
                if analyzed:
                    admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
                admit_release(prepared, connection=conn)
            with owned_service(output / "service"):
                for source in population["sources"]:
                    root = output / source["origin_group"]
                    root.mkdir()
                    project = "m1-source-" + source["origin_group"]
                    realization = f"source:{project}:{prepared.release_id}"
                    method = IngestPdfIntegrated()
                    registry = MethodRegistry([method], MethodsFile(configs={method.name: {"default": {
                        "originals": [source["excerpt"]["source_uri"]], "membership": "descendants",
                    }}}))
                    with open_runtime_engine(settings, "m1-source-register", purpose="write") as engine, engine.begin() as conn:
                        initialized = init_bound_project(conn, domain="statistics", corpus=HERE / "population-fixtures", name=project,
                            release_id=prepared.release_id, realization_id=realization, registry=registry)
                        retain(root / "project.json", initialized.model_dump(mode="json"))
                    with open_runtime_engine(settings, "m1-source-intake", purpose="write") as engine:
                        with engine.connect() as conn:
                            r, d = table("data.realization"), table("kb.document")
                            revision = conn.execute(select(r.c.data_revision).where(r.c.realization_id == realization)).scalar_one()
                            docs = conn.execute(select(d).where(d.c.project_id == project)).mappings().all()
                            corpus_record, _ = records(docs, {}, slice=None, scope=None, corpus=None)
                        started = time.monotonic()
                        run = run_source_methods(engine, project_id=project, prepared=prepared,
                            binding=OperationBinding(prepared.release_id, realization, revision, canonical_bytes({"source_population": digest(HERE / "source-population.json"), "origin": source["origin_group"]})),
                            registry=registry, graph=Graph(((Stage.INGEST, (Step("ingest.pdf_integrated/default"),)),), policy_propose=False),
                            method_settings=MethodSettings(data_dir=root / "data", model_cache=Path.home() / ".cache/docling/models", nemotron_endpoint=ENDPOINT,
                                nemotron_python=SERVICE / ".venv/bin/python", nemotron_worker=SERVICE / "worker.py", nemotron_receipts=output / "recognition", nemotron_timeout_seconds=1800),
                            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(), corpus_record=corpus_record,
                            policy_source=None, kind="full")
                    retain(root / "source-run.json", run.model_dump(mode="json"))
                    frozen = detached_sources(settings, run.run_id, root)
                    row = {"origin_group": source["origin_group"], "intended_partition": source["intended_partition"],
                           "run": run.model_dump(mode="json"), "source_freeze": frozen, "seconds": time.monotonic() - started}
                    report["sources"].append(row)
                    retain(root / "result.json", row)
                    print(json.dumps({"source": source["origin_group"], "status": run.status, "views": frozen["source_views"], "seconds": row["seconds"]}), flush=True)
                    storage_receipt(server, name, output, source["origin_group"])
            report["outcome"] = "passed"
        except BaseException as error:
            retain(output / "intake-failure.json", {"type": type(error).__name__, "message": str(error), "notes": getattr(error, "__notes__", ())})
            raise
        finally:
            archive_database(server, name, output, native_revision)
            storage_receipt(server, name, output, "archive")
            loaded = {str(Path(module.__file__).resolve().relative_to(ROOT)) for module in tuple(sys.modules.values()) if getattr(module, "__file__", None) and Path(module.__file__).resolve().is_relative_to(ROOT) and str(module.__file__).endswith(".py")}
            retain(output / "loaded-source-context.json", {"file_hashes": {path: initial_hashes.get(path) for path in sorted(loaded)}, "disk_changes_since_start": {path: digest(ROOT / path) for path in sorted(loaded) if path in initial_hashes and digest(ROOT / path) != initial_hashes[path]}})
            retain(output / "result.json", report)
    retain(output / "database-settlement.json", {"database": name, "exists_after_owned_context": server.exists(name), "dump_retained": True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--native-revision", required=True, help="Coordinator-selected qualified native revision; never implicit head")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    execute(output, args.native_revision)


if __name__ == "__main__":
    main()
