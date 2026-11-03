"""Select current run-bound PDF handles, refusing stale pins or changed five-section scope."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, tuple_

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import (
    load_source_view,
    resolve_native_sections,
    selected_source_views,
)
from corpus_structure.settings import Settings

SECTIONS = (
    "1.1: Sets",
    "1.2: Functions",
    "1.3: Relations",
    "1.8: Combinatorial Structures",
    "5.6: The Normal Distribution",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--expected-pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("preserve the prior current-source selection")
    expected = json.loads(args.expected_pin.read_bytes())
    expected = {key: expected[key] for key in ("task_id", "product_key", "content_digest")}
    with (
        open_runtime_engine(Settings(), "ci-current-consumer-selection", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        references = selected_source_views(conn, args.run_id)
        views = {
            reference.id: load_source_view(conn, reference.id)
            for reference in references
            if reference.analysis_eligible
        }
        if len(views) != len(SECTIONS):
            raise ValueError("current run must select exactly the five intact analysis sections")
        catalog = {
            identity: next(
                item["name"] for item in view.items if item["self_ref"] == view.ref.section_pointer
            )
            for identity, view in views.items()
        }
        resolved = resolve_native_sections(catalog, SECTIONS)
        for view in views.values():
            if view.ref.native_product.values() != expected:
                raise ValueError("current selected source differs from the explicit expected pin")
            if view.ref.membership != "descendants":
                raise ValueError("current selected section is not intact descendant membership")
        formula = next(
            (view, item)
            for identity in resolved
            for view in (views[identity],)
            for item in view.items
            if item.get("label") == "formula" and item.get("prov")
        )
        cell = next(
            (views[identity].ref.id, item["self_ref"], index, cell)
            for identity in resolved
            for item in views[identity].items
            if item.get("label") == "table"
            for index, cell in enumerate(item["data"]["table_cells"])
            # Cell inspection exposes retained content independently of optional
            # cell geometry. Region rendering below uses the formula's own provenance.
            if cell.get("text", "").strip()
        )
        selected_view, selected_formula = formula
        reader = PublishedPdfReader(conn, ProductReference(**expected))
        if reader.product_kind() != "integrated":
            raise ValueError("the current journey requires an integrated source product")
        occurrence = next(
            reader.iter_rows(
                "companion",
                {"family": "occurrence", "pointer": selected_formula["self_ref"]},
            )
        )["body"]["occurrence_id"]
        # Failed raw observations remain source evidence. This only reads the
        # immutable input declarations; it never reads extractor predictions.
        # Current integrated inputs are sealed record companions. The small
        # observation bodies retain their dedicated observation-only storage.
        pins = [
            (item["task_id"], item["product_key"], item["content_digest"])
            for item in reader.iter_companions("input")
            if item.get("role") == "recognition"
        ]
        products, bodies = table("ops.pdf_product"), table("ops.pdf_product_body")
        observation = bodies.c.descriptor["observation"]
        raw_digest = conn.execute(
            select(observation["raw_response_digest"].as_string())
            .join_from(
                bodies,
                products,
                (bodies.c.task_id == products.c.task_id)
                & (bodies.c.product_key == products.c.product_key),
            )
            .where(
                products.c.kind == "recognition_observation",
                tuple_(products.c.task_id, products.c.product_key, products.c.content_digest).in_(
                    pins
                ),
                observation["outcome"].as_string().in_(("partial", "failed")),
                observation["raw_response_digest"].as_string().is_not(None),
            )
            .order_by(products.c.task_id, products.c.product_key)
            .limit(1)
        ).scalar_one()
        selection = {
            "verified_at": datetime.now(UTC).isoformat(),
            "run_id": args.run_id,
            **expected,
            "source_view_id": selected_view.ref.id,
            "section_pointer": selected_view.ref.section_pointer,
            "membership": selected_view.ref.membership,
            "formula_pointer": selected_formula["self_ref"],
            "formula_occurrence_id": occurrence,
            "table_source_view_id": cell[0],
            "table_pointer": cell[1],
            "cell_index": cell[2],
            "cell_basis": "retained text-bearing table cell within the five analysis views",
            "cell_bbox_state": "present" if "bbox" in cell[3] else "absent",
            "artifact_digest": raw_digest,
            "artifact_basis": "retained failed-or-partial recognition raw response",
            "search_text": "normal",
            "analysis_views": [asdict(views[identity].ref) for identity in resolved],
            "section_titles": [catalog[identity] for identity in resolved],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        json.dump(selection, output, indent=2)
        output.write("\n")
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
