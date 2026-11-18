"""Generated read programs on controlled PostgreSQL relations, always rolled back."""

import pytest
from sqlalchemy import Column, MetaData, Table, bindparam, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.pdf_companion_read_native import (
    pdf_companion_field_read_sql,
    pdf_native_record_shape_sql,
)


@pytest.fixture
def generated_companion_reads(infrastructure_rollback):
    connection = infrastructure_rollback
    transaction = connection.begin_nested()
    try:
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS ops")
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS kb")
        controls = MetaData()
        for name in (
            "kb.pdf_record_companion_field",
            "kb.pdf_record_companion",
            "ops.pdf_published_revision",
        ):
            owner = get_metadata().tables[name]
            Table(
                owner.name,
                controls,
                *(Column(c.name, c.type) for c in owner.columns),
                schema=owner.schema,
            )
        controls.create_all(connection)
        connection.exec_driver_sql("""
            CREATE TEMP TABLE controlled_parts(product_id text,revision_id text,
              stream_id text,stage boolean,ordinal bigint,body bytea);
            CREATE FUNCTION ops.pdf_artifact_parts(p_product text,p_revision text,
              p_stage boolean,p_streams text[]) RETURNS TABLE(stream_id text,ordinal bigint,body bytea)
            LANGUAGE sql STABLE AS $control$
              SELECT stream_id,ordinal,body FROM pg_temp.controlled_parts
              WHERE product_id=p_product AND revision_id=p_revision AND stage=p_stage
                AND (p_streams IS NULL OR stream_id=ANY(p_streams))
            $control$;
        """)
        execute_native_sql(connection, pdf_native_record_shape_sql())
        execute_native_sql(connection, pdf_companion_field_read_sql(get_metadata()))
        yield connection
    finally:
        transaction.rollback()


def test_shape_predicates_preserve_unknown_required_scalar_and_native_float_rules(
    generated_companion_reads,
):
    connection = generated_companion_reads
    assert connection.execute(
        text("""
        SELECT proname,provolatile,prosecdef,proisstrict,pronargdefaults
        FROM pg_proc WHERE pronamespace='ops'::regnamespace
          AND proname IN ('pdf_native_record_shape','pdf_companion_field_bytes',
            'pdf_companion_restore_fields','pdf_companion_body') ORDER BY proname
    """)
    ).all() == [
        ("pdf_companion_body", "s", True, False, 0),
        ("pdf_companion_field_bytes", "s", False, False, 1),
        ("pdf_companion_restore_fields", "s", False, False, 0),
        ("pdf_native_record_shape", "i", False, False, 0),
    ]
    assert (
        connection.scalar(
            text(
                "SELECT has_function_privilege('corpus_sem_reader', 'ops.pdf_companion_body(text,text,text,text,jsonb)', 'EXECUTE')"
            )
        )
        is True
    )
    assert (
        connection.scalar(
            text(
                "SELECT has_function_privilege('corpus_sem_reader', 'ops.pdf_companion_field_bytes(text,text,text,boolean)', 'EXECUTE')"
            )
        )
        is False
    )

    def shape(kind, scalars, fields):
        return connection.scalar(
            select(
                func.ops.pdf_native_record_shape(
                    kind,
                    bindparam("scalars", scalars, type_=JSONB),
                    bindparam("fields", fields, type_=JSONB),
                )
            )
        )

    assert shape("not-a-native-type", {}, {}) is False
    assert shape(None, {}, {}) is False
    assert shape("NativeArray", {}, {"items": []}) is True
    assert shape("NativeArray", {"unexpected": 1}, {"items": []}) is False
    assert shape("NativeArray", {}, {}) is False
    assert shape("Size", {"width": 12, "height": 24.5}, {}) is True
    assert shape("Size", {"width": {"native_float64": "3ff0000000000000"}, "height": 1}, {}) is True
    assert shape("Size", {"width": {"native_float64": "BAD"}, "height": 1}, {}) is False
    assert shape("Size", {"width": "12", "height": 1}, {}) is False
    # Size has model defaults; BoundingBox and PageItem carry required members.
    assert shape("Size", {"width": 12}, {}) is True
    assert shape("BoundingBox", {"l": 0, "t": 1, "r": 2}, {}) is False
    assert shape("PageItem", {"page_no": 2}, {"size": {}}) is True
    assert shape("PageItem", {"page_no": 2.5}, {"size": {}}) is False
    assert shape("PageItem", {"page_no": "2"}, {"size": {}}) is False
    assert shape("Size", {"width": 12, "height": 1, "foreign": 1}, {}) is False


def test_companion_reads_keep_exact_bytes_scope_json_null_and_published_guards(
    generated_companion_reads,
):
    connection = generated_companion_reads
    parts = [
        ("product", "product", "text", False, 1, b"\x00tail"),
        ("product", "product", "text", False, 0, "aβ".encode()),
        ("other", "product", "text", False, 0, b"wrong-product"),
        ("product", "other", "text", False, 0, b"wrong-revision"),
        ("product", "product", "other", False, 0, b"wrong-stream"),
        ("product", "product", "text", True, 0, b"stage"),
        ("product", "product", "json", False, 0, b'{"number":2,"value":null}'),
        ("product", "product", "string", False, 0, "aβ".encode()),
    ]
    connection.execute(
        text("INSERT INTO pg_temp.controlled_parts VALUES(:p,:r,:s,:stage,:o,:b)"),
        [dict(zip(("p", "r", "s", "stage", "o", "b"), row, strict=True)) for row in parts],
    )
    assert (
        connection.scalar(select(func.ops.pdf_companion_field_bytes("product", "product", "text")))
        == "aβ".encode() + b"\x00tail"
    )
    assert (
        connection.scalar(
            select(func.ops.pdf_companion_field_bytes("product", "product", "text", True))
        )
        == b"stage"
    )
    assert (
        connection.scalar(
            select(func.ops.pdf_companion_field_bytes("product", "product", "missing"))
        )
        == b""
    )
    fields = get_metadata().tables["kb.pdf_record_companion_field"]
    connection.execute(
        fields.insert(),
        [
            dict(
                product_id="product",
                revision_id="product",
                family="relation",
                local_id="one",
                field_name="evidence",
                scalar_kind="s",
                stream_id="string",
            ),
            dict(
                product_id="product",
                revision_id="product",
                family="relation",
                local_id="one",
                field_name="endpoints",
                scalar_kind="y",
                stream_id="json",
            ),
            dict(
                product_id="product",
                revision_id="other",
                family="relation",
                local_id="one",
                field_name="foreign",
                scalar_kind="s",
                stream_id="string",
            ),
            dict(
                product_id="product",
                revision_id="product",
                family="relation",
                local_id="other",
                field_name="foreign",
                scalar_kind="s",
                stream_id="string",
            ),
        ],
    )

    def read(name, body, *, family="relation", local="one", revision="product"):
        return connection.scalar(
            select(
                getattr(func.ops, name)(
                    "product",
                    revision,
                    family,
                    local,
                    bindparam("body", body, type_=JSONB),
                )
            )
        )

    expected = {"id": "one", "evidence": "aβ", "endpoints": {"number": 2, "value": None}}
    assert read("pdf_companion_restore_fields", {"id": "one"}) == expected
    assert read("pdf_companion_restore_fields", None, local="absent") is None
    with pytest.raises(DBAPIError, match="both inline and byte-owned"), connection.begin_nested():
        read("pdf_companion_restore_fields", {"evidence": None})
    with pytest.raises(DBAPIError, match="not in a published revision"), connection.begin_nested():
        read("pdf_companion_body", {"id": "one"})
    connection.execute(
        get_metadata().tables["ops.pdf_published_revision"].insert(), {"build_id": "product"}
    )
    connection.execute(
        get_metadata().tables["kb.pdf_record_companion"].insert(),
        [
            dict(
                product_id="product",
                revision_id="product",
                family="relation",
                local_id="one",
                body={"id": "one"},
            ),
            dict(
                product_id="product",
                revision_id="product",
                family="native_metadata",
                local_id="recognition",
                body={"kind": "recognition_coverage"},
            ),
            dict(
                product_id="product",
                revision_id="product",
                family="native_metadata",
                local_id="opaque",
                body={"kind": "inline_candidate_pages"},
            ),
            dict(
                product_id="product",
                revision_id="product",
                family="native_metadata",
                local_id="missing-kind",
                body={},
            ),
        ],
    )
    assert read("pdf_companion_body", {"id": "one"}) == expected
    assert read(
        "pdf_companion_body",
        {"kind": "recognition_coverage"},
        family="native_metadata",
        local="recognition",
    ) == {"kind": "recognition_coverage"}
    assert read("pdf_companion_body", {}, family="native_metadata", local="missing-kind") == {}
    with pytest.raises(DBAPIError, match="lossless byte reader"), connection.begin_nested():
        read(
            "pdf_companion_body",
            {"kind": "inline_candidate_pages"},
            family="native_metadata",
            local="opaque",
        )
    with pytest.raises(DBAPIError, match="not in a published revision"), connection.begin_nested():
        read("pdf_companion_body", {"id": "one"}, revision="other")
