"""Run the registered WCE table policy arms on the independently frozen Table 6.1 view."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.methods.table_interpretation import POLICY_VERSION
from corpus_structure.semantic.observations import source_python
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


def frozen_inputs():
    reference_bytes = REFERENCE.read_bytes()
    reference = json.loads(reference_bytes)
    reference_digest = sha256(reference_bytes).hexdigest()
    anchor = reference["anchors"]["dice-cell-8"]
    packet = ROOT / anchor["packet"]
    if sha256(packet.read_bytes()).hexdigest() != reference["inputs"][anchor["packet"]]["sha256"]:
        raise ValueError("Table 6.1 source packet differs from the independent frame")
    view = next(v for v in read(packet)["views"] if v["passage"]["passage_id"] == anchor["passage_id"])
    source = ExternalSourceRef.model_validate(anchor["source"])
    for item in reference["anchors"].values():
        if item["passage_id"] != anchor["passage_id"] or item["projected_span"] is None:
            continue
        start, end = item["projected_span"]
        if view["passage"]["text"][start:end] != item["quote"]:
            raise ValueError("independent source quote differs at the frozen projection")
    inputs = StructuralInput(
        question="Table 6.1 nested header and measure interpretation",
        scope="grinstead-snell-physical234-table-6.1",
        inventory_id="gs120-wce-r18-table-6.1",
        policy_id=POLICY_VERSION,
        sources=(source,),
        passages=(StructuralPassage.model_validate(view["passage"]),),
        dependencies=("reference-frame:" + reference_digest,),
    )
    return reference, reference_digest, inputs


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
    with open_runtime_engine(settings, "gs120-wce-r18-ordinary-read", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            export = export_contribution_selection(
                conn,
                request.model_copy(update={"include_details": False, "include_interpretation": True}),
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
        subject, target = (source_python(by_id[value[key]]["value"]) for key in ("subject_id", "target_id"))
        result[identity] = (subject["source_pointer"], value["relation"], target["source_pointer"])
    return result


def assess(contributions, operations, reference):
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
        request = source_python(report["request"]) if "request" in report else None
        result = source_python(report["result"]) if "result" in report else None
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
                identity for identity, link in links.items() if link == (subject, relation, target)
            }
            checks = []
            for operation, item in reports.items():
                if not relevant.intersection(item["contribution_ids"]):
                    continue
                request, result = item["request"], item["result"]
                if request is None or result is None or result["outcome"] != "completed":
                    checks.append({"operation": operation, "state": item["status"]})
                    continue
                masked = {
                    key.removeprefix("source-disjoint:")
                    for key in request["selection"]["exclusions"]
                }
                alternatives = result["alternatives"]
                top = [
                    a for a in alternatives
                    if math.isclose(a["probability"], alternatives[0]["probability"], rel_tol=0, abs_tol=1e-12)
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
                    "relation_marginals": [
                        m for m in result["marginals"] if m["candidate"] in relevant
                    ],
                })
            comparisons[key] = {
                "relations": sorted(relevant),
                "policy_checks": checks,
                "nomination": "nominated" if relevant else "not_nominated",
            }
        cases[case["id"]] = {
            "independent_judgment": case["judgment"],
            "value_role": expected.get("value_role"),
            "comparisons": comparisons,
        }
    return {
        "contribution_ids": sorted(row["contribution_id"] for row in contributions),
        "report_counts": dict(Counter((r["status"] + "/" + r["executed_mode"]) for r in reports.values())),
        "reports": reports,
        "source_cases": cases,
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
    parser.add_argument("output", type=Path, help="fresh task-owned evidence directory")
    parser.add_argument("--release", required=True, help="exact admitted release under native cutover")
    args = parser.parse_args()
    output = args.output.resolve()
    if HERE not in output.parents:
        parser.error("output must be within this table evidence folder")
    output.mkdir()
    reference, digest, inputs = frozen_inputs()
    retain(output / "frozen-comparison.json", {
        "source_reference_sha256": digest,
        "source_reference": str(REFERENCE.relative_to(ROOT)),
        "inputs": inputs.model_dump(mode="json"),
        "arms": [dict(mode=mode, weight_scale=scale) for mode, scale in ARMS],
    })
    settings = Settings()
    with open_runtime_engine(settings, "gs120-wce-r18-read-release", purpose="read") as engine:
        with read_snapshot(engine) as conn:
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
        contributions, operations = retained_population(settings, stage, run, inputs.sources[0].source_view_id)
        arms[label] = {"run": run, "assessment": assess(contributions, operations, reference)}
        retain(stage / "assessment.json", arms[label])
    compare_support(arms)
    coupled = arms["coupled-1"]["assessment"]
    if not any(r["status"] == "completed" and r["executed_mode"] == "coupled" for r in coupled["reports"].values()):
        raise ValueError("no authentic shared source factor reached native completion")
    retain(output / "comparison.json", {
        "outcome": "passed",
        "scope": "retained native Table 6.1 view, independent first-row header opportunities",
        "limitations": (
            "Common native support and source-conditioned inference establish executed policy behavior. "
            "The literal merged-header paths are independently judged; these cases do not establish "
            "calibration, corpus-wide quality, or a separate genuinely ambiguous source cohort."
        ),
        "arms": {
            k: {"run": v["run"], "report_counts": v["assessment"]["report_counts"]}
            for k, v in arms.items()
        },
    })


if __name__ == "__main__":
    main()
