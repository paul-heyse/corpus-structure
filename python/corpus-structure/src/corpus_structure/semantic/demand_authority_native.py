"""Generate release, demand and discovered-population authority checks."""

from typing import Literal, get_args

from pglast import ast
from sqlalchemy import (
    Boolean,
    Integer,
    MetaData,
    Text,
    and_,
    case,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .data_operation_model import ReplicatePolicy
from .data_operation_native_identity import native_identity_field
from .demand_registration_native import _items, _json, _owned_row, _refusal
from .native_objects import INTERNAL_PROGRAM, native_sql_script
from .native_program import (
    Block,
    Continue,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    PerformQuery,
    Return,
    SelectInto,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _param(name, *datatype):
    return Parameter(name, pg_type(*datatype))


def _routine(
    name,
    params,
    result,
    body,
    locals_=(),
    *,
    volatile: Literal["stable", "immutable", "volatile"] = "stable",
    definer=True,
    strict=False,
):
    return NativeRoutine(
        "ops",
        name,
        parameters=params,
        returns=result,
        body=Block(tuple(body), tuple(locals_)),
        search_path=("pg_catalog", "pg_temp"),
        volatility=volatile,
        security_definer=definer,
        strict=strict,
    )


def _query(name, params, kind, expression, *, strict=False):
    return NativeRoutine(
        "ops",
        name,
        parameters=params,
        returns=pg_type(kind),
        body=expression,
        search_path=("pg_catalog", "pg_temp"),
        volatility="stable",
        security_definer=True,
        strict=strict,
    )


def _subject_authority(model, scopes):
    definitions = model.tables["sem.data_operation_definition"]
    releases = model.tables["sem.data_operation_release"]
    subjects = model.tables["sem.data_subject_scope"]
    release, operation = (core_variable(name, Text()) for name in ("p_release", "p_operation"))
    scope_map = core_variable("scopes", JSONB())
    subject, original, scope, policy = (
        core_variable(name, Text()) for name in ("subject", "source", "scope_", "policy")
    )
    release_param = (_param("p_release", "text"),)
    return (
        _routine(
            "ddo_replicate_required",
            (_param("policy", "text"),),
            pg_type("bool"),
            (
                _refusal(
                    or_(policy.is_(None), policy.not_in(get_args(ReplicatePolicy))),
                    "unknown operation replicate policy",
                    "23514",
                ),
                Return(policy == "explicit-replicates"),
            ),
            volatile="immutable",
            definer=False,
        ),
        _query(
            "ddo_operation_subject",
            (*release_param, _param("p_operation", "text")),
            "text",
            select(definitions.c.subject_definition).where(
                definitions.c.release_id == release,
                definitions.c.operation_id == operation,
            ),
            strict=True,
        ),
        _routine(
            "ddo_require_release_facts",
            release_param,
            pg_type("sem", "data_operation_release"),
            (
                SelectInto(
                    select(core_relation_row(releases))
                    .select_from(releases)
                    .where(releases.c.release_id == release),
                    ("facts",),
                ),
                _refusal(
                    or_(
                        _owned_row("facts", releases, "release_id").is_(None),
                        _owned_row("facts", releases, "lowering_digest").is_distinct_from(
                            native_identity_field("lowering_digest")
                        ),
                    ),
                    "release facts require current authenticated re-lowering",
                    "23514",
                ),
                Return(core_variable("facts", NullType())),
            ),
            (Local("facts", releases),),
        ),
        _routine(
            "ddo_release_subject_scopes",
            release_param,
            pg_type("jsonb"),
            (
                Perform(func.ops.ddo_require_release_facts(release)),
                Return(
                    select(
                        func.coalesce(
                            func.jsonb_object_agg(
                                subjects.c.subject_definition,
                                subjects.c.scope,
                            ),
                            _json("{}"),
                        )
                    )
                    .where(subjects.c.release_id == release)
                    .scalar_subquery()
                ),
            ),
        ),
        _routine(
            "ddo_require_subject_source",
            tuple(
                _param(name, type_)
                for name, type_ in (("scopes", "jsonb"), ("subject", "text"), ("source", "text"))
            ),
            pg_type("void"),
            (
                _refusal(
                    or_(scope.is_(None), scope.not_in(scopes)),
                    "subject definition is outside checked release scopes",
                    "23514",
                ),
                _refusal(
                    or_(
                        original == "", and_(original.is_(None), scope.is_distinct_from("project"))
                    ),
                    "only a checked project subject can have no original source",
                    "23514",
                ),
            ),
            (Local("scope_", pg_type("text"), scope_map[subject].astext),),
            volatile="immutable",
            definer=False,
        ),
    )


def _population_authority(model):
    definitions = model.tables["sem.data_operation_definition"]
    populations = model.tables["ops.data_population"]
    requests = model.tables["ops.data_request"]
    episodes = model.tables["ops.data_derivation"]
    outputs = model.tables["ops.data_derivation_output"]
    demand = model.tables["ops.data_demand"]
    read = model.tables["ops.data_demand_read"]
    use = model.tables["ops.demand_use"]
    obligation = model.tables["ops.data_obligation"]
    population = _param("pop", "ops", populations.name)
    evidence = core_variable("evidence", JSONB())
    pop_evidence = _owned_row("pop", populations, "evidence")
    fields = ("operation_id", "subject", "subject_definition", "original_source", "analyzed_scope")

    def body(values):
        return func.jsonb_build_object(
            *(item for name, value in zip(fields, values, strict=True) for item in (name, value))
        )

    def producer_context(source):
        return (
            select(
                body(
                    (
                        requests.c.operation_id,
                        requests.c.subject,
                        func.ops.ddo_operation_subject(
                            requests.c.release_id, requests.c.operation_id
                        ),
                        requests.c.original_source,
                        requests.c.analyzed_scope,
                    )
                )
            )
            .select_from(
                episodes.join(
                    requests,
                    requests.c.id == episodes.c.request_id,
                )
            )
            .where(episodes.c.id == source["derivation_id"].astext)
        )

    def d(name):
        return _owned_row("d", demand, name)

    def pop(name):
        return _owned_row("pop", populations, name)

    target, input_role, subject, original = (
        core_variable(name, Text()) for name in ("target", "input_role", "subject", "source")
    )
    scope = core_variable("scope", JSONB())
    boundary = core_variable("boundary", NullType())
    relations = _items(d("selection")["discovery"], "relation")
    relation = relations.c.value
    declared = _items(definitions.c.input_roles, "declared_role").lateral()
    selected_role = declared.c.value
    source_field_role = (
        select(1)
        .select_from(definitions.join(declared, true()))
        .where(
            definitions.c.release_id == d("release_id"),
            definitions.c.operation_id == target,
            selected_role["name"].astext == input_role,
            selected_role["subject_target"].astext == "original-source",
            func.nullif(selected_role["subject_field"].astext, "").is_not(None),
        )
        .exists()
    )
    released_discovery = definitions.alias("released_discovery")
    declared_relation = (
        select(1)
        .select_from(
            relations.join(episodes, episodes.c.id == pop_evidence["derivation_id"].astext)
            .join(requests, requests.c.id == episodes.c.request_id)
            .join(use, use.c.id == pop_evidence["admission_use_id"].astext)
            .join(obligation, obligation.c.id == use.c.obligation_id)
            .join(
                released_discovery,
                and_(
                    released_discovery.c.release_id == d("release_id"),
                    released_discovery.c.operation_id == obligation.c.operation_id,
                    released_discovery.c.recipe == episodes.c.recipe,
                    released_discovery.c.profile == "discovery",
                ),
            )
            .join(
                outputs,
                and_(
                    outputs.c.derivation_id == episodes.c.id,
                    outputs.c.product_id == pop_evidence["product_id"].astext,
                ),
            )
        )
        .where(
            relation["target"].astext == target,
            or_(
                relation["target_role"].astext == input_role,
                and_(
                    relation["target_role"].astext.is_(None),
                    pop("complete"),
                    requests.c.original_source.is_not_distinct_from(original),
                    source_field_role,
                ),
            ),
            relation["population"].astext == pop("name"),
            relation["producer"].astext == requests.c.operation_id,
            relation["output_role"].astext == outputs.c.role,
            outputs.c.role == pop_evidence["member_role"].astext,
            requests.c.project_id == d("project_id"),
            use.c.demand_id == d("id"),
            use.c.derivation_id == episodes.c.id,
            use.c.fate == "fulfilled",
            obligation.c.demand_id == d("id"),
            obligation.c.operation_id == requests.c.operation_id,
            obligation.c.subject == requests.c.subject,
            obligation.c.original_source.is_not_distinct_from(requests.c.original_source),
            obligation.c.analyzed_scope == requests.c.analyzed_scope,
            or_(
                _owned_row("boundary", read, "id").is_(None),
                func.ops.ddo_read_visible(use.c.created_at, use.c.created_xid, boundary),
            ),
        )
        .exists()
    )
    members = _items(pop("members"), "member")
    member = members.c.value
    member_matches = (
        select(1)
        .select_from(members)
        .where(
            member["subject"].astext == subject,
            member["subject_definition"].astext
            == func.ops.ddo_operation_subject(d("release_id"), target),
            member["original_source"].astext.is_not_distinct_from(original),
            member["analyzed_scope"] == scope,
        )
        .exists()
    )
    return (
        _query(
            "ddo_population_producer_context",
            (population,),
            "jsonb",
            producer_context(pop_evidence),
        ),
        _query(
            "ddo_population_evidence_scope",
            (_param("evidence", "jsonb"),),
            "jsonb",
            select(
                case(
                    (
                        evidence.has_key("selection"),
                        body(tuple(evidence["selection"][name] for name in fields)),
                    ),
                    else_=producer_context(evidence).scalar_subquery(),
                )
            ),
        ),
        _query(
            "ddo_population_scope",
            (population,),
            "jsonb",
            select(func.ops.ddo_population_evidence_scope(pop_evidence)),
        ),
        _query(
            "ddo_discovery_role_population",
            (
                _param("d", "ops", demand.name),
                population,
                *(_param(name, "text") for name in ("target", "input_role", "subject", "source")),
                _param("scope", "jsonb"),
                Parameter("boundary", pg_type("ops", read.name), ast.A_Const(isnull=True)),
            ),
            "bool",
            select(
                and_(
                    pop("demand_id") == d("id"),
                    ~pop_evidence.has_key("selection"),
                    func.ops.ddo_node_valid("population", pop("id"), boundary),
                    or_(
                        _owned_row("boundary", read, "id").is_(None),
                        func.ops.ddo_read_visible(pop("created_at"), pop("created_xid"), boundary),
                    ),
                    declared_relation,
                    member_matches,
                )
            ),
        ),
    )


def _demand_authority(model):
    definitions = model.tables["sem.data_operation_definition"]
    requests = model.tables["ops.data_request"]
    demand = model.tables["ops.data_demand"]
    cancellations = model.tables["ops.data_demand_cancellation"]
    kinds = model.tables["sem.data_kind_contract"]
    uses = model.tables["ops.demand_use"]
    target = core_variable("demand", Text())
    request = _param("r", "ops", requests.name)
    request_tuple = core_variable("r", NullType())
    support = core_variable("support", JSONB())
    available = func.ops.ddo_support_available(request_tuple, support)
    contract = _owned_row("def", definitions, "support_contract")
    outcome = core_variable("outcome", Text())
    transitions = _items(func.coalesce(contract["transitions"], _json("[]")), "transition")
    row = transitions.c.value
    result = core_variable("result", Text())
    count = core_variable("n", Integer())
    roles = _items(
        definitions.c.input_roles.op("||", return_type=JSONB())(definitions.c.output_roles), "role"
    ).lateral()
    later = uses.alias("later")
    demand_parameter = (_param("demand", "text"),)
    return (
        _routine(
            "ddo_support_available",
            (request, _param("support", "jsonb")),
            pg_type("bool"),
            (
                Return(
                    func.ops.ddo_bound_support_available(
                        request_tuple, support, _owned_row("r", requests, "binding")
                    )
                ),
            ),
        ),
        _routine(
            "ddo_assert_support",
            (request, _param("support", "jsonb")),
            pg_type("void"),
            (_refusal(~available, "support is unavailable or revoked", "23514"),),
        ),
        _routine(
            "ddo_completion_state",
            (
                _param("def", "sem", definitions.name),
                _param("outcome", "text"),
            ),
            pg_type("text"),
            (
                _refusal(
                    ~contract["outcomes"].has_key(outcome),
                    "completion outcome is outside admitted operation contract",
                ),
                SelectInto(
                    select(func.count(), func.min(row["after"].astext))
                    .select_from(transitions)
                    .where(
                        row["dimension"].astext == "completion",
                        row["outcome"].astext == outcome,
                        row["before"].astext == "pending",
                        row["after"].astext.in_(("success", "empty", "failed")),
                        func.coalesce(row["effects"], _json("[]")) == _json("[]"),
                    ),
                    ("n", "result"),
                ),
                If(count == 1, (Return(result),)),
                _refusal(literal(True), "completion requires one declared terminal-state mapping"),
            ),
            (Local("n", pg_type("int4")), Local("result", pg_type("text"))),
            definer=False,
            strict=True,
            volatile="immutable",
        ),
        _routine(
            "ddo_authorize_request",
            (request,),
            pg_type("void"),
            (
                PerformQuery(
                    select(func.ops.ddo_authorize(kinds.c.universe))
                    .select_from(
                        definitions.join(roles, true()).join(
                            kinds, kinds.c.kind_contract == roles.c.value["kind_contract"].astext
                        )
                    )
                    .where(
                        definitions.c.release_id == _owned_row("r", requests, "release_id"),
                        definitions.c.operation_id == _owned_row("r", requests, "operation_id"),
                    )
                ),
            ),
        ),
        _query(
            "ddo_demand_active",
            demand_parameter,
            "bool",
            select(
                ~select(1)
                .select_from(cancellations)
                .where(cancellations.c.demand_id == target)
                .exists()
            ),
        ),
        _routine(
            "ddo_require_active_demand",
            demand_parameter,
            pg_type("void"),
            (
                PerformQuery(
                    select(1)
                    .select_from(demand)
                    .where(demand.c.id == target)
                    .with_for_update(read=True)
                ),
                _refusal(~func.ops.ddo_demand_active(target), "data demand is cancelled", "23514"),
            ),
            volatile="volatile",
        ),
        _query(
            "ddo_request_useful",
            (request,),
            "bool",
            select(
                select(1)
                .select_from(uses)
                .where(
                    uses.c.request_id == _owned_row("r", requests, "id"),
                    uses.c.generation == _owned_row("r", requests, "generation"),
                    uses.c.fate == "attached",
                    func.ops.ddo_demand_active(uses.c.demand_id),
                    ~select(1)
                    .select_from(later)
                    .where(
                        later.c.obligation_id == uses.c.obligation_id,
                        tuple_(later.c.created_at, later.c.id)
                        > tuple_(uses.c.created_at, uses.c.id),
                    )
                    .correlate(uses)
                    .exists(),
                )
                .exists()
            ),
        ),
    )


def demand_authority_programs(
    model: MetaData, *, subject_scopes: tuple[str, ...]
) -> tuple[ProgramDeclaration, ...]:
    routines = (
        *_subject_authority(model, subject_scopes),
        *_population_authority(model),
        _bound_support(model),
        *_demand_authority(model),
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in routines
    )


def demand_authority_sql(model: MetaData, *, subject_scopes: tuple[str, ...]) -> str:
    """Render the existing capture with an explicit lowering determinant."""
    return native_sql_script(
        declaration.routine.render()
        for declaration in demand_authority_programs(model, subject_scopes=subject_scopes)
    )


def _bound_support(model):
    requests = model.tables["ops.data_request"]
    episodes = model.tables["ops.data_derivation"]
    uses = model.tables["ops.demand_use"]
    originals = model.tables["ops.original_source_admission"]
    outputs = model.tables["ops.data_derivation_output"]
    definitions = model.tables["sem.data_operation_definition"]
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    populations = model.tables["ops.data_population"]
    demands = model.tables["ops.data_demand"]
    boundaries = model.tables["ops.data_demand_read"]
    support = core_variable("support", JSONB())
    binding = core_variable("binding", JSONB())
    item = core_variable("item", JSONB())
    rows = _items(support, "support")
    origin = item["kind"].astext
    role = item["role"].astext
    location = item["position"].astext
    selected_use = item["admission_use_id"].astext

    def r(name):
        return _owned_row("r", requests, name)

    def a(name):
        return _owned_row("original", originals, name)

    def episode(name):
        return _owned_row("episode", episodes, name)

    def select_model(row, field, value):
        return select(core_relation_row(row)).select_from(row).where(row.c[field] == value)

    definition = (
        definitions.c.release_id == r("release_id"),
        definitions.c.operation_id == r("operation_id"),
    )
    inputs = _items(binding["inputs"], "selected_input")
    chosen = inputs.c.value
    roles = _items(definitions.c.input_roles, "roledef").lateral()
    policy = roles.c.value
    input_definition = (
        inputs.join(
            products,
            products.c.id == chosen["product_id"].astext,
        )
        .join(definitions, and_(*definition))
        .join(roles, true())
    )
    authenticated_original = (
        select(1)
        .select_from(input_definition)
        .where(
            chosen["role"].astext == role,
            chosen["position"].astext.is_not_distinct_from(location),
            policy["name"].astext == chosen["role"].astext,
            products.c.id == a("product_id"),
            chosen["member_id"].astext.is_(None),
            products.c.original_source.is_not_distinct_from(r("original_source")),
            func.ops.ddo_binding_subject(
                policy,
                func.jsonb_build_object(
                    "subject",
                    products.c.subject,
                    "meaning_body",
                    products.c.canonical_body,
                ),
                r("subject"),
                r("original_source"),
            ),
            or_(
                policy["subject_field"].astext.is_not(None),
                a("analyzed_scope") == r("analyzed_scope"),
            ),
        )
        .exists()
    )
    selected_population = _items(binding["populations"], "reference")
    pop_ref = selected_population.c.value
    referenced_population = (
        select(1)
        .select_from(
            selected_population.join(
                populations,
                populations.c.id == pop_ref["population_id"].astext,
            )
        )
        .where(
            pop_ref["role"].astext == chosen["role"].astext,
            role == literal("population:").op("||")(populations.c.name),
            populations.c.evidence["derivation_id"].astext == episode("id"),
        )
        .correlate(inputs)
        .exists()
    )
    in_output = (
        select(1)
        .select_from(outputs)
        .where(
            outputs.c.derivation_id == episode("id"),
            outputs.c.product_id == products.c.id,
            or_(outputs.c.member_id.is_(None), outputs.c.member_id == chosen["member_id"].astext),
        )
        .correlate(inputs, products)
        .exists()
    )
    source_sets = (
        select(demands.c.selection["source_sets"])
        .select_from(demands.join(boundaries, boundaries.c.demand_id == demands.c.id))
        .where(boundaries.c.id == binding["read_id"].astext)
        .scalar_subquery()
    )
    qualified_value = func.jsonb_build_object(
        "product",
        products.c.id,
        "member",
        members.c.member_id,
        "subject",
        func.coalesce(members.c.subject, products.c.subject),
        "subject_definition",
        func.coalesce(members.c.subject_definition, products.c.subject_definition),
        "original_source",
        products.c.original_source,
        "analyzed_scope",
        func.coalesce(members.c.analyzed_scope, products.c.analyzed_scope),
        "meaning_body",
        func.coalesce(members.c.body, products.c.canonical_body),
        "support_references",
        func.jsonb_build_array(
            func.jsonb_build_object(
                "kind",
                "computation",
                "derivation_id",
                item["derivation_id"].astext,
                "admission_use_id",
                selected_use,
            )
        ),
        "support_evidence",
        func.jsonb_build_object("producer_output", chosen["producer_output"]),
    )
    qualified_cut = (
        select(1)
        .select_from(
            input_definition.outerjoin(
                members,
                and_(
                    members.c.product_id == products.c.id,
                    members.c.member_id == chosen["member_id"].astext,
                ),
            )
        )
        .where(
            policy["name"].astext == chosen["role"].astext,
            or_(role == chosen["role"].astext, referenced_population),
            in_output,
            func.ops.ddo_binding_source(
                policy,
                qualified_value,
                r("original_source"),
                func.coalesce(source_sets, _json("{}")),
            ),
        )
        .exists()
    )

    def field_check(required, optional=()):
        from sqlalchemy.dialects.postgresql import array

        return Perform(
            func.ops.ddo_fields(item, array(required, type_=Text()), array(optional, type_=Text()))
        )

    return _routine(
        "ddo_bound_support_available",
        (
            _param("r", "ops", requests.name),
            _param("support", "jsonb"),
            _param("binding", "jsonb"),
        ),
        pg_type("bool"),
        (
            _refusal(
                func.jsonb_typeof(support).is_distinct_from("array"),
                "support manifest must be array",
            ),
            ForQuery(
                ("item",),
                select(rows.c.value),
                (
                    If(
                        origin.in_(("original-source", "authored")),
                        (
                            field_check(
                                ("kind", "admission_id", "source_reference", "role", "position")
                            ),
                            SelectInto(
                                select_model(originals, "id", item["admission_id"].astext),
                                ("original",),
                            ),
                            _refusal(
                                or_(
                                    a("id").is_(None),
                                    origin.is_distinct_from(
                                        case(
                                            (
                                                a("reference")["kind"].astext == "authored-fact",
                                                "authored",
                                            ),
                                            else_="original-source",
                                        )
                                    ),
                                    a("project_id").is_distinct_from(r("project_id")),
                                    a("source_reference").is_distinct_from(
                                        item["source_reference"].astext
                                    ),
                                    ~authenticated_original,
                                ),
                                "original support differs from selected factual input custody",
                            ),
                            If(
                                ~func.ops.ddo_original_admission_valid(
                                    core_variable("original", NullType())
                                ),
                                (Return(literal(False)),),
                            ),
                            Continue(),
                        ),
                    ),
                    _refusal(
                        func.coalesce(origin, "computation") != "computation",
                        "unknown support reference origin",
                    ),
                    field_check(
                        ("derivation_id", "role", "position"), ("admission_use_id", "kind")
                    ),
                    SelectInto(
                        select_model(episodes, "id", item["derivation_id"].astext),
                        ("episode",),
                        strict=True,
                    ),
                    SelectInto(
                        select_model(requests, "id", episode("request_id")),
                        ("source_request",),
                        strict=True,
                    ),
                    _refusal(
                        _owned_row("source_request", requests, "project_id").is_distinct_from(
                            r("project_id")
                        ),
                        "support outside project custody",
                    ),
                    _refusal(
                        and_(
                            _owned_row(
                                "source_request", requests, "original_source"
                            ).is_distinct_from(r("original_source")),
                            ~qualified_cut,
                        ),
                        "foreign support outside exact frozen source-set custody",
                        "23514",
                    ),
                    If(
                        selected_use.is_(None),
                        (
                            If(
                                ~func.ops.ddo_node_valid("episode", episode("id")),
                                (Return(literal(False)),),
                            ),
                        ),
                        (
                            SelectInto(
                                select_model(uses, "id", selected_use).where(
                                    uses.c.derivation_id == episode("id")
                                ),
                                ("selected",),
                            ),
                            If(
                                or_(
                                    ~core_variable("found", Boolean()),
                                    ~func.ops.ddo_node_valid(
                                        "use", _owned_row("selected", uses, "id")
                                    ),
                                ),
                                (Return(literal(False)),),
                            ),
                        ),
                    ),
                ),
            ),
            Return(literal(True)),
        ),
        (
            Local("item", pg_type("jsonb")),
            Local("episode", episodes),
            Local("source_request", requests),
            Local("selected", uses),
            Local("original", originals),
        ),
    )
