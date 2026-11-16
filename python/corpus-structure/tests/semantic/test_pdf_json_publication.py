"""Current native PDF companion shapes and exact registered descriptor custody."""

from copy import deepcopy

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.native_objects import native_owner
from semantic.current_pdf_integration_support import current_integration_journey


def test_every_current_integrated_companion_is_closed_under_its_real_claim(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    refused = []

    def check(case, engine, claim, holder, draft, arguments, publish):
        if draft.kind != "integrated":
            return
        from hashlib import sha256

        from corpus_structure.semantic.identity import canonical_bytes
        from corpus_structure.semantic.pdf_staging import begin_pdf_build

        cases = []
        classes = {
            "input": "PdfProductInput",
            "occurrence": "PdfProductOccurrence",
            "relation": "PdfProductRelation",
            "mapping_report": "PdfMappingDisposition",
            "coverage": "PdfProductCoverage",
        }
        for family in classes:
            assert draft.companions[family], family
            body = deepcopy(draft.companions[family][0])
            body["unmodeled"] = True
            cases.append((family, family, body))
        body = deepcopy(draft.companions["relation"][0])
        body["endpoints"][-1]["role"] = "unmodeled"
        cases.append(("endpoint-role", "relation", body))
        body = deepcopy(draft.companions["input"][0])
        body["task_id"] = str(body["task_id"])
        cases.append(("input-type", "input", body))
        for label, family, body in cases:
            # Exercise the installed publisher's actual guard with this command's
            # real fence. Each invalid staged row rolls back independently; no
            # full alternate document or callback-wide transaction is retained.
            with engine.begin() as connection:
                with pytest.raises(DBAPIError) as error, connection.begin_nested():
                    build = begin_pdf_build(
                        connection,
                        task_id=claim.task_id,
                        attempt=claim.attempt,
                        holder=holder,
                        source_digest=sha256(draft.original).hexdigest(),
                        recipe_digest=sha256(draft.recipe_bytes).hexdigest(),
                        schema_digest=sha256(draft.schema_bytes).hexdigest(),
                        replay_key="closed-shape-probe:" + label,
                    )
                    local = str(
                        body.get(
                            {
                                "occurrence": "occurrence_id",
                                "relation": "relation_id",
                                "coverage": "coverage_id",
                            }.get(family, ""),
                            0,
                        )
                    )
                    connection.execute(
                        text(
                            "SELECT ops.adopt_pdf_companion(:build,:task,:attempt,:holder,:family,:local,"
                            "CAST(:body AS jsonb),:key,0,'{}'::jsonb)"
                        ),
                        dict(
                            build=build.build_id,
                            task=claim.task_id,
                            attempt=claim.attempt,
                            holder=holder,
                            family=family,
                            local=local,
                            body=canonical_bytes(body).decode(),
                            key="negative:" + label,
                        ),
                    )
                assert isinstance(error.value.orig, psycopg.Error)
                assert (error.value.orig.sqlstate, error.value.orig.diag.message_primary) == (
                    "23514",
                    "parsing record shape differs: " + classes[family],
                )
            refused.append(label)

    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings, before_draft=check
    ) as case:
        assert len(refused) == 7
        with case.reader().connect() as connection:
            with pytest.raises(DBAPIError) as error, connection.begin_nested():
                connection.scalar(text("SELECT count(*) FROM ops.pdf_stage_build"))
            assert isinstance(error.value.orig, psycopg.Error)
            assert error.value.orig.sqlstate == "42501"
        with case.clone.admin.connect() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM ops.pdf_stage_build WHERE task_id=:task AND replay_key LIKE 'closed-shape-probe:%'"
                    ),
                    {"task": case.publications["integrated"].task_id},
                )
                == 0
            )


def test_descriptor_helper_is_part_of_exact_current_native_catalog(commit_db_engine):
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        verify_deployment_catalog,
    )
    from corpus_structure.semantic.migrations import current_revision

    with commit_db_engine.begin() as connection:
        revision = current_revision(connection)
        verify_deployment_catalog(connection, revision=revision)
        with connection.begin_nested() as drift:
            with native_owner(connection, "corpus_sem_publisher"):
                connection.exec_driver_sql("""
                  CREATE OR REPLACE FUNCTION ops.pdf_product_descriptor(p_payload bytea) RETURNS jsonb
                  LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp
                  AS $$ SELECT '{}'::jsonb $$
                """)
            with pytest.raises(ExecutionAdmissionError, match=r"ops\.pdf_product_descriptor"):
                verify_deployment_catalog(connection, revision=revision)
            drift.rollback()
        verify_deployment_catalog(connection, revision=revision)


@pytest.mark.prerequisite("task86_witness")
def test_retained_book_witness_descriptor_and_content_fit_without_relation_jsonb(commit_db_engine):
    import gzip
    import json
    import os
    from hashlib import sha256
    from pathlib import Path

    witness = Path(
        os.environ.get(
            "CORPUS_PDF_REPLAY_PAYLOAD",
            str(
                Path(__file__).resolve().parents[4]
                / "docs/design_review/evidence"
                / "2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-prepared.json.gz"
            ),
        )
    )
    payload = gzip.decompress(witness.read_bytes())
    assert len(payload) == 558190320
    assert (
        sha256(payload).hexdigest()
        == "c8f19ca1703206e9007b416eecb7c0d286de57d7ce82b006a605335efe7da524"
    )
    value = json.loads(payload)
    assert len(value["relations"]) == 270447
    expected = {
        key: child
        for key, child in value.items()
        if key
        not in {"content", "inputs", "occurrences", "relations", "coverage", "mapping_reports"}
    }
    expected["content_metadata"] = {
        key: value["content"][key] for key in ("schema_digest", "recipe_digest", "health")
    }
    del value
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        # This is a read-only witness check, not publication into fabricated input
        # custody. The coordinator runs the actual protected book producer.
        row = (
            conn.execute(
                text("""
          WITH content AS MATERIALIZED (
            SELECT (convert_from(:payload,'UTF8')::json->'content')::jsonb value
          ) SELECT ops.pdf_product_descriptor(:payload) descriptor,
                   pg_column_size(value) content_bytes,
                   jsonb_array_length(value->'document'->'texts') text_count
            FROM content
        """),
                {"payload": payload},
            )
            .mappings()
            .one()
        )
    assert row["descriptor"] == expected
    assert row["content_bytes"] == 137752426
    assert row["text_count"] == 183280
