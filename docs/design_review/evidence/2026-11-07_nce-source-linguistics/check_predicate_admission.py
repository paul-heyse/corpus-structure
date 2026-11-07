"""Verify an actual retained qualifier's host and one resealed competing candidate."""

import argparse

from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def check(conn, run_id):
    stored = conn.execute(text("""
        SELECT r.body, v.projection FROM ops.task AS t
        JOIN ops.task_result r ON r.task_id=coalesce(t.reused_task_id,t.id)
        JOIN kb.source_view v ON v.id=t.unit_id
        WHERE t.run_id=:run AND t.unit_type='source_view' AND v.id=135
    """), {"run": run_id}).mappings().one()
    body = stored["body"]
    rows = {row["contribution_id"]: row for row in body["contributions"]}
    attachment = next(
        row["component"] for row in rows.values()
        if row.get("component", {}).get("qualifier_kind") == "assumption"
        and any(
            "certain symmetric gambles" in a["source_piece"]
            for a in rows[row["component"]["qualifier_contribution_id"]]["anchors"]
        )
        and rows[row["component"]["qualifier_contribution_id"]]["component"]["scope"] == "benefit:135"
    )
    cue = rows[attachment["qualifier_contribution_id"]]["component"]
    host = rows[attachment["host_contribution_id"]]["component"]
    other = next(
        row["component"] for row in rows.values()
        if row.get("component", {}).get("kind") == "predicate_frame"
        and row["component"]["annotation"] == cue["annotation"]
        and row["component"]["predicate_token"] not in cue["candidate_tokens"]
    )
    annotation_task = next(
        op["annotation_origin_task_id"] for op in body["contribution_operations"]
        if op["question"] == "source_predicate_frames"
    )
    upstream = conn.scalar(
        text("SELECT body FROM ops.task_result WHERE task_id=:task"),
        {"task": annotation_task},
    )
    annotation = next(
        block for block in source_python(upstream["parse_detail"])["annotations"]
        if "annotation:" + block["dependency_digest"] == cue["annotation"]
    )

    def matches(value, token):
        return conn.scalar(text("""
            SELECT ops.predicate_cue_host_matches(
                CAST(:projection AS jsonb), CAST(:tokens AS jsonb), CAST(:cue AS jsonb), :host
            )
        """), {
            "projection": canonical_bytes(stored["projection"]).decode(),
            "tokens": canonical_bytes(annotation["tokens"]).decode(),
            "cue": canonical_bytes(value).decode(),
            "host": token,
        })

    wrong = other["predicate_token"]
    assert matches(cue, host["predicate_token"]) is True
    assert matches({**cue, "candidate_tokens": [wrong]}, wrong) is False
    return {
        "run_id": run_id,
        "annotation_task": annotation_task,
        "qualified_host": host["predicate_token"],
        "forged_host": wrong,
        "exact_host": "passed",
        "forged_candidate": "refused",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=int)
    args = parser.parse_args()
    with open_runtime_engine(Settings(), "nce-predicate-host-guard", purpose="maintenance") as engine:
        with read_snapshot(engine) as conn:
            print(canonical_bytes(check(conn, args.run_id)).decode())
