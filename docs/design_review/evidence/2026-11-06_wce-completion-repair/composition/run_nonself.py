"""Run the current native R15 source-to-linker route on the frozen GS120 view 117."""

import argparse
from collections import Counter
from hashlib import file_digest
import json
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidates
from corpus_structure.methods.m1_readings import M1Readings
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, inspect_review_bundle
from corpus_structure.serve.structural_products import StructuralExportRequest
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / "2026-11-06_wce-gs120"
sys.path.insert(0, str(OLD / "current-contextual-journey"))
sys.path.insert(0, str(OLD / "current-structural-journey"))

from journey_support import finish_source_stage, retain  # noqa: E402
from run_contextual import capture_named, prepare_inventory, summarize_raw  # noqa: E402

OLD_RELEASE = "release:cb08727ec668c048998c82db31ef0e1242d714ca23e2b0f2a223eb88c6061a29"
NAMED_PRODUCT = "structural:8733a17bdcb1cac3f841def4aad07e00f3034e66bc22b916a609ff74b491af4f"
SOURCE_VIEW = 117
M1_ORIGINAL_TASK = 857


def config(source, report, targets, route):
    if route == "retained-m1":
        producer = M1Readings()
        producer_config = {"retained_source_tasks": [M1_ORIGINAL_TASK]}
        semantic_types = ["source_occurrence"]
    else:
        producer = ScopedRelationsMethod()
        producer_config = {
            "inputs": report.inputs.model_dump(mode="json"),
            "structural_input_digest": report.inputs.identity,
            "interpretation_mode": "feasibility",
        }
        semantic_types = ["structural.located_participant"]
    linker = ContextualCandidates()
    configs = {
        producer.name: {"current": producer_config},
        linker.name: {"current": {
            "profile": "e5",
            "source_dependency_method": producer.name,
            "semantic_types": semantic_types,
            "target_components": targets,
            "relationship_constraints": [{
                "constraint_id": "source-observed-term-denotation",
                "relation_kinds": ["denotes"],
                "occurrence_role": "observed_source_mention",
                "target_role": "retained_definition_component",
                "multiplicity": "one",
                "exhaustive": False,
            }],
            "source_product_digest": source.native_content_digest,
            "source_projection_digest": source.projection_digest,
            "scope": report.inputs.scope,
            "unique_target_budget": len(targets),
            "channel_budget": max(30, len(targets)),
        }},
    }
    registry = MethodRegistry((producer, linker), MethodsFile(configs=configs))
    for method in (producer, linker):
        registry.resolve(method.name, "current")
    return producer, linker, configs, registry


def execute(settings, prepared, report, source, targets, args, output):
    producer, linker, configs, registry = config(source, report, targets, args.upstream)
    producer_step, linker_step = producer.name + "/current", linker.name + "/current"
    retain(output / "configuration.json", {
        "consuming_release": prepared.release_id,
        "named_origin_release": OLD_RELEASE,
        "graph": [producer_step, linker_step],
        "configurations": configs,
        "selected_original_source": source.model_dump(mode="json"),
        "source_population": "one authentic source view from the existing GS120 selection",
        "original_m1_task": M1_ORIGINAL_TASK if args.upstream == "retained-m1" else None,
    })
    if (output / "completed.json").exists():
        run = json.loads((output / "completed.json").read_bytes())
    elif (output / "source-ready.json").exists():
        ready = json.loads((output / "source-ready.json").read_bytes())
        run = finish_source_stage(settings, ready["run_id"], output)
    else:
        realization = f"gs120-r15-nonself:{args.upstream}:{args.attempt}:{prepared.release_id}"
        dependencies = canonical_bytes({
            "purpose": "WCE-R15 actual source-to-linker comparison",
            "source": source.model_dump(mode="json"),
            "retained_definition_product": report.product_id,
            "attempt": args.attempt,
        })
        with open_runtime_engine(settings, "gs120-r15-nonself", purpose="write") as engine:
            with engine.begin() as conn:
                initialize_source_project(
                    conn,
                    project_id=ProjectId(source.project_id),
                    release_id=ReleaseId(prepared.release_id),
                    realization_id=RealizationId(realization),
                    projection_context=prepared,
                )
            with read_snapshot(engine) as conn:
                realized = table("data.realization")
                revision = conn.scalar(select(realized.c.data_revision).where(
                    realized.c.realization_id == realization
                ))
            result = run_source_methods(
                engine,
                project_id=source.project_id,
                prepared=prepared,
                binding=OperationBinding(prepared.release_id, realization, revision, dependencies),
                registry=registry,
                graph=Graph(
                    ((Stage.SCOPE, (Step(producer_step), Step(linker_step, upstream=(producer.name,)))),),
                    policy_propose=False,
                ),
                method_settings=MethodSettings(
                    data_dir=output / "data",
                    model_cache=Path.home() / ".cache/docling/models",
                ),
                guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
                policy_source=None,
                kind="full",
                selected_sources=(source,),
            )
        retain(output / "source-ready.json", result.model_dump(mode="json"))
        if result.status != "source_ready":
            raise ValueError(f"native producer/linker graph stopped at {result.status}")
        run = finish_source_stage(settings, result.run_id, output)
    assert run["release_id"] == prepared.release_id
    return run, producer.name, linker.name


def read_pages(settings, run, methods, output):
    requests = []
    with open_runtime_engine(settings, "gs120-r15-read", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            for method in methods:
                req = ContributionRequest(
                    run_id=run["run_id"],
                    source_view_id=SOURCE_VIEW,
                    method=method,
                    include_interpretation=True,
                    limit=1000,
                    page_bytes=16_000_000,
                    max_bytes=128_000_000,
                )
                requests.append(req)
                pages, current = [], req
                while True:
                    page = serve_contributions(conn, current)
                    pages.append(page.model_dump(mode="json"))
                    if page.next_cursor is None:
                        break
                    current = req.model_copy(update={"cursor": page.next_cursor})
                retain(output / f"{method.replace('.', '-')}-pages.json", pages)
    return requests


def grade(bundle, linker, summary, inventory, output):
    reference_path = HERE.parent / "source-references/source-reference.json"
    ref = json.loads(reference_path.read_bytes())
    with reference_path.open("rb") as stream:
        ref_digest = file_digest(stream, "sha256").hexdigest()
    use = ref["anchors"]["normal-transform-use"]
    evidence = []
    target_ids = {
        target["reference"]["component_id"] for target in inventory["target_components"]
        if "standard normal" in target["label"].casefold().replace("-", " ")
    }
    with (bundle / "reports.jsonl").open("rb") as stream:
        for line in stream:
            raw = json.loads(json.loads(line)["payload_json"])
            if raw.get("method") != linker or raw.get("origin_unit_id") != SOURCE_VIEW:
                continue
            if raw.get("task_status") != "done" or raw.get("task_error"):
                raise ValueError("selected linker producer lacks a successful native result")
            evidence.extend(
                c for c in raw["body"]["contributions"]
                if c["semantic_type"] == "contextual.located_mention"
            )
    assert evidence and summary["candidate_lists"], "native route produced no actual candidates"
    adjacent, exact = [], []
    for item in evidence:
        for anchor in item.get("anchors", ()):
            if anchor["pointer"] != use["native_pointer"] or anchor["precision"] != "exact":
                continue
            if use["native_span"][0] <= anchor["start"] < anchor["end"] <= use["native_span"][1]:
                exact.append(item)
                break
            if anchor["source_piece"] in {"Z", "standard normal random variable Z"}:
                adjacent.append(item)
                break
    decisions = {d["occurrence_id"]: d for d in summary["relationship_decisions"]}
    exact_occurrence_ids = {item["occurrence_id"] for item in exact}
    adjacent_occurrence_ids = {item["occurrence_id"] for item in adjacent}
    coarse = [
        item for item in evidence if any(a["precision"] != "exact" for a in item.get("anchors", ()))
    ]
    exact_decisions = [decisions[k] for k in sorted(exact_occurrence_ids & decisions.keys())]
    selected_targets = {
        target for decision in exact_decisions
        for edge in decision["selected_edges"] for target in edge["member_target_ids"]
    }
    if selected_targets:
        status = "selected_requires_independent_edge_judgment"
    elif not exact and not target_ids:
        status = "missed_exact_source_occurrence_and_target"
    elif not exact:
        status = "missed_exact_source_occurrence"
    elif not target_ids:
        status = "missed_target_inventory"
    else:
        status = "no_supported_selection"
    outcome = {
        "reference_sha256": ref_digest,
        "case_id": "GS120-WCE-R15-NORMAL-USE",
        "located_mentions": len(evidence),
        "candidate_lists": len(summary["candidate_lists"]),
        "decision_outcomes": dict(Counter(d["outcome"] for d in decisions.values())),
        "retained_coarse_mentions": len(coarse),
        "distinct_coarse_occurrences": len({item["occurrence_id"] for item in coarse}),
        "exact_transform_occurrences": exact,
        "adjacent_nonself_occurrences": adjacent,
        "adjacent_nonself_candidates": [
            candidate for candidate in summary["candidate_lists"]
            if candidate["occurrence_id"] in adjacent_occurrence_ids
        ],
        "adjacent_nonself_decisions": [
            decisions[key] for key in sorted(adjacent_occurrence_ids & decisions.keys())
        ],
        "standard_normal_target_ids": sorted(target_ids),
        "exact_transform_candidates": [
            candidate for candidate in summary["candidate_lists"]
            if candidate["occurrence_id"] in exact_occurrence_ids
        ],
        "exact_transform_decisions": exact_decisions,
        "exact_case_outcome": status,
        "interpretation": "The corpus case tests exact capture and target coverage, separately "
                          "from successful native retrieval of other actual non-self occurrences.",
    }
    retain(output / "independent-assessment.json", outcome)
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-id", required=True, help="Already admitted current release.")
    parser.add_argument("--attempt", required=True, help="Unique evidence attempt name.")
    parser.add_argument("--upstream", choices=("retained-m1", "scoped"), default="retained-m1")
    parser.add_argument("--root-go", action="store_true")
    args = parser.parse_args()
    if not args.root_go or args.release_id == OLD_RELEASE:
        parser.error("Require the coordinator's current-release execution authorization.")
    if not args.attempt.isascii() or not args.attempt.replace("-", "").isalnum():
        parser.error("Attempt must be a single ASCII alphanumeric or hyphenated name.")
    output = HERE / f"native-{args.attempt}"
    output.mkdir(exist_ok=True)
    try:
        settings = Settings()
        named_args = SimpleNamespace(named_run=160, named_product=NAMED_PRODUCT, release_id=OLD_RELEASE)
        named, report, refs = capture_named(settings, named_args, output)
        inventory = prepare_inventory(report, refs, output)
        source = next(s for s in report.inputs.sources if s.source_view_id == SOURCE_VIEW)
        with open_runtime_engine(settings, "gs120-r15-release", purpose="read") as engine:
            with read_snapshot(engine) as conn:
                prepared = load_release(conn, args.release_id)
        retain(output / "release.json", {
            "consuming_release": prepared.release_id,
            "named_origin_release": named["release_id"],
        })
        run, producer, linker = execute(
            settings, prepared, report, source, inventory["target_components"], args, output
        )
        selections = read_pages(settings, run, (producer, linker), output)
        if args.upstream == "retained-m1":
            selections.append(ContributionRequest(
                run_id=161, source_view_id=SOURCE_VIEW,
                method="extract.m1_candidates", max_bytes=128_000_000,
            ))
        selection = ReviewSelection(
            selections=tuple(selections),
            structural_selections=(StructuralExportRequest(
                run_id=named["run_id"], cut_id=named["cut_id"], kind="definition_components",
                max_bytes=128_000_000,
            ),),
            max_bytes=256_000_000,
        )
        bundle = output / "review"
        if not bundle.exists():
            export_review_bundle(selection, bundle, settings)
        manifest = json.loads((bundle / "manifest.json").read_bytes())
        assert manifest["selection"] == selection.model_dump(mode="json")
        retain(output / "portable-closure.json", inspect_review_bundle(bundle))
        summary = summarize_raw(bundle, SOURCE_VIEW)
        # The bundle can be valid even if an actual product's application phases are unavailable.
        phase_outcomes = summary["phase_outcomes"]
        operational = (
            "failed" if phase_outcomes.get("failed")
            else "passed" if summary["candidate_lists"] and summary["relationship_decisions"]
            else "not_run"
        )
        retain(output / "native-phase-summary.json", {
            "outcome": operational,
            "phase_outcomes": phase_outcomes,
            "not_run_phases": [
                phase for phase in summary["phase_operations"] if phase["outcome"] == "not_run"
            ],
            "relationship_outcomes": summary["relationship_outcomes"],
        })
        assessed = grade(bundle, linker, summary, inventory, output)
        retain(output / "result.json", {
            "run": run,
            "upstream": args.upstream,
            "outcome": operational,
            "ordinary_reader_and_portable": "passed",
            "independent_assessment": assessed,
        })
        print(json.dumps({
            "run": run["run_id"], "cut": run["cut_id"], "outcome": operational,
            "candidate_lists": assessed["candidate_lists"],
            "case": assessed["exact_case_outcome"],
        }), flush=True)
        return int(operational != "passed")
    except BaseException as exc:
        retain(output / "failure.json", {"type": type(exc).__name__, "message": str(exc)})
        (output / "failure-traceback.txt").write_text(traceback.format_exc())
        raise


if __name__ == "__main__":
    raise SystemExit(main())
