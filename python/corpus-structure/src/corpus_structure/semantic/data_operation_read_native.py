"""Protected admission inspection and selected-body access from typed read models."""

from typing import Literal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    not_,
    null,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB, aggregate_order_by, array

from .data_operation_native_identity import native_identity_field
from .data_operation_projections import binding_branches, binding_columns
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
    Return,
    ReturnNext,
    ReturnQuery,
    SelectInto,
    column_type,
    core_relation_row,
    core_star,
    core_variable,
    pg_type,
)
from .native_program import (
    literal as pg_literal,
)
from .support_trust_native import evaluator_body_access


def _object(*values):
    return func.jsonb_build_object(*values, type_=JSONB())


def _rows(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived()
        .alias(name)
    )


def _row(name, relation):
    return {field.name: core_variable(name, field.type, field.name) for field in relation.c}


def _exists(relation, *conditions):
    return select(1).select_from(relation).where(*conditions).exists()


def _refuse(condition, message, state="P0001"):
    return If(condition, (Raise(message, state),))


def _program(
    name,
    parameters,
    statements,
    locals_=(),
    *,
    returns=None,
    volatility: Literal["stable", "volatile", "immutable"] = "stable",
    security=True,
    strict=False,
    table_columns=(),
):
    return NativeRoutine(
        "ops",
        name,
        parameters=parameters,
        returns=pg_type("jsonb") if returns is None else returns,
        body=Block(tuple(statements), tuple(locals_)),
        security_definer=security,
        search_path=("pg_catalog", "pg_temp"),
        volatility=volatility,
        strict=strict,
        table_columns=table_columns,
    )


def _hash(value):
    return func.encode(func.sha256(value), "hex")


def _decode(value):
    return cast(func.convert_from(value, "UTF8"), JSONB())


def _inspection_programs(model):
    artifacts, kinds, memberships, definitions, releases, runtimes = (
        model.tables[name]
        for name in (
            "sem.artifact",
            "sem.data_kind_contract",
            "sem.data_kind_release",
            "sem.data_operation_definition",
            "sem.data_operation_release",
            "sem.runtime_binding",
        )
    )
    p, projection, archived = (
        core_variable(name, JSONB()) for name in ("p", "projection", "archived")
    )
    projected_kinds, projected_operations = (
        _rows(projection["kinds"], "projected_kinds"),
        _rows(projection["operations"], "projected_operations"),
    )
    expected_kinds = select(
        projected_kinds.c.value["kind_contract"].astext.label("key"),
        projected_kinds.c.value.concat(
            _object(
                "collections",
                func.coalesce(projected_kinds.c.value["collections"], _object()),
            )
        ).label("body"),
    ).cte("expected_kinds")
    actual_kinds = (
        select(
            kinds.c.kind_contract.label("key"), func.to_jsonb(kinds.table_valued()).label("body")
        )
        .select_from(kinds.join(memberships, memberships.c.kind_contract == kinds.c.kind_contract))
        .where(memberships.c.release_id == p["release_id"].astext)
        .cte("actual_kinds")
    )
    authored_operations = _rows(archived["operations"], "authored_operations")
    projected_operation = projected_operations.c.value
    authored_operation = authored_operations.c.value
    expected_operations = (
        select(
            projected_operation["operation_id"].astext.label("key"),
            projected_operation.op("-", return_type=JSONB())(
                array(["binding", "definition", "eligibility"], type_=Text())
            )
            .concat(
                _object(
                    "parameter_definitions",
                    func.coalesce(authored_operation["parameters"]["json"], _object()),
                )
            )
            .label("body"),
        )
        .select_from(
            projected_operations.join(
                authored_operations,
                authored_operation["semantic_id"].astext
                == projected_operation["operation_id"].astext,
            )
        )
        .cte("expected_operations")
    )
    actual_operations = (
        select(
            definitions.c.operation_id.label("key"),
            func.to_jsonb(definitions.table_valued())
            .op("-", return_type=JSONB())(
                array(
                    [
                        "release_id",
                        "binding_expression",
                        "definition_identity",
                        "eligibility_identity",
                        "quantified",
                        "command_class",
                        "dependencies",
                    ],
                    type_=Text(),
                )
            )
            .label("body"),
        )
        .where(definitions.c.release_id == p["release_id"].astext)
        .cte("actual_operations")
    )

    def difference(expected, actual):
        return _exists(
            expected.join(actual, expected.c.key == actual.c.key, full=True),
            expected.c.body.is_distinct_from(actual.c.body),
        )

    conservative = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        definitions.c.operation_id,
                        definitions.c.operation_id,
                    )
                ),
                cast(literal("[]"), JSONB()),
            )
        )
        .where(
            definitions.c.release_id == p["release_id"].astext, definitions.c.validity_conservative
        )
        .scalar_subquery()
    )
    operation_id = projected_operations.c.value["operation_id"].astext
    expected_conservative = (
        select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(operation_id, operation_id)),
                cast(literal("[]"), JSONB()),
            )
        )
        .where(
            projected_operations.c.value["validity_conservative"] == cast(literal("true"), JSONB())
        )
        .scalar_subquery()
    )
    validity_only = func.coalesce(cast(p["validity_only"].astext, Boolean()), False)
    release_inspection = _program(
        "inspect_data_operation_release",
        (Parameter("p_payload", pg_type("jsonb")),),
        (
            Perform(
                func.ops.ddo_fields(
                    p, array(["release_id"], type_=Text()), array(["validity_only"], type_=Text())
                )
            ),
            If(
                not_(validity_only),
                (Perform(func.data.require_execution_release(p["release_id"].astext)),),
            ),
            SelectInto(
                select(_decode(artifacts.c.content)).where(
                    artifacts.c.release_id == p["release_id"].astext,
                    artifacts.c.artifact_name == "data_operation_native_definitions.json",
                    _exists(
                        releases,
                        releases.c.release_id == artifacts.c.release_id,
                        releases.c.native_definitions_digest == _hash(artifacts.c.content),
                    ),
                ),
                ("projection",),
            ),
            SelectInto(
                select(_decode(artifacts.c.content)).where(
                    artifacts.c.release_id == p["release_id"].astext,
                    artifacts.c.artifact_name == "data_operations.json",
                    _hash(artifacts.c.content) == projection["model_digest"].astext,
                ),
                ("archived",),
            ),
            _refuse(
                or_(projection.is_(None), archived.is_(None)),
                "read-only inspection lacks its authenticated operation archive",
                "23514",
            ),
            _refuse(
                not_(
                    _exists(
                        releases,
                        releases.c.release_id == p["release_id"].astext,
                        or_(
                            validity_only,
                            releases.c.lowering_digest == native_identity_field("lowering_digest"),
                        ),
                        or_(validity_only, releases.c.binding_types == archived["kinds"]),
                        releases.c.native_kernel_digest == projection["native_digest"].astext,
                        releases.c.model_digest == projection["model_digest"].astext,
                    )
                ),
                "read-only inspection native source correspondence differs",
                "23514",
            ),
            _refuse(
                and_(not_(validity_only), difference(expected_kinds, actual_kinds)),
                "read-only inspection admitted kind rowset differs from archived contracts",
                "23514",
            ),
            _refuse(
                and_(not_(validity_only), difference(expected_operations, actual_operations)),
                "read-only inspection admitted operation rowset differs from archived contracts",
                "23514",
            ),
            _refuse(
                conservative.is_distinct_from(expected_conservative),
                "read-only inspection admitted validity differs from archived contracts",
                "23514",
            ),
            Return(
                _object(
                    "payload",
                    _object(
                        "release_id",
                        p["release_id"].astext,
                        "model_digest",
                        projection["model_digest"].astext,
                        "native_digest",
                        projection["native_digest"].astext,
                        "conservative_operations",
                        conservative,
                    ),
                )
            ),
        ),
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("projection", pg_type("jsonb")),
            Local("archived", pg_type("jsonb")),
        ),
    )
    definition, runtime, retained = (
        _row("definition", definitions),
        _row("runtime", runtimes),
        core_variable("retained", JSONB()),
    )
    execution_inspection = _program(
        "inspect_data_execution",
        (Parameter("p_payload", pg_type("jsonb")),),
        (
            SelectInto(
                select(core_relation_row(definitions))
                .select_from(definitions)
                .where(
                    definitions.c.release_id == p["release_id"].astext,
                    definitions.c.operation_id == p["operation_id"].astext,
                ),
                ("definition",),
                True,
            ),
            If(
                p.has_key("runtime_id"),
                (
                    SelectInto(
                        select(core_relation_row(runtimes))
                        .select_from(runtimes)
                        .where(
                            runtimes.c.release_id == p["release_id"].astext,
                            runtimes.c.runtime_id == p["runtime_id"].astext,
                        ),
                        ("runtime",),
                        True,
                    ),
                    Assign(
                        "retained",
                        _object(
                            "manifest_sha256",
                            _hash(runtime["manifest_bytes"]),
                            "archive_sha256",
                            _hash(runtime["archive_bytes"]),
                        ),
                    ),
                ),
                (Assign("retained", cast(literal("null"), JSONB())),),
            ),
            Return(
                _object(
                    "payload",
                    _object(
                        "recipe",
                        definition["recipe"],
                        "profile",
                        definition["profile"],
                        "implementation_revision",
                        definition["implementation_revision"],
                        "input_roles",
                        definition["input_roles"],
                        "output_roles",
                        definition["output_roles"],
                        "runtime",
                        retained,
                    ),
                )
            ),
        ),
        (
            Local("p", pg_type("jsonb"), core_variable("p_payload", JSONB())),
            Local("definition", definitions),
            Local("runtime", runtimes),
            Local("retained", pg_type("jsonb")),
        ),
    )
    return release_inspection, execution_inspection


def _cpu_reply_program():
    evidence, value = core_variable("evidence", JSONB()), core_variable("value", JSONB())
    reply = core_variable("reply", Text())
    empty = cast(literal("[]"), JSONB())
    return _program(
        "ddo_cpu_reply_value",
        (Parameter("completion", pg_type("jsonb")),),
        (
            _refuse(
                or_(
                    func.jsonb_array_length(func.coalesce(evidence["cpu_receipts"], empty)) != 1,
                    func.jsonb_array_length(func.coalesce(evidence["cpu_replies"], empty)) != 1,
                    func.jsonb_typeof(evidence["cpu_replies"][0]).is_distinct_from("string"),
                ),
                "authority completion requires its actual CPU reply and original receipt",
                "23514",
            ),
            Assign("reply", evidence["cpu_replies"][0].astext),
            _refuse(
                _hash(func.convert_to(reply, "UTF8")).is_distinct_from(
                    evidence["cpu_receipts"][0]["result_digest"].astext
                ),
                "authority CPU reply differs from its original execution receipt",
                "23514",
            ),
            Assign("value", cast(reply, JSONB())),
            _refuse(
                func.jsonb_typeof(value).is_distinct_from("object"),
                "authority CPU reply lacks its declared object result",
                "23514",
            ),
            Return(value),
        ),
        (
            Local(
                "evidence",
                pg_type("jsonb"),
                core_variable("completion", JSONB())["execution_evidence"],
            ),
            Local("reply", pg_type("text")),
            Local("value", pg_type("jsonb")),
        ),
        volatility="immutable",
        security=False,
        strict=True,
    )


def _body_access_programs(model):
    kinds, products, members = (
        model.tables[name]
        for name in ("sem.data_kind_contract", "kb.data_product", "kb.data_product_member")
    )
    contract, universe = (
        core_variable("contract", kinds.c.kind_contract.type),
        core_variable("universe", kinds.c.universe.type),
    )
    kind_access = _program(
        "ddo_kind_access",
        (Parameter("contract", column_type(kinds.c.kind_contract)),),
        (
            SelectInto(
                select(kinds.c.universe).where(kinds.c.kind_contract == contract),
                ("universe",),
                True,
            ),
            Perform(func.ops.ddo_authorize(universe)),
            Return(true()),
        ),
        (Local("universe", column_type(kinds.c.universe)),),
        returns=pg_type("bool"),
    )
    p_kind, p_body = (
        core_variable("p_kind", kinds.c.kind_contract.type),
        core_variable("p_body", JSONB()),
    )
    kind, child_kind = _row("kind", kinds), _row("child_kind", kinds)
    packet, member_values, child_body = (
        core_variable(name, JSONB()) for name in ("packet", "members", "child_body")
    )
    child = core_variable("child", kinds.c.kind_contract.type)
    packets = _rows(member_values[1], "packets")
    set_text = pg_type("text")
    set_text.setof = True
    body_parameters = (
        Parameter("p_kind", column_type(kinds.c.kind_contract)),
        Parameter("p_body", pg_type("jsonb")),
    )
    admitted = core_variable("p_admitted", Boolean())
    body_contracts_impl = _program(
        "ddo_body_kind_contracts_impl",
        (*body_parameters, Parameter("p_admitted", pg_type("bool"))),
        (
            SelectInto(
                select(core_relation_row(kinds))
                .select_from(kinds)
                .where(kinds.c.kind_contract == p_kind),
                ("kind",),
                True,
            ),
            ReturnNext(p_kind),
            If(kind["member_schema"] == cast(literal('{"not":{}}'), JSONB()), (Return(),)),
            Assign("members", func.data.ddo_field(p_body, "members")),
            If(member_values.is_(None), (Return(),)),
            _refuse(
                member_values[0].astext.is_distinct_from("sequence"), "invalid nominal member body"
            ),
            ForQuery(
                ("packet",),
                select(packets.c.value),
                (
                    Assign(
                        "child",
                        func.data.ddo_field(packet, "kind_contract", type_=JSONB())[1].astext,
                    ),
                    Assign("child_body", func.data.ddo_field(packet, "body")),
                    _refuse(
                        or_(
                            child.is_(None),
                            child_body.is_(None),
                            not_(kind["member_contracts"].has_key(child)),
                        ),
                        "body member kind is outside its captured nominal contract",
                    ),
                    If(
                        admitted.is_distinct_from(True),
                        (
                            SelectInto(
                                select(core_relation_row(kinds))
                                .select_from(kinds)
                                .where(kinds.c.kind_contract == child),
                                ("child_kind",),
                                True,
                            ),
                            _refuse(
                                or_(
                                    not_(
                                        func.public.json_matches_schema(
                                            cast(child_kind["meaning_schema"], JSON()),
                                            cast(child_body, JSON()),
                                        )
                                    ),
                                    not_(
                                        func.public.json_matches_schema(
                                            cast(child_kind["body_schema"], JSON()),
                                            cast(func.data.ddo_json(child_body), JSON()),
                                        )
                                    ),
                                ),
                                "body member value differs from its captured nominal kind",
                            ),
                        ),
                    ),
                    ReturnQuery(
                        select(core_star()).select_from(
                            func.ops.ddo_body_kind_contracts_impl(child, child_body, admitted)
                        )
                    ),
                ),
            ),
        ),
        (
            Local("kind", kinds),
            Local("child_kind", kinds),
            *(Local(name, pg_type("jsonb")) for name in ("members", "packet", "child_body")),
            Local("child", column_type(kinds.c.kind_contract)),
        ),
        returns=set_text,
    )
    body_contracts = _program(
        "ddo_body_kind_contracts",
        body_parameters,
        (
            ReturnQuery(
                select(core_star()).select_from(
                    func.ops.ddo_body_kind_contracts_impl(p_kind, p_body, literal(False))
                )
            ),
        ),
        returns=set_text,
    )
    admitted_body_contracts = _program(
        "ddo_admitted_body_kind_contracts",
        body_parameters,
        (
            ReturnQuery(
                select(core_star()).select_from(
                    func.ops.ddo_body_kind_contracts_impl(p_kind, p_body, literal(True))
                )
            ),
        ),
        returns=set_text,
    )

    def access(name, kind_contracts, *, stored=False):
        contracts = (
            kind_contracts(p_kind, p_body)
            .table_valued(column("value", Text()))
            .render_derived(name="contracts")
        )
        authorization = select(contracts.c.value)
        if stored:
            authorization = authorization.distinct()
        return _program(
            name,
            body_parameters,
            (
                # The live evaluator purpose covers every admitted kind universe.
                *((If(evaluator_body_access(), (Return(true()),)),) if stored else ()),
                ForQuery(
                    ("contract",),
                    authorization,
                    (Perform(func.ops.ddo_kind_access(contract)),),
                ),
                Return(true()),
            ),
            (Local("contract", column_type(kinds.c.kind_contract)),),
            returns=pg_type("bool"),
        )

    body_access = access("ddo_body_access", func.ops.ddo_body_kind_contracts)
    admitted_body_access = access(
        "ddo_admitted_body_access", func.ops.ddo_admitted_body_kind_contracts, stored=True
    )
    binding, project = (
        core_variable("p_binding", JSONB()),
        core_variable("p_project", products.c.project_id.type),
    )
    inputs = _rows(binding["inputs"], "binding_inputs")
    selected = inputs.join(
        products,
        and_(
            products.c.id == inputs.c.value["product_id"].astext, products.c.project_id == project
        ),
    ).outerjoin(
        members,
        and_(
            members.c.product_id == products.c.id,
            members.c.member_id == inputs.c.value["member_id"].astext,
        ),
    )
    binding_access = _program(
        "ddo_binding_body_access",
        (
            Parameter("p_binding", pg_type("jsonb")),
            Parameter("p_project", column_type(products.c.project_id)),
        ),
        (
            PerformQuery(
                select(
                    func.ops.ddo_kind_access(products.c.kind_contract),
                    func.ops.ddo_admitted_body_access(
                        func.coalesce(members.c.kind_contract, products.c.kind_contract),
                        func.coalesce(members.c.body, products.c.canonical_body),
                    ),
                )
                .select_from(selected)
                .where(
                    or_(
                        inputs.c.value["member_id"].astext.is_(None),
                        members.c.member_id.is_not(None),
                    )
                )
            ),
            Return(true()),
        ),
        returns=pg_type("bool"),
    )
    return (
        kind_access,
        body_contracts_impl,
        body_contracts,
        admitted_body_contracts,
        body_access,
        admitted_body_access,
        binding_access,
    )


def _input_projection_programs(model, parameters, selected_rows):
    """Private whole-role parity read built on the existing binding authority."""
    empty = cast(literal("[]"), JSONB())

    def tag(kind, value):
        return func.jsonb_build_array(kind, value, type_=JSONB())

    def mapping(pairs):
        return tag("mapping", pairs)

    def pair(name, value):
        return func.jsonb_build_array(name, value, type_=JSONB())

    def tagged_fields(name, value):
        return mapping(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(pair(name, value), name.collate("C"))),
                empty,
            )
        )

    def text_rows(expression, name):
        return (
            func.jsonb_array_elements_text(expression)
            .table_valued(column("path", Text()))
            .render_derived(name=name)
        )

    # Select from the admitted tagged header so numeric kinds and explicit null
    # survive. An absent nested path contributes no synthetic enclosing record.
    header = core_variable("p_header", JSONB())
    paths = text_rows(core_variable("p_paths", JSONB()), "observed_paths")
    parent = func.split_part(paths.c.path, ".", 1)
    direct = parent == paths.c.path
    suffixes = (
        select(
            parent.label("field"),
            func.bool_or(direct).label("whole"),
            func.coalesce(
                func.jsonb_agg(func.substr(paths.c.path, func.length(parent) + 2)).filter(~direct),
                empty,
            ).label("suffixes"),
        )
        .group_by(parent)
        .subquery("selected_header_paths")
    )
    field = func.data.ddo_field(header, suffixes.c.field, type_=JSONB())
    selected_value = case(
        (suffixes.c.whole, field),
        else_=func.ops.ddo_input_projection_header(field, suffixes.c.suffixes, type_=JSONB()),
    )
    header_fields = select(tagged_fields(suffixes.c.field, selected_value)).where(
        field.is_not(None), or_(suffixes.c.whole, selected_value != mapping(empty))
    )
    header_projection = _program(
        "ddo_input_projection_header",
        (Parameter("p_header", pg_type("jsonb")), Parameter("p_paths", pg_type("jsonb"))),
        (
            If(header[0].astext.is_distinct_from("mapping"), (Return(mapping(empty)),)),
            Return(header_fields.scalar_subquery()),
        ),
        volatility="immutable",
        security=False,
    )

    demands = model.tables["ops.data_demand"]
    definitions = model.tables["sem.data_operation_definition"]
    partitions = model.tables["kb.data_product_partition"]
    binding_roles = _rows(definitions.c.input_roles, "binding_projection_role")
    projection = core_variable("projection", JSONB())
    actual_header = core_variable("admitted_header", JSONB())
    p_role = core_variable("p_role", Text())
    p_selected = core_variable("p_selected", JSONB())
    definition = (
        select(binding_roles.c.value["read_projection"])
        .select_from(
            demands.join(definitions, definitions.c.release_id == demands.c.release_id).join(
                binding_roles, true()
            )
        )
        .where(
            demands.c.id == core_variable("p_demand", Text()),
            definitions.c.operation_id == core_variable("p_operation", Text()),
            func.jsonb_array_length(definitions.c.input_roles) == 1,
            binding_roles.c.value["name"].astext == p_role,
            binding_roles.c.value["collection"].astext == "scalar",
            binding_roles.c.value["minimum"].astext == "1",
            binding_roles.c.value["maximum"].astext == "1",
        )
    )
    selected = selected_rows(decode=False)
    authorized_header = (
        select(selected.c.meaning_body)
        .where(
            selected.c.product == p_selected[0]["product_id"].astext,
            selected.c.member.is_(None),
        )
        .distinct()
    )
    collections = _rows(projection["collections"], "observed_collections")
    collection = collections.c.value
    groups = text_rows(collection["groups"], "observed_groups")
    group_fields = (
        select(
            tagged_fields(groups.c.path, tag("string", partitions.c.group_digests[groups.c.path]))
        )
        .select_from(groups)
        .correlate(partitions, collections)
        .scalar_subquery()
    )
    placement = mapping(
        func.jsonb_build_array(
            *(
                pair(name, tag("integer", partitions.c.placement[name].astext))
                for name in ("end", "start")
            )
        )
    )
    partition_fields = empty
    for name, value, observed in (
        ("groups", group_fields, func.jsonb_array_length(collection["groups"]) > 0),
        (
            "ordinal",
            tag("integer", cast(partitions.c.ordinal, Text())),
            collection["order"].astext == "true",
        ),
        (
            "partition_key",
            tag("string", partitions.c.partition_key),
            collection["membership"].astext == "true",
        ),
        ("placement", placement, collection["placement"].astext == "true"),
    ):
        partition_fields = partition_fields.concat(
            case((observed, func.jsonb_build_array(pair(name, value))), else_=empty)
        )
    partition_value = mapping(partition_fields)
    ordering = (
        case((collection["order"].astext == "true", partitions.c.ordinal), else_=0),
        func.convert_to(
            case(
                (collection["membership"].astext == "true", partitions.c.partition_key),
                else_=func.data.canonical_json(func.data.ddo_json(partition_value)),
            ),
            "UTF8",
        ),
    )
    collection_values = (
        select(
            tag(
                "sequence",
                func.coalesce(
                    func.jsonb_agg(aggregate_order_by(partition_value, *ordering)), empty
                ),
            )
        )
        .where(
            partitions.c.product_id == p_selected[0]["product_id"].astext,
            partitions.c.collection == collection["name"].astext,
        )
        .correlate(collections)
        .scalar_subquery()
    )
    projected_collections = select(
        tagged_fields(collection["name"].astext, collection_values)
    ).scalar_subquery()
    digest = func.data.ddo_identity(
        "input-projection-value",
        mapping(
            func.jsonb_build_array(
                pair("collections", projected_collections),
                pair(
                    "header",
                    func.ops.ddo_input_projection_header(actual_header, projection["header"]),
                ),
                pair("projection", tag("string", projection["fingerprint"])),
            )
        ),
        type_=Text(),
    )
    binding_projection = _program(
        "ddo_binding_input_projection_digest",
        (
            *parameters,
            Parameter("p_selected", pg_type("jsonb"), pg_literal(None)),
            Parameter("p_role", pg_type("text"), pg_literal(None)),
        ),
        (
            _refuse(
                or_(
                    func.jsonb_typeof(p_selected).is_distinct_from("array"),
                    func.jsonb_array_length(p_selected) != 1,
                    p_selected[0]["member_id"].astext.is_not(None),
                    p_selected[0]["product_id"].astext.is_(None),
                ),
                "input projection requires one exact whole-product pin",
                "23514",
            ),
            SelectInto(definition, ("projection",)),
            _refuse(
                or_(
                    projection["scope"].astext.is_distinct_from("whole"),
                    projection["version"].astext.is_distinct_from("1"),
                ),
                "input projection requires one declared scalar whole role",
                "23514",
            ),
            SelectInto(authorized_header, ("admitted_header",)),
            If(actual_header.is_(None), (Return(cast(null(), Text())),)),
            Return(digest),
        ),
        (Local("projection", pg_type("jsonb")), Local("admitted_header", pg_type("jsonb"))),
        returns=pg_type("text"),
    )
    return header_projection, binding_projection


def _binding_programs(model):
    demands, reads = model.tables["ops.data_demand"], model.tables["ops.data_demand_read"]
    p_demand, p_operation, p_read, p_subject = (
        core_variable(name, Text()) for name in ("p_demand", "p_operation", "p_read", "p_subject")
    )
    trust, source, scope = (
        core_variable(name, JSONB()) for name in ("p_trust", "p_source", "p_scope")
    )
    snapshot = core_variable("snapshot", JSONB())
    demand = _row("d", demands)
    operations = _rows(demand["selection"]["operations"], "selected_operations")
    parameters = (
        Parameter("p_demand", column_type(demands.c.id)),
        Parameter("p_operation", pg_type("text")),
        Parameter("p_trust", pg_type("jsonb")),
        Parameter("p_read", column_type(reads.c.id), pg_literal(None)),
        Parameter("p_subject", pg_type("text"), pg_literal(None)),
        Parameter("p_source", pg_type("jsonb"), pg_literal(None)),
        Parameter("p_scope", pg_type("jsonb"), pg_literal(None)),
    )
    columns = tuple(
        (field.name, column_type(Column(field.name, field.type))) for field in binding_columns()
    )
    set_record = pg_type("record")
    set_record.setof = True
    internal = _program(
        "ddo_binding_rows",
        (
            *parameters,
            Parameter("p_decode_body", pg_type("bool"), pg_literal(True)),
            Parameter("p_selected", pg_type("jsonb"), pg_literal(None)),
            Parameter("p_read_checked", pg_type("bool"), pg_literal(False)),
        ),
        (
            SelectInto(
                select(core_relation_row(demands))
                .select_from(demands)
                .where(demands.c.id == p_demand),
                ("d",),
                True,
            ),
            _refuse(p_read.is_(None), "binding requires exact native read acquisition"),
            SelectInto(
                select(core_relation_row(reads))
                .select_from(reads)
                .where(reads.c.id == p_read, reads.c.demand_id == demand["id"]),
                ("boundary",),
                True,
            ),
            If(
                core_variable("p_read_checked", Boolean()),
                (Assign("snapshot", trust),),
                (
                    Assign(
                        "snapshot",
                        func.ops.ddo_require_read_current(
                            core_variable("boundary", JSONB()), demand["project_id"]
                        ),
                    ),
                ),
            ),
            _refuse(
                not_(_exists(operations, operations.c.value["operation"].astext == p_operation)),
                "projection operation outside frozen demand",
            ),
            If(
                source.is_not(None),
                (
                    _refuse(
                        func.jsonb_typeof(source).not_in(("string", "null")),
                        "source filter requires JSON string or explicit null",
                        "23514",
                    ),
                    Perform(
                        func.ops.ddo_require_subject_source(
                            func.ops.ddo_release_subject_scopes(demand["release_id"]),
                            func.ops.ddo_operation_subject(demand["release_id"], p_operation),
                            source.op("#>>", return_type=Text())(array([], type_=Text())),
                        )
                    ),
                ),
            ),
            _refuse(
                func.ops.ddo_trust_snapshot_meaning(snapshot).is_distinct_from(
                    func.ops.ddo_trust_snapshot_meaning(trust)
                ),
                "binding trust snapshot changed",
            ),
            *(ReturnQuery(branch) for branch in binding_branches(model)),
        ),
        (Local("d", demands), Local("snapshot", pg_type("jsonb")), Local("boundary", reads)),
        returns=set_record,
        volatility="volatile",
        table_columns=columns,
    )

    def selected_rows(*, decode):
        return (
            func.ops.ddo_binding_rows(
                p_demand,
                p_operation,
                trust,
                p_read,
                p_subject,
                source,
                scope,
                decode,
                core_variable("p_selected", JSONB()),
            )
            .table_valued(*binding_columns())
            .alias("binding_rows")
        )

    rows = selected_rows(decode=True)
    public = _program(
        "data_binding_rows",
        (*parameters, Parameter("p_selected", pg_type("jsonb"), pg_literal(None))),
        (ReturnQuery(select(*rows.c)),),
        returns=set_record,
        table_columns=columns,
    )
    if "kb.data_product_partition" not in model.tables:
        return internal, public

    # Use the same authenticated binding projection, with the complete selected
    # pin set supplied explicitly, before touching any partition payload.
    selected = core_variable("p_selected", JSONB())
    bound = core_variable("p_max_bytes", BigInteger())
    collection_key = core_variable("p_collection", Text())
    partition_key = core_variable("p_partition_key", Text())
    rows = selected_rows(decode=False)
    parents = (
        select(rows.c.product)
        .where(rows.c.member.is_(None))
        .distinct()
        .cte("selected_partition_parents")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    partition = model.tables["kb.data_product_partition"]
    packet = _object(
        "collection",
        partition.c.collection,
        "partition_key",
        partition.c.partition_key,
        "ordinal",
        partition.c.ordinal,
        "partition_digest",
        partition.c.partition_digest,
        "placement",
        partition.c.placement,
        "body",
        partition.c.body,
    )
    selected_packets = (
        select(
            partition.c.product_id,
            partition.c.collection,
            partition.c.ordinal,
            packet.label("packet"),
        )
        .select_from(parents.join(partition, partition.c.product_id == parents.c.product))
        .where(
            or_(
                collection_key.is_(None),
                and_(
                    partition.c.collection == collection_key,
                    partition.c.partition_key == partition_key,
                ),
            )
        )
        .cte("selected_partition_packets")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    total_bytes = select(
        func.coalesce(func.sum(func.octet_length(cast(selected_packets.c.packet, Text()))), 0)
    ).scalar_subquery()
    # Return the size refusal as a single row so the same authorized selection
    # controls both sizing and acquisition in one statement.
    admitted_packets = (
        select(selected_packets.c.product_id, selected_packets.c.packet)
        .where(total_bytes <= bound)
        .order_by(
            selected_packets.c.product_id, selected_packets.c.collection, selected_packets.c.ordinal
        )
        .subquery("admitted_partition_packets")
    )
    packets = select(admitted_packets.c.product_id, admitted_packets.c.packet).union_all(
        select(cast(null(), Text()), cast(null(), JSONB())).where(total_bytes > bound)
    )
    partition_read = _program(
        "data_binding_partitions",
        (
            *parameters,
            Parameter("p_selected", pg_type("jsonb"), pg_literal(None)),
            Parameter("p_max_bytes", pg_type("bigint"), pg_literal(0)),
            Parameter("p_collection", pg_type("text"), pg_literal(None)),
            Parameter("p_partition_key", pg_type("text"), pg_literal(None)),
        ),
        (
            _refuse(
                or_(
                    func.jsonb_typeof(selected).is_distinct_from("array"),
                    func.jsonb_array_length(selected) == 0,
                    bound.is_(None),
                    bound <= 0,
                ),
                "partition hydration requires exact pins and positive capacity",
                "23514",
            ),
            _refuse(
                or_(
                    collection_key.is_(None).is_distinct_from(partition_key.is_(None)),
                    collection_key == "",
                    partition_key == "",
                    and_(collection_key.is_not(None), func.jsonb_array_length(selected) != 1),
                ),
                "partition lookup requires one exact pin and a complete collection address",
                "23514",
            ),
            ReturnQuery(packets),
        ),
        returns=set_record,
        table_columns=(("product_id", pg_type("text")), ("packet", pg_type("jsonb"))),
    )
    member_key = core_variable("p_member", Text())
    members = model.tables["kb.data_product_member"]
    member_row = (
        select(members.c.body)
        .select_from(parents.join(members, members.c.product_id == parents.c.product))
        .where(
            members.c.member_id == member_key,
            func.ops.ddo_body_access(members.c.kind_contract, members.c.body),
        )
    )
    reference_member = _program(
        "data_binding_reference_member",
        (
            *parameters,
            Parameter("p_selected", pg_type("jsonb"), pg_literal(None)),
            Parameter("p_member", pg_type("text"), pg_literal(None)),
        ),
        (
            _refuse(
                or_(
                    func.jsonb_typeof(selected).is_distinct_from("array"),
                    func.jsonb_array_length(selected) != 1,
                    member_key.is_(None),
                    member_key == "",
                ),
                "reference member lookup requires one exact parent and member address",
                "23514",
            ),
            Return(member_row.scalar_subquery()),
        ),
    )
    return (
        internal,
        public,
        partition_read,
        reference_member,
        *_input_projection_programs(model, parameters, selected_rows),
    )


def read_native_programs(model):
    """Declare the current inspection, nested access and selected binding readers."""
    from corpus_structure.schema.integrity import role_name

    from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess
    from .native_program_registry import ProgramDeclaration

    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=NativeProgramAccess(purposes=("read", "write", "evaluate"))
            if routine.name
            in {"data_binding_rows", "data_binding_partitions", "data_binding_reference_member"}
            else INTERNAL_PROGRAM,
        )
        for routine in (
            *_inspection_programs(model),
            _cpu_reply_program(),
            *_body_access_programs(model),
            *_binding_programs(model),
        )
    )


def read_native_sql(model) -> str:
    from .native_objects import native_sql_script

    return native_sql_script(item.render() for item in read_native_programs(model)) + "\n"
