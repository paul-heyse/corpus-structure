"""Freeze exact scopes for the matched interpretation and author the A/B passes."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    OperationSourceOpportunity,
    adjudication_packet,
    decode_frame,
    encode_frame,
    record_pass,
)
from corpus_structure.evaluate.semantic import unit_passes
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

FOLDER = Path(__file__).resolve().parent
PREVIOUS = FOLDER.parent / "2026-11-09_pm2-interpretation" / "raw"
RAW = FOLDER / "raw"
GUIDELINE = "pm2-interpretation-pair-1"
PARTITION = "development"
EXPOSURE = "The locations and earlier version 1 development outcomes are known; this is exposed development, not a held-out estimate."
METHOD = "extract.pm2_d1"


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


CASES = {
    "definition": (383, (811, 907), "passage_function_v1", "passage_functions", "definition_function"),
    "probability": (389, (18091, 18193), "literal_completion_v1", "quantity", "complete_probability_magnitude"),
    "loss": (387, (47316, 47345), "literal_completion_v1", "quantity", "exact_loss_magnitude_without_join"),
    "host": (389, (18091, 18193), "qualification_scope_v1", "qualification_host", "condition_host"),
    "referent": (405, (27850, 28039), "local_referent_choice_v1", "local_referent", "exact_referent"),
}
SETS = {"literal-and-function": ("definition", "probability", "loss"), "attachments": ("host", "referent")}


def freeze():
    old = read(PREVIOUS / "development-interpretation-request.json")
    scopes = {(scope["source"]["source_view_id"], scope["family"]): scope for scope in old["scopes"]}
    source = {
        value["evaluation_frame"]["pin"]["source_view_id"]: decode_frame(value)
        for value in read(PREVIOUS / "development-operation-sample.json")["frames"].values()
    }
    requests = []
    frames = {}
    for case, (view, extent, family, question, facet) in CASES.items():
        previous = source[view]
        assert previous.release_id == old["release"]
        scope = scopes[view, family]
        assert all(
            previous.pin[key] == scope["source"][pin]
            for key, pin in (
                ("product_digest", "native_content_digest"),
                ("product_key", "native_product_key"),
                ("native_product_task_id", "native_task_id"),
                ("projection_digest", "projection_digest"),
                ("recipe_digest", "recipe_digest"),
            )
        )
        requests.append({**scope, "extent": list(extent), "questions": [question]})
        frames[case] = replace(
            previous,
            guideline_version=GUIDELINE,
            rubric_version=GUIDELINE,
            operation_question=family,
            inspected_scope=f"view {view} chars {extent[0]}:{extent[1]}",
            opportunities=(OperationSourceOpportunity(case, view, *extent, facet, "stated"),),
            exposure_history=(EXPOSURE,),
        )
    for name, cases in SETS.items():
        population = {frames[case].unit: encode_frame(frames[case]) for case in cases}
        sampling = {
            "panel": GUIDELINE + ":" + name,
            "cohort": "Grinstead–Snell exposed interpretation development controls",
            "seed": 0,
            "strata": {key: "authored_development_control" for key in population},
            "inclusion_probabilities": dict.fromkeys(population, 1),
            "provenance": {"selection": "Complete enumeration of the named source-only development panel."},
            "comparison_arms": {
                arm: {
                    frames[case].unit: {
                        "method": METHOD,
                        "method_version": version,
                        "operation_question": frames[case].operation_question,
                        "operation_version": version,
                    }
                    for case in cases
                }
                for arm, version in (("baseline", "1"), ("revised", "2"))
            },
        }
        write(RAW / f"{name}-sample.json", {"frames": population, "sampling": sampling})
    write(RAW / "baseline-request.json", {**old, "scopes": requests})
    write(RAW / "revised-request.json", {**old, "scopes": [{**scope, "version": "2"} for scope in requests]})
    parser_request = read(PREVIOUS / "development-parser-request.json")
    (maverick,) = (scope for scope in parser_request["scopes"] if scope["profile"]["provider"] == "maverick")
    start = maverick["extent"][0]
    write(RAW / "reviewed-mentions-request.json", {
        **parser_request,
        "scopes": [{
            **maverick, "mode": "supplied_mentions",
            "supplied": [[left - start, right - start] for left, right in ((27850, 27859), (27893, 27896))],
        }],
    })


def expectations():
    old = read(PREVIOUS / "development-interpretation-request.json")
    host = next(scope["focus"] for scope in old["scopes"] if scope["family"] == "frame_interpretation_v1")
    candidate = next(
        item
        for scope in old["scopes"]
        if scope["family"] == "local_referent_choice_v1"
        for item in scope["candidates"]
    )
    return {
        "definition": [
            {"interpretation_state": "proposed", "interpretation_selected_keys": keys}
            for keys in (["definition"], ["definition", "assertion"])
        ],
        "probability": [{
            "interpretation_literal_pieces": ["1/8"],
            "interpretation_literal_anchors": [{"pointer": "#/texts/14369", "start": 98, "end": 101}],
            "interpretation_normalized_decimal": "0.125",
        }],
        "loss": [{
            "interpretation_literal_pieces": ["1"],
            "interpretation_literal_anchors": [{"pointer": "#/texts/543", "start": 0, "end": 1}],
            "interpretation_normalized_decimal": "1",
        }],
        "host": [{"interpretation_selected_keys": ["candidate_" + host["contribution_id"].rsplit(":", 1)[1]]}],
        "referent": [{"interpretation_selected_keys": ["candidate_" + candidate["contribution_id"].rsplit(":", 1)[1]]}],
    }


def _authored(frame, pass_kind, notes, alternatives, adjudications=None):
    (opportunity,) = frame.opportunities
    case = opportunity.opportunity_id
    _, extent, family, question, _ = CASES[case]
    explanation = notes[pass_kind][case]
    payload = {
        "protocol": "source-operation-reference-1",
        "release_id": frame.release_id,
        "unit_ref": frame.unit,
        "guideline": frame.guideline_version,
        "rubric_version": frame.rubric_version,
        "context_policy": frame.context_policy,
        "operation_question": frame.operation_question,
        "operation_version": frame.operation_version,
        "domain": frame.domain,
        "direction": frame.direction,
        "reason": explanation,
        "cases": [{
            "case_id": case,
            "facet": opportunity.facet,
            "anchor_ids": [],
            "inspected_scope": frame.inspected_scope,
            "source_state": opportunity.source_state,
            "judgment": "supported",
            "alternatives": alternatives[case],
            "explanation": explanation,
            "assessor_provenance": {"actor": notes["actors"][pass_kind], "material": "source-only development scope"},
            "contribution_kind": "composite" if case in {"probability", "loss"} else "proposal",
            "candidate_selector": {
                "semantic_type": "interpretation." + family,
                "interpretation_projection_extent": list(extent),
                "interpretation_question_key": question,
            },
        }],
    }
    if pass_kind == "C":
        payload["adjudication_passes"] = adjudications
    return json.dumps(payload, ensure_ascii=False).encode()


def protect():
    """Use native custody in one transaction after the separate source-only reviews."""
    notes = read(FOLDER / "source-reviews.json")
    alternatives = expectations()
    units = table("eval.reference_unit")
    report = []
    with open_runtime_engine(Settings(), "pm2-interpretation-protected-pair", purpose="evaluate") as engine, engine.begin() as conn:
        for name, cases in SETS.items():
            frozen = read(RAW / f"{name}-set.json")
            exact = {
                unit["unit_key"]: decode_frame(unit["frame"]) for unit in frozen["units"]
            }
            selected = conn.execute(select(units).where(units.c.set_id == frozen["set_id"]).order_by(units.c.id)).mappings().all()
            if set(exact) != {unit["unit_key"] for unit in selected}:
                raise ValueError("protected reference membership differs from the frozen receipt")
            for unit in selected:
                frame = decode_frame(unit["context"][0])
                if frame != exact[unit["unit_key"]] or any(unit_passes(conn, unit["id"]).values()):
                    raise ValueError("expected an exact unreviewed reference frame")
                (opportunity,) = frame.opportunities
                assert opportunity.opportunity_id in cases
                for pass_kind in ("A", "B", "C"):
                    linked = None
                    if pass_kind == "C":
                        linked = adjudication_packet(conn, unit["id"])["adjudication_passes"]
                    authored = _authored(frame, pass_kind, notes, alternatives, linked)
                    receipt = record_pass(
                        conn, unit_id=unit["id"], pass_kind=pass_kind, actor=notes["actors"][pass_kind],
                        authored=authored, frame=frame,
                    )
                    report.append({
                        "set_id": frozen["set_id"], "unit_id": unit["id"], "pass_id": receipt,
                        "pass_kind": pass_kind, "authored": json.loads(authored),
                    })
    write(RAW / "protected-passes.json", report)


def diagnostic():
    """Keep reviewed candidates out of the ordinary matched inference arms."""
    request = read(RAW / "revised-request.json")
    parser = read(RAW / "reviewed-mentions-run.json")
    run, cut = parser["run_id"], parser["cut_id"]
    runs = table("ops.run")
    with open_runtime_engine(Settings(), "pm2-interpretation-diagnostic", purpose="read") as engine, read_snapshot(engine) as conn:
        session = bind_completed_result(conn, run)
        runtime = conn.scalar(select(runs.c.runtime_id).where(runs.c.id == run))
        population = read_source_contributions(
            conn, prepared=session.prepared, run_id=run, cut_id=cut, source_view_id=405,
            include_details=True, limit=100,
        ).contributions
    rows = {item["contribution_id"]: item for item in population}

    def mention(literal):
        (selected,) = (
            row for row in population if row["semantic_type"] == "maverick.mention" and any(
                anchor["source_piece"] == literal
                for member in row["members"] for anchor in rows[member]["anchors"]
            )
        )
        return {
            "contribution_id": selected["contribution_id"], "project_id": request["project"],
            "release_id": request["release"], "run_id": run, "cut_id": cut,
            "selected_task_id": selected["selected_task_id"], "origin_task_id": selected["origin_task_id"],
            "runtime_fingerprint": runtime, "result_revision": session.binding.data_revision,
        }

    (local,) = (s for s in request["scopes"] if s["family"] == "local_referent_choice_v1")
    (host,) = (s for s in request["scopes"] if s["family"] == "qualification_scope_v1")
    (reviewed_host,) = expectations()["host"][0]["interpretation_selected_keys"]
    (host_ref,) = (item for item in host["candidates"] if reviewed_host.endswith(item["contribution_id"].rsplit(":", 1)[1]))
    write(RAW / "diagnostic-request.json", {**request, "scopes": [
        {**host, "candidates": [host_ref]},
        {**local, "focus": mention("She"), "candidates": [mention("A gambler")]},
    ]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--protect", action="store_true")
    selection.add_argument("--diagnostic", action="store_true")
    args = parser.parse_args()
    if args.protect:
        protect()
    elif args.diagnostic:
        diagnostic()
    else:
        freeze()
