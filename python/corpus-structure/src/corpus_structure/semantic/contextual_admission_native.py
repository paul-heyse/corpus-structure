"""Current contextual completion correspondence at the common native fence.

This helper adds no model, scoring implementation, receipt or validity owner.
The caller installs its hook alongside the authenticated CPU-basis helpers.
Retrieval requires a separately authenticated native scoring input; it is not
silently treated as a CPU result by the declared encoder/selection guard.
"""

from __future__ import annotations

import json

from sqlalchemy import Text, and_, case, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by, array
from sqlalchemy.types import NullType

from .native_objects import NativeIdentity, native_privilege_sql, native_sql_script
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    Continue,
    ForQuery,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_relation_row,
    core_variable,
    function,
    pg_type,
)


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
    ):
        arguments = tuple(Parameter(key, pg_type(*kind.split("."))) for key, kind in parameters)
        self.output.extend(
            (
                function(
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
                native_privilege_sql(
                    NativeIdentity("function", "ops", name, tuple(kind for _, kind in parameters)),
                    "PUBLIC",
                    grant=False,
                ),
            )
        )

    def script(self):
        return native_sql_script(self.output)


def contextual_admission_native_sql(*, target_metadata=None) -> str:
    p = _ContextualPrograms(target_metadata)
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
    factories = {
        "retrieve.contextual_query/declared": "corpus_structure.methods.contextual_encoding.ContextualEncodingOperation.acquire_port",
        "retrieve.contextual_query/selected-context": "corpus_structure.methods.contextual_encoding.SelectedContextEncodingOperation.acquire_port",
        "retrieve.contextual_target_vector/declared": "corpus_structure.methods.contextual_encoding.ContextualTargetEncodingOperation.acquire_port",
        "retrieve.contextual_vectors/selection": "corpus_structure.methods.contextual_targets.ContextualVectorSelectionOperation.acquire_port",
        "retrieve.contextual_targets/curated": "corpus_structure.methods.contextual_targets.CuratedContextualTargetsOperation.acquire_port",
        "retrieve.contextual_targets/components": "corpus_structure.methods.contextual_targets.SourceContextualTargetsOperation.acquire_port",
        "retrieve.contextual_target/declared": "corpus_structure.methods.contextual_targets.ContextualTargetOperation.acquire_port",
        "retrieve.contextual_inventory/declared": "corpus_structure.methods.contextual_declared.ContextualInventoryOperation.acquire_port",
        "retrieve.contextual_scores/declared": "corpus_structure.methods.contextual_scoring.ContextualScoringOperation.acquire_port",
        "retrieve.contextual/declared": "corpus_structure.methods.contextual_declared.ContextualRetrievalOperation.acquire_port",
        "retrieve.contextual_witnesses/declared": "corpus_structure.methods.contextual_witnesses.ContextualWitnessOperation.acquire_port",
        "retrieve.contextual/with-witnesses": "corpus_structure.methods.contextual_witnesses.ContextualWitnessedRetrievalOperation.acquire_port",
    }
    op = p.row("r", "ops.data_request", "operation_id")
    request = p.row("r", "ops.data_request")
    completion = _value("completion")
    contract = p.row("operation", "sem.data_operation_definition", "support_contract")
    batch = (
        "retrieve.contextual_query/declared",
        "retrieve.contextual_query/selected-context",
        "retrieve.contextual_target_vector/declared",
    )
    p.add(
        "ddo_require_contextual_producer",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(op.not_in(tuple(factories)), (Return(),)),
            p.lookup(
                "operation",
                "sem.data_operation_definition",
                definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
                definitions.c.operation_id == op,
            ),
            Assign("factory", case(factories, value=op)),
            _reject(
                or_(
                    contract["capabilities"]["prepared_factory"][
                        "entrypoint"
                    ].astext.is_distinct_from(_value("factory", Text())),
                    contract["capabilities"]["prepared_factory"]["source_digest"]
                    .astext.op("~")("^[0-9a-f]{64}$")
                    .is_not(True),
                    p.row("operation", "sem.data_operation_definition", "implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    p.row("operation", "sem.data_operation_definition", "profile").is_distinct_from(
                        case(
                            (
                                op.in_(
                                    (
                                        "retrieve.contextual_targets/curated",
                                        "retrieve.contextual_targets/components",
                                    )
                                ),
                                "discovery",
                            ),
                            else_="derivation",
                        )
                    ),
                    p.row("operation", "sem.data_operation_definition", "recipe").is_distinct_from(
                        p.row("r", "ops.data_request", "recipe")
                    ),
                    contract["capabilities"]["forms"].is_distinct_from(
                        case((op.in_(batch), _json(["batch"])), else_=_json(["scalar"]))
                    ),
                    contract["capabilities"]["preparation"].astext.is_distinct_from("resource"),
                    contract["effects"].is_distinct_from(_json([])),
                    func.jsonb_array_length(
                        func.coalesce(completion["execution_evidence"]["cpu_receipts"], _json([]))
                    )
                    != case((op == "retrieve.contextual_scores/declared", 0), else_=1),
                    completion["implementation_revision"].astext.is_distinct_from(
                        p.row(
                            "operation", "sem.data_operation_definition", "implementation_revision"
                        )
                    ),
                ),
                "contextual completion lacks its actual admitted captured producer",
            ),
        ),
        (p.local("operation", "sem.data_operation_definition"), p.local("factory", "text")),
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
            op == "retrieve.contextual_scores/declared",
            array(["inventory", "policy", "query", "vectors"]),
        ),
        (
            op == "retrieve.contextual/with-witnesses",
            array(["inventory", "policy", "query", "scores", "vectors", "witnesses"]),
        ),
        else_=array(["inventory", "policy", "query", "scores", "vectors"]),
    )
    role_operations = {
        "query": (
            "retrieve.contextual_query/declared",
            "retrieve.contextual_query/selected-context",
        ),
        "inventory": ("retrieve.contextual_inventory/declared",),
        "vectors": ("retrieve.contextual_vectors/selection",),
        "scores": ("retrieve.contextual_scores/declared",),
        "witnesses": ("retrieve.contextual_witnesses/declared",),
    }
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
                            *(
                                and_(
                                    role == name,
                                    p.row("producing", "ops.data_request", "operation_id").not_in(
                                        allowed
                                    ),
                                )
                                for name, allowed in role_operations.items()
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
                        for name in ("query", "inventory", "vectors", "policy")
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
            If(op.not_in(tuple(factories)), (Return(),)),
            Perform(func.ops.ddo_require_contextual_producer(request, completion)),
            If(
                op.in_(
                    (
                        "retrieve.contextual_scores/declared",
                        "retrieve.contextual/declared",
                        "retrieve.contextual/with-witnesses",
                    )
                ),
                (Assign("values_", func.ops.ddo_contextual_scoring_inputs(request, completion)),),
                (
                    If(
                        op == "retrieve.contextual_witnesses/declared",
                        (Perform(func.ops.ddo_contextual_witness_inputs(request, completion)),),
                        (
                            If(
                                op == "retrieve.contextual_targets/components",
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
                op == "retrieve.contextual_scores/declared",
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
                op.in_(batch),
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
                                        _json(["string", "contextual-encoder-member-failure-1"])
                                    ),
                                    code[0].astext.is_distinct_from("string"),
                                    func.coalesce(code[1].astext, "").not_in(
                                        (
                                            "source-coordinate-mismatch",
                                            "selected-context-unavailable",
                                            "token-core-limit",
                                            "invalid-vector",
                                        )
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
                            (op.in_(batch[:2]), _field(actual, item["role"].astext)), else_=actual
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
                    If(op.not_in(tuple(factories)), (Return(literal(True)),)),
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
                        func.ops.ddo_require_episode_correspondence(
                            p.row("episode", "ops.data_derivation"),
                            p.row("intent", "ops.data_completion_intent"),
                        ),
                    ),
                    If(
                        and_(
                            op == "retrieve.contextual_scores/declared",
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
    )
    return p.script()
