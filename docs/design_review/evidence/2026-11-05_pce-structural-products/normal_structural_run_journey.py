"""Reimport frozen supplied readings through the ordinary registered RUN executor.

This exercises execution and custody, not automatic interpretation or new model work.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic.observations import bind_result

from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.provenance import code_commit
from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.structural_products import StructuralProductsConfig, StructuralProductsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationBinding, seal_cut, create_run, start_run, create_task, end_source_run, claim_tasks, complete_task
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.authored_sql import has_authored_sql, analyze_archived_sql, admit_archived_sql
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
PROJECT = "pce-statistics-structural"


def main(release: str, attempt: str, existing_runs=()) -> None:
    settings = Settings()
    names = ("normal", "mean", "comparison", "dossier")
    reports = {
        name: StructuralProductReport.model_validate_json((HERE / f"raw/production-{name}-005.json").read_bytes())
        for name in names
    }
    method = StructuralProductsMethod()
    configs = {
        name: StructuralProductsConfig(report=report, structural_input_digest=report.inputs.identity).model_dump(mode="json", exclude_none=True)
        for name, report in reports.items()
    }
    with open_runtime_engine(settings, "pce-normal-structural-admit", purpose="admit") as admission, admission.begin() as conn:
        prepared = open_release(conn, release)
        if has_authored_sql(prepared):
            with open_runtime_engine(settings, "pce-normal-structural-sql", purpose="read") as reader, reader.connect() as source:
                analyzed = analyze_archived_sql(source, release)
            admit_archived_sql(conn, release, analyzed=analyzed)
        admit_release(prepared, connection=conn)
    realization = "pce-normal-structural-input:" + release
    with open_runtime_engine(settings, "pce-normal-structural-run", purpose="write") as engine:
        with engine.begin() as conn:
            prepared = open_release(conn, release)
            initialize_source_project(conn, project_id=ProjectId(PROJECT), release_id=ReleaseId(release), realization_id=RealizationId(realization), projection_context=prepared)
            before = dict(conn.execute(text("SELECT * FROM data.project WHERE project_id=:p"), {"p": PROJECT}).mappings().one())
        producer_runs = list(existing_runs)
        for name in (() if existing_runs else names):
            registry = MethodRegistry((method,), MethodsFile(configs={method.name: {name: configs[name]}}))
            graph = Graph(((Stage.LINK, (Step(f"{method.name}/{name}"),)),))
            result = run_source_methods(engine, project_id=PROJECT, prepared=prepared, binding=OperationBinding(release, realization, 0, canonical_bytes({"frozen_product": reports[name].product_id, "supplied_readings": True, "provider_execution": "not_run"})), registry=registry, graph=graph, method_settings=MethodSettings(data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache), domain="statistics")
            producer_runs.append(result.run_id)
            with engine.begin() as conn:
                producer_cut = seal_cut(conn, result.run_id, "normal-single-product-final", final=True)
            consolidate_cut(engine, producer_cut, f"pce-normal-single-result:{result.run_id}")
        # The fixed normal runner currently binds one configuration per method.
        # Its distinct operation manifests correctly prevent cross-config reuse.
        # Compose a private cut by the existing deterministic native import owner,
        # preserving the separate genuine normal-runner execution evidence above.
        with engine.begin() as conn:
            runtime_binding = prepare_runtime_binding(prepared)
            persist_runtime_binding(conn, prepared, runtime_binding)
            joined = create_run(conn, project_id=PROJECT, binding=OperationBinding(release, realization, 0, canonical_bytes({"producer_runs": producer_runs, "frozen_products": [r.product_id for r in reports.values()]})), kind="full", options={"structural_private": True, "domain": "statistics"}, code_commit=code_commit(), prepared=prepared, runtime_binding=runtime_binding)
            start_run(conn, joined, prepared=prepared)
            source_tasks = list(conn.execute(text("SELECT * FROM ops.task WHERE run_id=ANY(:runs) ORDER BY id"), {"runs": producer_runs}).mappings())
            assert len(source_tasks) == 4 and {t['unit_key'] for t in source_tasks} == {r.product_id for r in reports.values()}
            producers = list(conn.execute(text('SELECT status,runtime_id,release_id FROM ops.run WHERE id=ANY(:runs)'), {'runs':producer_runs}).mappings())
            assert len(producers) == 4 and all(p['status']=='finished' and p['runtime_id']==runtime_binding.runtime_id and p['release_id']==release for p in producers)
            for task in source_tasks:
                target = create_task(conn, run_id=joined, config_id=task['method_config_id'], stage=task['stage'], unit_type=task['unit_type'], unit_id=task['unit_id'], unit_key=task['unit_key'], packet_hash=task['packet_hash'], input_hash=task['input_hash'])
                row = conn.execute(text('SELECT status,reused_task_id FROM ops.task WHERE id=:t'), {'t':target}).mappings().one()
                assert row['status'] == 'pending' and row['reused_task_id'] is None
                claim = claim_tasks(conn, run_id=joined, config_id=task['method_config_id'], holder='normal-structural-composition', prepared=prepared)[0]
                name = next(name for name, report in reports.items() if report.product_id == task['unit_key'])
                cfg = StructuralProductsConfig.model_validate(configs[name])
                result = method.run((SimpleNamespace(ref=UnitRef(TaskUnitType.RUN, unit_key=task['unit_key'])),), cfg, None)[0]
                identity = conn.execute(text('SELECT t.input_hash,t.invocation_key,c.config_hash FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id WHERE t.id=:t'), {'t':target}).mappings().one()
                envelope = bind_result(prepared, source=task['unit_key'], method=method.name, operation_version=method.version, configuration_hash=identity['config_hash'], input_hash=identity['input_hash'], invocation_key=identity['invocation_key'], result=result).model_dump(mode='json')
                complete_task(conn, task_id=target, attempt=claim.attempt, holder=claim.holder, prepared=prepared, observations=(), outcome='done', envelope=envelope)
            cut = seal_cut(conn, joined, "normal-structural-final", final=True)
        completed = consolidate_cut(engine, cut, f"pce-normal-structural-result:{joined}")
        with engine.connect() as conn:
            tasks = [dict(row) for row in conn.execute(text("SELECT t.id task_id,t.status,t.reused_task_id,t.unit_key,r.body->'structural_product' product FROM ops.task t JOIN ops.task_result r ON r.task_id=coalesce(t.reused_task_id,t.id) WHERE t.run_id=:r ORDER BY t.id"), {"r": joined}).mappings()]
            for task in tasks:
                task["product_id"] = StructuralProductReport.model_validate(task.pop("product")).product_id
            runtime = conn.execute(text("SELECT runtime_id FROM ops.run WHERE id=:r"), {"r": joined}).scalar_one()
            after = dict(conn.execute(text("SELECT * FROM data.project WHERE project_id=:p"), {"p": PROJECT}).mappings().one())
    assert before == after
    assert {r["product_id"] for r in tasks} == {r.product_id for r in reports.values()}
    payload = {"outcome": "passed", "scope": "four separate ordinary registered leased RUN executions plus deterministic native private-cut composition of the same immutable supplied readings", "run_id": joined, "producer_runs": producer_runs, "cut_id": cut, "release_id": release, "runtime_id": runtime, "tasks": tasks, "result_realization_id": completed.realization_id, "defaults_activated": False, "project_defaults_before": before, "project_defaults_after": after, "source_reports": [f"production-{name}-005.json" for name in names], "provider_execution": "not_run", "quality_claim": "separate independent exposed-development assessment", "multi_configuration_normal_graph": "not supported: configurations currently keyed by method name; preserved failed001/002 attempts"}
    with (HERE / f"raw/normal-structural-run-{attempt}.json").open("xb") as output:
        output.write(canonical_bytes(payload) + b"\n")
    print(json.dumps(payload))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True)
    parser.add_argument("--attempt", default="001")
    parser.add_argument("--producer-runs", nargs=4, type=int, default=())
    args = parser.parse_args()
    main(args.release, args.attempt, args.producer_runs)
