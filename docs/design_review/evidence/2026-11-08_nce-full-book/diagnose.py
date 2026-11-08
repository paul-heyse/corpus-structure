"""Summarize actual whole-book producer outcomes without assigning support grades."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enrich import journey
from sqlalchemy import text

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def inspect(conn, cuts):
    """Count each retained report and operation once within the selected completed cuts."""
    rows = conn.execute(
        text("""
        WITH selected AS (
            SELECT DISTINCT ct.origin_task_id, m.name, r.body
            FROM ops.cut_task ct JOIN ops.task t ON t.id=ct.task_id
            JOIN ops.method_config cfg ON cfg.id=t.method_config_id
            JOIN ops.method m ON m.id=cfg.method_id
            JOIN ops.task_result r ON r.task_id=ct.origin_task_id
            WHERE ct.cut_id=ANY(:cuts)
        ), operations AS (
            SELECT name, op->>'question' AS question, op->>'outcome' AS outcome
            FROM selected
            CROSS JOIN LATERAL jsonb_array_elements(body->'contribution_operations') op
        ), model AS (
            SELECT name, stage->>'operation', stage->>'outcome'
            FROM selected
            CROSS JOIN LATERAL jsonb_array_elements(
              body->'structural_product'->'definition_components'->'stages') stage
        ), populations AS (
            SELECT name, question, outcome FROM operations
            UNION ALL SELECT * FROM model
            UNION ALL SELECT name,'producer',body->>'outcome' FROM selected
        )
        SELECT name,question,outcome,count(*) AS count
        FROM populations GROUP BY name,question,outcome
        ORDER BY name,question,outcome
    """),
        {"cuts": cuts},
    )
    return tuple(dict(row) for row in rows.mappings())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    args = parser.parse_args()
    inventory = json.loads((args.baseline / "source-inventory.json").read_bytes())
    phases = {}
    for phase in ("scoped", "model", "artifact", "contextual"):
        receipt = args.baseline / f"{phase}-summary.json"
        if receipt.exists():
            payload = json.loads(receipt.read_bytes())
            phases[phase] = payload["results"] if phase == "contextual" else payload
    cuts = sorted({record["cut_id"] for phase in phases.values() for record in phase})
    with (
        open_runtime_engine(Settings(), "nce-full-book-diagnosis", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        outcomes = inspect(conn, cuts) if cuts else ()
    result = dict(
        source=inventory["run"],
        physical_pages=len(inventory["physical_pages"]),
        native_region_pages=inventory["native_region_pages"],
        projected_pages=inventory["projected_pages"],
        source_views=len(inventory["views"]),
        absent_phase_receipts=sorted({"scoped", "model", "artifact", "contextual"} - phases.keys()),
        selected_cuts=cuts,
        outcomes=outcomes,
        assessment_standing="operational diagnostic counts; independent semantic support separate",
    )
    journey.retain(args.baseline / "diagnostics.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
