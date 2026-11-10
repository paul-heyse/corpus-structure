"""Read the current Section 5.1 replay inputs through the owning heading resolver."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import selected_source_views
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
SCOPE = "grinstead-snell-physical-1-518"


def inspect(release: str, run: int, cut: int) -> dict:
    source = json.loads((HERE / "raw/cross-chapter-current-source.json").read_bytes())
    cue = source["current_cue"]
    heading = source["current_heading"]
    with open_runtime_engine(Settings(), "pm2-section-inventory", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            completed = table("ops.completed_result")
            if (
                conn.execute(
                    select(completed.c.cut_id).where(completed.c.run_id == run)
                ).scalar_one_or_none()
                != cut
            ):
                raise ValueError("heading inventory requires the named completed source cut")
            views = selected_source_views(conn, run)
        if not views or any(
            (view.native_product.task_id, view.native_product.product_key)
            != (source["product_task"], source["product_key"])
            for view in views
        ):
            raise ValueError("heading inventory has drifted from the retained native product")
        (cue_view,) = tuple(
            view.id for view in views if view.projection_digest == cue["projection"]
        )
        (heading_view,) = tuple(
            view.id for view in views if view.projection_digest == heading["projection"]
        )
        frozen = prepare_structural_sources(
            engine,
            tuple(
                StructuralPassageSelection(
                    run_id=run,
                    source_view_id=view.id,
                    passage_id=f"section-replay-source-{view.id}",
                    start=cue["piece_range"][0] if view.id == cue_view else 0,
                    end=cue["piece_range"][1] if view.id == cue_view else 1,
                    scope=SCOPE,
                )
                for view in views
            ),
            read_budget=PublishedReadBudget(max_rows=500_000, max_bytes=384 * 1024 * 1024),
        )
        exact_cue = next(ref for ref in frozen.sources if ref.source_view_id == cue_view)
        if exact_cue.cut_id != cut or exact_cue.projection_digest != cue["projection"]:
            raise ValueError("cue source pin changed")
        passage = next(item for item in frozen.passages if item.source_ref == exact_cue.identity)
        if passage.text != cue["text"]:
            raise ValueError("cue text differs from the authenticated native piece")
        with read_snapshot(engine) as conn:
            reader = BoundReader(conn, run, open_release(conn, release), cut, analysis=False)
            inventory = reader.contextual_section_headings(frozen.sources, cue_view, SCOPE, None)
    matches = [row for row in inventory["targets"] if row["designator"] == "5.1"]
    if not inventory["complete"] or len(matches) != 1:
        raise ValueError("the selected heading population does not resolve one Section 5.1")
    (target,) = matches
    if (
        target["pointer"] != heading["pointer"]
        or target["label"] != heading["text"]
        or not any(
            citation["source_view_id"] == heading_view
            and citation["projection_digest"] == heading["projection"]
            for citation in target["citations"]
        )
    ):
        raise ValueError("resolved heading differs from the independently read source pin")
    return {
        "outcome": "passed",
        "consuming_release": release,
        "source_run": run,
        "source_cut": cut,
        "scope": SCOPE,
        "inventory_source_views": len(frozen.sources),
        "heading_targets": len(inventory["targets"]),
        "cue_source": exact_cue.model_dump(mode="json"),
        "cue_passage": passage.model_dump(mode="json"),
        "source_refs": [ref.model_dump(mode="json") for ref in frozen.sources],
        "target": target,
        "ordinary_replay": "not_run",
        "detached_export": "not_run",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--run", required=True, type=int)
    parser.add_argument("--cut", required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(inspect(args.release, args.run, args.cut), indent=2))
