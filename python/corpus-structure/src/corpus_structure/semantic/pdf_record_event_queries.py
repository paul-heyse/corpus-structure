"""Typed event relations shared by complete and selected PDF record exports."""

from dataclasses import dataclass

from sqlalchemy import (
    BigInteger,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, array
from sqlalchemy.sql.selectable import CTE


@dataclass(frozen=True)
class NativeEventRelations:
    nodes: CTE
    members: CTE
    fields: CTE
    walk: CTE
    events: CTE


def native_event_relations(model, published, *, roots=None, node_ids=None, prefix=""):
    """Build ordered containment events before any PostgreSQL serialization."""
    native = model.tables["kb.pdf_record_native"]
    membership = model.tables["kb.pdf_record_membership"]
    header = model.tables["ops.pdf_record_document"]

    def placed(relation):
        return and_(
            relation.c.product_id == published.c.build_id,
            relation.c.revision_id == published.c.build_id,
        )

    node_query = select(native).join(published, placed(native))
    if node_ids is not None:
        node_query = node_query.where(native.c.record_id.in_(node_ids))
    nodes = node_query.cte(prefix + "nodes").prefix_with("MATERIALIZED")
    member_query = select(membership).join(published, placed(membership))
    if node_ids is not None:
        member_query = member_query.where(membership.c.parent_id.in_(select(nodes.c.record_id)))
    members = member_query.cte(prefix + "members").prefix_with("MATERIALIZED")
    scalar_fields = (
        func.jsonb_each(nodes.c.scalars_json)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .lateral(prefix + "scalar_field")
    )
    object_fields = (
        func.jsonb_each(nodes.c.structure_json["fields"])
        .table_valued(column("key", Text()), column("value", JSONB()))
        .lateral(prefix + "object_field")
    )
    field_rows = union_all(
        select(
            nodes.c.record_id,
            scalar_fields.c.key.label("name"),
            scalar_fields.c.value,
            literal("scalar").label("kind"),
        ).select_from(nodes.join(scalar_fields, true())),
        select(
            nodes.c.record_id,
            object_fields.c.key,
            object_fields.c.value,
            object_fields.c.value["kind"].astext,
        ).select_from(nodes.join(object_fields, true())),
    ).subquery(prefix + "field_rows")
    fields = (
        select(
            *field_rows.c,
            (
                func.row_number().over(
                    partition_by=field_rows.c.record_id, order_by=field_rows.c.name.collate("C")
                )
                - 1
            ).label("slot"),
        )
        .cte(prefix + "fields")
        .prefix_with("MATERIALIZED")
    )

    def path(*values):
        return array(values, type_=BigInteger())

    edges = (
        union_all(
            select(
                fields.c.record_id.label("parent_id"),
                fields.c.value["target"].astext.label("child_id"),
                path(1, fields.c.slot, 1).label("suffix"),
            ).where(fields.c.kind == "object"),
            select(
                members.c.parent_id,
                members.c.record_id,
                path(1, fields.c.slot, 1, 1, members.c.ordinal, 1),
            )
            .select_from(
                members.join(
                    fields,
                    and_(
                        fields.c.record_id == members.c.parent_id,
                        fields.c.name == members.c.field_name,
                    ),
                )
            )
            .where(members.c.value_kind == "record"),
        )
        .cte(prefix + "edges")
        .prefix_with("MATERIALIZED")
    )
    seed = (
        select(header.c.root_id.label("record_id"), path().label("path")).join(
            published, placed(header)
        )
        if roots is None
        else roots(nodes)
    )
    seed = seed.subquery(prefix + "roots")
    walk = select(seed.c.record_id, cast(seed.c.path, ARRAY(BigInteger())).label("path")).cte(
        prefix + "walk", recursive=True
    )
    walk = walk.union_all(
        select(edges.c.child_id, walk.c.path.concat(edges.c.suffix)).select_from(
            walk.join(edges, edges.c.parent_id == walk.c.record_id)
        )
    )
    with_nodes = walk.join(nodes, nodes.c.record_id == walk.c.record_id)
    with_fields = with_nodes.join(fields, fields.c.record_id == walk.c.record_id)
    with_members = walk.join(fields, fields.c.record_id == walk.c.record_id).join(
        members,
        and_(members.c.parent_id == fields.c.record_id, members.c.field_name == fields.c.name),
    )

    def json(value):
        return func.to_jsonb(value, type_=JSONB())

    def event(suffix, kind, value, prefix_value, source):
        return select(
            walk.c.path.concat(suffix).label("path"),
            kind.label("kind"),
            value.label("value"),
            prefix_value.label("prefix"),
        ).select_from(source)

    empty = literal("")
    comma = case((members.c.ordinal > 0, ","), else_="")
    field_comma = case((fields.c.slot > 0, ","), else_="")
    map_key_parts = and_(fields.c.kind == "map", members.c.member_key.is_(None))
    field_count = (
        select(func.count())
        .select_from(fields)
        .where(fields.c.record_id == nodes.c.record_id)
        .correlate(nodes)
        .scalar_subquery()
    )
    events = union_all(
        event(
            path(0),
            literal("literal"),
            json(case((nodes.c.native_type == "NativeArray", ""), else_="{")),
            empty,
            with_nodes,
        ),
        event(
            path(1, fields.c.slot, 0),
            literal("literal"),
            json(
                case(
                    (nodes.c.native_type == "NativeArray", ""),
                    else_=field_comma + cast(json(fields.c.name), Text()) + ":",
                )
            ),
            empty,
            with_fields,
        ),
        event(
            path(1, fields.c.slot, 1),
            case((fields.c.kind == "scalar", "inline"), else_="parts"),
            case(
                (fields.c.kind == "scalar", fields.c.value),
                else_=json(fields.c.value["stream_id"].astext),
            ),
            empty,
            walk.join(fields, fields.c.record_id == walk.c.record_id),
        ).where(fields.c.kind.in_(("scalar", "parts"))),
        event(
            path(1, fields.c.slot, 1, 0),
            literal("literal"),
            json(case((fields.c.kind == "map", "{"), else_="[")),
            empty,
            walk.join(fields, fields.c.record_id == walk.c.record_id),
        ).where(fields.c.kind.in_(("array", "map"))),
        event(
            path(1, fields.c.slot, 1, 1, members.c.ordinal, 0),
            case((map_key_parts, "key_parts"), else_="literal"),
            case(
                (map_key_parts, json(members.c.member_key_stream_id)),
                else_=json(
                    comma
                    + case(
                        (fields.c.kind == "map", cast(json(members.c.member_key), Text()) + ":"),
                        else_="",
                    )
                ),
            ),
            comma,
            with_members,
        ).where(fields.c.kind.in_(("array", "map"))),
        event(
            path(1, fields.c.slot, 1, 1, members.c.ordinal, 1),
            case((members.c.value_kind == "scalar", "inline"), else_="parts"),
            case(
                (members.c.value_kind == "scalar", members.c.scalar_json),
                else_=json(members.c.stream_id),
            ),
            empty,
            with_members,
        ).where(members.c.value_kind.in_(("scalar", "parts"))),
        event(
            path(1, fields.c.slot, 1, 2),
            literal("literal"),
            json(case((fields.c.kind == "map", "}"), else_="]")),
            empty,
            walk.join(fields, fields.c.record_id == walk.c.record_id),
        ).where(fields.c.kind.in_(("array", "map"))),
        event(
            path(1, field_count, 0),
            literal("extension"),
            nodes.c.structure_json["extensions"]["stream_id"],
            case((field_count > 0, ","), else_=""),
            with_nodes,
        ).where(nodes.c.structure_json.bool_op("?")("extensions")),
        event(
            path(2),
            literal("literal"),
            json(case((nodes.c.native_type == "NativeArray", ""), else_="}")),
            empty,
            with_nodes,
        ),
    ).cte(prefix + "events")
    return NativeEventRelations(nodes, members, fields, walk, events)


def native_event_query(relations):
    events = relations.events
    return select(
        func.jsonb_build_object(
            "kind", events.c.kind, "value", events.c.value, "prefix", events.c.prefix
        )
    ).order_by(events.c.path)


def companion_event_relation(model, companions, *, prefix=""):
    """Build companion header, field, part and close events over selected rows."""
    companions = select(companions).cte(prefix + "companions").prefix_with("MATERIALIZED")
    source_fields = model.tables["kb.pdf_record_companion_field"]
    streams = model.tables["ops.pdf_artifact_stream"]
    from .pdf_record_model import record_upload_table

    parts_model = record_upload_table("ops.pdf_stage_artifact_part", model)
    fields = (
        select(*source_fields.c, companions.c.ordinal.label("row_ordinal"))
        .select_from(
            source_fields.join(
                companions,
                and_(
                    *(
                        source_fields.c[name] == companions.c[name]
                        for name in ("product_id", "revision_id", "family", "local_id")
                    )
                ),
            )
        )
        .cte(prefix + "fields")
        .prefix_with("MATERIALIZED")
    )
    parts = (
        func.ops.pdf_artifact_parts(
            fields.c.product_id,
            fields.c.revision_id,
            False,
            array([cast(fields.c.stream_id, Text())]),
        )
        .table_valued(*(column(field.name, field.type) for field in parts_model.c))
        .lateral(prefix + "part")
    )
    stream_match = and_(
        *(fields.c[name] == streams.c[name] for name in ("product_id", "revision_id", "stream_id"))
    )
    part_match = and_(
        *(fields.c[name] == parts.c[name] for name in ("product_id", "revision_id", "stream_id"))
    )

    def row_event(phase, payload):
        return select(
            companions.c.ordinal,
            companions.c.local_id,
            literal(phase).label("phase"),
            literal("").label("field_name"),
            literal(0).label("subphase"),
            cast(literal(0), BigInteger()).label("part_ordinal"),
            payload.label("event"),
        )

    stream_payload = func.to_jsonb(streams.table_valued(), type_=JSONB()).op("||")(
        func.jsonb_build_object(
            "field_name", fields.c.field_name, "scalar_kind", fields.c.scalar_kind, type_=JSONB()
        )
    )
    return union_all(
        row_event(0, func.jsonb_build_object("kind", "row", "body", companions.c.body)),
        select(
            fields.c.row_ordinal,
            fields.c.local_id,
            literal(1),
            fields.c.field_name,
            literal(0),
            cast(literal(0), BigInteger()),
            func.jsonb_build_object("kind", "field", "field", stream_payload),
        ).select_from(fields.join(streams, stream_match)),
        select(
            fields.c.row_ordinal,
            fields.c.local_id,
            literal(1),
            fields.c.field_name,
            literal(1),
            parts.c.ordinal,
            func.jsonb_build_object("kind", "part", "part", func.to_jsonb(parts.table_valued())),
        ).select_from(fields.join(parts, part_match)),
        row_event(2, func.jsonb_build_object("kind", "close")),
    ).cte(prefix + "events")


def companion_event_query(events):
    return select(events.c.event).order_by(
        events.c.ordinal,
        events.c.local_id,
        events.c.phase,
        events.c.field_name,
        events.c.subphase,
        events.c.part_ordinal,
    )
