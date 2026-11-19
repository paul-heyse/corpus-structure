"""Compile protected grading custody over exact native cuts and reference passes."""

from pglast import ast
from pglast.stream import RawStream
from sqlalchemy import (
    BigInteger,
    Boolean,
    Integer,
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
    tuple_,
    union,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import NullType

from .data_operation_projections import (
    cut_selection_projection,
    read_page,
    record_grade_census_nodes,
    record_grade_selected_outputs,
)
from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    Continue,
    Exit,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    While,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .record_policy_authority import GRADE_KIND
from .validity_programs import selected_family

_READING = "resolve.m1_readings/declared"


def _json(value):
    return cast(literal(value), JSONB())


def _object(**fields):
    return func.jsonb_build_object(
        *(item for field in fields.items() for item in field), type_=JSONB()
    )


def _items(value, name, *, ordinal=False):
    field = column("value", JSONB())
    result = func.jsonb_array_elements(value)
    if ordinal:
        return result.table_valued(field, with_ordinality="ordinal").render_derived(name=name)
    return result.table_valued(field).alias(name)


def _rows(table, *predicates, source=None):
    return (
        select(core_relation_row(table))
        .select_from(table if source is None else source)
        .where(*predicates)
    )


def _field(local, table, name):
    return core_variable(local, table.c[name].type, name)


def _hash(value):
    return func.encode(func.sha256(func.convert_to(value, "UTF8")), "hex")


def _different(left, right, *names):
    return or_(*(left[name].astext.is_distinct_from(right[name].astext) for name in names))


def _refuse(condition, message):
    return If(condition, (Raise(message, "23514"),))


def _defined(
    schema, name, args, returns, *, body=None, query=None, locals_=(), columns=(), setof=False
):
    parameters = tuple(
        Parameter(label, pg_type(*type_.split(".")), *default) for label, type_, *default in args
    )
    output = pg_type(returns)
    output.setof = setof or bool(columns)
    table_columns = tuple((label, pg_type(type_)) for label, type_ in columns)
    if query is None:
        assert body is not None
        declaration = function(
            schema,
            name,
            body=Block(tuple(body), tuple(locals_)),
            table_columns=table_columns,
            parameters=parameters,
            returns=output,
            volatility="stable",
            search_path=("pg_catalog", "pg_temp"),
            security_definer=True,
        )
    else:
        declaration = sql_function(
            schema,
            name,
            body=query,
            table_columns=table_columns,
            parameters=parameters,
            returns=output,
            volatility="stable",
            search_path=("pg_catalog", "pg_temp"),
            security_definer=True,
        )
    identity = NativeIdentity(
        "function", schema, name, tuple(RawStream()(item.type_) for item in parameters)
    )
    return declaration, native_privilege_sql(identity, "PUBLIC", grant=False)


def _grade(name, args, returns, **body):
    return _defined("ops", "ddo_record_grade_" + name, args, returns, **body)


def _class_contract(model):
    archive = model.tables["sem.artifact"]
    finalized = model.tables["sem.release_finalization"]
    release, contract, class_ = (
        core_variable(name, Text()) for name in ("p_release", "p_contract", "p_class")
    )
    document = (
        select(cast(func.convert_from(archive.c.content, "UTF8"), JSONB()).label("body"))
        .select_from(archive.join(finalized, finalized.c.release_id == archive.c.release_id))
        .where(archive.c.release_id == release, archive.c.artifact_name == "data_operations.json")
        .cte("bound_model")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    kinds = _items(document.c.body["kinds"], "owned").lateral()
    identities = _items(document.c.body["identities"], "identity_").lateral()
    owner, identity = kinds.c.value, identities.c.value
    classes = (
        select(owner["semantic_id"].astext.label("semantic_id"))
        .select_from(document.join(kinds, true()))
        .where(
            or_(class_.is_(None), owner["name"].astext == class_),
            owner["category"].astext == "class",
            cast(owner["complete"].astext, Boolean()),
        )
        .cte("complete_classes")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    keys = (
        select(identity["owner"].astext.label("semantic_id"))
        .select_from(document.join(identities, true()))
        .where(identity["domain"].astext == "kind", identity["key"].astext == contract)
        .cte("class_contract_owners")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    return _defined(
        "sem",
        "ddo_model_class_contract",
        (
            ("p_release", "text"),
            ("p_contract", "text"),
            ("p_class", "text", ast.A_Const(isnull=True)),
        ),
        "bool",
        query=select(func.count() == 1).select_from(
            classes.join(keys, keys.c.semantic_id == classes.c.semantic_id)
        ),
    )


def _grade_inputs(model):
    products = model.tables["kb.data_product"]
    members = model.tables["kb.data_product_member"]
    requests = model.tables["ops.data_request"]
    project, product, member, role = (
        core_variable(name, Text()) for name in ("project", "product", "member", "role_name")
    )
    value = core_variable("value", JSONB())
    selected = core_variable("selected", JSONB())
    bindings = _items(_field("r", requests, "binding")["inputs"], "item")

    def field(name, member_name=None):
        return case((member.is_(None), products.c[name]), else_=members.c[member_name or name])

    result = _object(
        product_id=products.c.id,
        member_id=member,
        project_id=products.c.project_id,
        **{
            name: field(name)
            for name in ("kind_contract", "subject", "subject_definition", "original_source")
        },
        analyzed_scope_meaning=func.data.ddo_json_meaning(field("analyzed_scope")),
        body=func.data.ddo_json(field("canonical_body", "body")),
    )
    return (
        *_grade(
            "input_value",
            (("project", "text"), ("product", "text"), ("member", "text")),
            "jsonb",
            body=(
                SelectInto(
                    select(result)
                    .select_from(
                        products.outerjoin(
                            members,
                            and_(
                                members.c.product_id == products.c.id,
                                members.c.member_id == member,
                            ),
                        )
                    )
                    .where(
                        products.c.id == product,
                        products.c.project_id == project,
                        or_(member.is_(None), members.c.member_id.is_not(None)),
                    ),
                    ("value",),
                    strict=True,
                ),
                Return(value),
            ),
            locals_=(Local("value", pg_type("jsonb")),),
        ),
        *_grade(
            "input",
            (("r", "ops.data_request"), ("role_name", "text")),
            "jsonb",
            body=(
                SelectInto(
                    select(bindings.c.value).where(bindings.c.value["role"].astext == role),
                    ("selected",),
                    strict=True,
                ),
                _refuse(
                    or_(
                        selected["member_id"].astext.is_not(None),
                        cast(selected["multiplicity"].astext, Integer()) != 1,
                    ),
                    "record grade scalar role requires one whole actual product",
                ),
                Return(
                    func.ops.ddo_record_grade_input_value(
                        _field("r", requests, "project_id"),
                        selected["product_id"].astext,
                        None,
                    )
                ),
            ),
            locals_=(Local("selected", pg_type("jsonb")),),
        ),
    )


def _finite_census(model):
    definitions = model.tables["sem.data_operation_definition"]
    kinds = model.tables["sem.data_kind_contract"]
    demand = model.tables["ops.data_demand"]
    boundaries = model.tables["ops.data_demand_read"]
    episodes = model.tables["ops.data_derivation"]
    requests = model.tables["ops.data_request"]
    originals = model.tables["ops.original_source_admission"]
    products = model.tables["kb.data_product"]

    role = _items(
        definitions.c.input_roles.op("||", return_type=JSONB())(definitions.c.output_roles), "role"
    ).lateral()
    guarded = (
        select(1)
        .select_from(
            role.join(
                kinds,
                kinds.c.kind_contract == role.c.value["kind_contract"].astext,
            )
        )
        .where(kinds.c.universe == "evaluator")
        .correlate(definitions)
        .exists()
    )
    denied = or_(
        definitions.c.validity_families.contains(["record-grade"]),
        definitions.c.validity_families.contains(["record-fit"]),
        definitions.c.command_class == "policy",
        guarded,
    )
    requested = _items(_field("d", demand, "selection")["operations"], "requested")
    initial = (
        select(1)
        .select_from(
            requested.join(
                definitions,
                and_(
                    definitions.c.release_id == _field("d", demand, "release_id"),
                    definitions.c.operation_id == requested.c.value["operation"].astext,
                ),
            )
        )
        .where(denied)
        .exists()
    )
    node_kind, node_id = (core_variable("node", Text(), field) for field in ("kind", "id"))
    producer = (
        select(1)
        .select_from(
            episodes.join(requests, requests.c.id == episodes.c.request_id).join(
                definitions,
                and_(
                    definitions.c.release_id == episodes.c.release_id,
                    definitions.c.operation_id == requests.c.operation_id,
                ),
            )
        )
        .where(episodes.c.id == node_id, denied)
        .exists()
    )
    original = (
        select(1)
        .select_from(
            originals.join(products, products.c.id == originals.c.product_id).join(
                kinds, kinds.c.kind_contract == products.c.kind_contract
            )
        )
        .where(originals.c.id == node_id, kinds.c.universe == "evaluator")
        .exists()
    )
    return _grade(
        "require_finite_census",
        (("d", "ops.data_demand"), ("boundary", "ops.data_demand_read")),
        "void",
        body=(
            _refuse(initial, "record census cannot consume a protected judgment demand"),
            ForQuery(
                ("node",),
                record_grade_census_nodes(model),
                (
                    _refuse(
                        and_(node_kind == "episode", producer),
                        "record census support reaches a protected judgment",
                    ),
                    _refuse(
                        and_(node_kind == "original", original),
                        "record census source reaches a protected judgment",
                    ),
                ),
            ),
        ),
        locals_=(
            Local("p", pg_type("jsonb"), _object(scope=_field("boundary", boundaries, "scope"))),
            Local("node", pg_type("record")),
        ),
    )


def _cut_programs(model):
    demand = model.tables["ops.data_demand"]
    read = model.tables["ops.data_demand_read"]
    retained = model.tables["ops.data_demand_read_scope"]
    project, text, identity = (
        core_variable(name, Text()) for name in ("project", "cut_text", "cut_id")
    )
    captured = core_variable("captured", JSONB())
    actual = core_variable("actual", JSONB())
    boundary = core_variable("boundary", NullType())
    cut_args = (("project", "text"), ("cut_text", "text"))
    require_args = (*cut_args, ("cut_id", "text"))
    base_locals = (
        Local("captured", pg_type("jsonb"), cast(text, JSONB())),
        Local("d", demand),
        Local("boundary", read),
    )
    acquire = (
        SelectInto(
            _rows(
                demand, demand.c.id == captured["demand_id"].astext, demand.c.project_id == project
            ),
            ("d",),
            strict=True,
        ),
        SelectInto(
            _rows(
                read,
                read.c.id == captured["read_id"].astext,
                read.c.demand_id == _field("d", demand, "id"),
            ),
            ("boundary",),
            strict=True,
        ),
    )
    scope = _object(scope=_field("boundary", read, "scope"))
    results = core_variable("results", JSONB())

    def index(name, key):
        rows = _items(results["payload"][name], "page_rows")
        current = core_variable(name if name != "uses" else "uses_", JSONB())
        return select(
            current.op("||")(
                func.coalesce(
                    func.jsonb_object_agg(rows.c.value[key].astext, rows.c.value),
                    _json("{}"),
                )
            )
        ).select_from(rows)

    continuation = results["payload"]["continuation"]
    available = record_grade_selected_outputs(model).subquery("selected_output")
    outputs = select(
        func.coalesce(func.jsonb_agg(func.to_jsonb(available.table_valued())), _json("[]"))
    ).select_from(available)
    return (
        *_grade(
            "cut_scopes",
            cut_args,
            "text",
            setof=True,
            body=(
                *acquire,
                _refuse(
                    ~func.coalesce(func.ops.ddo_read_acquisition_present(boundary), False),
                    "record census requires read reacquisition",
                ),
                _refuse(
                    ~_field("boundary", read, "grade_census_eligible"),
                    "record census support reaches a protected judgment",
                ),
                Assign("p", scope),
                SelectInto(cut_selection_projection(), ("actual",)),
                _refuse(
                    captured.is_distinct_from(actual),
                    "record grade scope acquisition differs from actual project/cut",
                ),
                ReturnQuery(
                    select(retained.c.scope)
                    .where(
                        retained.c.read_id == _field("boundary", read, "id"),
                        retained.c.ordinary,
                    )
                    .order_by(retained.c.scope)
                ),
            ),
            locals_=(*base_locals, Local("p", pg_type("jsonb")), Local("actual", pg_type("jsonb"))),
        ),
        *_grade(
            "require_cut",
            require_args,
            "void",
            body=(
                Perform(func.ops.ddo_record_grade_cut_scopes(project, text)),
                _refuse(
                    identity.is_distinct_from(literal("cut-selection:").op("||")(_hash(text))),
                    "record grade differs from exact retained native cut",
                ),
                *acquire,
                Perform(func.ops.ddo_require_read_current(boundary, project, True)),
            ),
            locals_=base_locals,
        ),
        *_grade(
            "acquire_census",
            require_args,
            "jsonb",
            body=(
                Perform(func.ops.ddo_record_grade_require_cut(project, text, identity)),
                *acquire,
                Assign("p", scope),
                While(
                    literal(True),
                    (
                        SelectInto(read_page(model), ("results",)),
                        SelectInto(index("obligations", "obligation_id"), ("obligations",)),
                        SelectInto(index("uses", "use_id"), ("uses_",)),
                        If(or_(continuation.is_(None), continuation == _json("null")), (Exit(),)),
                        Assign("after_key", continuation["after"].astext),
                    ),
                ),
                SelectInto(outputs, ("outputs",)),
                Return(
                    _object(
                        **{
                            label: core_variable(name, JSONB())
                            for label, name in (
                                ("obligations", "obligations"),
                                ("uses", "uses_"),
                                ("outputs", "outputs"),
                            )
                        }
                    )
                ),
            ),
            locals_=(
                *base_locals,
                Local("p", pg_type("jsonb")),
                Local("results", pg_type("jsonb")),
                Local("obligations", pg_type("jsonb"), _json("{}")),
                Local("uses_", pg_type("jsonb"), _json("{}")),
                Local("outputs", pg_type("jsonb")),
                Local("lim", pg_type("int8"), literal(1000)),
                Local("after_key", pg_type("text"), literal("")),
                Local("selected_view", pg_type("text"), literal("frontier")),
                Local("selected_max_bytes", pg_type("int8"), literal(64 * 1024**2)),
            ),
        ),
    )


def _request_cut_programs(model):
    requests = model.tables["ops.data_request"]
    episodes = model.tables["ops.data_derivation"]
    intents = model.tables["ops.data_completion_intent"]
    receipts = model.tables["ops.data_publication_receipt"]
    r = core_variable("r", NullType())
    operation, project, binding = (
        _field("r", requests, field) for field in ("operation_id", "project_id", "binding")
    )
    skip = If(
        ~selected_family(model, _field("r", requests, "release_id"), operation, "record-grade"),
        (Return(),),
    )
    specification, references, selection, question = (
        core_variable(name, JSONB())
        for name in ("specification", "references_", "selection_", "question_")
    )
    predictions = _items(specification["prediction_selections"], "predictions")
    questions = _items(references["references"], "references")
    question_row = questions.c.value["question"]
    selected_cut = cast(selection["cut_canonical_json"].astext, JSONB())
    source_cut = cast(question["source_cut_canonical_json"].astext, JSONB())
    cut_columns = (("cut_text", "text"), ("cut_id", "text"))
    request_parameters = (("r", "ops.data_request"),)
    cuts = func.ops.ddo_record_grade_cuts(r).table_valued(
        column("cut_text", Text()), column("cut_id", Text())
    )
    cut_text = core_variable("captured", Text(), "cut_text")
    cut_id = core_variable("captured", Text(), "cut_id")
    scopes = (
        func.ops.ddo_record_grade_cut_scopes(project, cut_text)
        .table_valued(column("scope", Text()))
        .render_derived()
    )
    completion_scopes = (
        func.ops.ddo_record_grade_completion_scopes(r)
        .table_valued(column("scope", Text()))
        .render_derived()
    )
    episode = core_variable("episode", Text())

    def producer(field):
        return _field("producing", episodes, field)

    def intent(field):
        return _field("intent", intents, field)

    acquired = (
        SelectInto(_rows(episodes, episodes.c.id == episode), ("producing",), strict=True),
        SelectInto(_rows(requests, requests.c.id == producer("request_id")), ("r",), strict=True),
    )
    intent_filter = (
        intents.c.id == producer("intent_id"),
        intents.c.request_id == producer("request_id"),
        intents.c.generation == producer("generation"),
    )
    intent_payload = intent("payload")
    return (
        *_grade(
            "cuts",
            request_parameters,
            "record",
            columns=cut_columns,
            body=(
                skip,
                Assign(
                    "specification",
                    func.ops.ddo_record_grade_input(r, "specification", type_=JSONB())["body"],
                ),
                Assign(
                    "references_",
                    func.ops.ddo_record_grade_input(r, "adjudication", type_=JSONB())["body"],
                ),
                ForQuery(
                    ("selection_",),
                    select(predictions.c.value),
                    (
                        _refuse(
                            or_(
                                selection["project_id"].astext.is_distinct_from(project),
                                _different(
                                    selected_cut, selection, "project_id", "demand_id", "read_id"
                                ),
                            ),
                            "record census selection differs from exact cut/project/read pins",
                        ),
                    ),
                ),
                ForQuery(
                    ("question_",),
                    select(question_row),
                    (
                        _refuse(
                            or_(
                                question["project_id"].astext.is_distinct_from(project),
                                source_cut["project_id"].astext.is_distinct_from(project),
                                source_cut["release_id"].astext.is_distinct_from(
                                    question["source_release_id"].astext
                                ),
                            ),
                            "record source question differs from original project/release cut",
                        ),
                    ),
                ),
                ReturnQuery(
                    union(
                        select(
                            question_row["source_cut_canonical_json"].astext,
                            question_row["source_cut_id"].astext,
                        ),
                        select(
                            predictions.c.value["cut_canonical_json"].astext,
                            predictions.c.value["expected_cut"].astext,
                        ),
                    )
                ),
            ),
            locals_=tuple(
                Local(name, pg_type("jsonb"))
                for name in ("specification", "references_", "selection_", "question_")
            ),
        ),
        *_grade(
            "completion_scopes",
            request_parameters,
            "text",
            setof=True,
            body=(
                skip,
                ForQuery(("captured",), select(cuts), (ReturnQuery(select(scopes.c.scope)),)),
            ),
            locals_=(Local("captured", pg_type("record")),),
        ),
        *_grade(
            "dependency_scopes",
            (("episode", "text"),),
            "text",
            setof=True,
            body=(
                *acquired,
                skip,
                SelectInto(_rows(intents, *intent_filter), ("intent",), strict=True),
                _refuse(
                    tuple_(
                        *(
                            intent(name)
                            for name in ("producer_task_id", "producer_attempt", "runtime_id")
                        )
                    ).is_distinct_from(
                        tuple_(
                            *(
                                producer(name)
                                for name in ("producer_task_id", "producer_attempt", "runtime_id")
                            )
                        )
                    ),
                    "grade dependency scopes differ from original producer fences",
                ),
                *(
                    Assign(("r", name), producer(name))
                    for name in ("release_id", "runtime_id", "recipe", "generation")
                ),
                Assign(
                    ("r", "binding"),
                    binding.op("||")(
                        _object(inputs=intent_payload["inputs"], support=intent_payload["support"])
                    ),
                ),
                ReturnQuery(select(completion_scopes.c.scope)),
            ),
            locals_=(Local("r", requests), Local("producing", episodes), Local("intent", intents)),
        ),
        *_grade(
            "dependencies_valid",
            (("episode", "text"),),
            "bool",
            body=(
                CatchDependencyInvalidity(
                    (
                        *acquired,
                        If(
                            ~selected_family(
                                model,
                                _field("r", requests, "release_id"),
                                operation,
                                "record-grade",
                            ),
                            (Return(literal(True)),),
                        ),
                        SelectInto(
                            _rows(
                                intents,
                                *intent_filter,
                                source=intents.join(
                                    receipts,
                                    and_(
                                        receipts.c.derivation_id == producer("id"),
                                        receipts.c.intent_id == intents.c.id,
                                    ),
                                ),
                            ),
                            ("intent",),
                            strict=True,
                        ),
                        Assign(
                            "r",
                            func.ops.ddo_require_episode_correspondence(
                                core_variable("producing", NullType()),
                                core_variable("intent", NullType()),
                            ),
                        ),
                        ForQuery(
                            ("captured",),
                            select(cuts),
                            (
                                Perform(
                                    func.ops.ddo_record_grade_require_cut(project, cut_text, cut_id)
                                ),
                            ),
                        ),
                        Return(literal(True)),
                    ),
                    (Return(literal(False)),),
                ),
            ),
            locals_=(
                Local("r", requests),
                Local("producing", episodes),
                Local("intent", intents),
                Local("captured", pg_type("record")),
            ),
        ),
    )


def _frame_program(model: MetaData):
    requests = model.tables["ops.data_request"]
    episodes = model.tables["ops.data_derivation"]
    definitions = model.tables["sem.data_operation_definition"]
    outputs = model.tables["ops.data_derivation_output"]
    receipts = model.tables["ops.data_publication_receipt"]
    intents = model.tables["ops.data_completion_intent"]
    products = model.tables["kb.data_product"]
    r = core_variable("r", NullType())
    project = _field("r", requests, "project_id")
    binding = _field("r", requests, "binding")
    grade = core_variable("grade", JSONB())
    values = (
        "a",
        "b",
        "c",
        "specification",
        "frame",
        "question",
        "selected",
        "source_census",
        "prediction_census",
        "u",
        "obligation",
        "cuts",
        "predicted",
        "carrier",
        "candidate",
        "event",
        "actual_event",
        "coverage",
        "ref",
        "pin",
        "bound",
        "pins",
        "sources_",
        "reading_completion",
        "reading_body",
        "verified_readings",
    )
    j = {name: core_variable(name, JSONB()) for name in values}
    a, b, c, specification, frame = (j[name] for name in ("a", "b", "c", "specification", "frame"))
    question, selected, bound, ref, pin = (
        j[name] for name in ("question", "selected", "bound", "ref", "pin")
    )
    source_census, prediction_census, u, obligation = (
        j[name] for name in ("source_census", "prediction_census", "u", "obligation")
    )
    coverage, predicted, carrier, candidate, event, actual_event = (
        j[name]
        for name in ("coverage", "predicted", "carrier", "candidate", "event", "actual_event")
    )
    cuts, pins, sources, verified = (
        j[name] for name in ("cuts", "pins", "sources_", "verified_readings")
    )
    n = core_variable("n", BigInteger())
    events, completed = (
        core_variable(name, Integer()) for name in ("event_count", "selected_count")
    )
    reading_key = core_variable("reading_key", Text())
    index = cast(n - 1, Integer())
    references = c["body"]["references"]
    passes = (
        select(cast(literal("A"), Text()).label("pass_kind"), a.label("pass_value"))
        .union_all(
            select(cast(literal("B"), Text()), b),
            select(cast(literal("C"), Text()), c),
        )
        .subquery("passes")
    )
    pass_kind = core_variable("pass_row", Text(), "pass_kind")
    pass_value = core_variable("pass_row", JSONB(), "pass_value")
    pass_ref = bound["body"]["references"][index]
    reference_pass = _items(frame["reference_passes"], "reference_pass")
    cut = func.ops.ddo_record_grade_cuts(r).table_valued(
        column("cut_text", Text()), column("cut_id", Text())
    )
    cut_text = core_variable("captured", Text(), "cut_text")
    cut_id = core_variable("captured", Text(), "cut_id")
    canonical_frame = grade["frame_canonical_json"].astext
    selection_cut = cast(selected["cut_canonical_json"].astext, JSONB())
    question_source = question["source"]
    reference_pins = _items(
        func.jsonb_build_array(question_source, type_=JSONB()).op("||")(
            func.coalesce(
                cast(question["frame_canonical_json"].astext, JSONB())["related_pins"], _json("[]")
            )
        ),
        "reference_pin",
    )
    bound_inputs = _items(binding["inputs"], "bound_input")
    prior_pins = _items(pins, "previous")
    used_source = _items(source_census["outputs"], "source_output")
    bound_support = _items(binding["support"], "bound_support")
    carrier_members = _items(carrier["members"], "packet")
    body = carrier_members.c.value["body"]
    eligible = and_(
        body["candidate_type"].astext == "record",
        body["family"].astext == question["family"].astext,
    )
    frame_events = _items(frame["events"], "frame_event")
    carrier_events = _items(
        cast(carrier["diagnostics_json"].astext, JSONB())["record_policy_events"], "carrier_event"
    )
    interpretation = candidate["interpretation_id"].astext
    record = candidate["record_id"].astext
    source_projection = predicted["body"]["source"]

    def producer(name):
        return _field("producer", episodes, name)

    def reading(name):
        return _field("reading", definitions, name)

    def reading_request(name):
        return _field("reading_request", requests, name)

    def intent(name):
        return _field("reading_intent", intents, name)

    def differs(left, right):
        return left.is_distinct_from(right)

    def append(local, value):
        return Assign(local, j[local].op("||")(func.jsonb_build_array(value)))

    actual_reading = (
        SelectInto(
            _rows(
                requests, requests.c.id == producer("request_id"), requests.c.project_id == project
            ),
            ("reading_request",),
            strict=True,
        ),
        SelectInto(
            _rows(
                intents,
                intents.c.id == producer("intent_id"),
                intents.c.request_id == producer("request_id"),
                intents.c.generation == producer("generation"),
                source=intents.join(
                    receipts,
                    and_(
                        receipts.c.intent_id == intents.c.id,
                        receipts.c.derivation_id == producer("id"),
                    ),
                ),
            ),
            ("reading_intent",),
            strict=True,
        ),
        _refuse(
            or_(
                tuple_(
                    *(
                        intent(name)
                        for name in ("producer_task_id", "producer_attempt", "runtime_id")
                    )
                ).is_distinct_from(
                    tuple_(
                        *(
                            producer(name)
                            for name in ("producer_task_id", "producer_attempt", "runtime_id")
                        )
                    )
                ),
                differs(intent("payload")["outcome"].astext, producer("outcome")),
            ),
            "record prediction differs from original reading producer fences",
        ),
        *(
            Assign(("reading_request", name), producer(name))
            for name in ("release_id", "runtime_id", "recipe", "generation")
        ),
        Assign(
            ("reading_request", "binding"),
            reading_request("binding").op("||")(
                _object(inputs=intent("payload")["inputs"], support=intent("payload")["support"])
            ),
        ),
        Assign("reading_completion", intent("payload")),
        SelectInto(
            select(products.c.canonical_body).where(
                products.c.id == selected["product_id"].astext,
                products.c.project_id == project,
            ),
            ("reading_body",),
            strict=True,
        ),
        _refuse(
            or_(
                differs(reading_request("operation_id"), reading("operation_id")),
                differs(reading("profile"), "derivation"),
                differs(reading("support_contract")["effects"], _json("[]")),
                differs(
                    reading("support_contract")["capabilities"]["prepared_factory"][
                        "entrypoint"
                    ].astext,
                    "corpus_structure.methods.reading_resolution.ReadingResolutionOperation.acquire_port",
                ),
                differs(
                    j["reading_completion"]["implementation_revision"].astext,
                    reading("implementation_revision"),
                ),
                differs(
                    func.ops.ddo_cpu_reply_output(
                        core_variable("reading_request", NullType()), j["reading_completion"]
                    ),
                    j["reading_body"],
                ),
            ),
            "record prediction differs from its actual reading CPU result and native basis",
        ),
        Assign("verified_readings", verified.op("||")(func.jsonb_build_object(reading_key, True))),
    )
    selected_event = (
        Assign("event_count", events + 1),
        SelectInto(
            select(frame_events.c.value).where(
                frame_events.c.value["interpretation_id"].astext == interpretation
            ),
            ("event",),
            strict=True,
        ),
        _refuse(
            or_(
                differs(event["record_id"].astext, record),
                differs(event["source"], question_source),
                differs(event["source_release_id"].astext, producer("release_id")),
                differs(event["derivation_id"].astext, producer("id")),
                differs(event["reading_recipe"].astext, reading("recipe")),
                differs(event["reading"]["product_id"].astext, selected["product_id"].astext),
                differs(event["features"]["record_id"].astext, record),
                differs(event["features"]["interpretation_id"].astext, interpretation),
                differs(event["features"]["release_id"].astext, producer("release_id")),
                ~coverage["event_ids"].has_key(interpretation),
            ),
            "grade event relabels actual eligible reading or producing context",
        ),
        _refuse(
            ~func.sem.ddo_model_class_contract(
                producer("release_id"),
                question["family_contract"].astext,
                candidate["contract"].astext,
            ),
            "grade family differs from its authenticated effective model class contract",
        ),
        SelectInto(
            select(carrier_events.c.value).where(
                carrier_events.c.value["record_id"].astext == record,
                carrier_events.c.value["interpretation_id"].astext == interpretation,
            ),
            ("actual_event",),
            strict=True,
        ),
        If(
            actual_event["outcome"].astext == "completed",
            (
                _refuse(
                    differs(
                        event["final_event"],
                        _object(
                            outcome="completed",
                            **{
                                key: actual_event[key].astext
                                for key in (
                                    "feature_instance_digest",
                                    "feature_input_digest",
                                    "event_procedure",
                                )
                            },
                            final_event_score=actual_event["final_event_score"],
                        ),
                    ),
                    "grade final event differs from actual sealed producer score",
                ),
            ),
            (
                _refuse(
                    or_(
                        differs(event["final_event"], _json("null")),
                        frame["partition"].astext == "final_event_calibration",
                    ),
                    "grade invents a completed final event",
                ),
            ),
        ),
    )
    for_reference = (
        Assign("question", ref["question"]),
        Assign("selected", specification["prediction_selections"][index]),
        append("sources_", question_source),
        _refuse(
            or_(
                differs(selected["source"], question_source),
                differs(frame["sources"][index], question_source),
                _different(
                    frame,
                    question,
                    "partition",
                    "family",
                    "family_contract",
                    "reading_recipe",
                    "subset",
                    "source_release_id",
                    "source_cut_id",
                ),
                differs(frame["prediction_cut_id"].astext, selected["expected_cut"].astext),
                differs(frame["prediction_release_id"].astext, selection_cut["release_id"].astext),
                differs(selected["project_id"].astext, project),
                _different(selection_cut, selected, "project_id", "demand_id", "read_id"),
            ),
            "record question/source/prediction census changed",
        ),
        Assign("source_census", cuts[question["source_cut_id"].astext]),
        Assign("prediction_census", cuts[selected["expected_cut"].astext]),
        ForQuery(
            ("pass_row",),
            select(passes),
            (
                Assign("bound", pass_value),
                _refuse(
                    or_(
                        differs(bound["body"]["pass_kind"].astext, pass_kind),
                        differs(pass_ref["pass_kind"].astext, pass_kind),
                        differs(pass_ref["question"], question),
                        differs(pass_ref["exposed_outputs"], _json("[]")),
                    ),
                    "record reference pass differs from exact source-only question/exposure",
                ),
                SelectInto(
                    select(reference_pass.c.value).where(
                        reference_pass.c.value["pass_kind"].astext == pass_kind,
                        reference_pass.c.value["source"] == question_source,
                    ),
                    ("event",),
                    strict=True,
                ),
                _refuse(
                    or_(
                        differs(
                            event["reference"]["product_id"].astext, bound["product_id"].astext
                        ),
                        event["reference"]["member_id"].astext.is_not(None),
                        differs(event["author"].astext, pass_ref["author"].astext),
                        differs(event["adjudicates"], pass_ref["adjudicates"]),
                    ),
                    "record grade relabels actual reference pass",
                ),
            ),
        ),
        ForQuery(
            ("pin",),
            select(reference_pins.c.value),
            (
                If(
                    ~select(1)
                    .select_from(prior_pins)
                    .where(
                        prior_pins.c.value["source_product"].astext == pin["source_product"].astext,
                        prior_pins.c.value["source_member"].astext.is_not_distinct_from(
                            pin["source_member"].astext
                        ),
                    )
                    .exists(),
                    (append("pins", pin),),
                ),
                SelectInto(
                    select(bound_inputs.c.value).where(
                        bound_inputs.c.value["role"].astext == "sources",
                        bound_inputs.c.value["product_id"].astext == pin["source_product"].astext,
                        bound_inputs.c.value["member_id"].astext.is_not_distinct_from(
                            pin["source_member"].astext
                        ),
                    ),
                    ("bound",),
                    strict=True,
                ),
                _refuse(
                    ~select(1)
                    .select_from(used_source)
                    .where(
                        used_source.c.value["product_id"].astext == pin["source_product"].astext,
                    )
                    .exists(),
                    "record question source is outside actual selected cut support",
                ),
                Assign(
                    "predicted",
                    func.ops.ddo_record_grade_input_value(
                        project, bound["product_id"].astext, bound["member_id"].astext
                    ),
                ),
                _refuse(
                    or_(
                        differs(
                            predicted.op("-")("body").op("-")("analyzed_scope_meaning"),
                            _object(
                                product_id=pin["source_product"].astext,
                                member_id=pin["source_member"].astext,
                                **{
                                    key: pin[key].astext
                                    for key in (
                                        "project_id",
                                        "kind_contract",
                                        "subject",
                                        "subject_definition",
                                        "original_source",
                                    )
                                },
                            ),
                        ),
                        differs(
                            predicted["analyzed_scope_meaning"],
                            cast(pin["analyzed_scope_meaning"].astext, JSONB()),
                        ),
                        differs(
                            source_projection["projection"].astext, pin["projection_digest"].astext
                        ),
                        _different(
                            source_projection, pin, "document", "section_pointer", "membership"
                        ),
                    ),
                    "record source pin differs from actual declared source product/member/context",
                ),
            ),
        ),
        Assign("u", prediction_census["uses"][selected["use_id"].astext]),
        Assign("obligation", prediction_census["obligations"][selected["obligation_id"].astext]),
        _refuse(
            or_(
                u.is_(None),
                obligation.is_(None),
                _different(u, selected, "obligation_id", "request_id"),
            ),
            "record opportunity is outside its exact native selected census",
        ),
        _refuse(
            or_(
                differs(obligation["operation_id"].astext, _READING),
                _different(
                    obligation, question_source, "subject", "subject_definition", "original_source"
                ),
                differs(
                    func.data.ddo_json_meaning(obligation["analyzed_scope"]),
                    cast(question_source["analyzed_scope_meaning"].astext, JSONB()),
                ),
            ),
            "record opportunity differs from actual source context",
        ),
        Assign("coverage", frame["coverage"][index]),
        _refuse(differs(coverage["source"], question_source), "record coverage source changed"),
        If(
            selected["outcome"].astext.in_(("failed", "no_output")),
            (
                _refuse(
                    or_(
                        differs(
                            u["completion_state"].astext,
                            case((selected["outcome"].astext == "failed", "failed"), else_="empty"),
                        ),
                        differs(
                            u["fate"].astext,
                            case(
                                (selected["outcome"].astext == "failed", "failed"),
                                else_="known-absent",
                            ),
                        ),
                        differs(coverage["outcome"].astext, selected["outcome"].astext),
                        differs(coverage["outputs"], _json("[]")),
                        differs(coverage["event_ids"], _json("[]")),
                        and_(
                            selected["outcome"].astext == "failed",
                            tuple_(
                                coverage["failure_request_id"].astext,
                                coverage["failure_use_id"].astext,
                            ).is_distinct_from(
                                tuple_(selected["request_id"].astext, selected["use_id"].astext)
                            ),
                        ),
                    ),
                    "failed or empty coverage differs from actual native completion",
                ),
                Continue(),
            ),
        ),
        _refuse(
            or_(
                differs(selected["outcome"].astext, "completed"),
                differs(u["completion_state"].astext, "success"),
                differs(u["fate"].astext, "fulfilled"),
                differs(u["derivation_id"].astext, selected["derivation_id"].astext),
            ),
            "record prediction is unavailable or differs from actual native success",
        ),
        SelectInto(
            select(bound_inputs.c.value).where(
                bound_inputs.c.value["role"].astext == "prediction",
                bound_inputs.c.value["product_id"].astext == selected["product_id"].astext,
                bound_inputs.c.value["member_id"].astext.is_(None),
                func.coalesce(cast(bound_inputs.c.value["multiplicity"].astext, Integer()), 0) == 1,
            ),
            ("bound",),
            strict=True,
        ),
        _refuse(
            or_(
                ~select(1)
                .select_from(bound_support)
                .where(
                    bound_support.c.value["derivation_id"].astext
                    == selected["derivation_id"].astext
                )
                .exists(),
                ~select(1)
                .select_from(outputs)
                .where(
                    outputs.c.derivation_id == selected["derivation_id"].astext,
                    outputs.c.product_id == selected["product_id"].astext,
                    outputs.c.member_id.is_(None),
                )
                .exists(),
            ),
            "record prediction lacks exact declared producer/output support",
        ),
        Assign("selected_count", completed + 1),
        SelectInto(
            _rows(
                episodes,
                episodes.c.id == selected["derivation_id"].astext,
                episodes.c.request_id == selected["request_id"].astext,
            ),
            ("producer",),
            strict=True,
        ),
        SelectInto(
            _rows(
                definitions,
                definitions.c.release_id == producer("release_id"),
                definitions.c.operation_id == _READING,
            ),
            ("reading",),
            strict=True,
        ),
        _refuse(
            or_(
                differs(producer("recipe"), reading("recipe")),
                differs(reading("recipe"), question["reading_recipe"].astext),
            ),
            "record prediction changed its admitted reading recipe",
        ),
        Assign(
            "reading_key",
            func.data.canonical_json(
                func.jsonb_build_array(producer("id"), selected["product_id"].astext)
            ),
        ),
        If(~verified.has_key(reading_key), actual_reading),
        Assign(
            "predicted",
            func.ops.ddo_record_grade_input_value(project, selected["product_id"].astext, None),
        ),
        Assign("carrier", predicted["body"]),
        _refuse(
            or_(
                differs(carrier["source_pin"], func.jsonb_strip_nulls(question_source)),
                func.jsonb_array_length(coverage["outputs"]) != 1,
                differs(coverage["outputs"][0]["product_id"].astext, selected["product_id"].astext),
            ),
            "record coverage differs from actual selected carrier/source",
        ),
        ForQuery(("candidate",), select(body).where(eligible), selected_event),
        _refuse(
            or_(
                func.jsonb_array_length(coverage["event_ids"])
                != select(func.count())
                .select_from(carrier_members)
                .where(eligible)
                .scalar_subquery(),
                differs(
                    coverage["outcome"].astext,
                    case(
                        (func.jsonb_array_length(coverage["event_ids"]) == 0, "no_output"),
                        else_="completed",
                    ),
                ),
            ),
            "grade coverage omits actual eligible reading events",
        ),
    )
    ref_rows = _items(references, "reference_row", ordinal=True)
    initial_values = {
        **{
            name: func.ops.ddo_record_grade_input(r, role, type_=JSONB())
            for name, role in (
                ("a", "reference_a"),
                ("b", "reference_b"),
                ("c", "adjudication"),
            )
        },
        "specification": func.ops.ddo_record_grade_input(r, "specification", type_=JSONB())["body"],
        "frame": grade["frame"],
        "pins": _json("[]"),
        "sources_": _json("[]"),
        "cuts": _json("{}"),
        "verified_readings": _json("{}"),
    }
    ref_count = func.jsonb_array_length(references)
    return _grade(
        "require_frame",
        (("r", "ops.data_request"), ("grade", "jsonb")),
        "void",
        body=(
            _refuse(
                or_(
                    differs(grade["version"].astext, "record-grade-1"),
                    differs(grade["frame_digest"].astext, _hash(canonical_frame)),
                    differs(cast(canonical_frame, JSONB()), frame),
                    differs(frame["project_id"].astext, project),
                    ref_count != func.jsonb_array_length(specification["prediction_selections"]),
                    ref_count != func.jsonb_array_length(frame["coverage"]),
                    3 * ref_count != func.jsonb_array_length(frame["reference_passes"]),
                    a["product_id"].astext == b["product_id"].astext,
                    a["product_id"].astext == c["product_id"].astext,
                    b["product_id"].astext == c["product_id"].astext,
                ),
                "record grade differs from canonical frame and genuine independent pass population",
            ),
            ForQuery(
                ("captured",),
                select(cut),
                (
                    Assign(
                        "cuts",
                        cuts.op("||")(
                            func.jsonb_build_object(
                                cut_id,
                                func.ops.ddo_record_grade_acquire_census(project, cut_text, cut_id),
                            )
                        ),
                    ),
                ),
            ),
            ForQuery(("ref", "n"), select(ref_rows.c.value, ref_rows.c.ordinal), for_reference),
            _refuse(
                or_(
                    differs(sources, frame["sources"]),
                    func.jsonb_array_length(frame["events"]) != events,
                    func.jsonb_array_length(pins)
                    != select(func.count())
                    .select_from(bound_inputs)
                    .where(
                        bound_inputs.c.value["role"].astext == "sources",
                    )
                    .scalar_subquery(),
                    completed
                    != select(func.count())
                    .select_from(bound_inputs)
                    .where(
                        bound_inputs.c.value["role"].astext == "prediction",
                    )
                    .scalar_subquery(),
                ),
                "grade does not cover exact declared source and prediction populations",
            ),
        ),
        locals_=(
            *(Local(name, pg_type("jsonb"), initial_values.get(name)) for name in values),
            Local("captured", pg_type("record")),
            Local("pass_row", pg_type("record")),
            Local("n", pg_type("int8")),
            Local("event_count", pg_type("int4"), literal(0)),
            Local("selected_count", pg_type("int4"), literal(0)),
            Local("reading_key", pg_type("text")),
            Local("producer", episodes),
            Local("reading", definitions),
            Local("reading_request", requests),
            Local("reading_intent", intents),
        ),
    )


def _completion_programs(model):
    requests = model.tables["ops.data_request"]
    definitions = model.tables["sem.data_operation_definition"]
    kinds = model.tables["sem.data_kind_contract"]
    r = core_variable("r", NullType())
    binding = _field("r", requests, "binding")
    operation = _field("r", requests, "operation_id")
    completion = core_variable("completion", JSONB())
    output = core_variable("output", JSONB())
    product = output["product"]
    declared_kind = _field("definition", definitions, "support_contract")
    factory = declared_kind["capabilities"]["prepared_factory"]
    implementation = _field("definition", definitions, "implementation_revision")
    arguments = (("r", "ops.data_request"), ("completion", "jsonb"))
    skip = If(
        ~selected_family(model, _field("r", requests, "release_id"), operation, "record-grade"),
        (Return(),),
    )
    result_body = completion["outputs"][0]["product"]["body"]
    return (
        *_grade(
            "require_producer",
            arguments,
            "void",
            body=(
                skip,
                SelectInto(
                    _rows(
                        definitions,
                        definitions.c.release_id == _field("r", requests, "release_id"),
                        definitions.c.operation_id == operation,
                    ),
                    ("definition",),
                    strict=True,
                ),
                _refuse(
                    or_(
                        _field("definition", definitions, "profile").is_distinct_from("derivation"),
                        declared_kind["effects"].is_distinct_from(_json("[]")),
                        func.nullif(factory["entrypoint"].astext, "").is_(None),
                        factory["source_digest"].astext.bool_op("~")("^[0-9a-f]{64}$").is_not(True),
                        implementation.like("implementation-slice:%").is_not(True),
                        completion["implementation_revision"].astext.is_distinct_from(
                            implementation
                        ),
                        func.jsonb_array_length(
                            func.coalesce(
                                completion["execution_evidence"]["cpu_receipts"], _json("[]")
                            )
                        )
                        != 1,
                        completion["outcome"].astext.is_distinct_from("success"),
                        completion["inputs"].is_distinct_from(binding["inputs"]),
                        func.jsonb_array_length(completion["outputs"]) != 1,
                    ),
                    "record grade requires its actual admitted pure CPU implementation and complete inputs",
                ),
                Assign("output", completion["outputs"][0]),
                _refuse(
                    or_(
                        output["role"].astext.is_distinct_from("grade"),
                        output["member_id"].astext.is_not(None),
                        cast(output["position"].astext, Integer()).is_distinct_from(0),
                        cast(output["multiplicity"].astext, Integer()).is_distinct_from(1),
                        product["members"].is_distinct_from(_json("[]")),
                        ~select(1)
                        .select_from(kinds)
                        .where(
                            kinds.c.kind_contract == product["kind_contract"].astext,
                            kinds.c.kind == GRADE_KIND,
                            kinds.c.universe == "evaluator",
                        )
                        .exists(),
                    ),
                    "record grade output differs from protected whole scalar contract",
                ),
            ),
            locals_=(Local("definition", definitions), Local("output", pg_type("jsonb"))),
        ),
        *_defined(
            "ops",
            "ddo_require_record_grade_completion",
            arguments,
            "void",
            body=(
                skip,
                Perform(func.ops.ddo_record_grade_require_producer(r, completion)),
                _refuse(
                    func.ops.ddo_cpu_reply_output(r, completion).is_distinct_from(
                        func.data.ddo_normalize(result_body)
                    ),
                    "record grade differs from actual CPU result and reference basis",
                ),
                Perform(
                    func.ops.ddo_record_grade_require_frame(r, func.data.ddo_json(result_body))
                ),
            ),
        ),
    )


def record_grade_native_sql(model: MetaData) -> str:
    return native_sql_script(
        (
            *_class_contract(model),
            *_grade_inputs(model),
            *_finite_census(model),
            *_cut_programs(model),
            *_request_cut_programs(model),
            *_frame_program(model),
            *_completion_programs(model),
        )
    )
