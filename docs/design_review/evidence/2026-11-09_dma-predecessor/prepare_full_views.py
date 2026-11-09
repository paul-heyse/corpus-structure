"""Prepare whole-view record frames from the immutable source-only cut, without reading predictions."""

import argparse
import json
from pathlib import Path

from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
from corpus_structure.evaluate.record_references import encode_frame, source_binding
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from sqlalchemy import select

PROJECT = "nce-grinstead-snell-full-book"
SOURCE_RUN = 404
SOURCE_CUT = 514
ORIGINAL = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
PRODUCT = (
    1627,
    "integrated",
    "35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb",
)
GUIDELINE = "statistics-m1-reference-3"
REFERENCE_POLICY = "statistics-reading-occurrence-2"
PREDICTION_POLICY = "m1-grouped-reading-logistic-1"
VIEWS = {381: "preface assertion control", 382: "chapter-heading empty control"}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument(
        "--section",
        action="store_true",
        help="Prepare the separately retained native-section control instead.",
    )
    args = cli.parse_args()
    if args.section:
        source_run, source_cut, views = (
            424,
            527,
            {408: "native subsection definition and qualification"},
        )
        selection = "Complete retained section selected from the source catalog by extent and role."
    else:
        source_run, source_cut, views = SOURCE_RUN, SOURCE_CUT, VIEWS
        selection = "Full preface and adjacent heading selected by source-only size and role; census within each view."
    settings = Settings()
    frames, strata = {}, {}
    with (
        open_runtime_engine(
            settings, "dma-reference-source", purpose="read"
        ) as reader_engine,
        open_runtime_engine(
            settings, "dma-reference-binding", purpose="evaluate"
        ) as evaluator,
        read_snapshot(reader_engine) as conn,
        read_snapshot(evaluator) as evaluation,
    ):
        run, cut, documents = map(table, ("ops.run", "ops.input_cut", "kb.document"))
        release = conn.execute(
            select(run.c.release_id)
            .join(cut, cut.c.run_id == run.c.id)
            .where(
                run.c.id == source_run,
                run.c.project_id == PROJECT,
                cut.c.id == source_cut,
                cut.c.release_id == run.c.release_id,
            )
        ).scalar_one()
        prepared = open_release(conn, release)
        reader = BoundReader(
            conn, source_run, prepared, cut_id=source_cut, analysis=False
        )
        for identity, stratum in views.items():
            view = reader.source_view(identity)
            ref = view.ref
            product = ref.native_product
            if (
                product.task_id,
                product.product_key,
                product.content_digest,
            ) != PRODUCT:
                raise ValueError(
                    "source view does not use the retained integrated product"
                )
            original = conn.execute(
                select(documents.c.content_hash).where(
                    documents.c.id == ref.document_id, documents.c.project_id == PROJECT
                )
            ).scalar_one()
            if original != ORIGINAL:
                raise ValueError("source view does not use the retained original")
            pin = dict(
                source=source_binding(
                    evaluation,
                    source_run_id=source_run,
                    source_view_id=identity,
                    source_cut_id=source_cut,
                ),
                native_product_task_id=product.task_id,
                product_key=product.product_key,
                product_digest=product.content_digest,
                projection_digest=ref.projection_digest,
                recipe_digest=ref.recipe_digest,
                source_view_id=identity,
            )
            scopes = []
            for item in sorted(
                (*view.items, *view.ancestors), key=lambda row: row["self_ref"]
            ):
                pointer = item["self_ref"]
                if pointer.startswith(("#/tables/", "#/pictures/")):
                    raise ValueError(
                        "this development sample does not declare table or picture scopes"
                    )
                for precision in ("item", "coarse"):
                    scopes.append(
                        dict(
                            pin=pin,
                            space="native",
                            pointer=pointer,
                            precision=precision,
                        )
                    )
                literal = item.get("text")
                if literal:
                    scopes.append(
                        dict(
                            pin=pin,
                            space="native",
                            pointer=pointer,
                            precision="exact",
                            start=0,
                            end=len(literal),
                        )
                    )
            for piece in view.pieces:
                if piece["kind"] != "native_text":
                    continue
                if piece.get("source_field") not in {"text", "orig"}:
                    raise ValueError("undeclared non-text projection carrier")
                if not 0 <= piece["start"] < piece["end"] <= len(view.text):
                    raise ValueError("invalid projection piece")
                scopes.append(
                    dict(
                        pin=pin,
                        space="selected_projection",
                        pointer=piece["item_ref"],
                        precision="exact",
                        start=piece["start"],
                        end=piece["end"],
                    )
                )
            frames[ref.key] = encode_frame(
                RecordEvaluationFrame(
                    unit=ref.key,
                    release_id=release,
                    guideline_version=GUIDELINE,
                    reference_policy_version=REFERENCE_POLICY,
                    prediction_policy_version=PREDICTION_POLICY,
                    pin=pin,
                    anchor_ids=frozenset(),
                    anchor_scopes=tuple(scopes),
                )
            )
            strata[ref.key] = stratum
    sample = dict(
        unit_keys=list(frames),
        frames=frames,
        sampling=dict(
            seed=20261109,
            strata=strata,
            inclusion_probabilities=dict.fromkeys(frames, 1),
            provenance=dict(
                selection=selection,
                limitations="Existing incumbent execution and exposed sentence set predate this freeze. Development only.",
                source_run_id=source_run,
                source_cut_id=source_cut,
                original_sha256=ORIGINAL,
            ),
            cohort="DMA-13 retained whole-view development controls",
        ),
    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(sample, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
