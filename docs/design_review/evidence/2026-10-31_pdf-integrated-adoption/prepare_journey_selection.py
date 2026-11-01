"""Choose actual pinned integrated source evidence for the external interface journey.

Read-only source inspection. No predictions, references or evaluation rows are read.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import (
    load_source_view,
    selected_source_views,
)
from corpus_structure.settings import Settings
from sqlalchemy import text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("retain the previous interface selection")
    settings = Settings()
    settings = settings.model_copy(
        update={"database": settings.database.model_copy(update={"url": args.database})}
    )
    with (
        open_runtime_engine(
            settings, "ci-integrated-interface-input", purpose="read"
        ) as engine,
        engine.connect() as conn,
    ):
        conn.execute(text("SET TRANSACTION READ ONLY"))
        refs = [
            ref
            for ref in selected_source_views(conn, args.run_id)
            if ref.analysis_eligible
        ]
        views = [load_source_view(conn, ref.id, analysis=False) for ref in refs]
        assert len(views) == 5, "journey requires the five intact analysis views"
        pins = {tuple(sorted(ref.native_product.values().items())) for ref in refs}
        assert len(pins) == 1, (
            "all selected sections must consume one integrated document"
        )
        pin = dict(next(iter(pins)))
        formula_view, formula = next(
            (view, item)
            for view in views
            for item in view.items
            if item.get("label") == "formula" and item.get("prov")
        )
        _, table = next(
            (view, item)
            for view in views
            for item in view.items
            if item.get("label") == "table" and item.get("data", {}).get("table_cells")
        )
        # A retained failed request independently exercises evidence reachability.
        # It is not selected source text and is never relabelled as a successful parse.
        raw = conn.execute(
            text("""
                SELECT b.descriptor->'observation'->>'raw_response_digest'
                FROM ops.pdf_product_input i
                JOIN ops.pdf_product_body b ON b.task_id=i.input_task_id
                  AND b.product_key=i.input_product_key
                WHERE i.task_id=:task AND i.product_key=:key
                  AND i.role='recognition'
                  AND b.descriptor->'observation'->>'outcome' IN ('partial','failed')
                  AND b.descriptor->'observation'->>'raw_response_digest' IS NOT NULL
                ORDER BY i.input_index LIMIT 1
            """),
            {"task": pin["task_id"], "key": pin["product_key"]},
        ).scalar_one()
        occurrence = conn.execute(
            text("""
                SELECT occurrence_id FROM kb.pdf_occurrence
                WHERE task_id=:task AND product_key=:key AND pointer=:pointer
                ORDER BY occurrence_id LIMIT 1
            """),
            {
                "task": pin["task_id"],
                "key": pin["product_key"],
                "pointer": formula["self_ref"],
            },
        ).scalar_one()
        kind = conn.execute(
            text(
                "SELECT kind FROM ops.pdf_product WHERE task_id=:task "
                "AND product_key=:key AND content_digest=:digest"
            ),
            {
                "task": pin["task_id"],
                "key": pin["product_key"],
                "digest": pin["content_digest"],
            },
        ).scalar_one()
        assert kind == "integrated", "journey requires the selected integrated product"
        selection = {
            "run_id": args.run_id,
            **pin,
            "source_view_id": formula_view.ref.id,
            "formula_pointer": formula["self_ref"],
            "formula_occurrence_id": occurrence,
            "section_pointer": formula_view.ref.section_pointer,
            "membership": formula_view.ref.membership,
            "table_pointer": table["self_ref"],
            "cell_index": 0,
            "artifact_digest": raw,
            "analysis_source_view_ids": [ref.id for ref in refs],
        }
    with args.output.open("x") as stream:
        json.dump(selection, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(selection, ensure_ascii=False))


if __name__ == "__main__":
    main()
