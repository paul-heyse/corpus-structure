"""Native projection correspondence from captured physical records."""

import json
from collections.abc import Mapping

from pglast import ast, enums, parse_sql
from pglast.visitors import Visitor
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Double,
    Integer,
    MetaData,
    Numeric,
    Select,
    Table,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, array, insert

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDataConversion,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    SelectInto,
    _render,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_access_projection import ITEM_REPORT_KINDS
from .pdf_record_model import record_upload_table
from .pdf_staging import stage_upload_profile


def prepare_pdf_access_statements(model: MetaData, build):
    """Derive the indexed item and page relations from the admitted JSON copies."""
    stage = model.tables["ops.pdf_stage_access"]
    access = model.tables["kb.pdf_record_access"]
    pages = model.tables["kb.pdf_record_page_access"]
    scoped = (
        select(stage.c.product_id, stage.c.revision_id, stage.c.pointer, stage.c.native_json)
        .where(stage.c.product_id == build, stage.c.revision_id == build)
        .cte("json_copies")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    body = scoped.c.native_json
    items = (
        select(
            scoped,
            body["parent"]["$ref"].astext.label("parent_pointer"),
            func.coalesce(body["label"].astext, "unspecified").label("label"),
            func.coalesce(body["content_layer"].astext, "body").label("content_layer"),
            body["text"].astext.label("text"),
        )
        .where(body.has_key("self_ref"))
        .cte("items")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    parent, child = items.alias("parent"), items.alias("child")
    is_section = child.c.label.in_(("section", "chapter"))
    owners = (
        select(child.c.pointer, case((is_section, child.c.pointer)).label("owner"))
        .select_from(child.outerjoin(parent, parent.c.pointer == child.c.parent_pointer))
        .where(parent.c.pointer.is_(None))
        .cte("section_owners", recursive=True)
    )
    owners = owners.union_all(
        select(
            child.c.pointer,
            case((is_section, child.c.pointer), else_=owners.c.owner),
        ).select_from(owners.join(child, child.c.parent_pointer == owners.c.pointer))
    )
    header = model.tables["ops.pdf_record_document"].alias("h")
    native = model.tables["kb.pdf_record_native"]
    document, root = native.alias("d"), native.alias("root")
    root_fields = (
        func.jsonb_each(document.c.structure_json["fields"])
        .table_valued(column("key", Text()), column("value", JSONB()))
        .lateral("root_fields")
    )
    roots = (
        select(
            root.c.scalars_json["self_ref"].astext.label("pointer"),
            cast(
                array([case((root_fields.c.key == "body", 0), else_=1)]), ARRAY(BigInteger())
            ).label("position"),
        )
        .select_from(
            header.join(
                document,
                and_(
                    document.c.product_id == build,
                    document.c.revision_id == build,
                    document.c.record_id == header.c.root_id,
                ),
            )
            .join(root_fields, true())
            .join(
                root,
                and_(
                    root.c.product_id == build,
                    root.c.revision_id == build,
                    root.c.record_id == root_fields.c.value["target"].astext,
                ),
            )
        )
        .where(
            header.c.product_id == build,
            header.c.revision_id == build,
            root_fields.c.key.in_(("body", "furniture")),
        )
        .cte("document_roots")
    )
    traversal = select(
        roots.c.pointer,
        roots.c.position,
        array([roots.c.pointer], type_=Text()).label("path"),  # pyrefly: ignore[bad-argument-type]
    ).cte("traversal", recursive=True)
    children = (
        func.jsonb_array_elements(
            func.coalesce(parent.c.native_json["children"], cast(literal("[]"), JSONB()))
        )
        .table_valued(column("value", JSONB()), with_ordinality="ordinality")
        .render_derived()
        .lateral("children")
    )
    edges = (
        select(
            parent.c.pointer.label("parent_pointer"),
            child.c.pointer.label("pointer"),
            func.min(children.c.ordinality).label("position"),
        )
        .select_from(
            parent.join(children, true()).join(
                child,
                and_(
                    child.c.pointer == children.c.value["$ref"].astext,
                    child.c.parent_pointer == parent.c.pointer,
                ),
            )
        )
        .group_by(parent.c.pointer, child.c.pointer)
        .cte("containment_edges")
    )
    traversal = traversal.union_all(
        select(
            edges.c.pointer,
            traversal.c.position.concat(
                array([edges.c.position], type_=BigInteger())  # pyrefly: ignore[bad-argument-type]
            ),
            traversal.c.path.concat(
                array([edges.c.pointer], type_=Text())  # pyrefly: ignore[bad-argument-type]
            ),
        )
        .select_from(traversal.join(edges, edges.c.parent_pointer == traversal.c.pointer))
        .where(~(edges.c.pointer == any_(traversal.c.path)))
    )
    ordered = select(
        items.c.product_id,
        items.c.revision_id,
        items.c.pointer,
        (
            func.row_number().over(
                order_by=(
                    traversal.c.position.is_(None),
                    traversal.c.position,
                    items.c.pointer.collate("C"),
                )
            )
            - 1
        ).label("ordinal"),
        items.c.label,
        items.c.parent_pointer,
        owners.c.owner.label("section_pointer"),
        items.c.content_layer,
        items.c.text,
        items.c.native_json,
    ).select_from(
        items.outerjoin(traversal, traversal.c.pointer == items.c.pointer).outerjoin(
            owners, owners.c.pointer == items.c.pointer
        )
    )
    dimensions = select(
        scoped.c.product_id,
        scoped.c.revision_id,
        cast(body["page_no"].astext, BigInteger()),
        cast(body["size"]["width"].astext, Numeric()),
        cast(body["size"]["height"].astext, Numeric()),
    ).where(~body.has_key("self_ref"))
    return (
        insert(access)
        .from_select([col.name for col in ordered.selected_columns], ordered)
        .on_conflict_do_nothing(),
        insert(pages).from_select(list(pages.c.keys()), dimensions).on_conflict_do_nothing(),
        prepare_pdf_region_addresses(model, build),
        _prepare_pdf_report_items(model, build),
    )


def prepare_pdf_region_addresses(model: MetaData, build=None):
    """Index retained provenance membership without copying coordinate values."""
    access = model.tables["kb.pdf_record_access"]
    addresses = model.tables["kb.pdf_record_region_address"]
    provenance = (
        func.jsonb_array_elements(
            func.coalesce(access.c.native_json["prov"], cast(literal("[]"), JSONB()))
        )
        .table_valued(column("value", JSONB()), with_ordinality="ordinality")
        .render_derived()
        .lateral("provenance")
    )
    rows = select(
        access.c.product_id,
        access.c.revision_id,
        cast(provenance.c.value["page_no"].astext, BigInteger()),
        access.c.pointer,
        cast(provenance.c.ordinality, BigInteger()) - 1,
    ).select_from(access.join(provenance, true()))
    if build is not None:
        rows = rows.where(access.c.product_id == build, access.c.revision_id == build)
    return (
        insert(addresses)
        .from_select(["product_id", "revision_id", "page_no", "pointer", "region_index"], rows)
        .on_conflict_do_nothing()
    )


def _prepare_pdf_report_items(model: MetaData, build):
    reports = model.tables["kb.pdf_record_report_item"]
    companion = model.tables["kb.pdf_record_companion"]
    kind = companion.c.body["kind"].astext
    scoped = (
        companion.c.product_id == build,
        companion.c.revision_id == build,
        companion.c.family == "native_metadata",
    )
    direct_pointer = companion.c.body["pointer"].astext
    direct = select(
        companion.c.product_id,
        companion.c.revision_id,
        kind,
        direct_pointer,
        companion.c.local_id,
    ).where(*scoped, kind.in_(ITEM_REPORT_KINDS[:2]), direct_pointer.is_not(None))
    # Adoption validates the compact addresses against the exact byte field.
    # The opaque report may contain values outside PostgreSQL JSONB's domain.
    pointer = (
        func.jsonb_array_elements_text(companion.c.body["item_pointers"])
        .table_valued(column("value", Text()))
        .lateral("pointers")
    )
    inline_items = (
        select(
            companion.c.product_id,
            companion.c.revision_id,
            kind,
            pointer.c.value,
            companion.c.local_id,
        )
        .select_from(companion.join(pointer, true()))
        .where(*scoped, kind == ITEM_REPORT_KINDS[2])
    )
    return (
        insert(reports)
        .from_select(
            ["product_id", "revision_id", "kind", "pointer", "local_id"],
            direct.union_all(inline_items),
        )
        .on_conflict_do_nothing()
    )


def pdf_region_view(model: MetaData) -> Select:
    """Seek by page or pointer before obtaining the exact admitted provenance value."""
    access = model.tables["kb.pdf_record_access"]
    addresses = model.tables["kb.pdf_record_region_address"]
    pages = model.tables["kb.pdf_record_page_access"]
    bbox = access.c.native_json["prov"][cast(addresses.c.region_index, Integer())]["bbox"]
    return select(
        addresses.c.product_id,
        addresses.c.revision_id,
        addresses.c.pointer,
        addresses.c.region_index,
        addresses.c.page_no,
        pages.c.page_width,
        pages.c.page_height,
        *(
            cast(bbox[key].astext, Numeric()).label(name)
            for name, key in (("left", "l"), ("top", "t"), ("right", "r"), ("bottom", "b"))
        ),
        cast(
            case((bbox["coord_origin"].astext == "TOPLEFT", "top_left"), else_="bottom_left"),
            Text(),
        ).label("origin"),
    ).select_from(
        addresses.join(
            access,
            and_(
                access.c.product_id == addresses.c.product_id,
                access.c.revision_id == addresses.c.revision_id,
                access.c.pointer == addresses.c.pointer,
            ),
        ).join(
            pages,
            and_(
                pages.c.product_id == addresses.c.product_id,
                pages.c.revision_id == addresses.c.revision_id,
                pages.c.page_no == addresses.c.page_no,
            ),
        )
    )


def pdf_region_relation(model: MetaData) -> Table:
    return Table(
        "pdf_record_region_view",
        MetaData(),
        *(Column(field.name, field.type) for field in pdf_region_view(model).selected_columns),
        schema="kb",
    )


def pdf_access_correspondence_programs(model: MetaData) -> tuple[ProgramDeclaration, ...]:
    stream = model.tables["ops.pdf_artifact_stream"]
    output = []
    text = pg_type("text")

    def json_value(value):
        return cast(literal(json.dumps(value)), JSONB())

    def scalar(value):
        return value.op("#>>", return_type=Text())(array([], type_=Text()))

    def routine(name, parameters, returns, statements, locals_=(), *, immutable=False):
        output.append(
            ProgramDeclaration(
                NativeRoutine(
                    "ops",
                    name,
                    parameters=parameters,
                    returns=pg_type(returns),
                    search_path=("pg_catalog", "pg_temp"),
                    volatility="immutable" if immutable else "stable",
                    body=Block(tuple(statements), tuple(locals_)),
                ),
                "authoring/pdf-record-access.sql",
                role_name("publisher"),
                INTERNAL_PROGRAM,
            )
        )

    p_value, expected = (core_variable(name, JSONB()) for name in ("p_value", "p_expected"))
    actual_bytes, expected_bytes = (
        core_variable(name, BYTEA()) for name in ("actual_", "expected_")
    )
    zero_bytes = tuple(
        func.decode(value, "hex") for value in ("0000000000000000", "8000000000000000")
    )
    numeric_value = cast(scalar(p_value), Numeric())
    routine(
        "pdf_projection_scalar_matches",
        (Parameter("p_value", pg_type("jsonb")), Parameter("p_expected", pg_type("jsonb"))),
        "bool",
        (
            CatchDataConversion(
                (
                    If(or_(p_value.is_(None), expected.is_(None)), (Return(literal(False)),)),
                    If(
                        and_(
                            func.jsonb_typeof(expected) == "object",
                            expected.bool_op("?")("native_float64"),
                        ),
                        (
                            If(func.jsonb_typeof(p_value) != "number", (Return(literal(False)),)),
                            Assign("actual_", func.float8send(cast(scalar(p_value), Double()))),
                            Assign(
                                "expected_", func.decode(expected["native_float64"].astext, "hex")
                            ),
                            Return(
                                or_(
                                    actual_bytes == expected_bytes,
                                    and_(expected_bytes.in_(zero_bytes), numeric_value == 0),
                                )
                            ),
                        ),
                    ),
                    Return(
                        and_(
                            func.jsonb_typeof(p_value) == func.jsonb_typeof(expected),
                            p_value == expected,
                        )
                    ),
                ),
                (Return(literal(False)),),
            ),
        ),
        (Local("actual_", pg_type("bytea")), Local("expected_", pg_type("bytea"))),
        immutable=True,
    )
    build, stream_id = core_variable("p_build", Text()), core_variable("p_stream", Text())
    profile = core_variable("stream_", stream.c.encoding_profile.type, "encoding_profile")
    length = core_variable("stream_", stream.c.byte_length.type, "byte_length")
    root = core_variable("stream_", stream.c.byte_root.type, "byte_root")
    payload = core_variable("payload_", BYTEA())
    selected_stream = SelectInto(
        select(core_relation_row(stream))
        .select_from(stream)
        .where(
            stream.c.product_id == build,
            stream.c.revision_id == build,
            stream.c.stream_id == stream_id,
        ),
        ("stream_",),
        strict=True,
    )
    part_model = record_upload_table("ops.pdf_stage_artifact_part", model)
    parts = (
        func.ops.pdf_artifact_parts(build, build, False, array([stream_id]))
        .table_valued(*(column(field.name, field.type) for field in part_model.c))
        .alias("parts")
    )
    part_scope = (
        parts.c.product_id == build,
        parts.c.revision_id == build,
        parts.c.stream_id == stream_id,
    )
    actual_length = core_variable("actual_length_", BigInteger())
    upload = stage_upload_profile(physical_sources=model.info["physical_sources"])
    empty_bytes = func.decode("", "hex")
    routine(
        "pdf_projection_stream_value",
        (Parameter("p_build", text), Parameter("p_stream", text)),
        "jsonb",
        (
            selected_stream,
            SelectInto(
                select(func.coalesce(func.sum(func.octet_length(parts.c.body)), 0)).where(
                    *part_scope
                ),
                ("actual_length_",),
            ),
            If(
                or_(actual_length > upload["max_native_bytes"], actual_length != length),
                (
                    Raise(
                        "native access scalar exceeds bounded projection or stream length", "23514"
                    ),
                ),
            ),
            SelectInto(
                select(
                    func.coalesce(
                        func.string_agg(parts.c.body, empty_bytes).aggregate_order_by(
                            parts.c.ordinal
                        ),
                        empty_bytes,
                    )
                ).where(*part_scope),
                ("payload_",),
            ),
            If(
                profile == "pdf-record-native-json-v1",
                (Return(cast(func.convert_from(payload, "UTF8"), JSONB())),),
            ),
            If(
                profile == "pdf-record-scalar-v1:s",
                (Return(func.to_jsonb(func.convert_from(payload, "UTF8"))),),
            ),
            Raise("native access requires a JSON/string stream profile", "23514"),
        ),
        (
            Local("stream_", stream),
            Local("actual_length_", pg_type("bigint")),
            Local("payload_", pg_type("bytea")),
        ),
    )

    floating_zero = and_(
        numeric_value == 0,
        length == 8,
        root.in_(
            tuple(
                func.encode(func.ops.pdf_identity_byte_root(value), "hex") for value in zero_bytes
            )
        ),
    )
    assign_scalar = (
        If(
            profile == "pdf-record-native-json-v1",
            (Return(func.ops.pdf_projection_stream_value(build, stream_id) == p_value),),
        ),
        If(
            and_(profile == "pdf-record-scalar-v1:s", func.jsonb_typeof(p_value) == "string"),
            (Assign("payload_", func.convert_to(scalar(p_value), "UTF8")),),
            (
                If(
                    and_(
                        profile == "pdf-record-scalar-v1:i", func.jsonb_typeof(p_value) == "number"
                    ),
                    (
                        If(
                            scalar(p_value).bool_op("!~")("^(0|-?[1-9][0-9]*)$"),
                            (Return(literal(False)),),
                        ),
                        Assign("payload_", func.convert_to(scalar(p_value), "UTF8")),
                    ),
                    (
                        If(
                            and_(
                                profile == "pdf-record-scalar-v1:f",
                                func.jsonb_typeof(p_value) == "number",
                            ),
                            (
                                Assign(
                                    "payload_", func.float8send(cast(scalar(p_value), Double()))
                                ),
                                If(floating_zero, (Return(literal(True)),)),
                            ),
                            (
                                If(
                                    and_(
                                        profile == "pdf-record-scalar-v1:n",
                                        p_value == json_value(None),
                                    ),
                                    (Assign("payload_", empty_bytes),),
                                    (
                                        If(
                                            and_(
                                                profile == "pdf-record-scalar-v1:b",
                                                func.jsonb_typeof(p_value) == "boolean",
                                            ),
                                            (
                                                Assign(
                                                    "payload_",
                                                    case(
                                                        (
                                                            p_value == json_value(True),
                                                            func.decode("01", "hex"),
                                                        ),
                                                        else_=func.decode("00", "hex"),
                                                    ),
                                                ),
                                            ),
                                            (Return(literal(False)),),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    routine(
        "pdf_projection_stream_matches",
        (
            Parameter("p_build", text),
            Parameter("p_stream", text),
            Parameter("p_value", pg_type("jsonb")),
        ),
        "bool",
        (
            CatchDataConversion(
                (
                    If(p_value.is_(None), (Return(literal(False)),)),
                    selected_stream,
                    *assign_scalar,
                    Return(
                        and_(
                            func.octet_length(payload) == length,
                            func.encode(func.ops.pdf_identity_byte_root(payload), "hex") == root,
                        )
                    ),
                ),
                (Return(literal(False)),),
            ),
        ),
        (Local("stream_", stream), Local("payload_", pg_type("bytea"))),
    )

    output.append(_access_checker_program(model))
    return tuple(output)


def pdf_access_correspondence_sql(model: MetaData) -> str:
    return (
        native_sql_script(
            statement
            for program in pdf_access_correspondence_programs(model)
            for statement in (
                program.routine.render(),
                native_privilege_sql(program.identity, "PUBLIC", grant=False),
            )
        )
        + "\n"
    )


def _cycle_predicate(query: Select, cycles: Mapping[str, tuple[str, str, str]]) -> ast.SubLink:
    """Attach PostgreSQL CYCLE to Core's declared recursive relations."""
    statement = parse_sql(_render(query))[0].stmt

    class Cycles(Visitor):
        def visit_CommonTableExpr(self, ancestors, node):
            if node.ctename in cycles:
                field, marker, path = cycles[node.ctename]
                node.cycle_clause = ast.CTECycleClause(
                    cycle_col_list=(ast.String(sval=field),),
                    cycle_mark_column=marker,
                    cycle_path_column=path,
                )

    if not isinstance(statement, ast.SelectStmt) or not statement.targetList:
        raise ValueError("projection cycle requires one structured predicate")
    Cycles()(statement)
    return ast.SubLink(subLinkType=enums.SubLinkType.EXISTS_SUBLINK, subselect=statement)


def _access_checker_program(model: MetaData) -> ProgramDeclaration:
    build = core_variable("p_build", Text())
    access = model.tables["kb.pdf_record_access"].alias("a")
    native = model.tables["kb.pdf_record_native"].alias("n")
    membership = model.tables["kb.pdf_record_membership"].alias("m")
    header = model.tables["ops.pdf_record_document"].alias("h")
    page_access = model.tables["kb.pdf_record_page_access"].alias("p")
    statements = []

    def scope(relation):
        return relation.c.product_id == build, relation.c.revision_id == build

    def reject(query, message, *, cycles=None):
        condition = _cycle_predicate(query, cycles) if cycles else query.exists()
        statements.append(If(condition, (Raise(message, "23514"),)))

    def json_items(value, name):
        return (
            func.jsonb_each(value)
            .table_valued(column("key", Text()), column("value", JSONB()))
            .lateral(name)
        )

    def member_value(container, fields, member):
        key = func.coalesce(
            member.c.member_key,
            func.ops.pdf_projection_stream_value(build, member.c.member_key_stream_id).op(
                "#>>", return_type=Text()
            )(array([], type_=Text())),
        )
        return case(
            (fields.c.value["kind"].astext == "map", container[key]),
            else_=container[cast(member.c.ordinal, Integer())],
        )

    reject(
        select(1)
        .select_from(
            access.outerjoin(
                native,
                and_(
                    *scope(native),
                    native.c.native_address == access.c.pointer,
                ),
            )
        )
        .where(
            access.c.product_id == build,
            or_(
                access.c.revision_id != build,
                native.c.record_id.is_(None),
                access.c.native_json["self_ref"].astext.is_distinct_from(access.c.pointer),
            ),
        ),
        "native access fields do not correspond to frozen native item",
    )

    projected = (
        select(native.c.record_id, access.c.native_json.label("value"))
        .select_from(
            access.join(native, and_(*scope(native), native.c.native_address == access.c.pointer))
        )
        .where(*scope(access))
        .cte("projected", recursive=True)
    )
    w = projected
    f = json_items(native.c.structure_json["fields"], "f")
    container = (
        select(
            case(
                (and_(native.c.native_type == "NativeArray", f.c.key == "items"), w.c.value),
                else_=w.c.value[f.c.key],
            ).label("value")
        )
        .correlate(native, f, w)
        .lateral("container")
    )
    child = union_all(
        select(f.c.value["target"].astext.label("record_id"), w.c.value[f.c.key].label("value"))
        .select_from(f)
        .where(f.c.value["kind"].astext == "object")
        .correlate(native, w),
        select(
            membership.c.record_id, member_value(container.c.value, f, membership).label("value")
        )
        .select_from(
            f.join(
                membership,
                and_(
                    *scope(membership),
                    membership.c.parent_id == w.c.record_id,
                    membership.c.field_name == f.c.key,
                ),
            ).join(container, true())
        )
        .where(f.c.value["kind"].astext.in_(("array", "map")), membership.c.value_kind == "record")
        .correlate(native, w),
    ).lateral("child")
    projected = projected.union_all(
        select(child.c.record_id, child.c.value).select_from(
            w.join(native, and_(*scope(native), native.c.record_id == w.c.record_id)).join(
                child, true()
            )
        )
    )
    w = projected.alias("w")
    # Both key sets belong to the same native row. Correlated scalar set-returning
    # expressions keep their row source outside the key union.
    scalar_keys = select(func.jsonb_object_keys(native.c.scalars_json)).correlate(native)
    structured_keys = select(func.jsonb_object_keys(native.c.structure_json["fields"])).correlate(
        native
    )
    keys = scalar_keys.union(structured_keys).subquery("field_keys")
    extra_keys = (
        select(func.coalesce(func.array_agg(keys.c[0]), cast(array([]), ARRAY(Text()))))
        .select_from(keys)
        .correlate(native)
        .scalar_subquery()
    )
    extra = w.c.value.op("-")(extra_keys)
    extensions = case(
        (
            native.c.structure_json.bool_op("?")("extensions"),
            func.ops.pdf_projection_stream_matches(
                build, native.c.structure_json["extensions"]["stream_id"].astext, extra
            ).is_not(True),
        ),
        else_=extra != cast(literal("{}"), JSONB()),
    )
    s = json_items(native.c.scalars_json, "s")
    bad_scalar = (
        select(1)
        .select_from(s)
        .where(func.ops.pdf_projection_scalar_matches(w.c.value[s.c.key], s.c.value).is_not(True))
        .correlate(native, w)
        .exists()
    )
    f = json_items(native.c.structure_json["fields"], "f")
    container = (
        select(
            case(
                (and_(native.c.native_type == "NativeArray", f.c.key == "items"), w.c.value),
                else_=w.c.value[f.c.key],
            ).label("value")
        )
        .correlate(native, f, w)
        .lateral("container")
    )
    object_keys = (
        func.jsonb_object_keys(container.c.value)
        .table_valued(column("value", Text()))
        .render_derived()
    )
    count_keys = (
        select(func.count()).select_from(object_keys).correlate(container).scalar_subquery()
    )
    actual = (
        select(member_value(container.c.value, f, membership).label("value"))
        .correlate(container, f, membership)
        .lateral("actual")
    )
    bad_member = (
        select(1)
        .select_from(membership.join(actual, true()))
        .where(
            *scope(membership),
            membership.c.parent_id == w.c.record_id,
            membership.c.field_name == f.c.key,
            or_(
                actual.c.value.is_(None),
                and_(
                    membership.c.value_kind == "scalar",
                    func.ops.pdf_projection_scalar_matches(
                        actual.c.value, membership.c.scalar_json
                    ).is_not(True),
                ),
                and_(
                    membership.c.value_kind == "parts",
                    func.ops.pdf_projection_stream_matches(
                        build, membership.c.stream_id, actual.c.value
                    ).is_not(True),
                ),
            ),
        )
        .correlate(w, f, container)
        .exists()
    )
    bad_field = (
        select(1)
        .select_from(f.join(container, true()))
        .where(
            or_(
                container.c.value.is_(None),
                and_(
                    f.c.value["kind"].astext == "object",
                    func.jsonb_typeof(container.c.value) != "object",
                ),
                and_(
                    f.c.value["kind"].astext == "parts",
                    func.ops.pdf_projection_stream_matches(
                        build, f.c.value["stream_id"].astext, container.c.value
                    ).is_not(True),
                ),
                and_(
                    f.c.value["kind"].astext == "array",
                    or_(
                        func.jsonb_typeof(container.c.value) != "array",
                        func.jsonb_array_length(container.c.value)
                        != cast(f.c.value["length"].astext, BigInteger()),
                    ),
                ),
                and_(
                    f.c.value["kind"].astext == "map",
                    or_(
                        func.jsonb_typeof(container.c.value) != "object",
                        count_keys != cast(f.c.value["length"].astext, BigInteger()),
                    ),
                ),
                bad_member,
            )
        )
        .correlate(native, w)
        .exists()
    )
    reject(
        select(1)
        .select_from(w.outerjoin(native, and_(*scope(native), native.c.record_id == w.c.record_id)))
        .where(
            or_(
                core_variable("w", Boolean(), "cycle_"),
                native.c.record_id.is_(None),
                w.c.value.is_(None),
                and_(
                    native.c.native_type == "NativeArray", func.jsonb_typeof(w.c.value) != "array"
                ),
                and_(
                    native.c.native_type != "NativeArray",
                    or_(func.jsonb_typeof(w.c.value) != "object", extensions),
                ),
                bad_scalar,
                bad_field,
            )
        ),
        "native access JSON differs from frozen record fields/members/scalars",
        cycles={"projected": ("record_id", "cycle_", "path_")},
    )

    pages, page, size = (
        model.tables["kb.pdf_record_membership"].alias("pages"),
        model.tables["kb.pdf_record_native"].alias("page"),
        model.tables["kb.pdf_record_native"].alias("page_size"),
    )
    page_sizes = (
        select(pages.c.member_key, size.c.scalars_json.label("dimensions"))
        .select_from(
            header.join(
                pages,
                and_(
                    *scope(pages),
                    pages.c.parent_id == header.c.root_id,
                    pages.c.field_name == "pages",
                ),
            )
            .outerjoin(page, and_(*scope(page), page.c.record_id == pages.c.record_id))
            .outerjoin(
                size,
                and_(
                    *scope(size),
                    size.c.record_id == page.c.structure_json["fields"]["size"]["target"].astext,
                ),
            )
        )
        .where(*scope(header))
        .cte("page_sizes")
        .prefix_with("MATERIALIZED")
    )
    reject(
        select(1)
        .select_from(
            page_access.outerjoin(
                page_sizes, page_sizes.c.member_key == cast(page_access.c.page_no, Text())
            )
        )
        .where(
            page_access.c.product_id == build,
            or_(
                page_access.c.revision_id != build,
                page_sizes.c.member_key.is_(None),
                func.ops.pdf_projection_scalar_matches(
                    func.to_jsonb(page_access.c.page_width), page_sizes.c.dimensions["width"]
                ).is_not(True),
                func.ops.pdf_projection_scalar_matches(
                    func.to_jsonb(page_access.c.page_height), page_sizes.c.dimensions["height"]
                ).is_not(True),
            ),
        ),
        "native access page JSON differs from frozen page dimensions",
    )
    provenance = (
        func.jsonb_array_elements(
            func.coalesce(access.c.native_json["prov"], cast(literal("[]"), JSONB()))
        )
        .table_valued(column("value", JSONB()))
        .lateral("provenance")
    )
    reject(
        select(1)
        .select_from(access.join(provenance, true()))
        .where(
            *scope(access),
            ~select(1)
            .select_from(page_access)
            .where(
                *scope(page_access),
                page_access.c.page_no == cast(provenance.c.value["page_no"].astext, BigInteger()),
            )
            .correlate(access, provenance)
            .exists(),
        ),
        "native access provenance has no corresponding page JSON copy",
    )
    routine = NativeRoutine(
        "ops",
        "pdf_check_access_correspondence",
        parameters=(Parameter("p_build", pg_type("text")),),
        returns=pg_type("void"),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(tuple(statements)),
    )
    return ProgramDeclaration(
        routine, "authoring/pdf-record-access.sql", role_name("publisher"), INTERNAL_PROGRAM
    )
