"""Native policy issuer recognition and bounded ordinary provenance disclosure."""

from corpus_structure.schema.integrity import role_name

GRADE_SCHEMA_SOURCE = "native/data-operation-record-grade.schema.json"
EVENT_FRAME_SCHEMA_SOURCE = "native/data-operation-operation-event-frame.schema.json"
EVENT_FRAME_KIND = (
    "https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFrame"
)
EVENT_FRAME_OPERATION = "operation_event.frame"
EVENT_FRAME_FACTORY = "corpus_structure.methods.operation_events.OperationEventFrame.acquire_port"


def _fit_frame_schema(model, prefix):
    from pydantic import TypeAdapter

    from .data_operation_wire import generated_json_schema
    from .identity import canonical_bytes

    schema = TypeAdapter(model).json_schema(ref_template="#/definitions/" + prefix + "_{model}")
    definitions = schema.pop("$defs", {})
    schema["definitions"] = {prefix + "_" + name: value for name, value in definitions.items()}
    return canonical_bytes(generated_json_schema(schema))


def record_policy_grade_schema() -> bytes:
    """Capture the actual protected grade DTO with collision-free Draft7 refs."""
    from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade

    return _fit_frame_schema(DdoRecordGrade, "record_grade")


def operation_event_frame_schema() -> bytes:
    """Capture the current frame owner; native acquisition authenticates the selection."""
    from corpus_structure.evaluate.selected_operation_events import DdoOperationEventFrame

    return _fit_frame_schema(DdoOperationEventFrame, "operation_event_frame")


def read_selected_feature_fit_frame(
    connection,
    *,
    variant,
    project_id,
    demand_id,
    read_id,
    use_id,
    derivation_id,
    product_id,
    expected_cut,
    frame_digest,
    cut,
    max_bytes=8388608,
):
    """Read one native-authenticated fit partition using an actual fitter login."""
    import json
    from typing import cast

    from ._data_operation_wire import WireReadSelectedFeatureFitFrameRequest
    from .data_operation_json import json_bytes
    from .data_operation_storage import DataOperationStorage
    from .data_operation_wire import validate_native_wire
    from .demand_results import CutSelection
    from .identity import canonical_bytes

    if not isinstance(cut, CutSelection) or cut.identity != expected_cut:
        raise ValueError("feature fit requires the exact retained cut bytes")
    pins = cut.record
    if (pins["project_id"], pins["demand_id"], pins["read_id"]) != (project_id, demand_id, read_id):
        raise ValueError("feature fit cut belongs to another selection")
    payload = dict(
        variant=variant,
        project_id=project_id,
        demand_id=demand_id,
        read_id=read_id,
        use_id=use_id,
        derivation_id=derivation_id,
        product_id=product_id,
        expected_cut=expected_cut,
        frame_digest=frame_digest,
        cut_canonical_json=cut.content.decode(),
        max_bytes=max_bytes,
    )
    request = cast(
        WireReadSelectedFeatureFitFrameRequest,
        validate_native_wire("read_selected_feature_fit_frame", "input", payload),
    )
    result = DataOperationStorage(connection).read_selected_feature_fit_frame(request)
    if CutSelection(json_bytes(result["cut"])).record != pins:
        raise ValueError("feature fit returned another retained cut")
    if (
        result["variant"] != variant
        or result["product_id"] != product_id
        or result["derivation_id"] != derivation_id
        or result["frame"]["frame_digest"] != frame_digest
    ):
        raise ValueError("feature fit returned another protected frame")
    # JSONB is a projection of the semantic body and can normalize signed zero.
    # The authenticated CPU grade retains its original exact frame text. Native
    # compares that text's parsed value and digest before disclosing it; restoring
    # its typed frame here preserves the actual numerical basis without guessing
    # PostgreSQL's float spelling or granting authority to caller-supplied bytes.
    if variant == "record-feature-grade":
        from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade

        frame_model = DdoRecordGrade
    elif variant == "operation-event-frame":
        from corpus_structure.evaluate.selected_operation_events import DdoOperationEventFrame

        frame_model = DdoOperationEventFrame
    else:
        raise ValueError("unknown selected feature fit frame variant")
    grade = result["frame"]
    restored = frame_model.model_validate_json(
        canonical_bytes(
            {
                **grade,
                "frame": json.loads(grade["frame_canonical_json"]),
            }
        ),
        strict=True,
    )
    return {**result, "frame": restored.model_dump(mode="json")}


def _revoke_policy(name, parameters):
    from pglast import ast, enums
    from pglast.stream import RawStream

    return (
        RawStream()(
            ast.GrantStmt(
                is_grant=False,
                targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                objtype=enums.ObjectType.OBJECT_FUNCTION,
                objects=(
                    ast.ObjectWithArgs(
                        objname=(ast.String(sval="ops"), ast.String(sval=name)),
                        objargs=tuple(parameter.type_ for parameter in parameters),
                        args_unspecified=False,
                    ),
                ),
                grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
                grant_option=False,
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        )
        + ";\n"
    )


def record_policy_native_sql(*, target_metadata=None):
    """Generate protected authority and feature-frame reads over captured metadata."""
    from dataclasses import asdict

    from sqlalchemy import Boolean, and_, case, cast, func, literal, or_, select
    from sqlalchemy.dialects.postgresql import JSONB

    from corpus_structure.evaluate.declared_operation_events import PARAMETERS_KIND

    from .binding_recursive_native import _check, _json, _value
    from .declared_structural_admission import ADMISSION_KIND
    from .identity import canonical_bytes
    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        Parameter,
        Return,
        SelectInto,
        core_relation_row,
        core_variable,
        function,
        pg_type,
        sql_function,
    )
    from .record_policy_authority import (
        AUTHORIZATION_EFFECT,
        AUTHORIZATION_FACTORY,
        AUTHORIZATION_KIND,
        AUTHORIZATION_OPERATION,
    )

    if target_metadata is None:
        from .metadata import get_metadata

        target_metadata = get_metadata()
    model = target_metadata
    definitions, episodes, requests, receipts, outputs, products, kinds, boundaries, uses = (
        model.tables[name]
        for name in (
            "sem.data_operation_definition",
            "ops.data_derivation",
            "ops.data_request",
            "ops.data_publication_receipt",
            "ops.data_derivation_output",
            "kb.data_product",
            "sem.data_kind_contract",
            "ops.data_demand_read",
            "ops.demand_use",
        )
    )

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def definition(field):
        return row("definition", definitions, field)

    def d(field):
        return row("d", episodes, field)

    def boundary(field):
        return row("boundary", boundaries, field)

    def chosen(field):
        return row("chosen", uses, field)

    def output(field):
        return row("output", outputs, field)

    def receipt(field):
        return row("receipt", receipts, field)

    def obj(**fields):
        return func.jsonb_build_object(
            *(part for pair in fields.items() for part in pair), type_=JSONB()
        )

    def selected(table, condition, target):
        return SelectInto(
            select(core_relation_row(table)).select_from(table).where(condition), (target,), True
        )

    def sql(name, parameters, body, *, immutable=False, strict=False, definer=False):
        return (
            sql_function(
                "ops",
                name,
                parameters=parameters,
                returns=pg_type("boolean"),
                body=body,
                volatility="immutable" if immutable else "stable",
                strict=strict,
                security_definer=definer,
                search_path=("pg_catalog", "pg_temp"),
            )
            + ";\n"
            + _revoke_policy(name, parameters)
        )

    parameters = (Parameter("definition", pg_type(str(definitions.schema), definitions.name)),)
    capabilities = definition("support_contract")["capabilities"]
    eligible = sql(
        "ddo_policy_command_eligible",
        parameters,
        select(
            and_(
                definition("operation_id") == AUTHORIZATION_OPERATION,
                definition("profile") == "command",
                capabilities["preparation"].astext == "native-publication",
                capabilities["forms"] == _json('["scalar"]'),
                capabilities["prepared_factory"]["entrypoint"].astext == AUTHORIZATION_FACTORY,
                definition("support_contract")["effects"]
                == cast(literal(canonical_bytes([asdict(AUTHORIZATION_EFFECT)]).decode()), JSONB()),
                capabilities["prepared_factory"]["source_digest"].astext.op("~")("^[0-9a-f]{64}$"),
                definition("implementation_revision").like("implementation-slice:%"),
            )
        ),
        immutable=True,
        strict=True,
    )
    episode = _value("episode")
    native_episode = episodes.alias("native_episode")
    native_request = requests.alias("native_request")
    native_definition = definitions.alias("native_definition")
    native_receipt = receipts.alias("native_receipt")
    native_output = outputs.alias("native_output")
    native_product = products.alias("native_product")
    native_kind = kinds.alias("native_kind")
    other_output = outputs.alias("other_output")
    only_one_output = (
        select(func.count())
        .where(other_output.c.derivation_id == native_episode.c.id)
        .correlate(native_episode)
        .scalar_subquery()
        == 1
    )
    authority = (
        select(native_episode.c.id)
        .select_from(
            native_episode.join(native_request, native_request.c.id == native_episode.c.request_id)
            .join(
                native_definition,
                and_(
                    native_definition.c.release_id == native_episode.c.release_id,
                    native_definition.c.operation_id == native_request.c.operation_id,
                ),
            )
            .join(
                native_receipt,
                and_(
                    native_receipt.c.derivation_id == native_episode.c.id,
                    native_receipt.c.intent_id == native_episode.c.intent_id,
                ),
            )
            .join(native_output, native_output.c.derivation_id == native_episode.c.id)
            .join(native_product, native_product.c.id == native_output.c.product_id)
            .join(native_kind, native_kind.c.kind_contract == native_product.c.kind_contract)
        )
        .where(
            native_episode.c.id == episode,
            native_episode.c.outcome == "success",
            or_(
                and_(
                    native_definition.c.command_class == "policy",
                    native_output.c.role == "authorization",
                    native_kind.c.kind == AUTHORIZATION_KIND,
                ),
                and_(
                    native_definition.c.command_class == "structural",
                    native_output.c.role == "admission",
                    native_kind.c.kind == ADMISSION_KIND,
                ),
                and_(
                    native_definition.c.command_class == "operation_event",
                    native_output.c.role == "parameters",
                    native_kind.c.kind == PARAMETERS_KIND,
                ),
            ),
            native_output.c.position == 0,
            native_output.c.multiplicity == 1,
            native_output.c.member_id.is_(None),
            native_kind.c.universe == "ordinary",
            only_one_output,
        )
        .exists()
    )
    leaf = sql(
        "ddo_policy_authority_leaf",
        (Parameter("episode", pg_type("text")),),
        select(authority),
        definer=True,
    )
    selected_use, read_id, standing = (
        _value(name) for name in ("selected_use", "read_id", "standing")
    )
    published = uses.alias("published")
    visible_publication = (
        select(published.c.id)
        .where(
            published.c.derivation_id == d("id"),
            published.c.fate == "fulfilled",
            func.ops.ddo_read_visible(
                published.c.created_at, published.c.created_xid, _value("boundary"), type_=Boolean()
            ),
        )
        .exists()
    )
    parameters = tuple(
        Parameter(name, pg_type("text")) for name in ("episode", "selected_use", "read_id")
    )
    summary = (
        function(
            "ops",
            "ddo_policy_authority_summary",
            parameters=parameters,
            returns=pg_type("jsonb"),
            volatility="stable",
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                (
                    _check(
                        ~func.coalesce(
                            func.ops.ddo_policy_authority_leaf(episode, type_=Boolean()), False
                        ),
                        "ordinary policy authority summary requires an authenticated native issuer",
                        "23514",
                    ),
                    selected(boundaries, boundaries.c.id == read_id, "boundary"),
                    _check(
                        ~boundary("public_disclosure"),
                        "policy authority summary requires its public acquisition",
                        "23514",
                    ),
                    selected(episodes, episodes.c.id == episode, "d"),
                    _check(
                        or_(d("completed_at") > boundary("frontier_at"), ~visible_publication),
                        "policy issuer is outside selected native visibility",
                        "23514",
                    ),
                    selected(outputs, outputs.c.derivation_id == episode, "output"),
                    selected(
                        receipts,
                        and_(
                            receipts.c.derivation_id == episode,
                            receipts.c.intent_id == d("intent_id"),
                        ),
                        "receipt",
                    ),
                    If(
                        selected_use.is_not(None),
                        (
                            selected(
                                uses,
                                and_(uses.c.id == selected_use, uses.c.derivation_id == episode),
                                "chosen",
                            ),
                            _check(
                                ~func.ops.ddo_read_visible(
                                    chosen("created_at"),
                                    chosen("created_xid"),
                                    _value("boundary"),
                                    type_=Boolean(),
                                ),
                                "policy authority use is outside selected native visibility",
                                "23514",
                            ),
                            Assign(
                                "standing",
                                case(
                                    (
                                        func.ops.ddo_node_valid(
                                            "use", chosen("id"), _value("boundary"), type_=Boolean()
                                        ),
                                        "valid",
                                    ),
                                    else_="unavailable",
                                ),
                            ),
                        ),
                        (
                            Assign(
                                "standing",
                                case(
                                    (
                                        func.ops.ddo_node_valid(
                                            "episode", episode, _value("boundary"), type_=Boolean()
                                        ),
                                        "valid",
                                    ),
                                    else_="unavailable",
                                ),
                            ),
                        ),
                    ),
                    Return(
                        obj(
                            format="ddo-native-authority-leaf-v1",
                            derivation_id=episode,
                            use_id=selected_use,
                            issuer_operation=select(requests.c.operation_id)
                            .where(requests.c.id == d("request_id"))
                            .scalar_subquery(),
                            release_id=d("release_id"),
                            runtime_id=d("runtime_id"),
                            recipe=d("recipe"),
                            product_id=output("product_id"),
                            kind_contract=select(products.c.kind_contract)
                            .where(products.c.id == output("product_id"))
                            .scalar_subquery(),
                            intent_id=d("intent_id"),
                            receipt_id=receipt("id"),
                            standing=standing,
                            protected_dependencies="undisclosed",
                        )
                    ),
                ),
                (
                    *(
                        Local(name, table)
                        for name, table in (
                            ("d", episodes),
                            ("chosen", uses),
                            ("boundary", boundaries),
                            ("output", outputs),
                            ("receipt", receipts),
                        )
                    ),
                    Local("standing", pg_type("text")),
                ),
            ),
        )
        + ";\n"
        + _revoke_policy("ddo_policy_authority_summary", parameters)
    )
    return "\n".join((eligible, leaf, summary, _feature_fit_sql(model)))


def _feature_fit_sql(model):
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Text,
        and_,
        case,
        cast,
        column,
        func,
        literal,
        or_,
        select,
        table,
        tuple_,
    )
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.sql.elements import Grouping

    from .binding_recursive_native import _check, _json, _value
    from .data_operation_projections import cut_selection_projection, selected_support_output
    from .native_catalog import namespace, relation
    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        Parameter,
        Perform,
        Return,
        SelectInto,
        core_relation_row,
        core_variable,
        function,
        pg_type,
    )
    from .record_policy_authority import GRADE_FACTORY, GRADE_KIND, GRADE_OPERATION

    (
        demands,
        boundaries,
        episodes,
        definitions,
        requests,
        intents,
        receipts,
        outputs,
        products,
        kinds,
    ) = (
        model.tables[name]
        for name in (
            "ops.data_demand",
            "ops.data_demand_read",
            "ops.data_derivation",
            "sem.data_operation_definition",
            "ops.data_request",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
            "ops.data_derivation_output",
            "kb.data_product",
            "sem.data_kind_contract",
        )
    )

    def row(name, table, field):
        return core_variable(name, table.c[field].type, field)

    def d(field):
        return row("d", demands, field)

    def boundary(field):
        return row("boundary", boundaries, field)

    def episode(field):
        return row("episode", episodes, field)

    def definition(field):
        return row("definition", definitions, field)

    def intent(field):
        return row("intent", intents, field)

    def obj(**fields):
        return func.jsonb_build_object(
            *(part for pair in fields.items() for part in pair), type_=JSONB()
        )

    def selected(table, condition, target):
        return SelectInto(
            select(core_relation_row(table)).select_from(table).where(condition), (target,), True
        )

    def routine(name, parameters, steps, locals_=(), *, result="jsonb", stable=True):
        return (
            function(
                "ops",
                name,
                parameters=parameters,
                returns=pg_type(result),
                body=Block(tuple(steps), tuple(locals_)),
                volatility="stable" if stable else None,
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
            )
            + ";\n"
            + _revoke_policy(name, parameters)
        )

    principal = _value("principal")
    roles = table(
        "pg_roles",
        column("rolname", Text()),
        *(
            column(name, Boolean())
            for name in (
                "rolsuper",
                "rolcreatedb",
                "rolcreaterole",
                "rolbypassrls",
                "rolreplication",
            )
        ),
        schema="pg_catalog",
    )
    elevated_role = (
        select(roles.c.rolname)
        .where(
            roles.c.rolname == principal,
            or_(
                *(
                    roles.c[name]
                    for name in (
                        "rolsuper",
                        "rolcreatedb",
                        "rolcreaterole",
                        "rolbypassrls",
                        "rolreplication",
                    )
                )
            ),
        )
        .exists()
    )
    owned_schema = (
        select(namespace.c.oid)
        .where(
            namespace.c.nspname.in_(("sem", "data", "ops", "kb", "eval")),
            or_(
                func.pg_has_role(principal, namespace.c.nspowner, "MEMBER", type_=Boolean()),
                func.has_schema_privilege(principal, namespace.c.oid, "CREATE", type_=Boolean()),
            ),
        )
        .exists()
    )
    table_read = (
        select(relation.c.oid)
        .select_from(relation.join(namespace, namespace.c.oid == relation.c.relnamespace))
        .where(
            namespace.c.nspname.in_(("ops", "kb", "eval")),
            relation.c.relkind.in_(("r", "p", "v", "m")),
            or_(
                func.has_table_privilege(principal, relation.c.oid, "SELECT", type_=Boolean()),
                func.has_any_column_privilege(principal, relation.c.oid, "SELECT", type_=Boolean()),
            ),
        )
        .exists()
    )
    principal_guard = routine(
        "ddo_require_feature_fit_principal",
        (),
        (
            _check(
                or_(
                    ~func.pg_has_role(principal, role_name("fitter"), "USAGE", type_=Boolean()),
                    ~func.current_setting("role").in_(("none", cast(principal, Text()))),
                    func.pg_has_role(principal, role_name("evaluator"), "MEMBER", type_=Boolean()),
                    func.pg_has_role(principal, role_name("publisher"), "MEMBER", type_=Boolean()),
                    func.has_database_privilege(
                        principal, func.current_database(), "TEMP", type_=Boolean()
                    ),
                    elevated_role,
                    owned_schema,
                    table_read,
                ),
                "feature fitting requires a restricted actual fitting principal",
                "42501",
            ),
        ),
        (Local("principal", pg_type("name"), func.session_user()),),
        result="void",
    )
    contract, body = _value("contract"), _value("body", JSONB())
    decoded = func.data.ddo_json(body, type_=JSONB())
    body_access = routine(
        "ddo_feature_fit_body_access",
        (Parameter("contract", pg_type("text")), Parameter("body", pg_type("jsonb"))),
        (
            Perform(func.ops.ddo_require_feature_fit_principal()),
            Return(
                select(kinds.c.kind_contract)
                .where(
                    kinds.c.kind_contract == contract,
                    kinds.c.universe == "evaluator",
                    or_(
                        and_(
                            kinds.c.kind == GRADE_KIND,
                            decoded["version"].astext == "record-grade-1",
                            decoded["frame"]["partition"].astext == "feature_fit",
                        ),
                        and_(
                            kinds.c.kind == EVENT_FRAME_KIND,
                            decoded["version"].astext == "selected-operation-event-frame-product-1",
                            decoded["frame"]["question"]["partition"].astext.in_(
                                ("development", "feature_fit")
                            ),
                        ),
                    ),
                )
                .exists()
            ),
        ),
        result="boolean",
    )
    p = _value("p", JSONB())
    p_product, p_derivation, variant = (
        _value(name) for name in ("p_product", "p_derivation", "variant")
    )
    grade, cut, result = (_value(name, JSONB()) for name in ("grade", "cut", "result"))
    expected_operation, expected_factory, expected_kind, expected_role, receipt_id = (
        _value(name)
        for name in (
            "expected_operation",
            "expected_factory",
            "expected_kind",
            "expected_role",
            "receipt_id",
        )
    )
    capabilities = definition("support_contract")["capabilities"]
    source_digest = capabilities["prepared_factory"]["source_digest"].astext
    project_for_frame = case(
        (variant == "record-feature-grade", grade["frame"]["project_id"].astext),
        else_=grade["frame"]["question"]["prediction_selection"]["project_id"].astext,
    )
    parameters = (Parameter("p_payload", pg_type("jsonb")),)
    read_frame = routine(
        "read_selected_feature_fit_frame",
        parameters,
        (
            Perform(func.ops.ddo_require_feature_fit_principal()),
            If(
                variant == "record-feature-grade",
                (
                    Assign("expected_operation", literal(GRADE_OPERATION)),
                    Assign("expected_factory", literal(GRADE_FACTORY)),
                    Assign("expected_kind", literal(GRADE_KIND)),
                    Assign("expected_role", literal("grade")),
                ),
                (
                    If(
                        variant == "operation-event-frame",
                        (
                            Assign("expected_operation", literal(EVENT_FRAME_OPERATION)),
                            Assign("expected_factory", literal(EVENT_FRAME_FACTORY)),
                            Assign("expected_kind", literal(EVENT_FRAME_KIND)),
                            Assign("expected_role", literal("frame")),
                        ),
                        (
                            _check(
                                literal(True), "unknown selected feature fit frame variant", "23514"
                            ),
                        ),
                    ),
                ),
            ),
            selected(
                demands,
                and_(
                    demands.c.id == p["demand_id"].astext,
                    demands.c.project_id == p["project_id"].astext,
                ),
                "d",
            ),
            selected(
                boundaries,
                and_(boundaries.c.id == p["read_id"].astext, boundaries.c.demand_id == d("id")),
                "boundary",
            ),
            Assign("p", p.op("||")(obj(scope=boundary("scope")))),
            Assign(
                "snapshot", func.ops.ddo_require_read_epochs(_value("boundary"), d("project_id"))
            ),
            SelectInto(selected_support_output(model, purpose="feature-fit"), ("admitted",)),
            _check(
                ~func.coalesce(_value("admitted", Boolean()), False),
                "feature fit grade is outside exact current selected support",
                "23514",
            ),
            SelectInto(cut_selection_projection(), ("cut",)),
            _check(
                or_(
                    cast(p["cut_canonical_json"].astext, JSONB()).is_distinct_from(cut),
                    p["expected_cut"].astext.is_distinct_from(
                        literal("cut-selection:")
                        + func.encode(
                            func.sha256(func.convert_to(p["cut_canonical_json"].astext, "UTF8")),
                            "hex",
                        )
                    ),
                ),
                "feature fit cut bytes or native pins differ",
                "23514",
            ),
            selected(
                episodes,
                and_(episodes.c.id == p_derivation, episodes.c.outcome == "success"),
                "episode",
            ),
            SelectInto(
                select(core_relation_row(definitions))
                .select_from(
                    definitions.join(
                        requests,
                        and_(
                            definitions.c.release_id == episode("release_id"),
                            requests.c.operation_id == definitions.c.operation_id,
                        ),
                    )
                )
                .where(
                    requests.c.id == episode("request_id"), requests.c.project_id == d("project_id")
                ),
                ("definition",),
                True,
            ),
            selected(
                intents,
                and_(
                    intents.c.id == episode("intent_id"),
                    intents.c.request_id == episode("request_id"),
                    intents.c.generation == episode("generation"),
                ),
                "intent",
            ),
            _check(
                tuple_(
                    intent("producer_task_id"), intent("producer_attempt"), intent("runtime_id")
                ).is_distinct_from(
                    tuple_(
                        episode("producer_task_id"),
                        episode("producer_attempt"),
                        episode("runtime_id"),
                    )
                ),
                "feature fit frame differs from original producer fences",
                "23514",
            ),
            _check(
                or_(
                    definition("operation_id").is_distinct_from(expected_operation),
                    definition("profile").is_distinct_from("derivation"),
                    definition("support_contract")["effects"].is_distinct_from(_json("[]")),
                    capabilities["prepared_factory"]["entrypoint"].astext.is_distinct_from(
                        expected_factory
                    ),
                    source_digest.op("~")("^[0-9a-f]{64}$").is_not(True),
                    definition("implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    intent("payload")["implementation_revision"].astext.is_distinct_from(
                        definition("implementation_revision")
                    ),
                    func.jsonb_array_length(
                        func.coalesce(
                            intent("payload")["execution_evidence"]["cpu_receipts"], _json("[]")
                        )
                    )
                    != 1,
                    episode("recipe").is_distinct_from(definition("recipe")),
                ),
                "feature fit requires the actual admitted protected grade implementation",
                "23514",
            ),
            SelectInto(
                select(receipts.c.id)
                .select_from(
                    receipts.join(outputs, outputs.c.derivation_id == receipts.c.derivation_id)
                )
                .where(
                    receipts.c.derivation_id == episode("id"),
                    receipts.c.intent_id == episode("intent_id"),
                    outputs.c.product_id == p_product,
                    outputs.c.member_id.is_(None),
                    outputs.c.role == expected_role,
                    outputs.c.position == 0,
                    outputs.c.multiplicity == 1,
                ),
                ("receipt_id",),
                True,
            ),
            _check(
                ~select(products.c.id)
                .select_from(
                    products.join(kinds, kinds.c.kind_contract == products.c.kind_contract)
                )
                .where(
                    products.c.id == p_product,
                    products.c.project_id == d("project_id"),
                    kinds.c.kind == expected_kind,
                    kinds.c.universe == "evaluator",
                )
                .exists(),
                "feature fit variant differs from actual protected frame kind",
                "23514",
            ),
            SelectInto(
                select(func.data.ddo_json(products.c.canonical_body)).where(
                    products.c.id == p_product, products.c.project_id == d("project_id")
                ),
                ("grade",),
                True,
            ),
            _check(
                or_(
                    grade["frame_digest"].astext.is_distinct_from(p["frame_digest"].astext),
                    grade["frame_digest"].astext.is_distinct_from(
                        func.encode(
                            func.sha256(
                                func.convert_to(grade["frame_canonical_json"].astext, "UTF8")
                            ),
                            "hex",
                        )
                    ),
                    cast(grade["frame_canonical_json"].astext, JSONB()).is_distinct_from(
                        grade["frame"]
                    ),
                    Grouping(project_for_frame).is_distinct_from(d("project_id")),
                ),
                "feature fit grade canonical frame differs",
                "23514",
            ),
            Assign(
                "result",
                obj(
                    variant=variant,
                    cut=cut,
                    product_id=p_product,
                    derivation_id=p_derivation,
                    receipt_id=receipt_id,
                    frame=grade,
                ),
            ),
            _check(
                func.octet_length(func.data.canonical_json(result))
                > func.coalesce(cast(p["max_bytes"].astext, BigInteger()), 8388608),
                "feature fit frame exceeds explicit byte bound",
                "23514",
            ),
            Return(obj(payload=result)),
        ),
        (
            Local("p", pg_type("jsonb"), _value("p_payload", JSONB())),
            *(
                Local(name, relation)
                for name, relation in (
                    ("d", demands),
                    ("boundary", boundaries),
                    ("definition", definitions),
                    ("episode", episodes),
                    ("intent", intents),
                )
            ),
            *(
                Local(name, pg_type("text"), p[field].astext)
                for name, field in (
                    ("p_use", "use_id"),
                    ("p_product", "product_id"),
                    ("p_derivation", "derivation_id"),
                    ("variant", "variant"),
                )
            ),
            *(Local(name, pg_type("jsonb")) for name in ("snapshot", "cut", "grade", "result")),
            Local("admitted", pg_type("boolean")),
            *(
                Local(name, pg_type("text"))
                for name in (
                    "expected_operation",
                    "expected_factory",
                    "expected_kind",
                    "expected_role",
                    "receipt_id",
                )
            ),
        ),
        stable=False,
    )
    return "\n".join((principal_guard, body_access, read_frame))
