"""Generate native demand intent registration from its graph and persistence model."""

from pglast import ast
from sqlalchemy import (
    BigInteger,
    Boolean,
    MetaData,
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
    union,
    union_all,
)
from sqlalchemy.dialects.postgresql import JSONB, array, insert

from corpus_structure.schema.integrity import role_name

from .data_operation_native_identity import native_identity_field
from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess, native_sql_script
from .native_program import (
    Assign,
    Block,
    ForQuery,
    GetRowCount,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _json(value):
    return cast(literal(value), JSONB())


def _items(value, name, *, text=False):
    function = func.jsonb_array_elements_text if text else func.jsonb_array_elements
    field = column("value", Text()) if text else column("value", JSONB())
    return function(value).table_valued(field).alias(name)


def _owned_row(variable, relation, name):
    return core_variable(variable, relation.c[name].type, name)


def _clock():
    return func.clock_timestamp()


def _xid():
    return cast(func.pg_current_xact_id(), Text())


def _identify(prefix, meaning):
    return literal(prefix).op("||")(func.ops.ddo_digest(meaning))


def _required(payload, *names):
    return Perform(func.ops.ddo_fields(payload, array(names, type_=Text())))


def _refusal(test, message, sqlstate="P0001"):
    return If(test, (Raise(message, sqlstate),))


def _operation_rows(selection):
    return _items(selection["operations"], "selected")


def _dependency_closure(initial, selected, name):
    closure = initial.cte(name, recursive=True)
    depends = _items(selected.c.value["dependencies"], name + "_dependency", text=True).lateral()
    return closure.union(
        select(depends.c.value).select_from(
            closure.join(selected, selected.c.value["operation"].astext == closure.c.id).join(
                depends, true()
            )
        )
    )


def _projection_difference(expected, declared):
    return (
        select(1)
        .select_from(expected.join(declared, expected.c.id == declared.c.id, full=True))
        .where(or_(expected.c.id.is_(None), declared.c.id.is_(None)))
        .exists()
    )


def dependency_selection_differs(required, potential, selected):
    dependencies = _items(selected, "local_dependency", text=True).lateral()
    offered = required.op("||", return_type=JSONB())(potential)
    return or_(
        ~required.bool_op("<@")(selected),
        select(1)
        .select_from(dependencies)
        .where(~offered.has_key(dependencies.c.value))
        .correlate_except(dependencies)
        .exists(),
        select(1)
        .select_from(dependencies)
        .group_by(dependencies.c.value)
        .having(func.count() != 1)
        .correlate_except(dependencies)
        .exists(),
    )


def _selected_graph_refusals(model, selection, operations, release):
    definitions = model.tables["sem.data_operation_definition"]
    kinds = model.tables["sem.data_kind_contract"]
    selected = operations.c.value
    chosen = selected["operation"].astext
    dependencies = _items(selected["dependencies"], "dependency", text=True).lateral()
    other = operations.alias("target")
    matched = operations.join(
        definitions,
        and_(
            definitions.c.release_id == release,
            definitions.c.operation_id == chosen,
        ),
    )
    mismatch = dependency_selection_differs(
        definitions.c.dependencies["required"],
        definitions.c.dependencies["potential"],
        selected["dependencies"],
    )
    missing_target = (
        ~select(1)
        .select_from(other)
        .where(other.c.value["operation"].astext == dependencies.c.value)
        .correlate(dependencies)
        .exists()
    )
    discovery = _items(selection["discovery"], "discovery")
    relation = discovery.c.value
    producer_kind = definitions.alias("producer")
    target_kind = definitions.alias("target_kind")
    output = _items(producer_kind.c.output_roles, "output_role").lateral()
    input_ = _items(target_kind.c.input_roles, "input_role").lateral()
    accepted = _items(input_.c.value["accepted_kind_contracts"], "accepted", text=True).lateral()
    kind_match = (
        select(1)
        .select_from(
            target_kind.join(input_, true())
            .join(
                producer_kind,
                and_(
                    producer_kind.c.release_id == target_kind.c.release_id,
                    producer_kind.c.operation_id == relation["producer"].astext,
                ),
            )
            .join(output, true())
            .join(kinds, kinds.c.kind_contract == output.c.value["kind_contract"].astext)
        )
        .where(
            target_kind.c.release_id == release,
            target_kind.c.operation_id == relation["target"].astext,
            input_.c.value["name"].astext == relation["target_role"].astext,
            output.c.value["name"].astext == relation["output_role"].astext,
            func.coalesce(
                input_.c.value["support"]["origins"], _json('["computation"]'), type_=JSONB()
            ).has_key("computation"),
            select(1)
            .select_from(accepted)
            .where(kinds.c.member_contracts.has_key(accepted.c.value))
            .correlate(input_, kinds)
            .exists(),
        )
        .correlate(discovery)
        .exists()
    )
    declared_outputs = _items(definitions.c.output_roles, "producer_output").lateral()
    producer = (
        select(1)
        .select_from(definitions)
        .where(
            definitions.c.release_id == release,
            definitions.c.operation_id == relation["producer"].astext,
            definitions.c.profile == "discovery",
            select(1)
            .select_from(declared_outputs)
            .where(declared_outputs.c.value["name"].astext == relation["output_role"].astext)
            .correlate(definitions, discovery)
            .exists(),
        )
        .correlate(discovery)
        .exists()
    )

    edges = (
        select(chosen.label("source"), dependencies.c.value.label("target"))
        .select_from(operations.join(dependencies, true()))
        .cte("edges")
    )
    reach = select(edges.c.source, edges.c.target).cte("reach", recursive=True)
    reach = reach.union(
        select(reach.c.source, edges.c.target).select_from(
            reach.join(edges, edges.c.source == reach.c.target)
        )
    )
    targets = _items(selection["targets"], "demand_target", text=True)
    all_targets = select(targets.c.value.label("id"))
    producers = select(relation["producer"].astext.label("id"))
    member_targets = select(relation["target"].astext.label("id"))
    roots = union(all_targets, producers).cte("roots")
    members = _dependency_closure(member_targets, operations, "member_closure")
    reachable_roots = _dependency_closure(select(roots.c.id), operations, "root_closure")
    expected_root = (
        select(reachable_roots.c.id)
        .where(
            or_(
                reachable_roots.c.id.in_(select(roots.c.id)),
                reachable_roots.c.id.not_in(select(members.c.id)),
            )
        )
        .subquery("root_expected")
    )
    declared_root = _items(selection["root_operations"], "root_operation", text=True)
    declared_root = select(declared_root.c.value.label("id")).subquery("declared_root")
    all_roots = union(all_targets, producers, member_targets).cte("all_roots")
    expected_full = _dependency_closure(select(all_roots.c.id), operations, "selected_closure")
    declared_full = select(chosen.label("id")).subquery("declared_operations")
    return (
        _refusal(
            or_(
                select(1)
                .select_from(operations)
                .group_by(chosen)
                .having(func.count() != 1)
                .exists(),
                select(1).select_from(matched).where(mismatch).exists(),
                select(1)
                .select_from(operations.join(dependencies, true()))
                .where(missing_target)
                .exists(),
            ),
            "selected dependencies differ from the authenticated declared graph",
        ),
        _refusal(
            or_(
                select(1)
                .select_from(discovery)
                .group_by(relation["population"].astext)
                .having(
                    func.count(
                        func.distinct(
                            func.jsonb_build_array(
                                relation["producer"].astext,
                                relation["output_role"].astext,
                            )
                        )
                    )
                    != 1
                )
                .exists(),
                select(1)
                .select_from(discovery)
                .group_by(relation)
                .having(func.count() != 1)
                .exists(),
            ),
            "discovery population requires one source projection and distinct targets",
        ),
        _refusal(
            select(1).select_from(discovery).where(~producer).exists(),
            "discovery relation differs from declared producer output",
        ),
        _refusal(
            or_(
                select(1)
                .select_from(discovery)
                .where(
                    relation.has_key("target_role"),
                    or_(
                        func.jsonb_typeof(relation["target_role"]).is_distinct_from("string"),
                        ~kind_match,
                    ),
                )
                .exists(),
                select(1)
                .select_from(discovery)
                .where(relation.has_key("target_role"))
                .group_by(relation["target"].astext, relation["target_role"].astext)
                .having(func.count() != 1)
                .exists(),
            ),
            "discovery target role differs from declared member/input contracts",
        ),
        _refusal(
            select(1).select_from(reach).where(reach.c.source == reach.c.target).exists(),
            "selected demand dependency cycle",
        ),
        _refusal(
            _projection_difference(expected_root, declared_root),
            "root operations differ from selected dependency closure",
        ),
        _refusal(
            _projection_difference(expected_full, declared_full),
            "selected operations differ from requested target/discovery closure",
        ),
    )


def _definition_roles(model, selection, release, *, output=True):
    definitions = model.tables["sem.data_operation_definition"]
    operations = _operation_rows(selection)
    raw_roles = definitions.c.input_roles
    if output:
        raw_roles = raw_roles.op("||", return_type=JSONB())(definitions.c.output_roles)
    roles = _items(raw_roles, "role").lateral()
    scoped = operations.join(
        definitions,
        and_(
            definitions.c.release_id == release,
            definitions.c.operation_id == operations.c.value["operation"].astext,
        ),
    ).join(roles, true())
    return roles, scoped


def _authorize_selection(model, selection, release):
    kinds = model.tables["sem.data_kind_contract"]
    roles, scoped = _definition_roles(model, selection, release)
    return PerformQuery(
        select(func.ops.ddo_authorize(kinds.c.universe)).select_from(
            scoped.join(kinds, kinds.c.kind_contract == roles.c.value["kind_contract"].astext)
        )
    )


def _demand_registration(model: MetaData) -> NativeRoutine:
    demand = model.tables["ops.data_demand"]
    project = model.tables["data.project"]
    release_row = model.tables["sem.data_operation_release"]
    definition = model.tables["sem.data_operation_definition"]
    artifact = model.tables["sem.artifact"]
    trust = model.tables["ops.data_trust_scope"]
    obligations = model.tables["ops.data_obligation"]
    payload = core_variable("p_payload", JSONB())
    selection = payload["selection"]
    project_id, release, runtime, strength = (
        payload[name].astext
        for name in (
            "project_id",
            "release_id",
            "runtime_id",
            "strength",
        )
    )
    demand_id = _owned_row("d", demand, "id")
    demand_root = _owned_row("d", demand, "root")
    demand_selection = _owned_row("d", demand, "selection")
    key = core_variable("key", demand.c.id.type)
    scopes = core_variable("subject_scopes", JSONB())
    root_context = core_variable("root_context", JSONB())
    subject_definition = _owned_row("selected_definition", definition, "subject_definition")
    inserted_count = core_variable("inserted_count", BigInteger())
    operations = _operation_rows(selection)
    selected = operations.c.value
    roots = _items(payload["root"], "requested_root")
    frozen_sources = func.coalesce(selection["source_sets"], _json("{}"), type_=JSONB())
    sources = (
        func.jsonb_each(frozen_sources)
        .table_valued(column("key", Text()), column("value", JSONB()))
        .alias("named_set")
    )
    source_entries = _items(sources.c.value["entries"], "source_entry").lateral()

    def matches_release(row):
        return row.c.release_id == release

    authenticated = (
        select(1)
        .select_from(definition)
        .where(
            matches_release(definition),
            definition.c.operation_id == selected["operation"].astext,
            definition.c.recipe == selected["recipe"].astext,
            definition.c.definition_identity == selected["definition"].astext,
            definition.c.eligibility_identity == selected["eligibility"].astext,
        )
        .correlate(operations)
        .exists()
    )
    content = cast(func.convert_from(artifact.c.content, "UTF8"), JSONB())
    compiled = _items(content["operations"], "compiled_operation").lateral()
    parameters = (
        select(func.ops.ddo_validate_parameters(compiled.c.value, selected, content))
        .select_from(
            artifact.join(compiled, true()).join(
                operations, selected["operation"].astext == compiled.c.value["semantic_id"].astext
            )
        )
        .where(matches_release(artifact), artifact.c.artifact_name == "data_operations.json")
    )
    replicate = (
        select(1)
        .select_from(
            operations.join(
                definition,
                and_(
                    matches_release(definition),
                    definition.c.operation_id == selected["operation"].astext,
                ),
            )
        )
        .where(
            or_(
                selected["replicate"].astext == "",
                func.ops.ddo_replicate_required(
                    definition.c.support_contract["replicate_policy"].astext
                ).is_distinct_from(selected["replicate"].astext.is_not(None)),
            )
        )
        .exists()
    )
    inputs, input_scope = _definition_roles(model, selection, release, output=False)
    episode_missing = (
        select(1)
        .select_from(input_scope)
        .where(~inputs.c.value["identity_requirements"].has_key("episode"))
        .exists()
    )
    root_definitions = (
        select(core_relation_row(definition))
        .select_from(definition)
        .where(
            matches_release(definition),
            selection["root_operations"].has_key(definition.c.operation_id),
        )
    )
    source_role = inputs.c.value["support"]["source_set"].astext
    source_set_differs = or_(
        select(1)
        .select_from(sources)
        .where(
            ~select(1)
            .select_from(input_scope)
            .where(source_role == sources.c.key)
            .correlate(sources)
            .exists()
        )
        .exists(),
        select(1)
        .select_from(input_scope)
        .where(source_role.is_not(None), ~frozen_sources.has_key(source_role))
        .exists(),
    )
    scoped_sources = union_all(
        select(roots.c.value.label("root")),
        select(source_entries.c.value).select_from(sources.join(source_entries, true())),
    ).subquery("scoped_sources")
    scope = func.ops.ddo_scope(project_id, scoped_sources.c.root["original_source"].astext).label(
        "scope"
    )
    initial_scopes = (
        select(scope, project_id, literal(0)).select_from(scoped_sources).distinct().order_by(scope)
    )
    create_scopes = (
        insert(trust)
        .from_select(("scope", "project_id", "epoch"), initial_scopes)
        .on_conflict_do_nothing()
    )
    create_demand = (
        insert(demand)
        .values(
            id=key,
            project_id=project_id,
            release_id=release,
            runtime_id=runtime,
            root=payload["root"],
            selection=selection,
            strength=strength,
            created_at=_clock(),
        )
        .on_conflict_do_nothing()
    )
    demand_roots = _items(demand_root, "root")
    demand_operations = _operation_rows(demand_selection)
    demand_operation = demand_operations.c.value
    obligation_payload = func.jsonb_build_object(
        "demand_id",
        demand_id,
        "operation_id",
        demand_operation["operation"].astext,
        "subject",
        demand_roots.c.value["subject"].astext,
        "original_source",
        demand_roots.c.value["original_source"].astext,
        "analyzed_scope",
        demand_roots.c.value["analyzed_scope"],
        "parameters",
        demand_operation["parameters"],
        type_=JSONB(),
    )
    qualification = (
        select(obligation_payload.label("payload"))
        .select_from(demand_roots.join(demand_operations, true()))
        .where(demand_selection["root_operations"].has_key(demand_operation["operation"].astext))
        .subquery("qualified")
    )
    intent = qualification.c.payload
    create_obligations = (
        insert(obligations)
        .from_select(
            (
                "id",
                "demand_id",
                "operation_id",
                "subject",
                "original_source",
                "analyzed_scope",
                "parameters",
                "created_at",
                "created_xid",
            ),
            select(
                _identify("obligation:", intent),
                demand_id,
                intent["operation_id"].astext,
                intent["subject"].astext,
                intent["original_source"].astext,
                intent["analyzed_scope"],
                intent["parameters"],
                _clock(),
                _xid(),
            )
            .select_from(qualification)
            .where(true()),
        )
        .on_conflict_do_nothing()
    )
    response = func.jsonb_build_object(
        "demand_id",
        demand_id,
        "selection",
        demand_selection,
        "inserted_obligations",
        inserted_count,
        type_=JSONB(),
    ).op("||")(
        case(
            (func.ops.ddo_demand_active(demand_id), _json("{}")),
            else_=func.jsonb_build_object("state", "cancelled"),
        )
    )
    return NativeRoutine(
        "ops",
        "register_data_demand",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                _required(
                    payload,
                    "project_id",
                    "release_id",
                    "runtime_id",
                    "root",
                    "selection",
                    "strength",
                ),
                _refusal(
                    or_(
                        ~select(1)
                        .select_from(project)
                        .where(project.c.project_id == project_id)
                        .exists(),
                        ~select(1)
                        .select_from(definition)
                        .where(matches_release(definition))
                        .exists(),
                        strength.not_in(("value", "episode", "independent")),
                    ),
                    "unadmitted demand/project/strength",
                ),
                _refusal(
                    or_(
                        selection["version"].astext.is_distinct_from("data-demand-intent-v2"),
                        payload["root"].is_distinct_from(selection["roots"]),
                        ~select(1)
                        .select_from(release_row)
                        .where(
                            matches_release(release_row),
                            release_row.c.lowering_digest
                            == native_identity_field("lowering_digest"),
                            release_row.c.model_digest == selection["model"].astext,
                        )
                        .exists(),
                        select(1).select_from(operations).where(~authenticated).exists(),
                    ),
                    "demand differs from authenticated effective model/selection",
                ),
                *_selected_graph_refusals(model, selection, operations, release),
                PerformQuery(parameters),
                _authorize_selection(model, selection, release),
                _refusal(
                    strength == "independent",
                    "independent strength requires declared distinct-episode replicate obligations",
                    "23514",
                ),
                _refusal(
                    replicate, "replicate selection differs from declared operation policy", "23514"
                ),
                _refusal(
                    and_(strength == "episode", episode_missing),
                    "episode strength requires episode-qualified input contracts",
                ),
                Assign("subject_scopes", func.ops.ddo_release_subject_scopes(release)),
                ForQuery(
                    ("root_context",),
                    select(roots.c.value),
                    (
                        ForQuery(
                            ("selected_definition",),
                            root_definitions,
                            (
                                Perform(
                                    func.ops.ddo_require_subject_source(
                                        scopes,
                                        subject_definition,
                                        root_context["original_source"].astext,
                                    )
                                ),
                            ),
                        ),
                    ),
                ),
                Perform(func.ops.ddo_validate_source_sets(frozen_sources, project_id, scopes)),
                Perform(func.ops.ddo_require_source_set_acquisitions(frozen_sources, project_id)),
                _refusal(
                    source_set_differs,
                    "frozen source sets differ from admitted selected role policies",
                ),
                Perform(func.sem.require_runtime_binding(release, runtime)),
                Assign("key", _identify("demand:", payload)),
                Sql(create_scopes),
                Sql(create_demand),
                SelectInto(
                    select(core_relation_row(demand)).select_from(demand).where(demand.c.id == key),
                    ("d",),
                    strict=True,
                ),
                Sql(create_obligations),
                GetRowCount("inserted_count"),
                Return(func.jsonb_build_object("payload", response)),
            ),
            (
                Local("key", pg_type("text")),
                Local("d", demand),
                Local("subject_scopes", pg_type("jsonb")),
                Local("root_context", pg_type("jsonb")),
                Local("selected_definition", definition),
                Local("inserted_count", pg_type("int8")),
            ),
        ),
    )


def _advance_demand_selection(model: MetaData) -> NativeRoutine:
    demand = model.tables["ops.data_demand"]
    history = model.tables["ops.data_demand_selection"]
    fields = (
        ("p_project", history.c.project_id),
        ("p_name", history.c.name),
        ("p_demand", history.c.demand_id),
        ("p_expected_demand", history.c.prior_demand_id),
        ("p_expected_generation", history.c.generation),
    )
    project, name, successor, prior, expected = (
        core_variable(parameter, column.type) for parameter, column in fields
    )
    generation = core_variable("next_generation", history.c.generation.type)
    scope = and_(history.c.project_id == project, history.c.name == name)
    row = select(core_relation_row(history)).select_from(history).where(scope)
    retained_demand = _owned_row("retained", history, "demand_id")
    retained_prior = _owned_row("retained", history, "prior_demand_id")
    current_generation = _owned_row("selection_head", history, "generation")
    current_demand = _owned_row("selection_head", history, "demand_id")
    stale = "stale named demand selection token"

    return NativeRoutine(
        "ops",
        "advance_demand_selection",
        parameters=tuple(Parameter(name, column_type(column)) for name, column in fields),
        returns=column_type(history.c.generation),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                Perform(func.sem.require_admission_caller()),
                _refusal(
                    func.current_setting("transaction_isolation").not_in(
                        ("read committed", "read uncommitted")
                    ),
                    "selection advancement requires a fresh read-committed snapshot",
                    "25000",
                ),
                _refusal(
                    or_(
                        func.nullif(project, "").is_(None),
                        func.nullif(name, "").is_(None),
                        func.nullif(successor, "").is_(None),
                        expected.is_(None),
                        ~expected.between(0, 2**63 - 2),
                        or_(
                            and_(expected == 0, prior.is_not(None)),
                            and_(expected > 0, func.nullif(prior, "").is_(None)),
                        ),
                    ),
                    "selection requires a named scope and exact predecessor token",
                    "22023",
                ),
                # A per-name transaction lock protects both the absent head and its
                # successors. A replay can inspect its completed generation before
                # checking current demand status or choosing new work.
                Perform(
                    func.pg_advisory_xact_lock(
                        func.hashtextextended(
                            cast(
                                func.jsonb_build_array("ops.data_demand_selection", project, name),
                                Text(),
                            ),
                            0,
                        )
                    )
                ),
                Assign("next_generation", expected + 1),
                SelectInto(row.where(history.c.generation == generation), ("retained",)),
                If(
                    core_variable("found", Boolean()),
                    (
                        _refusal(
                            or_(
                                retained_prior.is_distinct_from(prior),
                                retained_demand.is_distinct_from(successor),
                            ),
                            stale,
                            "40001",
                        ),
                        Return(generation),
                    ),
                ),
                SelectInto(row.order_by(history.c.generation.desc()).limit(1), ("selection_head",)),
                _refusal(
                    or_(
                        func.coalesce(current_generation, 0).is_distinct_from(expected),
                        current_demand.is_distinct_from(prior),
                    ),
                    stale,
                    "40001",
                ),
                _refusal(
                    successor.is_not_distinct_from(prior),
                    "selection advancement requires a different exact demand",
                    "22023",
                ),
                _refusal(
                    ~select(1)
                    .select_from(demand)
                    .where(demand.c.id == successor, demand.c.project_id == project)
                    .exists(),
                    "named selection requires an admitted demand in its project",
                    "23514",
                ),
                # The binding owner takes a shared demand lock before testing
                # cancellation. Cancellation takes that same row exclusively.
                Perform(func.ops.ddo_require_active_demand(successor)),
                Sql(
                    insert(history).values(
                        project_id=project,
                        name=name,
                        generation=generation,
                        prior_demand_id=prior,
                        demand_id=successor,
                        created_at=_clock(),
                        created_xid=_xid(),
                    )
                ),
                Return(generation),
            ),
            (
                Local("retained", history),
                Local("selection_head", history),
                Local("next_generation", column_type(history.c.generation)),
            ),
        ),
    )


def _cancel_demand(model: MetaData) -> NativeRoutine:
    from sqlalchemy import any_, update
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy.types import NullType

    from .data_operation_projections import cancellation_scopes

    demand = model.tables["ops.data_demand"]
    request = model.tables["ops.data_request"]
    obligations = model.tables["ops.data_obligation"]
    uses = model.tables["ops.demand_use"]
    cancellations = model.tables["ops.data_demand_cancellation"]
    trust = model.tables["ops.data_trust_scope"]
    read = model.tables["ops.data_demand_read"]
    tasks = model.tables["ops.task"]
    generations = model.tables["ops.data_request_generation"]
    payload = core_variable("p_payload", JSONB())
    demand_id, project, selection, release = (
        _owned_row("d", demand, name) for name in ("id", "project_id", "selection", "release_id")
    )
    request_id, generation, task_id = (
        _owned_row("r", request, name) for name in ("id", "generation", "live_task_id")
    )
    request_row = core_variable("r", NullType())
    obligation_id = _owned_row("o", obligations, "id")
    old_id, old_fate, old_request, old_generation, old_selection, old_trust = (
        _owned_row("old", uses, name)
        for name in ("id", "fate", "request_id", "generation", "selection", "trust_snapshot")
    )
    requested = core_variable("requests", JSONB())
    scope_key = core_variable("scope_key", trust.c.scope.type)
    scope_keys = core_variable("scope_keys", ARRAY(Text()))

    def row_query(row, *predicates):
        return select(core_relation_row(row)).select_from(row).where(*predicates)

    shares_request = (
        select(1)
        .select_from(uses)
        .where(
            uses.c.demand_id == demand_id,
            uses.c.request_id == request.c.id,
        )
        .correlate(request)
        .exists()
    )
    current_scopes = cancellation_scopes(model).subquery("required_scopes")
    selected_scopes = func.unnest(scope_keys).table_valued(column("scope", Text())).render_derived()
    retained = select(
        func.coalesce(
            func.array_agg(current_scopes.c.scope),
            array((), type_=Text()),
        )
    ).select_from(current_scopes)
    changed = (
        select(1)
        .select_from(current_scopes)
        .where(~(current_scopes.c.scope == any_(scope_keys)))
        .exists()
    )
    attach_cancel = (
        insert(uses)
        .values(
            id=_identify("use:", func.jsonb_build_array("cancel-demand", demand_id, obligation_id)),
            demand_id=demand_id,
            obligation_id=obligation_id,
            fate="cancelled",
            request_id=old_request,
            generation=old_generation,
            derivation_id=None,
            selection=func.coalesce(old_selection, _json("{}")),
            trust_snapshot=func.coalesce(old_trust, _json("{}")),
            created_at=_clock(),
            created_xid=_xid(),
        )
        .on_conflict_do_nothing()
    )
    cancellations_scope = uses.join(
        generations,
        and_(
            generations.c.request_id == uses.c.request_id,
            generations.c.generation == uses.c.generation,
        ),
    )
    cancelled_generations = (
        select(uses.c.request_id, uses.c.generation, generations.c.task_id)
        .select_from(cancellations_scope)
        .where(uses.c.demand_id == demand_id)
        .distinct()
        .order_by(uses.c.request_id, uses.c.generation)
    )
    selected_request = core_variable("generation_row", uses.c.request_id.type, "request_id")
    selected_generation = core_variable("generation_row", uses.c.generation.type, "generation")
    selected_task = core_variable("generation_row", generations.c.task_id.type, "task_id")
    relinquished = func.jsonb_build_object(
        "request_id",
        request_id,
        "generation",
        generation,
        "task_id",
        task_id,
        "interest",
        case((func.ops.ddo_request_useful(request_row), "shared"), else_="orphaned"),
        "physical_retirement",
        "unconfirmed",
    )
    reason = payload["reason"].astext
    reason_stored = _owned_row("cancellation", cancellations, "reason")
    array_type = pg_type("text")
    array_type.arrayBounds = (ast.Integer(ival=-1),)
    return NativeRoutine(
        "ops",
        "cancel_data_demand",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                _required(payload, "demand_id", "reason"),
                _refusal(func.nullif(reason, "").is_(None), "cancellation requires a reason"),
                SelectInto(
                    row_query(demand, demand.c.id == payload["demand_id"].astext),
                    ("d",),
                    strict=True,
                ),
                _authorize_selection(model, selection, release),
                Assign(("boundary", "read_snapshot"), cast(func.pg_current_snapshot(), Text())),
                Assign(("boundary", "frontier_at"), _clock()),
                Assign(("boundary", "owner_xid"), _xid()),
                SelectInto(retained, ("scope_keys",)),
                # Acquire trust scopes and only then lock demand, requests and tasks.
                ForQuery(
                    ("scope_key",),
                    select(selected_scopes.c.scope).order_by(selected_scopes.c.scope),
                    (
                        Sql(
                            insert(trust)
                            .values(scope=scope_key, project_id=project, epoch=0)
                            .on_conflict_do_nothing()
                        ),
                        PerformQuery(
                            select(1)
                            .select_from(trust)
                            .where(
                                trust.c.scope == scope_key,
                                trust.c.project_id == project,
                            )
                            .with_for_update(read=True)
                        ),
                    ),
                ),
                PerformQuery(
                    select(1).select_from(demand).where(demand.c.id == demand_id).with_for_update()
                ),
                Assign(("boundary", "read_snapshot"), cast(func.pg_current_snapshot(), Text())),
                Assign(("boundary", "frontier_at"), _clock()),
                _refusal(changed, "demand support changed during cancellation; retry", "40001"),
                PerformQuery(
                    select(1)
                    .select_from(request)
                    .where(shares_request)
                    .order_by(request.c.id)
                    .with_for_update()
                ),
                Sql(
                    insert(cancellations)
                    .values(
                        demand_id=demand_id,
                        reason=reason,
                        created_at=_clock(),
                        created_xid=_xid(),
                    )
                    .on_conflict_do_nothing()
                ),
                SelectInto(
                    row_query(cancellations, cancellations.c.demand_id == demand_id),
                    ("cancellation",),
                    strict=True,
                ),
                ForQuery(
                    ("o",),
                    row_query(obligations, obligations.c.demand_id == demand_id).order_by(
                        obligations.c.id
                    ),
                    (
                        SelectInto(
                            row_query(uses, uses.c.obligation_id == obligation_id)
                            .order_by(
                                uses.c.created_at.desc(),
                                uses.c.id.desc(),
                            )
                            .limit(1),
                            ("old",),
                        ),
                        If(
                            or_(
                                old_id.is_(None),
                                old_fate.not_in(
                                    ("fulfilled", "closed", "cancelled", "failed", "not-applicable")
                                ),
                            ),
                            (Sql(attach_cancel),),
                        ),
                    ),
                ),
                ForQuery(
                    ("r",),
                    row_query(request, shares_request).order_by(request.c.id),
                    (
                        If(
                            and_(~func.ops.ddo_request_useful(request_row), task_id.is_not(None)),
                            (
                                PerformQuery(
                                    select(1)
                                    .select_from(tasks)
                                    .where(tasks.c.id == task_id)
                                    .with_for_update()
                                ),
                                If(
                                    select(1)
                                    .select_from(tasks)
                                    .where(
                                        tasks.c.id == task_id,
                                        tasks.c.status.in_(("pending", "running")),
                                    )
                                    .exists(),
                                    (
                                        Sql(
                                            update(request)
                                            .where(request.c.id == request_id)
                                            .values(
                                                generation=request.c.generation + 1,
                                                live_task_id=None,
                                            )
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                ForQuery(
                    ("generation_row",),
                    cancelled_generations,
                    (
                        SelectInto(
                            row_query(request, request.c.id == selected_request),
                            ("r",),
                            strict=True,
                        ),
                        Assign(("r", "generation"), selected_generation),
                        Assign(("r", "live_task_id"), selected_task),
                        Assign(
                            "requests", requested.op("||")(func.jsonb_build_array(relinquished))
                        ),
                    ),
                ),
                Return(
                    func.jsonb_build_object(
                        "payload",
                        func.jsonb_build_object(
                            "demand_id",
                            demand_id,
                            "state",
                            "cancelled",
                            "reason",
                            reason_stored,
                            "requests",
                            requested,
                        ),
                    )
                ),
            ),
            (
                Local("d", demand),
                Local("r", request),
                Local("o", obligations),
                Local("old", uses),
                Local("cancellation", cancellations),
                Local("scope_key", pg_type("text")),
                Local("scope_keys", array_type),
                Local("boundary", read),
                Local("requests", pg_type("jsonb"), _json("[]")),
                Local("generation_row", pg_type("record")),
            ),
        ),
    )


def _record_fate(model: MetaData, recordable_fates: tuple[str, ...]) -> NativeRoutine:
    demands = model.tables["ops.data_demand"]
    obligations = model.tables["ops.data_obligation"]
    uses = model.tables["ops.demand_use"]
    definitions = model.tables["sem.data_operation_definition"]
    kinds = model.tables["sem.data_kind_contract"]
    payload = core_variable("p_payload", JSONB())
    demand, obligation, operation = (
        _owned_row("o", obligations, name) for name in ("demand_id", "id", "operation_id")
    )
    fate = payload["fate"].astext
    key = _identify("use:", payload)
    roles = _items(
        definitions.c.input_roles.op("||", return_type=JSONB())(definitions.c.output_roles),
        "role",
    ).lateral()
    resolved_kinds = (
        demands.join(
            definitions,
            and_(
                definitions.c.release_id == demands.c.release_id,
                definitions.c.operation_id == operation,
            ),
        )
        .join(roles, true())
        .join(kinds, kinds.c.kind_contract == roles.c.value["kind_contract"].astext)
    )
    return NativeRoutine(
        "ops",
        "record_data_fate",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                Perform(
                    func.ops.ddo_fields(
                        payload,
                        array(("obligation_id", "fate", "selection"), type_=Text()),
                        array(
                            ("request_id", "generation", "derivation_id", "trust_snapshot"),
                            type_=Text(),
                        ),
                    )
                ),
                SelectInto(
                    select(core_relation_row(obligations))
                    .select_from(obligations)
                    .where(
                        obligations.c.id == payload["obligation_id"].astext,
                    ),
                    ("o",),
                    strict=True,
                ),
                PerformQuery(
                    select(func.ops.ddo_authorize(kinds.c.universe))
                    .select_from(resolved_kinds)
                    .where(
                        demands.c.id == demand,
                    )
                ),
                Perform(func.ops.ddo_require_active_demand(demand)),
                _refusal(
                    fate.not_in(recordable_fates),
                    "native ownership required for fulfillment/attachment",
                ),
                Assign("key", key),
                Sql(
                    insert(uses)
                    .values(
                        id=core_variable("key", uses.c.id.type),
                        demand_id=demand,
                        obligation_id=obligation,
                        fate=fate,
                        request_id=None,
                        generation=None,
                        derivation_id=None,
                        selection=payload["selection"],
                        trust_snapshot=_json("{}"),
                        created_at=_clock(),
                        created_xid=_xid(),
                    )
                    .on_conflict_do_nothing()
                ),
                Return(
                    func.jsonb_build_object(
                        "payload",
                        func.jsonb_build_object(
                            "use_id",
                            core_variable("key", uses.c.id.type),
                            "fate",
                            fate,
                        ),
                    )
                ),
            ),
            (Local("o", obligations), Local("key", pg_type("text"))),
        ),
    )


def demand_intent_programs(model: MetaData, *, protocol: bytes) -> tuple[ProgramDeclaration, ...]:
    from .data_operation_protocol import protocol_value_sets

    routines = (
        _demand_registration(model),
        _cancel_demand(model),
        _record_fate(model, protocol_value_sets(protocol)["RecordableFate"]),
        _close_population(model),
    )
    commands = tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in routines
    )
    return (
        *commands,
        ProgramDeclaration(
            _advance_demand_selection(model),
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=NativeProgramAccess(purposes=("admit",)),
        ),
    )


def demand_intent_sql(model: MetaData, *, protocol: bytes) -> str:
    """Render captured intent programs before the owning wire-name projection."""
    return native_sql_script(
        declaration.routine.render()
        for declaration in demand_intent_programs(model, protocol=protocol)
    )


def _close_population(model: MetaData) -> NativeRoutine:
    from sqlalchemy.dialects.postgresql import aggregate_order_by

    demand = model.tables["ops.data_demand"]
    product = model.tables["kb.data_product"]
    derivation = model.tables["ops.data_derivation"]
    request = model.tables["ops.data_request"]
    populations = model.tables["ops.data_population"]
    occurrences = model.tables["kb.data_product_member"]
    obligations = model.tables["ops.data_obligation"]
    uses = model.tables["ops.demand_use"]
    definitions = model.tables["sem.data_operation_definition"]
    outputs = model.tables["ops.data_derivation_output"]
    kinds = model.tables["sem.data_kind_contract"]
    payload = core_variable("p_payload", JSONB())

    def demand_value(name):
        return _owned_row("d", demand, name)

    def product_value(name):
        return _owned_row("x", product, name)

    def request_value(name):
        return _owned_row("r", request, name)

    def admitted(name):
        return _owned_row("old", populations, name)

    product_id = product_value("id")
    derivation_id = _owned_row("producer", derivation, "id")
    request_id = _owned_row("producer", derivation, "request_id")
    demand_id = demand_value("id")
    selection = demand_value("selection")
    project_id = demand_value("project_id")
    release_id = demand_value("release_id")
    role = payload["member_role"].astext
    name = payload["name"].astext
    source_use = _owned_row("source_use", uses, "id")
    snapshot, members, evidence = (
        core_variable(field, JSONB()) for field in ("snapshot", "members", "evidence")
    )
    complete = core_variable("complete", Boolean())
    key, semantic_key = (core_variable(field, Text()) for field in ("key", "semantic_key"))
    count = core_variable("inserted_count", BigInteger())
    complete_json = func.data.ddo_json(
        func.data.ddo_field(product_value("canonical_body"), "complete"), type_=JSONB()
    )
    operation_id = _owned_row("source_obligation", obligations, "operation_id")
    discovery = _items(selection["discovery"], "relation")
    declared = discovery.c.value
    relevant = (
        select(declared.op("-")("target").op("-")("target_role"))
        .select_from(discovery)
        .where(
            declared["population"].astext == name,
            declared["producer"].astext == operation_id,
            declared["output_role"].astext == role,
        )
        .distinct()
    )

    def lookup(row, field, value):
        return select(core_relation_row(row)).select_from(row).where(row.c[field] == value)

    def acquire(row, name, field, value):
        return SelectInto(lookup(row, field, value), (name,), strict=True)

    def observed(row, *conditions):
        return select(1).select_from(row).where(*conditions).exists()

    custody = (uses.c.demand_id == demand_id, uses.c.derivation_id == derivation_id)
    active_use = func.ops.ddo_node_valid("use", uses.c.id)
    output_roles = _items(definitions.c.output_roles, "current_discovery_output")
    output_role = output_roles.c.value
    owned_members = occurrences.c.product_id == product_id
    coordinates = (
        "member_id",
        "subject",
        "subject_definition",
        "original_source",
        "analyzed_scope",
    )

    def packet(row, fields):
        return func.jsonb_build_object(
            *(item for field in fields for item in (field, row.c[field])), type_=JSONB()
        )

    member_rows = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(packet(occurrences, coordinates), occurrences.c.member_id)
                ),
                _json("[]"),
            )
        )
        .select_from(occurrences)
        .where(owned_members)
    )
    recorded = _items(members, "recorded")
    observed_member = recorded.c.value
    repeated = (
        select(1)
        .select_from(recorded)
        .group_by(
            observed_member["subject"].astext,
            observed_member["subject_definition"].astext,
            observed_member["original_source"].astext,
            observed_member["analyzed_scope"],
        )
        .having(func.count() != 1)
        .exists()
    )
    meaning = func.jsonb_build_object(
        "product",
        product_id,
        "member_role",
        role,
        "members",
        members,
        "complete",
        complete,
    )
    producer_context = func.jsonb_build_object(
        "operation_id",
        request_value("operation_id"),
        "subject",
        request_value("subject"),
        "subject_definition",
        func.ops.ddo_operation_subject(request_value("release_id"), operation_id),
        "original_source",
        request_value("original_source"),
        "analyzed_scope",
        request_value("analyzed_scope"),
    )
    basis = func.jsonb_build_object(
        "product_id",
        product_id,
        "derivation_id",
        derivation_id,
        "member_role",
        role,
        "admission_use_id",
        source_use,
        "trust_snapshot",
        snapshot,
        "producer_context",
        producer_context,
    )
    retained = (
        insert(populations)
        .values(
            id=key,
            demand_id=demand_id,
            semantic_key=semantic_key,
            name=name,
            context_key=func.ops.ddo_digest(func.ops.ddo_population_evidence_scope(evidence)),
            members=members,
            complete=complete,
            evidence=evidence,
            created_at=_clock(),
            created_xid=_xid(),
        )
        .on_conflict_do_nothing()
    )

    operations = _operation_rows(selection)
    selected = operations.c.value
    allowed = _dependency_closure(
        select(declared["target"].astext.label("id")).where(
            declared["population"].astext == admitted("name")
        ),
        operations,
        "allowed_operations",
    )
    members_set = _items(admitted("members"), "admitted_member")
    member = members_set.c.value
    qualified = (
        select(
            func.jsonb_build_object(
                "demand_id",
                demand_id,
                "operation_id",
                selected["operation"].astext,
                "subject",
                member["subject"].astext,
                "original_source",
                member["original_source"].astext,
                "analyzed_scope",
                member["analyzed_scope"],
                "parameters",
                selected["parameters"],
                type_=JSONB(),
            ).label("payload")
        )
        .select_from(
            members_set.join(operations, true()).join(
                allowed, allowed.c.id == selected["operation"].astext
            )
        )
        .where(
            member["subject_definition"].astext
            == func.ops.ddo_operation_subject(release_id, allowed.c.id)
        )
        .cte("qualified")
    )
    intent = qualified.c.payload
    subordinate = (
        insert(obligations)
        .from_select(
            (
                "id",
                "demand_id",
                "operation_id",
                "subject",
                "original_source",
                "analyzed_scope",
                "parameters",
                "created_at",
                "created_xid",
            ),
            select(
                _identify("obligation:", intent),
                demand_id,
                intent["operation_id"].astext,
                intent["subject"].astext,
                intent["original_source"].astext,
                intent["analyzed_scope"],
                intent["parameters"],
                _clock(),
                _xid(),
            )
            .select_from(qualified)
            .where(true()),
        )
        .on_conflict_do_nothing()
    )
    return NativeRoutine(
        "ops",
        "close_data_population",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                _required(
                    payload, "demand_id", "name", "product_id", "derivation_id", "member_role"
                ),
                acquire(demand, "d", "id", payload["demand_id"].astext),
                acquire(derivation, "producer", "id", payload["derivation_id"].astext),
                acquire(request, "r", "id", request_id),
                acquire(product, "x", "id", payload["product_id"].astext),
                Assign(
                    "snapshot",
                    func.ops.ddo_lock_support(
                        request_value("project_id"),
                        request_value("original_source"),
                        func.jsonb_build_array(
                            func.jsonb_build_object("derivation_id", derivation_id)
                        ),
                    ),
                ),
                Perform(func.ops.ddo_require_active_demand(demand_id)),
                SelectInto(
                    select(core_relation_row(uses))
                    .select_from(uses.join(obligations, obligations.c.id == uses.c.obligation_id))
                    .where(
                        *custody,
                        active_use,
                        uses.c.fate == "fulfilled",
                        obligations.c.demand_id == demand_id,
                        obligations.c.subject.is_not_distinct_from(product_value("subject")),
                        obligations.c.original_source.is_not_distinct_from(
                            product_value("original_source")
                        ),
                        obligations.c.analyzed_scope.is_not_distinct_from(
                            product_value("analyzed_scope")
                        ),
                        select(1)
                        .select_from(discovery)
                        .where(
                            declared["population"].astext == name,
                            declared["producer"].astext == obligations.c.operation_id,
                            declared["output_role"].astext == role,
                        )
                        .correlate(obligations)
                        .exists(),
                    )
                    .order_by(uses.c.created_at.desc(), uses.c.id.desc())
                    .limit(1),
                    ("source_use",),
                ),
                _refusal(
                    source_use.is_(None), "population lacks admitted declared discovery output"
                ),
                acquire(
                    obligations,
                    "source_obligation",
                    "id",
                    _owned_row("source_use", uses, "obligation_id"),
                ),
                SelectInto(relevant, ("relation_",), strict=True),
                _refusal(
                    or_(
                        product_value("project_id") != project_id,
                        request_value("project_id") != project_id,
                        _owned_row("source_obligation", obligations, "demand_id") != demand_id,
                        _owned_row("source_obligation", obligations, "subject").is_distinct_from(
                            product_value("subject")
                        ),
                        _owned_row(
                            "source_obligation", obligations, "original_source"
                        ).is_distinct_from(product_value("original_source")),
                        _owned_row(
                            "source_obligation", obligations, "analyzed_scope"
                        ).is_distinct_from(product_value("analyzed_scope")),
                        ~observed(
                            definitions,
                            definitions.c.release_id == release_id,
                            definitions.c.operation_id == operation_id,
                            definitions.c.profile == "discovery",
                            definitions.c.recipe == _owned_row("producer", derivation, "recipe"),
                            select(1)
                            .select_from(output_roles)
                            .where(
                                output_role["name"].astext == role,
                                output_role["kind_contract"].astext
                                == product_value("kind_contract"),
                            )
                            .exists(),
                        ),
                        ~observed(
                            outputs,
                            outputs.c.derivation_id == derivation_id,
                            outputs.c.product_id == product_id,
                            outputs.c.role == role,
                        ),
                    ),
                    "population lacks admitted declared discovery output",
                ),
                PerformQuery(
                    select(func.ops.ddo_authorize(kinds.c.universe))
                    .select_from(kinds)
                    .where(
                        kinds.c.kind_contract == product_value("kind_contract"),
                    )
                ),
                _refusal(
                    func.jsonb_typeof(complete_json).is_distinct_from("boolean"),
                    "discovery closure must declare complete boolean",
                ),
                Assign("complete", cast(complete_json[()].astext, Boolean())),
                _refusal(
                    observed(
                        occurrences,
                        owned_members,
                        or_(
                            func.nullif(occurrences.c.subject, "").is_(None),
                            func.nullif(occurrences.c.subject_definition, "").is_(None),
                            occurrences.c.original_source.is_distinct_from(
                                product_value("original_source")
                            ),
                            occurrences.c.analyzed_scope.is_(None),
                        ),
                    ),
                    "discovery member lacks qualified subject/source/scope",
                ),
                SelectInto(member_rows, ("members",)),
                _refusal(repeated, "discovery has ambiguous duplicate complete contexts"),
                Assign("semantic_key", _identify("population-value:", meaning)),
                Assign("evidence", basis),
                Assign(
                    "key",
                    _identify(
                        "population:",
                        func.jsonb_build_array(demand_id, name, semantic_key, evidence),
                    ),
                ),
                Assign(
                    "evidence", evidence.op("||")(func.jsonb_build_object("population_id", key))
                ),
                PerformQuery(
                    select(1).select_from(demand).where(demand.c.id == demand_id).with_for_update()
                ),
                Sql(retained),
                acquire(populations, "old", "id", key),
                _refusal(
                    ~func.ops.ddo_node_valid("population", admitted("id")),
                    "population witness is historical or no longer admitted",
                ),
                Sql(subordinate),
                GetRowCount("inserted_count"),
                Return(
                    func.jsonb_build_object(
                        "payload",
                        func.jsonb_build_object(
                            "inserted_obligations",
                            count,
                            "population_id",
                            key,
                            "semantic_key",
                            semantic_key,
                            "name",
                            admitted("name"),
                            "complete",
                            admitted("complete"),
                            "members",
                            admitted("members"),
                            "evidence",
                            admitted("evidence"),
                        ),
                    )
                ),
            ),
            (
                Local("d", demand),
                Local("x", product),
                Local("producer", derivation),
                Local("r", request),
                Local("relation_", pg_type("jsonb")),
                Local("members", pg_type("jsonb")),
                Local("complete", pg_type("bool")),
                Local("evidence", pg_type("jsonb")),
                Local("key", pg_type("text")),
                Local("old", populations),
                Local("snapshot", pg_type("jsonb")),
                Local("semantic_key", pg_type("text")),
                Local("source_use", uses),
                Local("source_obligation", obligations),
                Local("inserted_count", pg_type("int8")),
            ),
        ),
    )
