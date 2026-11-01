"""Explicit exact-witness storage derivation; does not run recognition or finalize knowledge.

Run only after deploying the reviewed semantic_0065 implementation. The output checkpoint
owns one migration task; rerun with the same arguments to resume its private/frozen build.
All database changes go through current production preparation and source-operation APIs.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.provenance import code_commit
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated, PdfIntegratedIngestConfig
from corpus_structure.orchestrate.pdf_streaming import migrate_retained_pdf_envelope, resume_pdf_publication
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.execution_admission import admit_execution_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding, binding_of, claim_tasks, create_run, create_task,
    read_original, record_method, run_view, start_run,
)
from corpus_structure.semantic.pdf_contracts import pdf_context_for_task, store_pdf_original
from corpus_structure.semantic.pdf_publication import inspect_pdf_build, published_pdf_revision
from corpus_structure.semantic.pdf_records import native_validation_contract
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import activation_token, activate_release, load_release, persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "pdf-docling-adoption"
TASK = 86
ENVELOPE_SHA256 = "c8f19ca1703206e9007b416eecb7c0d286de57d7ce82b006a605335efe7da524"
SOURCE_SHA256 = "e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9"
RECIPE_SHA256 = "040c2c4eeab8fa48dee0612dee6c72536b672b5978590454c96528718fce24bf"
DEFAULT_WITNESS = Path("docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-prepared.json.gz")


def retain(path: Path, value: Any) -> None:
    """Atomic local checkpoint; existing attempts/errors remain in the append-only journal."""
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2, default=str) + "\n")
    temporary.replace(path)


def derived_recipe_digest(recipe: bytes) -> str:
    profile = native_validation_contract()["retained_serialization_projection"]["profile"]
    return sha256(canonical_bytes({
        "recipe_id": "retained-pdf-record-derivation-v1",
        "source_recipe_sha256": sha256(recipe).hexdigest(),
        "source_envelope_sha256": ENVELOPE_SHA256,
        "native_projection_profile": profile,
    })).hexdigest()


def execute(args: argparse.Namespace) -> None:
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "checkpoint.json"
    settings = Settings()
    settings = settings.model_copy(update={"database": settings.database.model_copy(update={"url": args.database})})
    state: dict[str, Any] = json.loads(checkpoint.read_bytes()) if checkpoint.exists() else {}
    if state and state["database"] != args.database:
        raise ValueError("checkpoint belongs to another database")
    witness = args.witness.resolve(strict=True)
    if state and state["witness"] != str(witness):
        raise ValueError("checkpoint belongs to another retained witness")
    method = IngestPdfIntegrated()
    try:
        with open_runtime_engine(settings, "pdf-retained-inspect", purpose="read") as engine:
            with engine.connect() as conn, conn.begin():
                conn.exec_driver_sql("SET TRANSACTION READ ONLY")
                available = conn.execute(text("""
                    SELECT to_regclass('ops.pdf_published_revision') IS NOT NULL
                       AND to_regprocedure('ops.seal_pdf_build(text,bigint,bigint,text,text,text)') IS NOT NULL
                """)).scalar_one()
                if not available:
                    raise ValueError("requires reviewed semantic_0065 deployment; publication API absent")
                # Availability alone is not admission. Current production admission below
                # verifies the exact native implementation before any source execution.
                source = dict(conn.execute(text("""
                    SELECT t.run_id,t.unit_type,m.params,b.recipe_digest,d.source_uri,
                           d.original_path,d.content_hash,d.title,d.meta
                    FROM ops.task t JOIN ops.method_config m ON m.id=t.method_config_id
                    JOIN ops.source_build b ON b.task_id=t.id
                    JOIN kb.document d ON d.id=t.unit_id WHERE t.id=:task
                """), {"task": TASK}).mappings().one())
                if source["run_id"] != 13 or source["unit_type"] != "document" or source["content_hash"] != SOURCE_SHA256:
                    raise ValueError("retained task source identity differs")
        cfg = PdfIntegratedIngestConfig.model_validate(source["params"])
        if cfg.integrated_product is not None or cfg.native_product is None:
            raise ValueError("task86 requires its original declared structural input")
        recipe = method.original_recipe(cfg)
        if sha256(recipe).hexdigest() != source["recipe_digest"] or source["recipe_digest"] != RECIPE_SHA256:
            raise ValueError("actual task86 method configuration no longer denotes retained recipe")
        original_path = Path(source["original_path"]).resolve(strict=True)
        original = original_path.read_bytes()
        if sha256(original).hexdigest() != SOURCE_SHA256:
            raise ValueError("original PDF bytes differ")
        schema_bytes = files("corpus_structure").joinpath("model/semantic/docling-validation.schema.json").read_bytes()
        schema_digest = sha256(schema_bytes).hexdigest()
        stage_recipe_digest = derived_recipe_digest(recipe)
        retain(output / "retained-inputs.json", {
            "source_task": TASK, "source_run": 13, "source": source,
            "serialization_sha256": ENVELOPE_SHA256, "stage_recipe_sha256": stage_recipe_digest,
            "schema_sha256": schema_digest,
        })
        if args.inspect_only:
            print(json.dumps({"outcome": "inspected_read_only", "source_task": TASK,
                "source_digest": SOURCE_SHA256, "recipe_digest": RECIPE_SHA256,
                "stage_recipe_digest": stage_recipe_digest, "schema_digest": schema_digest}), flush=True)
            return
        if not state:
            bundle, dependencies, profile, prepared = prepare_pack(DOMAINS / "statistics")
            with open_runtime_engine(settings, "pdf-retained-archive", purpose="admit") as engine, engine.begin() as conn:
                persist_release(conn, bundle, dependencies, profile, prepared)
            analyzed = {}
            if has_authored_sql(prepared):
                with open_runtime_engine(settings, "pdf-retained-sql", purpose="read") as engine, engine.connect() as conn:
                    analyzed = analyze_archived_sql(conn, prepared.release_id)
            with open_runtime_engine(settings, "pdf-retained-admit", purpose="admit") as engine, engine.begin() as conn:
                if analyzed:
                    admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
                admit_execution_release(prepared, connection=conn)
                admit_release(prepared, connection=conn)
            realization = f"source:{PROJECT}:{prepared.release_id}"
            corpus = original_path
            for _part in Path(source["source_uri"]).parts:
                corpus = corpus.parent
            with open_runtime_engine(settings, "pdf-retained-project", purpose="write") as engine, engine.begin() as conn:
                init_bound_project(conn, domain="statistics", corpus=corpus, name=PROJECT,
                                   release_id=prepared.release_id, realization_id=realization)
            with open_runtime_engine(settings, "pdf-retained-activate", purpose="admit") as engine, engine.begin() as conn:
                token = activation_token(conn, PROJECT)
                if token.release_id != prepared.release_id:
                    activate_release(conn, PROJECT, prepared.release_id, expected_parent=token.release_id,
                                     expected_generation=token.generation, sql_admissions=analyzed)
            with open_runtime_engine(settings, "pdf-retained-task", purpose="write") as engine, engine.begin() as conn:
                realization_table = table("data.realization")
                revision = conn.execute(select(realization_table.c.data_revision).where(
                    realization_table.c.realization_id == realization)).scalar_one()
                binding = OperationBinding(prepared.release_id, realization, revision, canonical_bytes({
                    "domain": "statistics", "retained_source_task": TASK,
                    "source_envelope_sha256": ENVELOPE_SHA256, "stage_recipe_sha256": stage_recipe_digest,
                }))
                run_id = create_run(conn, project_id=PROJECT, binding=binding, kind="ingest",
                                    options={"scope": None, "purpose": "retained-pdf-storage-derivation"},
                                    code_commit=code_commit())
                start_run(conn, run_id)
                config_id = record_method(conn, method, "retained-book-task86", source["params"],
                    config_key(method.name, method.version, source["params"]), prepared=prepared)
                documents = table("kb.document")
                document = conn.execute(select(documents).where(documents.c.project_id == PROJECT,
                    documents.c.source_uri == source["source_uri"], documents.c.content_hash == SOURCE_SHA256)).mappings().one()
                ref = UnitRef(TaskUnitType.DOCUMENT, document["id"], document["key"])
                digest = method.input_digest(UnitView(ref, run_view(conn, run_id, prepared), document_id=document["id"]), cfg)
                input_hash = sha256(canonical_bytes([prepared.release_id, realization, revision,
                    binding.dependency_digest, method.name, method.version,
                    config_key(method.name, method.version, source["params"]), digest.bytes.hex()])).hexdigest()
                task_id = create_task(conn, run_id=run_id, config_id=config_id, stage="ingest",
                    unit_type="document", unit_id=ref.unit_id, unit_key=ref.unit_key,
                    input_hash=input_hash, packet_hash=digest.packet_hash, fresh=True)
            state = {"database": args.database, "witness": str(witness), "run_id": run_id,
                     "task_id": task_id, "config_id": config_id, "release_id": prepared.release_id,
                     "stage_recipe_digest": stage_recipe_digest, "schema_digest": schema_digest}
            retain(checkpoint, state)
        if state["stage_recipe_digest"] != stage_recipe_digest or state["schema_digest"] != schema_digest:
            raise ValueError("checkpoint's immutable derivation inputs changed")
        with open_runtime_engine(settings, "pdf-retained-migrate", purpose="write") as engine:
            if "published" in state:
                with engine.connect() as conn:
                    archived = published_pdf_revision(conn, state["task_id"], "integrated",
                                                     state["published"]["logical_digest"])
                    if archived is None or asdict(archived) != state["published"]:
                        raise ValueError("checkpoint publication no longer matches protected revision")
                print(json.dumps({"outcome": "published_replay", **asdict(archived)}), flush=True)
                return
            holder = f"retained-book-migration:{state['task_id']}"
            with engine.begin() as conn:
                prepared = load_release(conn, state["release_id"])
                binding = binding_of(conn, state["run_id"])
                if binding.release_id != prepared.release_id:
                    raise ValueError("checkpoint release differs from actual run")
                claims = claim_tasks(conn, run_id=state["run_id"], config_id=state["config_id"], holder=holder)
                if len(claims) != 1 or claims[0].task_id != state["task_id"]:
                    raise ValueError("migration task not claimable; preserve checkpoint and wait for existing lease expiry")
                claim = claims[0]
                if claim.unit_id is None or claim.unit_type != TaskUnitType.DOCUMENT:
                    raise ValueError("migration claim lost its document identity")
                actual = read_original(conn, claim.unit_id, prepared=prepared)
                if actual != original:
                    raise ValueError("new task original custody differs")
                store_pdf_original(conn, task_id=claim.task_id, attempt=claim.attempt,
                                   holder=holder, original=original, recipe_bytes=recipe)
                if pdf_context_for_task(conn, claim.task_id).native_schema_digest != schema_digest:
                    raise ValueError("new task native schema differs")
                existing = inspect_pdf_build(conn, task_id=claim.task_id, attempt=claim.attempt,
                    holder=holder, replay_key="product:integrated")
            if existing is not None and (existing.frozen is not None or existing.published is not None):
                with maintained_claims(engine, [claim], holder) as check_active:
                    published = resume_pdf_publication(engine, claim, holder, product_key="integrated",
                        source_digest=SOURCE_SHA256, recipe_digest=stage_recipe_digest,
                        schema_digest=schema_digest, kind="integrated", check_active=check_active)
            else:
                published = migrate_retained_pdf_envelope(engine, claim, holder, path=witness,
                    expected_sha256=ENVELOPE_SHA256, original=original, schema_bytes=schema_bytes,
                    recipe_bytes=recipe, directory=output / "private", kind="integrated")
            retain(output / "published.json", asdict(published))
            retain(checkpoint, {**state, "published": asdict(published)})
            print(json.dumps({"outcome": "published", **asdict(published)}), flush=True)
    finally:
        method.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="libpq writer URL on the deployed actual source database")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inspect-only", action="store_true", help="verify actual retained source/config/schema with read-only SQL; no release or task writes")
    parser.add_argument("--witness", type=Path, default=DEFAULT_WITNESS)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        execute(args)
    except BaseException as error:
        with (args.output / "attempts.jsonl").open("a") as stream:
            stream.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                "outcome": "failed", "error_type": type(error).__name__, "message": str(error)}) + "\n")
        raise


if __name__ == "__main__":
    main()
