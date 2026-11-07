"""Independent controls for directed model definition attachment replay."""

import json
import struct
import sys
from pathlib import Path

from sqlalchemy import text


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
