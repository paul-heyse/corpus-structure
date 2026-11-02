"""Small controlled native publications for maintained source-consumer journeys."""

from hashlib import sha256

import pyarrow as pa

from corpus_structure.ingest.pdf_health import FormulaOutcome
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, begin_pdf_build


def publish_native_record_fixture(
    engine, directory, *, task_id, attempt, holder, product, document
):
    """Exercise the production stage/freeze/validate/seal phases with the fixture's native graph."""
    values = product.values()
    with engine.begin() as conn:
        build = begin_pdf_build(
            conn,
            task_id=task_id,
            attempt=attempt,
            holder=holder,
            source_digest=sha256(product.original).hexdigest(),
            recipe_digest=sha256(product.recipe_bytes).hexdigest(),
            schema_digest=sha256(product.schema_bytes).hexdigest(),
            replay_key="fixture-records:" + values["product_key"],
        )
    result = StreamingPdfResult(
        document,
        PdfStreamSpool(directory / "pages"),
        values["health"]["conversion"],
        tuple(values["health"].get("issues", ())),
        product.recipe_bytes,
        tuple(
            FormulaOutcome(row["pointer"], row["outcome"], row.get("error"))
            for row in values["health"].get("formula_outcomes", ())
        ),
    )
    for replay in result.write_record_batches(
        directory / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
    ):
        with pa.memory_map(str(replay.path), "r") as source:
            batches = pa.ipc.open_file(source)
            for index in range(batches.num_record_batches):
                with engine.begin() as conn:
                    adopt_pdf_batch(
                        conn,
                        build,
                        f"{replay.family}:{index}",
                        {
                            replay.family: (batches.get_batch(index),),
                        },
                    )
    with engine.begin() as conn:
        health = dict(values["health"])
        outcomes = health.pop("formula_outcomes", ())
        wrapper = dict(health, source_scope=values["source_scope"])
        for key in ("page_start", "page_end"):
            if key in values:
                wrapper[key] = values[key]
        adopt_pdf_companion_batch(conn, build, "health", (wrapper,), "fixture-health")
        if values.get("parent_task_id") is not None:
            adopt_pdf_companion_batch(
                conn,
                build,
                "input",
                (
                    dict(
                        role="structural",
                        task_id=values["parent_task_id"],
                        product_key=values["parent_product_key"],
                        content_digest=values["parent_digest"],
                    ),
                ),
                "fixture-parent",
            )
        metadata = []
        for kind, records in (
            ("formula_outcomes", outcomes),
            *(
                (kind, values.get(kind, ()))
                for kind in (
                    "derivation_mappings",
                    "cell_reports",
                    "inline_alignment_reports",
                    "recognition_coverage",
                    "inline_candidate_pages",
                )
            ),
            ("runtime_report", (values["runtime_report"],) if "runtime_report" in values else ()),
        ):
            metadata.extend(
                dict(kind=kind, ordinal=index, value=value) for index, value in enumerate(records)
            )
        if metadata:
            adopt_pdf_companion_batch(conn, build, "native_metadata", metadata, "fixture-metadata")
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        return seal_pdf_build(conn, frozen, values["product_key"])
