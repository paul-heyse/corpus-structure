"""Server ownership closure rejects invalid membership despite a callback success."""

from hashlib import sha256

import pyarrow as pa
import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
)
from corpus_structure.semantic.pdf_records import iter_native_records
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, stage_schema

from .test_pdf_staging import private_build as private_build


@pytest.mark.parametrize("defect", ["orphan", "repeated-owner"])
def test_native_owner_counts_refuse_missing_or_duplicate_membership(
    private_build, semantic_writer_engine, defect
):
    build = private_build
    document = DoclingDocument(name="independent ownership control")
    document.add_text(label=DocItemLabel.TEXT, text="one owned item")

    def no_parts(*args):
        raise AssertionError("bounded ownership fixture must not need external values")

    rows = {}
    for row in iter_native_records(
        document.model_dump(mode="json", by_alias=True),
        product_id=build.product_id,
        revision_id=build.revision_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
        record_id_for=lambda address, kind: sha256((address + "\0" + kind).encode()).hexdigest(),
        write_scalar=no_parts,
    ):
        family = "header" if row.kind == "document" else row.kind
        rows.setdefault(family, []).append(dict(row.values))
    members = rows["membership"]
    owned = next(row for row in members if row["field_name"] == "texts")
    if defect == "orphan":
        members.remove(owned)
    else:
        # Two edges from the same parent are still two owners; DISTINCT parent
        # counting would hide this independently constructed invalid input.
        members.append(owned | {"ordinal": owned["ordinal"] + 1})
    with semantic_writer_engine.begin() as conn:
        for family in ("header", "native", "membership", "reference"):
            adopt_pdf_batch(
                conn,
                build,
                "owner-control-" + family,
                {family: [pa.RecordBatch.from_pylist(rows[family], schema=stage_schema(family))]},
            )
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
            "owner-health",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
        # Challenge the independent SQL invariant, rather than letting the native
        # callback reject this fixture before the server's ownership check runs.
        conn.execute(
            text(
                "SELECT ops.record_pdf_native_validation(:build,:task,:attempt,:holder,"
                ":frozen,true)"
            ),
            dict(
                build=build.build_id,
                task=build.task_id,
                attempt=build.attempt,
                holder=build.holder,
                frozen=frozen.frozen_digest,
            ),
        )
    with (
        pytest.raises(DBAPIError, match="native orphan or repeated containment owner"),
        semantic_writer_engine.begin() as conn,
    ):
        conn.execute(
            text("SELECT * FROM ops.validate_pdf_build(:build,:task,:attempt,:holder,:frozen)"),
            dict(
                build=build.build_id,
                task=build.task_id,
                attempt=build.attempt,
                holder=build.holder,
                frozen=frozen.frozen_digest,
            ),
        )
