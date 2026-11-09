"""Submit one independently authored judgment through the existing protected owner."""

import argparse
import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import (
    adjudication_packet,
    author_packet,
    decode_frame,
    record_pass,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pass-kind", choices=("A", "B", "C"), required=True)
    parser.add_argument("--set-receipt", required=True, type=Path)
    parser.add_argument("--focal-cases", required=True, type=Path)
    parser.add_argument("--arm-freeze", required=True, type=Path)
    parser.add_argument("--author-notes", required=True, type=Path)
    args = parser.parse_args()
    frozen, notes = read(args.set_receipt), read(args.author_notes)
    (unit,) = frozen["units"]
    frame = decode_frame(unit["frame"])
    cases = read(args.focal_cases)
    targets = {
        row["label"].casefold(): row["reference"]["component_id"]
        for row in read(args.arm_freeze)["config_by_arm"]["literal"]["target_components"]
    }
    authored = dict(
        protocol="source-operation-reference-1",
        release_id=frame.release_id,
        unit_ref=frame.unit,
        guideline=frame.guideline_version,
        rubric_version=frame.rubric_version,
        context_policy=frame.context_policy,
        operation_question=frame.operation_question,
        operation_version=frame.operation_version,
        domain=frame.domain,
        direction=frame.direction,
        reason="Independent source-only adjudication under the frozen competitive rubric.",
        cases=[],
    )
    for opportunity in frame.opportunities:
        key = opportunity.opportunity_id
        row = notes["judgments"][key]
        target = row["target"]
        value = cases[key]
        alternative = (
            {"retrieval_outcome": "insufficient_evidence"}
            if target is None
            else {"retrieval_target_id": targets[target.casefold()]}
        )
        authored["cases"].append(
            dict(
                case_id=key,
                facet=opportunity.facet,
                anchor_ids=[value["anchor"]["anchor_id"]],
                inspected_scope=frame.inspected_scope,
                source_state=opportunity.source_state,
                judgment="supported",
                alternatives=[alternative],
                explanation=row["reason"],
                assessor_provenance={"actor": notes["actor"], "source_only": True},
                contribution_kind=(
                    "contextual_relationship_decision"
                    if target is None
                    else "contextual_candidate_list"
                ),
                candidate_selector={"retrieval_occurrence_id": value["occurrence_id"]},
            )
        )
    with (
        open_runtime_engine(
            Settings(), "pm2-protected-competitive-reference", purpose="evaluate"
        ) as engine,
        engine.begin() as conn,
    ):
        if args.pass_kind == "C":
            authored["adjudication_passes"] = adjudication_packet(conn, unit["unit_id"])[
                "adjudication_passes"
            ]
        else:
            author_packet(conn, unit["unit_id"])
        identity = record_pass(
            conn,
            unit_id=unit["unit_id"],
            pass_kind=args.pass_kind,
            actor=notes["actor"],
            authored=canonical_bytes(authored),
            frame=frame,
        )
    print(
        canonical_bytes(
            dict(
                set_id=frozen["set_id"],
                unit_id=unit["unit_id"],
                pass_id=identity,
                pass_kind=args.pass_kind,
            )
        ).decode()
    )


if __name__ == "__main__":
    main()
