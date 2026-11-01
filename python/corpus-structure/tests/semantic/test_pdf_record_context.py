"""Python and PostgreSQL frames consume one published source-context definition."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, NoResultFound

from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.product_reference import ProductReference


@pytest.fixture
def context_database(semantic_bare_engine):
    with semantic_bare_engine.begin() as conn:
        for ddl in (
            "CREATE SCHEMA ops",
            "CREATE SCHEMA kb",
            (
                "CREATE TABLE ops.pdf_published_revision(build_id text,task_id "
                "bigint,product_key text,logical_digest text,release_id "
                "text,source_digest text,schema_digest text,recipe_digest "
                "text,frozen_digest text,kind text)"
            ),
            (
                "CREATE TABLE kb.pdf_record_access(product_id text,revision_id text,"
                "pointer text,parent_pointer text,native_json jsonb)"
            ),
            (
                "CREATE TABLE kb.pdf_record_companion(product_id text,revision_id "
                "text,family text,local_id text,body jsonb,ordinal bigint)"
            ),
            (
                "CREATE TABLE kb.pdf_record_companion_field(product_id "
                "text,revision_id text,family text,local_id text,field_name "
                "text,stream_id text,scalar_kind text)"
            ),
            (
                "CREATE TABLE ops.pdf_artifact_part(product_id text,revision_id "
                "text,stream_id text,ordinal bigint,body bytea)"
            ),
            (
                "CREATE TABLE kb.pdf_record_endpoint(product_id text,revision_id "
                "text,relation_id text,ordinal bigint,target_task_id "
                "bigint,target_product_key text,target_content_digest "
                "text,occurrence_id text,role text)"
            ),
            (
                "CREATE FUNCTION ops.read_pdf_published_revision(p_task "
                "bigint,p_key text,p_digest text) RETURNS SETOF "
                "ops.pdf_published_revision LANGUAGE sql AS $$ SELECT * FROM "
                "ops.pdf_published_revision WHERE "
                "(task_id,product_key,logical_digest)=(p_task,p_key,p_digest) $$"
            ),
            (
                "INSERT INTO ops.pdf_published_revision "
                "VALUES('b',42,'chosen',repeat('f',64),'r',repeat('a',64),repeat('"
                "b',64),repeat('c',64),'freeze','integrated')"
            ),
        ):
            conn.exec_driver_sql(ddl)
        conn.exec_driver_sql(
            "INSERT INTO kb.pdf_record_access VALUES"
            "('b','b','#/body',NULL,'{}'),"
            "('b','b','#/groups/0','#/body','{}'),"
            "('b','b','#/groups/1','#/groups/0','{}'),"
            "('b','b','#/texts/0','#/groups/1','{\"prov\":[{\"page_no\":1}]}')"
        )
        conn.execute(
            text(
                "INSERT INTO kb.pdf_record_companion "
                "VALUES('b','b','input','2',CAST(:body AS jsonb),2)"
            ),
            {
                "body": '{"role":"recognition","task_id":12,"product_key":"B","content_digest":"'
                + "b" * 64
                + '"}'
            },
        )
        rows = [
            (
                "occurrence",
                "o",
                (
                    '{"occurrence_id":"o","kind":"item","pointer":"#/texts/0","page_no'
                    '":1,"precision":"coarse","address_space":"selected_item"}'
                ),
                0,
            ),
            (
                "occurrence",
                "other",
                (
                    '{"occurrence_id":"other","kind":"item","pointer":"#/texts/1","pag'
                    'e_no":2,"precision":"item","address_space":"selected_item"}'
                ),
                1,
            ),
            (
                "relation",
                "r",
                (
                    '{"relation_id":"r","kind":"decision","outcome":"selected","endpoi'
                    'nts":[{"role":"output","occurrence_id":"o"},{"role":"input","inpu'
                    't_index":2,"occurrence_id":"prior"}]}'
                ),
                0,
            ),
            (
                "coverage",
                "c",
                (
                    '{"coverage_id":"c","scope":"page:1","family":"text","outcome":"pa'
                    'rtial","supports":[{"input_index":2,"coverage_id":"old"}]}'
                ),
                0,
            ),
            (
                "coverage",
                "outside",
                '{"coverage_id":"outside","scope":"page:2","family":"text","outcome":"complete"}',
                1,
            ),
            ("mapping_report", "3", '{"input_index":2,"outcome":"mapped"}', 3),
        ]
        for family, local_id, body, ordinal in rows:
            conn.execute(
                text(
                    "INSERT INTO kb.pdf_record_companion "
                    "VALUES('b','b',:family,:local,:body\\:\\:jsonb,:ordinal)"
                ),
                {"family": family, "local": local_id, "body": body, "ordinal": ordinal},
            )
        conn.exec_driver_sql(
            "INSERT INTO kb.pdf_record_endpoint "
            "VALUES('b','b','r',0,0,'@self','@self','o','output'),('b','b','r'"
            ",1,12,'B',repeat('b',64),'prior','input')"
        )
        from corpus_structure.semantic.pdf_publication_native import _companion_field_sql

        conn.exec_driver_sql(_companion_field_sql(), execution_options={"no_parameters": True})
        helper = (
            Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/pdf_record_context.sql"
        )
        conn.exec_driver_sql(helper.read_text(), execution_options={"no_parameters": True})
        from corpus_structure.semantic.pdf_record_reader_native import pdf_record_context_sql

        conn.exec_driver_sql(pdf_record_context_sql(), execution_options={"no_parameters": True})
    yield semantic_bare_engine


def test_shared_native_context_preserves_scope_precision_and_pins(context_database):
    with context_database.connect() as conn:
        reader = PublishedPdfReader(conn, ProductReference(42, "chosen", "f" * 64))
        actual = reader.source_context(["#/texts/0"], "#/body")
        assert (
            actual
            == conn.execute(
                text(
                    "SELECT ops.record_integrated_source_context(42,'chosen',repeat('f"
                    "',64),ARRAY['#/texts/0'],'#/body','direct')"
                )
            ).scalar_one()
        )
    assert actual["selection"] == {
        "task_id": 42,
        "product_key": "chosen",
        "content_digest": "f" * 64,
    }
    assert actual["inputs"][0]["input_index"] == 2
    assert [row["occurrence_id"] for row in actual["occurrences"]] == ["o"]
    assert actual["occurrences"][0]["precision"] == "coarse"
    assert actual["occurrences"][0]["address_space"] == "selected_item"
    assert actual["relations"][0]["endpoints"][0]["target_content_digest"] == "f" * 64
    assert actual["relations"][0]["endpoints"][1]["target_task_id"] == 12
    assert [row["coverage_id"] for row in actual["coverage"]] == ["c"]
    assert actual["mapping_reports"][0]["report_index"] == 3


def test_shared_native_context_budget_refuses_instead_of_truncating(context_database):
    with context_database.connect() as conn, pytest.raises(DBAPIError, match="row budget"):
        PublishedPdfReader(conn, ProductReference(42, "chosen", "f" * 64)).source_context(
            ["#/texts/0"], "#/body", row_budget=3
        )


def test_shared_native_context_wrong_pin_refuses(context_database):
    with (
        context_database.connect() as conn,
        pytest.raises(NoResultFound, match=r"row was found|available|No row"),
    ):
        PublishedPdfReader(conn, ProductReference(42, "chosen", "e" * 64))


def test_nested_and_ancestor_coverage_and_page_ranges_keep_original_claims(context_database):
    claims = [
        ("nested", "#/groups/1:direct", "unknown"),
        ("ancestor", "#/body:descendants", "partial"),
        ("range", "pages:1-3", "unknown"),
        ("outside-range", "pages:2-4", "complete"),
        ("outside-section", "#/groups/9:descendants", "complete"),
    ]
    with context_database.begin() as conn:
        for identity, scope, outcome in claims:
            conn.execute(
                text(
                    "INSERT INTO kb.pdf_record_companion VALUES"
                    "('b','b','coverage',:identity,CAST(:body AS jsonb),10)"
                ),
                {
                    "identity": identity,
                    "body": json.dumps(
                        dict(coverage_id=identity, scope=scope, family="formula", outcome=outcome)
                    ),
                },
            )
        reader = PublishedPdfReader(conn, ProductReference(42, "chosen", "f" * 64))
        pointers = ["#/groups/0", "#/groups/1", "#/texts/0"]
        actual = reader.source_context(pointers, "#/groups/0", membership="descendants")
        paginated = list(reader.context_rows("coverage", pointers, "#/groups/0"))
        assert {row["local_id"]: row["body"] for row in paginated} == {
            row["coverage_id"]: row["body"] for row in actual["coverage"]
        }
        assert [row["local_id"] for row in paginated] == sorted(
            row["coverage_id"] for row in actual["coverage"]
        )
    assert {
        row["coverage_id"]: (row["body"]["scope"], row["body"]["outcome"])
        for row in actual["coverage"]
    } == {
        "c": ("page:1", "partial"),
        "nested": ("#/groups/1:direct", "unknown"),
        "ancestor": ("#/body:descendants", "partial"),
        "range": ("pages:1-3", "unknown"),
    }


def test_metadata_page_selector_filters_before_artifact_replay(context_database):
    from corpus_structure.semantic.pdf_payloads import PROFILE
    from corpus_structure.semantic.pdf_record_reader_native import pdf_record_reader_sql

    with context_database.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE ops.pdf_artifact_stream(product_id text,revision_id text,"
            "stream_id text,encoding_profile text)"
        )
        for number in (1, 2):
            conn.execute(
                text(
                    "INSERT INTO kb.pdf_record_companion VALUES"
                    "('b','b','native_metadata',:key,CAST(:body AS jsonb),:ordinal)"
                ),
                dict(
                    key=f"page-{number}",
                    body=json.dumps(
                        dict(
                            kind="inline_candidate_pages",
                            page_no=number,
                            payload_codec=PROFILE,
                        )
                    ),
                    ordinal=number,
                ),
            )
            conn.execute(
                text(
                    "INSERT INTO kb.pdf_record_companion_field VALUES"
                    "('b','b','native_metadata',:key,'value',:key,'y')"
                ),
                dict(key=f"page-{number}"),
            )
            conn.execute(
                text("INSERT INTO ops.pdf_artifact_stream VALUES('b','b',:key,:profile)"),
                dict(key=f"page-{number}", profile=PROFILE),
            )
        conn.exec_driver_sql(pdf_record_reader_sql(), execution_options={"no_parameters": True})
        reader = PublishedPdfReader(conn, ProductReference(42, "chosen", "f" * 64))
        rows = list(
            reader.iter_rows(
                "companion",
                {
                    "family": "native_metadata",
                    "kind": "inline_candidate_pages",
                    "page_nos": [2],
                },
                batch_size=1,
            )
        )
        assert [row["local_id"] for row in rows] == ["page-2"]
        assert rows[0]["_fields"] == [
            {
                "field_name": "value",
                "stream_id": "page-2",
                "scalar_kind": "y",
                "encoding_profile": PROFILE,
            }
        ]
