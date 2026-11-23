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
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB
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


def _page(records, payload):
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
    return select(
        _obj(
            cut=cut,
            rows=select(_aggregate(page.c.record, page.c.key)).scalar_subquery(),
            answer_after=case((more, last), else_=null()),
            oversized=oversized,
        )
    )


def outputs_answer(model, payload):
    uses = _selected_use_rows(model, payload)
    outputs = model.tables["ops.data_derivation_output"]
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    episodes = model.tables["ops.data_derivation"]
    kinds = model.tables["sem.data_kind_contract"].alias("answer_output_kinds")
    select_body = func.coalesce(payload["body"].as_boolean(), False)
    member_filter = payload["member_id"].astext
    containers_only = func.coalesce(payload["containers_only"].as_boolean(), False)
    want_members = func.coalesce(payload["include_members"].as_boolean(), True)
    base = (
        uses.join(episodes, episodes.c.id == uses.c.derivation_id)
        .join(outputs, outputs.c.derivation_id == uses.c.derivation_id)
        .join(products, products.c.id == outputs.c.product_id)
    )
    header_names = (
        "kind_contract",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
    )
    common = (
        uses.c.id.label("use_id"),
        uses.c.obligation_id,
        uses.c.derivation_id,
        uses.c.operation_id,
        episodes.c.release_id,
        case(
            (
                and_(
                    func.coalesce(payload["include_binding"].as_boolean(), False),
                    ~_public_authority_leaf(uses.c.derivation_id),
                ),
                uses.c.selection,
            )
        ).label("selection"),
        outputs.c.role,
        outputs.c.position,
        outputs.c.multiplicity,
        outputs.c.product_id,
        outputs.c.member_id.label("output_member_id"),
        products.c.kind_contract.label("parent_kind"),
    )
    product_filter = or_(
        ~payload.has_key("product_id"), outputs.c.product_id == payload["product_id"].astext
    )
    parents = (
        select(
            *common,
            cast(null(), Text()).label("member_id"),
            *(products.c[name] for name in header_names),
            products.c.canonical_body.label("body"),
        )
        .select_from(base)
        .where(product_filter, outputs.c.member_id.is_(None), member_filter.is_(None))
    )
    packets = (
        select(
            *common,
            members.c.member_id,
            *(members.c[name] for name in header_names),
            members.c.body,
        )
        .select_from(base.join(members, members.c.product_id == products.c.id))
        .where(
            product_filter,
            want_members,
            ~containers_only,
            or_(outputs.c.member_id.is_(None), outputs.c.member_id == members.c.member_id),
            or_(member_filter.is_(None), members.c.member_id == member_filter),
        )
    )
    projected = union_all(parents, packets).subquery("answer_output_addresses")
    o = projected.c
    disclosed = and_(
        _disclosed_kind_access(model, o.parent_kind),
        _disclosed_kind_access(model, o.kind_contract),
    )

    # Only admitted rows are interpreted. Member filters apply to the indexed
    # member relation before the body's record classification is opened.
    def classification(name):
        return or_(
            ~payload.has_key(name),
            func.data.ddo_field(o.body, name, type_=JSONB())[1].astext == payload[name].astext,
        )

    matches = (
        select(projected)
        .where(
            or_(
                ~payload.has_key("kind_contract"),
                o.kind_contract == payload["kind_contract"].astext,
            ),
            or_(
                ~payload.has_key("kind_contracts"),
                payload["kind_contracts"].has_key(o.kind_contract),
            ),
            case(
                (disclosed, and_(classification("record_type"), classification("family"))),
                else_=False,
            ),
        )
        .cte("answer_output_matches")
        .prefix_with("MATERIALIZED")
    )
    output = matches.c
    validity = _validity_rows(
        select(func.array_agg(output.use_id.distinct())).scalar_subquery(),
        name="answer_output_validity",
    )
    key = func.jsonb_build_array(
        output.obligation_id,
        output.use_id,
        output.role,
        output.position,
        output.product_id,
        func.coalesce(output.member_id, ""),
        type_=JSONB(),
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
                "selection",
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
    )
    record = header.concat(case((select_body, _obj(meaning_body=output.body)), else_=_json({})))
    source_metadata = func.coalesce(payload["source_metadata"].as_boolean(), False)
    record = record.concat(
        case(
            (
                source_metadata,
                _obj(
                    source=func.data.ddo_field(output.body, "source", type_=JSONB()),
                    selectors=func.data.ddo_field(output.body, "selectors", type_=JSONB()),
                ),
            ),
            else_=_json({}),
        )
    )
    return _page(
        select(key.label("key"), record.label("record"))
        .select_from(matches.join(kinds, kinds.c.kind_contract == output.kind_contract))
        .where(
            case(
                (
                    _set_valid(validity, "use", output.use_id),
                    case(
                        (
                            or_(select_body, source_metadata),
                            _disclosed_body_access(model, output.kind_contract, output.body),
                        ),
                        else_=True,
                    ),
                ),
                else_=False,
            )
        ),
        payload,
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
    records = select(
        func.jsonb_build_array(p.ordinal, p.partition_key, type_=JSONB()).label("key"),
        func.to_jsonb(partitions.table_valued(), type_=JSONB()).label("record"),
    ).where(
        p.product_id == payload["product_id"].astext,
        p.collection == payload["collection"].astext,
        or_(~payload.has_key("partition_key"), p.partition_key == payload["partition_key"].astext),
        ~payload.has_key("item_key"),
        ~func.coalesce(payload["items"].as_boolean(), False),
        ~payload.has_key("member_id"),
        visible,
    )
    retained, items, _, item_join = _typed_partition_sources(model)
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
    exact = (
        select(
            func.jsonb_build_array(retained.c.ordinal, items.c.item_ordinal, type_=JSONB()).label(
                "key"
            ),
            _obj(
                product_id=retained.c.product_id,
                collection=retained.c.collection,
                partition_key=retained.c.partition_key,
                item_ordinal=items.c.item_ordinal,
            )
            .concat(item_data)
            .label("record"),
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
            select(1)
            .where(
                authorized.c.product_id == retained.c.product_id,
                authorized.c.output_member_id.is_(None),
            )
            .exists(),
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
            func.jsonb_build_array(inputs.c.role, inputs.c.position, type_=JSONB()).label("key"),
            input_record.label("record"),
        )
        .select_from(
            episodes.join(inputs, inputs.c.derivation_id == episode.id)
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
            or_(
                ~payload.has_key("input_product_id"),
                inputs.c.product_id == payload["input_product_id"].astext,
            ),
            or_(~payload.has_key("input_role"), inputs.c.role == payload["input_role"].astext),
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
    return _page(union_all(facts, producers), payload)


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
    evidence = (
        select(
            p.rule_fingerprint,
            p.premise,
            _aggregate(
                _obj(derivation_id=p.derivation_id, role=p.role, position=p.position),
                p.derivation_id,
                p.role,
                p.position,
            ).label("provenance"),
        )
        .where(_visible(provenance), ~_public_authority_leaf(p.derivation_id), issuer_is_visible)
        .group_by(p.rule_fingerprint, p.premise)
        .cte("answer_proof_evidence")
    )
    rows = (
        select(
            func.jsonb_build_array(
                matching.c.rule_fingerprint, matching.c.premise, type_=JSONB()
            ).label("key"),
            _obj(
                rule_fingerprint=matching.c.rule_fingerprint,
                premise=matching.c.premise,
                provenance=func.coalesce(evidence.c.provenance, _json([])),
            ).label("record"),
        )
        .select_from(
            matching.outerjoin(
                evidence,
                and_(
                    evidence.c.rule_fingerprint == matching.c.rule_fingerprint,
                    evidence.c.premise == matching.c.premise,
                ),
            )
        )
        .where(or_(matching.c.checker == "admission", evidence.c.provenance.is_not(None)))
    )
    return _page(rows, payload)
