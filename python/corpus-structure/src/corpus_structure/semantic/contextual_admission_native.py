"""Current contextual completion correspondence at the common native fence.

This helper adds no model, scoring implementation, receipt or validity owner.
The caller installs its hook alongside the authenticated CPU-basis helpers.
Retrieval requires a separately authenticated native scoring input; it is not
silently treated as a CPU result by the declared encoder/selection guard.
"""

from __future__ import annotations

import json

from sqlalchemy import Integer, Text, and_, case, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    Continue,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration, ProgramValidity
from .validity_programs import input_role, operation_field, selected_family


def _json(value):
    return cast(literal(json.dumps(value, separators=(",", ":"))), JSONB())


def _field(value, *path):
    for name in path:
        value = func.data.ddo_field(value, name, type_=JSONB())
    return value


def _text(value, *path):
    return _field(value, *path)[1].astext


def _plain(value):
    return func.data.ddo_json(value, type_=JSONB())


def _object(**fields):
    return func.jsonb_build_object(
        *(part for key, value in fields.items() for part in (key, value)), type_=JSONB()
    )


def _items(value, name="item"):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _value(name, type_=None):
    return core_variable(name, JSONB() if type_ is None else type_)


def _reject(condition, message):
    return If(condition, (Raise(message, "23514"),))


def _contextual_producer_allowed(input_roles, dependencies, role, producer):
    """Separate authenticated frozen input permission from local executable dependencies."""
    roles = _items(input_roles, "contextual_input_role")
    declared = roles.c.value
    frozen = (
        select(1)
        .select_from(roles)
        .where(
            declared["name"].astext == role,
            declared["direction"].astext == "input",
            declared["support"]["source"].astext == "frozen-source-set",
            func.nullif(declared["support"]["source_set"].astext, "").is_not(None),
        )
        .exists()
    )
    # Common binding admission authenticates the named set and its exact producer
    # proof. Retained inputs do not require reacquiring their producer's code.
    return or_(
        frozen,
        dependencies["required"].contains(func.jsonb_build_array(producer)),
        dependencies["potential"].contains(func.jsonb_build_array(producer)),
    )


class _ContextualPrograms:
    """Shared typed framing and captured row lookups for the contextual guards."""

    def __init__(self, metadata=None):
        if metadata is None:
            from .metadata import get_metadata

            metadata = get_metadata()
        self.model = metadata
        self.output = []

    def table(self, name):
        return self.model.tables[name]

    def row(self, name, relation, field=None):
        return core_variable(
            name, NullType() if field is None else self.table(relation).c[field].type, field
        )

    def local(self, name, kind="jsonb", initial=None):
        return Local(
            name, self.table(kind) if kind in self.model.tables else pg_type(kind), initial
        )

    def lookup(self, target, relation, *conditions):
        selected = self.table(relation)
        return SelectInto(
            select(core_relation_row(selected)).select_from(selected).where(*conditions),
            (target,),
            strict=True,
        )

    def role(self, basis, role, target):
        rows = _items(_field(basis, "roles")[1], "selected_role")
        return SelectInto(
            select(rows.c.value).where(_text(rows.c.value, "role") == role), (target,), strict=True
        )

    def bind(self, original="original", request="r", completion="completion"):
        return Assign(
            (original, "binding"),
            self.row(request, "ops.data_request", "binding").op("||")(
                _object(inputs=_value(completion)["inputs"], support=_value(completion)["support"])
            ),
        )

    def restore(self, request, episode, intent):
        payload = self.row(intent, "ops.data_completion_intent", "payload")
        return (
            *(
                Assign((request, name), self.row(episode, "ops.data_derivation", name))
                for name in ("release_id", "runtime_id", "recipe", "generation")
            ),
            Assign(
                (request, "binding"),
                self.row(request, "ops.data_request", "binding").op("||")(
                    _object(inputs=payload["inputs"], support=payload["support"])
                ),
            ),
        )

    def add(
        self,
        name,
        parameters,
        statements,
        locals_=(),
        *,
        returns="void",
        immutable=False,
        strict=False,
        definer=True,
        validity=(),
    ):
        arguments = tuple(Parameter(key, pg_type(*kind.split("."))) for key, kind in parameters)
        self.output.append(
            ProgramDeclaration(
                NativeRoutine(
                    "ops",
                    name,
                    parameters=arguments,
                    returns=pg_type(*returns.split(".")),
                    body=Block(tuple(statements), tuple(locals_)),
                    volatility="immutable" if immutable else "stable",
                    strict=strict,
                    security_definer=definer,
                    search_path=("pg_catalog", "pg_temp"),
                ),
                source="data-operations:forward",
                owner=role_name("publisher"),
                access=INTERNAL_PROGRAM,
                validity=validity,
            )
        )


def contextual_admission_native_programs(*, target_metadata=None) -> tuple[ProgramDeclaration, ...]:
    p = _ContextualPrograms(target_metadata)
    from .contextual_encoder_batch import MEMBER_FAILURE_CODES, MEMBER_FAILURE_VERSION

    requests, episodes, intents, outputs, receipts, definitions = (
        p.table(name)
        for name in (
            "ops.data_request",
            "ops.data_derivation",
            "ops.data_completion_intent",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
            "sem.data_operation_definition",
        )
    )
    op = p.row("r", "ops.data_request", "operation_id")
    request = p.row("r", "ops.data_request")
    completion = _value("completion")
    contract = p.row("operation", "sem.data_operation_definition", "support_contract")
    release = p.row("r", "ops.data_request", "release_id")
    lowered_contract = operation_field(p.model, release, op, "support_contract")
    batch = lowered_contract["capabilities"]["forms"] == _json(["batch"])

    def has_role(name):
        return input_role(p.model, release, op, name)

    score_operation = has_role("policy") & ~has_role("scores")
    scoring_operation = has_role("policy") & has_role("vectors")
    p.add(
        "ddo_require_contextual_producer",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(
                ~selected_family(
                    p.model, p.row("r", "ops.data_request", "release_id"), op, "contextual"
                ),
                (Return(),),
            ),
            p.lookup(
                "operation",
                "sem.data_operation_definition",
                definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
                definitions.c.operation_id == op,
            ),
            _reject(
                or_(
                    func.nullif(
                        contract["capabilities"]["prepared_factory"]["entrypoint"].astext, ""
                    ).is_(None),
                    contract["capabilities"]["prepared_factory"]["source_digest"]
                    .astext.op("~")("^[0-9a-f]{64}$")
                    .is_not(True),
                    p.row("operation", "sem.data_operation_definition", "implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    p.row("operation", "sem.data_operation_definition", "profile").not_in(
                        ("derivation", "discovery")
                    ),
                    p.row("operation", "sem.data_operation_definition", "recipe").is_distinct_from(
                        p.row("r", "ops.data_request", "recipe")
                    ),
                    ~contract["capabilities"]["forms"].in_((_json(["batch"]), _json(["scalar"]))),
                    contract["capabilities"]["preparation"].astext.is_distinct_from("resource"),
                    contract["effects"].is_distinct_from(_json([])),
                    func.jsonb_array_length(
                        func.coalesce(completion["execution_evidence"]["cpu_receipts"], _json([]))
                    )
                    != func.coalesce(
                        cast(contract["capabilities"]["cpu_receipts"].astext, Integer()), -1
                    ),
                    completion["implementation_revision"].astext.is_distinct_from(
                        p.row(
                            "operation", "sem.data_operation_definition", "implementation_revision"
                        )
                    ),
                ),
                "contextual completion lacks its actual admitted captured producer",
            ),
        ),
        (p.local("operation", "sem.data_operation_definition"),),
    )
    basis, item, result = (_value(name) for name in ("basis", "item", "result"))
    role = _value("role_name", Text())
    support = _items(_plain(_field(item, "support")), "reference")
    producer = episodes.join(outputs, outputs.c.derivation_id == episodes.c.id).join(
        receipts,
        and_(
            receipts.c.derivation_id == episodes.c.id, receipts.c.intent_id == episodes.c.intent_id
        ),
    )
    rows = _items(_field(basis, "roles")[1], "role_row")
    producer_basis, vector_query, query_context = (
        _value(name) for name in ("producer_basis", "vector_query", "query_context")
    )
    vector_support = _items(_plain(_field(vector_query, "support")), "reference")
    role_keys = (
        func.jsonb_object_keys(result)
        .table_valued(column("key", Text()))
        .render_derived(name="keys")
    )
    expected = case(
        (
            score_operation,
            array(["inventory", "policy", "query", "vectors"]),
        ),
        (
            has_role("witnesses"),
            array(["inventory", "policy", "query", "scores", "vectors", "witnesses"]),
        ),
        else_=array(["inventory", "policy", "query", "scores", "vectors"]),
    )
    p.add(
        "ddo_contextual_scoring_inputs",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            p.bind(),
            Assign("basis", func.ops.ddo_cpu_input_basis(p.row("original", "ops.data_request"))),
            ForQuery(
                ("item",),
                select(rows.c.value),
                (
                    Assign("role_name", _text(item, "role")),
                    _reject(
                        or_(
                            result.has_key(role),
                            role.not_in(
                                ("query", "inventory", "vectors", "policy", "scores", "witnesses")
                            ),
                            _field(item, "member_id").is_distinct_from(_json(["null"])),
                            _field(item, "multiplicity").is_distinct_from(_json(["integer", "1"])),
                        ),
                        "native contextual scoring requires exact distinct whole role products",
                    ),
                    Assign(
                        "result",
                        result.op("||")(
                            func.jsonb_build_object(role, _plain(_field(item, "body")))
                        ),
                    ),
                    If(role == "policy", (Continue(),)),
                    SelectInto(
                        select(core_relation_row(episodes))
                        .select_from(producer)
                        .where(
                            outputs.c.product_id == _text(item, "product_id"),
                            outputs.c.member_id.is_(None),
                            outputs.c.multiplicity == 1,
                            select(1)
                            .select_from(support)
                            .where(
                                support.c.value["kind"].astext == "computation",
                                support.c.value["derivation_id"].astext == episodes.c.id,
                            )
                            .exists(),
                        ),
                        ("episode",),
                        strict=True,
                    ),
                    p.lookup(
                        "producing",
                        "ops.data_request",
                        requests.c.id == p.row("episode", "ops.data_derivation", "request_id"),
                        requests.c.project_id == p.row("r", "ops.data_request", "project_id"),
                    ),
                    _reject(
                        or_(
                            ~_contextual_producer_allowed(
                                operation_field(p.model, release, op, "input_roles"),
                                operation_field(p.model, release, op, "dependencies"),
                                role,
                                p.row("producing", "ops.data_request", "operation_id"),
                            ),
                            ~func.ops.ddo_contextual_dependencies_valid(
                                p.row("episode", "ops.data_derivation", "id")
                            ),
                        ),
                        "native contextual input lacks its actual declared producer/common receipt",
                    ),
                    *(
                        If(
                            role == name,
                            (
                                Assign(
                                    f"{prefix}_episode", p.row("episode", "ops.data_derivation")
                                ),
                                Assign(f"{prefix}_request", p.row("producing", "ops.data_request")),
                            ),
                        )
                        for name, prefix in (
                            ("witnesses", "witness"),
                            ("scores", "scores"),
                            ("vectors", "vectors"),
                        )
                    ),
                    If(
                        role == "query",
                        (
                            Assign("query_episode", p.row("episode", "ops.data_derivation")),
                            Assign("query_context", _field(item, "context")),
                        ),
                    ),
                ),
            ),
            _reject(
                select(func.array_agg(aggregate_order_by(role_keys.c.key, role_keys.c.key)))
                .scalar_subquery()
                .is_distinct_from(expected),
                "native contextual input population is incomplete or foreign",
            ),
            _reject(
                or_(
                    query_context.is_distinct_from(_field(basis, "context")),
                    result["query"]["source_pin"]["project_id"].astext.is_distinct_from(
                        p.row("r", "ops.data_request", "project_id")
                    ),
                    result["query"]["source_pin"]["original_source"].astext.is_distinct_from(
                        p.row("r", "ops.data_request", "original_source")
                    ),
                ),
                "native contextual query differs from selected product/original context",
            ),
            p.lookup(
                "intent",
                "ops.data_completion_intent",
                intents.c.id == p.row("vectors_episode", "ops.data_derivation", "intent_id"),
            ),
            *p.restore("vectors_request", "vectors_episode", "intent"),
            Assign(
                "producer_basis",
                func.ops.ddo_cpu_input_basis(p.row("vectors_request", "ops.data_request")),
            ),
            _reject(
                func.ops.ddo_rich_role_population(basis, "inventory").is_distinct_from(
                    func.ops.ddo_rich_role_population(producer_basis, "inventory")
                ),
                "native scoring inventory differs from actual selected vector assembly",
            ),
            p.role(producer_basis, "query", "vector_query"),
            _reject(
                ~select(1)
                .select_from(
                    vector_support.join(
                        outputs,
                        outputs.c.derivation_id == vector_support.c.value["derivation_id"].astext,
                    )
                )
                .where(
                    vector_support.c.value["kind"].astext == "computation",
                    outputs.c.derivation_id == p.row("query_episode", "ops.data_derivation", "id"),
                    outputs.c.product_id == _text(vector_query, "product_id"),
                    outputs.c.member_id.is_(None),
                    outputs.c.role == "vector",
                    outputs.c.multiplicity == 1,
                )
                .exists(),
                "native scoring query and assembly vector have different original encoder episodes",
            ),
            If(
                p.row("scores_episode", "ops.data_derivation", "id").is_not(None),
                (
                    p.lookup(
                        "intent",
                        "ops.data_completion_intent",
                        intents.c.id == p.row("scores_episode", "ops.data_derivation", "intent_id"),
                    ),
                    *p.restore("scores_request", "scores_episode", "intent"),
                    Assign(
                        "producer_basis",
                        func.ops.ddo_cpu_input_basis(p.row("scores_request", "ops.data_request")),
                    ),
                    *(
                        _reject(
                            func.ops.ddo_rich_role_population(basis, name).is_distinct_from(
                                func.ops.ddo_rich_role_population(producer_basis, name)
                            ),
                            "native scores belong to another exact selected input/support population",
                        )
                        for name in ("query", "inventory", "vectors")
                    ),
                    # Both uses admit the authored policy in their own demand.
                    # Compare the policy meaning authenticated by exact binding.
                    _reject(
                        _field(
                            p.row("original", "ops.data_request", "binding")["request_inputs"],
                            "policy",
                        ).is_distinct_from(
                            _field(
                                p.row("scores_request", "ops.data_request", "binding")[
                                    "request_inputs"
                                ],
                                "policy",
                            )
                        ),
                        "native scores differ from the selected authored policy",
                    ),
                    p.lookup(
                        "definition",
                        "sem.data_operation_definition",
                        definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
                        definitions.c.operation_id == op,
                    ),
                    p.lookup(
                        "score_definition",
                        "sem.data_operation_definition",
                        definitions.c.release_id
                        == p.row("scores_episode", "ops.data_derivation", "release_id"),
                        definitions.c.operation_id
                        == p.row("scores_request", "ops.data_request", "operation_id"),
                    ),
                    _reject(
                        p.row("definition", "sem.data_operation_definition", "support_contract")[
                            "numerical_policy"
                        ].is_distinct_from(
                            p.row(
                                "score_definition",
                                "sem.data_operation_definition",
                                "support_contract",
                            )["numerical_policy"]
                        ),
                        "native scores and CPU reduction have different captured numerical policies",
                    ),
                ),
            ),
            If(
                p.row("witness_episode", "ops.data_derivation", "id").is_not(None),
                (
                    p.lookup(
                        "intent",
                        "ops.data_completion_intent",
                        intents.c.id
                        == p.row("witness_episode", "ops.data_derivation", "intent_id"),
                    ),
                    *p.restore("witness_request", "witness_episode", "intent"),
                    Assign(
                        "producer_basis",
                        func.ops.ddo_cpu_input_basis(p.row("witness_request", "ops.data_request")),
                    ),
                    *(
                        _reject(
                            func.ops.ddo_rich_role_population(basis, name).is_distinct_from(
                                func.ops.ddo_rich_role_population(producer_basis, name)
                            ),
                            "contextual witness binding belongs to another exact query/inventory support population",
                        )
                        for name in ("query", "inventory")
                    ),
                ),
            ),
            Return(result),
        ),
        (
            p.local("original", "ops.data_request", request),
            *(
                p.local(name)
                for name in ("basis", "item", "producer_basis", "vector_query", "query_context")
            ),
            p.local("result", initial=_json({})),
            p.local("role_name", "text"),
            p.local("episode", "ops.data_derivation"),
            p.local("producing", "ops.data_request"),
            p.local("intent", "ops.data_completion_intent"),
            *(
                p.local(f"{name}_episode", "ops.data_derivation")
                for name in ("scores", "witness", "vectors", "query")
            ),
            *(
                p.local(f"{name}_request", "ops.data_request")
                for name in ("scores", "witness", "vectors")
            ),
            p.local("definition", "sem.data_operation_definition"),
            p.local("score_definition", "sem.data_operation_definition"),
        ),
        returns="jsonb",
    )
    actual, expected_value, values = (_value(name) for name in ("actual", "expected", "values_"))
    failure, code, detail = (_value(name) for name in ("failure_", "code_", "detail_"))
    output_rows = _items(completion["outputs"], "output_row")
    p.add(
        "ddo_require_contextual_completion",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(
                ~selected_family(
                    p.model, p.row("r", "ops.data_request", "release_id"), op, "contextual"
                ),
                (Return(),),
            ),
            Perform(func.ops.ddo_require_contextual_producer(request, completion)),
            If(
                scoring_operation,
                (Assign("values_", func.ops.ddo_contextual_scoring_inputs(request, completion)),),
                (
                    If(
                        has_role("hypotheses") & has_role("cues"),
                        (Perform(func.ops.ddo_contextual_witness_inputs(request, completion)),),
                        (
                            If(
                                has_role("report"),
                                (
                                    p.bind(),
                                    Assign(
                                        "source_basis",
                                        func.ops.ddo_cpu_input_basis(
                                            p.row("original", "ops.data_request")
                                        ),
                                    ),
                                    p.role(_value("source_basis"), "report", "report_row"),
                                    Perform(
                                        func.ops.ddo_definition_component_basis(
                                            _value("report_row")
                                        )
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            If(
                score_operation,
                (
                    p.lookup(
                        "definition",
                        "sem.data_operation_definition",
                        definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
                        definitions.c.operation_id == op,
                    ),
                    Assign(
                        "actual",
                        func.ops.ddo_contextual_score_meaning(
                            func.ops.ddo_contextual_native_scores(
                                values["query"],
                                values["inventory"],
                                values["vectors"],
                                values["policy"],
                                p.row(
                                    "definition",
                                    "sem.data_operation_definition",
                                    "support_contract",
                                )["numerical_policy"]["body"]["json"],
                            )
                        ),
                    ),
                ),
                (Assign("actual", func.ops.ddo_cpu_reply_output(request, completion)),),
            ),
            If(
                batch,
                (
                    Assign("failure_", _field(actual, "encoder_member_failure")),
                    If(
                        failure.is_not(None),
                        (
                            Assign("code_", _field(failure, "code")),
                            Assign("detail_", _field(failure, "detail")),
                            _reject(
                                or_(
                                    actual[0].astext.is_distinct_from("mapping"),
                                    func.jsonb_array_length(actual[1]) != 1,
                                    failure[0].astext.is_distinct_from("mapping"),
                                    func.jsonb_array_length(failure[1]) != 3,
                                    _field(failure, "version").is_distinct_from(
                                        _json(["string", MEMBER_FAILURE_VERSION])
                                    ),
                                    code[0].astext.is_distinct_from("string"),
                                    func.coalesce(code[1].astext, "").not_in(
                                        sorted(MEMBER_FAILURE_CODES)
                                    ),
                                    detail[0].astext.is_distinct_from("string"),
                                    func.length(detail[1].astext) > 1024,
                                    completion["outcome"].astext.is_distinct_from("failed"),
                                    completion["outputs"].is_distinct_from(_json([])),
                                ),
                                "encoder failure completion differs from its authenticated member slot",
                            ),
                            Return(),
                        ),
                        (
                            _reject(
                                completion["outcome"].astext.is_distinct_from("success"),
                                "encoder failure lacks its authenticated native member failure",
                            ),
                        ),
                    ),
                ),
            ),
            ForQuery(
                ("item",),
                select(output_rows.c.value),
                (
                    Assign(
                        "expected",
                        case(
                            (
                                lowered_contract["result_fields"] != _json({}),
                                _field(actual, item["role"].astext),
                            ),
                            else_=actual,
                        ),
                    ),
                    _reject(
                        expected_value.is_distinct_from(
                            func.data.ddo_normalize(item["product"]["body"])
                        ),
                        "contextual publication differs from its actual processed CPU reply",
                    ),
                ),
            ),
        ),
        (
            *(
                p.local(name)
                for name in (
                    "actual",
                    "expected",
                    "item",
                    "values_",
                    "failure_",
                    "code_",
                    "detail_",
                    "source_basis",
                    "report_row",
                )
            ),
            p.local("definition", "sem.data_operation_definition"),
            p.local("original", "ops.data_request", request),
        ),
        validity=(ProgramValidity("contextual", "completion_guard"),),
    )
    evidence_outputs = _items(
        p.row("intent", "ops.data_completion_intent", "payload")["outputs"], "output_row"
    )
    p.add(
        "ddo_contextual_dependencies_valid",
        (("episode_id", "text"),),
        (
            CatchDependencyInvalidity(
                (
                    p.lookup(
                        "episode",
                        "ops.data_derivation",
                        episodes.c.id == _value("episode_id", Text()),
                    ),
                    p.lookup(
                        "r",
                        "ops.data_request",
                        requests.c.id == p.row("episode", "ops.data_derivation", "request_id"),
                    ),
                    If(
                        ~selected_family(
                            p.model, p.row("r", "ops.data_request", "release_id"), op, "contextual"
                        ),
                        (Return(literal(True)),),
                    ),
                    If(
                        p.row("episode", "ops.data_derivation", "outcome") != "success",
                        (Return(literal(False)),),
                    ),
                    p.lookup(
                        "intent",
                        "ops.data_completion_intent",
                        intents.c.id == p.row("episode", "ops.data_derivation", "intent_id"),
                        intents.c.request_id
                        == p.row("episode", "ops.data_derivation", "request_id"),
                        intents.c.generation
                        == p.row("episode", "ops.data_derivation", "generation"),
                    ),
                    Assign(
                        "r",
                        func.ops.ddo_require_episode_contextual_correspondence(
                            p.row("episode", "ops.data_derivation"),
                            p.row("intent", "ops.data_completion_intent"),
                        ),
                    ),
                    If(
                        and_(
                            score_operation,
                            ~select(1)
                            .select_from(evidence_outputs)
                            .where(
                                evidence_outputs.c.value["product"]["body"].is_not(None),
                                _field(
                                    func.data.ddo_normalize(
                                        evidence_outputs.c.value["product"]["body"], type_=JSONB()
                                    ),
                                    "linguistic_observation",
                                ).is_not_distinct_from(
                                    func.data.record_json_meaning(
                                        func.data.record_json_source(
                                            func.ops.ddo_contextual_linguistic_context()
                                        )
                                    )
                                ),
                            )
                            .exists(),
                        ),
                        (Return(literal(False)),),
                    ),
                    Return(literal(True)),
                ),
                (Return(literal(False)),),
            ),
        ),
        (
            p.local("r", "ops.data_request"),
            p.local("episode", "ops.data_derivation"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="boolean",
        validity=(ProgramValidity("contextual", "validator"),),
    )
    return tuple(p.output)


def contextual_admission_native_sql(*, target_metadata=None) -> str:
    """Render the current captured private declarations."""
    return native_sql_script(
        statement
        for declaration in contextual_admission_native_programs(target_metadata=target_metadata)
        for statement in (
            declaration.routine.render(),
            native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
        )
    )
