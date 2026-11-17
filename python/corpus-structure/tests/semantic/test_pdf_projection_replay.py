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
    adopt_pdf_companions,
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
    from pdf_acceptance_support import stage_pdf_document

    stage_pdf_document(commit_writer_engine, build, tmp_path, document)
    bodies = {}
    with commit_db_engine.connect() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        for family in ("access", "region"):
            bodies[family] = (
                conn.execute(
                    text(
                        "SELECT to_jsonb(r)-'product_id'-'revision_id' "
                        f"FROM ops.pdf_stage_{family} r "
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
    )
    statement = text(
        "SELECT ops.stage_pdf_access_batch(:build,:task,:attempt,:holder,"
        "jsonb_build_array(jsonb_build_object('family',:family,'body',CAST(:body AS jsonb))))"
    )
    for family, rows in bodies.items():
        for row in rows:
            with commit_writer_engine.begin() as conn:
                conn.execute(statement, params | {"family": family, "body": json.dumps(row)})
        row = rows[0]
        changes = ({"left": row["left"] + 1},) if family == "region" else ({"text": "changed"},)
        for change in changes:
            with (
                pytest.raises(DBAPIError, match=f"changed {family} projection"),
                commit_writer_engine.begin() as conn,
            ):
                conn.execute(
                    statement, params | {"family": family, "body": json.dumps(row | change)}
                )

    with commit_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(commit_writer_engine, frozen)
    # Projection membership now freezes with its certified producer, before the
    # reconstruction oracle or final validation can run. Even exact late writes refuse.
    for family, rows in bodies.items():
        with pytest.raises(DBAPIError, match="not owned/open"), commit_writer_engine.begin() as conn:
            conn.execute(statement, params | {"family": family, "body": json.dumps(rows[0])})
