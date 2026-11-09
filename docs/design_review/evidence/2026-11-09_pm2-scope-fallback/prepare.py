"""Authenticate and prepare one sentence-coherent parent per native parser profile."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from corpus_structure.orchestrate.pm2_stage import _partition, _sentences
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent
OLD_REQUEST = (
    ROOT
    / "docs/design_review/evidence/2026-11-08_pm2-parsers/raw/book-parser-request.json"
)
RELEASE = "release:ca0d3cbe0eb56ce659afada0f4b1692624558622ebf61bfdd9a93b44aa11354f"
PROJECT = "nce-grinstead-snell-full-book"
VIEW_ID = 383
SOURCE_START = 811
COUNTS = {"maverick": 28, "dipo": 130}
EXPECTED = {
    "maverick": ((811, 4564), ((811, 2742), (2742, 4564))),
    "dipo": ((811, 15015), ((811, 7866), (7866, 15015))),
}
TARGET = StorageTarget(
    database="corpus_structure_dev",
    database_oid=25921445,
    system_identifier="7701811359771751232",
    host="/var/run/postgresql",
    port=5434,
    purpose="maintenance",
)


def main() -> None:
    previous = json.loads(OLD_REQUEST.read_bytes())
    source = next(
        scope["source"]
        for scope in previous["scopes"]
        if scope["source"]["source_view_id"] == VIEW_ID
    )
    profiles = {
        provider: next(
            scope["profile"]
            for scope in previous["scopes"]
            if scope["profile"]["provider"] == provider
            and scope["source"]["source_view_id"] == VIEW_ID
        )
        for provider in COUNTS
    }
    realization_id = f"source:pm2-scope-fallback:{RELEASE}"
    settings = Settings()
    budget = PublishedReadBudget(max_rows=200_000, max_bytes=128 * 1024**2)
    results = {}
    with (
        open_runtime_engine(settings, "pm2-scope-fallback-prepare", purpose="maintenance") as engine,
        engine.begin() as conn,
    ):
        verify_target(conn, TARGET, purpose="maintenance")
        prepared = open_release(conn, RELEASE)
        conn.execute(
            text("SELECT ops.validate_structural_source(CAST(:pin AS jsonb))"),
            {"pin": json.dumps(source)},
        )
        view = load_source_view(
            conn,
            VIEW_ID,
            analysis_context=prepared,
            read_budget=budget,
        )
        if view.ref.projection_digest != source["projection_digest"]:
            raise ValueError("retained source projection differs from its authenticated pin")
        canonical_sentences = _sentences(view)
        first = next(
            index
            for index, (start, _end) in enumerate(canonical_sentences)
            if start == SOURCE_START
        )
        for provider, sentence_count in COUNTS.items():
            parent = (SOURCE_START, canonical_sentences[first + sentence_count - 1][1])
            children = _partition(parent, canonical_sentences)
            if (parent, children) != EXPECTED[provider]:
                raise ValueError(f"{provider} source boundaries differ from the reviewed prep")
            results[provider] = {
                "parent_extent": list(parent),
                "canonical_sentence_count": sentence_count,
                "children": [list(bounds) for bounds in children],
                "parent_digest": source["native_content_digest"],
                "projection_digest": source["projection_digest"],
            }

        realization = table("data.realization")
        conn.execute(
            insert(realization)
            .values(
                realization_id=realization_id,
                release_id=RELEASE,
                project_id=PROJECT,
            )
            .on_conflict_do_nothing(index_elements=[realization.c.realization_id])
        )
        binding = conn.execute(
            select(
                realization.c.release_id,
                realization.c.project_id,
                realization.c.state,
            ).where(realization.c.realization_id == realization_id)
        ).one()
        if tuple(binding) != (RELEASE, PROJECT, "active"):
            raise ValueError("private parser realization is not active on the exact release")

    assets = str((ROOT / "build/models/pm2").resolve())
    for provider, (parent, _children) in EXPECTED.items():
        request = {
            "project": PROJECT,
            "release": RELEASE,
            "realization": realization_id,
            "assets": assets,
            "scopes": [
                {
                    "source": source,
                    "extent": list(parent),
                    "profile": profiles[provider],
                }
            ],
        }
        path = EVIDENCE / "raw" / f"{provider}-request.json"
        path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    (EVIDENCE / "raw" / "scope-preparation.json").write_text(
        json.dumps(
            {
                "release": RELEASE,
                "realization": realization_id,
                "source_view_id": VIEW_ID,
                "native_product_digest": source["native_content_digest"],
                "projection_digest": source["projection_digest"],
                "recipe_digest": source["recipe_digest"],
                "parent_scopes": results,
                "realization_binding": {
                    "release": binding.release_id,
                    "project": binding.project_id,
                    "state": binding.state,
                },
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"prepared": results, "realization": realization_id}, indent=2))


if __name__ == "__main__":
    main()
