"""I06 native-schema/geometry and PostgreSQL datatype probe; no product publication."""
from __future__ import annotations

import argparse
import copy
import json
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from docling_core.types.doc import (
    BoundingBox, CoordOrigin, DocItemLabel, DoclingDocument, GroupLabel, ImageRef,
    ProvenanceItem, Size, TableCell, TableData,
)
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, insert, null, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

HERE = Path(__file__).resolve().parent


def native_case():
    doc = DoclingDocument(name="Independent I06 fixture")
    doc.add_page(page_no=1, size=Size(width=612, height=792))
    section = doc.add_group(label=GroupLabel.SECTION, name="Independent section")
    subsection = doc.add_group(label=GroupLabel.SECTION, name="Independent subsection", parent=section)
    doc.add_heading(text="Independent section", level=1, parent=section)
    box = BoundingBox(l=20, t=30, r=150, b=60, coord_origin=CoordOrigin.TOPLEFT)
    prov = ProvenanceItem(page_no=1, bbox=box, charspan=(0, 3))
    doc.add_text(label=DocItemLabel.FORMULA, text="x^2", orig="x²", prov=prov, parent=subsection)
    doc.add_text(label=DocItemLabel.FORMULA, text="x^2", orig="x²", prov=prov, parent=subsection)
    cells = [TableCell(start_row_offset_idx=0, end_row_offset_idx=1,
                       start_col_offset_idx=0, end_col_offset_idx=1,
                       text="12.3400", column_header=False)]
    doc.add_table(data=TableData(num_rows=1, num_cols=1, table_cells=cells), parent=subsection)
    return doc


def validate_variants(payload, validators):
    out = {}
    cases = {"native": payload}
    bad = copy.deepcopy(payload)
    bad["texts"][0]["label"] = "invented_label"
    cases["unknown_label"] = bad
    bad = copy.deepcopy(payload)
    bad["body"]["children"].append({"$ref": "#/texts/99999"})
    cases["dangling_reference"] = bad
    bad = copy.deepcopy(payload)
    bad["texts"][0]["parent"] = {"$ref": "#/texts/99999"}
    cases["wrong_parent"] = bad
    for name, value in cases.items():
        result = {}
        for mode, validator in validators.items():
            errors = list(validator.iter_errors(value))
            result[mode] = [{"instance": list(e.absolute_path), "schema": list(e.absolute_schema_path),
                             "message": e.message} for e in errors[:10]]
        try:
            loaded = DoclingDocument.model_validate_json(json.dumps(value))
            loaded.validate_document()
            result["native"] = "accepted"
        except Exception as exc:
            result["native"] = {"type": type(exc).__name__, "message": str(exc)[:1500]}
        out[name] = result
    return out


def database_roundtrip(payload):
    name = "corpus_pdf_i06_" + uuid4().hex[:12]
    marker = "I06 owned probe " + uuid4().hex
    admin = psycopg.connect("dbname=postgres host=/var/run/postgresql port=5434", autocommit=True)
    created = False
    engine = None
    try:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        created = True
        admin.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(name), sql.Literal(marker)))
        engine = create_engine(f"postgresql+psycopg:///{name}?host=/var/run/postgresql&port=5434")
        meta = MetaData()
        tab = Table("native_probe", meta, Column("id", Integer, primary_key=True),
                    Column("body", JSONB(none_as_null=True)))
        with engine.begin() as conn:
            meta.create_all(conn)
            conn.execute(insert(tab), [{"id": 1, "body": payload},
                                      {"id": 2, "body": {"explicit": None, "lexical": "12.3400"}},
                                      {"id": 3, "body": JSON.NULL}])
            conn.execute(insert(tab).values(id=4, body=null()))
            rows = dict(conn.execute(select(tab.c.id, tab.c.body)).all())
            sql_nulls = dict(conn.execute(select(tab.c.id, tab.c.body.is_(None))).all())
            assert rows[1] == payload
            assert "omitted" not in rows[2] and rows[2]["explicit"] is None
            assert rows[2]["lexical"] == "12.3400"
            assert sql_nulls[3] is False and sql_nulls[4] is True
            reloaded = DoclingDocument.model_validate_json(json.dumps(rows[1]))
            reloaded.validate_document()
            assert reloaded.export_to_dict() == payload
            result = {"outcome": "passed", "database": name, "checks": ["native JSON structure",
                "array order/pointers", "lexical numeric string", "omitted/present null", "SQL NULL vs JSON null",
                "native reload after JSONB"]}
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            ownership = admin.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s", (name,)).fetchone()
            if ownership != (marker,):
                raise RuntimeError("owned scratch database marker differs; refusing removal")
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
        admin.close()
    result["owned_database_removed"] = True
    return result



def image_custody(raw):
    image_doc = DoclingDocument(name="Missing image payload is not an absent picture")
    image_doc.add_picture(image=ImageRef(mimetype="image/png", dpi=72,
        size=Size(width=2, height=2), uri=Path("schema-missing-image.png")))
    path = raw / "schema-missing-image.document.json"
    path.write_text(json.dumps(image_doc.export_to_dict()))
    reloaded = DoclingDocument.load_from_json(path)
    assert len(reloaded.pictures) == 1
    result = {"default_reload": "accepted structure with one picture and unresolved local image reference"}
    try:
        loaded = DoclingDocument.load_from_json(path, allow_local_images=True)
        result["trusted_reload"] = {"outcome": "accepted", "picture_count": len(loaded.pictures),
                                      "image_retained": loaded.pictures[0].image is not None}
    except Exception as exc:
        result["trusted_reload"] = {"outcome": "failed", "type": type(exc).__name__, "message": str(exc)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path)
    args = parser.parse_args()
    raw = HERE / "raw"
    raw.mkdir(exist_ok=True)
    prefix = "schema-real" if args.document else "schema"
    doc = native_case() if args.document is None else DoclingDocument.model_validate_json(args.document.read_bytes())
    before = doc.export_to_dict()
    doc.validate_document()
    payload = doc.export_to_dict()
    (raw / f"{prefix}-native.document.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    validators = {}
    for mode in ("validation", "serialization"):
        schema = DoclingDocument.model_json_schema(mode=mode)
        Draft202012Validator.check_schema(schema)
        registry = Registry().with_resource("urn:i06:docling:" + mode, DRAFT202012.create_resource(schema))
        validators[mode] = Draft202012Validator(schema, registry=registry)
        (raw / f"{prefix}-{mode}.json").write_text(json.dumps(schema, indent=2))
    outcomes = validate_variants(payload, validators)
    assert outcomes["native"]["native"] == "accepted"
    assert not outcomes["native"]["validation"]
    assert outcomes["unknown_label"]["native"] != "accepted"
    assert outcomes["dangling_reference"]["native"] != "accepted"
    outside = native_case()
    outside.texts[1].prov[0].bbox.l = -50
    outside.texts[1].prov[0].bbox.r = 800
    outside_before = outside.export_to_dict()
    outside.validate_document()
    outside_after = outside.export_to_dict()
    normalization = {"changed": outside_before != outside_after,
                     "before": outside_before["texts"][1]["prov"],
                     "after": outside_after["texts"][1]["prov"]}
    result = {"scope": "I06 native fixture/schema and actual PostgreSQL JSONB datatype; not protected product publication",
              "versions": {p: version(p) for p in ("docling-core", "pydantic", "jsonschema", "sqlalchemy", "psycopg")},
              "document": str(args.document) if args.document else "independent hand-authored fixture",
              "validation_changed_initial": before != payload, "cases": outcomes,
              "geometry_normalization": normalization, "image_custody": image_custody(raw), "database": database_roundtrip(payload)}
    (raw / f"{prefix}-results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"outcome": "passed", "geometry_changed": normalization["changed"],
                      "cases": list(outcomes), "database": result["database"]}, indent=2))


if __name__ == "__main__":
    main()
