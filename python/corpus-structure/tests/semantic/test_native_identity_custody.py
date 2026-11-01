"""Actual native exclusion evidence retains located custody without synthetic spans."""

import json

from sqlalchemy import text

from .test_identity_exclusions import exclusion_result


def test_native_exclusion_primary_and_supporting_custody_use_exact_projection(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    exclusion_result(semantic_db_engine, semantic_writer_engine, tmp_path, citations=2)
    with semantic_writer_engine.connect() as conn:
        evidence = (
            conn.execute(
                text("""
          SELECT es.span_id,es.rendition_id,es.source_view_id,es.native_address,
                 ev.locator,v.projection->>'text' source_text,v.projection_digest,
                 v.native_content_digest
          FROM data.identity_exclusion_evidence xe
          JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
          JOIN data.evidence ev USING(release_id,realization_id,evidence_id)
          JOIN kb.source_view v ON v.id=es.source_view_id
          ORDER BY ev.locator
        """)
            )
            .mappings()
            .all()
        )
        assert len(evidence) == 2
        assert conn.scalar(text("SELECT count(*) FROM kb.span")) == 0
        roles = set()
        for row in evidence:
            assert row["span_id"] is None and row["rendition_id"] is None
            address = json.loads(row["native_address"][4:])
            citation = json.loads(row["locator"])
            roles.add(citation["role"])
            quote = "Alice is here." if citation["role"] == "primary" else "Alice"
            start = row["source_text"].index(quote)
            assert (address["start"], address["end"]) == (start, start + len(quote))
            assert (citation["start"], citation["end"]) == (start, start + len(quote))
            assert address["source_view_id"] == row["source_view_id"]
            assert address["projection_digest"] == row["projection_digest"]
            assert address["product_digest"] == row["native_content_digest"]
        assert roles == {"primary", "supporting"}
