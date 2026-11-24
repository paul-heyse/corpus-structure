"""Actual projected region keys preserve exact replay and finalized membership."""

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

from corpus_structure.semantic import _pdf_native_calls as calls
from corpus_structure.semantic.identifiers import TaskAttempt, TaskId
from corpus_structure.semantic.pdf_publication import (
    freeze_pdf_build,
    prepare_pdf_build,
    validate_pdf_build,
)
from semantic.pdf_staging_support import private_build as private_build


def test_native_projection_replays_exact_keys_and_refuses_changed_membership(
    private_build, commit_db_engine, commit_writer_engine, tmp_path
):

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
    bodies = {"access": [], "page": []}
    with commit_db_engine.connect() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        copies = conn.execute(
            text(
                "SELECT native_json FROM ops.pdf_stage_access "
                "WHERE product_id=:build AND revision_id=:build ORDER BY pointer"
            ),
            {"build": build.build_id},
        ).scalars()
        for copy in copies:
            if "self_ref" in copy:
                bodies["access"].append({"native_json": copy})
            else:
                bodies["page"].append(copy)
    assert len(bodies["page"]) == 2
    assert all(set(row) == {"native_json"} for row in bodies["access"])

    def write(connection, family, row):
        calls.stage_pdf_access_batch(
            connection,
            build_id=build.build_id,
            task_id=TaskId(build.task_id),
            attempt=TaskAttempt(build.attempt),
            holder=build.holder,
            rows=[{"family": family, "body": row}],
        )

    for family, rows in bodies.items():
        for row in rows:
            with commit_writer_engine.begin() as conn:
                write(conn, family, row)
        row = rows[0]
        changed = (
            row | {"size": dict(width=201, height=300)}
            if family == "page"
            else {"native_json": row["native_json"] | {"name": "changed"}}
        )
        with (
            pytest.raises(DBAPIError, match="changed native projection JSON copy"),
            commit_writer_engine.begin() as conn,
        ):
            write(conn, family, changed)

    with commit_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(commit_writer_engine, frozen)
    with commit_db_engine.connect() as conn:
        conn.execute(text("SET LOCAL ROLE corpus_sem_publisher"))
        assert conn.execute(
            text(
                "SELECT page_no, pointer, region_index "
                "FROM kb.pdf_record_region_address "
                "WHERE product_id=:build AND revision_id=:build ORDER BY page_no"
            ),
            {"build": build.build_id},
        ).all() == [(1, "#/texts/0", 0), (2, "#/texts/0", 1)]
        assert conn.execute(
            text(
                'SELECT pointer, region_index, page_no, "left", top, origin '
                "FROM kb.pdf_record_region_view WHERE product_id=:build AND revision_id=:build "
                "ORDER BY pointer, region_index"
            ),
            {"build": build.build_id},
        ).all() == [
            ("#/texts/0", 0, 1, 10, 20, "top_left"),
            ("#/texts/0", 1, 2, 10, 20, "top_left"),
        ]
        assert conn.execute(
            text(
                "SELECT pointer, parent_pointer, section_pointer, label, content_layer, text "
                "FROM kb.pdf_record_access WHERE product_id=:build AND revision_id=:build "
                "ORDER BY ordinal"
            ),
            {"build": build.build_id},
        ).all() == [
            ("#/body", None, None, "unspecified", "body", None),
            ("#/texts/0", "#/body", None, "text", "body", "expected"),
            ("#/furniture", None, None, "unspecified", "furniture", None),
        ]
    # Projection membership now freezes with its certified producer, before the
    # reconstruction oracle or final validation can run. Even exact late writes refuse.
    for family, rows in bodies.items():
        with (
            pytest.raises(DBAPIError, match="not owned/open"),
            commit_writer_engine.begin() as conn,
        ):
            write(conn, family, rows[0])
