"""Captured native custody for selected operation-event frames and parameters."""

from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Integer,
    MetaData,
    Table,
    Text,
    and_,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    tuple_,
    union,
)
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.evaluate.declared_operation_events import (
    AUTHORIZATION_EFFECT,
    AUTHORIZATION_FACTORY,
    AUTHORIZATION_OPERATION,
    NAMESPACE,
)

from .data_operation_projections import selected_support_output
from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .types import SourceArtifact

_OPERATIONS = (
    "operation_event.frame",
    "operation_event.fit",
    "operation_event.authorize",
    "urn:corpus:operation:score-operation-event",
)
_SCORE = _OPERATIONS[-1]


def _json(value):
    import json

    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB())


def _at(value, *path):
    for item in path:
        value = value[item]
    return value


def _text(value, *path):
    return _at(value, *path).astext


def _items(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _object(**fields):
    return func.jsonb_build_object(
        *(part for key, value in fields.items() for part in (key, value)), type_=JSONB()
    )


def _digest_text(value):
    return func.encode(func.sha256(func.convert_to(value, "UTF8")), "hex")


def _reject(condition, message):
    return If(condition, (Raise(message, "23514"),))


@dataclass(frozen=True)
class _Record:
    name: str
    table: Table

    def __call__(self, field=None):
        return core_variable(
            self.name,
            self.table.table_valued().type if field is None else self.table.c[field].type,
            field,
        )

    def local(self):
        return Local(self.name, self.table)

    def lookup(self, *where):
        return SelectInto(
            select(core_relation_row(self.table)).select_from(self.table).where(*where),
            (self.name,),
            strict=True,
        )


class _Programs:
    def __init__(self, model: MetaData):
        self.model = model
        self.output: list[str] = []

    def row(self, name, table):
        return _Record(name, self.model.tables[table])

    def add(
        self,
        name,
        parameters,
        steps,
        locals_=(),
        *,
        returns="void",
        setof=False,
        immutable=False,
        strict=False,
        definer=True,
        query=None,
    ):
        kind = pg_type(returns)
        kind.setof = setof
        params = tuple(Parameter(key, pg_type(*type_.split("."))) for key, type_ in parameters)
        if query is not None:
            self.output.append(
                sql_function(
                    "ops",
                    name,
                    parameters=params,
                    returns=kind,
                    body=query,
                    search_path=("pg_catalog", "pg_temp"),
                    volatility="immutable" if immutable else "stable",
                    strict=strict,
                )
            )
        else:
            self.output.append(
                function(
                    "ops",
                    name,
                    parameters=params,
                    returns=kind,
                    body=Block(tuple(steps), tuple(locals_)),
                    security_definer=definer,
                    search_path=("pg_catalog", "pg_temp"),
                    volatility="immutable" if immutable else "stable",
                    strict=strict,
                )
            )
        self.output.append(
            native_privilege_sql(
                NativeIdentity("function", "ops", name, tuple(kind for _, kind in parameters)),
                "PUBLIC",
                grant=False,
            )
        )

    def restore(self, request, producer, intent):
        return (
            *(
                Assign((request.name, key), producer(key))
                for key in ("release_id", "runtime_id", "recipe", "generation")
            ),
            Assign(
                (request.name, "binding"),
                request("binding").op("||")(
                    _object(
                        inputs=intent("payload")["inputs"], support=intent("payload")["support"]
                    )
                ),
            ),
        )

    def fences(self, producer, intent):
        fields = ("producer_task_id", "producer_attempt", "runtime_id")
        return tuple_(*(intent(key) for key in fields)).is_distinct_from(
            tuple_(*(producer(key) for key in fields))
        )


def operation_event_native_sql(model: MetaData) -> str:
    programs = _Programs(model)
    _eligibility(programs)
    _scopes(programs)
    _require_frame(programs)
    _require_fit(programs)
    _require_parameters(programs)
    _completion(programs)
    _dependencies(programs)
    return native_sql_script(programs.output) + "\n"


def operation_event_native_sources(*, target_metadata: MetaData) -> tuple[SourceArtifact, ...]:
    """Keep the existing frozen helper and producer source artifact identities."""
    root = Path(__file__).parents[1]
    return (
        SourceArtifact(
            "native/data-operation-operation-event.sql",
            operation_event_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-operation-event-native.py", Path(__file__).read_bytes()
        ),
        SourceArtifact(
            "native/data-operation-operation-event-producers.py",
            (root / "evaluate/declared_operation_events.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-operation-event-methods.py",
            (root / "methods/operation_events.py").read_bytes(),
        ),
    )


def _eligibility(p):
    definition = p.row("definition", "sem.data_operation_definition")
    contract = definition("support_contract")
    capabilities = contract["capabilities"]
    p.add(
        "ddo_operation_event_command_eligible",
        (("definition", "sem.data_operation_definition"),),
        (),
        returns="bool",
        immutable=True,
        strict=True,
        definer=False,
        query=select(
            and_(
                definition("operation_id") == AUTHORIZATION_OPERATION,
                definition("profile") == "command",
                _text(capabilities, "preparation") == "native-publication",
                capabilities["forms"] == _json(["scalar"]),
                _text(capabilities, "prepared_factory", "entrypoint") == AUTHORIZATION_FACTORY,
                contract["effects"] == _json([asdict(AUTHORIZATION_EFFECT)]),
                _text(capabilities, "prepared_factory", "source_digest").bool_op("~")(
                    "^[0-9a-f]{64}$"
                ),
                definition("implementation_revision").like("implementation-slice:%"),
            )
        ),
    )


def _cut_pair(question):
    return union(select(question["original_selection"]), select(question["prediction_selection"]))


def _scopes(p):
    r = p.row("r", "ops.data_request")
    question, specification, selected = (
        core_variable(name, JSONB()) for name in ("question", "specification", "selected")
    )
    grade_scopes = (
        func.ops.ddo_record_grade_cut_scopes(r("project_id"), _text(selected, "cut_canonical_json"))
        .table_valued(column("scope", Text()))
        .render_derived(name="grade_scope")
    )
    fit_scopes = (
        func.ops.ddo_record_fit_cut_scopes(r("project_id"), selected)
        .table_valued(column("scope", Text()))
        .render_derived(name="fit_scope")
    )
    p.add(
        "ddo_operation_event_completion_scopes",
        (("r", "ops.data_request"),),
        (
            If(
                r("operation_id") == "operation_event.frame",
                (
                    Assign(
                        "question",
                        func.ops.ddo_record_grade_input(r(), "question", type_=JSONB())["body"],
                    ),
                    ForQuery(
                        ("selected",),
                        _cut_pair(question),
                        (
                            _reject(
                                _text(selected, "project_id").is_distinct_from(r("project_id")),
                                "event frame cut belongs to another project",
                            ),
                            ReturnQuery(select(grade_scopes.c.scope)),
                        ),
                    ),
                ),
                (
                    If(
                        r("operation_id") == "operation_event.fit",
                        (
                            Assign(
                                "specification",
                                func.ops.ddo_record_grade_input(
                                    r(), "specification", type_=JSONB()
                                )["body"],
                            ),
                            Assign("selected", specification["frame"]["selection"]),
                            ReturnQuery(select(fit_scopes.c.scope)),
                        ),
                    ),
                ),
            ),
        ),
        tuple(Local(name, pg_type("jsonb")) for name in ("question", "specification", "selected")),
        returns="text",
        setof=True,
    )
    producer, intent = (
        p.row("producing", "ops.data_derivation"),
        p.row("intent", "ops.data_completion_intent"),
    )
    episode = core_variable("episode", Text())
    scopes = (
        func.ops.ddo_operation_event_completion_scopes(r())
        .table_valued(column("scope", Text()))
        .render_derived(name="event_scope")
    )
    p.add(
        "ddo_operation_event_dependency_scopes",
        (("episode", "text"),),
        (
            producer.lookup(producer.table.c.id == episode),
            r.lookup(r.table.c.id == producer("request_id")),
            If(r("operation_id").not_in(_OPERATIONS), (Return(),)),
            intent.lookup(
                intent.table.c.id == producer("intent_id"),
                intent.table.c.request_id == producer("request_id"),
                intent.table.c.generation == producer("generation"),
            ),
            _reject(
                p.fences(producer, intent),
                "event dependency scopes differ from original producer fences",
            ),
            *p.restore(r, producer, intent),
            ReturnQuery(select(scopes.c.scope)),
        ),
        (r.local(), producer.local(), intent.local()),
        returns="text",
        setof=True,
    )


def _require_frame(p):
    r, question_product, report_product, producer, definition = (
        p.row(name, table)
        for name, table in (
            ("r", "ops.data_request"),
            ("question_product", "kb.data_product"),
            ("report_product", "kb.data_product"),
            ("producer", "ops.data_derivation"),
            ("definition", "sem.data_operation_definition"),
        )
    )
    products, kinds, requests = (
        question_product.table,
        p.model.tables["sem.data_kind_contract"],
        r.table,
    )
    (
        body,
        question,
        frame,
        selected,
        original_census,
        prediction_census,
        report_pin,
        source_pin,
        bound,
        actual,
        cpu_roles,
        role_meaning,
        use,
        reports,
        sources,
    ) = (
        core_variable(name, JSONB())
        for name in (
            "body",
            "question",
            "frame",
            "selected",
            "original_census",
            "prediction_census",
            "report_pin",
            "source_pin",
            "bound",
            "actual",
            "cpu_roles",
            "role_meaning",
            "u",
            "reports_",
            "sources_",
        )
    )
    inputs = _items(r("binding")["inputs"], "item")
    support = _items(r("binding")["support"], "support")
    original_outputs, prediction_outputs = (
        _items(original_census["outputs"], "original_output"),
        _items(prediction_census["outputs"], "prediction_output"),
    )
    judgments, roles = _items(question["judgments"], "judgment"), _items(cpu_roles[1], "cpu_role")
    selected_cut = cast(_text(selected, "cut_canonical_json"), JSONB())
    components = _items(
        func.data.ddo_json(report_product("canonical_body"), type_=JSONB())[
            "definition_components"
        ]["components"],
        "component",
    )
    report_reference = func.jsonb_build_array(
        _text(source_pin, "source_product"), _text(source_pin, "source_member")
    )
    source_context = _object(
        **{
            key: _text(source_pin, source)
            for key, source in (
                ("product_id", "source_product"),
                ("member_id", "source_member"),
                ("project_id", "project_id"),
                ("kind_contract", "kind_contract"),
                ("subject", "subject"),
                ("subject_definition", "subject_definition"),
                ("original_source", "original_source"),
            )
        }
    )
    steps = (
        SelectInto(
            select(core_relation_row(products))
            .select_from(
                inputs.join(
                    products,
                    and_(
                        products.c.id == _text(inputs.c.value, "product_id"),
                        products.c.project_id == r("project_id"),
                    ),
                ).join(kinds, kinds.c.kind_contract == products.c.kind_contract)
            )
            .where(
                _text(inputs.c.value, "role") == "question",
                _text(inputs.c.value, "member_id").is_(None),
                cast(_text(inputs.c.value, "multiplicity"), Integer()) == 1,
                kinds.c.kind == NAMESPACE + "DdoOperationEventQuestion",
                kinds.c.universe == "evaluator",
            ),
            ("question_product",),
            strict=True,
        ),
        Assign("question", func.data.ddo_json(question_product("canonical_body"))),
        _reject(
            or_(
                _text(body, "version").is_distinct_from("selected-operation-event-frame-product-1"),
                _text(body, "frame_digest").is_distinct_from(
                    _digest_text(_text(body, "frame_canonical_json"))
                ),
                cast(_text(body, "frame_canonical_json"), JSONB()).is_distinct_from(frame),
                frame["question"].is_distinct_from(question),
                frame["question_reference"].is_distinct_from(
                    func.ops.ddo_structural_product_reference(question_product())
                ),
                _text(question, "pass_kind").is_distinct_from("C"),
                _text(question, "exposure").is_distinct_from("output_first"),
                _text(question, "partition").not_in(("development", "feature_fit")),
            ),
            "event frame changes actual protected question or exact canonical frame",
        ),
        ForQuery(
            ("selected",),
            _cut_pair(question),
            (
                _reject(
                    or_(
                        _text(selected, "project_id").is_distinct_from(r("project_id")),
                        *(
                            _text(selected_cut, field).is_distinct_from(_text(selected, field))
                            for field in ("demand_id", "read_id", "release_id", "runtime_id")
                        ),
                    ),
                    "event question changes exact native cut pins",
                ),
                Perform(
                    func.ops.ddo_record_grade_require_cut(
                        r("project_id"),
                        _text(selected, "cut_canonical_json"),
                        _text(selected, "cut_id"),
                    )
                ),
            ),
        ),
        *(
            Assign(
                name + "_census",
                func.ops.ddo_record_grade_acquire_census(
                    r("project_id"),
                    _text(question, name + "_selection", "cut_canonical_json"),
                    _text(question, name + "_selection", "cut_id"),
                ),
            )
            for name in ("original", "prediction")
        ),
        ForQuery(
            ("selected",),
            select(judgments.c.value["selection"]),
            (
                Assign("report_pin", selected["report"]),
                Assign("source_pin", selected["source"]),
                _reject(
                    _text(selected, "origin_group").is_distinct_from(
                        _text(source_pin, "original_source")
                    ),
                    "event origin group differs from actual original source",
                ),
                If(
                    ~reports.bool_op("?")(_text(report_pin, "product_id")),
                    (
                        Assign(
                            "reports_",
                            reports.op("||")(
                                func.jsonb_build_array(_text(report_pin, "product_id"))
                            ),
                        ),
                    ),
                ),
                If(
                    ~sources.bool_op("@>")(func.jsonb_build_array(report_reference)),
                    (
                        Assign(
                            "sources_", sources.op("||")(func.jsonb_build_array(report_reference))
                        ),
                    ),
                ),
                SelectInto(
                    select(inputs.c.value).where(
                        _text(inputs.c.value, "role") == "reports",
                        _text(inputs.c.value, "product_id") == _text(report_pin, "product_id"),
                        _text(inputs.c.value, "member_id").is_(None),
                        cast(_text(inputs.c.value, "multiplicity"), Integer()) == 1,
                    ),
                    ("bound",),
                    strict=True,
                ),
                report_product.lookup(
                    products.c.id == _text(report_pin, "product_id"),
                    products.c.project_id == r("project_id"),
                ),
                _reject(
                    or_(
                        report_pin.is_distinct_from(
                            func.ops.ddo_structural_product_reference(report_product())
                        ),
                        ~select(1)
                        .select_from(prediction_outputs)
                        .where(
                            _text(prediction_outputs.c.value, "product_id") == report_product("id"),
                            _text(prediction_outputs.c.value, "derivation_id")
                            == _text(selected, "derivation_id"),
                        )
                        .exists(),
                        ~select(1)
                        .select_from(support)
                        .where(
                            _text(support.c.value, "role") == "reports",
                            _text(support.c.value, "derivation_id")
                            == _text(selected, "derivation_id"),
                        )
                        .exists(),
                    ),
                    "event report changes actual selected whole context/producer support",
                ),
                Assign("u", prediction_census["uses"][_text(selected, "use_id")]),
                _reject(
                    or_(
                        use.is_(None),
                        _text(use, "derivation_id").is_distinct_from(
                            _text(selected, "derivation_id")
                        ),
                        _text(use, "completion_state").is_distinct_from("success"),
                        _text(use, "fate").not_in(("fulfilled", "attached")),
                    ),
                    "event report lacks its exact successful selected native use",
                ),
                producer.lookup(
                    producer.table.c.id == _text(selected, "derivation_id"),
                    producer.table.c.outcome == "success",
                ),
                SelectInto(
                    select(core_relation_row(definition.table))
                    .select_from(
                        definition.table.join(
                            requests, requests.c.operation_id == definition.table.c.operation_id
                        )
                    )
                    .where(
                        requests.c.id == producer("request_id"),
                        requests.c.project_id == r("project_id"),
                        definition.table.c.release_id == producer("release_id"),
                    ),
                    ("definition",),
                    strict=True,
                ),
                _reject(
                    or_(
                        definition("operation_id").is_distinct_from(
                            _text(selected, "producer_operation")
                        ),
                        definition("implementation_revision").is_distinct_from(
                            _text(selected, "producer_revision")
                        ),
                        producer("release_id").is_distinct_from(
                            _text(question, "prediction_selection", "release_id")
                        ),
                    ),
                    "event report changes its actual admitted producer revision/release",
                ),
                SelectInto(
                    select(roles.c.value).where(
                        _text(func.data.ddo_json(roles.c.value, type_=JSONB()), "role")
                        == "reports",
                        _text(func.data.ddo_json(roles.c.value, type_=JSONB()), "product_id")
                        == report_product("id"),
                    ),
                    ("role_meaning",),
                    strict=True,
                ),
                Perform(func.ops.ddo_definition_component_basis(role_meaning)),
                _reject(
                    ~select(1)
                    .select_from(components)
                    .where(
                        _text(components.c.value, "component_id") == _text(selected, "component_id")
                    )
                    .exists(),
                    "event component is absent from its actual whole report",
                ),
                SelectInto(
                    select(inputs.c.value).where(
                        _text(inputs.c.value, "role") == "sources",
                        _text(inputs.c.value, "product_id") == _text(source_pin, "source_product"),
                        _text(inputs.c.value, "member_id").is_not_distinct_from(
                            _text(source_pin, "source_member")
                        ),
                        cast(_text(inputs.c.value, "multiplicity"), Integer()) == 1,
                    ),
                    ("bound",),
                    strict=True,
                ),
                _reject(
                    ~select(1)
                    .select_from(original_outputs)
                    .where(
                        _text(original_outputs.c.value, "product_id")
                        == _text(source_pin, "source_product")
                    )
                    .exists(),
                    "event original source is outside exact original selected support",
                ),
                Assign(
                    "actual",
                    func.ops.ddo_record_grade_input_value(
                        r("project_id"), _text(bound, "product_id"), _text(bound, "member_id")
                    ),
                ),
                _reject(
                    or_(
                        actual.op("-")("body")
                        .op("-")("analyzed_scope_meaning")
                        .is_distinct_from(source_context),
                        actual["analyzed_scope_meaning"].is_distinct_from(
                            cast(_text(source_pin, "analyzed_scope_meaning"), JSONB())
                        ),
                        *(
                            _text(actual, "body", "source", field).is_distinct_from(
                                _text(source_pin, target)
                            )
                            for field, target in (
                                ("document", "document"),
                                ("projection", "projection_digest"),
                                ("section_pointer", "section_pointer"),
                                ("membership", "membership"),
                            )
                        ),
                    ),
                    "event source pin changes exact selected coordinate/context",
                ),
            ),
        ),
        _reject(
            or_(
                *(
                    select(func.count())
                    .select_from(inputs)
                    .where(_text(inputs.c.value, "role") == role)
                    .scalar_subquery()
                    != func.jsonb_array_length(expected)
                    for role, expected in (("reports", reports), ("sources", sources))
                )
            ),
            "event frame changes the exact declared report/source population",
        ),
    )
    p.add(
        "ddo_operation_event_require_frame",
        (("r", "ops.data_request"), ("body", "jsonb")),
        steps,
        (
            question_product.local(),
            Local("question", pg_type("jsonb")),
            Local("frame", pg_type("jsonb"), body["frame"]),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "selected",
                    "original_census",
                    "prediction_census",
                    "report_pin",
                    "source_pin",
                    "bound",
                    "actual",
                )
            ),
            report_product.local(),
            producer.local(),
            definition.local(),
            Local(
                "cpu_roles",
                pg_type("jsonb"),
                func.data.ddo_field(func.ops.ddo_cpu_input_basis(r()), "roles"),
            ),
            Local("role_meaning", pg_type("jsonb")),
            Local("u", pg_type("jsonb")),
            Local("reports_", pg_type("jsonb"), _json([])),
            Local("sources_", pg_type("jsonb"), _json([])),
        ),
    )


def _require_fit(p):
    r, demand, boundary, producer, frame_request, intent, actual, definition = (
        p.row(name, table)
        for name, table in (
            ("r", "ops.data_request"),
            ("d", "ops.data_demand"),
            ("boundary", "ops.data_demand_read"),
            ("producer", "ops.data_derivation"),
            ("frame_request", "ops.data_request"),
            ("intent", "ops.data_completion_intent"),
            ("actual", "kb.data_product"),
            ("definition", "sem.data_operation_definition"),
        )
    )
    body, specification, selected, selection = (
        core_variable(name, JSONB()) for name in ("body", "specification", "selected", "selection_")
    )
    product, derivation = core_variable("p_product", Text()), core_variable("p_derivation", Text())
    admitted = core_variable("admitted", Boolean())
    inputs, support = (
        _items(r("binding")["inputs"], "item"),
        _items(r("binding")["support"], "support"),
    )
    receipts, outputs = (
        p.model.tables["ops.data_publication_receipt"],
        p.model.tables["ops.data_derivation_output"],
    )
    current_receipt = (
        select(1)
        .select_from(receipts.join(outputs, outputs.c.derivation_id == receipts.c.derivation_id))
        .where(
            receipts.c.derivation_id == producer("id"),
            receipts.c.intent_id == intent("id"),
            outputs.c.product_id == product,
            outputs.c.member_id.is_(None),
            outputs.c.role == "frame",
        )
        .exists()
    )
    parameters = body["result"]["parameters"]
    p.add(
        "ddo_operation_event_require_fit",
        (("r", "ops.data_request"), ("body", "jsonb")),
        (
            _reject(
                or_(
                    _text(selection, "project_id").is_distinct_from(r("project_id")),
                    _text(selected, "reference", "member_id").is_not(None),
                    _text(selection, "cut_id").is_distinct_from(
                        literal("cut-selection:")
                        + _digest_text(_text(selection, "cut_canonical_json"))
                    ),
                ),
                "event fit changes exact selected frame project/cut",
            ),
            Perform(func.ops.ddo_record_fit_cut_scopes(r("project_id"), selection)),
            demand.lookup(
                demand.table.c.id == _text(selection, "demand_id"),
                demand.table.c.project_id == r("project_id"),
            ),
            boundary.lookup(
                boundary.table.c.id == _text(selection, "read_id"),
                boundary.table.c.demand_id == demand("id"),
            ),
            Perform(func.ops.ddo_require_read_current(boundary(), r("project_id"), True)),
            Assign("p", _object(scope=boundary("scope"))),
            SelectInto(selected_support_output(p.model), ("admitted",)),
            _reject(
                ~func.coalesce(admitted, False),
                "event frame is outside exact native selected support",
            ),
            SelectInto(
                select(inputs.c.value).where(
                    _text(inputs.c.value, "role") == "frame",
                    _text(inputs.c.value, "product_id") == product,
                    _text(inputs.c.value, "member_id").is_(None),
                    cast(_text(inputs.c.value, "multiplicity"), Integer()) == 1,
                ),
                ("chosen",),
                strict=True,
            ),
            _reject(
                ~select(1)
                .select_from(support)
                .where(
                    _text(support.c.value, "role") == "frame",
                    _text(support.c.value, "derivation_id") == derivation,
                )
                .exists(),
                "event fit changes exact frame producing support",
            ),
            producer.lookup(
                producer.table.c.id == derivation, producer.table.c.outcome == "success"
            ),
            frame_request.lookup(
                frame_request.table.c.id == producer("request_id"),
                frame_request.table.c.project_id == r("project_id"),
            ),
            intent.lookup(
                intent.table.c.id == producer("intent_id"),
                intent.table.c.request_id == producer("request_id"),
                intent.table.c.generation == producer("generation"),
            ),
            _reject(
                p.fences(producer, intent), "event frame differs from original producer fences"
            ),
            *p.restore(frame_request, producer, intent),
            definition.lookup(
                definition.table.c.release_id == producer("release_id"),
                definition.table.c.operation_id == frame_request("operation_id"),
            ),
            actual.lookup(
                actual.table.c.id == product, actual.table.c.project_id == r("project_id")
            ),
            _reject(
                or_(
                    selected["reference"].is_distinct_from(
                        func.ops.ddo_structural_product_reference(actual())
                    ),
                    _text(
                        func.data.ddo_json(actual("canonical_body"), type_=JSONB()), "frame_digest"
                    ).is_distinct_from(_text(selected, "frame_digest")),
                    definition("operation_id").is_distinct_from("operation_event.frame"),
                    ~current_receipt,
                ),
                "event fit lacks actual selected current frame CPU/common receipt",
            ),
            Perform(
                func.ops.ddo_require_operation_event_completion(frame_request(), intent("payload"))
            ),
            _reject(
                func.data.ddo_normalize(
                    _at(intent("payload"), "outputs", 0, "product", "body")
                ).is_distinct_from(actual("canonical_body")),
                "event frame differs from actual original CPU completion body",
            ),
            _reject(
                or_(
                    body["specification"].is_distinct_from(specification),
                    _text(body, "result", "frame_digest").is_distinct_from(
                        _text(selected, "frame_digest")
                    ),
                    and_(
                        parameters.is_not(None),
                        parameters != _json(None),
                        or_(
                            parameters["algorithm"].is_distinct_from(specification["algorithm"]),
                            _text(parameters, "frame_digest").is_distinct_from(
                                _text(selected, "frame_digest")
                            ),
                        ),
                    ),
                ),
                "event fit changes actual frame identity or declared algorithm",
            ),
        ),
        (
            Local(
                "specification",
                pg_type("jsonb"),
                func.ops.ddo_record_grade_input(r(), "specification", type_=JSONB())["body"],
            ),
            Local("selected", pg_type("jsonb"), specification["frame"]),
            Local("selection_", pg_type("jsonb"), selected["selection"]),
            demand.local(),
            boundary.local(),
            Local("p", pg_type("jsonb")),
            Local("p_use", pg_type("text"), _text(selected, "use_id")),
            Local("p_product", pg_type("text"), _text(selected, "reference", "product_id")),
            Local("p_derivation", pg_type("text"), _text(selected, "derivation_id")),
            Local("admitted", pg_type("bool")),
            Local("chosen", pg_type("jsonb")),
            producer.local(),
            frame_request.local(),
            intent.local(),
            actual.local(),
            definition.local(),
        ),
    )


def _require_parameters(p):
    r, issuing, issuer_request, intent = (
        p.row(name, table)
        for name, table in (
            ("r", "ops.data_request"),
            ("issuing", "ops.data_derivation"),
            ("issuer_request", "ops.data_request"),
            ("intent", "ops.data_completion_intent"),
        )
    )
    products, requests, definitions, receipts, outputs = (
        p.model.tables[name]
        for name in (
            "kb.data_product",
            "ops.data_request",
            "sem.data_operation_definition",
            "ops.data_publication_receipt",
            "ops.data_derivation_output",
        )
    )
    chosen = core_variable("chosen", JSONB())
    inputs, support = (
        _items(r("binding")["inputs"], "item"),
        _items(r("binding")["support"], "support"),
    )
    producer = issuing.table
    protected_context = (
        select(1)
        .select_from(products)
        .where(
            products.c.id == _text(chosen, "product_id"),
            products.c.project_id == r("project_id"),
            products.c.subject == r("subject"),
            products.c.subject_definition
            == func.ops.ddo_operation_subject(r("release_id"), r("operation_id")),
            products.c.original_source.is_not_distinct_from(r("original_source")),
            products.c.analyzed_scope == r("analyzed_scope"),
        )
        .exists()
    )
    producer_query = (
        select(core_relation_row(producer))
        .select_from(
            producer.join(outputs, outputs.c.derivation_id == producer.c.id)
            .join(
                receipts,
                and_(
                    receipts.c.derivation_id == producer.c.id,
                    receipts.c.intent_id == producer.c.intent_id,
                ),
            )
            .join(
                requests,
                and_(
                    requests.c.id == producer.c.request_id, requests.c.project_id == r("project_id")
                ),
            )
            .join(
                definitions,
                and_(
                    definitions.c.release_id == producer.c.release_id,
                    definitions.c.operation_id == requests.c.operation_id,
                ),
            )
        )
        .where(
            outputs.c.product_id == _text(chosen, "product_id"),
            outputs.c.member_id.is_(None),
            outputs.c.role == "parameters",
            outputs.c.position == 0,
            outputs.c.multiplicity == 1,
            producer.c.outcome == "success",
            definitions.c.command_class == "operation_event",
            select(1)
            .select_from(support)
            .where(
                _text(support.c.value, "role") == "parameters",
                _text(support.c.value, "derivation_id") == producer.c.id,
            )
            .exists(),
            func.ops.ddo_input_support_selection(chosen).bool_op("?")(producer.c.id),
        )
    )
    p.add(
        "ddo_operation_event_require_parameters",
        (("r", "ops.data_request"),),
        (
            SelectInto(
                select(inputs.c.value).where(
                    _text(inputs.c.value, "role") == "parameters",
                    _text(inputs.c.value, "member_id").is_(None),
                    cast(_text(inputs.c.value, "multiplicity"), Integer()) == 1,
                ),
                ("chosen",),
                strict=True,
            ),
            _reject(
                ~protected_context, "event score parameters change exact selected event context"
            ),
            SelectInto(producer_query, ("issuing",), strict=True),
            issuer_request.lookup(
                requests.c.id == issuing("request_id"), requests.c.project_id == r("project_id")
            ),
            intent.lookup(
                intent.table.c.id == issuing("intent_id"),
                intent.table.c.request_id == issuing("request_id"),
                intent.table.c.generation == issuing("generation"),
            ),
            _reject(
                p.fences(issuing, intent),
                "event parameter issuer differs from original producer fences",
            ),
            *p.restore(issuer_request, issuing, intent),
            Perform(
                func.ops.ddo_require_operation_event_completion(issuer_request(), intent("payload"))
            ),
            _reject(
                func.data.ddo_normalize(
                    _at(intent("payload"), "outputs", 0, "product", "body")
                ).is_distinct_from(
                    select(products.c.canonical_body)
                    .where(
                        products.c.id == _text(chosen, "product_id"),
                        products.c.project_id == r("project_id"),
                    )
                    .scalar_subquery()
                ),
                "event score parameters differ from actual original native issuer",
            ),
        ),
        (
            Local("chosen", pg_type("jsonb")),
            issuing.local(),
            issuer_request.local(),
            intent.local(),
        ),
    )


def _completion(p):
    r, definition, basis, producing, fit_request, fit_intent = (
        p.row(name, table)
        for name, table in (
            ("r", "ops.data_request"),
            ("definition", "sem.data_operation_definition"),
            ("basis", "kb.data_product"),
            ("producing", "ops.data_derivation"),
            ("fit_request", "ops.data_request"),
            ("fit_intent", "ops.data_completion_intent"),
        )
    )
    completion, output, body, selected, expected = (
        core_variable(name, JSONB())
        for name in ("completion", "output", "body", "selected", "expected")
    )
    expected_factory, output_role, output_kind = (
        core_variable(name, Text()) for name in ("expected_factory", "output_role", "output_kind")
    )
    kinds, products, producers, outputs, receipts = (
        p.model.tables[name]
        for name in (
            "sem.data_kind_contract",
            "kb.data_product",
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
        )
    )
    supports = _items(completion["support"], "support")
    fit_body = func.data.ddo_json(basis("canonical_body"), type_=JSONB())
    payload = fit_intent("payload")
    authorization = (
        _reject(
            or_(
                ~func.coalesce(definition("command_class") == "operation_event", False),
                func.jsonb_array_length(completion["inputs"]) != 1,
            ),
            "operation event issuer requires exact command/effect/factory and fit basis",
        ),
        Assign("output_role", literal("parameters")),
        Assign("output_kind", literal("urn:corpus:kind:operation-event:parameters")),
        Assign("selected", completion["inputs"][0]),
        _reject(
            or_(
                _text(selected, "role").is_distinct_from("basis"),
                _text(selected, "member_id").is_not(None),
                cast(_text(selected, "multiplicity"), Integer()) != 1,
            ),
            "event issuer requires actual whole protected fit basis",
        ),
        SelectInto(
            select(core_relation_row(products))
            .select_from(products.join(kinds, kinds.c.kind_contract == products.c.kind_contract))
            .where(
                products.c.id == _text(selected, "product_id"),
                products.c.project_id == r("project_id"),
                kinds.c.kind == NAMESPACE + "DdoOperationEventFit",
                kinds.c.universe == "evaluator",
            ),
            ("basis",),
            strict=True,
        ),
        SelectInto(
            select(core_relation_row(producers))
            .select_from(
                producers.join(outputs, outputs.c.derivation_id == producers.c.id).join(
                    receipts,
                    and_(
                        receipts.c.derivation_id == producers.c.id,
                        receipts.c.intent_id == producers.c.intent_id,
                    ),
                )
            )
            .where(
                outputs.c.product_id == basis("id"),
                outputs.c.member_id.is_(None),
                outputs.c.role == "fit",
                producers.c.outcome == "success",
                select(1)
                .select_from(supports)
                .where(
                    _text(supports.c.value, "role") == "basis",
                    _text(supports.c.value, "derivation_id") == producers.c.id,
                )
                .exists(),
                func.ops.ddo_input_support_selection(selected).bool_op("?")(producers.c.id),
            ),
            ("producing",),
            strict=True,
        ),
        fit_request.lookup(
            fit_request.table.c.id == producing("request_id"),
            fit_request.table.c.project_id == r("project_id"),
            fit_request.table.c.operation_id == "operation_event.fit",
        ),
        fit_intent.lookup(
            fit_intent.table.c.id == producing("intent_id"),
            fit_intent.table.c.request_id == producing("request_id"),
            fit_intent.table.c.generation == producing("generation"),
        ),
        _reject(p.fences(producing, fit_intent), "event fit differs from original producer fences"),
        *p.restore(fit_request, producing, fit_intent),
        Perform(func.ops.ddo_require_operation_event_completion(fit_request(), payload)),
        _reject(
            or_(
                func.data.ddo_normalize(
                    _at(payload, "outputs", 0, "product", "body")
                ).is_distinct_from(basis("canonical_body")),
                _text(fit_body, "result", "status").is_distinct_from("fitted"),
            ),
            "event issuer basis differs from actual successful protected CPU fit",
        ),
        Assign(
            "expected",
            func.data.ddo_field(
                func.data.ddo_field(basis("canonical_body"), "result"), "parameters"
            ),
        ),
        _reject(
            or_(
                expected == _json(["null"]),
                func.data.ddo_normalize(_at(output, "product", "body")).is_distinct_from(expected),
            ),
            "event issuer may disclose only exact fitted strict parameters",
        ),
    )
    is_frame, is_fit, is_score = (
        r("operation_id") == name
        for name in ("operation_event.frame", "operation_event.fit", _SCORE)
    )
    contract = definition("support_contract")
    derivation = (
        Assign("output_role", case((is_frame, "frame"), (is_fit, "fit"), else_="probability")),
        Assign(
            "output_kind",
            literal(NAMESPACE)
            + case((is_frame, "DdoOperationEventFrame"), else_="DdoOperationEventFit"),
        ),
        Assign(
            "expected_factory",
            case(
                (
                    is_score,
                    "corpus_structure.semantic.operation_policy.acquire_operation_event_score_port",
                ),
                else_=literal("corpus_structure.methods.operation_events.")
                + case((is_frame, "OperationEventFrame"), else_="OperationEventFit")
                + literal(".acquire_port"),
            ),
        ),
        _reject(
            or_(
                definition("profile").is_distinct_from("derivation"),
                contract["effects"].is_distinct_from(_json([])),
                _text(contract, "capabilities", "prepared_factory", "entrypoint").is_distinct_from(
                    expected_factory
                ),
                _text(contract, "capabilities", "prepared_factory", "source_digest")
                .bool_op("~")("^[0-9a-f]{64}$")
                .is_not(True),
                definition("implementation_revision").like("implementation-slice:%").is_not(True),
                func.jsonb_array_length(
                    func.coalesce(_at(completion, "execution_evidence", "cpu_receipts"), _json([]))
                )
                != 1,
                func.data.ddo_normalize(_at(output, "product", "body")).is_distinct_from(
                    func.ops.ddo_cpu_reply_output(r(), completion)
                ),
            ),
            "event conclusion differs from actual admitted CPU body/factory/receipt",
        ),
        Assign("body", func.data.ddo_json(_at(output, "product", "body"))),
        If(
            is_frame,
            (Perform(func.ops.ddo_operation_event_require_frame(r(), body)),),
            (
                If(
                    is_fit,
                    (Perform(func.ops.ddo_operation_event_require_fit(r(), body)),),
                    (Perform(func.ops.ddo_operation_event_require_parameters(r())),),
                ),
            ),
        ),
    )
    exact_kind = (
        select(1)
        .select_from(kinds)
        .where(
            kinds.c.kind_contract == _text(output, "product", "kind_contract"),
            case(
                (
                    is_score,
                    kinds.c.kind_contract == definition("output_roles")[0]["kind_contract"].astext,
                ),
                else_=kinds.c.kind == output_kind,
            ),
            kinds.c.universe
            == case(
                (r("operation_id").in_(("operation_event.authorize", _SCORE)), "ordinary"),
                else_="evaluator",
            ),
        )
        .exists()
    )
    p.add(
        "ddo_require_operation_event_completion",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(r("operation_id").not_in(_OPERATIONS), (Return(),)),
            definition.lookup(
                definition.table.c.release_id == r("release_id"),
                definition.table.c.operation_id == r("operation_id"),
            ),
            _reject(
                or_(
                    _text(completion, "outcome").is_distinct_from("success"),
                    func.jsonb_array_length(completion["outputs"]) != 1,
                    completion["inputs"].is_distinct_from(r("binding")["inputs"]),
                    completion["support"].is_distinct_from(r("binding")["support"]),
                    definition("implementation_revision").is_distinct_from(
                        _text(completion, "implementation_revision")
                    ),
                    definition("recipe").is_distinct_from(r("recipe")),
                ),
                "operation event completion changes exact current request/implementation",
            ),
            Assign("output", completion["outputs"][0]),
            If(r("operation_id") == AUTHORIZATION_OPERATION, authorization, derivation),
            _reject(
                or_(
                    _text(output, "role").is_distinct_from(output_role),
                    _text(output, "member_id").is_not(None),
                    cast(_text(output, "position"), Integer()).is_distinct_from(0),
                    cast(_text(output, "multiplicity"), Integer()).is_distinct_from(1),
                    _at(output, "product", "members").is_distinct_from(_json([])),
                    ~exact_kind,
                ),
                "event output changes exact finite whole nominal contract",
            ),
        ),
        (
            definition.local(),
            Local("output", pg_type("jsonb")),
            Local("body", pg_type("jsonb")),
            *(
                Local(name, pg_type("text"))
                for name in ("expected_factory", "output_role", "output_kind")
            ),
            basis.local(),
            producing.local(),
            fit_request.local(),
            fit_intent.local(),
            Local("selected", pg_type("jsonb")),
            Local("expected", pg_type("jsonb")),
        ),
    )


def _dependencies(p):
    r, producer, intent, boundary = (
        p.row(name, table)
        for name, table in (
            ("r", "ops.data_request"),
            ("producing", "ops.data_derivation"),
            ("intent", "ops.data_completion_intent"),
            ("boundary", "ops.data_demand_read"),
        )
    )
    episode, selected = core_variable("episode", Text()), core_variable("selected", JSONB())
    question = func.ops.ddo_record_grade_input(r(), "question", type_=JSONB())["body"]
    p.add(
        "ddo_operation_event_dependencies_valid",
        (("episode", "text"),),
        (
            CatchDependencyInvalidity(
                (
                    producer.lookup(producer.table.c.id == episode),
                    r.lookup(r.table.c.id == producer("request_id")),
                    If(r("operation_id").not_in(_OPERATIONS), (Return(literal(True)),)),
                    If(producer("outcome").is_distinct_from("success"), (Return(literal(False)),)),
                    intent.lookup(
                        intent.table.c.id == producer("intent_id"),
                        intent.table.c.request_id == producer("request_id"),
                        intent.table.c.generation == producer("generation"),
                    ),
                    Assign("r", func.ops.ddo_require_episode_correspondence(producer(), intent())),
                    If(
                        r("operation_id") == "operation_event.frame",
                        (
                            ForQuery(
                                ("selected",),
                                _cut_pair(question),
                                (
                                    Perform(
                                        func.ops.ddo_record_grade_require_cut(
                                            r("project_id"),
                                            _text(selected, "cut_canonical_json"),
                                            _text(selected, "cut_id"),
                                        )
                                    ),
                                ),
                            ),
                        ),
                        (
                            If(
                                r("operation_id") == "operation_event.fit",
                                (
                                    Assign(
                                        "selected",
                                        func.ops.ddo_record_grade_input(
                                            r(), "specification", type_=JSONB()
                                        )["body"]["frame"]["selection"],
                                    ),
                                    Perform(
                                        func.ops.ddo_record_fit_cut_scopes(
                                            r("project_id"), selected
                                        )
                                    ),
                                    boundary.lookup(
                                        boundary.table.c.id == _text(selected, "read_id"),
                                        boundary.table.c.demand_id == _text(selected, "demand_id"),
                                    ),
                                    Perform(
                                        func.ops.ddo_require_read_current(
                                            boundary(), r("project_id"), True
                                        )
                                    ),
                                ),
                            ),
                        ),
                    ),
                    Return(literal(True)),
                ),
                (Return(literal(False)),),
            ),
        ),
        (
            r.local(),
            producer.local(),
            intent.local(),
            Local("selected", pg_type("jsonb")),
            boundary.local(),
        ),
        returns="bool",
    )
