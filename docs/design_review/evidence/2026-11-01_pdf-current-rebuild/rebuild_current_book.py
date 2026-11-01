"""Rebuild exact retained native inputs on an already initialized current deployment.

Default mode verifies local witnesses only. --execute writes solely to the fresh target;
source-database inventory always uses a read-only snapshot. Recognition/extraction is a
separate current ci regenerate invocation recorded in the output, never implicit inference.
"""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import file_digest, sha256
from importlib.resources import files
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from corpus_structure.core.evidence import config_key
from corpus_structure.core.provenance import code_commit
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.pdf_methods import IngestPdf, PdfIngestConfig
from corpus_structure.orchestrate.pdf_streaming import migrate_retained_pdf_envelope, resume_pdf_publication
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.operations import (
    OperationBinding, claim_tasks, complete_task, create_run, create_task, record_method, renew_claim, start_run,
)
from corpus_structure.semantic.operation_results import ClaimedTask
from corpus_structure.semantic.pdf_contracts import pdf_context_for_task, store_pdf_original
from corpus_structure.semantic.pdf_publication import inspect_pdf_build, published_pdf_revision
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import activation_token, activate_release, load_release, persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "pdf-docling-adoption"
TARGET = "corpus_pdf_20261101"
SOURCE = "corpus_pdf_20261031"
HEAD = "semantic_pdf_snapshot_20261101"
SOURCE_DIGEST = "e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9"
CHAIN = ((2, "native"), (2, "organized"), (7, "math-enriched"))


def retain(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2, default=str) + "\n")
    temporary.replace(path)


def settings_for(database: str) -> Settings:
    settings = Settings()
    url = make_url(settings.database.url).set(database=database)
    return settings.model_copy(update={"database": settings.database.model_copy(
        update={"url": url.render_as_string(hide_password=False)}
    )})


def witnesses(root: Path):
    result = []
    previous = None
    for task, key in CHAIN:
        path = root / f"retained-{task}-{key}.json"
        binding = json.loads(path.with_suffix(".binding.json").read_bytes())
        with path.open("rb") as stream:
            digest = file_digest(stream, "sha256").hexdigest()
        if digest != binding["content_digest"] or path.stat().st_size != binding["byte_length"]:
            raise ValueError("retained envelope byte identity differs: " + str(path))
        actual_parent = tuple(binding[name] for name in (
            "parent_task_id", "parent_product_key", "parent_digest"
        ))
        expected_parent = previous or (None, None, None)
        if actual_parent != expected_parent:
            raise ValueError("retained structural chain differs: " + str(path))
        previous = (task, key, digest)
        result.append((path, binding))
    return result


def source_inputs(settings, retained):
    """Read old metadata/recipe bytes only; never migrate or rewrite historical products."""
    result = {}
    with open_runtime_engine(settings, "retained-book-source", purpose="maintenance") as engine:
        with read_snapshot(engine) as conn:
            for _, binding in retained:
                row = dict(conn.execute(text("""
                    SELECT d.source_uri,d.original_path,d.content_hash,b.recipe_digest,
                           a.content AS recipe_bytes
                    FROM ops.task t JOIN kb.document d ON d.id=t.unit_id
                    JOIN ops.source_build b ON b.task_id=t.id
                    JOIN kb.source_artifact a ON a.artifact_digest=b.recipe_digest
                    WHERE t.id=:task
                """), {"task": binding["task_id"]}).mappings().one())
                recipe = bytes(row.pop("recipe_bytes"))
                if row["content_hash"] != SOURCE_DIGEST:
                    raise ValueError("historical source identity differs")
                if sha256(recipe).hexdigest() != binding["recipe_digest"]:
                    raise ValueError("historical retained recipe differs from exact product binding")
                result[binding["task_id"]] = (row, recipe)
    return result


def prepare_target(settings, corpus, output):
    bundle, deps, profile, prepared = prepare_pack(DOMAINS / "statistics")
    with open_runtime_engine(settings, "book-current-archive", purpose="admit") as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, deps, profile, prepared)
    analyzed = {}
    if has_authored_sql(prepared):
        with open_runtime_engine(settings, "book-current-sql", purpose="read") as engine:
            with read_snapshot(engine) as conn:
                analyzed = analyze_archived_sql(conn, prepared.release_id)
    with open_runtime_engine(settings, "book-current-admit", purpose="admit") as engine:
        with engine.begin() as conn:
            if analyzed:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
            admit_release(prepared, connection=conn)
    source_id = f"source:{PROJECT}:{prepared.release_id}"
    with open_runtime_engine(settings, "book-current-activate", purpose="admit") as engine:
        with engine.begin() as conn:
            projects = table("data.project")
            existing = conn.execute(select(projects.c.project_id).where(
                projects.c.project_id == PROJECT)).scalar_one_or_none()
            if existing is not None:
                token = activation_token(conn, PROJECT)
                if token.release_id != prepared.release_id:
                    activate_release(conn, PROJECT, prepared.release_id,
                        expected_parent=token.release_id, expected_generation=token.generation,
                        sql_admissions=analyzed)
    with open_runtime_engine(settings, "book-current-project", purpose="write") as engine:
        with engine.begin() as conn:
            init_bound_project(conn, domain="statistics", corpus=corpus, name=PROJECT,
                               release_id=prepared.release_id, realization_id=source_id)
    retain(output / "release.json", {"release_id": prepared.release_id,
                                     "source_realization_id": source_id})
    return prepared, source_id



def finish_storage_task(engine, prepared, step):
    """Close only this exact storage task; no extraction observation is manufactured."""
    holder = "current-book-storage:" + str(step["task_id"])
    with engine.begin() as conn:
        task = table("ops.task")
        row = conn.execute(select(task).where(task.c.id == step["task_id"])).mappings().one()
        if row["status"] == "empty":
            return
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        if (row["status"] == "running" and row["claimed_by"] == holder
                and row["lease_until"] is not None and row["lease_until"] > now):
            attempt = row["attempt"]
        else:
            claims = claim_tasks(conn, run_id=step["run_id"], config_id=step["config_id"], holder=holder)
            if len(claims) != 1 or claims[0].task_id != step["task_id"]:
                raise ValueError("published storage task cannot be reclaimed for exact completion")
            attempt = claims[0].attempt
        complete_task(conn, task_id=step["task_id"], attempt=attempt, holder=holder,
                      prepared=prepared, observations=[], outcome="empty")




def claim_storage_task(conn, step, holder, release_id, *, reattach=False) -> ClaimedTask:
    """Reattach only the settled local process's exact live claim; otherwise ordinary claim."""
    claims = claim_tasks(conn, run_id=step["run_id"], config_id=step["config_id"], holder=holder)
    if claims:
        if len(claims) != 1 or claims[0].task_id != step["task_id"]:
            raise ValueError("checkpoint claim selected another task")
        return claims[0]
    if not reattach:
        raise ValueError("live checkpoint claim needs explicit authenticated settled-process reattachment")
    tasks = table("ops.task")
    row = conn.execute(select(tasks).where(tasks.c.id == step["task_id"])).mappings().one()
    if (row["status"] != "running" or row["claimed_by"] != holder
            or row["run_id"] != step["run_id"] or row["method_config_id"] != step["config_id"]
            or row["release_id"] != release_id):
        raise ValueError("checkpoint task is not owned by this exact settled local process")
    if row["error"] and "semantic_proposal_first_result" in row["error"]:
        raise ValueError("held agent progress requires its owning submission path")
    # The production native fence decides whether the same holder/attempt is still live.
    renew_claim(conn, task_id=row["id"], attempt=row["attempt"], holder=holder)
    row = conn.execute(select(tasks).where(tasks.c.id == step["task_id"])).mappings().one()
    return ClaimedTask(task_id=row["id"], run_id=row["run_id"], release_id=row["release_id"],
        method_config_id=row["method_config_id"], unit_type=TaskUnitType(row["unit_type"]),
        unit_id=row["unit_id"], unit_key=row["unit_key"], packet_hash=row["packet_hash"],
        attempt=row["attempt"], holder=row["claimed_by"], deadline=row["lease_until"],
        invocation_key=row["invocation_key"], held_progress=None)


def select_checkpoint(args, target, output, release_id, retained) -> dict[str, Any]:
    checkpoint = output / "checkpoint.json"
    if not checkpoint.exists():
        return {"target": args.target, "source": args.source, "release_id": release_id, "steps": {}}
    state = json.loads(checkpoint.read_bytes())
    if state["target"] != args.target or state["source"] != args.source:
        raise ValueError("checkpoint belongs to another target/source")
    if state["release_id"] == release_id:
        return state
    if args.reuse_published_prefix:
        from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader

        keys = list(state["steps"])
        chain_keys = [f"{task}/{key}" for task, key in CHAIN]
        if (args.supersede_known_open or not 0 < len(keys) < len(chain_keys)
                or keys != chain_keys[:len(keys)]):
            raise ValueError("reuse requires an exact ordered completed storage prefix")
        schema_digest = sha256(files("corpus_structure").joinpath(
            "model/semantic/docling-validation.schema.json").read_bytes()).hexdigest()
        verified = []
        parent = None
        with open_runtime_engine(target, "book-published-prefix-check", purpose="read") as engine:
            with read_snapshot(engine) as conn:
                for key, (_, old) in zip(keys, retained, strict=False):
                    step = state["steps"][key]
                    if not step.get("completed") or "published" not in step:
                        raise ValueError("prefix step is not durably published and terminal")
                    expected_old = {name: old[name] for name in (
                        "task_id", "product_key", "content_digest")}
                    if step["old_pin"] != expected_old or step["structural_parent"] != parent:
                        raise ValueError("published prefix source/parent mapping differs")
                    revision = step["published"]
                    actual = published_pdf_revision(conn, revision["task_id"],
                        old["product_key"], revision["logical_digest"])
                    if (actual is None or asdict(actual) != revision or actual.kind != "native"
                            or actual.source_digest != SOURCE_DIGEST
                            or actual.schema_digest != schema_digest
                            or actual.task_id != step["task_id"]):
                        raise ValueError("published prefix exact binding/source/schema differs")
                    tasks, runs = table("ops.task"), table("ops.run")
                    task = conn.execute(select(tasks.c.status, tasks.c.lease_until,
                        tasks.c.release_id, tasks.c.run_id, runs.c.project_id).join_from(
                        tasks, runs, tasks.c.run_id == runs.c.id).where(
                        tasks.c.id == actual.task_id)).one()
                    if (task.status != "empty" or task.lease_until is not None
                            or task.release_id != actual.release_id
                            or task.run_id != step["run_id"] or task.project_id != PROJECT):
                        raise ValueError("published prefix task is not terminal under its producing release")
                    reference = ProductReference(actual.task_id, old["product_key"],
                        actual.logical_digest)
                    reader = PublishedPdfReader(conn, reference)
                    digest = sha256()
                    for block in reader.scalar("retained/envelope"):
                        digest.update(block)
                    if digest.hexdigest() != old["content_digest"]:
                        raise ValueError("published prefix retained original envelope differs")
                    inputs = [row["body"] for row in reader.iter_rows(
                        "companion", {"family": "input"})]
                    expected_inputs = [] if parent is None else [{"role": "structural", **parent}]
                    if inputs != expected_inputs:
                        raise ValueError("published prefix admitted structural input differs")
                    verified.append({"step": key, "producing_release_id": actual.release_id,
                        "pin": reference.values(), "retained_envelope_sha256": digest.hexdigest()})
                    parent = reference.values()
        content = checkpoint.read_bytes()
        archive = output / ("checkpoint-published-prefix-" + state["release_id"].split(":")[-1][:12]
            + "-" + sha256(content).hexdigest()[:12] + ".json")
        if archive.exists() and archive.read_bytes() != content:
            raise ValueError("published-prefix checkpoint archive denotes another state")
        if not archive.exists():
            archive.write_bytes(content)
        new_state = {"target": args.target, "source": args.source, "release_id": release_id,
                     "steps": state["steps"], "reused_published_prefix_from": state["release_id"],
                     "prior_checkpoint": archive.name}
        retain(output / ("published-prefix-reuse-" + release_id.split(":")[-1][:12] + ".json"),
            {"outcome": "passed", "authorization": "explicit --reuse-published-prefix; compatible immutable input reuse",
             "published_prefix": verified, "remaining_tasks_release_id": release_id,
             "unchanged_published_bindings": {key: state["steps"][key]["published"] for key in keys},
             "source_digest": SOURCE_DIGEST, "schema_digest": schema_digest,
             "checkpoint_archive": archive.name})
        return new_state
    if not args.supersede_known_open:
        raise ValueError("release changed; inspect the prior outcome and explicitly select --supersede-known-open")
    receipt_path = args.supersession_receipt or (output / "supersession-001.json")
    receipt = json.loads(receipt_path.read_bytes())
    archived = output / receipt["checkpoint_archive"]
    if (receipt["outcome"] != "passed" or receipt["old_release_id"] != state["release_id"]
            or receipt["published_count_before"] != 0 or receipt["frozen_count_before"] != 0
            or archived.read_bytes() != checkpoint.read_bytes()):
        raise ValueError("prior checkpoint has no exact known-unsealed supersession receipt")
    with open_runtime_engine(target, "book-supersede-checkpoint", purpose="maintenance") as engine:
        with read_snapshot(engine) as conn:
            for step in state["steps"].values():
                if "published" in step:
                    raise ValueError("a published checkpoint requires its own explicit migration route")
                task = conn.execute(text("SELECT status,lease_until FROM ops.task WHERE id=:task"),
                    {"task": step["task_id"]}).mappings().one()
                stages = list(conn.execute(text("SELECT build_id,state FROM ops.pdf_stage_build WHERE task_id=:task"),
                    {"task": step["task_id"]}).mappings())
                if task["status"] != "failed" or task["lease_until"] is not None or not stages:
                    raise ValueError("prior source task has not settled failed with retained private state")
                if any(row["state"] != "abandoned" for row in stages):
                    raise ValueError("prior private build has not been explicitly abandoned")
                for row in stages:
                    frozen = conn.execute(text("SELECT count(*) FROM ops.pdf_frozen_build WHERE build_id=:id"),
                        {"id": row["build_id"]}).scalar_one()
                    if frozen:
                        raise ValueError("prior build has frozen effects; refuse automatic supersession")
                published = conn.execute(text("SELECT count(*) FROM ops.pdf_published_revision WHERE task_id=:task"),
                    {"task": step["task_id"]}).scalar_one()
                if published:
                    raise ValueError("prior task has published effects; refuse automatic supersession")
    new_state = {"target": args.target, "source": args.source, "release_id": release_id,
                 "steps": {}, "supersedes_checkpoint": receipt["checkpoint_archive"]}
    retain(output / ("supersession-selection-" + state["release_id"].split(":")[-1][:12] + ".json"),
        {"outcome": "passed", "old_release_id": state["release_id"],
         "new_release_id": release_id, "checkpoint_archive": receipt["checkpoint_archive"],
         "receipt": str(receipt_path),
         "authorization": "explicit --supersede-known-open and named known-failure receipt; no frozen/published effects, terminal failed task"})
    return new_state



def settled_claim_proof(path: Path, checkpoint: Path):
    import os

    proof = json.loads(path.read_bytes())
    if (proof["exit_code"] != 130 or proof["checkpoint_sha256"] != sha256(checkpoint.read_bytes()).hexdigest()):
        raise ValueError("settled-process receipt differs from the exact local checkpoint")
    try:
        os.kill(proof["pid"], 0)
    except ProcessLookupError:
        pass
    else:
        raise ValueError("the previously owned data process still exists; refuse reattachment")
    return proof


def resume_frozen_step(args, target, output, proof, *, product_key):
    """Complete the exact first unfinished frozen suffix under its producing release."""
    checkpoint = output / "checkpoint.json"
    state = json.loads(checkpoint.read_bytes())
    index = next(i for i, (_, key) in enumerate(CHAIN) if key == product_key)
    expected_keys = [f"{task}/{key}" for task, key in CHAIN[:index + 1]]
    if (state["target"] != args.target or state["source"] != args.source
            or list(state["steps"]) != expected_keys
            or args.supersede_known_open or args.reuse_published_prefix):
        raise ValueError("frozen resume requires its exact ordered checkpoint prefix/suffix")
    for key in expected_keys[:-1]:
        prior = state["steps"][key]
        if not prior.get("completed") or "published" not in prior:
            raise ValueError("an earlier prefix step is not published and terminal")
    step = state["steps"][expected_keys[-1]]
    if ("published" in step or step["task_id"] != proof["task_id"]
            or proof.get("product_key", product_key) != product_key
            or proof["build"]["state"] != "frozen"):
        raise ValueError("receipt differs from the first frozen unfinished suffix")
    holder = "current-book-storage:" + str(step["task_id"])
    with open_runtime_engine(target, "book-frozen-" + product_key + "-resume", purpose="write") as engine:
        with engine.begin() as conn:
            prepared = load_release(conn, state["release_id"])
            context = pdf_context_for_task(conn, step["task_id"])
            claim = claim_storage_task(conn, step, holder, state["release_id"], reattach=True)
            existing = inspect_pdf_build(conn, task_id=claim.task_id, attempt=claim.attempt,
                holder=holder, replay_key="product:" + product_key)
            if (existing is None or existing.frozen is None or existing.published is not None
                    or existing.build.build_id != proof["build"]["build_id"]
                    or existing.frozen.frozen_digest != proof["build"]["frozen_digest"]
                    or existing.build.release_id != state["release_id"]
                    or existing.build.source_digest != SOURCE_DIGEST
                    or existing.build.schema_digest != context.native_schema_digest
                    or (proof["build"].get("recipe_digest") is not None
                        and existing.build.recipe_digest != proof["build"]["recipe_digest"])):
                raise ValueError("frozen suffix source/schema/release/inventory differs from receipt")
        with maintained_claims(engine, [claim], holder) as check_active:
            published = resume_pdf_publication(engine, claim, holder, product_key=product_key,
                source_digest=existing.build.source_digest, recipe_digest=existing.build.recipe_digest,
                schema_digest=existing.build.schema_digest, kind="native", check_active=check_active)
        step["published"] = asdict(published)
        retain(checkpoint, state)
        finish_storage_task(engine, prepared, step)
        step["completed"] = True
        retain(checkpoint, state)
    pin = ProductReference(published.task_id, product_key, published.logical_digest)
    retain(output / (product_key + ".pin.json"), pin.values())
    if product_key == "native":
        retain(output / "raw-producing-qualification.json", {
            "outcome": "passed", "scope": "original-native-graph-access-and-provenance-only",
            "producing_release_id": published.release_id, "build_id": published.build_id,
            "frozen_digest": published.frozen_digest, "pin": pin.values(),
            "occurrence_derivative": "not populated by retained71 adapter; unused by raw intermediate",
            "selected_consumer_source": False, "remaining_chain": "not_run"})
    retain(output / (product_key + "-frozen-resume-" + published.build_id[:12] + ".json"), {
        "outcome": "passed", "scope": "exact-frozen-storage-suffix-only",
        "pin": pin.values(), "producing_release_id": published.release_id,
        "build_id": published.build_id, "frozen_digest": published.frozen_digest,
        "proof": str(args.reattach_settled_claim), "task_completed": "empty",
        "remaining_chain": "not_run"})
    print(json.dumps({"outcome": "passed", "scope": "exact-frozen-storage-suffix-only",
        "pin": pin.values(), "producing_release_id": published.release_id,
        "remaining_chain": "not_run"}), flush=True)


def execute(args):
    retained = witnesses(args.witnesses)
    receipts = args.receipts.resolve(strict=True)
    observations = sum(1 for _ in receipts.rglob("observation-*.json"))
    if not observations:
        raise ValueError("actual retained recognition observations are absent")
    if not args.execute:
        print(json.dumps({"outcome": "passed", "scope": "local-exact-witnesses-only",
                          "witnesses": len(retained), "recognition_observation_files": observations,
                          "target_writes": "not_run"}), flush=True)
        return
    if args.target != TARGET or args.source != SOURCE:
        raise ValueError("this bounded driver owns only the named fresh target and historical source")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = settings_for(args.target)
    with open_runtime_engine(target, "book-current-head", purpose="maintenance") as engine:
        with read_snapshot(engine) as conn:
            if current_revision(conn) != HEAD:
                raise ValueError("migrate the target to the reviewed current head before execution")
    proof = None
    if args.reattach_settled_claim is not None:
        proof = settled_claim_proof(args.reattach_settled_claim, output / "checkpoint.json")
    if args.resume_frozen_raw and args.resume_frozen_product is not None:
        raise ValueError("select one exact frozen suffix")
    resume_product = "native" if args.resume_frozen_raw else args.resume_frozen_product
    if resume_product is not None:
        if proof is None:
            raise ValueError("frozen resume requires an authenticated settled-process receipt")
        resume_frozen_step(args, target, output, proof, product_key=resume_product)
        return
    source = source_inputs(settings_for(args.source), retained)
    metadata, _ = source[CHAIN[0][0]]
    original_path = Path(metadata["original_path"]).resolve(strict=True)
    original = original_path.read_bytes()
    if sha256(original).hexdigest() != SOURCE_DIGEST:
        raise ValueError("retained original PDF differs")
    corpus = original_path
    for _ in Path(metadata["source_uri"]).parts:
        corpus = corpus.parent
    schema = files("corpus_structure").joinpath("model/semantic/docling-validation.schema.json").read_bytes()
    selected_release = prepare_pack(DOMAINS / "statistics")[-1].release_id
    state = select_checkpoint(args, target, output, selected_release, retained)
    prepared, source_id = prepare_target(target, corpus, output)
    if prepared.release_id != selected_release:
        raise ValueError("source changed while preparing the explicit target release")
    checkpoint = output / "checkpoint.json"
    retain(checkpoint, state)
    method = IngestPdf()
    parent = None
    raw = output / "raw"
    raw.mkdir(exist_ok=True)
    try:
        with open_runtime_engine(target, "book-current-publish", purpose="write") as engine:
            for path, old in retained:
                key = f"{old['task_id']}/{old['product_key']}"
                step = state["steps"].get(key)
                old_pin = {name: old[name] for name in ("task_id", "product_key", "content_digest")}
                if step and "published" in step:
                    published = step["published"]
                    with engine.connect() as conn:
                        actual = published_pdf_revision(conn, published["task_id"], old["product_key"],
                                                        published["logical_digest"])
                    if actual is None or asdict(actual) != published:
                        raise ValueError("checkpoint publication differs from protected revision")
                    if not step.get("completed"):
                        finish_storage_task(engine, prepared, step)
                        step["completed"] = True
                        retain(checkpoint, state)
                    parent = ProductReference(published["task_id"], old["product_key"],
                                              published["logical_digest"])
                    retain(output / (old["product_key"] + ".pin.json"), parent.values())
                    if args.stop_after_native and old["product_key"] == "native":
                        print(json.dumps({"outcome": "passed", "scope": "raw-native-only",
                                          "native_pin": parent.values(), "remaining_chain": "not_run"}), flush=True)
                        return
                    continue
                recipe = source[old["task_id"]][1]
                kept = raw / path.name
                if not kept.exists():
                    shutil.copyfile(path, kept)
                retained_binding = kept.with_suffix(".binding.json")
                if not retained_binding.exists():
                    shutil.copyfile(path.with_suffix(".binding.json"), retained_binding)
                recipe_path = raw / f"retained-{old['task_id']}.recipe.json"
                if not recipe_path.exists():
                    recipe_path.write_bytes(recipe)
                if step is None:
                    # This task records an exact storage derivation, not newly performed inference.
                    cfg = PdfIngestConfig(native_product=parent)
                    params = cfg.model_dump(mode="json")
                    dependencies = canonical_bytes({"purpose": "retained-pdf-storage-derivation",
                        "source_pin": old_pin, "source_envelope_sha256": old["content_digest"],
                        "structural_parent": None if parent is None else parent.values()})
                    with engine.begin() as conn:
                        realization = table("data.realization")
                        revision = conn.execute(select(realization.c.data_revision).where(
                            realization.c.realization_id == source_id)).scalar_one()
                        binding = OperationBinding(prepared.release_id, source_id, revision, dependencies)
                        run = create_run(conn, project_id=PROJECT, binding=binding, kind="ingest",
                            options={"scope": None, "purpose": "retained-pdf-storage-derivation"},
                            code_commit=code_commit())
                        start_run(conn, run)
                        config = record_method(conn, method, "retained-storage:" + key, params,
                            config_key(method.name, method.version, params), prepared=prepared)
                        docs = table("kb.document")
                        document = conn.execute(select(docs).where(docs.c.project_id == PROJECT,
                            docs.c.source_uri == metadata["source_uri"],
                            docs.c.content_hash == SOURCE_DIGEST)).mappings().one()
                        task = create_task(conn, run_id=run, config_id=config, stage="ingest",
                            unit_type="document", unit_id=document["id"], unit_key=document["key"],
                            input_hash=sha256(dependencies).hexdigest(), fresh=True)
                    step = {"run_id": run, "task_id": task, "config_id": config,
                            "old_pin": old_pin, "structural_parent": None if parent is None else parent.values()}
                    state["steps"][key] = step
                    retain(checkpoint, state)
                if step["structural_parent"] != (None if parent is None else parent.values()):
                    raise ValueError("checkpoint structural parent differs from rebuilt chain")
                holder = "current-book-storage:" + str(step["task_id"])
                with engine.begin() as conn:
                    claim = claim_storage_task(conn, step, holder, prepared.release_id,
                        reattach=args.reattach_settled_claim is not None)
                    store_pdf_original(conn, task_id=claim.task_id, attempt=claim.attempt, holder=holder,
                                       original=original, recipe_bytes=recipe)
                    existing = inspect_pdf_build(conn, task_id=claim.task_id, attempt=claim.attempt,
                        holder=holder, replay_key="product:" + old["product_key"])
                if existing is not None and (existing.frozen is not None or existing.published is not None):
                    with maintained_claims(engine, [claim], holder) as check_active:
                        published = resume_pdf_publication(engine, claim, holder,
                            product_key=old["product_key"], source_digest=SOURCE_DIGEST,
                            recipe_digest=existing.build.recipe_digest,
                            schema_digest=sha256(schema).hexdigest(), kind="native", check_active=check_active)
                else:
                    published = migrate_retained_pdf_envelope(engine, claim, holder, path=kept,
                        expected_sha256=old["content_digest"], original=original, schema_bytes=schema,
                        recipe_bytes=recipe, directory=output / "private" / old["product_key"],
                        kind="native", product_key=old["product_key"], structural_parent=parent)
                step["published"] = asdict(published)
                retain(checkpoint, state)
                finish_storage_task(engine, prepared, step)
                step["completed"] = True
                retain(checkpoint, state)
                parent = ProductReference(published.task_id, old["product_key"], published.logical_digest)
                retain(output / (old["product_key"] + ".pin.json"), parent.values())
                if args.stop_after_native and old["product_key"] == "native":
                    print(json.dumps({"outcome": "passed", "scope": "raw-native-only",
                                      "native_pin": parent.values(), "remaining_chain": "not_run"}), flush=True)
                    return
        if parent is None:
            raise ValueError("native chain produced no terminal enriched pin")
        retain(output / "regenerate-command.json", {"environment": {
            "CORPUS_DATABASE__URL": target.database.url,
            "CORPUS_NEMOTRON__RECEIPTS": str(receipts)},
            "argv": ["uv", "run", "ci", "regenerate", "--domain", "statistics", "--corpus", str(corpus),
                     "--project", PROJECT, "--native-source", str(output / "math-enriched.pin.json"),
                     "--leave-unselected", "--json"], "outcome": "not_run"})
        print(json.dumps({"outcome": "passed", "scope": "current-native-storage-chain-only",
                          "native_pin": parent.values(), "regeneration": "not_run"}), flush=True)
    finally:
        method.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--stop-after-native", action="store_true")
    parser.add_argument("--resume-frozen-raw", action="store_true")
    parser.add_argument("--resume-frozen-product", choices=[key for _, key in CHAIN])
    parser.add_argument("--reattach-settled-claim", type=Path)
    parser.add_argument("--supersede-known-open", action="store_true")
    parser.add_argument("--reuse-published-prefix", action="store_true")
    parser.add_argument("--supersession-receipt", type=Path)
    parser.add_argument("--target", default=TARGET)
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--witnesses", type=Path, default=Path("build/pdf-current-rebuild"))
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "runtime")
    parser.add_argument("--receipts", type=Path, default=Path(
        "docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/runtime/pages"))
    args = parser.parse_args()
    try:
        execute(args)
    except BaseException as error:
        args.output.mkdir(parents=True, exist_ok=True)
        with (args.output / "attempts.jsonl").open("a") as stream:
            stream.write(json.dumps({"at": datetime.now(UTC).isoformat(), "outcome": "failed",
                                     "error_type": type(error).__name__, "message": str(error)}) + "\n")
        raise


if __name__ == "__main__":
    main()
