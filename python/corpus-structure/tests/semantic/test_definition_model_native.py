"""Independent controls for directed model definition attachment replay."""

import json
import struct
import sys
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text


def test_located_request_binds_ordered_schema_and_exact_inference(semantic_db_engine):
    policy = {
        "request_version": "located-model-request-1",
        "definition": {"bare": ['{"entities":[', {"field": "term_entity"}, "]}"]},
        "inference": {"operation": "batch_extract", "include_spans": True},
    }
    profile = {
        "snapshot": "/acquired",
        "checkpoint": "checkpoint",
        "timeout_seconds": 120.0,
        "artifact_hashes": [["z", "last"], ["a", "first"]],
    }
    config = {
        "profile": profile,
        "description_arm": "bare",
        "term_entity": '\u03b1 "term"',
        "threshold": 0.5,
        "evaluation_overlap": "nested",
    }
    expected = [
        "located-model-request-1",
        "r",
        "native-local-v1",
        '{"entities":["\u03b1 \\"term\\""]}',
        {
            "checkpoint": "checkpoint",
            "timeout_seconds": "120",
            "artifact_hashes": [["a", "first"], ["z", "last"]],
        },
        [["structure.definition_components/9", "context", "digest", " \u03b1\t\u03b2"]],
        "0.5",
        "nested",
        True,
        {"operation": "batch_extract", "include_spans": True},
    ]
    expected_key = sha256(
        json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    sql = (
        Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/structural_products.sql"
    ).read_text()
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})
        query = text(
            "SELECT ops.located_model_request('r','structure.definition_components/9',"
            "CAST(:policy AS jsonb),CAST(:config AS jsonb),'context','digest',:body)"
        )
        params = {
            "policy": json.dumps(policy),
            "config": json.dumps(config),
            "body": " \u03b1\t\u03b2",
        }
        assert conn.scalar(query, params) == expected_key
        assert (
            conn.scalar(
                query,
                {
                    **params,
                    "config": json.dumps(
                        {
                            **config,
                            "evaluation_overlap": "allow",
                        }
                    ),
                },
            )
            != expected_key
        )


def test_native_model_report_preserves_exact_binary_profile_and_scores(semantic_db_engine):
    sql = (
        Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/record_publication.sql"
    ).read_text()
    cutoff = sql.index("CREATE OR REPLACE FUNCTION data.record_source_json")
    values = (
        120.0,
        0.1,
        -0.0,
        float.fromhex("0x0.0000000000001p-1022"),
        float.fromhex("0x0.fffffffffffffp-1022"),
        sys.float_info.min,
        sys.float_info.max,
    )
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql[:cutoff], execution_options={"no_parameters": True})
        for value in values:
            actual = conn.scalar(
                text("SELECT float8send(data.record_source_float(CAST(:value AS jsonb)))"),
                {"value": json.dumps({"kind": "float", "hexadecimal": value.hex()})},
            )
            assert actual == struct.pack("!d", value)


def test_native_model_components_need_directed_provider_attachment(semantic_db_engine):
    passage = {
        "passage_id": "p",
        "text": "term means content",
        "start": 0,
        "end": 18,
        "scope": "s",
    }
    term = {"start": 0, "end": 4, "text": "term"}
    content = {"start": 11, "end": 18, "text": "content"}
    raw = {
        "entities": {
            "term": [
                {**term, "interpretation": "definition"},
                {**term, "interpretation": {"label": "explanation"}},
                {**term, "interpretation": "unsupported"},
            ],
            "content": [content],
        },
        "relation_extraction": {"attachment": [{"head": term, "tail": content}] * 2},
    }
    config = {
        "description_arm": "bare",
        "use_model": True,
        "profile": {"timeout_seconds": "120"},
        "target_ids": ["p"],
        "term_entity": "term",
        "content_entity": "content",
        "attachment_relation": "attachment",
    }
    entry = {
        "passage_id": "p",
        "window_start": 0,
        "window_end": 18,
        "computation": "provider",
        "profile": "profile",
        "pack": "pack",
        "context_id": "definition-target:context",
        "context_digest": "context",
        "preparation": {"synthetic_suffix": ".", "consumed_text": "term means content."},
        "raw_json": json.dumps(raw),
    }
    detail = {
        "version": "located-definition-extraction-3",
        "description_arm": "bare",
        "overlap_policy": "flat",
        "profile": {"timeout_seconds": 120.0},
        "profile_fingerprint": "profile",
        "pack_fingerprint": "pack",
        "raw_reports": [entry],
    }
    sql = (
        Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/structural_products.sql"
    ).read_text()
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})

        def replay():
            return conn.execute(
                text("""
                    WITH inputs AS (
                        SELECT CAST(:detail AS jsonb) AS d, CAST(:config AS jsonb) AS c,
                               CAST(:passages AS jsonb) AS p
                    )
                    SELECT roles, ops.definition_model_components(d,c,p,roles)
                    FROM inputs CROSS JOIN LATERAL (
                        SELECT ops.definition_role_candidates(d,c,p) AS roles
                    ) exact
                """),
                {
                    "detail": json.dumps(detail),
                    "config": json.dumps(config),
                    "passages": json.dumps({"p": passage}),
                },
            ).one()

        roles, (component,) = replay()
        assert len(roles) == 4
        assert component["term"] == {**term, "passage_id": "p"}
        assert component["content"] == {**content, "passage_id": "p"}
        assert component["interpretation"] == "explanation"
        assert component["basis"] == "model_reading"
        raw["relation_extraction"]["attachment"] = [{"head": content, "tail": term}]
        entry["raw_json"] = json.dumps(raw)
        assert replay() == (roles, [])


def test_genuine_definition_spans_require_named_cue_custody(semantic_db_engine):
    import pytest
    from sqlalchemy.exc import DBAPIError

    term = dict(passage_id="p", start=0, end=4, text="term")
    content = dict(passage_id="p", start=11, end=18, text="content")
    named = dict(term=term, content=content, basis="matched_cue", interpretation="definition")
    weak = {**named, "basis": "unqualified", "interpretation": "unresolved"}
    sql = (
        Path(__file__).parents[2] / "src/corpus_structure/semantic/sql/structural_products.sql"
    ).read_text()
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(sql, execution_options={"no_parameters": True})
        check = text("""
            SELECT ops.validate_definition_basis(
              CAST(:component AS jsonb),
              jsonb_build_object('passage_id','p','text','term means content','start',0,'end',18),
              '{}', jsonb_build_object('use_named_candidates',true), '{}')
            """)
        with (
            pytest.raises(DBAPIError, match="exact retained annotation witness"),
            conn.begin_nested(),
        ):
            conn.execute(check, {"component": json.dumps(named)})
        conn.execute(check, {"component": json.dumps(weak)})
        with pytest.raises(DBAPIError, match="unsupported interpretation"), conn.begin_nested():
            conn.execute(check, {"component": json.dumps({**weak, "interpretation": "definition"})})
