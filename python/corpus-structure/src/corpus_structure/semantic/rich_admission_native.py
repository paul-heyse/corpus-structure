"""Private rich-admission correspondence at the existing native completion fence.

Policy numerics and graph lowering belong to their captured CPU owners. Native
admission authenticates those owners, their exact declared inputs, and the actual
child reply rather than interpreting an ungrounded accepted flag.
"""

from __future__ import annotations

import json

from sqlalchemy import Boolean, Integer, Text, and_, cast, column, func, literal, or_, select
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


class _RichPrograms:
    """Resolve rich native authority queries against the captured relation model."""

    def __init__(self, metadata):
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

    def add(
        self,
        name,
        parameters,
        body,
        locals_=(),
        *,
        returns="void",
        sql=False,
        immutable=False,
        strict=False,
        definer=True,
        setof=False,
        validity=(),
    ):
        arguments = tuple(Parameter(key, pg_type(*kind.split("."))) for key, kind in parameters)
        result_type = pg_type(*returns.split("."))
        result_type.setof = setof
        self.output.append(
            ProgramDeclaration(
                NativeRoutine(
                    "ops",
                    name,
                    parameters=arguments,
                    returns=result_type,
                    body=body if sql else Block(tuple(body), tuple(locals_)),
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


def _rich_input_programs(p):
    support = _value("support")
    refs = _items(support, "support_item")
    distinct = (
        select(
            (func.jsonb_strip_nulls(refs.c.value).op("-")("admission_use_id")).label("reference")
        )
        .distinct()
        .subquery("references_")
    )
    p.add(
        "ddo_rich_support_population",
        (("support", "jsonb"),),
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        distinct.c.reference,
                        func.convert_to(func.data.canonical_json(distinct.c.reference), "UTF8"),
                    )
                ),
                _json([]),
            )
        ),
        returns="jsonb",
        sql=True,
        immutable=True,
        strict=True,
        definer=False,
    )
    basis = _value("basis")
    roles = _items(_field(basis, "roles")[1], "role_meaning")
    pairs = _items(roles.c.value[1], "pair")
    header = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(pairs.c.value, pairs.c.value[0].astext.collate("C"))
                ),
                _json([]),
            )
        )
        .select_from(pairs)
        .where(pairs.c.value[0].astext.not_in(("body", "context")))
        .correlate(roles)
        .scalar_subquery()
    )
    p.add(
        "ddo_rich_role_headers",
        (("basis", "jsonb"),),
        select(_plain(func.jsonb_build_array("mapping", header))).select_from(roles),
        returns="jsonb",
        sql=True,
        immutable=True,
        strict=True,
        definer=False,
        setof=True,
    )
    headers = (
        func.ops.ddo_rich_role_headers(basis)
        .table_valued(column("value", JSONB()))
        .render_derived(name="row_value")
    )
    population = (
        select(
            func.jsonb_build_object(
                "product_id",
                headers.c.value["product_id"],
                "member_id",
                headers.c.value["member_id"],
                "multiplicity",
                headers.c.value["multiplicity"],
                "support",
                func.ops.ddo_rich_support_population(headers.c.value["support"]),
            ).label("item")
        )
        .where(headers.c.value["role"].astext == _value("role_name", Text()))
        .subquery("population")
    )
    p.add(
        "ddo_rich_role_population",
        (("basis", "jsonb"), ("role_name", "text")),
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        population.c.item,
                        func.convert_to(func.data.canonical_json(population.c.item), "UTF8"),
                    )
                ),
                _json([]),
            )
        ),
        returns="jsonb",
        sql=True,
        immutable=True,
        strict=True,
        definer=False,
    )
    products, members = p.table("kb.data_product"), p.table("kb.data_product_member")
    selected, bound = _value("selected"), _value("bound")
    bound_roles = _items(_field(basis, "roles")[1], "bound_role")
    p.add(
        "ddo_rich_selected_value",
        (("project", "text"), ("basis", "jsonb"), ("role_name", "text"), ("selected", "jsonb")),
        (
            SelectInto(
                select(bound_roles.c.value).where(
                    _text(bound_roles.c.value, "role") == _value("role_name", Text()),
                    _text(bound_roles.c.value, "product_id") == selected["product_id"].astext,
                    _field(bound_roles.c.value, "member_id") == _json(["null"]),
                ),
                ("bound",),
                strict=True,
            ),
            _reject(
                _field(bound, "support").is_distinct_from(
                    func.data.ddo_normalize(
                        func.data.ddo_json_meaning(
                            func.jsonb_strip_nulls(selected["support_references"])
                        )
                    )
                ),
                "rich selection differs from actual whole-role support",
            ),
            p.lookup(
                "product",
                "kb.data_product",
                products.c.id == selected["product_id"].astext,
                products.c.project_id == _value("project", Text()),
            ),
            If(
                selected["member_id"].astext.is_(None),
                (
                    _reject(
                        p.row("product", "kb.data_product", "kind_contract").is_distinct_from(
                            selected["kind_contract"].astext
                        ),
                        "rich whole selection differs from its actual kind",
                    ),
                    Return(p.row("product", "kb.data_product", "canonical_body")),
                ),
            ),
            p.lookup(
                "member",
                "kb.data_product_member",
                members.c.product_id == p.row("product", "kb.data_product", "id"),
                members.c.member_id == selected["member_id"].astext,
            ),
            _reject(
                p.row("member", "kb.data_product_member", "kind_contract").is_distinct_from(
                    selected["kind_contract"].astext
                ),
                "rich nominal member differs from its actual whole-report kind",
            ),
            Return(p.row("member", "kb.data_product_member", "body")),
        ),
        (
            p.local("bound"),
            p.local("product", "kb.data_product"),
            p.local("member", "kb.data_product_member"),
        ),
        returns="jsonb",
    )
    episodes, outputs, receipts, requests, definitions, intents = (
        p.table(name)
        for name in (
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_publication_receipt",
            "ops.data_request",
            "sem.data_operation_definition",
            "ops.data_completion_intent",
        )
    )
    evidence = _items(selected["support_references"], "reference")
    contract, payload = (
        p.row("definition", "sem.data_operation_definition", "support_contract"),
        p.row("intent", "ops.data_completion_intent", "payload"),
    )
    from .producer_correspondence_native import producer_cpu_witness

    requirement = _value("requirement")
    required_effect = requirement["required_effect"].astext
    required_family = requirement["required_family"].astext
    consumer_roles = _items(definitions.c.input_roles, "consumer_role")
    admitted_families = p.row("definition", "sem.data_operation_definition", "validity_families")
    effect_granted = func.ops.ddo_privileged_effect_admitted(
        core_variable("definition", JSONB()), required_effect
    )
    p.add(
        "ddo_rich_producing_request",
        (
            ("consumer", "ops.data_request"),
            ("selected", "jsonb"),
            ("role", "text"),
        ),
        (
            SelectInto(
                select(consumer_roles.c.value["producer_requirement"])
                .select_from(definitions.join(consumer_roles, literal(True)))
                .where(
                    definitions.c.release_id == p.row("consumer", "ops.data_request", "release_id"),
                    definitions.c.operation_id
                    == p.row("consumer", "ops.data_request", "operation_id"),
                    consumer_roles.c.value["name"].astext == _value("role", Text()),
                ),
                ("requirement",),
                strict=True,
            ),
            _reject(
                or_(
                    requirement.is_(None),
                    required_family.is_(None),
                    required_family == "undetermined",
                    func.jsonb_typeof(requirement["requires_cpu"]).is_distinct_from("boolean"),
                ),
                "consumer role has unresolved producer requirements",
            ),
            SelectInto(
                select(core_relation_row(episodes))
                .select_from(
                    episodes.join(outputs, outputs.c.derivation_id == episodes.c.id).join(
                        receipts,
                        and_(
                            receipts.c.derivation_id == episodes.c.id,
                            receipts.c.intent_id == episodes.c.intent_id,
                        ),
                    )
                )
                .where(
                    outputs.c.product_id == selected["product_id"].astext,
                    outputs.c.member_id.is_(None),
                    or_(
                        requirement["output_role"].astext.is_(None),
                        outputs.c.role == requirement["output_role"].astext,
                    ),
                    outputs.c.multiplicity == 1,
                    episodes.c.outcome == "success",
                    select(1)
                    .select_from(evidence)
                    .where(
                        evidence.c.value["kind"].astext == "computation",
                        evidence.c.value["derivation_id"].astext == episodes.c.id,
                    )
                    .exists(),
                ),
                ("producer",),
                strict=True,
            ),
            p.lookup(
                "request",
                "ops.data_request",
                requests.c.id == p.row("producer", "ops.data_derivation", "request_id"),
                requests.c.project_id == p.row("consumer", "ops.data_request", "project_id"),
            ),
            p.lookup(
                "definition",
                "sem.data_operation_definition",
                definitions.c.release_id == p.row("request", "ops.data_request", "release_id"),
                definitions.c.operation_id == p.row("request", "ops.data_request", "operation_id"),
            ),
            p.lookup(
                "intent",
                "ops.data_completion_intent",
                intents.c.id == p.row("producer", "ops.data_derivation", "intent_id"),
            ),
            _reject(
                and_(
                    required_family != "none",
                    admitted_families.contains(array([required_family])).is_not(True),
                ),
                "rich selection producer lacks its required validity family",
            ),
            _reject(
                or_(
                    and_(
                        required_effect.is_not(None),
                        effect_granted.is_not(True),
                    ),
                    contract["capabilities"]["prepared_factory"]["source_digest"]
                    .astext.op("~")("^[0-9a-f]{64}$")
                    .is_not(True),
                    p.row("definition", "sem.data_operation_definition", "implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    payload["implementation_revision"].astext.is_distinct_from(
                        p.row(
                            "definition", "sem.data_operation_definition", "implementation_revision"
                        )
                    ),
                    p.row("producer", "ops.data_derivation", "recipe").is_distinct_from(
                        p.row("definition", "sem.data_operation_definition", "recipe")
                    ),
                    p.row("request", "ops.data_request", "recipe").is_distinct_from(
                        p.row("definition", "sem.data_operation_definition", "recipe")
                    ),
                    and_(
                        cast(requirement["requires_cpu"].astext, Boolean()),
                        producer_cpu_witness(
                            p.row("definition", "sem.data_operation_definition", "profile"),
                            contract["effects"],
                            payload,
                        ).is_not(True),
                    ),
                ),
                "rich selection lacks its actual admitted producer and CPU/common receipt",
            ),
            Return(p.row("request", "ops.data_request")),
        ),
        (
            p.local("requirement"),
            p.local("request", "ops.data_request"),
            p.local("producer", "ops.data_derivation"),
            p.local("definition", "sem.data_operation_definition"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="ops.data_request",
    )
    artifacts = p.table("sem.artifact")
    archive = _value("archive")
    kinds = _items(archive["kinds"], "kind")
    identities = _items(archive["identities"], "identity")
    p.add(
        "ddo_rich_family_contract",
        (("p_release", "text"), ("local_name", "text")),
        (
            SelectInto(
                select(cast(func.convert_from(artifacts.c.content, "UTF8"), JSONB())).where(
                    artifacts.c.release_id == _value("p_release", Text()),
                    artifacts.c.artifact_name == "data_operations.json",
                ),
                ("archive",),
                strict=True,
            ),
            SelectInto(
                select(identities.c.value["key"].astext)
                .select_from(
                    kinds.join(
                        identities,
                        identities.c.value["owner"].astext == kinds.c.value["semantic_id"].astext,
                    )
                )
                .where(
                    kinds.c.value["name"].astext == _value("local_name", Text()),
                    kinds.c.value["category"].astext == "class",
                    kinds.c.value["complete"] == _json(True),
                    identities.c.value["domain"].astext == "kind",
                ),
                ("result",),
                strict=True,
            ),
            Return(_value("result", Text())),
        ),
        (p.local("archive"), p.local("result", "text")),
        returns="text",
    )
    context = (
        func.ops.ddo_rich_role_headers(_value("consolidation_basis"))
        .table_valued(column("value", JSONB()))
        .render_derived(name="context_input")
    )
    consumed = _value("consumed")
    located = (
        func.ops.ddo_rich_role_headers(_value("located_basis"))
        .table_valued(column("value", JSONB()))
        .render_derived(name="located")
    )
    p.add(
        "ddo_rich_require_proposal_context",
        (("consolidation_basis", "jsonb"), ("located_basis", "jsonb")),
        (
            SelectInto(
                select(located.c.value).where(located.c.value["role"].astext == "packet"),
                ("consumed",),
                strict=True,
            ),
            _reject(
                or_(
                    consumed["member_id"].astext.is_not(None),
                    ~select(1)
                    .select_from(context)
                    .where(
                        context.c.value["role"].astext == "proposal_contexts",
                        context.c.value["product_id"].astext == consumed["product_id"].astext,
                        context.c.value["member_id"].astext.is_(None),
                        func.ops.ddo_rich_support_population(context.c.value["support"])
                        == func.ops.ddo_rich_support_population(consumed["support"]),
                    )
                    .exists(),
                ),
                "rich located proposal differs from actual consumed whole packet/context support",
            ),
        ),
        (p.local("consumed"),),
        immutable=True,
        strict=True,
        definer=False,
    )
    packet = _value("packet")
    normalized = func.data.ddo_normalize(packet, type_=JSONB())
    p.add(
        "ddo_rich_carried_reading",
        (("packet", "jsonb"), ("known_packets", "jsonb")),
        select(
            func.coalesce(
                and_(
                    _field(packet, "body", "member_type")
                    == _json(["string", "source-reading-assertion"]),
                    _value("known_packets")[func.ops.ddo_digest(normalized)] == normalized,
                ),
                False,
            )
        ),
        returns="boolean",
        sql=True,
        immutable=True,
        strict=True,
        definer=False,
    )


def _rich_producer_programs(p):
    definitions, kinds, requests, episodes, intents = (
        p.table(name)
        for name in (
            "sem.data_operation_definition",
            "sem.data_kind_contract",
            "ops.data_request",
            "ops.data_derivation",
            "ops.data_completion_intent",
        )
    )
    contract = p.row("definition", "sem.data_operation_definition", "support_contract")
    p.add(
        "ddo_rich_command_eligible",
        (("definition", "sem.data_operation_definition"),),
        select(
            and_(
                func.ops.ddo_privileged_effect_eligible(
                    core_variable("definition", JSONB()), "native-rich-knowledge-admission"
                ),
                p.row("definition", "sem.data_operation_definition", "profile") == "command",
                contract["capabilities"]["preparation"].astext == "native-publication",
                contract["capabilities"]["forms"] == _json(["scalar"]),
                func.nullif(
                    contract["capabilities"]["prepared_factory"]["entrypoint"].astext, ""
                ).is_not(None),
                contract["capabilities"]["prepared_factory"]["source_digest"].astext.op("~")(
                    "^[0-9a-f]{64}$"
                ),
                p.row(
                    "definition", "sem.data_operation_definition", "implementation_revision"
                ).like("implementation-slice:%"),
            )
        ),
        returns="boolean",
        sql=True,
        immutable=True,
        strict=True,
        definer=False,
    )
    operation = p.row("r", "ops.data_request", "operation_id")
    completion, output = _value("completion"), _value("output")
    binding = p.row("r", "ops.data_request", "binding")
    output_shape = or_(
        output["member_id"].astext.is_not(None),
        cast(output["position"].astext, Integer()).is_distinct_from(0),
        cast(output["multiplicity"].astext, Integer()).is_distinct_from(1),
    )
    p.add(
        "ddo_rich_require_preparation_producer",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            p.lookup(
                "definition",
                "sem.data_operation_definition",
                definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
                definitions.c.operation_id == operation,
            ),
            _reject(
                or_(
                    p.row(
                        "definition", "sem.data_operation_definition", "profile"
                    ).is_distinct_from("derivation"),
                    contract["effects"].is_distinct_from(_json([])),
                    func.nullif(
                        contract["capabilities"]["prepared_factory"]["entrypoint"].astext, ""
                    ).is_(None),
                    contract["capabilities"]["prepared_factory"]["source_digest"]
                    .astext.op("~")("^[0-9a-f]{64}$")
                    .is_not(True),
                    p.row("definition", "sem.data_operation_definition", "implementation_revision")
                    .like("implementation-slice:%")
                    .is_not(True),
                    completion["implementation_revision"].astext.is_distinct_from(
                        p.row(
                            "definition", "sem.data_operation_definition", "implementation_revision"
                        )
                    ),
                    p.row("r", "ops.data_request", "recipe").is_distinct_from(
                        p.row("definition", "sem.data_operation_definition", "recipe")
                    ),
                    and_(
                        input_role(
                            p.model,
                            p.row("r", "ops.data_request", "release_id"),
                            operation,
                            "proposals",
                        ),
                        p.row("r", "ops.data_request", "original_source").is_not(None),
                    ),
                    completion["inputs"].is_distinct_from(binding["inputs"]),
                    completion["support"].is_distinct_from(binding["support"]),
                    func.jsonb_array_length(
                        func.coalesce(completion["execution_evidence"]["cpu_receipts"], _json([]))
                    )
                    != 1,
                ),
                "rich preparation requires actual derivation/factory/CPU and declared inputs",
            ),
            _reject(
                or_(
                    completion["outcome"].astext.is_distinct_from("success"),
                    func.jsonb_array_length(completion["outputs"]) != 1,
                ),
                "rich preparation requires one exact successful conclusion",
            ),
            Assign("output", completion["outputs"][0]),
            _reject(
                or_(
                    output["role"].astext.is_distinct_from(
                        p.row("definition", "sem.data_operation_definition", "output_roles")[0][
                            "name"
                        ].astext
                    ),
                    output_shape,
                    ~select(1)
                    .select_from(kinds)
                    .where(
                        kinds.c.kind_contract == output["product"]["kind_contract"].astext,
                        kinds.c.kind_contract
                        == p.row("definition", "sem.data_operation_definition", "output_roles")[0][
                            "kind_contract"
                        ].astext,
                        kinds.c.universe == "ordinary",
                    )
                    .exists(),
                ),
                "rich preparation differs from its actual whole nominal output",
            ),
        ),
        (
            p.local("definition", "sem.data_operation_definition"),
            p.local("output"),
        ),
    )
    inputs = _items(binding["inputs"], "input")
    p.add(
        "ddo_rich_require_admission_producer",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            p.lookup(
                "definition",
                "sem.data_operation_definition",
                definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
                definitions.c.operation_id == operation,
            ),
            _reject(
                or_(
                    ~func.coalesce(
                        p.row("definition", "sem.data_operation_definition", "command_class")
                        == "rich",
                        False,
                    ),
                    completion["implementation_revision"].astext.is_distinct_from(
                        p.row(
                            "definition", "sem.data_operation_definition", "implementation_revision"
                        )
                    ),
                    p.row("r", "ops.data_request", "recipe").is_distinct_from(
                        p.row("definition", "sem.data_operation_definition", "recipe")
                    ),
                    p.row("r", "ops.data_request", "original_source").is_not(None),
                    completion["inputs"].is_distinct_from(binding["inputs"]),
                    completion["support"].is_distinct_from(binding["support"]),
                    func.jsonb_array_length(
                        func.coalesce(completion["execution_evidence"]["cpu_receipts"], _json([]))
                    )
                    != 1,
                ),
                "rich admission requires actual command/effect/factory/CPU and whole declared inputs",
            ),
            _reject(
                or_(
                    completion["outcome"].astext.is_distinct_from("success"),
                    func.jsonb_array_length(completion["outputs"]) != 1,
                ),
                "rich admission requires one exact successful conclusion",
            ),
            Assign("output", completion["outputs"][0]),
            _reject(
                or_(
                    output["role"].astext.is_distinct_from("admission"),
                    output_shape,
                    ~select(1)
                    .select_from(kinds)
                    .where(
                        kinds.c.kind_contract == output["product"]["kind_contract"].astext,
                        kinds.c.kind
                        == "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichAdmission",
                        kinds.c.universe == "ordinary",
                    )
                    .exists(),
                    select(func.count())
                    .select_from(inputs)
                    .where(inputs.c.value["role"].astext == "consolidation")
                    .scalar_subquery()
                    != 1,
                    select(1)
                    .select_from(inputs)
                    .where(
                        or_(
                            inputs.c.value["member_id"].astext.is_not(None),
                            cast(inputs.c.value["multiplicity"].astext, Integer()).is_distinct_from(
                                1
                            ),
                            inputs.c.value["role"].astext.not_in(
                                ("consolidation", "records", "readings", "policy_authorizations")
                            ),
                        )
                    )
                    .exists(),
                ),
                "rich admission differs from its actual whole populations and nominal output",
            ),
        ),
        (p.local("definition", "sem.data_operation_definition"), p.local("output")),
    )
    p.add(
        "ddo_rich_admission_dependencies_valid",
        (("episode", "text"),),
        (
            CatchDependencyInvalidity(
                (
                    SelectInto(
                        select(core_relation_row(requests))
                        .select_from(
                            requests.join(episodes, episodes.c.request_id == requests.c.id)
                        )
                        .where(episodes.c.id == _value("episode", Text())),
                        ("r",),
                        strict=True,
                    ),
                    If(
                        ~selected_family(
                            p.model, p.row("r", "ops.data_request", "release_id"), operation, "rich"
                        ),
                        (Return(literal(True)),),
                    ),
                    p.lookup(
                        "producing",
                        "ops.data_derivation",
                        episodes.c.id == _value("episode", Text()),
                    ),
                    If(
                        p.row("producing", "ops.data_derivation", "outcome").is_distinct_from(
                            "success"
                        ),
                        (Return(literal(False)),),
                    ),
                    p.lookup(
                        "intent",
                        "ops.data_completion_intent",
                        intents.c.id == p.row("producing", "ops.data_derivation", "intent_id"),
                    ),
                    Assign(
                        "r",
                        func.ops.ddo_require_episode_rich_correspondence(
                            p.row("producing", "ops.data_derivation"),
                            p.row("intent", "ops.data_completion_intent"),
                        ),
                    ),
                    Return(literal(True)),
                ),
                (Return(literal(False)),),
            ),
        ),
        (
            p.local("r", "ops.data_request"),
            p.local("producing", "ops.data_derivation"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="boolean",
        validity=(ProgramValidity("rich", "validator"),),
    )


def _retained_completion(p, request_name, reference):
    episodes, intents = p.table("ops.data_derivation"), p.table("ops.data_completion_intent")
    support = _items(reference["support_references"], "support")
    return SelectInto(
        select(intents.c.payload)
        .select_from(episodes.join(intents, intents.c.id == episodes.c.intent_id))
        .where(
            episodes.c.request_id == p.row(request_name, "ops.data_request", "id"),
            select(1)
            .select_from(support)
            .where(support.c.value["derivation_id"].astext == episodes.c.id)
            .exists(),
        ),
        ("item",),
        strict=True,
    )


def _selected_reference(selected):
    return func.jsonb_build_object(
        "product_id",
        selected["product_id"].astext,
        "member_id",
        literal(None),
        "kind_contract",
        selected["kind_contract"].astext,
        "support_references",
        selected["support"],
        type_=JSONB(),
    )


def _rich_preparation_programs(p):
    operation = p.row("r", "ops.data_request", "operation_id")
    request, completion = p.row("r", "ops.data_request"), _value("completion")
    p.add(
        "ddo_require_rich_preparation_completion",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(
                operation_field(
                    p.model, p.row("r", "ops.data_request", "release_id"), operation, "profile"
                )
                != "derivation",
                (Return(),),
            ),
            Perform(func.ops.ddo_rich_require_preparation_producer(request, completion)),
            _reject(
                func.ops.ddo_cpu_reply_output(request, completion).is_distinct_from(
                    func.data.ddo_normalize(completion["outputs"][0]["product"]["body"])
                ),
                "rich preparation differs from actual original CPU reply and input basis",
            ),
            If(
                input_role(
                    p.model, p.row("r", "ops.data_request", "release_id"), operation, "proposals"
                ),
                (
                    Perform(
                        func.ops.ddo_rich_require_proposal_inputs(
                            request,
                            func.ops.ddo_cpu_input_basis(request),
                        )
                    ),
                ),
            ),
        ),
        validity=(ProgramValidity("rich", "completion_guard"),),
    )
    selected, reference, item = (_value(name) for name in ("selected", "reference", "item"))
    basis, project = _value("basis"), p.row("r", "ops.data_request", "project_id")
    headers = (
        func.ops.ddo_rich_role_headers(basis)
        .table_valued(column("value", JSONB()))
        .render_derived(name="header")
    )
    loops = []
    for role, request_name, message in (
        (
            "proposals",
            "located_request",
            "rich proposal differs from actual located CPU output",
        ),
        (
            "proposal_contexts",
            "packet_request",
            "rich proposal context differs from actual prepared CPU packet",
        ),
    ):
        body = (
            Assign("reference", _selected_reference(selected)),
            Assign(
                request_name,
                func.ops.ddo_rich_producing_request(
                    p.row("r", "ops.data_request"), reference, role
                ),
            ),
            _retained_completion(p, request_name, reference),
            Perform(
                func.ops.ddo_require_rich_preparation_completion(
                    p.row(request_name, "ops.data_request"), item
                )
            ),
            _reject(
                item["outputs"][0]["product"]["body"].is_distinct_from(
                    func.ops.ddo_rich_selected_value(project, basis, role, reference)
                ),
                message,
            ),
        )
        if role == "proposals":
            body += (
                Perform(
                    func.ops.ddo_rich_require_proposal_context(
                        basis, func.ops.ddo_cpu_input_basis(p.row(request_name, "ops.data_request"))
                    )
                ),
            )
        loops.append(
            ForQuery(
                ("selected",),
                select(headers.c.value).where(headers.c.value["role"].astext == role),
                body,
            )
        )
    p.add(
        "ddo_rich_require_proposal_inputs",
        (("r", "ops.data_request"), ("basis", "jsonb")),
        tuple(loops),
        (
            *(p.local(name) for name in ("selected", "reference", "item")),
            p.local("located_request", "ops.data_request"),
            p.local("packet_request", "ops.data_request"),
        ),
    )


def _rich_admission_program(p):
    definitions, episodes, intents, products, members, kinds = (
        p.table(name)
        for name in (
            "sem.data_operation_definition",
            "ops.data_derivation",
            "ops.data_completion_intent",
            "kb.data_product",
            "kb.data_product_member",
            "sem.data_kind_contract",
        )
    )
    json_names = (
        "basis",
        "admission_meaning",
        "admission",
        "consolidated_meaning",
        "consolidated",
        "consolidation_basis",
        "selected",
        "resolution_basis",
        "reference",
        "decision",
        "raw_meaning",
        "resolved_meaning",
        "raw_record",
        "resolved_record",
        "resolution_meaning",
        "report",
        "policy_meaning",
        "policy",
        "events",
        "event",
        "item",
        "packet",
        "raw_comparison",
        "resolved_comparison",
        "assertion",
        "known_meaning",
        "known_graph",
    )
    (
        basis,
        admission_meaning,
        admission,
        consolidated_meaning,
        consolidated,
        consolidation_basis,
        selected,
    ) = (_value(name) for name in json_names[:7])
    (
        resolution_basis,
        reference,
        decision,
        raw_meaning,
        resolved_meaning,
        raw_record,
        resolved_record,
        resolution_meaning,
        report,
        policy_meaning,
        policy,
        events,
        event,
        item,
        packet,
        raw_comparison,
        resolved_comparison,
        assertion,
        known_meaning,
        known_graph,
    ) = (_value(name) for name in json_names[7:])
    reports, raw_reports, policies, known_packets = (
        _value(name) for name in ("reports", "raw_reports", "policies", "known_packets")
    )
    request = p.row("r", "ops.data_request")
    project = p.row("r", "ops.data_request", "project_id")
    completion = _value("completion")

    def headers(value, name="header"):
        return (
            func.ops.ddo_rich_role_headers(value)
            .table_valued(column("value", JSONB()))
            .render_derived(name=name)
        )

    def role_population(left, right, role):
        return func.ops.ddo_rich_role_population(left, role).is_distinct_from(
            func.ops.ddo_rich_role_population(right, role)
        )

    def producer_episode(request_name, target, *, with_intent=False):
        support = _items(reference["support_references"], "support")
        relation = (
            episodes.join(intents, intents.c.id == episodes.c.intent_id)
            if with_intent
            else episodes
        )
        return SelectInto(
            select(episodes.c.id)
            .select_from(relation)
            .where(
                episodes.c.request_id == p.row(request_name, "ops.data_request", "id"),
                select(1)
                .select_from(support)
                .where(support.c.value["derivation_id"].astext == episodes.c.id)
                .exists(),
            ),
            (target,),
            strict=True,
        )

    bound = headers(consolidation_basis)
    known_members = _items(_field(known_meaning, "members")[1], "known_member")
    admission_members = _items(_field(admission_meaning, "members")[1], "admitted_member")
    original_members = _items(_field(consolidated_meaning, "members")[1], "original_member")
    plain_members = _items(admission["members"], "member")
    policy_refs = _items(admission["policy_authorizations"], "policy_reference")
    event_rows = _items(events, "event_row")
    resolution_headers = headers(resolution_basis, "resolution_header")
    judgments = _items(admission["reading_decisions"], "judgment")
    report_inputs = _items(report["inputs"], "input")
    raw_pairs = _items(raw_meaning[1], "raw_pair")
    resolved_pairs = _items(resolved_meaning[1], "resolved_pair")
    dependencies = _items(_field(raw_meaning, "computation_dependencies")[1], "dependency")
    retained = _items(_field(resolved_meaning, "computation_dependencies")[1], "retained")
    selected_ids = (
        func.jsonb_array_elements_text(admission["selected_reading_ids"])
        .table_valued(column("value", Text()))
        .render_derived(name="selected_id")
    )
    effects = _items(definitions.c.support_contract["effects"], "effect")
    foreign_effect = (
        select(1)
        .select_from(definitions.join(effects, literal(True)))
        .where(
            definitions.c.release_id == p.row("r", "ops.data_request", "release_id"),
            definitions.c.operation_id == p.row("r", "ops.data_request", "operation_id"),
            effects.c.value["name"].astext == "native-rich-knowledge-admission",
        )
        .exists()
    )
    census = []
    for role, endpoint, message in (
        ("records", "original", "rich decision census omits or duplicates actual raw records"),
        (
            "readings",
            "resolved",
            "rich decision census omits or duplicates actual resolved records",
        ),
    ):
        missing = (
            select(func.count())
            .select_from(judgments)
            .where(
                judgments.c.value[endpoint]["product_id"].astext == members.c.product_id,
                judgments.c.value[endpoint]["member_id"].astext == members.c.member_id,
            )
            .correlate(members)
            .scalar_subquery()
            != 1
        )
        census.append(
            _reject(
                select(1)
                .select_from(
                    bound.join(members, members.c.product_id == bound.c.value["product_id"].astext)
                )
                .where(
                    bound.c.value["role"].astext == role,
                    _field(members.c.body, "candidate_type") == _json(["string", "record"]),
                    missing,
                )
                .exists(),
                message,
            )
        )
    from .effect_policy import require_admitted_effect

    admitted_effect = require_admitted_effect(
        p.model,
        lambda field: p.row("r", "ops.data_request", field),
        "native-rich-knowledge-admission",
    )
    p.add(
        "ddo_require_rich_admission_completion",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            If(
                ~admitted_effect,
                (
                    _reject(
                        foreign_effect, "rich admission effect requires its actual operation owner"
                    ),
                    Return(),
                ),
            ),
            Perform(func.ops.ddo_rich_require_admission_producer(request, completion)),
            Assign("basis", func.ops.ddo_cpu_input_basis(request)),
            Assign(
                "admission_meaning",
                func.data.ddo_normalize(completion["outputs"][0]["product"]["body"]),
            ),
            _reject(
                func.ops.ddo_cpu_reply_output(request, completion).is_distinct_from(
                    admission_meaning
                ),
                "rich admission differs from exact CPU decision and graph projection",
            ),
            Assign("admission", _plain(admission_meaning)),
            Assign(
                "consolidated_meaning",
                func.ops.ddo_rich_selected_value(
                    project, basis, "consolidation", admission["consolidation"]
                ),
            ),
            Assign("consolidated", _plain(consolidated_meaning)),
            Assign(
                "consolidation_request",
                func.ops.ddo_rich_producing_request(
                    request, admission["consolidation"], "consolidation"
                ),
            ),
            _retained_completion(p, "consolidation_request", admission["consolidation"]),
            _reject(
                func.ops.ddo_cpu_reply_output(
                    p.row("consolidation_request", "ops.data_request"), item
                ).is_distinct_from(consolidated_meaning),
                "rich consolidation differs from actual original CPU graph reply",
            ),
            Assign(
                "consolidation_basis",
                func.ops.ddo_cpu_input_basis(p.row("consolidation_request", "ops.data_request")),
            ),
            _reject(
                or_(
                    consolidated["version"].astext.is_distinct_from("rich-consolidation-1"),
                    consolidated["standing"].astext.is_distinct_from("private-consolidated"),
                    admission["version"].astext.is_distinct_from("rich-admission-1"),
                    admission["standing"].astext.is_distinct_from("accepted"),
                    *(
                        role_population(basis, consolidation_basis, role)
                        for role in ("records", "readings")
                    ),
                ),
                "rich admission changes actual consolidated records/readings population or producer custody",
            ),
            _reject(
                or_(
                    admission["eligibility_policy_digest"].astext.is_(None),
                    admission["eligibility_policy_digest"].astext.op("!~")("^[0-9a-f]{64}$"),
                    admission["eligibility_policy_digest"].astext.is_distinct_from(
                        consolidated["eligibility"]["eligibility_policy_digest"].astext
                    ),
                    *(
                        admission[key].is_distinct_from(consolidated["eligibility"][key])
                        for key in (
                            "selected_fact_ids",
                            "selected_occurrence_ids",
                            "scientific_representatives",
                        )
                    ),
                ),
                "rich admission changes actual rule eligibility or its checked policy basis",
            ),
            Perform(
                func.ops.ddo_rich_require_proposal_inputs(
                    p.row("consolidation_request", "ops.data_request"), consolidation_basis
                )
            ),
            ForQuery(
                ("selected",),
                select(bound.c.value).where(bound.c.value["role"].astext == "known_universe"),
                (
                    Assign("reference", _selected_reference(selected)),
                    Assign(
                        "known_request",
                        func.ops.ddo_rich_producing_request(
                            p.row("consolidation_request", "ops.data_request"),
                            reference,
                            "known_universe",
                        ),
                    ),
                    producer_episode("known_request", "known_episode"),
                    _reject(
                        ~func.ops.ddo_rich_admission_dependencies_valid(
                            _value("known_episode", Text())
                        ),
                        "rich known universe lacks actual sealed native admission authority",
                    ),
                    SelectInto(
                        select(products.c.canonical_body).where(
                            products.c.id == reference["product_id"].astext,
                            products.c.project_id == project,
                        ),
                        ("known_meaning",),
                        strict=True,
                    ),
                    Assign("known_graph", _plain(known_meaning)),
                    _reject(
                        or_(
                            known_graph["eligibility_policy_digest"].astext.is_distinct_from(
                                admission["eligibility_policy_digest"].astext
                            ),
                            func.jsonb_typeof(known_graph["selected_reading_ids"]).is_distinct_from(
                                "array"
                            ),
                        ),
                        "rich known eligibility requires its actual current policy basis and selection",
                    ),
                    ForQuery(
                        ("packet",),
                        select(known_members.c.value).where(
                            _field(known_members.c.value, "body", "member_type")
                            == _json(["string", "source-reading-assertion"]),
                            known_graph["selected_reading_ids"].has_key(
                                _text(known_members.c.value, "member_id")
                            ),
                        ),
                        (
                            Assign(
                                "known_packets",
                                known_packets.op("||")(
                                    func.jsonb_build_object(
                                        func.ops.ddo_digest(func.data.ddo_normalize(packet)),
                                        func.data.ddo_normalize(packet),
                                    )
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            _reject(
                or_(
                    select(1)
                    .select_from(admission_members)
                    .where(
                        ~select(1)
                        .select_from(original_members)
                        .where(
                            func.data.ddo_normalize(original_members.c.value)
                            == func.data.ddo_normalize(admission_members.c.value)
                        )
                        .correlate(admission_members)
                        .exists()
                    )
                    .exists(),
                    select(1)
                    .select_from(plain_members)
                    .group_by(plain_members.c.value["member_id"].astext)
                    .having(func.count() != 1)
                    .exists(),
                ),
                "rich admission changes actual consolidated graph members",
            ),
            _reject(
                func.jsonb_array_length(admission["policy_authorizations"]).is_distinct_from(
                    func.jsonb_array_length(
                        func.ops.ddo_rich_role_population(basis, "policy_authorizations")
                    )
                ),
                "rich policy population differs from actual declared authorizations",
            ),
            ForQuery(
                ("reference",),
                select(policy_refs.c.value),
                (
                    _reject(
                        or_(
                            reference["member_id"].astext.is_not(None),
                            policies.has_key(reference["product_id"].astext),
                        ),
                        "rich policy requires unique whole issued authorizations",
                    ),
                    Assign(
                        "policy_meaning",
                        func.ops.ddo_rich_selected_value(
                            project, basis, "policy_authorizations", reference
                        ),
                    ),
                    Assign(
                        "authorization_request",
                        func.ops.ddo_rich_producing_request(
                            request,
                            reference,
                            "policy_authorizations",
                        ),
                    ),
                    _reject(
                        ~select(1)
                        .select_from(kinds)
                        .where(
                            kinds.c.kind_contract == reference["kind_contract"].astext,
                            kinds.c.kind
                            == "https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization",
                            kinds.c.universe == "ordinary",
                        )
                        .exists(),
                        "rich policy is not the actual public authorization contract",
                    ),
                    producer_episode(
                        "authorization_request", "authorization_episode", with_intent=True
                    ),
                    _reject(
                        func.ops.ddo_policy_authority_leaf(
                            _value("authorization_episode", Text())
                        ).is_not(True),
                        "rich policy lacks its authentic issued public authorization",
                    ),
                    Assign(
                        "policies",
                        policies.op("||")(
                            func.jsonb_build_object(
                                reference["product_id"].astext,
                                func.jsonb_build_object(
                                    "reference", reference, "body", _plain(policy_meaning)
                                ),
                            )
                        ),
                    ),
                ),
            ),
            ForQuery(
                ("selected",),
                select(bound.c.value).where(bound.c.value["role"].astext == "records"),
                (
                    Assign("reference", _selected_reference(selected)),
                    Perform(func.ops.ddo_rich_producing_request(request, reference, "records")),
                    SelectInto(
                        select(func.ops.ddo_digest(products.c.canonical_body)).where(
                            products.c.id == selected["product_id"].astext,
                            products.c.project_id == project,
                        ),
                        ("raw_digest",),
                        strict=True,
                    ),
                    Assign(
                        "raw_reports",
                        raw_reports.op("||")(
                            func.jsonb_build_object(
                                selected["product_id"].astext, _value("raw_digest", Text())
                            )
                        ),
                    ),
                ),
            ),
            ForQuery(
                ("selected",),
                select(bound.c.value).where(bound.c.value["role"].astext == "readings"),
                (
                    Assign("reference", _selected_reference(selected)),
                    Assign(
                        "resolution_request",
                        func.ops.ddo_rich_producing_request(request, reference, "readings"),
                    ),
                    Assign(
                        "resolution_basis",
                        func.ops.ddo_cpu_input_basis(
                            p.row("resolution_request", "ops.data_request")
                        ),
                    ),
                    Assign(
                        "resolution_meaning",
                        func.ops.ddo_rich_selected_value(
                            project, consolidation_basis, "readings", reference
                        ),
                    ),
                    _retained_completion(p, "resolution_request", reference),
                    _reject(
                        func.ops.ddo_cpu_reply_output(
                            p.row("resolution_request", "ops.data_request"), item
                        ).is_distinct_from(resolution_meaning),
                        "rich final-event report differs from actual original reading CPU reply",
                    ),
                    Assign("report", _plain(resolution_meaning)),
                    Assign(
                        "events",
                        cast(report["diagnostics_json"].astext, JSONB())["record_policy_events"],
                    ),
                    _reject(
                        or_(
                            func.jsonb_typeof(events).is_distinct_from("array"),
                            select(1)
                            .select_from(event_rows)
                            .group_by(
                                event_rows.c.value["record_id"].astext,
                                event_rows.c.value["interpretation_id"].astext,
                            )
                            .having(func.count() != 1)
                            .exists(),
                        ),
                        "rich resolution requires unique actual final-event attribution",
                    ),
                    SelectInto(
                        select(
                            func.coalesce(
                                func.jsonb_object_agg(
                                    func.data.canonical_json(
                                        func.jsonb_build_array(
                                            event_rows.c.value["record_id"].astext,
                                            event_rows.c.value["interpretation_id"].astext,
                                        )
                                    ),
                                    event_rows.c.value,
                                ),
                                _json({}),
                            )
                        ),
                        ("events",),
                    ),
                    Assign(
                        "reports",
                        reports.op("||")(
                            func.jsonb_build_object(
                                reference["product_id"].astext,
                                func.jsonb_build_object(
                                    "inputs",
                                    select(
                                        func.coalesce(
                                            func.jsonb_agg(resolution_headers.c.value), _json([])
                                        )
                                    ).scalar_subquery(),
                                    "release_id",
                                    p.row("resolution_request", "ops.data_request", "release_id"),
                                    "recipe",
                                    p.row("resolution_request", "ops.data_request", "recipe"),
                                    "events",
                                    events,
                                ),
                            )
                        ),
                    ),
                ),
            ),
            *census,
            ForQuery(
                ("decision",),
                select(judgments.c.value),
                (
                    Assign(
                        "raw_meaning",
                        func.ops.ddo_rich_selected_value(
                            project, consolidation_basis, "records", decision["original"]
                        ),
                    ),
                    Assign("raw_record", _plain(raw_meaning)),
                    _reject(
                        or_(
                            raw_record["candidate_type"].astext.is_distinct_from("record"),
                            decision["original"]["member_id"].astext.is_(None),
                            raw_record["record_id"].astext.is_distinct_from(
                                decision["record_id"].astext
                            ),
                            raw_record["interpretation_id"].astext.is_distinct_from(
                                decision["source_interpretation_id"].astext
                            ),
                        ),
                        "rich decision relabels actual original record attribution",
                    ),
                    If(
                        or_(
                            decision["resolution"] == _json(None),
                            decision["resolved"] == _json(None),
                        ),
                        (
                            _reject(
                                or_(
                                    decision["resolution"].is_distinct_from(_json(None)),
                                    decision["resolved"].is_distinct_from(_json(None)),
                                    decision["outcome"].astext.is_distinct_from("not-checkable"),
                                    decision["reason_code"].astext.is_distinct_from(
                                        "resolution-unavailable"
                                    ),
                                    decision["assertion_member_id"].astext.is_not(None),
                                ),
                                "rich missing resolution must remain explicitly uncheckable",
                            ),
                            Continue(),
                        ),
                    ),
                    Assign(
                        "resolved_meaning",
                        func.ops.ddo_rich_selected_value(
                            project, consolidation_basis, "readings", decision["resolved"]
                        ),
                    ),
                    Perform(
                        func.ops.ddo_rich_selected_value(
                            project, consolidation_basis, "readings", decision["resolution"]
                        )
                    ),
                    Assign("resolved_record", _plain(resolved_meaning)),
                    Assign("report", reports[decision["resolution"]["product_id"].astext]),
                    _reject(
                        or_(
                            report.is_(None),
                            decision["resolved"]["product_id"].astext.is_distinct_from(
                                decision["resolution"]["product_id"].astext
                            ),
                            decision["resolution"]["member_id"].astext.is_not(None),
                            decision["original"]["member_id"].astext.is_(None),
                            decision["resolved"]["member_id"].astext.is_(None),
                            raw_record["candidate_type"].astext.is_distinct_from("record"),
                            resolved_record["candidate_type"].astext.is_distinct_from("record"),
                            *(
                                record["record_id"].astext.is_distinct_from(
                                    decision["record_id"].astext
                                )
                                for record in (raw_record, resolved_record)
                            ),
                            raw_record["interpretation_id"].astext.is_distinct_from(
                                decision["source_interpretation_id"].astext
                            ),
                            resolved_record["interpretation_id"].astext.is_distinct_from(
                                decision["interpretation_id"].astext
                            ),
                            ~select(1)
                            .select_from(report_inputs)
                            .where(
                                report_inputs.c.value["role"].astext == "candidates",
                                report_inputs.c.value["product_id"].astext
                                == decision["original"]["product_id"].astext,
                                report_inputs.c.value["member_id"].astext.is_(None),
                                func.ops.ddo_rich_support_population(
                                    report_inputs.c.value["support"]
                                )
                                == func.ops.ddo_rich_support_population(
                                    decision["original"]["support_references"]
                                ),
                            )
                            .exists(),
                        ),
                        "rich decision relabels actual raw/resolved member and producing report custody",
                    ),
                    SelectInto(
                        select(
                            func.jsonb_build_array(
                                "mapping",
                                func.jsonb_agg(
                                    aggregate_order_by(
                                        raw_pairs.c.value, raw_pairs.c.value[0].astext.collate("C")
                                    )
                                ),
                            )
                        ).where(
                            raw_pairs.c.value[0].astext.not_in(
                                ("interpretation_id", "computation_dependencies")
                            )
                        ),
                        ("raw_comparison",),
                    ),
                    SelectInto(
                        select(
                            func.jsonb_build_array(
                                "mapping",
                                func.jsonb_agg(
                                    aggregate_order_by(
                                        resolved_pairs.c.value,
                                        resolved_pairs.c.value[0].astext.collate("C"),
                                    )
                                ),
                            )
                        ).where(
                            resolved_pairs.c.value[0].astext.not_in(
                                ("interpretation_id", "computation_dependencies")
                            )
                        ),
                        ("resolved_comparison",),
                    ),
                    _reject(
                        or_(
                            raw_comparison.is_distinct_from(resolved_comparison),
                            ~_field(resolved_meaning, "computation_dependencies")[1].contains(
                                func.jsonb_build_array(
                                    func.jsonb_build_array(
                                        "string",
                                        literal("raw-candidate-result:")
                                        + raw_reports[
                                            decision["original"]["product_id"].astext
                                        ].astext,
                                    )
                                )
                            ),
                            select(1)
                            .select_from(dependencies)
                            .where(
                                ~select(1)
                                .select_from(retained)
                                .where(retained.c.value == dependencies.c.value)
                                .correlate(dependencies)
                                .exists()
                            )
                            .exists(),
                        ),
                        "rich resolved reading changes complete original fields/evidence/alternatives",
                    ),
                    _reject(
                        and_(
                            decision["authorization"] != _json(None),
                            decision["authorization"].is_distinct_from(
                                policies[decision["authorization"]["product_id"].astext][
                                    "reference"
                                ]
                            ),
                        ),
                        "rich decision references authority outside actual declared issuer population",
                    ),
                    If(
                        decision["outcome"].astext.in_(("accepted", "below-threshold")),
                        (
                            Assign(
                                "policy",
                                policies[decision["authorization"]["product_id"].astext]["body"],
                            ),
                            Assign(
                                "event",
                                report["events"][
                                    func.data.canonical_json(
                                        func.jsonb_build_array(
                                            decision["record_id"].astext,
                                            decision["interpretation_id"].astext,
                                        )
                                    )
                                ],
                            ),
                            Assign(
                                "family_contract",
                                func.ops.ddo_rich_family_contract(
                                    report["release_id"].astext, resolved_record["contract"].astext
                                ),
                            ),
                            _reject(
                                or_(
                                    policy.is_(None),
                                    decision["authorization"].is_distinct_from(
                                        policies[decision["authorization"]["product_id"].astext][
                                            "reference"
                                        ]
                                    ),
                                    event.is_(None),
                                    event["outcome"].astext.is_distinct_from("completed"),
                                    *(
                                        event[key].astext.is_distinct_from(decision[key].astext)
                                        for key in (
                                            "feature_input_digest",
                                            "feature_instance_digest",
                                            "event_procedure",
                                        )
                                    ),
                                    *(
                                        policy[key].astext.is_distinct_from(decision[key].astext)
                                        for key in ("feature_instance_digest", "event_procedure")
                                    ),
                                    policy["family"].astext.is_distinct_from(
                                        resolved_record["family"].astext
                                    ),
                                    policy["family_contract"].astext.is_distinct_from(
                                        _value("family_contract", Text())
                                    ),
                                    _value("family_contract", Text()).is_distinct_from(
                                        func.ops.ddo_rich_family_contract(
                                            p.row("r", "ops.data_request", "release_id"),
                                            resolved_record["contract"].astext,
                                        )
                                    ),
                                    policy["reading_recipe"].astext.is_distinct_from(
                                        report["recipe"].astext
                                    ),
                                    policy["applicability"]["project_id"].astext.is_distinct_from(
                                        project
                                    ),
                                    func.encode(
                                        func.sha256(
                                            func.convert_to(
                                                event["feature_input_canonical_json"].astext, "UTF8"
                                            )
                                        ),
                                        "hex",
                                    ).is_distinct_from(event["feature_input_digest"].astext),
                                ),
                                "rich decision lacks exact issued policy/current family/recipe and unique sealed feature event",
                            ),
                        ),
                    ),
                    If(
                        decision["outcome"].astext == "accepted",
                        (
                            SelectInto(
                                select(plain_members.c.value).where(
                                    plain_members.c.value["member_id"].astext
                                    == decision["assertion_member_id"].astext
                                ),
                                ("assertion",),
                                strict=True,
                            ),
                            _reject(
                                or_(
                                    assertion["body"]["member_type"].astext.is_distinct_from(
                                        "source-reading-assertion"
                                    ),
                                    *(
                                        assertion["body"][key].is_distinct_from(decision[key])
                                        for key in ("original", "resolution", "resolved")
                                    ),
                                    *(
                                        assertion["body"][key].astext.is_distinct_from(
                                            decision[key].astext
                                        )
                                        for key in (
                                            "record_id",
                                            "source_interpretation_id",
                                            "interpretation_id",
                                        )
                                    ),
                                ),
                                "rich accepted assertion differs from actual complete reading decision",
                            ),
                        ),
                        (
                            _reject(
                                decision["assertion_member_id"].astext.is_not(None),
                                "rich rejected reading cannot retain an accepted assertion",
                            ),
                        ),
                    ),
                ),
            ),
            _reject(
                select(1)
                .select_from(admission_members)
                .where(
                    _field(admission_members.c.value, "body", "member_type")
                    == _json(["string", "source-reading-assertion"]),
                    select(func.count())
                    .select_from(judgments)
                    .where(
                        judgments.c.value["outcome"].astext == "accepted",
                        judgments.c.value["assertion_member_id"].astext
                        == _text(admission_members.c.value, "member_id"),
                    )
                    .correlate(admission_members)
                    .scalar_subquery()
                    != 1,
                    ~func.ops.ddo_rich_carried_reading(admission_members.c.value, known_packets),
                )
                .exists(),
                "rich accepted graph has no exact actual reading decision",
            ),
            _reject(
                or_(
                    func.jsonb_typeof(admission["selected_reading_ids"]).is_distinct_from("array"),
                    select(
                        func.coalesce(
                            func.jsonb_agg(
                                aggregate_order_by(
                                    plain_members.c.value["member_id"].astext,
                                    plain_members.c.value["member_id"].astext.collate("C"),
                                )
                            ),
                            _json([]),
                        )
                    )
                    .where(
                        plain_members.c.value["body"]["member_type"].astext
                        == "source-reading-assertion"
                    )
                    .scalar_subquery()
                    .is_distinct_from(
                        select(
                            func.coalesce(
                                func.jsonb_agg(
                                    aggregate_order_by(
                                        selected_ids.c.value, selected_ids.c.value.collate("C")
                                    )
                                ),
                                _json([]),
                            )
                        ).scalar_subquery()
                    ),
                ),
                "rich selected readings differ from actual retained assertion packets",
            ),
        ),
        (
            *(p.local(name) for name in json_names),
            *(
                p.local(name, initial=_json({}))
                for name in ("reports", "raw_reports", "policies", "known_packets")
            ),
            *(
                p.local(name, "ops.data_request")
                for name in (
                    "consolidation_request",
                    "authorization_request",
                    "resolution_request",
                    "known_request",
                )
            ),
            *(
                p.local(name, "text")
                for name in (
                    "authorization_episode",
                    "known_episode",
                    "raw_digest",
                    "family_contract",
                )
            ),
        ),
        validity=(ProgramValidity("rich", "completion_guard"),),
    )


def rich_admission_native_programs(*, target_metadata=None) -> tuple[ProgramDeclaration, ...]:
    programs = _RichPrograms(target_metadata)
    _rich_input_programs(programs)
    _rich_producer_programs(programs)
    _rich_preparation_programs(programs)
    _rich_admission_program(programs)
    return tuple(programs.output)


def rich_admission_native_sql(*, target_metadata=None) -> str:
    """Render the current capture from its typed declarations."""
    return native_sql_script(
        statement
        for declaration in rich_admission_native_programs(target_metadata=target_metadata)
        for statement in (
            declaration.routine.render(),
            native_privilege_sql(declaration.identity, "PUBLIC", grant=False),
        )
    )
