"""Independent native rows and access projection correspondence on PostgreSQL."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.pdf_record_identity import byte_root, emit_parts

from .test_pdf_record_reader import NativeRows, native


@pytest.fixture
def access_database(semantic_bare_engine):
    value = native()
    value["pages"] = {
        "1": {"size": {"width": 100.0, "height": 100.0}, "page_no": 1},
        "2": {"size": {"width": 200.0, "height": 300.0}, "page_no": 2},
    }
    value["texts"][0]["prov"] = [
        {
            "page_no": 1,
            "bbox": {"l": -0.0, "t": 20.0, "r": 30.0, "b": 40.0, "coord_origin": "TOPLEFT"},
            "charspan": [0, 9],
        },
        {
            "page_no": 2,
            "bbox": {"l": 10.0, "t": 30.0, "r": 40.0, "b": 50.0, "coord_origin": "TOPLEFT"},
            "charspan": [0, 9],
        },
    ]
    value["body"]["meta"] = {"vendor": {"z": 1, "a": [True, None]}}
    lowered = NativeRows(value)
    with semantic_bare_engine.begin() as conn:
        for ddl in (
            "CREATE SCHEMA ops",
            "CREATE SCHEMA kb",
            "CREATE TABLE ops.pdf_record_document(product_id text,revision_id text,root_id text)",
            (
                "CREATE TABLE kb.pdf_record_native(product_id text,revision_id "
                "text,record_id text,native_type text,native_address "
                "text,scalars_json jsonb,structure_json jsonb)"
            ),
            (
                "CREATE TABLE kb.pdf_record_membership(product_id "
                "text,revision_id text,parent_id text,field_name text,ordinal "
                "bigint,value_kind text,record_id text,scalar_json "
                "jsonb,stream_id text,member_key text,member_key_stream_id text)"
            ),
            (
                "CREATE TABLE ops.pdf_artifact_stream(product_id text,revision_id "
                "text,stream_id text,byte_length bigint,byte_root "
                "text,encoding_profile text)"
            ),
            (
                "CREATE TABLE ops.pdf_artifact_part(product_id text,revision_id "
                "text,stream_id text,ordinal bigint,body bytea)"
            ),
            (
                "CREATE TABLE kb.pdf_record_access(product_id text,revision_id "
                "text,pointer text,ordinal bigint,label text,parent_pointer "
                "text,section_pointer text,content_layer text,text "
                "text,native_json jsonb)"
            ),
            (
                "CREATE TABLE kb.pdf_record_region(product_id text,revision_id "
                "text,pointer text,region_index bigint,page_no bigint,page_width "
                'numeric,page_height numeric,"left" numeric,top numeric,"right" '
                "numeric,bottom numeric,origin text)"
            ),
        ):
            conn.exec_driver_sql(ddl)
        for row in lowered.rows:
            if row.kind == "document":
                fields = ("product_id", "revision_id", "root_id")
                relation = "ops.pdf_record_document"
            elif row.kind == "native":
                fields = (
                    "product_id",
                    "revision_id",
                    "record_id",
                    "native_type",
                    "native_address",
                    "scalars_json",
                    "structure_json",
                )
                relation = "kb.pdf_record_native"
            elif row.kind == "membership":
                fields = (
                    "product_id",
                    "revision_id",
                    "parent_id",
                    "field_name",
                    "ordinal",
                    "value_kind",
                    "record_id",
                    "scalar_json",
                    "stream_id",
                    "member_key",
                    "member_key_stream_id",
                )
                relation = "kb.pdf_record_membership"
            else:
                continue
            values = {name: row.values.get(name) for name in fields}
            placeholders = [
                f"CAST(:{name} AS jsonb)" if name.endswith("_json") else ":" + name
                for name in fields
            ]
            conn.execute(
                text(
                    f"INSERT INTO {relation}({','.join(fields)}) VALUES({','.join(placeholders)})"
                ),
                values,
            )
        for stream, chunks in lowered.streams.items():
            length, root = byte_root(chunks)
            conn.execute(
                text(
                    "INSERT INTO ops.pdf_artifact_stream "
                    "VALUES('b','b',:stream,:length,:root,:profile)"
                ),
                dict(
                    stream=stream, length=length, root=root.hex(), profile=lowered.profiles[stream]
                ),
            )
            for part in emit_parts(stream, chunks):
                conn.execute(
                    text(
                        "INSERT INTO ops.pdf_artifact_part VALUES('b','b',:stream,:ordinal,:body)"
                    ),
                    dict(stream=stream, ordinal=part.ordinal, body=part.body),
                )
        for ordinal, node in enumerate((value["body"], value["texts"][0], value["furniture"])):
            conn.execute(
                text(
                    "INSERT INTO kb.pdf_record_access "
                    "VALUES('b','b',:pointer,:ordinal,:label,:parent,NULL,:layer,:text"
                    ",CAST(:native AS jsonb))"
                ),
                dict(
                    pointer=node["self_ref"],
                    ordinal=ordinal,
                    label=node["label"],
                    parent=node.get("parent", {}).get("$ref"),
                    layer=node.get("content_layer", "body"),
                    text=node.get("text"),
                    native=json.dumps(node),
                ),
            )
        conn.exec_driver_sql(
            "INSERT INTO kb.pdf_record_region "
            "VALUES('b','b','#/texts/0',0,1,100,100,0,20,30,40,'top_left')"
        )
        conn.exec_driver_sql(
            "INSERT INTO kb.pdf_record_region "
            "VALUES('b','b','#/texts/0',1,2,200,300,10,30,40,50,'top_left')"
        )
        sql_dir = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
        conn.exec_driver_sql(
            (sql_dir / "pdf_record_identity.sql").read_text(),
            execution_options={"no_parameters": True},
        )
        conn.exec_driver_sql(
            (sql_dir / "pdf_record_access_correspondence.sql").read_text(),
            execution_options={"no_parameters": True},
        )
    yield semantic_bare_engine


def test_native_projection_correspondence_accepts_actual_values(access_database):
    with access_database.connect() as conn:
        conn.execute(text("SELECT ops.pdf_check_access_correspondence('b')"))
        assert conn.execute(
            text(
                "SELECT ops.pdf_projection_scalar_matches('0'::jsonb,'{\"native_flo"
                'at64":"8000000000000000"}\'::jsonb)'
            )
        ).scalar_one()


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE kb.pdf_record_access SET text='invented' WHERE pointer='#/texts/0'",
        (
            "UPDATE kb.pdf_record_access SET "
            "native_json=jsonb_set(native_json,'{text}', '\"invented\"') WHERE "
            "pointer='#/texts/0'"
        ),
        "UPDATE kb.pdf_record_access SET parent_pointer='#/furniture' WHERE pointer='#/texts/0'",
        "UPDATE kb.pdf_record_access SET ordinal=9 WHERE pointer='#/texts/0'",
        "DELETE FROM kb.pdf_record_access WHERE pointer='#/texts/0'",
        "UPDATE kb.pdf_record_access SET content_layer='forged-layer' WHERE pointer='#/texts/0'",
        "UPDATE kb.pdf_record_access SET section_pointer='#/body' WHERE pointer='#/texts/0'",
        (
            "UPDATE kb.pdf_record_access SET "
            "native_json=jsonb_set(native_json,'{body_fake}', '1') WHERE "
            "pointer='#/body'"
        ),
        (
            "UPDATE kb.pdf_record_access SET "
            "native_json=jsonb_set(native_json,'{meta,vendor,z}', '2') WHERE "
            "pointer='#/body'"
        ),
        "UPDATE kb.pdf_record_region SET top=21",
        "UPDATE kb.pdf_record_region SET page_width=101",
        "DELETE FROM kb.pdf_record_region",
        "UPDATE kb.pdf_record_region SET revision_id='other' WHERE region_index=1",
        "UPDATE kb.pdf_record_access SET revision_id='other' WHERE pointer='#/texts/0'",
    ],
)
def test_native_projection_refuses_independent_deviation(access_database, change):
    with access_database.begin() as conn:
        conn.exec_driver_sql(change)
    with access_database.connect() as conn, pytest.raises(DBAPIError, match="native access"):
        conn.execute(text("SELECT ops.pdf_check_access_correspondence('b')"))


def test_projection_lookups_use_complete_revision_keys(access_database):
    with access_database.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO kb.pdf_record_native SELECT product_id,'other',record_id,"
            "native_type,native_address,'{}'::jsonb,'{}'::jsonb FROM kb.pdf_record_native"
        )
        conn.exec_driver_sql(
            "INSERT INTO kb.pdf_record_membership SELECT product_id,'other',parent_id,"
            "field_name,ordinal,value_kind,record_id,scalar_json,stream_id,member_key,"
            "member_key_stream_id FROM kb.pdf_record_membership"
        )
        conn.execute(text("SELECT ops.pdf_check_access_correspondence('b')"))
