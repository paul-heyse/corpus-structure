"""Independent ordered event expectations over nested native and companion values."""

import json

from sqlalchemy import Column, MetaData, Table, literal, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.pdf_record_event_queries import (
    native_event_query,
    native_event_relations,
)


def test_typed_native_events_preserve_nested_order_and_parts(infrastructure_rollback):
    conn = infrastructure_rollback
    conn.exec_driver_sql("CREATE SCHEMA ops; CREATE SCHEMA kb")
    models = {}
    for name in ("ops.pdf_record_document", "kb.pdf_record_native", "kb.pdf_record_membership"):
        source = metadata.tables[name]
        relation = Table(
            source.name,
            MetaData(),
            *(Column(col.name, col.type) for col in source.c),
            schema=source.schema,
        )
        conn.execute(CreateTable(relation))
        models[name] = relation
    conn.execute(
        models["ops.pdf_record_document"].insert(),
        dict(product_id="b", revision_id="b", root_id="root"),
    )
    records = [
        dict(
            record_id="root",
            native_type="GroupItem",
            scalars_json={"alpha": "β", "null": None},
            structure_json={
                "fields": {
                    "array": {"kind": "array", "length": 2},
                    "child": {"kind": "object", "target": "child"},
                    "map": {"kind": "map", "length": 1},
                }
            },
        ),
        dict(
            record_id="child",
            native_type="TextItem",
            scalars_json={"x": 1},
            structure_json={"fields": {}},
        ),
        dict(
            record_id="foreign",
            native_type="TextItem",
            scalars_json={"bad": True},
            structure_json={"fields": {}},
        ),
    ]
    for record in records:
        conn.execute(
            models["kb.pdf_record_native"].insert(),
            record
            | dict(
                product_id="b", revision_id="other" if record["record_id"] == "foreign" else "b"
            ),
        )
    for field, ordinal, value in (("array", 0, True), ("array", 1, None), ("map", 0, "value")):
        conn.execute(
            models["kb.pdf_record_membership"].insert(),
            dict(
                product_id="b",
                revision_id="b",
                parent_id="root",
                field_name=field,
                ordinal=ordinal,
                value_kind="scalar",
                scalar_json=value,
                member_key="quoted" if field == "map" else None,
            ),
        )
    published = select(literal("b").label("build_id")).cte("published")
    query = native_event_query(native_event_relations(metadata, published))
    events = conn.execute(query).scalars().all()
    encoded = "".join(
        event["value"]
        if event["kind"] == "literal"
        else json.dumps(event["value"], ensure_ascii=False)
        for event in events
    )
    assert (
        encoded
        == '{"alpha":"β","array":[true,null],"child":{"x":1},"map":{"quoted":"value"},"null":null}'
    )
    assert all(event["kind"] in {"literal", "inline"} for event in events)
    empty = select(literal("absent").label("build_id")).cte("empty_published")
    assert conn.execute(native_event_query(native_event_relations(metadata, empty))).all() == []
    selected = native_event_relations(
        metadata,
        published,
        roots=lambda nodes: select(
            nodes.c.record_id.label("record_id"), array([9]).label("path")
        ).where(nodes.c.record_id == "child"),
        node_ids=select(literal("child")),
        prefix="selected_",
    )
    actual = conn.execute(native_event_query(selected)).scalars().all()
    assert actual == [
        {"kind": "literal", "value": "{", "prefix": ""},
        {"kind": "literal", "value": '"x":', "prefix": ""},
        {"kind": "inline", "value": 1, "prefix": ""},
        {"kind": "literal", "value": "}", "prefix": ""},
    ]


def test_typed_companion_events_preserve_field_and_part_scope(infrastructure_rollback):
    from corpus_structure.semantic.pdf_record_event_queries import (
        companion_event_query,
        companion_event_relation,
    )

    conn = infrastructure_rollback
    conn.exec_driver_sql("CREATE SCHEMA ops; CREATE SCHEMA kb")
    tables = {}
    for name in (
        "kb.pdf_record_companion",
        "kb.pdf_record_companion_field",
        "ops.pdf_artifact_stream",
    ):
        source = metadata.tables[name]
        relation = Table(
            source.name,
            MetaData(),
            *(Column(col.name, col.type) for col in source.c),
            schema=source.schema,
        )
        conn.execute(CreateTable(relation))
        tables[name] = relation
    from corpus_structure.semantic.pdf_record_model import record_upload_table

    source = record_upload_table("ops.pdf_stage_artifact_part", metadata)
    parts = Table(
        "event_parts",
        MetaData(),
        *(Column(col.name, col.type) for col in source.c),
        schema="ops",
    )
    conn.execute(CreateTable(parts))
    conn.exec_driver_sql("""
CREATE FUNCTION ops.pdf_artifact_parts(text,text,boolean,text[])
RETURNS SETOF ops.event_parts LANGUAGE sql AS $$
 SELECT * FROM ops.event_parts WHERE product_id=$1 AND revision_id=$2 AND stream_id=ANY($4)
$$
""")
    companions = tables["kb.pdf_record_companion"]
    fields = tables["kb.pdf_record_companion_field"]
    streams = tables["ops.pdf_artifact_stream"]
    for name, ordinal in (("second", 1), ("first", 0)):
        conn.execute(
            companions.insert(),
            dict(
                product_id="b",
                revision_id="b",
                family="occurrence",
                local_id=name,
                ordinal=ordinal,
                body={"pointer": "#/texts/0"},
            ),
        )
    conn.execute(
        fields.insert(),
        dict(
            product_id="b",
            revision_id="b",
            family="occurrence",
            local_id="first",
            field_name="text",
            stream_id="s",
            scalar_kind="s",
        ),
    )
    conn.execute(
        streams.insert(),
        dict(
            product_id="b",
            revision_id="b",
            stream_id="s",
            byte_length=2,
            byte_root="root",
            encoding_profile="scalar",
        ),
    )
    for ordinal, body, revision in ((1, b"b", "b"), (0, b"a", "b"), (0, b"x", "other")):
        conn.execute(
            parts.insert(),
            dict(
                product_id="b",
                revision_id=revision,
                stream_id="s",
                ordinal=ordinal,
                byte_offset=ordinal,
                byte_length=1,
                body=body,
            ),
        )
    chosen = select(companions).where(
        companions.c.product_id == "b", companions.c.revision_id == "b"
    )
    events = companion_event_relation(metadata, chosen.subquery("chosen"), prefix="selected_")
    actual = conn.execute(companion_event_query(events)).scalars().all()
    assert [event["kind"] for event in actual] == [
        "row",
        "field",
        "part",
        "part",
        "close",
        "row",
        "close",
    ]
    assert [event["part"]["ordinal"] for event in actual if event["kind"] == "part"] == [0, 1]
    assert [event["part"]["body"] for event in actual if event["kind"] == "part"] == [
        "\\x61",
        "\\x62",
    ]
    assert actual[1]["field"]["field_name"] == "text"
    assert actual[1]["field"]["scalar_kind"] == "s"
