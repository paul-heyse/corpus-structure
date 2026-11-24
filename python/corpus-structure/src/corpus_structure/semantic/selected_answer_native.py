"""Read projections over an authenticated, already acquired native cut."""

from sqlalchemy import (
    BigInteger,
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
    tuple_,
    union_all,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, array
from sqlalchemy.types import NullType

from .data_operation_projections import (
    _aggregate,
    _cut_fields,
    _disclosed_body_access,
    _disclosed_kind_access,
    _items,
    _json,
    _latest_read_use,
    _obj,
    _public_authority_leaf,
    _scoped_read_obligations,
    _selected_support_output_rows,
    _set_valid,
    _validity_rows,
    _var,
    _visible,
)
from .native_program import core_reference


def _selected_use_rows(model, payload):
    obligations = _scoped_read_obligations(model).cte("answer_obligations")
    latest = _latest_read_use(model, obligations)
    return (
        select(latest, obligations.c.operation_id.label("operation_id"))
        .select_from(obligations.join(latest, literal(True)))
        .where(
            latest.c.fate == "fulfilled",
            or_(~payload.has_key("use_id"), latest.c.id == payload["use_id"].astext),
        )
        .cte("answer_selected_uses")
    )


def _page(records, payload, *, truncated=None):
    """Carry the exact last delivered key and examine at most one lookahead."""
    limit = _var("lim", BigInteger)
    candidates = records.cte("answer_matching_rows")
    window = (
        select(candidates)
        .where(or_(~payload.has_key("answer_after"), candidates.c.key > payload["answer_after"]))
        .order_by(candidates.c.key)
        .limit(limit + 1)
        .cte("answer_window")
        .prefix_with("MATERIALIZED")
    )
    sized = select(
        window,
        func.row_number().over(order_by=window.c.key).label("ordinal"),
        func.sum(func.octet_length(func.data.canonical_json(window.c.record)) + 1)
        .over(order_by=window.c.key, rows=(None, 0))
        .label("bytes"),
    ).cte("answer_sized")
    cut = _obj(**_cut_fields())
    max_bytes = (
        _var("selected_max_bytes", BigInteger)
        - func.octet_length(func.data.canonical_json(cut))
        - 256
    )
    page = (
        select(sized.c.key, sized.c.record)
        .where(sized.c.ordinal <= limit, sized.c.bytes <= max_bytes)
        .cte("answer_page")
        .prefix_with("MATERIALIZED")
    )
    more = (
        select(1)
        .select_from(sized)
        .where(or_(sized.c.ordinal > limit, sized.c.bytes > max_bytes))
        .exists()
    )
    last = select(page.c.key).order_by(page.c.key.desc()).limit(1).scalar_subquery()
    oversized = (
        select(sized.c.key).where(sized.c.ordinal == 1, sized.c.bytes > max_bytes).scalar_subquery()
    )
    if truncated is not None:
        more = or_(more, truncated)
    result = _obj(
        cut=cut,
        rows=select(_aggregate(page.c.record, page.c.key)).scalar_subquery(),
        answer_after=case((more, last), else_=null()),
        oversized=oversized,
    )
    if truncated is not None:
        # A marker only for the native endpoint. Never publish an examined
        # address, and never report exhaustion when all examined rows hid it.
        result = result.concat(
            _obj(examination_exhausted=and_(truncated, last.is_(None), oversized.is_(None)))
        )
    return select(result)


def _output_address_window(model, payload, *, capacity):
    """Visit output prefixes in index order, retaining at most one shared address window."""
    outputs = model.tables["ops.data_derivation_output"]
    members = model.tables["kb.data_product_member"]
    products = model.tables["kb.data_product"]
    episodes = model.tables["ops.data_derivation"]
    demand_uses = model.tables["ops.demand_use"]
    requested_use = payload["use_id"].astext
    want_members = and_(
        func.coalesce(payload["include_members"].as_boolean(), True),
        ~func.coalesce(payload["containers_only"].as_boolean(), False),
    )

    def requested_kind(kind):
        return and_(
            or_(~payload.has_key("kind_contract"), kind == payload["kind_contract"].astext),
            or_(~payload.has_key("kind_contracts"), payload["kind_contracts"].has_key(kind)),
        )

    requested_obligation = (
        select(demand_uses.c.obligation_id)
        .where(demand_uses.c.id == requested_use)
        .scalar_subquery()
    )
    scope = _scoped_read_obligations(model).subquery("answer_seek_scope")
    after = payload["answer_after"]
    empty_members = cast(array([]), ARRAY(Text()))
    steps = select(
        func.coalesce(after[0].astext, "").label("obligation_id"),
        func.coalesce(after[1].astext, "").label("use_id"),
        func.coalesce(after[2].astext, "").label("role"),
        func.coalesce(cast(after[3].astext, BigInteger()), 0).label("position"),
        func.coalesce(after[4].astext, "").label("product_id"),
        cast(null(), Text()).label("output_member_id"),
        cast(null(), Text()).label("derivation_id"),
        cast(null(), Text()).label("operation_id"),
        cast(null(), BigInteger()).label("multiplicity"),
        literal(False).label("parent"),
        empty_members.label("member_ids"),
        literal(capacity).label("remaining"),
        literal(True).label("initial"),
    ).cte("answer_address_steps", recursive=True)
    s = steps.c
    latest = _latest_read_use(model, scope)
    same_use = and_(scope.c.id == s.obligation_id, latest.c.id == s.use_id)
    coordinate = tuple_(outputs.c.role, outputs.c.position)
    previous = tuple_(s.role, s.position)
    exact_cursor_output = and_(same_use, coordinate == previous)
    output = (
        select(outputs)
        .where(
            outputs.c.derivation_id == latest.c.derivation_id,
            coordinate
            >= tuple_(
                case((same_use, s.role), else_=""),
                case((same_use, s.position), else_=0),
            ),
            or_(
                ~exact_cursor_output,
                and_(s.initial, outputs.c.product_id >= s.product_id),
            ),
            or_(
                ~payload.has_key("product_id"), outputs.c.product_id == payload["product_id"].astext
            ),
            or_(
                and_(want_members, ~payload.has_key("member_id")),
                and_(
                    outputs.c.member_id.is_(None),
                    or_(
                        want_members,
                        select(1)
                        .where(
                            products.c.id == outputs.c.product_id,
                            requested_kind(products.c.kind_contract),
                        )
                        .exists(),
                    ),
                ),
                and_(want_members, outputs.c.member_id == payload["member_id"].astext),
            ),
        )
        .order_by(outputs.c.role, outputs.c.position)
        .limit(1)
        .correlate(steps, latest, scope)
        .lateral("answer_next_output")
    )
    prefix = (
        select(
            scope.c.id.label("obligation_id"),
            latest.c.id.label("use_id"),
            scope.c.operation_id,
            output.c.derivation_id,
            output.c.role,
            output.c.position,
            output.c.multiplicity,
            output.c.product_id,
            output.c.member_id.label("output_member_id"),
        )
        .select_from(scope.join(latest, literal(True)).join(output, literal(True)))
        .where(
            scope.c.id >= s.obligation_id,
            or_(scope.c.id > s.obligation_id, latest.c.id >= s.use_id),
            or_(~payload.has_key("use_id"), scope.c.id == requested_obligation),
            or_(~payload.has_key("use_id"), latest.c.id == requested_use),
            latest.c.fate == "fulfilled",
        )
        .order_by(scope.c.id)
        .limit(1)
        .correlate(steps)
        .lateral("answer_next_prefix")
    )
    p = prefix.c
    resumes_members = and_(
        s.initial,
        p.obligation_id == s.obligation_id,
        p.use_id == s.use_id,
        p.role == s.role,
        p.position == s.position,
        p.product_id == s.product_id,
    )
    parent = and_(
        p.output_member_id.is_(None),
        ~payload.has_key("member_id"),
        ~resumes_members,
        select(1)
        .where(products.c.id == p.product_id, requested_kind(products.c.kind_contract))
        .correlate(prefix)
        .exists(),
    )
    member_slots = s.remaining - case((parent, 1), else_=0)
    lower_member = case((resumes_members, after[5].astext), else_=null())
    exact_member = func.coalesce(payload["member_id"].astext, p.output_member_id)
    eligible_member = (
        select(members.c.member_id)
        .where(
            members.c.product_id == p.product_id,
            members.c.member_id > func.coalesce(lower_member, ""),
            requested_kind(members.c.kind_contract),
            want_members,
        )
        .correlate(steps, prefix)
    )
    point_member = eligible_member.where(members.c.member_id == exact_member, member_slots > 0)
    member_page = (
        eligible_member.where(exact_member.is_(None))
        .order_by(members.c.member_id)
        .limit(func.greatest(member_slots, 0))
    )
    matched_members = union_all(point_member, member_page).subquery("answer_next_members")
    batch = (
        select(
            func.coalesce(
                func.array_agg(
                    aggregate_order_by(matched_members.c.member_id, matched_members.c.member_id)
                ),
                empty_members,
            ).label("member_ids")
        )
        .select_from(matched_members)
        .lateral("answer_member_batch")
    )
    steps = steps.union_all(
        select(
            p.obligation_id,
            p.use_id,
            p.role,
            p.position,
            p.product_id,
            p.output_member_id,
            p.derivation_id,
            p.operation_id,
            p.multiplicity,
            parent,
            batch.c.member_ids,
            member_slots - func.cardinality(batch.c.member_ids),
            literal(False),
        )
        .select_from(steps.join(prefix, literal(True)).join(batch, literal(True)))
        .where(s.remaining > 0)
    )

    s = steps.c
    addresses = union_all(
        select(*s, cast(null(), Text()).label("member_id")).where(s.parent),
        select(*s, func.unnest(s.member_ids, type_=Text()).label("member_id")).where(~s.initial),
    ).subquery("answer_sought_addresses")
    a = addresses.c
    seek = func.jsonb_build_array(
        a.obligation_id,
        a.use_id,
        a.role,
        a.position,
        a.product_id,
        func.coalesce(a.member_id, ""),
        type_=JSONB(),
    )
    headers = (
        "kind_contract",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
    )
    return (
        select(
            a.use_id,
            a.obligation_id,
            a.derivation_id,
            a.operation_id,
            episodes.c.release_id,
            a.role,
            a.position,
            a.multiplicity,
            a.product_id,
            a.output_member_id,
            a.member_id,
            products.c.kind_contract.label("parent_kind"),
            *(
                case((a.member_id.is_(None), products.c[name]), else_=members.c[name]).label(name)
                for name in headers
            ),
            seek.label("key"),
        )
        .select_from(
            addresses.join(episodes, episodes.c.id == a.derivation_id)
            .join(products, products.c.id == a.product_id)
            .outerjoin(
                members,
                and_(members.c.product_id == a.product_id, members.c.member_id == a.member_id),
            )
        )
        .cte("answer_candidate_addresses")
        .prefix_with("MATERIALIZED")
    )


def outputs_answer(model, payload):
    uses = model.tables["ops.demand_use"]
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    kinds = model.tables["sem.data_kind_contract"].alias("answer_output_kinds")
    select_body = func.coalesce(payload["body"].as_boolean(), False)
    header_names = (
        "kind_contract",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
    )
    # Work bounds and delivery bounds are independent. A cheap extra address
    # proves truncation without opening an unexamined body's classification.
    examined = 4096
    candidates = _output_address_window(model, payload, capacity=examined + 1)
    truncated = select(func.count()).select_from(candidates).scalar_subquery() > examined
    window = (
        select(candidates)
        .order_by(candidates.c.key)
        .limit(examined)
        .cte("answer_examined_addresses")
        .prefix_with("MATERIALIZED")
    )
    body = case((window.c.member_id.is_(None), products.c.canonical_body), else_=members.c.body)

    def classification(name):
        return or_(
            ~payload.has_key(name),
            func.data.ddo_field(body, name, type_=JSONB())[1].astext == payload[name].astext,
        )

    disclosed = and_(
        _disclosed_kind_access(model, window.c.parent_kind),
        _disclosed_kind_access(model, window.c.kind_contract),
    )
    matches = (
        select(window)
        .select_from(
            window.join(products, products.c.id == window.c.product_id).outerjoin(
                members,
                and_(
                    members.c.product_id == window.c.product_id,
                    members.c.member_id == window.c.member_id,
                ),
            )
        )
        .where(
            case(
                (disclosed, and_(classification("record_type"), classification("family"))),
                else_=False,
            )
        )
        .cte("answer_output_matches")
        .prefix_with("MATERIALIZED")
    )
    output = matches.c
    validity = _validity_rows(
        select(func.array_agg(output.use_id.distinct())).scalar_subquery(),
        name="answer_output_validity",
    )
    source_metadata = func.coalesce(payload["source_metadata"].as_boolean(), False)
    body = case((output.member_id.is_(None), products.c.canonical_body), else_=members.c.body)
    load_body = or_(select_body, source_metadata)
    selected_deliveries = (
        select(matches)
        .select_from(
            matches.join(products, products.c.id == output.product_id).outerjoin(
                members,
                and_(
                    members.c.product_id == output.product_id,
                    members.c.member_id == output.member_id,
                ),
            )
        )
        .where(
            case(
                (
                    _set_valid(validity, "use", output.use_id),
                    case(
                        (load_body, _disclosed_body_access(model, output.kind_contract, body)),
                        else_=True,
                    ),
                ),
                else_=False,
            )
        )
        .order_by(output.key)
        .limit(_var("lim", BigInteger) + 1)
        .cte("answer_deliverable_addresses")
        .prefix_with("MATERIALIZED")
    )
    output = selected_deliveries.c
    body = case((output.member_id.is_(None), products.c.canonical_body), else_=members.c.body)
    selection = case(
        (
            and_(
                func.coalesce(payload["include_binding"].as_boolean(), False),
                ~_public_authority_leaf(output.derivation_id),
            ),
            uses.c.selection,
        )
    )
    header = _obj(
        **{
            name: output[name]
            for name in (
                "obligation_id",
                "use_id",
                "derivation_id",
                "operation_id",
                "release_id",
                "role",
                "position",
                "multiplicity",
                "product_id",
                "output_member_id",
                "member_id",
                *header_names,
            )
        },
        kind=kinds.c.kind,
        selection=selection,
    )
    record = header.concat(case((select_body, _obj(meaning_body=body)), else_=_json({})))
    record = record.concat(
        case(
            (
                source_metadata,
                _obj(
                    source=func.data.ddo_field(body, "source", type_=JSONB()),
                    selectors=func.data.ddo_field(body, "selectors", type_=JSONB()),
                ),
            ),
            else_=_json({}),
        )
    )
    return _page(
        select(output.key, record.label("record")).select_from(
            selected_deliveries.join(kinds, kinds.c.kind_contract == output.kind_contract)
            .join(uses, uses.c.id == output.use_id)
            .join(products, products.c.id == output.product_id)
            .outerjoin(
                members,
                and_(
                    members.c.product_id == output.product_id,
                    members.c.member_id == output.member_id,
                ),
            )
        ),
        payload,
        truncated=truncated,
    )


def _authorized_outputs(model, payload, *product_fields):
    selected = _selected_use_rows(model, payload)
    anchor = select(selected.c.obligation_id).where(selected.c.id == payload["use_id"].astext)
    return _selected_support_output_rows(
        model,
        one_use=False,
        member_aware=True,
        exact_obligation=anchor.scalar_subquery(),
        requested_products=tuple(payload[name].astext for name in product_fields),
    ).cte("answer_authorized_outputs")


def partitions_answer(model, payload):
    from .data_operation_rule_native import _rule_partition_headers, _typed_partition_sources

    authorized = _authorized_outputs(model, payload, "product_id")
    partitions = _rule_partition_headers(model, "answer_partitions")
    p = partitions.c
    visible = (
        select(1)
        .where(authorized.c.product_id == p.product_id, authorized.c.output_member_id.is_(None))
        .exists()
    )
    header_key = func.jsonb_build_array(p.ordinal, p.partition_key, type_=JSONB())
    after = payload["answer_after"]
    after_ordinal = case(
        (func.jsonb_typeof(after[0]) == "number", cast(after[0].astext, BigInteger())),
        else_=-1,
    )
    header_window = (
        select(partitions, header_key.label("key"))
        .where(
            p.product_id == payload["product_id"].astext,
            p.collection == payload["collection"].astext,
            or_(
                ~payload.has_key("partition_key"),
                p.partition_key == payload["partition_key"].astext,
            ),
            ~payload.has_key("item_key"),
            ~func.coalesce(payload["items"].as_boolean(), False),
            ~payload.has_key("member_id"),
            tuple_(p.ordinal, p.partition_key)
            > tuple_(after_ordinal, func.coalesce(after[1].astext, "")),
            or_(~payload.has_key("answer_after"), header_key > after),
            visible,
        )
        .order_by(p.ordinal, p.partition_key)
        .limit(_var("lim", BigInteger) + 1)
        .cte("answer_partition_header_addresses")
        .prefix_with("MATERIALIZED")
    )
    records = select(
        header_window.c.key,
        func.to_jsonb(header_window.table_valued(), type_=JSONB()).op("-")("key").label("record"),
    )
    retained, items, _, item_join = _typed_partition_sources(model)
    coordinate = (
        "intent_id",
        "output_role",
        "output_position",
        "collection",
        "partition_key",
        "item_ordinal",
    )
    item_cursor = func.jsonb_build_array(retained.c.ordinal, items.c.item_ordinal, type_=JSONB())
    item_window = (
        select(
            retained.c.product_id,
            *(items.c[field] for field in coordinate),
            item_cursor.label("key"),
        )
        .select_from(item_join)
        .where(
            retained.c.product_id == payload["product_id"].astext,
            retained.c.collection == payload["collection"].astext,
            retained.c.partition_key == payload["partition_key"].astext,
            or_(
                items.c.address_key == cast(payload["item_key"], Text()),
                and_(
                    ~payload.has_key("item_key"),
                    func.coalesce(payload["items"].as_boolean(), False),
                ),
            ),
            retained.c.ordinal >= after_ordinal,
            items.c.item_ordinal
            > case(
                (
                    and_(
                        retained.c.ordinal == after_ordinal, func.jsonb_typeof(after[1]) == "number"
                    ),
                    cast(after[1].astext, BigInteger()),
                ),
                else_=-1,
            ),
            or_(~payload.has_key("answer_after"), item_cursor > after),
            select(1)
            .where(
                authorized.c.product_id == retained.c.product_id,
                authorized.c.output_member_id.is_(None),
            )
            .exists(),
        )
        .order_by(items.c.item_ordinal)
        .limit(_var("lim", BigInteger) + 1)
        .cte("answer_partition_item_addresses")
        .prefix_with("MATERIALIZED")
    )
    requested_fields = _items(payload["fields"], "answer_item_fields")
    field = requested_fields.c.value.op("#>>")(literal("{}"))
    item_body = cast(items.c.canonical_text, JSONB())
    fields = (
        select(func.jsonb_object_agg(field, func.data.ddo_field(item_body, field, type_=JSONB())))
        .select_from(requested_fields)
        .correlate(items)
        .scalar_subquery()
    )
    item_data = case(
        (payload.has_key("fields"), _obj(fields=func.coalesce(fields, _json({})))),
        else_=_obj(meaning_body=item_body),
    )
    exact = select(
        item_window.c.key,
        _obj(
            product_id=item_window.c.product_id,
            collection=items.c.collection,
            partition_key=items.c.partition_key,
            item_ordinal=items.c.item_ordinal,
        )
        .concat(item_data)
        .label("record"),
    ).select_from(
        item_window.join(
            items,
            and_(*(items.c[field] == item_window.c[field] for field in coordinate)),
        )
    )
    members = model.tables["kb.data_product_member"]
    member = select(
        func.jsonb_build_array(members.c.product_id, members.c.member_id, type_=JSONB()).label(
            "key"
        ),
        _obj(
            product_id=members.c.product_id,
            member_id=members.c.member_id,
            kind_contract=members.c.kind_contract,
            meaning_body=members.c.body,
        ).label("record"),
    ).where(
        members.c.product_id == payload["product_id"].astext,
        members.c.member_id == payload["member_id"].astext,
        select(1)
        .where(
            authorized.c.product_id == members.c.product_id,
            or_(
                authorized.c.output_member_id.is_(None),
                authorized.c.output_member_id == members.c.member_id,
            ),
        )
        .exists(),
        _disclosed_body_access(model, members.c.kind_contract, members.c.body),
    )
    return _page(union_all(records, exact, member), payload)


def derivation_facts_answer(model, payload):
    authorized = _authorized_outputs(model, payload)
    episodes = model.tables["ops.data_derivation"]
    inputs = model.tables["ops.data_derivation_input"]
    requests = model.tables["ops.data_request"]
    definitions = model.tables["sem.data_operation_definition"]
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    kinds = model.tables["sem.data_kind_contract"].alias("answer_input_kinds")
    admissions = model.tables["ops.original_source_admission"].alias("answer_input_admissions")
    episode = episodes.c
    source = select(1).where(authorized.c.derivation_id == episode.id).exists()
    input_key = func.jsonb_build_array(inputs.c.role, inputs.c.position, type_=JSONB())
    after = payload["answer_after"]
    after_position = case(
        (func.jsonb_typeof(after[1]) == "number", cast(after[1].astext, BigInteger())),
        else_=-1,
    )
    examined = 4096
    input_addresses = (
        select(inputs.c.derivation_id, inputs.c.role, inputs.c.position, input_key.label("key"))
        .where(
            inputs.c.derivation_id == payload["derivation_id"].astext,
            select(1)
            .where(authorized.c.derivation_id == inputs.c.derivation_id)
            .correlate(inputs)
            .exists(),
            ~_public_authority_leaf(inputs.c.derivation_id),
            tuple_(inputs.c.role, inputs.c.position)
            > tuple_(func.coalesce(after[0].astext, ""), after_position),
            or_(~payload.has_key("answer_after"), input_key > after),
            or_(
                ~payload.has_key("input_product_id"),
                inputs.c.product_id == payload["input_product_id"].astext,
            ),
            or_(~payload.has_key("input_role"), inputs.c.role == payload["input_role"].astext),
        )
        .order_by(inputs.c.role, inputs.c.position)
        .limit(examined + 1)
        .cte("answer_derivation_input_addresses")
        .prefix_with("MATERIALIZED")
    )
    truncated = select(func.count()).select_from(input_addresses).scalar_subquery() > examined
    input_window = (
        select(input_addresses)
        .order_by(input_addresses.c.role, input_addresses.c.position)
        .limit(examined)
        .cte("answer_examined_input_addresses")
        .prefix_with("MATERIALIZED")
    )
    role_inputs = func.ops.ddo_derivation_input_positions(
        requests.c.binding["inputs"], definitions.c.input_roles
    ).table_valued(column("input_record", JSONB()), column("physical_position", BigInteger()))
    entry = role_inputs.c.input_record
    refs = (
        func.ops.ddo_input_support_refs(requests.c.binding, entry)
        .table_valued(column("reference", JSONB()))
        .render_derived(name="answer_input_support")
    )
    reference = refs.c.reference
    admitted_original = (
        select(1)
        .where(
            admissions.c.id == reference["admission_id"].astext,
            admissions.c.product_id == inputs.c.product_id,
            admissions.c.project_id == _var("d.project_id", Text),
            _visible(admissions),
            func.ops.ddo_original_admission_valid(
                admissions.table_valued(), core_reference("boundary", type_=NullType())
            ),
        )
        .correlate(inputs, refs)
        .exists()
    )
    admitted_computation = (
        select(1)
        .where(
            authorized.c.product_id == inputs.c.product_id,
            authorized.c.derivation_id == reference["derivation_id"].astext,
            authorized.c.admission_use_id == reference["admission_use_id"].astext,
            or_(
                authorized.c.output_member_id.is_(None),
                authorized.c.output_member_id == inputs.c.member_id,
            ),
        )
        .correlate(inputs, refs)
        .exists()
    )
    eligible_refs = (
        select(reference)
        .where(or_(admitted_computation, admitted_original))
        .correlate(requests, role_inputs, inputs)
    )
    support = (
        select(_aggregate(reference, reference))
        .where(
            case(
                (reference["derivation_id"].astext.is_(None), admitted_original),
                else_=and_(
                    admitted_computation, ~_public_authority_leaf(reference["derivation_id"].astext)
                ),
            )
        )
        .correlate(requests, role_inputs, inputs)
        .scalar_subquery()
    )
    input_kind = func.coalesce(members.c.kind_contract, products.c.kind_contract)
    input_body = func.coalesce(members.c.body, products.c.canonical_body)
    input_record = (
        func.to_jsonb(inputs.table_valued(), type_=JSONB())
        .concat(
            _obj(
                support=support,
                kind_contract=input_kind,
                kind=kinds.c.kind,
                subject=func.coalesce(members.c.subject, products.c.subject),
                subject_definition=func.coalesce(
                    members.c.subject_definition, products.c.subject_definition
                ),
                original_source=case(
                    (inputs.c.member_id.is_(None), products.c.original_source),
                    else_=members.c.original_source,
                ),
                analyzed_scope=func.coalesce(members.c.analyzed_scope, products.c.analyzed_scope),
            )
        )
        .concat(
            case(
                (func.coalesce(payload["body"].as_boolean(), False), _obj(meaning_body=input_body)),
                else_=_json({}),
            )
        )
    )
    facts = (
        select(
            input_window.c.key,
            input_record.label("record"),
        )
        .select_from(
            input_window.join(
                inputs,
                and_(
                    inputs.c.derivation_id == input_window.c.derivation_id,
                    inputs.c.role == input_window.c.role,
                    inputs.c.position == input_window.c.position,
                ),
            )
            .join(episodes, episode.id == input_window.c.derivation_id)
            .join(requests, requests.c.id == episode.request_id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == episode.release_id,
                    definitions.c.operation_id == requests.c.operation_id,
                ),
            )
            .join(
                role_inputs,
                and_(
                    entry["role"].astext == inputs.c.role,
                    role_inputs.c.physical_position == inputs.c.position,
                ),
            )
            .join(products, products.c.id == inputs.c.product_id)
            .outerjoin(
                members,
                and_(
                    members.c.product_id == inputs.c.product_id,
                    members.c.member_id == inputs.c.member_id,
                ),
            )
            .join(kinds, kinds.c.kind_contract == input_kind)
        )
        .where(
            episode.id == payload["derivation_id"].astext,
            source,
            eligible_refs.exists(),
            ~_public_authority_leaf(episode.id),
            case(
                (
                    func.coalesce(payload["body"].as_boolean(), False),
                    _disclosed_body_access(model, input_kind, input_body),
                ),
                else_=_disclosed_kind_access(model, input_kind),
            ),
        )
    )
    producers = (
        select(
            func.jsonb_build_array(
                episode.id,
                authorized.c.admission_use_id,
                authorized.c.role,
                authorized.c.position,
                type_=JSONB(),
            ).label("key"),
            _obj(
                derivation_id=episode.id,
                release_id=episode.release_id,
                recipe=episode.recipe,
                outcome=episode.outcome,
                operation_id=requests.c.operation_id,
                use_id=authorized.c.admission_use_id,
                role=authorized.c.role,
                position=authorized.c.position,
                member_id=authorized.c.output_member_id,
            ).label("record"),
        )
        .select_from(
            authorized.join(episodes, episode.id == authorized.c.derivation_id).join(
                requests, requests.c.id == episode.request_id
            )
        )
        .where(
            authorized.c.product_id == payload["product_id"].astext,
            ~_public_authority_leaf(episode.id),
        )
    )
    return _page(union_all(facts, producers), payload, truncated=truncated)


def proofs_answer(model, payload):
    proofs = model.tables["kb.data_validity"]
    provenance = model.tables["kb.data_validity_establishment"]
    rules = model.tables["sem.data_rule"]
    products = model.tables["kb.data_product"]
    authorized = _authorized_outputs(model, payload, "product_id", "target_product_id")
    p = provenance.c
    requested = _items(payload["premises"], "answer_rule_premises")
    fingerprint = requested.c.value["rule_fingerprint"].astext
    premise = requested.c.value["premise"].astext
    declared = rules.c.specification
    product = payload["product_id"].astext
    target = payload["target_product_id"].astext
    source_partition = payload["partition_key"].astext
    target_partition = payload["target_partition_key"].astext
    original_visible = (
        select(1)
        .where(authorized.c.product_id == product, authorized.c.output_member_id.is_(None))
        .exists()
    )
    target_visible = (
        select(1)
        .where(authorized.c.product_id == target, authorized.c.output_member_id.is_(None))
        .exists()
    )
    scope_matches = or_(
        and_(declared["scope"].astext == "product", source_partition.is_(None), target.is_(None)),
        and_(
            declared["scope"].astext == "partition", source_partition.is_not(None), target.is_(None)
        ),
        and_(
            declared["scope"].astext == "partition-pair",
            source_partition.is_not(None),
            target_visible,
            target_partition.is_not(None),
        ),
    )
    matching = (
        select(
            fingerprint.label("rule_fingerprint"),
            premise.label("premise"),
            declared["checker"].astext.label("checker"),
        )
        .select_from(
            requested.join(rules, rules.c.specification["fingerprint"].astext == fingerprint)
            .join(products, products.c.kind_contract == rules.c.kind_contract)
            .join(
                proofs, and_(proofs.c.rule_fingerprint == fingerprint, proofs.c.premise == premise)
            )
        )
        .where(
            rules.c.release_id == _var("d.release_id", Text),
            products.c.id == product,
            or_(
                ~payload.has_key("answer_after"),
                func.jsonb_build_array(fingerprint, premise, type_=JSONB())
                > payload["answer_after"],
            ),
            case(
                (
                    and_(original_visible, scope_matches),
                    func.ops.ddo_rule_premise(
                        declared, product, source_partition, target, target_partition
                    )
                    == premise,
                ),
                else_=False,
            ),
        )
        .distinct()
        .cte("answer_checked_proofs")
    )
    issuer_is_visible = (
        select(1)
        .where(
            authorized.c.derivation_id == p.derivation_id,
            authorized.c.role == p.role,
            authorized.c.position == p.position,
            authorized.c.product_id == product,
        )
        .exists()
    )
    proof_match = and_(
        p.rule_fingerprint == matching.c.rule_fingerprint,
        p.premise == matching.c.premise,
        _visible(provenance),
        ~_public_authority_leaf(p.derivation_id),
        issuer_is_visible,
    )
    key = func.jsonb_build_array(matching.c.rule_fingerprint, matching.c.premise, type_=JSONB())
    proof_window = (
        select(matching, key.label("key"))
        .where(
            or_(
                matching.c.checker == "admission",
                select(1).where(proof_match).correlate(matching).exists(),
            )
        )
        .order_by(key)
        .limit(_var("lim", BigInteger) + 1)
        .cte("answer_proof_addresses")
        .prefix_with("MATERIALIZED")
    )
    evidence = (
        select(
            _aggregate(
                _obj(derivation_id=p.derivation_id, role=p.role, position=p.position),
                p.derivation_id,
                p.role,
                p.position,
            )
        )
        .where(
            p.rule_fingerprint == proof_window.c.rule_fingerprint,
            p.premise == proof_window.c.premise,
            _visible(provenance),
            ~_public_authority_leaf(p.derivation_id),
            issuer_is_visible,
        )
        .correlate(proof_window)
        .scalar_subquery()
    )
    rows = select(
        proof_window.c.key,
        _obj(
            rule_fingerprint=proof_window.c.rule_fingerprint,
            premise=proof_window.c.premise,
            provenance=evidence,
        ).label("record"),
    )
    return _page(rows, payload)
