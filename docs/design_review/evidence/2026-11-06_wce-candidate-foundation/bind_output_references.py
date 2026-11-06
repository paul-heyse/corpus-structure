"""Retain independent per-output location/role passes in existing native custody."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL, OperationCase, OperationSourceOpportunity, create_reference_set,
    decode_frame, record_pass, reference_evaluate,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUTPUT = HERE / "normal-native-output001"
OUTPUT.mkdir(exist_ok=False)
inspection = json.loads((HERE / "candidates009/wce-statistics-normal-20261106/inspection.json").read_bytes())
rows = {item["row"]["contribution_id"]: item["row"] for item in inspection["items"] if item["population"] == "contribution"}
authored = {kind: json.loads((RAW / f"output-author-{kind}-001.json").read_bytes()) for kind in ("A", "B", "C")}
judgments = {"A": {v["contribution_id"]: v for v in authored["A"]["items"]}, "B": {v["contribution_id"]: v for v in authored["B"]["judgments"]}, "C": {v["contribution_id"]: v for v in authored["C"]["items"]}}
try:
    with open_runtime_engine(Settings(), "wce-native-output-refs", purpose="evaluate") as engine, engine.begin() as conn:
        prior = conn.scalar(select(table("eval.reference_unit").c.context).where(table("eval.reference_unit").c.id == 35))
        initial = decode_frame(prior[0])
        if set(initial.contribution_ids) != rows.keys() or any(set(v) != rows.keys() for v in judgments.values()):
            raise ValueError("independent output population differs from exact previously frozen membership")
        questions = []
        for identifier, row in rows.items():
            value = source_python(row["value"])
            extents = value["extents"]
            for suffix, facet in (("location", "source_location"), ("role", "linguistic_role")):
                questions.append(OperationSourceOpportunity(identifier + "/" + suffix, initial.pin["source_view_id"],
                    min(start for start, _ in extents), max(end for _, end in extents), facet, "stated"))
        frame = replace(initial, rubric_version="wce-output-location-role-rubric-1", opportunities=tuple(questions),
            inspected_scope="all23 exact emitted candidates; location and linguistic-role questions separate; rawmatch role N/A represented unassessed")
        created = create_reference_set(conn, project_id="wce-statistics-normal-20261106", source_run_id=113, source_cut_id=inspection["cut_id"],
            label="wce-normal-output-location-role-002", legacy_split="dev", guideline=frame.guideline_version,
            guideline_text="Judge exact quoted output locations independently of linguistic role. Raw match evidence does not itself assert a role. Preserve incorrect σ-as-term separately from correct defining cue. No native-pointer-independent, attachment, applicability, scientific or public-policy claim.", partition="feature_fit",
            sampling={"seed": 0, "strata": {frame.unit: "complete23output_twofacets"}, "inclusion_probabilities": {frame.unit: 1},
                "provenance": {"supersedes_inventory_only_set": 25, "same_frozen23output_ids": True, "independent_author_files": {k: sha256((RAW / f"output-author-{k}-001.json").read_bytes()).hexdigest() for k in ("A", "B", "C")}},
                "cohort": "wce-normal-output-001"}, frames={frame.unit: frame})
        unit = conn.scalar(select(table("eval.reference_unit").c.id).where(table("eval.reference_unit").c.set_id == created["set_id"]))
        ids = {}
        for kind in ("A", "B", "C"):
            cases = []
            for identifier, row in rows.items():
                reference = judgments[kind][identifier]
                anchors = tuple(a["anchor_id"] for a in row["anchors"])
                if kind == "C":
                    pieces = reference["expected_source_pieces"]
                    loc = reference["location_judgment"]
                    role = reference["role_judgment"]
                    role_reason = reference["role_reason"]
                    location_reason = reference["location_scope"]
                else:
                    location = reference["source_location"]
                    pieces = location["exact_source_pieces"] if kind == "A" else [s["text"] for s in location["observed_slices"]]
                    loc = location["status"]
                    role = reference["linguistic_role"]["status"]
                    role_reason = reference["linguistic_role"]["reason"]
                    location_reason = location["reason"]
                if role == "not_applicable":
                    role = "unassessed"
                provenance = {"independent_raw_author": kind, "raw_author_file_sha256": sha256((RAW / f"output-author-{kind}-001.json").read_bytes()).hexdigest(),
                    "claim_grain": "one exact emitted contribution and one facet", "native_pointer_verification": "unassessed by source-only authors"}
                cases.append(OperationCase(case_id=identifier + "/location", facet="source_location", anchor_ids=anchors,
                    inspected_scope="declared projection extents checked against independently frozen authentic source", source_state="stated", judgment=loc,
                    alternatives=({"source_pieces": pieces},) if loc == "supported" else (),
                    explanation=location_reason, assessor_provenance=provenance, contribution_id=identifier))
                cases.append(OperationCase(case_id=identifier + "/role", facet="linguistic_role", anchor_ids=anchors,
                    inspected_scope="declared role in actual quoted source context; separate from attachment/applicability", source_state="stated", judgment=role,
                    alternatives=({"semantic_type": row["semantic_type"], "source_pieces": pieces},) if role == "supported" else (),
                    explanation=role_reason, assessor_provenance=provenance, contribution_id=identifier,
                    error_category="wrong_role" if role == "unsupported" else None))
            payload = {"protocol": PROTOCOL, "release_id": frame.release_id, "unit_ref": frame.unit, "guideline": frame.guideline_version,
                "rubric_version": frame.rubric_version, "context_policy": frame.context_policy, "operation_question": frame.operation_question,
                "operation_version": frame.operation_version, "domain": frame.domain, "direction": frame.direction,
                "reason": "Independent raw per-output author judgments retained; no source-location-to-role promotion. Group σ-role disagreement retained separately in raw C.",
                "cases": [asdict(c) for c in cases], "adjudication_passes": [ids["A"], ids["B"]] if kind == "C" else []}
            body = canonical_bytes(payload)
            ids[kind] = record_pass(conn, unit_id=unit, pass_kind=kind, actor="wce-independent-output-" + kind, authored=body, frame=frame)
            with (OUTPUT / f"native-author-{kind}.json").open("xb") as stream:
                stream.write(body + b"\n")
        grade = reference_evaluate(conn, project_id="wce-statistics-normal-20261106", run_id=113, set_id=created["set_id"])
    for filename, value in (("frame.json", asdict(frame)), ("grade.json", grade.model_dump(mode="json")),
        ("result.json", {"outcome": "passed", "set_id": created["set_id"], "unit_id": unit, "pass_ids": ids,
            "evaluation_id": grade.id, "output_population": len(rows), "facet_opportunities": len(questions), "same_exact_output_ids_as_set25": True,
            "source_location_role_attachment_separate": True, "public_policy_activation": False,
            "quality_scope": "declared exact outputs/source projection only; no scientific, calibrated or corpus-general claim"})):
        with (OUTPUT / filename).open("xb") as stream:
            stream.write(canonical_bytes(value) + b"\n")
    print(json.dumps({"outcome": "passed", "set_id": created["set_id"], "pass_ids": ids, "evaluation_id": grade.id, "facet_opportunities": len(questions)}))
except BaseException as error:
    with (OUTPUT / "failure.json").open("x") as stream:
        json.dump({"outcome": "failed", "type": type(error).__name__, "message": str(error)}, stream)
    raise
