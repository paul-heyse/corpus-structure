"""Freeze a bounded output-first development unit with no correctness grades."""

from __future__ import annotations

import json

from sqlalchemy import text

from corpus_structure.evaluate.operation_assessment import OperationEvaluationFrame, encode_frame
from corpus_structure.evaluate.record_references import source_binding
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "wce-gs120-method-development-20261106"
RUN, CUT = 161, 245
GUIDELINE = "nce12-attachment-guide-1"
FACET = "defining_text_attachment_correctness"


def capture(conn, view, expected_count):
    source, release, projection = conn.execute(
        text("""
        SELECT v.key, r.release_id,v.projection
        FROM kb.source_view v JOIN ops.run r ON r.id=:run AND r.project_id=:project
        JOIN ops.run_source_view sv ON sv.run_id=r.id AND sv.source_view_id=v.id
        JOIN ops.completed_result cr ON cr.run_id=r.id AND cr.cut_id=:cut
        WHERE v.id=:view
        """), dict(project=PROJECT, run=RUN, cut=CUT, view=view),
    ).one()
    bound = source_binding(conn, source_run_id=RUN, source_view_id=view, source_cut_id=CUT)
    rows = conn.execute(
        text("""
        SELECT c.contribution_id,r.body,c.position,o.question,o.operation_version
        FROM kb.source_contribution c JOIN ops.task_result r ON r.task_id=c.task_id
        JOIN kb.source_contribution_operation o ON o.task_id=c.task_id AND o.operation_key=c.operation_key
        WHERE c.source_view_id=:view AND c.kind='relation'
          AND c.semantic_type='definition.defining_text_attachment'
          AND EXISTS(SELECT FROM ops.cut_task ct WHERE ct.origin_task_id=c.task_id AND ct.cut_id=:cut)
        ORDER BY c.contribution_id
        """), dict(cut=CUT, view=view),
    ).all()
    if len(rows) != expected_count or len({(r.question, r.operation_version) for r in rows}) != 1:
        raise ValueError("declared all-attachments source-view frame changed")
    anchors, events = {}, []
    for identity, body, position, question, version in rows:
        relation = body["contributions"][position]
        contributors = {c["contribution_id"]: c for c in body["contributions"]}
        event = dict(contribution_id=identity, endpoints={})
        for endpoint in relation["endpoints"]:
            member = contributors[endpoint["contribution_id"]]
            event["endpoints"][endpoint["role"]] = [
                dict(
                    anchor_id=anchor["anchor_id"],
                    pointer=anchor["pointer"],
                    start=anchor["start"],
                    end=anchor["end"],
                    quote=anchor["source_piece"],
                ) for anchor in member["anchors"]
            ]
            for anchor in member["anchors"]:
                scope = {
                    key: anchor[key] for key in ("space", "precision", "pointer", "start", "end")
                }
                scope["pin"] = dict(anchor["pin"], source=bound)
                anchors[anchor["anchor_id"]] = scope
        events.append(event)
    frame = encode_frame(
        OperationEvaluationFrame(
            unit=source, release_id=release, guideline_version=GUIDELINE,
            rubric_version="nce12-attachment-role-direction-scope-1",
            context_policy="exact-native-source-view-1",
            operation_question=question, operation_version=version, domain="statistics",
            direction="output_first", pin=dict(relation["pin"], source=bound),
            anchor_ids=tuple(anchors), anchor_scopes=tuple(anchors.values()),
            contribution_ids=tuple(event["contribution_id"] for event in events),
        )
    )
    return dict(
        sample=dict(
            sampling=dict(
                seed=0, strata={source: "one-full-source-view"},
                inclusion_probabilities={source: 1},
                provenance={"selection": "purposeful complete source-view development slice"},
                cohort="gs120-attachment-development",
            ),
            frames={source: frame},
        ),
        author_packet=dict(
            unit=source, events=events, text=projection["text"],
            pieces=projection["pieces"], frame=frame,
        ),
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("view", type=int)
    parser.add_argument("expected_count", type=int)
    args = parser.parse_args()
    with (
        open_runtime_engine(Settings(), "nce-attachment-freeze", purpose="evaluate") as engine,
        engine.connect() as conn,
    ):
        print(json.dumps(capture(conn, args.view, args.expected_count), ensure_ascii=False))
