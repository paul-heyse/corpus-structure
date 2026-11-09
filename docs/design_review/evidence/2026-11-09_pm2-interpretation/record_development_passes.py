"""Record the source-only review and adjudication in existing protected custody."""
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    adjudication_packet,
    decode_frame,
    record_pass,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

FOLDER = Path(__file__).resolve().parent
ACTORS = {"A": "pm2-source-only-a", "B": "pm2-source-only-b", "C": "pm2-coordinator"}


def expectation(frame, explanation, actor):
    (opportunity,) = frame.opportunities
    case = opportunity.opportunity_id
    alternatives = []
    kind = "proposal"
    question = None
    if case == "foundation-definition":
        question = "passage_functions"
        alternatives = [
            {"interpretation_selected_keys": labels, "interpretation_state": "proposed"}
            for labels in (["definition"], ["definition", "assertion"])
        ]
    elif case == "fair-coin-modality":
        question = "quantity"
        kind = "composite"
        alternatives = [{
            "interpretation_literal_pieces": ["1/8"],
            "interpretation_literal_anchors": [{"pointer": "#/texts/14369", "start": 98, "end": 101}],
            "interpretation_normalized_value": 0.125,
        }]
    selector = {
        "semantic_type": "interpretation." + frame.operation_question,
        "interpretation_projection_extent": [opportunity.start, opportunity.end],
    }
    if question:
        selector["interpretation_question_key"] = question
    return dict(
        case_id=case, facet=opportunity.facet, anchor_ids=[], inspected_scope=frame.inspected_scope,
        source_state=opportunity.source_state, judgment="supported" if alternatives else "unassessed",
        alternatives=alternatives, explanation=explanation,
        assessor_provenance={"actor": actor, "partition": "exposed development", "material": "source-only packet and rubric"},
        contribution_kind=kind, candidate_selector=selector,
    )


def main():
    notes = json.loads((FOLDER/"reference-pass-notes.json").read_bytes())
    frozen = json.loads((FOLDER/"raw/development-operation-set.json").read_bytes())
    references = table("eval.reference_unit")
    passes = table("eval.reference_pass")
    results = []
    with open_runtime_engine(Settings(), "pm2-development-reference", purpose="evaluate") as engine:
        with engine.begin() as conn:
            units = conn.execute(select(references).where(references.c.set_id == frozen["set_id"])
                                 .order_by(references.c.id)).mappings().all()
            if len(units) != len(frozen["units"]) or conn.scalar(
                select(passes.c.id).where(passes.c.unit_id.in_([unit["id"] for unit in units])).limit(1)
            ) is not None:
                raise ValueError("expected a fresh, exact, unreviewed development reference set")
            for unit in units:
                frame = decode_frame(unit["context"][0])
                (source,) = frame.opportunities
                for kind, actor in ACTORS.items():
                    payload = dict(
                        protocol="source-operation-reference-1", release_id=frame.release_id,
                        unit_ref=frame.unit, guideline=frame.guideline_version,
                        rubric_version=frame.rubric_version, context_policy=frame.context_policy,
                        operation_question=frame.operation_question, operation_version=frame.operation_version,
                        domain=frame.domain, direction=frame.direction, reason=notes[kind][source.opportunity_id],
                        cases=[expectation(frame, notes[kind][source.opportunity_id], actor)],
                    )
                    if kind == "C":
                        payload["adjudication_passes"] = adjudication_packet(conn, unit["id"])["adjudication_passes"]
                    authored = json.dumps(payload, ensure_ascii=False).encode()
                    pass_id = record_pass(conn, unit_id=unit["id"], pass_kind=kind, actor=actor,
                                          authored=authored, frame=frame)
                    results.append(dict(unit_id=unit["id"], pass_id=pass_id, pass_kind=kind, authored=payload))
    print(json.dumps({"set_id": frozen["set_id"], "passes": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
