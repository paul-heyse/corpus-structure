"""Typed inventory guards challenge real Docling rows with independent defects."""

import json
from hashlib import sha256
from types import SimpleNamespace

import pytest
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    PageItem,
    ProvenanceItem,
    Size,
)
from sqlalchemy import Column, MetaData, Table, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner
from corpus_structure.semantic.pdf_access_projection import write_pdf_access_projection
from corpus_structure.semantic.pdf_publication_native import pdf_inventory_native_sql
from corpus_structure.semantic.pdf_records import iter_native_records


@pytest.mark.parametrize(
    "defect,expected,state",
    [
        (None, None, None),
        ("orphan", "native orphan or repeated containment owner", "23514"),
        ("repeated-owner", "native orphan or repeated containment owner", "23514"),
        ("disconnected-cycle", "native containment cycle or unreachable record", "23514"),
        ("scalar-gap", "native ordered membership incomplete", "23514"),
        ("access-parent", "native parent/child backpointer differs", "23514"),
        ("access-missing-child", "native parent/child backpointer differs", "23514"),
        ("access-missing-children", "native parent/child backpointer differs", "23514"),
        ("access-dangling-child", "native parent/child backpointer differs", "23514"),
        ("access-malformed-child", "native parent/child backpointer differs", "23514"),
        ("access-null-children", "cannot extract elements from a scalar", "22023"),
        ("access-duplicate-child", None, None),
        ("access-absent-parent", None, None),
        (
            "duplicate-address",
            "duplicate native address including overflow representation",
            "23514",
        ),
        (
            "reference-spelling",
            "native reference index does not correspond to supplied spelling",
            "23514",
        ),
        ("missing-access", "native access inventory incomplete", "23514"),
    ],
)
def test_generated_inventory_retains_independent_containment_expectations(
    native_rollback, tmp_path, defect, expected, state
):
    document = DoclingDocument(name="inventory control")
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
    body = document.model_dump(mode="json", by_alias=True)

    def no_parts(*args):
        raise AssertionError("bounded fixture has no external values")

    rows = {}
    for row in iter_native_records(
        body,
        product_id="inventory-control",
        revision_id="inventory-control",
        release_id="inventory-control",
        source_digest="a" * 64,
        record_id_for=lambda address, kind: sha256((address + "\0" + kind).encode()).hexdigest(),
        write_scalar=no_parts,
    ):
        rows.setdefault(row.kind, []).append(
            {
                key: json.loads(value)
                if key.endswith("_json") and isinstance(value, str)
                else value
                for key, value in row.values.items()
            }
        )
    addresses = {row["native_address"]: row["record_id"] for row in rows["native"]}
    for reference in rows["reference"]:
        reference["target_id"] = addresses[reference["native_pointer"]]
    projection = tmp_path / "projection.jsonl"
    write_pdf_access_projection(
        document.model_dump(mode="json", by_alias=True, exclude_none=True), projection
    )
    rows["access"] = [
        json.loads(line)["body"]
        | dict(product_id="inventory-control", revision_id="inventory-control")
        for line in projection.read_text().splitlines()
        if json.loads(line)["family"] == "access"
    ]
    members = rows["membership"]
    owned = next(row for row in members if row["field_name"] == "texts")
    if defect == "orphan":
        members.remove(owned)
    elif defect == "repeated-owner":
        members.append(owned | {"ordinal": owned["ordinal"] + 1})
    elif defect == "scalar-gap":
        next(row for row in members if row["field_name"] == "charspan" and row["ordinal"] == 1)[
            "ordinal"
        ] = 2
    elif defect == "access-parent":
        next(row for row in rows["access"] if row["pointer"] == "#/texts/0")["parent_pointer"] = (
            "#/furniture"
        )
    elif defect in {
        "access-missing-child",
        "access-missing-children",
        "access-dangling-child",
        "access-malformed-child",
        "access-null-children",
        "access-duplicate-child",
        "access-absent-parent",
    }:
        parent = next(row for row in rows["access"] if row["pointer"] == "#/body")
        children = parent["native_json"]["children"]
        if defect in {"access-missing-child", "access-absent-parent"}:
            children.clear()
            if defect == "access-absent-parent":
                # The inventory guard compares reciprocal links only for
                # present parents. This keeps its existing scope explicit.
                next(row for row in rows["access"] if row["pointer"] == "#/texts/0")[
                    "parent_pointer"
                ] = "#/absent"
        elif defect == "access-missing-children":
            del parent["native_json"]["children"]
        elif defect == "access-dangling-child":
            children.append({"$ref": "#/absent"})
        elif defect == "access-malformed-child":
            children.append({})
        elif defect == "access-null-children":
            parent["native_json"]["children"] = None
        else:
            children.append(dict(children[0]))
    elif defect == "duplicate-address":
        rows["native"][1]["native_address"] = rows["native"][0]["native_address"]
    elif defect == "reference-spelling":
        next(row for row in rows["reference"] if row["field_name"] == "$ref")["native_pointer"] = (
            "#/wrong"
        )
    elif defect == "missing-access":
        rows["access"].clear()
    elif defect == "disconnected-cycle":
        template = next(row for row in rows["native"] if row["native_type"] == "GroupItem")
        for index, (record, child) in enumerate((("cycle-a", "cycle-b"), ("cycle-b", "cycle-a"))):
            rows["native"].append(
                template
                | dict(
                    record_id=record,
                    native_address=f"#/groups/{1000000 + index}",
                    scalars_json={
                        **{
                            key: value
                            for key, value in template["scalars_json"].items()
                            if key != "parent"
                        },
                        "self_ref": f"#/groups/{1000000 + index}",
                    },
                    structure_json={
                        "fields": {
                            "children": {"kind": "array", "length": 0},
                            "parent": {"kind": "object", "target": child},
                        }
                    },
                )
            )
    relations = {
        "document": "ops.pdf_record_document",
        "native": "kb.pdf_record_native",
        "membership": "kb.pdf_record_membership",
        "reference": "kb.pdf_record_reference",
        "access": "kb.pdf_record_access",
    }
    tables = {
        key: Table(
            "inventory_" + family,
            MetaData(),
            *(
                Column(field.name, field.type, nullable=field.nullable)
                for field in get_metadata().tables[key].c
            ),
            schema="pg_temp",
        )
        for family, key in relations.items()
    }
    model = SimpleNamespace(tables={**get_metadata().tables, **tables})
    connection = native_rollback.connection
    with native_owner(connection, "corpus_sem_publisher"):
        for family, key in relations.items():
            connection.execute(CreateTable(tables[key]))
            for row in rows.get(family, ()):
                connection.execute(tables[key].insert(), row)
        execute_native_sql(connection, pdf_inventory_native_sql(model))
        call = text(
            "SELECT ops.pdf_check_build_inventory('inventory-control',:source,'inventory-project')"
        )
        if expected is None:
            connection.execute(call, {"source": "a" * 64})
        else:
            with pytest.raises(DBAPIError, match=expected) as failure, connection.begin_nested():
                connection.execute(call, {"source": "a" * 64})
            assert getattr(failure.value.orig, "sqlstate", None) == state
    with native_owner(connection, "corpus_sem_writer"):
        with pytest.raises(DBAPIError) as failure, connection.begin_nested():
            connection.execute(call, {"source": "a" * 64})
        assert getattr(failure.value.orig, "sqlstate", None) == "42501"
