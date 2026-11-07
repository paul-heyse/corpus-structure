"""Encode independent attachment judgments as one protected operation pass."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import PROTOCOL, decode_authored, decode_frame

FACETS = ("attachment_head", "attachment_tail", "attachment_direction", "attachment_scope")
STATES = {
    "supported": "stated",
    "unsupported": "stated",
    "ambiguous": "unresolved",
    "unassessed": "uninspected",
}


def _case(contribution_id, facet, judgment, reason, alternative):
    if judgment not in STATES or not isinstance(reason, str) or not reason.strip():
        raise ValueError("each independently authored facet needs a judgment and source reason")
    return {
        "case_id": f"{contribution_id}:{facet}",
        "facet": facet,
        "anchor_ids": [],
        "inspected_scope": "selected exact native endpoint and section scope",
        "source_state": STATES[judgment],
        "judgment": judgment,
        "alternatives": (
            [{"semantic_type": "definition.defining_text_attachment", **alternative}]
            if judgment == "supported" else []
        ),
        "explanation": reason,
        "assessor_provenance": {"method": "independent_original_source"},
        "contribution_kind": "relation",
        "contribution_id": contribution_id,
    }


def _event_cases(event, authored, sections):
    if set(authored) != set(FACETS):
        raise ValueError("each emitted event requires exactly the four independent facets")
    endpoints = event["endpoints"]
    anchor_ids = {role: [a["anchor_id"] for a in rows] for role, rows in endpoints.items()}
    scope = {
        "kind": "native_section_scope",
        **{
            role: sorted({
                sections[re.sub(r"/data/table_cells/[0-9]+$", "", a["pointer"])]
                for a in anchors
            })
            for role, anchors in endpoints.items()
        },
    }
    alternatives = {
        "attachment_head": anchor_ids["term"],
        "attachment_tail": anchor_ids["defining_text"],
        "attachment_direction": ["term", "defining_text"],
        "attachment_scope": scope,
    }
    cases = []
    for facet in FACETS:
        choice = authored[facet]
        case = _case(event["contribution_id"], facet, choice["judgment"],
                     choice["reason"], {facet: alternatives[facet]})
        if "alternatives" in choice:
            case["alternatives"] = [
                {"semantic_type": "definition.defining_text_attachment", facet: value}
                for value in choice["alternatives"]
            ]
        cases.append(case)
    statuses = {case["judgment"] for case in cases}
    joint = next(
        status for status in ("unsupported", "ambiguous", "unassessed", "supported")
        if status in statuses
    )
    cases.append(_case(
        event["contribution_id"], "defining_text_attachment_correctness", joint,
        " ".join(case["explanation"] for case in cases),
        {"endpoint_semantics": [
            {"role": role, "anchor_ids": anchor_ids[role], "fields": {}}
            for role in ("term", "defining_text")
        ]},
    ))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("judgments", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--parents", nargs=2, type=int)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    judgments = json.loads(args.judgments.read_text(encoding="utf-8"))
    frame = decode_frame(packet["frame"])
    if set(judgments) != {event["contribution_id"] for event in packet["events"]}:
        raise ValueError("the independently authored judgment population differs from the packet")
    payload = {
        "protocol": PROTOCOL,
        "release_id": frame.release_id,
        "unit_ref": frame.unit,
        "guideline": frame.guideline_version,
        "rubric_version": frame.rubric_version,
        "context_policy": frame.context_policy,
        "operation_question": frame.operation_question,
        "operation_version": frame.operation_version,
        "domain": frame.domain,
        "direction": frame.direction,
        "reason": "Independent exact source assessment of emitted attachment roles and scope.",
        "cases": [
            case
            for event in packet["events"]
            for case in _event_cases(
                event, judgments[event["contribution_id"]], packet["native_section_by_pointer"]
            )
        ],
        "adjudication_passes": args.parents or [],
    }
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    decode_authored(encoded, frame)
    with args.output.open("xb") as stream:
        stream.write(encoded)


if __name__ == "__main__":
    main()
