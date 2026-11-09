"""Reproduce the bounded retained-source retrieval experiment, one native stage at a time."""

import argparse
import json
from pathlib import Path

import yaml
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate.operation_assessment import (
    OperationEvaluationFrameV2,
    OperationSourceOpportunity,
    encode_frame,
)
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidatesWithNamedBindings,
    ContextualCandidatesWithQueryContext,
)
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.m1_source import M1Candidates
from corpus_structure.methods.scoped_relations import ScopedRelationsWithRoleClosure
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic._operation_ids import RunId, SourceViewId
from corpus_structure.semantic.contributions import anchor_identity, occurrence_identity
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, create_run, seal_cut, start_run
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PREVIOUS = HERE.parent / "2026-11-09_pm2-interpretation/raw"
PARSERS = HERE.parent / "2026-11-08_pm2-parsers/raw"
SOURCE = 407
SCOPE = "grinstead-snell-physical-1-518"
RETRIEVAL_QUESTION = "retained producer occurrence roles and contextual encoder products"
QUERIES = (("affine", 391, 61694, 61942), ("binomial-use", 391, 1816, 2009))
DEFINITIONS = (
    ("random-variable", 383, 811, 907),
    ("binomial-distribution", 387, 52066, 52355),
    ("normal-density", 391, 59211, 59395),
    ("standard-normal", 393, 91884, 91974),
    ("constant-density", 393, 107620, 107792),
    ("fair-coin-control", 389, 18091, 18193),
)


def load(path):
    return json.loads(path.read_bytes())


def retain(name, value):
    (RAW / name).write_bytes(canonical_bytes(value) + b"\n")


def input_revision(conn, binding):
    realization = table("data.realization")
    return conn.execute(select(realization.c.data_revision).where(
        realization.c.realization_id == binding["realization"],
        realization.c.release_id == binding["release"],
        realization.c.project_id == binding["project"],
    )).scalar_one()


def inputs(engine, windows, inventory):
    frozen = prepare_structural_sources(
        engine,
        tuple(
            StructuralPassageSelection(
                run_id=SOURCE, source_view_id=view, passage_id=name,
                start=start, end=end, scope=SCOPE,
            )
            for name, view, start, end in windows
        ),
        read_budget=PublishedReadBudget(max_rows=100_000, max_bytes=256 * 1024 * 1024),
    )
    if any(
        (ref.native_task_id, ref.native_product_key, ref.native_content_digest) != (
            1627, "integrated",
            "35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb",
        )
        for ref in frozen.sources
    ):
        raise ValueError("selected windows differ from the retained book source")
    return StructuralInput(
        question="Find source-located terms and evidence under declared scope",
        scope=SCOPE, inventory_id=inventory, policy_id="source-grounded-private-proposals-2",
        sources=frozen.sources, passages=frozen.passages,
        dependencies=tuple(ref.identity for ref in frozen.sources),
    )


def run(settings, binding, sources, stages, receipt):
    if (RAW / receipt).exists():
        raise ValueError("native attempt already has a receipt; finalize or inspect it by ID")
    registry = MethodRegistry(
        tuple(method for method, _, _ in stages),
        MethodsFile(configs={method.name: {"paired": cfg} for method, cfg, _ in stages}),
    )
    with open_runtime_engine(settings, "pm2-retrieval-pair", purpose="write") as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, binding["release"])
            revision = input_revision(conn, binding)
        result = run_source_methods(
            engine, project_id=binding["project"], prepared=prepared,
            binding=OperationBinding(
                binding["release"], binding["realization"], revision,
                canonical_bytes({"scope": SCOPE, "input": "pm2-bounded-retrieval-pair"}),
            ),
            registry=registry,
            graph=Graph(((Stage.SCOPE, tuple(
                Step(method.name + "/paired", upstream=upstream)
                for method, _, upstream in stages
            )),), policy_propose=False),
            method_settings=MethodSettings(
                data_dir=Path("build/models/pm2/adoption"), model_cache=Path.home()/".cache/docling/models"
            ),
            selected_sources=sources, kind="slice",
        )
    retain(receipt, result.model_dump(mode="json"))
    print(result.model_dump_json())


def targets(conn, run_id):
    session = bind_completed_result(conn, run_id)
    page = serve_structural_products(
        conn, StructuralRequest(run_id=run_id, kind="definition_components"),
    )
    (report,) = page.reports
    (task,) = page.task_ids
    run, membership, tasks = map(table, ("ops.run", "ops.cut_task", "ops.task"))
    runtime, origin = conn.execute(select(run.c.runtime_id, membership.c.origin_task_id)
        .select_from(run.join(tasks, tasks.c.run_id == run.c.id)
                     .join(membership, membership.c.task_id == tasks.c.id))
        .where(membership.c.cut_id == page.cut_id, tasks.c.id == task, run.c.id == run_id)).one()
    return [
        dict(
            reference=dict(
                product_id=report.product_id, component_id=c.component_id,
                operation_id="structure.definition_components", operation_version="9",
                project_id=report.inputs.sources[0].project_id, run_id=run_id,
                cut_id=page.cut_id, release_id=page.release_id,
                result_revision=session.binding.data_revision, selected_task_id=task,
                origin_task_id=origin, runtime_fingerprint=runtime,
                dependencies=report.inputs.dependencies,
            ),
            label=c.term.text, description=c.content.text, scope=c.scope,
            effective_version=c.effective_version,
        )
        for c in report.definition_components.components if c.interpretation == "definition"
    ]


def freeze_reference(settings, binding, query):
    source = query.sources[0]
    original = load(RAW / "source-cut-514-views.json")
    comparator = load(RAW / "m1-cut-517-views.json")
    if original != comparator or len(original) != 29:
        raise ValueError("source and comparator do not select the same book worklist")
    (view,) = [row for row in original if row["id"] == source.source_view_id]
    pin = dict(
        source=view["key"], source_view_id=source.source_view_id,
        native_product_task_id=source.native_task_id, product_key=source.native_product_key,
        product_digest=source.native_content_digest, projection_digest=source.projection_digest,
        recipe_digest=source.recipe_digest,
    )
    affine, binomial = query.passages
    equation = affine.text.index("X = σZ + μ")
    locations = (
        ("affine-x", "selection", affine, "#/texts/11503", 0, equation, "X"),
        ("affine-z", "witness", affine, "#/texts/11503", 0, equation+5, "Z"),
        ("cross-chapter-binomial", "top10_availability", binomial, "#/texts/9829", 0, 4,
         "binomial distribution"),
        ("empty-adverb", "empty_outcome", affine, "#/texts/11503", 0,
         affine.text.index("above"), "above"),
    )
    opportunities = []
    case_source = {}
    for case, facet, passage, pointer, native_offset, start, literal in locations:
        end = start + len(literal)
        if passage.text[start:end] != literal:
            raise ValueError("the frozen literal does not resolve to its exact source")
        anchor = dict(pin=pin, pointer=pointer, space="native", precision="exact",
                      start=start+native_offset, end=end+native_offset, source_piece=literal)
        anchor["anchor_id"] = anchor_identity(anchor)
        case_source[case] = dict(anchor=anchor, occurrence_id=occurrence_identity((anchor,)))
        opportunities.append(OperationSourceOpportunity(
            case, source.source_view_id, passage.start+start, passage.start+end, facet,
            "unstated" if case == "empty-adverb" else "stated",
        ))
    guideline = "pm2-bounded-retrieval-1"
    frame = OperationEvaluationFrameV2(
        unit=view["key"], release_id=binding["release"], guideline_version=guideline,
        rubric_version=guideline, context_policy=guideline, operation_question=RETRIEVAL_QUESTION,
        operation_version="10", domain="statistics", direction="source_first", pin=pin,
        anchor_ids=tuple(value["anchor"]["anchor_id"] for value in case_source.values()),
        source_group="grinstead-snell", partition="development",
        inspected_scope="view 391: two exact source passages for native retrieval",
        opportunities=tuple(opportunities),
        exposure_history=("Previous development investigated the affine controls on this origin.",),
    )
    retain("retrieval-case-source.json", case_source)
    retain("retrieval-sample.json", dict(
        frames={frame.unit: encode_frame(frame)},
        sampling=dict(
            panel="pm2-retained-source-retrieval", seed=0,
            strata={frame.unit: "source-authored-development"},
            inclusion_probabilities={frame.unit: 1},
            provenance={"selection": "fixed source-first development controls"},
            cohort="Grinstead–Snell exposed development",
            comparison_arms={
                arm: {frame.unit: dict(method="retrieve.contextual", method_version=version,
                                       operation_question=RETRIEVAL_QUESTION,
                                       operation_version=version)}
                for arm, version in (("baseline", "10"), ("revised", "11"))
            },
        ),
    ))
    if (RAW / "retrieval-source-cut.json").exists():
        return
    from corpus_structure.core.provenance import code_commit

    with open_runtime_engine(settings, "pm2-retrieval-reference", purpose="write") as engine:
        with engine.begin() as conn:
            prepared = open_release(conn, binding["release"])
            revision = input_revision(conn, binding)
            run_id = create_run(
                conn, project_id=binding["project"], binding=OperationBinding(
                    binding["release"], binding["realization"], revision,
                    canonical_bytes({"scope": "pm2-retained-source-retrieval-reference"}),
                ), kind="slice", options={"source_reference_only": True},
                code_commit=code_commit(), prepared=prepared,
            )
            start_run(conn, run_id, prepared=prepared)
            select_source_view(conn, run_id=run_id, source_run_id=RunId(SOURCE),
                               source_view_id=SourceViewId(source.source_view_id),
                               projection_context=prepared)
            cut_id = seal_cut(conn, run_id, "source-ready")
    retain("retrieval-source-cut.json", {"run_id": run_id, "cut_id": cut_id})
    print(json.dumps({"run_id": run_id, "cut_id": cut_id}))


def parser_binding(settings, carrier_run):
    result = load(RAW / "retrieval-dipo-result.json")
    cases = load(RAW / "retrieval-case-source.json")
    focal_tasks = {"affine-x": 0, "affine-z": 0, "cross-chapter-binomial": 1}
    with (
        open_runtime_engine(settings, "pm2-retrieval-context", purpose="read") as reader,
        read_snapshot(reader) as conn,
    ):
        session = bind_completed_result(conn, result["run_id"])
        run = table("ops.run")
        runtime, project = conn.execute(select(run.c.runtime_id, run.c.project_id)
                                        .where(run.c.id == result["run_id"])).one()
        carrier = bind_completed_result(conn, carrier_run)
        if carrier.prepared.release_id != result["release"]:
            raise ValueError("carrier and parser were not completed under the same release")
        carriers = read_source_contributions(
            conn, prepared=carrier.prepared, run_id=carrier_run, cut_id=carrier.completed_cut_id,
            source_view_id=391, method="extract.m1_candidates", include_details=True, limit=1000,
        )
        available = {row["occurrence_id"] for row in carriers.contributions
                     if row["semantic_type"] == "source_occurrence"}
        refs = {}
        bound = []
        for name, position in focal_tasks.items():
            occurrence = cases[name]["occurrence_id"]
            if occurrence not in available:
                continue
            task_id = result["tasks"][position]
            if task_id not in refs:
                reports = read_source_contributions(
                    conn, prepared=session.prepared, run_id=result["run_id"],
                    cut_id=result["cut_id"], source_view_id=391, selected_task_id=task_id,
                    method="extract.pm2_dipo", include_details=True, limit=1000,
                )
                (root,) = [row for row in reports.contributions if row["semantic_type"] == "dipo.tree"]
                refs[task_id] = dict(
                    contribution_id=root["contribution_id"], project_id=project,
                    run_id=result["run_id"], cut_id=result["cut_id"], release_id=result["release"],
                    result_revision=session.binding.data_revision,
                    selected_task_id=root["selected_task_id"], origin_task_id=root["origin_task_id"],
                    runtime_fingerprint=runtime,
                )
            bound.append(dict(occurrence_id=occurrence, evidence=refs[task_id]))
        if not bound:
            raise ValueError("the bounded producer lacks every prespecified occurrence carrier")
    retain("retrieval-dipo-context.json", {
        "recipe": "located-discourse-neighbor-1",
        "bindings": sorted(bound, key=lambda row: row["occurrence_id"]),
    })


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("stage", choices=("freeze", "freeze-query", "reference", "parser-binding", "scoped", "carrier", "targets", "inventory", "baseline", "revised"))
    cli.add_argument("--target-run", type=int)
    cli.add_argument("--carrier-run", type=int)
    cli.add_argument("--query-context", type=Path)
    args = cli.parse_args()
    binding = load(PREVIOUS / "development-source-request.json")
    settings = Settings()
    if args.stage in {"freeze", "freeze-query"}:
        with open_runtime_engine(settings, "pm2-retrieval-source", purpose="read") as reader:
            query = inputs(reader, QUERIES, "pm2-retrieval-query-windows")
            retain("query-inputs.json", query.model_dump(mode="json"))
            parser = load(PARSERS / "book-parser-request.json")
            parser.update(release=binding["release"], realization=binding["realization"])
            profiles = {
                scope["profile"]["provider"]: scope["profile"] for scope in parser["scopes"]
                if scope.get("mode", "ordinary") == "ordinary"
            }
            parser["scopes"] = [
                dict(source=query.sources[0].model_dump(mode="json"), extent=[start, end],
                     profile=profiles[provider])
                for _, _, start, end in QUERIES for provider in ("hanlp", "dipo")
            ]
            retain("retrieval-parser-request.json", parser)
            if args.stage == "freeze-query":
                print(json.dumps({"query_windows": len(QUERIES)}))
                return
            target = inputs(reader, DEFINITIONS, "pm2-retrieval-target-windows")
            retain("target-inputs.json", target.model_dump(mode="json"))
        print(json.dumps({"query_windows": len(QUERIES), "target_windows": len(DEFINITIONS)}))
        return
    query = StructuralInput.model_validate(load(RAW / "query-inputs.json"))
    if args.stage == "reference":
        freeze_reference(settings, binding, query)
        return
    if args.stage == "parser-binding":
        if not args.carrier_run:
            cli.error("parser binding requires the completed bounded occurrence producer")
        parser_binding(settings, args.carrier_run)
        return
    scoped = ScopedRelationsWithRoleClosure()
    scoped_cfg = dict(
        inputs=query.model_dump(mode="json"), structural_input_digest=query.identity,
        interpretation_mode="feasibility",
    )
    if args.stage == "scoped":
        run(settings, binding, query.sources, ((scoped, scoped_cfg, ()),), "scoped-ready.json")
        return
    annotations, producer = M1Annotations(), M1Candidates()
    m1 = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_text())["configs"]
    projection = query.sources[0].projection_digest
    carrier_stages = (
        (annotations, {"source_projection_digest": projection}, ()),
        (producer, dict(m1[producer.name]["default"], source_projection_digest=projection,
                        region_pointers=["#/texts/11503", *(f"#/texts/{i}" for i in range(9829, 9836))]),
         (annotations.name,)),
    )
    if args.stage == "carrier":
        run(settings, binding, query.sources, carrier_stages, "carrier-ready.json")
        return
    if args.stage == "targets":
        target = StructuralInput.model_validate(load(RAW / "target-inputs.json"))
        config = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_text())["configs"][
            "extract.m1_candidates"
        ]
        profile = {
            key: config["default"][key]
            for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")
        }
        run(settings, binding, target.sources, ((DefinitionComponentsMethod(), dict(
            inputs=target.model_dump(mode="json"), structural_input_digest=target.identity,
            target_ids=tuple(p.passage_id for p in target.passages), profile=profile,
            annotation_rules=config["witnessed"]["annotation_rules"],
        ), ()),), "targets-ready.json")
        return
    if not args.target_run:
        cli.error("paired retrieval requires the exact completed target run")
    source = query.sources[0]
    with (
        open_runtime_engine(settings, "pm2-retrieval-targets", purpose="read") as reader,
        read_snapshot(reader) as conn,
    ):
        components = targets(conn, args.target_run)
    if args.stage == "inventory":
        retain("retrieval-target-inventory.json", components)
        print(json.dumps({"targets": len(components)}))
        return
    cfg = dict(
        profile="e5", source_dependency_method=producer.name,
        semantic_types=["source_occurrence"],
        target_components=components,
        relationship_constraints=[dict(
            constraint_id="source-observed-term-denotation", relation_kinds=["denotes"],
            occurrence_role="observed_source_mention", target_role="retained_definition_component",
            multiplicity="one", exhaustive=False,
        )],
        source_product_digest=source.native_content_digest,
        source_projection_digest=source.projection_digest, scope=SCOPE,
        unique_target_budget=10, channel_budget=30,
    )
    linker = ContextualCandidatesWithNamedBindings()
    if args.stage == "revised":
        if args.query_context is None:
            cli.error("v11 requires one exact retained parser context recipe")
        linker = ContextualCandidatesWithQueryContext()
        cfg["query_context"] = load(args.query_context)
    retain(f"{args.stage}-configuration.json", cfg)
    run(settings, binding, query.sources, (*carrier_stages, (
        linker, cfg, (producer.name,),
    )), f"{args.stage}-ready.json")


if __name__ == "__main__":
    main()
