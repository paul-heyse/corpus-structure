"""Prepare source-only opportunities, native Dipo requests, and exactly bound /11 arms."""

import argparse
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    OperationEvaluationFrameV2,
    OperationSourceOpportunity,
    encode_frame,
)
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidatesWithQueryContext,
    ContextualQueryConfig,
)
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
    component_target_input,
)
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contributions import anchor_identity, occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PRIOR = HERE.parent / "2026-11-09_pm2-bounded-retrieval"
OLDER = HERE.parent / "2026-11-09_pm2-adoption"
CASE_SPECS = (
    ("binomial-use", 1820, 0, (1816, 2009), "stated"),
    ("normal-density-use", 2635, 0, (2472, 2709), "stated"),
    ("negative-binomial-control", 7436, 9, (7420, 7508), "stated"),
    ("exponential-density-use", 9074, 0, (8767, 9217), "stated"),
)
EXCLUDED = {
    "the distribution function": "retained content is a particular coin mass assignment",
    "the binomial coefficient": "retained content is only zero, without its condition",
    "the expected value": "truncated source qualification after the equation",
    "the support": "retained content is only 'the set'",
    "the normal distribution": "retained content describes area rather than the distribution",
    "the mean": "retained content conflates mean and variance fragments",
}
QUESTION = "retained producer occurrence roles and contextual encoder products"
GUIDELINE = "pm2-competitive-retrieval-1"


def load(path):
    return json.loads(path.read_bytes())


def source_cases():
    all_rows = load(RAW / "source-opportunities.json")["opportunities"]
    old = load(OLDER / "raw/retrieval-case-source.json")
    pin = old["cross-chapter-binomial"]["anchor"]["pin"]
    rows = {}
    for key, position, extend, extent, state in CASE_SPECS:
        (row,) = [row for row in all_rows if row["start"] == position]
        start, end = position - extend, row["end"]
        piece = row["piece"]
        if not piece["start"] <= start < end <= piece["end"]:
            raise ValueError("source-only opportunity crosses a native text piece")
        focal = row["text"][start - row["context_start"] : end - row["context_start"]]
        anchor = dict(
            pin=pin,
            pointer=piece["item_ref"],
            space="native",
            precision="exact",
            start=start - piece["start"],
            end=end - piece["start"],
            source_piece=focal,
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        rows[key] = dict(
            anchor=anchor,
            occurrence_id=occurrence_identity((anchor,)),
            start=start,
            end=end,
            extent=extent,
            state=state,
        )
    return rows


def parser_request():
    request = load(PRIOR / "raw/dipo-request.json")
    sample = request["scopes"][1]
    request["scopes"] = [dict(sample, extent=row["extent"]) for row in source_cases().values()]
    return request


def contexts(parser, cases):
    run = table("ops.run")
    with (
        open_runtime_engine(Settings(), "pm2-competitive-context", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        selected = bind_completed_result(conn, parser["run_id"])
        project, runtime = conn.execute(
            select(run.c.project_id, run.c.runtime_id).where(run.c.id == parser["run_id"])
        ).one()
        bindings = []
        for row in cases.values():
            (scope,) = [
                scope
                for scope in parser["scope_coverage"]
                if tuple(scope["extent"]) == row["extent"] and scope["outcome"] == "succeeded"
            ]
            page = read_source_contributions(
                conn,
                prepared=selected.prepared,
                run_id=parser["run_id"],
                cut_id=selected.completed_cut_id,
                source_view_id=391,
                selected_task_id=scope["task_id"],
                method="extract.pm2_dipo",
                include_details=True,
                limit=1000,
            )
            (root,) = [item for item in page.contributions if item["semantic_type"] == "dipo.tree"]
            bindings.append(
                dict(
                    occurrence_id=row["occurrence_id"],
                    evidence=dict(
                        contribution_id=root["contribution_id"],
                        project_id=project,
                        run_id=parser["run_id"],
                        cut_id=selected.completed_cut_id,
                        release_id=selected.prepared.release_id,
                        result_revision=selected.binding.data_revision,
                        selected_task_id=root["selected_task_id"],
                        origin_task_id=root["origin_task_id"],
                        runtime_fingerprint=runtime,
                    ),
                )
            )
    return dict(recipe="located-discourse-neighbor-1", bindings=bindings)


def freeze(parser):
    frozen = load(PRIOR / "raw/binomial-frozen.json")
    cases = source_cases()
    inventory = load(RAW / "competitive-targets.json")
    targets = tuple(
        ExtractedComponentTarget.model_validate(t)
        for t in inventory["targets"]
        if t["label"].casefold() not in EXCLUDED
    )
    if len(targets) != 8:
        raise ValueError("reviewed inventory differs from its frozen population")
    registry_id, _ = component_target_input(targets)
    focal_pointers = list(dict.fromkeys(row["anchor"]["pointer"] for row in cases.values()))
    frozen["upstream"][1][1]["region_pointers"] = focal_pointers
    config = dict(
        frozen["config_by_arm"]["literal"],
        target_components=[target.model_dump(mode="json") for target in targets],
        required_occurrence_ids=[row["occurrence_id"] for row in cases.values()],
    )
    signal = contexts(parser, cases)
    configs = {"literal": config, "enriched": dict(config, query_context=signal)}
    cfgs = {
        arm: ContextualQueryConfig.model_validate(cfg).model_dump(mode="json")
        for arm, cfg in configs.items()
    }
    method = ContextualCandidatesWithQueryContext()
    hashes = {
        arm: MethodRegistry((method,), MethodsFile(configs={method.name: {"bounded": cfg}}))
        .resolve(method.name, "bounded", artifacts={})
        .config_hash
        for arm, cfg in cfgs.items()
    }
    if len(set(hashes.values())) != 2 or any(
        b["evidence"]["release_id"] != frozen["release"] for b in signal["bindings"]
    ):
        raise ValueError("comparison arms are not distinct and release bound")
    return dict(frozen, cases=list(cases), config_by_arm=cfgs, hashes=hashes, registry=registry_id)


def sample(frozen):
    cases = source_cases()
    pin = next(iter(cases.values()))["anchor"]["pin"]
    frame = OperationEvaluationFrameV2(
        unit=pin["source"],
        release_id=frozen["release"],
        guideline_version=GUIDELINE,
        rubric_version=GUIDELINE,
        context_policy=GUIDELINE,
        operation_question=QUESTION,
        operation_version="11",
        domain="statistics",
        direction="source_first",
        pin=pin,
        anchor_ids=tuple(row["anchor"]["anchor_id"] for row in cases.values()),
        source_group="grinstead-snell",
        partition="development",
        inspected_scope="view 391: four exact source opportunity windows",
        opportunities=tuple(
            OperationSourceOpportunity(
                key,
                391,
                row["start"],
                row["end"],
                "selection" if key == "negative-binomial-control" else "top10_availability",
                row["state"],
            )
            for key, row in cases.items()
        ),
        exposure_history=(
            "Book origin previously used for method development; binomial control exposed.",
        ),
    )
    return dict(
        frames={frame.unit: encode_frame(frame)},
        sampling=dict(
            panel="pm2-competitive-retrieval",
            seed=0,
            strata={frame.unit: "source-authored-development"},
            inclusion_probabilities={frame.unit: 1},
            provenance={"selection": "four exact source opportunity windows"},
            cohort="Grinstead-Snell exposed development",
            comparison_arms={
                name: {
                    frame.unit: dict(
                        method="retrieve.contextual",
                        method_version="11",
                        operation_question=QUESTION,
                        operation_version="11",
                        configuration_hash=frozen["hashes"][arm],
                    )
                }
                for name, arm in (("baseline", "literal"), ("revised", "enriched"))
            },
        ),
    )


def source_reference(binding):
    from corpus_structure.core.provenance import code_commit
    from corpus_structure.semantic._operation_calls import select_source_view
    from corpus_structure.semantic._operation_ids import RunId, SourceViewId
    from corpus_structure.semantic.operations import (
        OperationBinding,
        create_run,
        seal_cut,
        start_run,
    )
    from corpus_structure.semantic.releases import open_release

    prior = runpy.run_path(str(OLDER / "prepare_retrieval.py"))
    with (
        open_runtime_engine(Settings(), "pm2-competitive-reference", purpose="write") as engine,
        engine.begin() as conn,
    ):
        prepared = open_release(conn, binding["release"])
        revision = prior["input_revision"](conn, binding)
        run_id = create_run(
            conn,
            project_id=binding["project"],
            binding=OperationBinding(
                binding["release"],
                binding["realization"],
                revision,
                canonical_bytes({"scope": GUIDELINE}),
            ),
            kind="slice",
            options={"source_reference_only": True},
            code_commit=code_commit(),
            prepared=prepared,
        )
        start_run(conn, run_id, prepared=prepared)
        select_source_view(
            conn,
            run_id=run_id,
            source_run_id=RunId(407),
            source_view_id=SourceViewId(391),
            projection_context=prepared,
        )
        cut_id = seal_cut(conn, run_id, "source-ready")
    return dict(run_id=run_id, cut_id=cut_id)


def carriers():
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.core.vocab import Stage
    from corpus_structure.methods.m1_annotations import M1Annotations
    from corpus_structure.methods.m1_source import M1Candidates
    from corpus_structure.orchestrate.runner import Graph, Step
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.semantic.operations import OperationBinding
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.structural_products import StructuralInput

    prior = runpy.run_path(str(OLDER / "prepare_retrieval.py"))
    frozen = load(PRIOR / "raw/binomial-frozen.json")
    annotation, candidate = M1Annotations(), M1Candidates()
    a, b = [row[1] for row in frozen["upstream"]]
    cases = source_cases()
    b["region_pointers"] = list(dict.fromkeys(row["anchor"]["pointer"] for row in cases.values()))
    registry = MethodRegistry(
        (annotation, candidate),
        MethodsFile(
            configs={
                annotation.name: {"bounded": a},
                candidate.name: {"bounded": b},
            }
        ),
    )
    sources = StructuralInput.model_validate(load(OLDER / "raw/query-inputs.json")).sources
    with open_runtime_engine(
        Settings(), "pm2-competitive-carrier-preflight", purpose="write"
    ) as engine:
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, frozen["release"])
            revision = prior["input_revision"](conn, frozen)
        result = run_source_methods(
            engine,
            project_id=frozen["project"],
            prepared=prepared,
            binding=OperationBinding(
                frozen["release"],
                frozen["realization"],
                revision,
                canonical_bytes({"scope": GUIDELINE, "cases": cases}),
            ),
            registry=registry,
            graph=Graph(
                (
                    (
                        Stage.SCOPE,
                        (
                            Step(annotation.name + "/bounded"),
                            Step(candidate.name + "/bounded", upstream=(annotation.name,)),
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


def carrier_read(run_id):
    cases = source_cases()
    with (
        open_runtime_engine(Settings(), "pm2-competitive-carrier-read", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        selected = bind_completed_result(conn, run_id)
        coverage = {}
        for name, case in cases.items():
            page = read_source_contributions(
                conn,
                prepared=selected.prepared,
                run_id=run_id,
                source_view_id=391,
                cut_id=selected.completed_cut_id,
                method="extract.m1_candidates",
                occurrence_id=case["occurrence_id"],
                include_details=True,
                limit=50,
            )
            found = [
                row["contribution_id"]
                for row in page.contributions
                if row["semantic_type"] == "source_occurrence"
                and list(row["anchors"]) == [case["anchor"]]
            ]
            coverage[name] = dict(occurrence_id=case["occurrence_id"], contributions=found)
        return dict(
            run_id=run_id,
            cut_id=selected.completed_cut_id,
            coverage=coverage,
            ready=all(row["contributions"] for row in coverage.values()),
        )


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "stage",
        choices=(
            "source",
            "parser",
            "carrier",
            "carrier-read",
            "freeze",
            "sample",
            "reference",
            "run",
        ),
    )
    cli.add_argument("--arm", choices=("literal", "enriched"))
    cli.add_argument("--input", type=Path)
    cli.add_argument("--run-id", type=int)
    args = cli.parse_args()
    if args.stage == "run":
        prior = runpy.run_path(str(PRIOR / "run_control.py"))
        result = prior["run"](SimpleNamespace(frozen=args.input, arm=args.arm))
    else:
        result = {
            "source": source_cases,
            "parser": parser_request,
            "carrier": carriers,
            "carrier-read": lambda: carrier_read(args.run_id),
            "freeze": lambda: freeze(load(args.input)),
            "sample": lambda: sample(load(args.input)),
            "reference": lambda: source_reference(load(args.input)),
        }[args.stage]()
    print(canonical_bytes(result).decode())


if __name__ == "__main__":
    main()
