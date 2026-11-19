"""Protected selected membership/context over the existing native event algebra."""

import json

import yaml
from sqlalchemy import (
    BigInteger,
    Integer,
    MetaData,
    Table,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
    union_all,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, aggregate_order_by, array

from corpus_structure.schema.integrity import role_name

from .native_objects import NativeProgramAccess, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Raise,
    ReturnQuery,
    SelectInto,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration
from .pdf_record_event_queries import companion_event_relation, native_event_relations


def selected_membership_relations(metadata: MetaData, *, published, section):
    """Pin access rows before traversing descendants and ancestors."""
    source = metadata.tables["kb.pdf_record_access"].alias("a")
    root = section
    access = (
        select(source)
        .join(
            published,
            (source.c.product_id == published.c.build_id)
            & (source.c.revision_id == published.c.build_id),
        )
        .cte("access")
        .prefix_with("MATERIALIZED")
    )
    subtree = (
        select(access.c.pointer).where(access.c.pointer == root).cte("subtree", recursive=True)
    )
    child = access.alias("child")
    subtree = subtree.union_all(
        select(child.c.pointer).join(subtree, child.c.parent_pointer == subtree.c.pointer)
    )
    selected = (
        select(access)
        .where(access.c.pointer.in_(select(subtree.c.pointer)))
        .cte("selected")
        .prefix_with("MATERIALIZED")
    )
    ancestors = (
        select(access.c.parent_pointer.label("pointer"))
        .where(access.c.pointer == root, access.c.parent_pointer.is_not(None))
        .cte("ancestors", recursive=True)
    )
    parent = access.alias("ancestor_access")
    ancestors = ancestors.union(
        select(parent.c.parent_pointer)
        .join(ancestors, parent.c.pointer == ancestors.c.pointer)
        .where(parent.c.parent_pointer.is_not(None))
    )
    return access, subtree, selected, ancestors


def selected_content_relations(metadata: MetaData, selected, ancestors, *, published):
    """Follow pinned native children and select contextual native metadata."""
    native = metadata.tables["kb.pdf_record_native"].alias("n")
    contained = (
        select(native.c.record_id)
        .select_from(
            native.join(
                published,
                (native.c.product_id == published.c.build_id)
                & (native.c.revision_id == published.c.build_id),
            ).join(selected, selected.c.pointer == native.c.native_address)
        )
        .cte("contained", recursive=True)
    )
    source = metadata.tables["kb.pdf_record_native"].alias("contained_native")
    fields = (
        func.jsonb_each(source.c.structure_json["fields"])
        .table_valued(column("key", Text()), column("value", JSONB()))
        .lateral("f")
    )
    members = metadata.tables["kb.pdf_record_membership"].alias("m")
    children = union_all(
        select(fields.c.value["target"].astext.label("record_id"))
        .select_from(fields)
        .where(fields.c.value["kind"].astext == "object")
        .correlate(source, published),
        select(members.c.record_id)
        .where(
            members.c.product_id == published.c.build_id,
            members.c.revision_id == published.c.build_id,
            members.c.parent_id == source.c.record_id,
            members.c.value_kind == "record",
        )
        .correlate(source, published),
    ).lateral("child")
    contained = contained.union(
        select(children.c.record_id).select_from(
            contained.join(source, source.c.record_id == contained.c.record_id)
            .join(
                published,
                (source.c.product_id == published.c.build_id)
                & (source.c.revision_id == published.c.build_id),
            )
            .join(children, true())
        )
    )
    companion = metadata.tables["kb.pdf_record_companion"].alias("c")
    selected_pointers = select(selected.c.pointer)
    coverage_pointer = func.ops.pdf_companion_body(
        companion.c.product_id,
        companion.c.revision_id,
        companion.c.family,
        companion.c.local_id,
        companion.c.body,
        type_=JSONB(),
    )["value"]["section_pointer"].astext
    contextual_pointers = selected_pointers.union(select(ancestors.c.pointer))
    selected_metadata = (
        select(companion)
        .join(
            published,
            (companion.c.product_id == published.c.build_id)
            & (companion.c.revision_id == published.c.build_id),
        )
        .where(
            companion.c.family == "native_metadata",
            case(
                {
                    "formula_outcomes": companion.c.body["pointer"].astext.in_(selected_pointers),
                    "recognition_coverage": coverage_pointer.in_(contextual_pointers),
                },
                value=companion.c.body["kind"].astext,
                else_=False,
            ),
        )
        .cte("selected_metadata")
        .prefix_with("MATERIALIZED")
    )
    return contained, selected_metadata


def _path(*parts):
    return array(
        tuple(
            cast(literal(part), BigInteger()) if isinstance(part, int) else cast(part, BigInteger())
            for part in parts
        )
    )


def _event(event, **values):
    return func.jsonb_build_object(
        "event", event, *(item for pair in values.items() for item in pair), type_=JSONB()
    )


def _utf8(text):
    return func.convert_to(text, "UTF8", type_=BYTEA())


def _qualified_target(task, key, digest, **attributes):
    return func.jsonb_build_object(
        "task_id",
        task,
        "product_key",
        key,
        "content_digest",
        digest,
        *(item for pair in attributes.items() for item in pair),
        type_=JSONB(),
    )


def _output(phase, path, event, *, source=None):
    query = select(literal(phase).label("phase"), path.label("path"), event.label("event"))
    return query if source is None else query.select_from(source)


def _selected_events(model, revision, section, part_bytes):
    pin_table = model.tables["ops.pdf_published_revision"]
    task, key, digest = (
        core_variable(revision, pin_table.c[name].type, name)
        for name in ("task_id", "product_key", "logical_digest")
    )
    published_rows = func.ops.read_pdf_published_revision(task, key, digest).table_valued(
        column("build_id", pin_table.c.build_id.type)
    )
    published = select(published_rows.c.build_id).cte("published").prefix_with("MATERIALIZED")

    def placed(row):
        return and_(
            row.c.product_id == published.c.build_id, row.c.revision_id == published.c.build_id
        )

    access, _, selected, ancestors = selected_membership_relations(
        model, published=published, section=section
    )
    contained, metadata = selected_content_relations(
        model, selected, ancestors, published=published
    )

    def roots(nodes):
        return select(nodes.c.record_id, _path(selected.c.ordinal).label("path")).select_from(
            nodes.join(selected, nodes.c.native_address == selected.c.pointer)
        )

    native = native_event_relations(
        model, published, roots=roots, node_ids=select(contained.c.record_id)
    )
    events = native.events
    metadata_events = companion_event_relation(model, metadata, prefix="metadata_")

    selected_pointers = select(selected.c.pointer)
    pointers = select(func.coalesce(func.array_agg(selected.c.pointer), array((), type_=Text())))
    companions = model.tables["kb.pdf_record_companion"]
    contexts = func.ops.pdf_record_context_rows(
        task, key, digest, pointers.scalar_subquery(), section
    ).table_valued(
        *(
            column(name, companions.c[name].type)
            for name in ("family", "local_id", "ordinal", "body")
        )
    )
    context = select(contexts).cte("selected_context").prefix_with("MATERIALIZED")
    endpoints = model.tables["kb.pdf_record_endpoint"]

    def endpoint_value(column, current):
        return case((endpoints.c.target_task_id == 0, current), else_=column)

    end_task = endpoint_value(endpoints.c.target_task_id, task)
    end_key = endpoint_value(endpoints.c.target_product_key, key)
    end_digest = endpoint_value(endpoints.c.target_content_digest, digest)
    endpoint_id = endpoints.c.relation_id.op("||")(":").op("||")(cast(endpoints.c.ordinal, Text()))
    endpoint_payload = func.jsonb_build_object(
        "relation_id",
        endpoints.c.relation_id,
        "endpoint_ordinal",
        endpoints.c.ordinal,
        "role",
        endpoints.c.role,
        "target_task_id",
        end_task,
        "target_product_key",
        end_key,
        "target_content_digest",
        end_digest,
        "occurrence_id",
        endpoints.c.occurrence_id,
    )

    def companion_rows(row):
        return select(
            row.c.family, row.c.local_id, row.c.ordinal, cast(row.c.body, Text()).label("payload")
        )

    companion = (
        companion_rows(context)
        .union_all(
            companion_rows(companions)
            .select_from(companions.join(published, placed(companions)))
            .where(companions.c.family == "health"),
            companion_rows(metadata),
            select(
                literal("endpoint"),
                endpoint_id,
                endpoints.c.ordinal,
                cast(endpoint_payload, Text()),
            )
            .select_from(endpoints.join(published, placed(endpoints)))
            .where(
                endpoints.c.relation_id.in_(
                    select(context.c.local_id).where(context.c.family == "relation")
                )
            ),
        )
        .cte("companion")
        .prefix_with("MATERIALIZED")
    )
    ordered = select(
        companion,
        func.row_number()
        .over(
            order_by=(
                companion.c.family.collate("C"),
                companion.c.ordinal,
                companion.c.local_id.collate("C"),
            )
        )
        .label("position"),
    ).cte("companion_order")

    refs = model.tables["kb.pdf_record_reference"]
    origin = native.nodes.alias("origin")
    target = native.nodes.alias("target")
    reference_target = _qualified_target(task, key, digest).op("||")(
        case(
            (
                refs.c.field_name.in_(("source_cell_id", "target_cell_id")),
                func.jsonb_build_object(
                    "address_space", "native_graph_cell", "cell_id_lexical", refs.c.native_pointer
                ),
            ),
            else_=func.jsonb_build_object(
                "address_space", "native_item", "pointer", refs.c.native_pointer
            ),
        )
    )
    reference = func.jsonb_build_object(
        "from_pointer",
        selected.c.pointer,
        "field",
        refs.c.field_name,
        "reference_id",
        refs.c.reference_id,
        "source_id",
        refs.c.source_id,
        "native_address",
        origin.c.native_address,
        "source_ordinal",
        selected.c.ordinal,
        "source_order",
        func.to_jsonb(native.walk.c.path),
        "target",
        reference_target,
        "resolution",
        "qualified_external",
        type_=JSONB(),
    )
    end_reference = func.jsonb_build_object(
        "relation_id",
        endpoints.c.relation_id,
        "endpoint_ordinal",
        endpoints.c.ordinal,
        "role",
        endpoints.c.role,
        "target",
        _qualified_target(
            end_task,
            end_key,
            end_digest,
            occurrence_id=endpoints.c.occurrence_id,
        ),
        "resolution",
        "qualified_external",
        type_=JSONB(),
    )
    outside = (
        select(reference.label("body"))
        .select_from(
            selected.join(native.walk, native.walk.c.path[1] == selected.c.ordinal)
            .join(refs, refs.c.source_id == native.walk.c.record_id)
            .join(origin, origin.c.record_id == refs.c.source_id)
            .join(published, placed(refs))
        )
        .where(
            refs.c.native_pointer.is_not(None),
            ~select(1).select_from(target).where(target.c.record_id == refs.c.target_id).exists(),
        )
        .union_all(
            select(end_reference)
            .select_from(endpoints.join(published, placed(endpoints)))
            .where(
                endpoints.c.relation_id.in_(
                    select(companion.c.local_id).where(companion.c.family == "relation")
                ),
                tuple_(
                    endpoints.c.target_task_id,
                    endpoints.c.target_product_key,
                    endpoints.c.target_content_digest,
                ).not_in((tuple_(task, key, digest), tuple_(0, "@self", "@self"))),
                endpoints.c.occurrence_id.in_(
                    select(companion.c.local_id).where(companion.c.family == "occurrence")
                ),
            )
        )
        .cte("external")
    )

    listing = (
        selected.c.pointer.op("||")(func.chr(9))
        .op("||")(cast(selected.c.ordinal, Text()))
        .op("||")(func.chr(9))
        .op("||")(func.coalesce(selected.c.parent_pointer, ""))
        .op("||")(func.chr(10))
    )
    membership = (
        select(
            func.encode(
                func.sha256(
                    _utf8(
                        func.coalesce(
                            func.string_agg(
                                listing, aggregate_order_by(literal(""), selected.c.ordinal)
                            ),
                            "",
                        )
                    )
                ),
                "hex",
            )
        )
        .select_from(selected)
        .scalar_subquery()
    )
    region = model.tables["kb.pdf_record_region"].alias("r")
    payload = ordered.c.payload
    size = func.octet_length(payload)
    parts = (
        func.generate_series(0, cast(size - 1, Integer()).op("/")(part_bytes))
        .table_valued(column("part", BigInteger()))
        .render_derived()
        .lateral()
    )
    part_index = parts.c.part
    ordinary = ordered.c.family != "native_metadata"
    inline_fragment = func.jsonb_build_object(
        "kind",
        events.c.kind,
        "value",
        events.c.value,
        "prefix",
        events.c.prefix,
    )
    ord_ = ordered.c.position
    output = union_all(
        _output(
            -1,
            array((), type_=BigInteger()),
            _event(
                "selection_metadata",
                selected_count=select(func.count()).select_from(selected).scalar_subquery(),
                membership_sha256=membership,
            ),
        ),
        _output(
            0,
            _path(selected.c.ordinal, -1),
            _event(
                "record_start",
                pointer=selected.c.pointer,
                record_id=native.nodes.c.record_id,
                ordinal=selected.c.ordinal,
                parent_pointer=selected.c.parent_pointer,
                section_pointer=selected.c.section_pointer,
                label=selected.c.label,
                role="selected",
            ),
            source=selected.join(native.nodes, selected.c.pointer == native.nodes.c.native_address),
        ),
        _output(0, events.c.path, _event("native_fragment", native=inline_fragment)),
        _output(0, _path(selected.c.ordinal, 3), _event("record_end", pointer=selected.c.pointer)),
        _output(
            1,
            _path(access.c.ordinal),
            _event(
                "context",
                kind="ancestor",
                pointer=access.c.pointer,
                ordinal=access.c.ordinal,
                parent_pointer=access.c.parent_pointer,
                label=access.c.label,
                name=access.c.native_json["name"],
            ),
        ).where(access.c.pointer.in_(select(ancestors.c.pointer))),
        _output(
            2,
            _path(func.row_number().over(order_by=(region.c.pointer, region.c.region_index))),
            _event(
                "context",
                kind="frame",
                body=func.to_jsonb(region.table_valued(), type_=JSONB())
                .op("-", precedence=7, return_type=JSONB())("product_id")
                .op("-", precedence=7, return_type=JSONB())("revision_id"),
            ),
            source=region.join(published, placed(region)),
        ).where(region.c.pointer.in_(selected_pointers)),
        _output(
            3,
            _path(ord_, 0),
            _event(
                case((ordinary, "companion_start"), else_="companion_native_start"),
                family=ordered.c.family,
                local_id=ordered.c.local_id,
                ordinal=ordered.c.ordinal,
            ),
        ),
        _output(
            3,
            _path(ord_, 1, part_index),
            _event(
                "scalar_part",
                part=part_index,
                encoding="base64",
                value=func.encode(
                    func.substr(
                        _utf8(payload), cast(part_index * part_bytes + 1, Integer()), part_bytes
                    ),
                    "base64",
                ),
                final=(part_index + 1) * part_bytes >= size,
            ),
            source=ordered.join(parts, true()),
        ).where(ordinary),
        _output(
            3,
            _path(ord_, 2),
            _event(
                "companion_end",
                byte_length=size,
                sha256=func.encode(func.sha256(_utf8(payload)), "hex"),
            ),
        ).where(ordinary),
        _output(
            3,
            _path(
                ord_,
                1,
                func.row_number().over(
                    partition_by=ord_,
                    order_by=(
                        metadata_events.c.phase,
                        metadata_events.c.field_name.collate("C"),
                        metadata_events.c.subphase,
                        metadata_events.c.part_ordinal,
                    ),
                ),
            ),
            _event("companion_native_fragment", fragment=metadata_events.c.event),
            source=metadata_events.join(
                ordered,
                and_(~ordinary, ordered.c.local_id == metadata_events.c.local_id),
            ),
        ),
        _output(3, _path(ord_, 2), _event("companion_native_end"), source=ordered).where(~ordinary),
        _output(
            4,
            _path(func.row_number().over(order_by=cast(outside.c.body, Text()))),
            _event(
                "outside_reference",
                body=outside.c.body,
            ),
        ),
    ).subquery("output")
    return select(output.c.event).order_by(output.c.phase, output.c.path)


def selected_source_reader_programs(
    *, target_metadata: MetaData | None = None, pdf_domain=None
) -> tuple[ProgramDeclaration, ...]:
    from .metadata import get_metadata
    from .pdf_contracts import trusted_pdf_context

    model = get_metadata() if target_metadata is None else target_metadata
    domain = trusted_pdf_context().domain if pdf_domain is None else pdf_domain
    declaration = yaml.safe_load(domain.source("logical/selected_source").content)
    profile = json.loads(declaration["annotations"]["selected-source"])
    (membership,) = declaration["enums"]["SourceMembership"]["permissible_values"]
    names = (
        "p_project",
        "p_demand",
        "p_read",
        "p_use",
        "p_product",
        "p_derivation",
        "p_section",
        "p_membership",
        "p_policy",
    )
    values = tuple(core_variable(name, Text()) for name in names)
    section, membership_value, policy = values[-3:]
    placement = model.tables["ops.pdf_published_revision"]
    pin = (
        func.ops.require_published_companion_pin(*values[:6])
        .table_valued(*(column(field.name, field.type) for field in placement.c))
        .alias("pinned")
    )
    access = model.tables["kb.pdf_record_access"]
    build = core_variable("revision", placement.c.build_id.type, "build_id")
    name = "read_pdf_selected_source_events"
    result = pg_type("jsonb")
    result.setof = True
    routine = NativeRoutine(
        "ops",
        name,
        parameters=tuple(Parameter(key, pg_type("text")) for key in names),
        returns=result,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        volatility="volatile",
        body=Block(
            (
                If(
                    or_(
                        section.is_(None),
                        membership_value.is_distinct_from(membership),
                        policy.is_distinct_from(profile["context_policy"]),
                    ),
                    (Raise("invalid selected source selector/policy", "22023"),),
                ),
                SelectInto(
                    select(core_relation_row(Table("pinned", MetaData()))).select_from(pin),
                    ("revision",),
                    strict=True,
                ),
                If(
                    ~select(1)
                    .select_from(access)
                    .where(
                        access.c.product_id == build,
                        access.c.revision_id == build,
                        access.c.pointer == section,
                        access.c.label.in_(("section", "chapter")),
                    )
                    .exists(),
                    (Raise("selected source root is not a published section", "22023"),),
                ),
                ReturnQuery(_selected_events(model, "revision", section, profile["part_bytes"])),
            ),
            (Local("revision", placement),),
        ),
    )
    return (
        ProgramDeclaration(
            routine,
            "authoring/pdf-selected-source.sql",
            role_name("publisher"),
            NativeProgramAccess(purposes=("read", "write", "evaluate")),
        ),
    )


def selected_source_reader_sql(*, target_metadata: MetaData | None = None, pdf_domain=None) -> str:
    return native_sql_script(
        statement
        for program in selected_source_reader_programs(
            target_metadata=target_metadata, pdf_domain=pdf_domain
        )
        for statement in (
            program.routine.render(),
            native_privilege_sql(program.identity, "PUBLIC", grant=False),
            *(
                native_privilege_sql(program.identity, role, privilege.lower(), grant_option=option)
                for role, privilege, option in program.access.grants(program.owner)
            ),
        )
    )
