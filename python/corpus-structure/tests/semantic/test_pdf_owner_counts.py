"""Server ownership closure independently rejects deliberately tampered membership."""

import json
from hashlib import sha256

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
    freeze_pdf_build,
    prepare_pdf_build,
)
from corpus_structure.semantic.pdf_records import iter_native_records
from semantic.pdf_staging_support import private_build as private_build


@pytest.mark.parametrize(
    "defect",
    ["orphan", "repeated-owner", "disconnected-cycle", "root-cycle", "scalar-gap", "empty-scalar"],
)
def test_native_owner_counts_refuse_missing_or_duplicate_membership(
    private_build, commit_writer_engine, commit_db_engine, tmp_path, defect
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
        record_id_for=lambda address, kind: sha256(
            (build.source_digest + "\0" + address + "\0" + kind).encode()
        ).hexdigest(),
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
    from pdf_acceptance_support import stage_pdf_document

    stage_pdf_document(commit_writer_engine, build, tmp_path, document)
    with commit_writer_engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    # Tamper with the prepared database representation under fixture authority.
    # The genuine producer certified its valid original document; these invalid
    # rows challenge SQL ownership directly and never claim a passed oracle.
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        assert conn.scalar(
            text("SELECT root_id FROM ops.pdf_record_document WHERE product_id=:build"),
            {"build": build.build_id},
        ) == rows["header"][0]["root_id"]
        relations = {
            "native": "kb.pdf_record_native",
            "membership": "kb.pdf_record_membership",
            "reference": "kb.pdf_record_reference",
        }
        # This owned database fixture deliberately bypasses only the immutable
        # write guard while replacing the independently authored invalid rows.
        # Restore it before the inventory checker runs under publisher authority.
        for relation in relations.values():
            conn.exec_driver_sql(
                "ALTER TABLE " + relation + " DISABLE TRIGGER semantic_immutable"
            )
        for family in ("reference", "membership", "native"):
            conn.execute(
                text(f"DELETE FROM {relations[family]} WHERE product_id=:build"),
                {"build": build.build_id},
            )
        for family in ("native", "membership", "reference"):
            for value in rows.get(family, ()):
                value = {
                    key: json.loads(item)
                    if key.endswith("_json") and isinstance(item, str)
                    else item
                    for key, item in value.items()
                }
                conn.execute(
                    text(
                        f"INSERT INTO {relations[family]} SELECT (jsonb_populate_record("
                        f"NULL::{relations[family]}, CAST(:body AS jsonb))).*"
                    ),
                    {"body": json.dumps(value)},
                )
        for relation in relations.values():
            conn.exec_driver_sql(
                "ALTER TABLE " + relation + " ENABLE TRIGGER semantic_immutable"
            )
    with (
        pytest.raises(
            DBAPIError,
            match=(
                r"native (orphan or repeated containment owner|"
                r"containment cycle or unreachable record|ordered membership incomplete)"
            ),
        ),
        commit_db_engine.begin() as conn,
    ):
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            text(
                "SELECT ops.pdf_check_build_inventory(:build,:source,"
                "(SELECT project_id FROM ops.pdf_task_context(:task)))"
            ),
            dict(build=build.build_id, source=build.source_digest, task=build.task_id),
        )
