"""Server ownership closure rejects invalid membership despite a callback success."""

import json
from hashlib import sha256

import pyarrow as pa
import pytest
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    PageItem,
    ProvenanceItem,
    Size,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
)
from corpus_structure.semantic.pdf_publication_native import publication_sql
from corpus_structure.semantic.pdf_records import iter_native_records
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, stage_schema

from .pdf_staging_support import private_build as private_build


@pytest.mark.parametrize(
    "defect",
    ["orphan", "repeated-owner", "disconnected-cycle", "root-cycle", "scalar-gap", "empty-scalar"],
)
def test_native_owner_counts_refuse_missing_or_duplicate_membership(
    private_build, semantic_writer_engine, semantic_db_engine, defect
):
    build = private_build
    document = DoclingDocument(name="independent ownership control")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    document.add_text(
        label=DocItemLabel.TEXT,
        text="one owned item",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=0, t=0, r=50, b=10, coord_origin="TOPLEFT"),
            charspan=(0, 14),
        ),
    )

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
    elif defect == "repeated-owner":
        # Two edges from the same parent are still two owners; DISTINCT parent
        # counting would hide this independently constructed invalid input.
        members.append(owned | {"ordinal": owned["ordinal"] + 1})
    elif defect == "root-cycle":
        root = rows["header"][0]["root_id"]
        row = next(row for row in rows["native"] if row["record_id"] == root)
        structure = json.loads(row["structure_json"])
        structure["fields"]["body"]["target"] = root
        row["structure_json"] = json.dumps(structure)
    elif defect in {"scalar-gap", "empty-scalar"}:
        if defect == "empty-scalar":
            members[:] = [row for row in members if row["field_name"] != "charspan"]
        else:
            next(row for row in members if row["field_name"] == "charspan" and row["ordinal"] == 1)[
                "ordinal"
            ] = 2
    else:
        # Both disconnected nodes have exactly one owner. Only root reachability,
        # rather than the owner counts alone, establishes the missing global closure.
        template = next(row for row in rows["native"] if row["native_type"] == "GroupItem")
        for index, (record, child) in enumerate((("cycle-a", "cycle-b"), ("cycle-b", "cycle-a"))):
            scalars = json.loads(template["scalars_json"])
            scalars.pop("parent", None)
            address = f"#/groups/{1000000 + index}"
            scalars["self_ref"] = address
            rows["native"].append(
                template
                | dict(
                    record_id=record,
                    native_address=address,
                    scalars_json=json.dumps(scalars),
                    structure_json=json.dumps(
                        {
                            "fields": {
                                "children": {"kind": "array", "length": 0},
                                "parent": {"kind": "object", "target": child},
                            }
                        }
                    ),
                )
            )
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
    # Install only the current owned function in this disposable test database;
    # source authoring intentionally waits for the coordinator's integrated freeze.
    sql = publication_sql()
    start = sql.index("CREATE OR REPLACE FUNCTION ops.validate_pdf_build(")
    stop = sql.index("CREATE OR REPLACE FUNCTION ops.seal_pdf_build(", start)
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql(sql[start:stop], execution_options={"no_parameters": True})
    with (
        pytest.raises(
            DBAPIError,
            match=(
                r"native (orphan or repeated containment owner|"
                r"containment cycle or unreachable record|ordered membership incomplete)"
            ),
        ),
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
