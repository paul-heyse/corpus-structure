"""Run current registered construction against the recovered, shared GS120 sources."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml
from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.m1_source import M1Candidates
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
sys.path.insert(0, str(EVIDENCE / "source-recovery"))
from recover_sources import admit_current  # noqa: E402


def retain(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt")
    parser.add_argument("--mode", choices=("named", "model"), required=True)
    args = parser.parse_args()
    output = HERE / (args.mode + args.attempt)
    output.mkdir(exist_ok=False)
    try:
        recovery = EVIDENCE / "source-recovery/attempt001"
        coverage = json.loads((recovery / "coverage.json").read_bytes())
        if coverage["outcome"] != "passed" or coverage["missing_projected_text_pages"]:
            raise ValueError("Full120-page recovered text coverage is required")
        packet = json.loads((recovery / "source-packets/source-packet.json").read_bytes())
        project = packet["sources"][0]["project_id"]
        settings = Settings()
        prepared = admit_current(settings, output)
        with open_runtime_engine(settings, "gs120-current-inputs", purpose="read") as engine:
            with read_snapshot(engine) as conn:
                annotation_tasks = conn.execute(text(
                    "SELECT t.id FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id "
                    "JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=ANY(:runs) "
                    "AND m.name='extract.m1_annotations' AND t.status IN ('done','reused') ORDER BY t.id"
                ), {"runs": [v["run_id"] for v in coverage["source_runs"]]}).scalars().all()
        inputs = StructuralInput.model_validate(dict(
            question="Construct located source knowledge across the shared120-page corpus",
            scope="grinstead-snell-physical191-310",
            inventory_id="gs120:" + packet["source_manifest"]["parent_sha256"],
            policy_id="located-definition-1", sources=packet["sources"], passages=packet["passages"],
            dependencies=list(dict.fromkeys([
                *("native:" + str(s["native_task_id"]) for s in packet["sources"]),
                *("annotation:" + str(t) for t in annotation_tasks),
            ])),
        ))
        declared = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_text())["configs"][M1Candidates.name]
        definition_cfg = dict(inputs=inputs.model_dump(mode="json"), structural_input_digest=inputs.identity,
                              target_ids=[p.passage_id for p in inputs.passages],
                              annotation_rules=declared["witnessed"]["annotation_rules"],
                              use_model=args.mode == "model")
        if args.mode == "model":
            definition_cfg["profile"] = {key: declared["default"][key]
                                         for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")}
        definition = DefinitionComponentsMethod()
        methods = [definition]
        configs = {definition.name: {"current": definition_cfg}}
        steps = [Step(definition.name + "/current")]
        if args.mode == "model":
            methods = [M1Annotations(), M1Candidates(), definition]
            configs.update({M1Annotations.name: {"current": {}}, M1Candidates.name: {"current": declared["witnessed"]}})
            steps = [Step(M1Annotations.name + "/current"),
                     Step(M1Candidates.name + "/current", upstream=(M1Annotations.name,)), *steps]
        registry = MethodRegistry(tuple(methods), MethodsFile(configs=configs))
        retain(output / "configuration.json", dict(mode=args.mode, definition=definition_cfg,
                m1=declared["witnessed"] if args.mode == "model" else None,
                method_versions={m.name: m.version for m in methods},
                source_coverage=coverage, scope="shared exposed development, no held-out claim"))
        realization = "gs120-current:" + args.mode + args.attempt + ":" + prepared.release_id
        with open_runtime_engine(settings, "gs120-current-register", purpose="write") as engine:
            with engine.begin() as conn:
                initialize_source_project(conn, project_id=ProjectId(project), release_id=ReleaseId(prepared.release_id),
                                          realization_id=RealizationId(realization), projection_context=prepared)
        with open_runtime_engine(settings, "gs120-current-construct", purpose="write") as engine:
            with read_snapshot(engine) as conn:
                revision = conn.scalar(select(table("data.realization").c.data_revision).where(
                    table("data.realization").c.realization_id == realization))
                docs = conn.execute(select(table("kb.document")).where(table("kb.document").c.project_id == project)).mappings().all()
                corpus_record, _ = records(docs, {}, slice=None, scope=None, corpus=None)
            run = run_source_methods(engine, project_id=project, prepared=prepared,
                binding=OperationBinding(prepared.release_id, realization, revision, canonical_bytes(dict(
                    corpus=packet["source_manifest"]["parent_sha256"], mode=args.mode,
                    input_digest=inputs.identity, attempt=args.attempt))), registry=registry,
                graph=Graph(((Stage.EXTRACT, tuple(steps)),), policy_propose=False),
                method_settings=MethodSettings(data_dir=output / "data", model_cache=Path.home() / ".cache/docling/models"),
                guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(), corpus_record=corpus_record,
                policy_source=None, kind="full", selected_sources=inputs.sources)
            retain(output / "run.json", run.model_dump(mode="json"))
            if run.status != "source_ready":
                raise ValueError("Current construction did not reach source readiness")
            with engine.begin() as conn:
                cut = seal_cut(conn, run.run_id, "gs120-current-final", final=True)
            retain(output / "sealed.json", dict(run_id=run.run_id, cut_id=cut))
            consolidate_cut(engine, cut, "gs120-current-result:" + str(run.run_id))
        retain(output / "result.json", dict(outcome="passed", run_id=run.run_id, cut_id=cut,
               mode=args.mode, release_id=prepared.release_id, source_views=len(inputs.sources),
               source_pages=120, semantic_quality="unassessed", scope="Current registered construction and native completion"))
        print((output / "result.json").read_text(), flush=True)
    except BaseException as error:
        retain(output / "failure.json", dict(outcome="failed", type=type(error).__name__, message=str(error)))
        raise


if __name__ == "__main__":
    main()
