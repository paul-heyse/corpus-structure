"""Registered CPU retrieval on source-only inputs; never reads reference answers.

One explicit profile per run. Re-run E5 with --extend-weibull after its baseline,
under the identical runtime, to inspect retained target-vector reuse.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import func, select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate.operation_assessment import read_evaluation
from corpus_structure.methods.contextual_candidates import ContextualCandidateConfig
from corpus_structure.orchestrate import commands, m1
from corpus_structure.orchestrate.phase0 import bind_pdf_source
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import installed_runtime_id
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PROJECT = "m1-source-grinstead-snell"


def write(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def recover_completed(args):
    """Detach existing completed products in a read-only snapshot; execute no tasks."""
    prefix = RAW / args.receipt
    for suffix in ("-result.json", "-products.json", "-common-pages.json"):
        if Path(str(prefix) + suffix).exists():
            raise FileExistsError(str(prefix) + suffix)
    packet_path = RAW / "contextual-source-author-packet-001.json"
    packet = json.loads(packet_path.read_bytes())
    settings = Settings()
    with open_runtime_engine(settings, "pce-contextual-completed-recovery", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            runs, completed, tasks, configs, methods, results, projects = map(table, (
                "ops.run", "ops.completed_result", "ops.task", "ops.method_config",
                "ops.method", "ops.task_result", "data.project"))
            run = conn.execute(select(runs).where(runs.c.id == args.recover_run,
                runs.c.project_id == PROJECT)).mappings().one()
            if run["status"] != "finished" or not run["sealed"]:
                raise RuntimeError("recovery requires an already finished/sealed run")
            completion = dict(conn.execute(select(completed).where(
                completed.c.run_id == args.recover_run)).mappings().one())
            inventory = [dict(row) for row in conn.execute(select(tasks.c.id, tasks.c.status,
                tasks.c.reused_task_id, methods.c.name).join(configs,
                configs.c.id == tasks.c.method_config_id).join(methods,
                methods.c.id == configs.c.method_id).where(tasks.c.run_id == args.recover_run)).mappings()]
            origin = tasks.alias("immutable_origin")
            rows = [dict(row) for row in conn.execute(select(tasks.c.id,
                origin.c.id.label("origin_task_id"), origin.c.run_id.label("origin_run_id"),
                configs.c.params, results.c.body).join(configs,
                configs.c.id == tasks.c.method_config_id).join(methods,
                methods.c.id == configs.c.method_id).join(origin,
                origin.c.id == func.coalesce(tasks.c.reused_task_id, tasks.c.id)).join(results,
                results.c.task_id == origin.c.id).where(tasks.c.run_id == args.recover_run,
                methods.c.name == "retrieve.contextual")).mappings()]
            if len(rows) != 1 or any(item["status"] not in ("done", "empty", "reused") for item in inventory):
                raise RuntimeError("completed cohort lacks exactly one successful contextual origin")
            row = rows[0]
            cfg = ContextualCandidateConfig.model_validate(row.pop("params"))
            if cfg.source_product_digest != packet["physical_pin"]["product_digest"] or (
                cfg.source_projection_digest != packet["physical_pin"]["projection_digest"]):
                raise RuntimeError("completed cohort source binding differs from declared packet")
            if [case.model_dump(mode="json") for case in cfg.cases] != [
                {key: case.get(key, "") for key in ("case_id","pointer","text","start","end","mention","heading","parent")}
                for case in packet["cases"]]:
                raise RuntimeError("completed cohort supplied cases differ from the source packet")
            pages, cursor = [], None
            while True:
                page = serve_contributions(conn, ContributionRequest(run_id=args.recover_run,
                    method="retrieve.contextual", include_details=True, include_publication=True,
                    include_support=True, cursor=cursor, page_bytes=8_000_000, max_bytes=32_000_000))
                pages.append(page.model_dump(mode="json"))
                cursor = page.next_cursor
                if cursor is None:
                    break
            current_defaults = dict(conn.execute(select(projects).where(
                projects.c.project_id == PROJECT)).mappings().one())
            record_assertions = table("data.record_assertion")
            whole_record_count = conn.scalar(select(func.count()).select_from(record_assertions).where(
                record_assertions.c.release_id == completion["release_id"],
                record_assertions.c.realization_id == completion["output_realization_id"]))
    dependencies = json.loads(bytes(run["dependencies"]))
    contextual = next(op["contextual_enrichment"] for op in row["body"]["contribution_operations"]
                      if "contextual_enrichment" in op)
    defaults_preserved, defaults_reference = None, None
    if args.defaults_reference is not None:
        reference = json.loads(args.defaults_reference.read_bytes())
        if reference["runtime_id"] != run["runtime_id"] or reference["release_id"] != run["release_id"]:
            raise RuntimeError("defaults reference belongs to a different runtime/release")
        defaults_preserved = reference["project_after"] == current_defaults
        defaults_reference = dict(path=str(args.defaults_reference),
            sha256=sha256(args.defaults_reference.read_bytes()).hexdigest())
        if not defaults_preserved:
            raise RuntimeError("project defaults differ from the retained pre-cohort observation")
    admission = dependencies.get("local_semantic_admission", [])
    admitted = pages[0]["inventory_counts"]["admitted_semantic_claims"]
    if whole_record_count != 0 or (admission and admitted < 1):
        raise RuntimeError("completed cohort violates declared local-publication boundary")
    write(Path(str(prefix) + "-products.json"), rows)
    write(Path(str(prefix) + "-common-pages.json"), pages)
    result = dict(outcome="passed", run_id=args.recover_run, release_id=run["release_id"],
        runtime_id=run["runtime_id"], profile=cfg.profile, cases=len(cfg.cases), targets=len(cfg.registry_targets),
        source_packet_sha256=sha256(packet_path.read_bytes()).hexdigest(),
        script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), recovery="read_only_completed_run",
        provider_execution=False, source_execution=False, completion_execution=False,
        current_project_defaults=current_defaults, project_defaults_preserved=defaults_preserved,
        defaults_reference=defaults_reference, completed=completion, binding=pages[0]["binding"],
        method_inventory=inventory, selected_task_id=row["id"], origin_task_id=row["origin_task_id"],
        product_counts=contextual["product_counts"], reused_vector_count=len(contextual.get("vector_reuse", [])),
        local_semantic_admission=admission, admitted_semantic_claims=admitted,
        whole_record_assertion_count=whole_record_count,
        scope="recovered completed supplied-mention cohort; no new execution or corpus-quality inference")
    write(Path(str(prefix) + "-result.json"), result)
    print(json.dumps(result), flush=True)


def main(args):
    if args.recover_run is not None:
        return recover_completed(args)
    prefix = RAW / args.receipt
    for suffix in ("-prepared.json", "-result.json", "-products.json", "-common-pages.json"):
        if Path(str(prefix) + suffix).exists():
            raise FileExistsError(str(prefix) + suffix)
    packet_path = RAW / "contextual-source-author-packet-001.json"
    packet = json.loads(packet_path.read_bytes())
    targets = list(packet["inventory"])
    if args.extend_weibull:
        if args.profile != "e5":
            raise ValueError("changed-inventory experiment is declared for E5")
        targets.append(dict(target_id="statistics:weibull", label="Weibull distribution",
                            description="Positive continuous shape-and-scale distribution."))
    cfg = ContextualCandidateConfig(
        profile=args.profile, registry_targets=targets,
        cases=[{k: v for k, v in case.items() if k != "question"} for case in packet["cases"]],
        source_product_digest=packet["physical_pin"]["product_digest"],
        source_projection_digest=packet["physical_pin"]["projection_digest"],
        scope="statistics.chapter5", unique_target_budget=10, channel_budget=30)
    product = ProductReference(packet["physical_pin"]["native_product_task_id"],
                               packet["physical_pin"]["product_key"],
                               packet["physical_pin"]["product_digest"])
    settings = Settings()
    admission, graded_run = (), None
    if args.admission is not None:
        supplied_grade = json.loads(args.admission.read_bytes())
        evaluation_id = int(supplied_grade["evaluation_id"])
        with open_runtime_engine(settings, "pce-contextual-prior-grade", purpose="evaluate") as evaluator:
            with evaluator.connect() as conn:
                validated = read_evaluation(conn, project_id=PROJECT, evaluation_id=evaluation_id)
                evaluation = table("eval.reference_evaluation")
                frozen_grade = conn.execute(select(evaluation.c.run_id, evaluation.c.content_digest)
                    .where(evaluation.c.id == evaluation_id, evaluation.c.project_id == PROJECT)).mappings().one()
        if (frozen_grade["content_digest"] != supplied_grade["content_digest"] or
                frozen_grade["run_id"] != supplied_grade["run_id"] or
                validated["release_id"] != args.release):
            raise RuntimeError("supplied grade differs from protected project/run/release/digest")
        graded_run = frozen_grade["run_id"]
        admission = (dict(evaluation_id=evaluation_id,
                          evaluation_digest=frozen_grade["content_digest"]),)
    pack = DOMAINS / "statistics"
    method_settings = MethodSettings(data_dir=settings.paths.data_dir,
        model_cache=settings.paths.model_cache, nemotron_endpoint=settings.nemotron.endpoint,
        nemotron_python=settings.nemotron.python, nemotron_worker=settings.nemotron.worker,
        nemotron_receipts=settings.nemotron.receipts,
        nemotron_timeout_seconds=settings.nemotron.timeout_seconds)
    with open_runtime_engine(settings, "pce-contextual-corpus", purpose="write") as engine:
        with engine.connect() as conn:
            prepared = open_release(conn, args.release)
            if installed_runtime_id(prepared) != args.runtime:
                raise RuntimeError("installed runtime differs from the coordinator's final pin")
            projects, realizations, documents = map(table,
                ("data.project", "data.realization", "kb.document"))
            before = dict(conn.execute(select(projects).where(
                projects.c.project_id == PROJECT)).mappings().one())
            realization = conn.execute(select(realizations).where(
                realizations.c.realization_id == args.realization,
                realizations.c.project_id == PROJECT,
                realizations.c.release_id == args.release)).mappings().one()
            docs = [dict(d) for d in conn.execute(select(documents).where(
                documents.c.project_id == PROJECT)).mappings()]
            document = m1.retained_document(conn, product, prepared=prepared,
                                            project_id=PROJECT, documents=docs)
            corpus, _ = records([d for d in docs if d["id"] == document.id], {},
                                 slice=None, scope=None, corpus=None)
            binding = OperationBinding(args.release, args.realization,
                realization["data_revision"], canonical_bytes(dict(domain="statistics",
                release=args.release, source_packet_sha256=sha256(packet_path.read_bytes()).hexdigest())))
        registry = bind_pdf_source(m1.registry(pack), product, configuration="default",
                                   method_name="ingest.pdf_integrated", input_role="integrated")
        registry = m1.bind_retained_document(registry, document)
        allowed = {"ingest.pdf_integrated", "retrieve.contextual"}
        configs = {key: value for key, value in registry.file.configs.items() if key in allowed}
        configs["retrieve.contextual"] = {"default": cfg.model_dump(mode="json")}
        registry = MethodRegistry([m for m in registry.methods() if m.name in allowed],
            replace(registry.file, configs=configs), registry.sources, prepared=registry.prepared)
        source = m1.source_graph("source-only")
        graph = Graph((*source.stages, (Stage.ASSEMBLE, (
            Step("retrieve.contextual/default", upstream=("ingest.pdf_integrated",)),))),
            policy_propose=False)
        report = run_source_methods(engine, project_id=PROJECT, prepared=prepared,
            binding=binding, registry=registry, graph=graph, method_settings=method_settings,
            domain="statistics", guideline=(pack / "m1-guideline.md").read_text(),
            corpus_record=corpus, extraction_policy="m1-candidate",
            extraction_policy_config=canonical_bytes(dict(route="contextual-source-input-1",
                input_population="explicit-supplied-mentions-1", profile=args.profile,
                references_consumed=False, unique_target_budget=10, channel_budget=30)).decode(),
            local_semantic_admission=admission)
        write(Path(str(prefix) + "-prepared.json"), report.model_dump(mode="json"))
        tasks, configurations, methods, results, runs = map(table,
            ("ops.task", "ops.method_config", "ops.method", "ops.task_result", "ops.run"))
        with engine.connect() as conn:
            inventory = [dict(row) for row in conn.execute(select(tasks.c.id, tasks.c.status,
                tasks.c.reused_task_id, methods.c.name).join(configurations,
                configurations.c.id == tasks.c.method_config_id).join(methods,
                methods.c.id == configurations.c.method_id).where(
                tasks.c.run_id == report.run_id)).mappings()]
            if {row["name"] for row in inventory} - allowed:
                raise RuntimeError("cohort executed an undeclared producer")
            runtime = conn.scalar(select(runs.c.runtime_id).where(runs.c.id == report.run_id))
            if runtime != args.runtime:
                raise RuntimeError("actual run runtime differs from declared cohort pin")
            origin = tasks.alias("immutable_origin")
            bodies = [dict(row) for row in conn.execute(select(tasks.c.id,
                origin.c.id.label("origin_task_id"), origin.c.run_id.label("origin_run_id"), results.c.body)
                .join(configurations, configurations.c.id == tasks.c.method_config_id)
                .join(methods, methods.c.id == configurations.c.method_id)
                .join(origin, origin.c.id == func.coalesce(tasks.c.reused_task_id, tasks.c.id))
                .join(results, results.c.task_id == origin.c.id).where(
                    tasks.c.run_id == report.run_id, methods.c.name == "retrieve.contextual")).mappings()]
            if admission:
                contextual_tasks = [item for item in inventory if item["name"] == "retrieve.contextual"]
                if len(contextual_tasks) != 1 or contextual_tasks[0]["status"] != "reused":
                    raise RuntimeError("admission run must reuse the exact graded contextual observation")
                completed_runs, cut_tasks = map(table, ("ops.completed_result", "ops.cut_task"))
                graded_origins = set(conn.scalars(select(cut_tasks.c.origin_task_id)
                    .join(completed_runs, completed_runs.c.cut_id == cut_tasks.c.cut_id)
                    .where(completed_runs.c.run_id == graded_run)))
                if len(bodies) != 1 or bodies[0]["origin_task_id"] not in graded_origins:
                    raise RuntimeError("reused contextual origin is outside the exact graded completed cut")
        write(Path(str(prefix) + "-products.json"), bodies)
        if len(bodies) != 1 or any(row["status"] not in ("done", "empty", "reused") for row in inventory):
            raise RuntimeError("cohort did not complete exactly one registered contextual task")
        completed = commands.finalize_bound_run(engine, report.run_id,
            f"{args.receipt}:contextual:{report.run_id}", analytics=settings.analytics)
        pages, cursor = [], None
        with read_snapshot(engine) as conn:
            while True:
                page = serve_contributions(conn, ContributionRequest(run_id=int(report.run_id),
                    method="retrieve.contextual", include_details=True, include_publication=True,
                    include_support=bool(admission),
                    cursor=cursor, page_bytes=8_000_000, max_bytes=32_000_000))
                pages.append(page.model_dump(mode="json"))
                cursor = page.next_cursor
                if cursor is None:
                    break
            after = dict(conn.execute(select(projects).where(
                projects.c.project_id == PROJECT)).mappings().one())
            complete_records = table("data.record_assertion")
            whole_record_count = conn.scalar(select(func.count()).select_from(complete_records)
                .where(complete_records.c.release_id == args.release,
                       complete_records.c.realization_id == completed.realization_id))
        write(Path(str(prefix) + "-common-pages.json"), pages)
        if before != after:
            raise RuntimeError("cohort changed the project defaults")
        admitted_semantic_claims = pages[0]["inventory_counts"]["admitted_semantic_claims"]
        if admission and admitted_semantic_claims < 1:
            raise RuntimeError("prior-grade publication produced no independently admitted semantic claim")
        if whole_record_count != 0:
            raise RuntimeError("contextual cohort unexpectedly admitted a complete-record assertion")
        body = bodies[0]["body"]
        contextual = next(op["contextual_enrichment"] for op in body["contribution_operations"]
                          if "contextual_enrichment" in op)
        if args.extend_weibull and len(contextual.get("vector_reuse", ())) != 20:
            raise RuntimeError("changed registry did not reuse precisely the20 original target vectors")
        result = dict(outcome="passed", run_id=int(report.run_id), release_id=args.release,
            runtime_id=runtime, profile=args.profile, extended_inventory=args.extend_weibull,
            source_packet_sha256=sha256(packet_path.read_bytes()).hexdigest(),
            script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            cases=len(cfg.cases), targets=len(cfg.registry_targets), method_inventory=inventory,
            product_counts=contextual["product_counts"],
            reused_vector_count=len(contextual.get("vector_reuse", ())),
            local_semantic_admission=admission, graded_run_id=graded_run,
            admitted_semantic_claims=admitted_semantic_claims,
            whole_record_assertion_count=whole_record_count,
            selected_task_id=bodies[0]["id"], origin_task_id=bodies[0]["origin_task_id"],
            completed=asdict(completed), project_defaults_preserved=True,
            reference_answers_consumed=False,
            scope="registered supplied-mention cohort; no discovery or whole-corpus quality claim")
        write(Path(str(prefix) + "-result.json"), result)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    for optional in ("release", "realization", "runtime"):
        parser.add_argument("--" + optional)
    parser.add_argument("--profile", choices=("e5", "qwen"))
    parser.add_argument("--recover-run", type=int)
    parser.add_argument("--defaults-reference", type=Path)
    parser.add_argument("--extend-weibull", action="store_true")
    parser.add_argument("--admission", type=Path,
                        help="Immutable protected grade JSON; binds publication to reused origin")
    args = parser.parse_args()
    if args.recover_run is None and any(getattr(args, name) is None for name in (
        "release", "realization", "runtime", "profile")):
        parser.error("execution requires --release --realization --runtime --profile")
    main(args)
