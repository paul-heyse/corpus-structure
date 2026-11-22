"""Generated PostgreSQL evaluation and establishment of declared collection rules."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
    Numeric,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    null,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, aggregate_order_by, insert

from .data_operation_value_native import json_observation_identity
from .native_program import (
    Assign,
    ForQuery,
    GetRowCount,
    If,
    Local,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    pg_type,
)


def _empty():
    return cast(literal("[]"), JSONB())


def _rows(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()), with_ordinality="ordinality")
        .render_derived(name=name)
    )


def _reject(condition, message):
    return If(condition, (Raise(message, "23514"),))


def _routine(output, name, params, statements, locals_=(), *, returns="jsonb"):
    from .data_product_admission_native import _routine as product_routine

    product_routine(output, name, params, statements, locals_, returns=returns)


_SPEC = (
    ("p_spec", "jsonb"),
    ("p_product", "text"),
    ("p_partition", "text"),
    ("p_target", "text"),
    ("p_target_partition", "text"),
)


def _variables():
    spec = core_variable("p_spec", JSONB())
    product, partition, target, target_partition = (
        core_variable(name, Text())
        for name in ("p_product", "p_partition", "p_target", "p_target_partition")
    )
    return spec, product, partition, target, target_partition


def rule_premise_specification(specification):
    """The complete projection contract read by the native premise evaluator.

    Checker identity, policy determinants and input-role observations govern
    their own authorities; they do not alter these output facts.
    """
    return func.jsonb_build_object(
        *(
            item
            for field in ("scope", "collection", "reads", "form", "checker")
            for item in (field, specification[field])
        ),
        "parameters",
        func.jsonb_build_object(
            *(
                item
                for field in ("inline_collection", "target_collection")
                for item in (field, specification["parameters"][field])
            )
        ),
        type_=JSONB(),
    )


def _collection_scope(table, product_id, collection, partition_key):
    return and_(
        table.c.product_id == product_id,
        table.c.collection == collection,
        or_(partition_key.is_(None), table.c.partition_key == partition_key),
    )


def _inline_rule_items(product, product_id, collection, name):
    tagged = func.ops.ddo_partition_field(product.c.canonical_body, collection, type_=JSONB())
    items = _rows(tagged[1], name).lateral()
    return (
        select(
            items.c.value.label("body"),
            items.c.ordinality.label("item"),
            literal(0).label("part_order"),
            cast(null(), Text()).label("key"),
            cast(null(), JSONB()).label("placement"),
        )
        .select_from(product.join(items, true()))
        .where(product.c.id == product_id)
    )


def _premise(model, output):
    product = model.tables["kb.data_product"]
    partitions = model.tables["kb.data_product_partition"]
    supplied_spec, product_id, partition_key, target_id, target_key = _variables()
    spec = core_variable("v_projection", JSONB())
    scope = spec["scope"].astext
    reads = _rows(spec["reads"], "read_paths")
    groups = _rows(reads.c.value["groups"], "read_groups")
    path = reads.c.value["path"].astext
    side = reads.c.value["side"].astext
    group = groups.c.value[()].astext

    def facts(pid, collection, key, side_name):
        selected = _collection_scope(partitions, pid, collection, key)
        whole = (
            select(1).select_from(reads).where(side == side_name, path == "$all").exists()
            | (spec["checker"].astext == "producer")
            & ~select(1).select_from(reads).where(side == side_name).exists()
        )
        ungrouped = and_(
            side == side_name,
            ~path.startswith("$"),
            func.jsonb_array_length(reads.c.value["groups"]) == 0,
        )
        tagged_items = _rows(partitions.c.body[1], "premise_items")
        path_value = func.ops.ddo_partition_field(tagged_items.c.value, path, type_=JSONB())
        observed_values = (
            select(
                func.coalesce(
                    func.jsonb_agg(aggregate_order_by(path_value, tagged_items.c.ordinality)),
                    _empty(),
                )
            )
            .select_from(tagged_items)
            .correlate(reads, partitions)
            .scalar_subquery()
        )
        exact_paths = (
            select(func.jsonb_object_agg(path, observed_values))
            .select_from(reads)
            .where(ungrouped)
            .correlate(partitions)
            .scalar_subquery()
        )
        selected_groups = (
            select(
                group.label("name"),
                partitions.c.group_digests[group].label("value"),
            )
            .select_from(reads.join(groups, true()))
            .where(side == side_name)
            .distinct()
            .correlate(partitions)
            .subquery("selected_read_group")
        )
        all_groups = select(
            func.jsonb_object_agg(selected_groups.c.name, selected_groups.c.value)
        ).scalar_subquery()

        def notices(placement_path):
            return (
                select(1)
                .select_from(reads)
                .where(
                    side == side_name,
                    path == placement_path,
                )
                .exists()
            )

        payload = func.jsonb_build_array(
            case((key.is_(None), partitions.c.partition_key)),
            case(
                (
                    and_(
                        scope == "product",
                        or_(whole, spec["form"].astext.in_(("ordered_by", "dense_ordinal"))),
                    ),
                    partitions.c.ordinal,
                )
            ),
            case((or_(whole, notices("$placement.start")), partitions.c.placement["start"])),
            case((or_(whole, notices("$placement.end")), partitions.c.placement["end"])),
            case((whole, func.to_jsonb(partitions.c.partition_digest))),
            all_groups,
            exact_paths,
        )
        return (
            select(
                func.coalesce(
                    func.jsonb_agg(
                        aggregate_order_by(
                            payload,
                            func.convert_to(partitions.c.partition_key, "UTF8"),
                        )
                    ),
                    _empty(),
                )
            )
            .where(selected)
            .scalar_subquery(),
            select(1).select_from(partitions).where(selected).exists(),
        )

    source_facts, source_found = facts(
        product_id, spec["collection"].astext, partition_key, "source"
    )
    target_facts, target_found = facts(
        target_id, spec["parameters"]["target_collection"].astext, target_key, "target"
    )
    body_value = func.ops.ddo_partition_field(product.c.canonical_body, path, type_=JSONB())
    product_paths = (
        select(func.jsonb_object_agg(path, body_value))
        .select_from(reads)
        .where(side == "source", ~path.startswith("$"))
        .correlate(product)
        .scalar_subquery()
    )
    product_wide = select(1).select_from(reads).where(side == "source", path == "$all").exists()
    product_facts = (
        select(
            func.jsonb_build_array(
                case((product_wide, product.c.body_digest)),
                product_paths,
            )
        )
        .select_from(product)
        .where(product.c.id == product_id)
        .scalar_subquery()
    )
    inline_items = _inline_rule_items(
        product, product_id, spec["collection"].astext, "inline_rule_premise_items"
    ).subquery()
    inline_path_value = func.ops.ddo_partition_field(inline_items.c.body, path, type_=JSONB())
    item_facts = (
        select(func.jsonb_object_agg(path, inline_path_value))
        .select_from(reads)
        .where(side == "source")
        .correlate(inline_items)
        .scalar_subquery()
    )
    inline_observations = select(item_facts.label("observed")).select_from(inline_items).subquery()
    observed = inline_observations.c.observed
    inline_facts = (
        select(func.coalesce(func.jsonb_agg(aggregate_order_by(observed, observed)), _empty()))
        .select_from(inline_observations)
        .scalar_subquery()
    )

    def pins(name):
        return (
            select(1)
            .select_from(reads)
            .where(
                side == "source",
                path.in_((name, "$all")),
            )
            .exists()
        )

    pinned_source = (
        select(
            func.jsonb_build_array(
                case((pins("$source"), product.c.original_source)),
                case((pins("$analyzed_scope"), product.c.analyzed_scope)),
            )
        )
        .where(product.c.id == product_id)
        .scalar_subquery()
    )
    datum = func.jsonb_build_array(
        scope,
        case(
            (spec["collection"].astext.is_(None), product_facts),
            (
                spec["parameters"]["inline_collection"] == cast(literal("true"), JSONB()),
                inline_facts,
            ),
            else_=source_facts,
        ),
        case((scope == "partition-pair", target_facts)),
        case((spec["checker"].astext == "producer", pinned_source)),
    )
    _routine(
        output,
        "ddo_rule_premise",
        _SPEC,
        (
            Assign("v_projection", rule_premise_specification(supplied_spec)),
            _reject(
                or_(
                    scope.is_(None),
                    ~scope.in_(("product", "partition", "partition-pair")),
                    and_(
                        partition_key.is_(None),
                        ~select(1).select_from(product).where(product.c.id == product_id).exists(),
                    ),
                    (scope == "product") != partition_key.is_(None),
                    (scope == "partition-pair") != target_id.is_not(None),
                    target_id.is_not(None) != target_key.is_not(None),
                    and_(partition_key.is_not(None), ~source_found),
                    and_(scope == "partition-pair", ~target_found),
                ),
                "rule scope does not identify admitted partition facts",
            ),
            Return(json_observation_identity("rule-premise", datum)),
        ),
        (Local("v_projection", pg_type("jsonb")),),
        returns="text",
    )


def _predicate(output):
    expression = core_variable("p_expression", JSONB())
    item = core_variable("p_item", JSONB())
    args = _rows(expression["args"], "predicate_args")
    function = expression["call"].astext
    op = expression["op"].astext

    def evaluate(node):
        return func.ops.ddo_rule_expression(node, item, type_=JSONB())

    def arg(index):
        return evaluate(expression["args"][index])

    def plain(value):
        return case((value == cast(literal("null"), JSONB()), cast(null(), JSONB())), else_=value)

    first, second, third = (plain(arg(i)) for i in range(3))

    def scalar(value):
        return value[()].astext

    def boolean(value):
        return cast(scalar(value), Boolean())

    def json(value):
        return cast(func.to_jsonb(value), JSONB())

    selected = plain(evaluate(args.c.value))
    outcomes = select(boolean(selected).label("value")).select_from(args).subquery()
    choices = (
        select(selected.label("value")).select_from(args).where(args.c.ordinality > 1).subquery()
    )
    inclusion = case(
        (select(1).select_from(choices).where(choices.c.value == first).exists(), True),
        (
            or_(
                first.is_(None),
                select(1).select_from(choices).where(choices.c.value.is_(None)).exists(),
            ),
            null(),
        ),
        else_=False,
    )

    def logical(all_values):
        terminal = (
            select(1).select_from(outcomes).where(outcomes.c.value.is_(not all_values)).exists()
        )
        unknown = select(1).select_from(outcomes).where(outcomes.c.value.is_(None)).exists()
        return case((terminal, not all_values), (unknown, null()), else_=all_values)

    def binary_array(value):
        return cast(scalar(value), BYTEA())

    comparisons = {
        fld: compare(first, second)
        for fld, compare in (
            ("eq", lambda a, b: a == b),
            ("ne", lambda a, b: a != b),
            ("gt", lambda a, b: a > b),
            ("lt", lambda a, b: a < b),
            ("ge", lambda a, b: a >= b),
            ("le", lambda a, b: a <= b),
            ("distinct", lambda a, b: a.is_distinct_from(b)),
            ("not_distinct", lambda a, b: a.is_not_distinct_from(b)),
        )
    }
    operators = {
        **{name: json(value) for name, value in comparisons.items()},
        "regex": json(scalar(first).bool_op("~")(scalar(second))),
        "like": json(scalar(first).like(scalar(second))),
        "concat": json(scalar(first).concat(scalar(second))),
        "json": first.op("->", return_type=JSONB())(scalar(second)),
        "json_text": json(first.op("->>", return_type=Text())(scalar(second))),
        "all": json(logical(True)),
        "any": json(logical(False)),
        "not": json(~boolean(first)),
        "is_null": json(first.is_(None)),
        "is_not_null": json(first.is_not(None)),
        "in": json(inclusion),
        "not_in": json(~inclusion),
        "between": json(first.between(second, third)),
        "case": case((boolean(first), second), else_=third),
    }
    calls = {
        "jsonb_typeof": json(func.jsonb_typeof(first)),
        "octet_length": json(func.octet_length(scalar(first))),
        "convert_to": json(func.convert_to(scalar(first), scalar(second))),
        "sha256": json(func.sha256(binary_array(first))),
        "encode": json(func.encode(binary_array(first), scalar(second))),
    }
    _routine(
        output,
        "ddo_rule_expression",
        (("p_expression", "jsonb"), ("p_item", "jsonb")),
        (
            If(expression.is_(None), (Return(cast(null(), JSONB())),)),
            If(
                expression.has_key("field"),
                (
                    Return(
                        func.data.ddo_json(
                            func.ops.ddo_partition_field(item, expression["field"].astext)
                        )
                    ),
                ),
            ),
            If(
                expression.has_key("cast"),
                (
                    Return(
                        case(
                            (
                                expression["cast"].astext == "text",
                                json(scalar(evaluate(expression["value"]))),
                            ),
                            else_=evaluate(expression["value"]),
                        )
                    ),
                ),
            ),
            If(expression.has_key("value"), (Return(expression["value"]),)),
            *(If(op == name, (Return(value),)) for name, value in operators.items()),
            *(If(function == name, (Return(value),)) for name, value in calls.items()),
            Raise("unsupported checked row expression", "23514"),
        ),
    )


def _evaluator(model, output):
    partitions = model.tables["kb.data_product_partition"]
    products = model.tables["kb.data_product"]
    spec, product_id, partition_key, target_id, target_key = _variables()
    params = spec["parameters"]
    label = spec["form"].astext

    def items(pid, collection, key, name):
        table = partitions.alias(name + "_partition")
        elements = _rows(table.c.body[1], name + "_items").lateral()
        return (
            select(
                elements.c.value.label("body"),
                elements.c.ordinality.label("item"),
                table.c.ordinal.label("part_order"),
                table.c.partition_key.label("key"),
                table.c.placement,
            )
            .select_from(table.join(elements, true()))
            .where(_collection_scope(table, pid, collection, key))
        )

    inline = (params["inline_collection"] == cast(literal("true"), JSONB())).is_(True)
    collection = spec["collection"].astext
    rows = (
        items(product_id, collection, partition_key, "source_rule_items")
        .where(~inline)
        .union_all(
            _inline_rule_items(products, product_id, collection, "inline_rule_items").where(inline)
        )
        .cte("source_rule_items")
    )
    paths = _rows(params["paths"], "rule_paths")
    group_paths = _rows(params["group_by"], "rule_group_paths")
    target_paths = _rows(params["target_paths"], "rule_target_paths")

    def field(body, path):
        return func.ops.ddo_partition_field(body, path, type_=JSONB())

    def value(row, path):
        return field(row.c.body, path)

    def tuple_key(row, members):
        typed = value(row, members.c.value[()].astext)
        return (
            select(
                case(
                    (
                        func.bool_and(typed.is_not(None)),
                        func.jsonb_agg(aggregate_order_by(typed, members.c.ordinality)),
                    ),
                    else_=cast(null(), JSONB()),
                )
            )
            .select_from(members)
            .correlate(row)
            .scalar_subquery()
        )

    order = (rows.c.part_order, rows.c.item)
    equality_keys = tuple_key(rows, paths)
    ordinal_group = tuple_key(rows, group_paths)
    annotated = select(
        rows.c.key,
        rows.c.item,
        rows.c.part_order,
        rows.c.body,
        equality_keys.label("values"),
        func.count().over(partition_by=equality_keys).label("duplicates"),
        func.lag(rows.c.body).over(order_by=order).label("previous"),
        func.row_number().over(partition_by=ordinal_group, order_by=order).label("rank"),
        ordinal_group.label("ordinal_group"),
        value(rows, params["path"].astext).label("ordinal_value"),
    ).subquery("ordinal_rule_rows")
    ordinal_value = annotated.c.ordinal_value
    path = paths.c.value[()].astext
    before, after = field(annotated.c.previous, path), value(annotated, path)
    first_difference = (
        select(
            case(
                (
                    before[0].astext == "string",
                    func.convert_to(before[1].astext, "UTF8")
                    > func.convert_to(after[1].astext, "UTF8"),
                ),
                (
                    before[0].astext.in_(("integer", "float", "decimal")),
                    cast(before[1].astext, Numeric()) > cast(after[1].astext, Numeric()),
                ),
                else_=before > after,
            )
        )
        .select_from(paths)
        .where(before.is_distinct_from(after))
        .order_by(paths.c.ordinality)
        .limit(1)
        .correlate(annotated)
        .scalar_subquery()
    )

    def numeric(path):
        return cast(value(rows, path)[1].astext, Numeric())

    lower = case(
        (
            params["coordinates"].astext == "placement",
            cast(rows.c.placement["start"].astext, Numeric()),
        ),
        else_=literal(0),
    )
    upper = case(
        (
            params["limit"].astext == "$placement.end",
            cast(rows.c.placement["end"].astext, Numeric()),
        ),
        (
            params["limit"].astext == "$placement.start",
            cast(rows.c.placement["start"].astext, Numeric()),
        ),
        else_=numeric(params["limit"].astext),
    )
    start, end = numeric(params["start"].astext), numeric(params["end"].astext)
    members = items(
        func.coalesce(target_id, product_id),
        params["target_collection"].astext,
        func.coalesce(target_key, partition_key),
        "target_rule_items",
    ).cte("target_rule_items")
    target_value = tuple_key(members, target_paths)
    unique_targets = (
        select(target_value.label("address"))
        .select_from(members)
        .group_by(target_value)
        .having(func.count() == 1)
        .subquery("unique_rule_targets")
    )
    reference_violation = ~(
        select(1)
        .select_from(unique_targets)
        .where(unique_targets.c.address == tuple_key(rows, paths))
        .correlate(rows)
        .exists()
    )
    candidate = {
        "unique": (annotated, or_(annotated.c["values"].is_(None), annotated.c.duplicates > 1)),
        "ordered_by": (
            annotated,
            or_(
                annotated.c["values"].is_(None),
                and_(annotated.c.previous.is_not(None), first_difference.is_(True)),
            ),
        ),
        "dense_ordinal": (
            annotated,
            or_(
                and_(params.has_key("group_by"), annotated.c.ordinal_group.is_(None)),
                ordinal_value[0].astext.is_distinct_from("integer"),
                cast(ordinal_value[1].astext, BigInteger()).is_distinct_from(
                    annotated.c.rank - 1 + cast(params["start"].astext, BigInteger())
                ),
            ),
        ),
        "span_within": (rows, and_(start >= lower, end >= start, end <= upper).is_not(True)),
        "refers_to": (rows, reference_violation),
        "predicate": (
            rows,
            func.ops.ddo_rule_expression(
                params["expression"], rows.c.body, type_=JSONB()
            ).is_distinct_from(cast(literal("true"), JSONB())),
        ),
    }
    steps: list[If | Raise] = []
    for form, (source, violation) in candidate.items():
        first = (
            select(func.jsonb_build_object("partition", source.c.key, "item", source.c.item))
            .select_from(source)
            .where(violation)
            .order_by(source.c.part_order, source.c.item)
            .limit(1)
            .scalar_subquery()
        )
        steps.append(If(label == form, (Return(first),)))
    steps.append(Raise("unsupported generated collection rule form", "23514"))
    _routine(output, "ddo_rule_violation", _SPEC, steps)


def _establish(model, output):
    proof = model.tables["kb.data_validity"]
    spec, product_id, partition_key, target_id, target_key = _variables()
    args = (spec, product_id, partition_key, target_id, target_key)
    premise = core_variable("v_premise", Text())
    violation = core_variable("v_violation", JSONB())
    fingerprint = spec["fingerprint"].astext
    _routine(
        output,
        "ddo_establish_rule",
        _SPEC,
        (
            _reject(
                spec["checker"].astext.is_distinct_from("admission"),
                "producer rule requires an authenticated attestation",
            ),
            Assign("v_premise", func.ops.ddo_rule_premise(*args, type_=Text())),
            If(
                select(1)
                .select_from(proof)
                .where(proof.c.rule_fingerprint == fingerprint, proof.c.premise == premise)
                .exists(),
                (Return(literal(0)),),
            ),
            Assign("v_violation", func.ops.ddo_rule_violation(*args, type_=JSONB())),
            _reject(
                violation.is_not(None),
                literal("collection rule ")
                + spec["id"].astext
                + " violated at "
                + cast(violation, Text()),
            ),
            Sql(
                insert(proof)
                .values(rule_fingerprint=fingerprint, premise=premise)
                .on_conflict_do_nothing()
            ),
            GetRowCount("v_inserted"),
            Return(cast(core_variable("v_inserted", BigInteger()), Integer())),
        ),
        (
            Local("v_premise", pg_type("text")),
            Local("v_violation", pg_type("jsonb")),
            Local("v_inserted", pg_type("bigint")),
        ),
        returns="int4",
    )


def _target_partition(model, output):
    partitions = model.tables["kb.data_product_partition"]
    spec, product_id, key, _, _ = _variables()
    target_path = spec["parameters"]["target_key"].astext
    items = _rows(partitions.c.body[1], "source_pair_keys").lateral()
    values = func.ops.ddo_partition_field(items.c.value, target_path, type_=JSONB())
    mapped = (
        select(case((values[0].astext == "string", values[1].astext)).label("target_key"))
        .select_from(partitions.join(items, true()))
        .where(_collection_scope(partitions, product_id, spec["collection"].astext, key))
        .distinct()
        .subquery("pair_targets")
    )
    _routine(
        output,
        "ddo_rule_target_partition",
        _SPEC[:3],
        (
            _reject(
                or_(key.is_(None), select(func.count()).select_from(mapped).scalar_subquery() != 1),
                "pair rule requires exactly one target partition key",
            ),
            SelectInto(select(mapped.c.target_key), ("v_target_key",), strict=True),
            _reject(
                core_variable("v_target_key", Text()).is_(None),
                "pair rule requires a string target partition key",
            ),
            Return(core_variable("v_target_key", Text())),
        ),
        (Local("v_target_key", pg_type("text")),),
        returns="text",
    )


def _admission(model, output):
    rules = model.tables["sem.data_rule"]
    partitions = model.tables["kb.data_product_partition"]
    release_id, product_id, kind_contract = (
        core_variable(name, Text()) for name in ("p_release", "p_product", "p_kind")
    )
    spec, key = core_variable("v_spec", JSONB()), core_variable("v_key", Text())
    pair = spec["scope"].astext == "partition-pair"
    target_role = spec["parameters"]["target_role"].astext
    none = cast(null(), Text())
    target_kind = spec["parameters"]["target_kind"].astext
    target_product = core_variable("v_target", Text())
    target_key = core_variable("v_target_key", Text())
    derivation = core_variable("p_derivation", Text())
    inputs = model.tables["ops.data_derivation_input"]
    products = model.tables["kb.data_product"]
    kinds = model.tables["sem.data_kind_contract"]
    bound_target = SelectInto(
        select(inputs.c.product_id)
        .select_from(
            inputs.join(products, products.c.id == inputs.c.product_id).join(
                kinds, kinds.c.kind_contract == products.c.kind_contract
            )
        )
        .where(
            inputs.c.derivation_id == derivation,
            inputs.c.role == target_role,
            inputs.c.member_id.is_(None),
            kinds.c.kind == target_kind,
        ),
        ("v_target",),
        strict=True,
    )
    selectors = (
        Assign("v_target_key", func.ops.ddo_rule_target_partition(spec, product_id, key)),
        Perform(func.ops.ddo_establish_rule(spec, product_id, key, target_product, target_key)),
    )
    for bound in (False, True):
        name = "ddo_apply_bound_product_rules" if bound else "ddo_apply_product_rules"
        params = (("p_release", "text"), ("p_product", "text"), ("p_kind", "text"))
        _routine(
            output,
            name,
            (*params, ("p_derivation", "text")) if bound else params,
            (
                ForQuery(
                    ("v_spec",),
                    select(rules.c.specification)
                    .where(
                        rules.c.release_id == release_id,
                        rules.c.kind_contract == kind_contract,
                        rules.c.specification["checker"].astext == "admission",
                        target_role.is_not(None) if bound else target_role.is_(None),
                    )
                    .order_by(rules.c.rule_id),
                    (
                        If(
                            spec["scope"].astext == "product",
                            (
                                Perform(
                                    func.ops.ddo_establish_rule(spec, product_id, none, none, none)
                                ),
                            ),
                            (
                                ForQuery(
                                    ("v_key",),
                                    select(partitions.c.partition_key)
                                    .where(
                                        partitions.c.product_id == product_id,
                                        partitions.c.collection == spec["collection"].astext,
                                    )
                                    .order_by(partitions.c.ordinal),
                                    (bound_target, *selectors)
                                    if bound
                                    else (
                                        If(
                                            pair,
                                            (Assign("v_target", product_id), *selectors),
                                            (
                                                Perform(
                                                    func.ops.ddo_establish_rule(
                                                        spec, product_id, key, none, none
                                                    )
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                Return(),
            ),
            (
                Local("v_spec", pg_type("jsonb")),
                Local("v_key", pg_type("text")),
                Local("v_target", pg_type("text")),
                Local("v_target_key", pg_type("text")),
            ),
            returns="void",
        )


def _retained_establishment(model, output):
    from .data_operation_projections import selected_support_output

    rules = model.tables["sem.data_rule"]
    products = model.tables["kb.data_product"]
    demands = model.tables["ops.data_demand"]
    reads = model.tables["ops.data_demand_read"]
    inputs = model.tables["ops.data_derivation_input"]
    uses = model.tables["ops.demand_use"]
    kinds = model.tables["sem.data_kind_contract"]
    payload = core_variable("p_payload", JSONB())
    product_id = core_variable("p_product", Text())
    target_id = payload["target_product_id"].astext
    source_key = payload["partition_key"].astext
    target_key = payload["target_partition_key"].astext
    derivation = core_variable("p_derivation", Text())
    use = core_variable("p_use", Text())
    spec = core_variable("v_spec", JSONB())
    demand_id = core_variable("d", Text(), "id")
    project_id = core_variable("d", Text(), "project_id")
    release_id = core_variable("d", Text(), "release_id")
    read = core_variable("boundary", reads.table_valued().type)
    target_kind = spec["parameters"]["target_kind"].astext
    target_role = spec["parameters"]["target_role"].astext
    target_mismatch = func.ops.ddo_rule_target_partition(
        spec, product_id, source_key, type_=Text()
    ).is_distinct_from(target_key)
    # A historical derivation role is not an authorization grant. Access to the
    # actual target still follows the selected use and current disclosure cut.
    from .data_operation_projections import _selected_support_output_rows

    obligation = select(uses.c.obligation_id).where(uses.c.id == use).scalar_subquery()
    target_scope = _selected_support_output_rows(model, exact_obligation=obligation).subquery(
        "authorized_target"
    )
    selected_target = (
        select(1)
        .select_from(
            inputs.join(products, products.c.id == inputs.c.product_id).join(
                kinds, kinds.c.kind_contract == products.c.kind_contract
            )
        )
        .where(
            inputs.c.derivation_id == derivation,
            inputs.c.role == target_role,
            inputs.c.product_id == target_id,
            inputs.c.member_id.is_(None),
            products.c.project_id == project_id,
            kinds.c.kind == target_kind,
            select(1)
            .select_from(target_scope)
            .where(target_scope.c.product_id == target_id)
            .exists(),
        )
        .exists()
    )
    recorded_selection = (
        select(uses.c.id)
        .where(uses.c.id == use, uses.c.demand_id == demand_id, uses.c.derivation_id == derivation)
        .exists()
    )
    _routine(
        output,
        "establish_data_rule_proof",
        (("p_payload", "jsonb"),),
        (
            SelectInto(
                select(core_relation_row(demands)).where(
                    demands.c.id == payload["demand_id"].astext,
                ),
                ("d",),
                strict=True,
            ),
            SelectInto(
                select(core_relation_row(reads)).where(
                    reads.c.id == payload["read_id"].astext,
                    reads.c.demand_id == demand_id,
                ),
                ("boundary",),
                strict=True,
            ),
            Perform(func.ops.ddo_require_read_current(read, project_id)),
            Assign(
                "p", func.jsonb_build_object("scope", core_variable("boundary", JSONB(), "scope"))
            ),
            _reject(~recorded_selection, "rule establishment requires exact selected use"),
            _reject(
                selected_support_output(model, exact_obligation=obligation)
                .scalar_subquery()
                .is_not(True),
                "rule establishment requires disclosed selected product",
            ),
            SelectInto(
                select(rules.c.specification)
                .select_from(
                    rules.join(products, products.c.kind_contract == rules.c.kind_contract)
                )
                .where(
                    rules.c.release_id == release_id,
                    rules.c.rule_id == payload["rule_id"].astext,
                    products.c.id == product_id,
                    products.c.project_id == project_id,
                ),
                ("v_spec",),
                strict=True,
            ),
            If(
                spec["scope"].astext == "partition-pair",
                (
                    _reject(
                        or_(target_id.is_(None), target_key.is_(None), source_key.is_(None)),
                        "pair rule requires exact bound partitions",
                    ),
                    If(
                        target_role.is_not(None),
                        (
                            _reject(
                                or_(~selected_target, target_mismatch),
                                "pair target differs from its admitted input role or partition key",
                            ),
                        ),
                        (
                            _reject(
                                or_(
                                    target_id.is_distinct_from(product_id),
                                    target_mismatch,
                                ),
                                "local pair must use the same product and partition key",
                            ),
                        ),
                    ),
                ),
            ),
            Assign(
                "v_count",
                func.ops.ddo_establish_rule(spec, product_id, source_key, target_id, target_key),
            ),
            Return(
                func.jsonb_build_object(
                    "established",
                    core_variable("v_count", BigInteger()),
                    "matched",
                    1 - core_variable("v_count", BigInteger()),
                )
            ),
        ),
        (
            Local("d", demands),
            Local("boundary", reads),
            Local("p", pg_type("jsonb")),
            Local("p_use", pg_type("text"), payload["use_id"].astext),
            Local("p_product", pg_type("text"), payload["product_id"].astext),
            Local("p_derivation", pg_type("text"), payload["derivation_id"].astext),
            Local("v_spec", pg_type("jsonb")),
            Local("v_count", pg_type("int4")),
        ),
    )


def rule_native_programs(model):
    output = []
    _premise(model, output)
    _predicate(output)
    _evaluator(model, output)
    _establish(model, output)
    _target_partition(model, output)
    _admission(model, output)
    _retained_establishment(model, output)
    return tuple(output)
