"""Prepare protected literal frames from two exact d1 requests, without DB writes."""

import argparse
import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    decode_authored,
    decode_frame,
    encode_frame,
)
from corpus_structure.orchestrate.pm2_stage import InterpretationRunRequest
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import selected_source_views
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
METHOD = "extract.pm2_d1"
FAMILY = "literal_completion_v1"
SPECS = {
    "fair_coin": (("fair_coin", "quantity", "literal", "0.125"),),
    "roulette": (
        ("roulette_amount", "loss_amount", "amount", "1"),
        ("roulette_unit", "loss_unit", "unit", None),
        ("roulette_role", "loss_role_cue", "loss_role", None),
    ),
}
ACTORS = {"A": "pm2-source-reader-one", "B": "source_second", "C": "source_adjudication"}


def read(path):
    return json.loads(path.read_bytes())


def binding(conn, scope, expected_hash):
    methods, configs = table("ops.method"), table("ops.method_config")
    params = conn.scalar(
        select(configs.c.params)
        .join(methods, methods.c.id == configs.c.method_id)
        .where(
            methods.c.name == METHOD,
            methods.c.version == scope.version,
            configs.c.config_hash == expected_hash,
        )
    )
    profile = scope.profile.model_dump(mode="json")
    if not isinstance(params, dict) or sha256(canonical_bytes(params)).hexdigest() != expected_hash:
        raise ValueError("literal arm needs an exact registered d1 profile configuration")
    if params != profile:
        # Runtime preflight supplies this determinant after reading the request.
        startup = dict(params.get("startup", {}))
        if not startup.pop("runtime_identity", None):
            raise ValueError("registered literal configuration differs from its request profile")
        if params | {"startup": startup} != profile:
            raise ValueError("registered literal configuration differs from its request profile")
    return {
        "method": METHOD,
        "method_version": scope.version,
        "operation_question": FAMILY,
        "operation_version": scope.version,
        "configuration_hash": expected_hash,
    }


def authored(frame, roles, specifications, kind, reason, adjudication_passes=None):
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
        "reason": reason,
        "cases": [],
    }
    if kind == "C":
        payload["adjudication_passes"] = adjudication_passes
    for opportunity, (case_id, question, role, normalized) in zip(
        frame.opportunities, specifications, strict=True
    ):
        if opportunity.opportunity_id != case_id:
            raise ValueError("literal frame case identity changed")
        anchors = roles[role]["native_anchors"]
        expected = {
            "interpretation_literal_pieces": [a["source_piece"] for a in anchors],
            "interpretation_literal_anchors": [
                {key: a[key] for key in ("pointer", "start", "end")} for a in anchors
            ],
        }
        if normalized is not None:
            expected["interpretation_normalized_decimal"] = normalized
        payload["cases"].append(
            {
                "case_id": case_id,
                "facet": opportunity.facet,
                "anchor_ids": [],
                "inspected_scope": frame.inspected_scope,
                "source_state": opportunity.source_state,
                "judgment": "supported",
                "alternatives": [expected],
                "explanation": reason,
                "assessor_provenance": {
                    "actor": ACTORS[kind],
                    "material": "source-only development",
                },
                "contribution_kind": "composite",
                "candidate_selector": {
                    "semantic_type": f"interpretation.{FAMILY}",
                    "interpretation_projection_extent": [opportunity.start, opportunity.end],
                    "interpretation_question_key": question,
                },
            }
        )
    decode_authored(canonical_bytes(payload), frame)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=SPECS)
    parser.add_argument("--from-run", type=int, required=True)
    parser.add_argument("--source-cut", type=int, required=True)
    for arm in ("baseline", "revised"):
        parser.add_argument(f"--{arm}-request", type=Path, required=True)
        parser.add_argument(f"--{arm}-configuration", required=True)
    parser.add_argument("--adjudication-packet", type=Path)
    args = parser.parse_args()
    packet = read(HERE / "raw/source-windows.json")
    case = packet["cases"][args.case]
    template = decode_frame(packet["d1_frame_templates"][args.case])
    specs = SPECS[args.case]
    questions = tuple(question for _, question, _, _ in specs)
    requests = {
        arm: InterpretationRunRequest.model_validate(read(getattr(args, f"{arm}_request")))
        for arm in ("baseline", "revised")
    }
    scopes = {}
    for arm, request in requests.items():
        matched = [
            scope
            for scope in request.scopes
            if scope.family == FAMILY
            and scope.extent == tuple(case["extent"])
            and scope.source.projection_digest == case["pin"]["projection_digest"]
        ]
        if (
            len(matched) != 1
            or matched[0].questions != questions
            or not matched[0].schedule
            or matched[0].focus
            or matched[0].candidates
            or matched[0].retrieval
        ):
            raise ValueError(f"{arm} does not answer the exact released literal question panel")
        scopes[arm] = matched[0]
    left, right = (scopes[arm].source for arm in ("baseline", "revised"))
    if left != right:
        raise ValueError("literal arms must use the same exact retained source reference")
    with (
        open_runtime_engine(Settings(), "pm2-literal-reference-prepare", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        run, cut = table("ops.run"), table("ops.input_cut")
        row = conn.execute(
            select(run.c.project_id, run.c.release_id)
            .join(cut, cut.c.run_id == run.c.id)
            .where(
                run.c.id == args.from_run,
                cut.c.id == args.source_cut,
                cut.c.release_id == run.c.release_id,
            )
        ).one()
        if left.project_id != row.project_id or any(
            (request.project, request.release) != tuple(row) for request in requests.values()
        ):
            raise ValueError(
                "reference and both prediction requests must share project and release"
            )
        views = {view.id: view for view in selected_source_views(conn, args.from_run)}
        view = views.get(left.source_view_id)
        if view is None:
            raise ValueError("prediction view does not belong to the frozen reference run")
        pin = dict(
            source=view.key,
            source_view_id=view.id,
            native_product_task_id=view.native_product.task_id,
            product_key=view.native_product.product_key,
            product_digest=view.native_product.content_digest,
            projection_digest=view.projection_digest,
            recipe_digest=view.recipe_digest,
        )
        if {k: v for k, v in pin.items() if k not in {"source", "source_view_id"}} != {
            k: v for k, v in case["pin"].items() if k not in {"source", "source_view_id"}
        } or (
            left.native_task_id,
            left.native_product_key,
            left.native_content_digest,
            left.projection_digest,
            left.recipe_digest,
        ) != (
            pin["native_product_task_id"],
            pin["product_key"],
            pin["product_digest"],
            pin["projection_digest"],
            pin["recipe_digest"],
        ):
            raise ValueError(
                "literal reference changes the adjudicated native source or projection"
            )
        bindings = {
            arm: binding(conn, scope, getattr(args, f"{arm}_configuration"))
            for arm, scope in scopes.items()
        }
    if bindings["baseline"] == bindings["revised"]:
        raise ValueError(
            "identical method/operation arms require distinct registered configurations"
        )
    frame = replace(
        template,
        unit=view.key,
        release_id=row.release_id,
        pin=pin,
        operation_version=scopes["revised"].version,
        inspected_scope=f"view {view.id} chars {case['extent'][0]}:{case['extent'][1]}",
        opportunities=tuple(
            replace(opportunity, source_view_id=view.id) for opportunity in template.opportunities
        ),
    )
    frame_json = encode_frame(frame)
    sample = {
        "frames": {frame.unit: frame_json},
        "sampling": {
            "panel": f"{frame.guideline_version}:{args.case}",
            "cohort": "Grinstead-Snell exposed development controls",
            "seed": 0,
            "strata": {frame.unit: "source-authored-development"},
            "inclusion_probabilities": {frame.unit: 1},
            "provenance": {"selection": "Previously frozen source-only PM2 literal opportunity."},
            "comparison_arms": {arm: {frame.unit: producer} for arm, producer in bindings.items()},
        },
    }
    a = read(HERE / "judgments.json")["workflows"][args.case]
    b = read(HERE / "second-reading.json")["cases"][args.case]
    reason_a = a.get("reason")
    if not reason_a:
        qualifier = case["anchors"]["qualifier"]["native_anchors"][0]["source_piece"]
        reason_a = (
            f"The exact literal {a['literal']} normalizes to {a['normalized_decimal']}; "
            f"preserve {qualifier!r} as its condition."
        )
    passes = {
        kind: authored(frame, case["anchors"], specs, kind, reason)
        for kind, reason in (("A", reason_a), ("B", b["meaning"]))
    }
    if args.adjudication_packet:
        adjudication = read(args.adjudication_packet)
        frozen = adjudication["source"]["source_frame"]
        if "contribution_ids" not in frozen["evaluation_frame"]:
            frozen["evaluation_frame"]["contribution_ids"] = []
        if decode_frame(frozen) != frame:
            raise ValueError("C packet differs from the prepared literal frame")
        ids = adjudication["adjudication_passes"]
        if (
            len(ids) != 2
            or ids[0] == ids[1]
            or any(type(value) is not int or value <= 0 for value in ids)
            or [(author["pass_id"], author["actor"]) for author in adjudication["authors"]]
            != list(zip(ids, (ACTORS["A"], ACTORS["B"]), strict=True))
        ):
            raise ValueError("C needs the real distinct native A and B pass IDs")
        c = read(HERE / "adjudication.json")["cases"][args.case]
        passes["C"] = authored(frame, case["anchors"], specs, "C", c["agreed_fact"], ids)
    print(
        canonical_bytes(
            {
                "sample": sample,
                "frame": frame_json,
                "actors": {kind: ACTORS[kind] for kind in passes},
                "passes": passes,
                "registered": False,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
