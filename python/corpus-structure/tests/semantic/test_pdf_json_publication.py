"""Independent protected checks for the bounded JSON-text publication realization."""

from copy import deepcopy
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes

from . import pdf_integration_support as fixtures

native_source = fixtures.native_source
pdf13_db = fixtures.pdf13_db


def test_json_envelope_and_every_decomposed_record_remain_closed_and_typed(pdf13_db):
    db = pdf13_db
    value = fixtures.integrated(db.source, db.inputs)
    value["mapping_reports"] = [{"input_index": 1, "occurrence_id": "block-0", "outcome": "mapped"}]
    product = fixtures.prepare(value, db.source)
    # The removed aggregate document writer no longer accepts collection/envelope
    # arguments. Their closed preparation boundary remains independently assessed.
    envelope_cases = []
    record_cases = []
    for collection in ("inputs", "occurrences", "relations", "coverage", "mapping_reports"):
        invalid = deepcopy(value)
        invalid[collection][-1]["unmodeled"] = True
        record_cases.append(invalid)
        invalid = deepcopy(value)
        invalid[collection] = None
        envelope_cases.append(invalid)
    for change in ("unknown", "missing", "null", "empty_coverage", "nested_enum", "nested_type"):
        invalid = deepcopy(value)
        if change == "unknown":
            invalid["unmodeled"] = []
        elif change == "missing":
            del invalid["health"]
        elif change == "null":
            invalid["health"] = None
        elif change == "empty_coverage":
            invalid["coverage"] = []
        elif change == "nested_enum":
            invalid["relations"][-1]["endpoints"][-1]["role"] = "unmodeled"
            record_cases.append(invalid)
        else:
            invalid["inputs"][-1]["task_id"] = str(invalid["inputs"][-1]["task_id"])
            record_cases.append(invalid)
        envelope_cases.append(invalid)
    for invalid in envelope_cases:
        with pytest.raises(ValueError):
            fixtures.prepare(invalid, db.source)
    for index, invalid in enumerate(record_cases):
        invalid["product_key"] = f"invalid-json-{index}"
        with pytest.raises(DBAPIError):
            fixtures._publish_record_values(db, invalid)
    digest = fixtures.publish(db, product)
    assert fixtures.publish(db, product) == digest
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.product_reference import ProductReference

    with db.writer.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.pdf_product WHERE product_key LIKE 'invalid-json-%'")
            )
            == 0
        )
        reader = published_record_reader(conn, ProductReference(db.job.task, "selected", digest))
        assert reader is not None
        descriptor = reader.product_descriptor()
    assert descriptor["version"] == 2 and descriptor["kind"] == "integrated"
    assert descriptor["health"] == value["health"]
    assert descriptor["revision"]["logical_digest"] == digest
    assert descriptor["revision"]["schema_digest"] == value["content"]["schema_digest"]
    assert descriptor["revision"]["recipe_digest"] == value["content"]["recipe_digest"]
    assert descriptor["revision"]["release_id"] == db.prepared.release_id
    assert (
        not {"content", "inputs", "occurrences", "relations", "coverage", "mapping_reports"}
        & descriptor.keys()
    )


def test_decomposed_cardinality_is_derived_from_effective_model(pdf13_db):
    from corpus_structure.semantic.native_shapes import decomposed_record_guards
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task

    db = pdf13_db
    value = fixtures.integrated(db.source, db.inputs)
    with db.writer.connect() as conn:
        boundary = pdf_context_for_task(conn, db.job.task).boundary
    definitions = tuple(
        replace(
            definition,
            properties=tuple(
                replace(prop, minimum_cardinality=1, maximum_cardinality=1)
                if prop.name == "coverage"
                else prop
                for prop in definition.properties
            ),
        )
        if definition.name == "PdfIntegratedProduct"
        else definition
        for definition in boundary.definitions
    )
    boundary = replace(boundary, definitions=definitions)
    collections = {
        "inputs": ("input_rows", "input"),
        "occurrences": ("occurrence_rows", "occurrence"),
        "relations": ("relation_rows", "relation"),
        "coverage": ("coverage_rows", "coverage"),
        "mapping_reports": ("mapping_rows", "mapping_report"),
    }
    plan = decomposed_record_guards(
        boundary,
        "PdfIntegratedProduct",
        "product",
        field_names="envelope_fields",
        collections=collections,
        records={"content": "parsing_item"},
    )
    compact = {k: v for k, v in value.items() if k not in {"content", *collections}}
    content = dict(value["content"])
    content["document_json"] = canonical_bytes(content.pop("document")).decode()

    def literal(item):
        return "'" + canonical_bytes(item).decode().replace("'", "''") + "'"

    for count in (0, 1, 2):
        declarations = [
            "product jsonb:=" + literal(compact) + "::jsonb",
            "parsing_item jsonb:=" + literal(content) + "::jsonb",
            "envelope_fields text[]:=ARRAY[" + ",".join("'" + k + "'" for k in value) + "]",
        ]
        for name, (variable, _) in collections.items():
            rows = value.get(name, [])
            if name == "coverage":
                rows = rows * count
            declarations.append(variable + " json:=" + literal(rows) + "::json")
        sql = (
            "DO $shape$ DECLARE "
            + ";".join(declarations)
            + "; BEGIN "
            + plan.envelope
            + " END $shape$"
        )
        if count == 1:
            with db.admin.begin() as conn:
                conn.exec_driver_sql(sql)
        else:
            with (
                db.admin.begin() as conn,
                pytest.raises(DBAPIError, match="record shape differs"),
                conn.begin_nested(),
            ):
                conn.exec_driver_sql(sql)


def test_descriptor_helper_is_part_of_exact_native_admission(pdf13_db):
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        admit_execution_release,
    )

    db = pdf13_db
    with db.admin.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.exec_driver_sql("""
          CREATE OR REPLACE FUNCTION ops.pdf_product_descriptor(p_payload bytea) RETURNS jsonb
          LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp
          AS $$ SELECT '{}'::jsonb $$
        """)
    with (
        db.admin.begin() as conn,
        pytest.raises(ExecutionAdmissionError, match=r"ops\.pdf_product_descriptor"),
    ):
        admit_execution_release(db.prepared, connection=conn)


def test_retained_book_witness_descriptor_and_content_fit_without_relation_jsonb(pdf13_db):
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
    if not witness.is_file():
        pytest.skip("retained task86 canonical-byte witness is not available")
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
    with pdf13_db.admin.begin() as conn:
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
