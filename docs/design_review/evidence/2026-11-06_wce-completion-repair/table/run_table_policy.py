"""Run registered WCE table policy arms against independently frozen source frames."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod, discover_relations
from corpus_structure.methods.table_interpretation import POLICY_VERSION, table_policy_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)
from corpus_structure.serve.contributions import (
    ContributionRequest,
    export_contribution_selection,
    serve_contributions,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REFERENCE = HERE.parent / "source-references/source-reference.json"
MARGINAL = "marginal-role-reference.json"
FRAMES = {
    REFERENCE.name: (
        "dice-cell-8", "Table 6.1 nested header and measure interpretation",
        "grinstead-snell-physical234-table-6.1", "gs120-wce-r18-table-6.1",
    ),
    MARGINAL: (
        "marginal-observed-3", "Tables 5.2 and 5.3 observed counts and marginal roles",
        "grinstead-snell-physical202-marginal-counts", "gs120-wce-r18-marginal-counts",
    ),
}
PREVIOUS = HERE.parents[1] / "2026-11-06_wce-gs120/current-structural-journey"
sys.path.insert(0, str(PREVIOUS))
from journey_support import retain, run_method  # noqa: E402

ARMS = (
    ("feasibility", 1.0),
    ("independent", 1.0),
    ("coupled", 1.0),
    ("independent", 0.5),
    ("independent", 2.0),
    ("coupled", 0.5),
    ("coupled", 2.0),
)


def read(path):
    return json.loads(path.read_bytes())


def frozen_inputs(frame_name=REFERENCE.name):
    anchor_name, question, scope, inventory_id = FRAMES[frame_name]
    path = REFERENCE.with_name(frame_name)
    reference_bytes = path.read_bytes()
    reference = json.loads(reference_bytes)
    reference_digest = sha256(reference_bytes).hexdigest()
    anchor = reference["anchors"][anchor_name]
    packet = ROOT / anchor["packet"]
    if sha256(packet.read_bytes()).hexdigest() != reference["inputs"][anchor["packet"]]["sha256"]:
        raise ValueError("source packet differs from the independent frame")
    view = next(
        v for v in read(packet)["views"] if v["passage"]["passage_id"] == anchor["passage_id"]
    )
    source = ExternalSourceRef.model_validate(anchor["source"])
    for item in reference["anchors"].values():
        if item["passage_id"] != anchor["passage_id"] or item["projected_span"] is None:
            continue
        start, end = item["projected_span"]
        if view["passage"]["text"][start:end] != item["quote"]:
            raise ValueError("independent source quote differs at the frozen projection")
    inputs = StructuralInput(
        question=question,
        scope=scope,
        inventory_id=inventory_id,
        policy_id=POLICY_VERSION,
        sources=(source,),
        passages=(StructuralPassage.model_validate(view["passage"]),),
        dependencies=("reference-frame:" + reference_digest,),
    )
    return reference, reference_digest, inputs, view


def retained_population(settings, stage: Path, run, source_view_id: int):
    request = ContributionRequest(
        run_id=run["run_id"],
        source_view_id=source_view_id,
        method=ScopedRelationsMethod.name,
        include_details=True,
        limit=1000,
        page_bytes=16_000_000,
        max_bytes=128_000_000,
    )
    pages = []
    with (
        open_runtime_engine(settings, "gs120-wce-r18-ordinary-read", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        export = export_contribution_selection(
            conn,
            request.model_copy(
                update={"include_details": False, "include_interpretation": True}
            ),
            stage / "export",
        )
        cursor = None
        seen = set()
        while True:
            page = serve_contributions(conn, request.model_copy(update={"cursor": cursor}))
            if page.cut_id != run["cut_id"]:
                raise ValueError("ordinary table detail read returned a different completed cut")
            pages.append(page.model_dump(mode="json"))
            cursor = page.next_cursor
            if cursor is None:
                break
            if cursor in seen:
                raise ValueError("ordinary table continuation did not advance")
            seen.add(cursor)
    retain(stage / "pages.json", pages)
    retain(stage / "export.json", export)
    items = [item for page in pages for item in page["items"]]
    contributions = [item["row"] for item in items if item["population"] == "contribution"]
    operations = [item["row"] for item in items if item["population"] == "operation"]
    return contributions, operations


def relation_projection(contributions):
    by_id = {row["contribution_id"]: row for row in contributions}
    result = {}
    for identity, row in by_id.items():
        if row.get("semantic_type") != "structural.scoped_attachment":
            continue
        value = source_python(row["value"])
        subject, target = (
            source_python(by_id[value[key]]["value"]) for key in ("subject_id", "target_id")
        )
        witnesses = []
        for dependency in value["dependencies"]:
            if dependency in {value["subject_id"], value["target_id"]}:
                continue
            retained = by_id.get(dependency)
            if retained is None:
                continue
            witness = source_python(retained["value"])
            if witness.get("role") == "table_role_declaration":
                witnesses.append(witness)
        result[identity] = {
            "subject": subject,
            "relation": value["relation"],
            "target": target,
            "basis": value["basis"],
            "witnesses": witnesses,
        }
    return result


def policy_checks(relevant, reports):
    checks = []
    for operation, item in reports.items():
        if not relevant.intersection(item["contribution_ids"]):
            continue
        request, result = item["request"], item["result"]
        if request is None or result is None or result["outcome"] != "completed":
            checks.append({"operation": operation, "state": item["status"]})
            continue
        axes = [
            decision for decision in request["decisions"]
            if any(c["key"] in relevant for c in decision["candidates"])
        ]
        axis_keys = {d["key"] for d in axes}
        masked = {
            key.removeprefix("source-disjoint:") for key in request["selection"]["exclusions"]
        }
        alternatives = result["alternatives"]
        top = [
            a for a in alternatives
            if math.isclose(
                a["probability"], alternatives[0]["probability"], rel_tol=0, abs_tol=1e-12,
            )
        ]
        truncated_tie = (
            len(top) == len(alternatives) and result["search"]["positive_states"] > len(top)
        )
        selections = [
            bool({c["candidate"] for c in a["choices"]} & relevant) for a in top
        ]
        state = (
            "hard_excluded" if relevant <= masked else
            "unresolved_tie" if truncated_tie or len(set(selections)) > 1 else
            "top_assignment_present" if selections and selections[0] else
            "top_assignment_absent"
        )
        checks.append({
            "operation": operation,
            "state": state,
            "relation_marginals": [m for m in result["marginals"] if m["decision"] in axis_keys],
            "candidate_axes": axes,
            "shared_factors": [
                factor for factor in request["potentials"]
                if len(factor["scope"]) > 1 and axis_keys.intersection(factor["scope"])
            ],
        })
    return checks


def compare_dice(links, reports, reference):
    cases = {}
    for case in reference["cases"]:
        expected = case["expected"]
        if case["family"] != "scoped_table_composition":
            continue
        value_name = expected.get("value") or case["anchors"][0]
        subject = reference["anchors"][value_name]["native_pointer"]
        comparisons = {}
        questions = [
            (key, "header", expected[key])
            for key in (
                "measure_header", "sample_size_header",
                "excluded_measure_header", "excluded_sample_size_header",
            )
            if key in expected
        ]
        if "value_role" in expected:
            questions.append(("value_role", "value_role", expected["measure_header"]))
        if "row_label" in expected:
            questions.append(("row_label", "row_label", expected["row_label"]))
        for key, relation, target_name in questions:
            target = reference["anchors"][target_name]["native_pointer"]
            relevant = {
                identity for identity, link in links.items()
                if (
                    link["subject"]["source_pointer"] == subject
                    and link["relation"] == relation
                    and link["target"]["source_pointer"] == target
                )
            }
            comparisons[key] = {
                "relations": sorted(relevant),
                "policy_checks": policy_checks(relevant, reports),
                "nomination": "nominated" if relevant else "not_nominated",
            }
        cases[case["id"]] = {
            "independent_judgment": case["judgment"],
            "value_role": expected.get("value_role"),
            "comparisons": comparisons,
        }
    return cases


_MEASURE_ROLES = {
    "observed_count": "observed_count",
    "row_marginal_count": "row_sum",
    "column_marginal_count": "column_sum",
    "grand_total_count": "sample_count",
}


def compare_marginals(links, reports, reference):
    cases = {}
    definition = reference["anchors"]["marginal-definitions"]
    for case in reference["cases"]:
        subject = reference["anchors"][case["observed_cell"]]
        target = reference["anchors"][case["same_position_schematic_cell"]]
        role = _MEASURE_ROLES[case["role"]]
        related = {
            identity: link for identity, link in links.items()
            if (
                link["relation"] == "value_role"
                and link["subject"]["source_pointer"] == subject["native_pointer"]
                and link["subject"]["text"] == subject["quote"]
            )
        }
        supported = {
            identity for identity, link in related.items()
            if (
                link["basis"] == "matched_cue"
                and link["target"]["source_pointer"] == target["native_pointer"]
                and link["target"]["text"] == target["quote"]
                and any(
                    witness["source_pointer"] == definition["native_pointer"]
                    and witness["measure_role"] == role
                    and witness["text"] in definition["quote"]
                    for witness in link["witnesses"]
                )
            )
        }
        layout_only = {
            identity for identity, link in related.items()
            if (
                case["role"] != "observed_count"
                and link["basis"] == "native_geometry"
                and link["target"]["source_pointer"] == definition["native_pointer"]
                and link["target"].get("measure_role") == "observed_count"
            )
        }
        accepted = policy_checks(supported, reports)
        competing = policy_checks(layout_only, reports)
        cases[case["id"]] = {
            "independent_role": case["role"],
            "scope": case["scope"],
            "positive": {k: related[k] for k in sorted(supported)},
            "contrary_layout": {k: related[k] for k in sorted(layout_only)},
            "other_candidates": {
                k: related[k] for k in sorted(related.keys() - supported - layout_only)
            },
            "positive_checks": accepted,
            "layout_checks": competing,
            "competing_choices_on_same_axis": any(
                set(c["key"] for c in axis["candidates"]).intersection(layout_only)
                for item in accepted for axis in item.get("candidate_axes", ())
            ),
            "unit_scope": case["other_units"],
            "note_scope": case["note_applicability"],
        }
    return cases


def assess(contributions, operations, reference, frame_name=REFERENCE.name):
    links = relation_projection(contributions)
    reports = {}
    contribution_ids = {row["contribution_id"] for row in contributions}
    for operation in operations:
        report = operation.get("local_interpretation")
        if report is None:
            continue
        if not set(report["contribution_ids"]) <= contribution_ids:
            raise ValueError("ordinary Reader lost a selected interpretation input")
        if report["policy_version"] != POLICY_VERSION:
            raise ValueError("ordinary Reader returned a superseded table policy")
        request = source_python(report["request"]) if report.get("request") else None
        result = source_python(report["result"]) if report.get("result") else None
        reports[operation["operation_key"]] = {
            "status": report["outcome"],
            "executed_mode": report["policy_mode"],
            "input_digest": report["retained_input_digest"],
            "contribution_ids": report["contribution_ids"],
            "request_digest": report.get("request_digest"),
            "result_digest": report.get("result_digest"),
            "request": request,
            "result": result,
        }
    compare = compare_marginals if frame_name == MARGINAL else compare_dice
    return {
        "contribution_ids": sorted(contribution_ids),
        "report_counts": dict(
            Counter(r["status"] + "/" + r["executed_mode"] for r in reports.values())
        ),
        "reports": reports,
        "source_cases": compare(links, reports, reference),
    }


def case_summary(assessment, frame_name):
    if frame_name != MARGINAL:
        return {}
    return {
        name: {
            "role": case["independent_role"],
            "positive_nominated": bool(case["positive"]),
            "layout_nominated": bool(case["contrary_layout"]),
            "competing_choices_on_same_axis": case["competing_choices_on_same_axis"],
            "positive_states": sorted({c["state"] for c in case["positive_checks"]}),
            "layout_states": sorted({c["state"] for c in case["layout_checks"]}),
            "shared_factor_on_role_axis": any(
                check["shared_factors"]
                for check in case["positive_checks"] if "shared_factors" in check
            ),
        }
        for name, case in assessment["source_cases"].items()
    }


def preflight(frame_name, reference, inputs, view):
    source = inputs.sources[0]
    native = view["native_view"]
    frame = NativeFrameSource(
        unit_ref=source.identity,
        text=view["passage"]["text"],
        sentences=(),
        source_view_id=source.source_view_id,
        native_product=ProductReference(
            task_id=source.native_task_id,
            product_key=source.native_product_key,
            content_digest=source.native_content_digest,
        ),
        section_pointer=native["section_pointer"],
        membership=native["membership"],
        projection_digest=source.projection_digest,
        recipe_digest=source.recipe_digest,
        native_context=canonical_bytes(view["native_context"]).decode(),
        version=source.coordinate_version,
    )
    produced = discover_relations(frame)
    assessments = {}
    for mode, scale in ARMS:
        operations = table_policy_operations(
            contributions=produced["contributions"],
            dependency_ids=produced["operation"]["computation_dependencies"],
            source_revision=source.native_content_digest,
            mode=mode,
            weight_scale=scale,
        )
        assessments[f"{mode}-{scale:g}"] = {
            "assessment": assess(produced["contributions"], operations, reference, frame_name)
        }
    compare_support(assessments)
    return {
        "outcome": "passed",
        "scope": "detached production relation and policy calls on exact source packet",
        "source_view_id": source.source_view_id,
        "arms": {
            key: {
                "report_counts": value["assessment"]["report_counts"],
                "cases": case_summary(value["assessment"], frame_name),
            }
            for key, value in assessments.items()
        },
    }


def compare_support(arms):
    anchor = arms["feasibility-1"]["assessment"]
    for label, arm in arms.items():
        assessment = arm["assessment"]
        if assessment["contribution_ids"] != anchor["contribution_ids"]:
            raise ValueError("table policy changed its selected contribution population: " + label)
        if assessment["reports"].keys() != anchor["reports"].keys():
            raise ValueError("table policy changed its local scope selection: " + label)
        for key, baseline in anchor["reports"].items():
            candidate = assessment["reports"][key]
            if candidate["input_digest"] != baseline["input_digest"]:
                raise ValueError("table policy substituted retained inputs: " + label)
            left, right = baseline["request"], candidate["request"]
            if (left is None) != (right is None):
                raise ValueError("table policy changed support availability: " + label)
            if left and right:
                for field in ("decisions", "constraints", "selection", "events"):
                    if left[field] != right[field]:
                        raise ValueError(f"table policy changed common {field}: {label} / {key}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", help="fresh task-owned evidence directory")
    parser.add_argument("--release", help="exact admitted release under native cutover")
    parser.add_argument("--frame", choices=FRAMES, default=REFERENCE.name)
    parser.add_argument("--preflight", action="store_true", help="run detached policy comparisons")
    args = parser.parse_args()
    reference, digest, inputs, view = frozen_inputs(args.frame)
    if args.preflight:
        print(json.dumps(preflight(args.frame, reference, inputs, view), indent=2))
        return
    if args.output is None or args.release is None:
        parser.error("native execution requires output and --release")
    output = args.output.resolve()
    if HERE not in output.parents:
        parser.error("output must be within this table evidence folder")
    output.mkdir()
    retain(output / "frozen-comparison.json", {
        "source_reference_sha256": digest,
        "source_reference": str(REFERENCE.with_name(args.frame).relative_to(ROOT)),
        "inputs": inputs.model_dump(mode="json"),
        "arms": [dict(mode=mode, weight_scale=scale) for mode, scale in ARMS],
    })
    settings = Settings()
    with (
        open_runtime_engine(settings, "gs120-wce-r18-read-release", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = load_release(conn, args.release)
    arms = {}
    for mode, scale in ARMS:
        label = f"{mode}-{scale:g}"
        stage = output / label
        run = run_method(
            settings, prepared, ScopedRelationsMethod(),
            dict(
                inputs=inputs.model_dump(mode="json"),
                structural_input_digest=inputs.identity,
                interpretation_mode=mode,
                interpretation_weight_scale=scale,
            ),
            inputs, stage, label, "wce-r18-" + output.name,
        )
        contributions, operations = retained_population(
            settings, stage, run, inputs.sources[0].source_view_id
        )
        arms[label] = {
            "run": run, "assessment": assess(contributions, operations, reference, args.frame),
        }
        retain(stage / "assessment.json", arms[label])
    compare_support(arms)
    coupled = arms["coupled-1"]["assessment"]
    if not any(
        r["status"] == "completed" and r["executed_mode"] == "coupled"
        for r in coupled["reports"].values()
    ):
        raise ValueError("no authentic shared source factor reached native completion")
    summaries = {k: case_summary(v["assessment"], args.frame) for k, v in arms.items()}
    scoped_ambiguity = any(
        case["competing_choices_on_same_axis"] for case in summaries["coupled-1"].values()
    )
    shared_role_factor = any(
        case["shared_factor_on_role_axis"] for case in summaries["coupled-1"].values()
    )
    retain(output / "comparison.json", {
        "outcome": "passed",
        "scope": inputs.question,
        "source_view_id": inputs.sources[0].source_view_id,
        "source_reference": args.frame,
        "competing_role_choices_on_same_axis": scoped_ambiguity,
        "shared_factor_on_assessed_role_axis": shared_role_factor,
        "limitations": (
            "Independent source judgments apply to these exact cases. "
            "The declared probabilities are private and candidate-relative."
        ),
        "arms": {
            k: {
                "run": v["run"],
                "report_counts": v["assessment"]["report_counts"],
                "cases": summaries[k],
            }
            for k, v in arms.items()
        },
    })


if __name__ == "__main__":
    main()
