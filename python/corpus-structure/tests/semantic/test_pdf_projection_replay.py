"""Actual projected region keys preserve exact replay and finalized membership."""

import json

import pytest
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch
from semantic.pdf_staging_support import private_build as private_build


def test_native_projection_replays_exact_keys_and_refuses_changed_membership(
    private_build, commit_db_engine, commit_writer_engine, tmp_path
):
    import pyarrow as pa

    build = private_build
    document = DoclingDocument(name="two-region projection")
    for number in (1, 2):
        document.add_page(page_no=number, size=Size(width=200, height=300))
    item = document.add_text(label=DocItemLabel.TEXT, text="expected")
    for number in (1, 2):
        item.prov.append(
            ProvenanceItem(
                page_no=number,
                bbox=BoundingBox(l=10, t=20, r=30, b=40, coord_origin=CoordOrigin.TOPLEFT),
                charspan=(0, 8),
            )
        )
    result = StreamingPdfResult(
        document, PdfStreamSpool(tmp_path / "pages"), "success", (), b"{}", ()
    )
    for replay in result.write_record_batches(
        tmp_path / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
    ):
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                with commit_writer_engine.begin() as conn:
                    adopt_pdf_batch(
                        conn,
                        build,
                        f"{replay.family}:{index}",
                        {replay.family: (reader.get_batch(index),)},
                    )
    with commit_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "health",
            [
                {
                    "conversion": "success",
                    "source_scope": "whole_document",
                    "display_coverage": "unknown",
                    "inline_coverage": "unknown",
                    "cell_coverage": "unknown",
                }
            ],
            "health",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(commit_writer_engine, frozen)
    bodies = {}
    with commit_db_engine.connect() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        for family in ("access", "region"):
            bodies[family] = (
                conn.execute(
                    text(
                        "SELECT to_jsonb(r)-'product_id'-'revision_id' "
                        f"FROM kb.pdf_record_{family} r "
                        "WHERE product_id=:build AND revision_id=:build"
                    ),
                    {"build": build.build_id},
                )
                .scalars()
                .all()
            )
    assert sorted(
        (r["pointer"], r["region_index"], r["page_no"], r["left"], r["top"], r["origin"])
        for r in bodies["region"]
    ) == [
        ("#/texts/0", 0, 1, 10, 20, "top_left"),
        ("#/texts/0", 1, 2, 10, 20, "top_left"),
    ]
    params = dict(
        build=build.build_id,
        task=build.task_id,
        attempt=build.attempt,
        holder=build.holder,
        frozen=frozen.frozen_digest,
    )
    statement = text(
        "SELECT ops.adopt_pdf_access(:build,:task,:attempt,:holder,:frozen,:family,"
        "CAST(:body AS jsonb))"
    )
    for family, rows in bodies.items():
        for row in rows:
            with commit_writer_engine.begin() as conn:
                conn.execute(statement, params | {"family": family, "body": json.dumps(row)})
        row = rows[0]
        changes = (
            ({"left": row["left"] + 1}, {"region_index": 99})
            if family == "region"
            else ({"text": "changed"}, {"pointer": "#/unpublished"})
        )
        for change in changes:
            with (
                pytest.raises(DBAPIError, match="projection membership is immutable"),
                commit_writer_engine.begin() as conn,
            ):
                conn.execute(
                    statement, params | {"family": family, "body": json.dumps(row | change)}
                )
