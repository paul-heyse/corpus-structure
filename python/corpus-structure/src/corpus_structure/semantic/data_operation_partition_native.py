"""Generated admission of declared partition bodies and placement commitments."""

from sqlalchemy import BigInteger, Boolean, Text, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSON, JSONB, aggregate_order_by, insert

from .native_program import Assign, ForQuery, If, Local, Perform, Raise, Return, SelectInto, Sql, core_variable, pg_type


def partition_admission_programs(model, output, routine):
    """Append private helpers before the product publication routine uses them."""
    partition = model.tables["kb.data_product_partition"]
    empty = cast(literal("[]"), JSONB())
    empty_object = cast(literal("{}"), JSONB())

    def obj(**fields):
        return func.jsonb_build_object(*(part for pair in fields.items() for part in pair), type_=JSONB())

    def tagged(tag, payload):
        return func.jsonb_build_array(tag, payload, type_=JSONB())

    def rows(value, name):
        return func.jsonb_array_elements(value).table_valued(column("value", JSONB())).render_derived(name=name)

    def entries(value, name):
        return func.jsonb_each(value).table_valued(column("key", Text()), column("value", JSONB())).render_derived(name=name)

    def identity(domain, value):
        return func.data.ddo_identity(domain, value, type_=Text())

    def reject(condition, message):
        return If(condition, (Raise(message, "23514"),))

    path_value = core_variable("p_value", JSONB())
    path_text = core_variable("p_path", Text())
    path_segment = core_variable("path_segment", Text())
    segments = func.unnest(func.string_to_array(path_text, ".")).table_valued(column("value", Text()), with_ordinality="ordinality").render_derived(name="path_segments")
    routine(output, "ddo_partition_field", (("p_value", "jsonb"), ("p_path", "text")), (
        ForQuery(("path_segment",), select(segments.c.value).order_by(segments.c.ordinality), (
            If(path_value[0].astext.is_distinct_from("mapping"), (Return(cast(literal(None), JSONB())),)),
            Assign("p_value", func.data.ddo_field(path_value, path_segment, type_=JSONB())),
        )), Return(path_value),
    ), (Local("path_segment", pg_type("text")),), returns="jsonb")

    key = core_variable("product_key", Text())
    specification, body, packets = (core_variable("p_body" if n == "body" else n, JSONB()) for n in ("specification", "body", "packets"))
    fresh = core_variable("fresh", Boolean())
    name, group_name = (core_variable(n, Text()) for n in ("name", "group_name"))
    declaration, packet, item, paths, group_digests, roots, placements, header = (
        core_variable("v_group_digests" if n == "group_digests" else n, JSONB()) for n in ("declaration", "packet", "item", "paths", "group_digests", "roots", "placements", "header")
    )
    count, item_count, ordinal = (core_variable("v_" + n, BigInteger()) for n in ("count", "item_count", "ordinal"))
    candidates = rows(packets, "candidate")
    declarations = entries(func.coalesce(specification["declarations"], empty_object), "declared")
    selected_packets = select(candidates.c.value).where(candidates.c.value["collection"].astext == name).order_by(func.convert_to(candidates.c.value["partition_key"].astext, "UTF8"))
    partition_body = core_variable("partition_body", JSONB())
    items = func.jsonb_array_elements(partition_body[1]).table_valued(column("value", JSONB()), with_ordinality="ordinality").render_derived(name="item_row")
    groups = entries(declaration["field_groups"], "group_row")
    path_rows = func.jsonb_array_elements_text(paths).table_valued(column("value", Text())).render_derived(name="path_row")
    field = func.ops.ddo_partition_field(items.c.value, path_rows.c.value, type_=JSONB())
    projected_item = select(func.coalesce(func.jsonb_agg(aggregate_order_by(
        func.jsonb_build_array(path_rows.c.value, field), func.convert_to(path_rows.c.value, "UTF8")
    )), empty)).select_from(path_rows).where(field.is_not(None)).correlate(items).scalar_subquery()
    projected_group = select(func.coalesce(func.jsonb_agg(aggregate_order_by(
        tagged("mapping", projected_item), items.c.ordinality
    )), empty)).select_from(items).scalar_subquery()
    group_steps = (
        Assign("v_group_digests", group_digests.op("||")(func.jsonb_build_object(
            group_name, identity("partition-group", tagged("sequence", projected_group))
        ))),
    )
    partition_steps = (
        Assign("partition_body", func.data.ddo_normalize(packet["body"], type_=JSONB())),
        reject(or_(partition_body[0].astext.is_distinct_from("sequence"), func.jsonb_typeof(partition_body[1]).is_distinct_from("array")), "partition body requires a sequence"),
        reject(identity("partition", partition_body).is_distinct_from(packet["partition_digest"].astext), "partition digest differs from body"),
        reject(or_(cast(packet["ordinal"].astext, BigInteger()) < 0, cast(packet["placement"]["start"].astext, BigInteger()) < 0, cast(packet["placement"]["end"].astext, BigInteger()) < cast(packet["placement"]["start"].astext, BigInteger())), "invalid partition placement or order"),
        ForQuery(("item",), select(items.c.value), (
            reject(or_(
                func.public.json_matches_schema(cast(specification["schemas"][name]["meaning_schema"], JSON()), cast(item, JSON())).is_not(True),
                func.public.json_matches_schema(cast(specification["schemas"][name]["body_schema"], JSON()), cast(func.data.ddo_json(item), JSON())).is_not(True),
            ), "partition item violates its declared schema"),
        )),
        Assign("v_group_digests", empty_object),
        ForQuery(("group_name", "paths"), select(groups.c.key, groups.c.value), group_steps),
        Assign("v_ordinal", cast(packet["ordinal"].astext, BigInteger())),
        If(fresh, (Sql(insert(partition).values(
            product_id=key, collection=name, partition_key=packet["partition_key"].astext,
            ordinal=ordinal, partition_digest=packet["partition_digest"].astext,
            item_count=func.jsonb_array_length(partition_body[1]), group_digests=group_digests,
            placement=packet["placement"], body=partition_body,
        )),)),
        reject(~select(1).select_from(partition).where(
            partition.c.product_id == key, partition.c.collection == name,
            partition.c.partition_key == packet["partition_key"].astext,
            partition.c.ordinal == ordinal,
            partition.c.partition_digest == packet["partition_digest"].astext,
            partition.c.item_count == func.jsonb_array_length(partition_body[1]),
            partition.c.group_digests == group_digests,
            partition.c.placement == packet["placement"], partition.c.body == partition_body,
        ).exists(), "partition replay differs from admitted content"),
        Assign("v_count", count + 1), Assign("v_item_count", item_count + func.jsonb_array_length(partition_body[1])),
    )
    duplicate_key = select(1).select_from(candidates).group_by(candidates.c.value["collection"], candidates.c.value["partition_key"]).having(func.count() > 1).exists()
    duplicate_ordinal = select(1).select_from(candidates).group_by(candidates.c.value["collection"], candidates.c.value["ordinal"]).having(func.count() > 1).exists()
    routine(output, "ddo_install_product_partitions", (("product_key", "text"), ("specification", "jsonb"), ("p_body", "jsonb"), ("packets", "jsonb"), ("fresh", "boolean")), (
        reject(func.jsonb_typeof(packets).is_distinct_from("array"), "partitions must be an array"),
        reject(or_(duplicate_key, duplicate_ordinal), "duplicate partition key or ordinal"),
        reject(select(1).select_from(candidates).where(~func.coalesce(specification["declarations"], empty_object).has_key(candidates.c.value["collection"].astext)).exists(), "undeclared partition collection"),
        ForQuery(("name", "declaration"), select(declarations.c.key, declarations.c.value), (
            If(declaration["unit"].astext == "partitioned", (
                Assign("roots", empty), Assign("placements", empty), Assign("v_count", literal(0)), Assign("v_item_count", literal(0)),
                ForQuery(("packet",), selected_packets, partition_steps),
                Assign("roots", select(func.coalesce(func.jsonb_agg(aggregate_order_by(func.jsonb_build_array(candidates.c.value["partition_key"], candidates.c.value["partition_digest"]), func.convert_to(candidates.c.value["partition_key"].astext, "UTF8"))), empty)).select_from(candidates).where(candidates.c.value["collection"].astext == name).scalar_subquery()),
                Assign("placements", tagged("sequence", select(func.coalesce(func.jsonb_agg(aggregate_order_by(tagged("sequence", func.jsonb_build_array(
                    tagged("string", candidates.c.value["partition_key"].astext),
                    tagged("integer", candidates.c.value["ordinal"].astext),
                    tagged("integer", candidates.c.value["placement"]["start"].astext),
                    tagged("integer", candidates.c.value["placement"]["end"].astext),
                )), func.convert_to(candidates.c.value["partition_key"].astext, "UTF8"))), empty)).select_from(candidates).where(candidates.c.value["collection"].astext == name).scalar_subquery())),
                Assign("header", func.data.ddo_json(func.data.ddo_field(body, name), type_=JSONB())),
                reject(header.is_distinct_from(obj(root=identity("partition-root", func.data.ddo_json_meaning(roots)), placement_root=identity("partition-placement", placements), partition_count=count, item_count=item_count)), "partition collection header differs from bodies"),
                reject(select(func.coalesce(func.max(partition.c.ordinal), -1)).where(partition.c.product_id == key, partition.c.collection == name).scalar_subquery() != count - 1, "partition ordinal gap or replay population mismatch"),
            )),
        )),
        reject(select(func.count()).select_from(partition).where(partition.c.product_id == key).scalar_subquery() != func.jsonb_array_length(packets), "partition population mismatch"),
        Return(),
    ), (
        *(Local(n, pg_type("text")) for n in ("name", "group_name")),
        *(Local("v_group_digests" if n == "group_digests" else n, pg_type("jsonb")) for n in ("declaration", "packet", "item", "paths", "group_digests", "roots", "placements", "header", "partition_body")),
        *(Local("v_" + n, pg_type("bigint")) for n in ("count", "item_count", "ordinal")),
    ), returns="void")


    product = model.tables["kb.data_product"]
    acquired_project = core_variable("acquired_project", Text())
    collection = core_variable("collection_name", Text())
    partition_key = core_variable("p_partition_key", Text())
    kind_contract = core_variable("kind_contract", Text())
    result = core_variable("result", JSONB())
    routine(output, "ddo_acquired_product_partition", (("product_key", "text"), ("acquired_project", "text"), ("collection_name", "text"), ("p_partition_key", "text")), (
        SelectInto(select(product.c.kind_contract).where(product.c.id == key, product.c.project_id == acquired_project), ("kind_contract",), strict=True),
        Perform(func.ops.ddo_kind_access(kind_contract)),
        SelectInto(select(obj(
            partition_key=partition.c.partition_key, ordinal=partition.c.ordinal,
            partition_digest=partition.c.partition_digest, item_count=partition.c.item_count,
            group_digests=partition.c.group_digests, placement=partition.c.placement, body=partition.c.body,
        )).where(partition.c.product_id == key, partition.c.collection == collection, partition.c.partition_key == partition_key), ("result",), strict=True),
        Return(result),
    ), (Local("kind_contract", pg_type("text")), Local("result", pg_type("jsonb"))), returns="jsonb")
