"""Generate publication-time closure for declared semantic reference slots."""

from sqlalchemy import Integer, Text, and_, case, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array

from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    SelectInto,
    core_variable,
    pg_type,
)


def _rows(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()), with_ordinality="ordinality")
        .render_derived(name=name)
    )


def _reject(condition, detail):
    return If(condition, (Raise(detail, "23514"),))


def reference_native_programs(model):
    """Check actual closure before sealing completion under its bound input manifest."""
    definitions = model.tables["sem.data_operation_definition"]
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    kinds = model.tables["sem.data_kind_contract"]
    completion, target, output, ref, part = (
        core_variable(name, JSONB())
        for name in ("completion", "target", "output", "ref", "partition_body")
    )
    role, product, bound_member = (
        core_variable(name, Text()) for name in ("target_role", "target_product", "bound_member")
    )
    count = core_variable("target_count", Integer())
    partition_indexes, address_index = (
        core_variable(name, JSONB()) for name in ("partition_indexes", "address_index")
    )
    request = model.tables["ops.data_request"]

    def request_field(name):
        return core_variable("r", request.c[name].type, name)

    def decoded(value):
        return func.data.ddo_json(func.data.ddo_normalize(value), type_=JSONB())

    empty = cast(literal("[]"), JSONB())
    empty_index = cast(literal("{}"), JSONB())
    targets = _rows(
        func.coalesce(definitions.c.support_contract["reference_targets"], empty),
        "reference_targets",
    )
    input_roles = _rows(definitions.c.input_roles, "reference_input_roles")
    admitted_contracts = (
        select(input_roles.c.value["accepted_kind_contracts"])
        .select_from(input_roles)
        .where(
            input_roles.c.value["name"].astext == targets.c.value["input_role"].astext,
            input_roles.c.value["kind"].astext == targets.c.value["input_kind"].astext,
        )
        .correlate(definitions, targets)
        .scalar_subquery()
    )
    contracts = core_variable("target_contracts", JSONB())
    outputs = _rows(completion["outputs"], "reference_outputs")
    request_inputs = request_field("binding")["inputs"]
    selected_bindings = core_variable("selected_bindings", JSONB())
    bindings = _rows(selected_bindings, "reference_inputs")
    bound = bindings.c.value
    variant = target["variant"].astext
    occurrence = target["occurrence_field"].astext
    binding_label = target["occurrence_binding"].astext == "true"
    ledger_position = target["occurrence_position"].astext == "true"
    uses_occurrence = or_(occurrence.is_not(None), binding_label, ledger_position)
    captured_roles = core_variable("captured_roles", JSONB())
    ledger = func.ops.ddo_derivation_input_positions(request_inputs, captured_roles).table_valued(
        column("input_record", JSONB()), column("physical_position", Integer())
    )
    positioned_bindings = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    ledger.c.input_record.op("||")(
                        func.jsonb_build_object("reference_position", ledger.c.physical_position)
                    )
                ),
                empty,
            )
        )
        .where(ledger.c.input_record["role"].astext == role)
        .scalar_subquery()
    )
    member_id = ref["member_id"].astext
    collection = ref["collection"].astext
    role_paths = array(["variant", "role"], type_=Text())
    occurrence_paths = case(
        (uses_occurrence, array(["occurrence"], type_=Text())),
        else_=array([], type_=Text()),
    )
    fields = role_paths.concat(occurrence_paths).concat(
        case(
            (variant == "member", array(["member_id"], type_=Text())),
            (
                variant == "partition-item",
                array(["collection", "partition_key", "item_key"], type_=Text()),
            ),
            else_=array([], type_=Text()),
        )
    )

    select_input = (
        select(
            func.coalesce(func.sum(cast(bound["multiplicity"].astext, Integer())), func.count()),
            func.min(products.c.id),
            func.min(bound["member_id"].astext),
        )
        .select_from(
            bindings.join(products, products.c.id == bound["product_id"].astext)
            .outerjoin(
                members,
                and_(
                    members.c.product_id == products.c.id,
                    members.c.member_id == bound["member_id"].astext,
                ),
            )
            .join(
                kinds,
                kinds.c.kind_contract
                == func.coalesce(members.c.kind_contract, products.c.kind_contract),
            )
        )
        .where(
            bound["role"].astext == role,
            products.c.project_id == request_field("project_id"),
            contracts.bool_op("?")(kinds.c.kind_contract),
            or_(bound["member_id"].astext.is_(None), members.c.member_id.is_not(None)),
            case(
                (binding_label, bound["occurrence_label"].astext == ref["occurrence"].astext),
                (
                    ledger_position,
                    bound["reference_position"].astext == ref["occurrence"].astext,
                ),
                (occurrence.is_(None), literal(True)),
                else_=decoded(func.coalesce(members.c.body, products.c.canonical_body)).op(
                    "#>>", return_type=Text()
                )(func.data.ddo_witness_path(occurrence))
                == ref["occurrence"].astext,
            ),
        )
    )
    member_exists = (
        select(1)
        .select_from(members)
        .where(members.c.product_id == product, members.c.member_id == member_id)
        .exists()
    )
    paths = _rows(
        kinds.c.collections["declarations"][collection]["address"], "reference_address_paths"
    )
    items = _rows(part[1], "addressed_items")
    field = func.ops.ddo_partition_field(items.c.value, paths.c.value[()].astext, type_=JSONB())
    key = (
        select(func.jsonb_agg(aggregate_order_by(func.data.ddo_json(field), paths.c.ordinality)))
        .select_from(
            products.join(kinds, kinds.c.kind_contract == products.c.kind_contract).join(
                paths, literal(True)
            )
        )
        .where(products.c.id == product)
        .correlate(items)
        .scalar_subquery()
    )
    addressed = select(cast(key, Text()).label("address")).select_from(items).subquery()
    multiplicities = (
        select(addressed.c.address, func.count().label("multiplicity"))
        .group_by(addressed.c.address)
        .subquery()
    )
    partition_index = select(
        func.jsonb_object_agg(multiplicities.c.address, multiplicities.c.multiplicity)
    ).scalar_subquery()
    partition_address = cast(
        func.jsonb_build_array(product, collection, ref["partition_key"].astext), Text()
    )
    keys = _rows(ref["item_key"], "submitted_address_fields")
    key_part = keys.c.value
    part_kind = key_part["kind"].astext
    text_part, integer_part = key_part["text"], key_part["integer"]
    parsed_part = case((part_kind == "text", text_part), else_=integer_part)
    submitted_key = (
        select(func.jsonb_agg(aggregate_order_by(parsed_part, keys.c.ordinality), type_=JSONB()))
        .select_from(keys)
        .scalar_subquery()
    )
    bad_key_field = (
        select(1)
        .select_from(keys)
        .where(
            or_(
                and_(
                    key_part == func.jsonb_build_object("kind", "text", "text", text_part),
                    func.jsonb_typeof(text_part) == "string",
                    text_part.astext != "",
                ),
                and_(
                    key_part == func.jsonb_build_object("kind", "integer", "integer", integer_part),
                    func.jsonb_typeof(integer_part) == "number",
                    integer_part.astext.regexp_match(r"^-?[0-9]+$"),
                ),
            ).is_distinct_from(True)
        )
        .exists()
    )
    detail = func.format(
        "semantic reference at output %s path %s does not resolve address %s",
        target["output_role"].astext,
        target["path"].astext,
        ref,
    )
    check_reference = (
        Perform(func.ops.ddo_fields(ref, fields)),
        _reject(
            or_(
                ref["variant"].astext.is_distinct_from(variant),
                ref["role"].astext.is_distinct_from(role),
                func.jsonb_typeof(ref["variant"]).is_distinct_from("string"),
                func.jsonb_typeof(ref["role"]).is_distinct_from("string"),
                and_(
                    uses_occurrence,
                    or_(
                        func.jsonb_typeof(ref["occurrence"]).is_distinct_from("string"),
                        ref["occurrence"].astext == "",
                    ),
                ),
            ),
            detail,
        ),
        SelectInto(select_input, ("target_count", "target_product", "bound_member")),
        _reject(count != 1, detail),
        _reject(and_(bound_member.is_not(None), bound_member.is_distinct_from(member_id)), detail),
        If(
            variant == "member",
            (
                _reject(
                    or_(
                        func.jsonb_typeof(ref["member_id"]).is_distinct_from("string"),
                        ~member_exists,
                    ),
                    detail,
                ),
                Perform(
                    select(
                        func.ops.ddo_admitted_body_access(members.c.kind_contract, members.c.body)
                    )
                    .where(members.c.product_id == product, members.c.member_id == member_id)
                    .scalar_subquery()
                ),
            ),
        ),
        If(
            variant == "partition-item",
            (
                _reject(
                    or_(
                        collection.is_distinct_from(target["collection"].astext),
                        func.jsonb_typeof(ref["collection"]).is_distinct_from("string"),
                        func.jsonb_typeof(ref["partition_key"]).is_distinct_from("string"),
                        ref["partition_key"].astext == "",
                        func.jsonb_typeof(ref["item_key"]).is_distinct_from("array"),
                    ),
                    detail,
                ),
                _reject(or_(func.jsonb_array_length(ref["item_key"]) == 0, bad_key_field), detail),
                # The request's authorization and exact input occurrence are checked
                # above even when this invocation already indexed the immutable body.
                Assign("address_index", partition_indexes[partition_address]),
                If(
                    address_index.is_(None),
                    (
                        Assign(
                            "partition_body",
                            func.ops.ddo_acquired_product_partition(
                                product,
                                request_field("project_id"),
                                collection,
                                ref["partition_key"].astext,
                                type_=JSONB(),
                            )["body"],
                        ),
                        Assign("address_index", func.coalesce(partition_index, empty_index)),
                        Assign(
                            "partition_indexes",
                            partition_indexes.op("||")(
                                func.jsonb_build_object(partition_address, address_index)
                            ),
                        ),
                    ),
                ),
                _reject(
                    address_index[cast(submitted_key, Text())].astext.is_distinct_from("1"),
                    detail,
                ),
            ),
        ),
    )
    output_members = _rows(output["product"]["members"], "output_member_packets")
    output_body = case(
        (
            output["member_id"].astext.is_not(None),
            select(output_members.c.value["body"])
            .where(output_members.c.value["member_id"].astext == output["member_id"].astext)
            .scalar_subquery(),
        ),
        else_=output["product"]["body"],
    )
    output_partitions = _rows(output["product"]["partitions"], "output_partition_packets")
    partition_items = _rows(
        decoded(output_partitions.c.value["body"]), "output_partition_items"
    ).lateral()

    def at_path(body, name):
        return (
            func.data.ddo_witness_records(body, target["path"].astext)
            .table_valued(column("value", JSONB()), with_ordinality="ordinality")
            .render_derived(name=name)
        )

    header_refs = at_path(decoded(output_body), "header_refs")
    item_refs = at_path(partition_items.c.value, "item_refs").lateral()
    check_output = If(
        target["output_collection"].astext.is_(None),
        (
            ForQuery(
                ("ref",),
                select(header_refs.c.value).order_by(header_refs.c.ordinality),
                check_reference,
            ),
        ),
        (
            ForQuery(
                ("ref",),
                select(item_refs.c.value)
                .select_from(
                    output_partitions.join(partition_items, literal(True)).join(
                        item_refs, literal(True)
                    )
                )
                .where(
                    output_partitions.c.value["collection"].astext
                    == target["output_collection"].astext
                )
                .order_by(
                    output_partitions.c.ordinality,
                    partition_items.c.ordinality,
                    item_refs.c.ordinality,
                ),
                check_reference,
            ),
        ),
    )
    return (
        NativeRoutine(
            "ops",
            "ddo_assert_output_references",
            (
                Parameter("r", pg_type("ops", "data_request")),
                Parameter("completion", pg_type("jsonb")),
            ),
            pg_type("void"),
            Block(
                (
                    Perform(
                        func.ops.ddo_binding_body_access(
                            request_field("binding"), request_field("project_id")
                        )
                    ),
                    ForQuery(
                        ("target", "target_contracts", "captured_roles"),
                        select(targets.c.value, admitted_contracts, definitions.c.input_roles)
                        .select_from(definitions.join(targets, literal(True)))
                        .where(
                            definitions.c.release_id == request_field("release_id"),
                            definitions.c.operation_id == request_field("operation_id"),
                        )
                        .order_by(targets.c.ordinality),
                        (
                            Assign("target_role", target["input_role"].astext),
                            Assign(
                                "selected_bindings",
                                case((ledger_position, positioned_bindings), else_=request_inputs),
                            ),
                            ForQuery(
                                ("output",),
                                select(outputs.c.value)
                                .where(
                                    outputs.c.value["role"].astext == target["output_role"].astext
                                )
                                .order_by(outputs.c.ordinality),
                                (check_output,),
                            ),
                        ),
                    ),
                ),
                (
                    *(
                        Local(name, pg_type("jsonb"))
                        for name in (
                            "target",
                            "target_contracts",
                            "captured_roles",
                            "selected_bindings",
                            "output",
                            "ref",
                            "partition_body",
                            "address_index",
                        )
                    ),
                    Local("partition_indexes", pg_type("jsonb"), empty_index),
                    *(
                        Local(name, pg_type("text"))
                        for name in ("target_role", "target_product", "bound_member")
                    ),
                    Local("target_count", pg_type("int4")),
                ),
            ),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            volatility="stable",
        ),
    )
