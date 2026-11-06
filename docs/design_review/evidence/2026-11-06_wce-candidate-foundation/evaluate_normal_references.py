"""Grade all frozen source opportunities and freeze exact output-first membership."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    OperationSourceOpportunity, create_reference_set, decode_frame, reference_evaluate,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "normal-native-assessment002"
OUTPUT.mkdir(exist_ok=False)
refs = json.loads((HERE / "normal-native-references003/result.json").read_bytes())
inspection_file = HERE / "candidates009/wce-statistics-normal-20261106/inspection.json"
inspection = json.loads(inspection_file.read_bytes())
if not inspection["population_paging_complete"]:
    raise ValueError("output frame requires complete bounded population")
contributions = [r["row"] for r in inspection["items"] if r["population"] == "contribution"]
try:
    with open_runtime_engine(Settings(), "wce-normal-reference-grade", purpose="evaluate") as engine, engine.begin() as conn:
        stored = conn.scalar(select(table("eval.reference_unit").c.context).where(table("eval.reference_unit").c.id == refs["unit_id"]))
        frame = decode_frame(stored[0])
        grade = reference_evaluate(conn, project_id="wce-statistics-normal-20261106", run_id=113, set_id=refs["set_id"])
        source_payload = grade.model_dump(mode="json")
        anchors = {a["anchor_id"]: a for row in contributions for a in row.get("anchors", ())}
        output_opportunities = []
        for row in contributions:
            value = source_python(row["value"])
            extents = value.get("extents", ())
            output_opportunities.append(OperationSourceOpportunity(row["contribution_id"], frame.pin["source_view_id"],
                min(start for start, _ in extents) if extents else 0,
                max(end for _, end in extents) if extents else 5684,
                "emitted_candidate", "stated" if extents else "unresolved"))
        scopes = tuple({k: v for k, v in a.items() if k in {"pin", "space", "pointer", "precision", "start", "end", "recognition"}} for a in anchors.values())
        output_frame = replace(frame, direction="output_first", contribution_ids=tuple(row["contribution_id"] for row in contributions),
            anchor_ids=tuple(dict.fromkeys((*frame.anchor_ids, *anchors))),
            anchor_scopes=tuple([*frame.anchor_scopes, *scopes]), opportunities=tuple(output_opportunities),
            inspected_scope="all exact emitted candidates in run113 methodextract.wce_named_candidates; bounding projection scopes are not continuous source quotations")
        created = create_reference_set(conn, project_id="wce-statistics-normal-20261106", source_run_id=113, source_cut_id=inspection["cut_id"],
            label="wce-normal-output-first-001", legacy_split="dev", guideline=frame.guideline_version,
            guideline_text="Independent assessment of exact emitted candidate locations/linguistic roles. Attachment, applicability and scientific truth require separate questions.", partition="feature_fit",
            sampling={"seed": 0, "strata": {frame.unit: "all_emitted_candidates"}, "inclusion_probabilities": {frame.unit: 1}, "provenance": {"inspection_sha256": sha256(inspection_file.read_bytes()).hexdigest(), "selection": "census of retained exact output IDs after producer execution; independent authoring follows freeze"}, "cohort": "wce-normal-output-001"}, frames={frame.unit: output_frame})
        output_unit = conn.scalar(select(table("eval.reference_unit").c.id).where(table("eval.reference_unit").c.set_id == created["set_id"]))
    for filename, value in (("source-grade.json", source_payload), ("output-frame.json", asdict(output_frame)),
        ("result.json", {"outcome": "passed", "source_evaluation_id": grade.id, "source_set_id": refs["set_id"], "source_opportunities": len(frame.opportunities), "output_set_id": created["set_id"], "output_unit_id": output_unit, "output_ids": list(output_frame.contribution_ids), "output_author_passes": "pending; exact population frozen", "quality_claim": "declared source quotation cases only; no scientific/calibrated/whole-record/public-policy claim"})):
        with (OUTPUT / filename).open("xb") as stream:
            stream.write(canonical_bytes(value) + b"\n")
    print(json.dumps({"outcome": "passed", "source_evaluation_id": grade.id, "output_set_id": created["set_id"], "output_candidates": len(contributions)}))
except BaseException as error:
    with (OUTPUT / "failure.json").open("x") as stream:
        json.dump({"outcome": "failed", "type": type(error).__name__, "message": str(error)}, stream)
    raise
