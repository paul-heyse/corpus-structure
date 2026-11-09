"""Freeze and run literal/enriched controls on the same authenticated carrier inventory."""

import argparse
import json
import runpy
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidatesWithQueryContext,
    ContextualQueryConfig,
)
from corpus_structure.methods.scoped_relations import ScopedRelationsWithOrderedWitness
from corpus_structure.orchestrate.pm2_stage import InterpretationRunRequest
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.contextual_storage import (
    RetainedCandidateListRef,
    read_interpretation_candidates,
)
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader, OperationBinding
from corpus_structure.semantic.query import ReadLimit, bind_completed_result, read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ADOPTION = HERE.parent / "2026-11-09_pm2-adoption"


def load(path):
    return json.loads(path.read_bytes())


def context(args):
    parser = load(args.parser_receipt)
    cases = load(ADOPTION / "raw/retrieval-case-source.json")
    names, extent = (
        (("affine-x", "affine-z"), [61694, 61942])
        if args.population == "affine"
        else (("cross-chapter-binomial",), [1816, 2009])
    )
    (task,) = [
        row["task_id"]
        for row in parser["scope_coverage"]
        if row["extent"] == extent and row["outcome"] == "succeeded"
    ]
    run = table("ops.run")
    with (
        open_runtime_engine(Settings(), "pm2-bounded-retrieval-context", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        selected = bind_completed_result(conn, parser["run_id"])
        project, runtime = conn.execute(
            select(run.c.project_id, run.c.runtime_id).where(run.c.id == parser["run_id"])
        ).one()
        page = read_source_contributions(
            conn,
            prepared=selected.prepared,
            run_id=parser["run_id"],
            cut_id=selected.completed_cut_id,
            source_view_id=391,
            selected_task_id=task,
            method="extract.pm2_dipo",
            include_details=True,
            limit=1000,
        )
        (root,) = [row for row in page.contributions if row["semantic_type"] == "dipo.tree"]
        evidence = dict(
            contribution_id=root["contribution_id"],
            project_id=project,
            run_id=parser["run_id"],
            cut_id=selected.completed_cut_id,
            release_id=selected.prepared.release_id,
            result_revision=selected.binding.data_revision,
            selected_task_id=root["selected_task_id"],
            origin_task_id=root["origin_task_id"],
            runtime_fingerprint=runtime,
        )
    return dict(
        recipe="located-discourse-neighbor-1",
        bindings=[
            dict(occurrence_id=cases[name]["occurrence_id"], evidence=evidence) for name in names
        ],
    )


def freeze(args):
    source_inputs = StructuralInput.model_validate(load(ADOPTION / "raw/query-inputs.json"))
    (source,) = source_inputs.sources
    cases = load(ADOPTION / "raw/retrieval-case-source.json")
    component = load(args.eligible_target)["component"]
    request = load(args.binding)
    prior = runpy.run_path(str(ADOPTION / "prepare_retrieval.py"))
    ordered = runpy.run_path(
        str(HERE.parent / "2026-11-09_pm2-affine-ordered-source/run_ordered_witness.py")
    )
    if args.population == "affine":
        names = ("affine-x", "affine-z")
        producer = ScopedRelationsWithOrderedWitness()
        producer_config = ordered["prepare"](Settings(), request["release"])["configuration"]
        upstream = ((producer.name, producer_config, ()),)
        semantic_types = ["structural.located_participant"]
    else:
        names = ("cross-chapter-binomial",)
        annotations, producer = prior["M1Annotations"](), prior["M1Candidates"]()
        m1 = prior["yaml"].safe_load((prior["DOMAINS"] / "statistics/m1-methods.yaml").read_text())[
            "configs"
        ]
        upstream = (
            (annotations.name, {"source_projection_digest": source.projection_digest}, ()),
            (
                producer.name,
                dict(
                    m1[producer.name]["default"],
                    source_projection_digest=source.projection_digest,
                    region_pointers=[f"#/texts/{i}" for i in range(9829, 9836)],
                ),
                (annotations.name,),
            ),
        )
        semantic_types = ["source_occurrence"]
    config = dict(
        profile="e5",
        source_dependency_method=producer.name,
        semantic_types=semantic_types,
        required_occurrence_ids=[cases[name]["occurrence_id"] for name in names],
        target_components=[component],
        relationship_constraints=[
            dict(
                constraint_id="source-observed-term-denotation",
                relation_kinds=["denotes"],
                occurrence_role="observed_source_mention",
                target_role="retained_definition_component",
                multiplicity="one",
                exhaustive=False,
            )
        ],
        source_product_digest=source.native_content_digest,
        source_projection_digest=source.projection_digest,
        scope=component["scope"],
        unique_target_budget=10,
        channel_budget=30,
    )
    signal = load(args.context)
    if {b["occurrence_id"] for b in signal["bindings"]} != set(config["required_occurrence_ids"]):
        raise ValueError("comparison context differs from the exact carrier set")
    if any(b["evidence"]["release_id"] != request["release"] for b in signal["bindings"]):
        raise ValueError("comparison context belongs to a different release")
    config_by_arm = {
        "literal": ContextualQueryConfig.model_validate(config).model_dump(mode="json"),
        "enriched": ContextualQueryConfig.model_validate(
            dict(config, query_context=signal)
        ).model_dump(mode="json"),
    }
    return dict(
        project=request["project"],
        release=request["release"],
        realization=request["realization"],
        population=args.population,
        cases=names,
        upstream=upstream,
        config_by_arm=config_by_arm,
    )


def run(args):
    frozen = load(args.frozen)
    cfg = ContextualQueryConfig.model_validate(frozen["config_by_arm"][args.arm])
    prior = runpy.run_path(str(ADOPTION / "prepare_retrieval.py"))
    instances = {
        method.name: method
        for method in (
            ScopedRelationsWithOrderedWitness(),
            prior["M1Annotations"](),
            prior["M1Candidates"](),
        )
    }
    linker = ContextualCandidatesWithQueryContext()
    stages = tuple(
        (instances[name], config, tuple(upstream)) for name, config, upstream in frozen["upstream"]
    )
    stages += ((linker, cfg.model_dump(mode="json"), (cfg.source_dependency_method,)),)
    sources = StructuralInput.model_validate(load(ADOPTION / "raw/query-inputs.json")).sources
    settings = Settings()
    registry = MethodRegistry(
        tuple(method for method, _, _ in stages),
        MethodsFile(
            configs={method.name: {"bounded": config} for method, config, _ in stages},
        ),
    )
    with open_runtime_engine(settings, "pm2-bounded-retrieval", purpose="write") as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, frozen["release"])
            revision = prior["input_revision"](conn, frozen)
        result = run_source_methods(
            engine,
            project_id=frozen["project"],
            prepared=prepared,
            binding=OperationBinding(
                frozen["release"], frozen["realization"], revision, canonical_bytes(frozen)
            ),
            registry=registry,
            graph=Graph(
                (
                    (
                        Stage.SCOPE,
                        tuple(
                            Step(method.name + "/bounded", upstream=upstream)
                            for method, _, upstream in stages
                        ),
                    ),
                ),
                policy_propose=False,
            ),
            method_settings=MethodSettings(
                data_dir=Path("build/models/pm2/adoption"),
                model_cache=Path.home() / ".cache/docling/models",
            ),
            selected_sources=sources,
            kind="slice",
        )
    return result.model_dump(mode="json")


def projection(args):
    frozen = load(args.frozen)
    config = frozen["config_by_arm"]["literal"]
    chosen = tuple(config["required_occurrence_ids"])
    types = tuple(config["semantic_types"])
    method = config["source_dependency_method"]
    with (
        open_runtime_engine(Settings(), "pm2-bounded-projection", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        reader = BoundReader(conn, args.run_id, open_release(conn, frozen["release"]))
        try:
            reader.source_result(391, method)
        except ReadLimit as exc:
            if exc.reason != "oversized_item":
                raise
        else:
            raise ValueError("the retained report does not reproduce the original byte limit")
        body = reader.source_result(391, method, occurrence_ids=chosen, semantic_types=types)
        wrong = reader.source_result(391, method, occurrence_ids=chosen, semantic_types=("wrong",))
        if body is None or wrong is None or wrong["contributions"]:
            raise ValueError("bounded producer projection returned an unexpected population")
        occurrences = {row["occurrence_id"] for row in body["contributions"]}
        if occurrences != set(chosen):
            raise ValueError("bounded producer projection changed the configured carrier set")
        return dict(
            run_id=args.run_id,
            outcome="passed",
            full_read="oversized_item",
            occurrences=sorted(occurrences),
            projected_bytes=len(canonical_bytes(body)),
            negative_type_carriers=0,
        )


def interpretation(args):
    parser = load(args.binding)
    profile = load(args.profile)["scopes"][0]["profile"]
    selected_scope = next(row for row in parser["scopes"] if row["extent"] == [1816, 2009])
    scopes = []
    runs = table("ops.run")
    with (
        open_runtime_engine(Settings(), "pm2-bounded-interpretation", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        for path in args.reader:
            page = load(path)
            (operation,) = [row["row"] for row in page["items"] if row["population"] == "operation"]
            (carrier,) = [
                row["row"] for row in page["items"] if row["population"] == "contribution"
            ]
            (candidates,) = operation["contextual_enrichment"]["candidate_lists"]
            (runtime,) = conn.execute(
                select(runs.c.runtime_id).where(runs.c.id == page["run_id"])
            ).one()
            reference = RetainedCandidateListRef.model_validate(
                dict(
                    carrier=dict(
                        contribution_id=carrier["contribution_id"],
                        project_id=parser["project"],
                        release_id=page["binding"]["release_id"],
                        run_id=page["run_id"],
                        cut_id=page["cut_id"],
                        result_revision=page["binding"]["data_revision"],
                        selected_task_id=carrier["selected_task_id"],
                        origin_task_id=carrier["origin_task_id"],
                        runtime_fingerprint=runtime,
                    ),
                    operation_key=operation["operation_key"],
                    list_id=candidates["list_id"],
                )
            )
            inventory = read_interpretation_candidates(
                conn,
                reference,
                source_pin=carrier["pin"],
                project_id=parser["project"],
                release_id=parser["release"],
            )
            if not 1 <= len(inventory.targets) <= 12:
                raise ValueError("candidate list cannot be submitted to the bounded interpreter")
            scopes.append(
                dict(
                    source=selected_scope["source"],
                    extent=selected_scope["extent"],
                    profile=profile,
                    family="contextual_link_assessment_v1",
                    version="2",
                    questions=["concept_link"],
                    retrieval=reference,
                )
            )
    return InterpretationRunRequest.model_validate({**parser, "scopes": scopes}).model_dump(
        mode="json"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    context_command = commands.add_parser("context")
    context_command.add_argument("population", choices=("affine", "binomial"))
    context_command.add_argument("parser_receipt", type=Path)
    freeze_command = commands.add_parser("freeze")
    freeze_command.add_argument("population", choices=("affine", "binomial"))
    freeze_command.add_argument("--binding", required=True, type=Path)
    freeze_command.add_argument("--eligible-target", required=True, type=Path)
    freeze_command.add_argument("--context", required=True, type=Path)
    run_command = commands.add_parser("run")
    run_command.add_argument("arm", choices=("literal", "enriched"))
    run_command.add_argument("frozen", type=Path)
    projection_command = commands.add_parser("projection")
    projection_command.add_argument("run_id", type=int)
    projection_command.add_argument("frozen", type=Path)
    interpret_command = commands.add_parser("interpretation")
    interpret_command.add_argument("--binding", type=Path, required=True)
    interpret_command.add_argument("--profile", type=Path, required=True)
    interpret_command.add_argument("reader", type=Path, nargs=2)
    args = parser.parse_args()
    print(
        canonical_bytes(
            {
                "context": context,
                "freeze": freeze,
                "run": run,
                "projection": projection,
                "interpretation": interpretation,
            }[args.command](args)
        ).decode()
    )


if __name__ == "__main__":
    main()
