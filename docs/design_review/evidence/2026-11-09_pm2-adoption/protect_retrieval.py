"""Attach independent source decisions to the exact protected frame before retrieval."""
import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import (
    adjudication_packet,
    decode_frame,
    record_pass,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SOURCES = {
    "A": ("pm2-retrieval-coordinator-a", "retrieval-reference.md"),
    "B": ("pm2-retrieval-interpretation-agent-b", "retrieval-pass-b.md"),
    "C": ("pm2-retrieval-dma-agent-c", "retrieval-adjudication.md"),
}


def load(name):
    return json.loads((RAW / name).read_bytes())


def main():
    frozen = load("retrieval-reference-set.json")
    (unit,) = frozen["units"]
    frame = decode_frame(unit["frame"])
    cases = load("retrieval-case-source.json")
    inventory = load("retrieval-target-inventory.json")
    # Bind the source-adjudicated expected meaning to an actual immutable eligible
    # target. No provider prediction or expected answer is added to arm configuration.
    binomial = [
        candidate for candidate in inventory
        if candidate["label"].strip().lower() in {"binomial distribution", "the binomial distribution"}
        and "bernoulli" in candidate["description"].lower()
    ]
    if len(binomial) > 1:
        raise ValueError("the frozen target meaning has ambiguous actual component custody")
    expectations = {
        "affine-x": ("contextual_relationship_decision", {"retrieval_outcome": "insufficient_evidence"}),
        "affine-z": ("contextual_relationship_decision", {"retrieval_outcome": "insufficient_evidence"}),
        "cross-chapter-binomial": (
            "contextual_candidate_list",
            {"retrieval_target_id": binomial[0]["reference"]["component_id"]} if binomial else None,
        ),
        "empty-adverb": ("contextual_candidate_list", {"retrieval_outcome": "empty"}),
    }
    with open_runtime_engine(Settings(), "pm2-retrieval-golden", purpose="evaluate") as engine:
        receipts = []
        with engine.begin() as conn:
            for kind, (actor, evidence) in SOURCES.items():
                note = (HERE / evidence).read_text()
                authored = dict(
                    protocol="source-operation-reference-1", release_id=frame.release_id,
                    unit_ref=frame.unit, guideline=frame.guideline_version,
                    rubric_version=frame.rubric_version, context_policy=frame.context_policy,
                    operation_question=frame.operation_question, operation_version=frame.operation_version,
                    domain=frame.domain, direction=frame.direction, reason=note,
                    cases=[],
                )
                for opportunity in frame.opportunities:
                    case_id = opportunity.opportunity_id
                    emitted_kind, alternative = expectations[case_id]
                    identity = cases[case_id]
                    authored["cases"].append(dict(
                        case_id=case_id, facet=opportunity.facet,
                        anchor_ids=[identity["anchor"]["anchor_id"]],
                        inspected_scope=frame.inspected_scope, source_state=opportunity.source_state,
                        judgment="supported" if alternative else "unassessed",
                        alternatives=[alternative] if alternative else [],
                        explanation=(
                            "Exact source-only reading in " + evidence + "."
                            if alternative else
                            "The expected definition is in the source, but no unambiguous matching "
                            "component entered the frozen target inventory."
                        ),
                        assessor_provenance={"actor": actor, "source_only_evidence": evidence},
                        contribution_kind=emitted_kind,
                        candidate_selector={"retrieval_occurrence_id": identity["occurrence_id"]},
                    ))
                if kind == "C":
                    authored["adjudication_passes"] = adjudication_packet(
                        conn, unit["unit_id"]
                    )["adjudication_passes"]
                pass_id = record_pass(
                    conn, unit_id=unit["unit_id"], pass_kind=kind, actor=actor,
                    authored=canonical_bytes(authored), frame=frame,
                )
                receipts.append(dict(pass_id=pass_id, unit_id=unit["unit_id"], kind=kind,
                                     authored=authored))
    (RAW / "retrieval-reference-passes.json").write_bytes(canonical_bytes(receipts) + b"\n")
    print(json.dumps({"set_id": frozen["set_id"], "passes": [r["pass_id"] for r in receipts]}))


if __name__ == "__main__":
    main()
