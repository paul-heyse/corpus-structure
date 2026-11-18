"""Private rich-admission correspondence at the existing native completion fence.

Policy numerics and graph lowering belong to their captured CPU owners. Native
admission authenticates those owners, their exact declared inputs, and the actual
child reply rather than interpreting an ungrounded accepted flag.
"""

from __future__ import annotations

import json

from sqlalchemy import Boolean, Integer, Text, and_, cast, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by
from sqlalchemy.types import NullType

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
    SelectInto,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
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


def _items(value, name="item"):
    return func.jsonb_array_elements(value).table_valued(column("value", JSONB())).render_derived(name=name)


def _value(name, type_=None):
    return core_variable(name, JSONB() if type_ is None else type_)


def _reject(condition, message):
    return If(condition, (Raise(message, "23514"),))


class _RichPrograms:
    """Resolve rich native authority queries against the captured relation model."""

    def __init__(self, metadata):
        if metadata is None:
            from .metadata import metadata
        self.model = metadata
        self.output = []

    def table(self, name):
        return self.model.tables[name]

    def row(self, name, relation, field=None):
        return core_variable(name, NullType() if field is None else self.table(relation).c[field].type, field)

    def local(self, name, kind="jsonb", initial=None):
        return Local(name, self.table(kind) if kind in self.model.tables else pg_type(kind), initial)

    def lookup(self, target, relation, *conditions):
        selected = self.table(relation)
        return SelectInto(select(core_relation_row(selected)).select_from(selected).where(*conditions), (target,), strict=True)

    def add(self, name, parameters, body, locals_=(), *, returns="void", sql=False, immutable=False, strict=False, definer=True, setof=False):
        arguments = tuple(Parameter(key, pg_type(*kind.split("."))) for key, kind in parameters)
        result_type = pg_type(*returns.split("."))
        result_type.setof = setof
        if sql:
            rendered = sql_function("ops", name, parameters=arguments, returns=result_type, body=body, volatility="immutable" if immutable else "stable", strict=strict, security_definer=definer, search_path=("pg_catalog", "pg_temp"))
        else:
            rendered = function("ops", name, parameters=arguments, returns=result_type, body=Block(tuple(body), tuple(locals_)), volatility="immutable" if immutable else "stable", strict=strict, security_definer=definer, search_path=("pg_catalog", "pg_temp"))
        self.output.extend((rendered, native_privilege_sql(NativeIdentity("function", "ops", name, tuple(kind for _, kind in parameters)), "PUBLIC", grant=False)))


def _rich_input_programs(p):
    support = _value("support")
    refs = _items(support, "support_item")
    distinct = select((func.jsonb_strip_nulls(refs.c.value).op("-")("admission_use_id")).label("reference")).distinct().subquery("references_")
    p.add("ddo_rich_support_population", (("support", "jsonb"),), select(func.coalesce(func.jsonb_agg(aggregate_order_by(distinct.c.reference, func.convert_to(func.data.canonical_json(distinct.c.reference), "UTF8"))), _json([]))), returns="jsonb", sql=True, immutable=True, strict=True, definer=False)
    basis = _value("basis")
    roles = _items(_field(basis, "roles")[1], "role_meaning")
    pairs = _items(roles.c.value[1], "pair")
    header = select(func.coalesce(func.jsonb_agg(aggregate_order_by(pairs.c.value, pairs.c.value[0].astext.collate("C"))), _json([]))).select_from(pairs).where(pairs.c.value[0].astext.not_in(("body", "context"))).correlate(roles).scalar_subquery()
    p.add("ddo_rich_role_headers", (("basis", "jsonb"),), select(_plain(func.jsonb_build_array("mapping", header))).select_from(roles), returns="jsonb", sql=True, immutable=True, strict=True, definer=False, setof=True)
    headers = func.ops.ddo_rich_role_headers(basis).table_valued(column("value", JSONB())).render_derived(name="row_value")
    population = select(func.jsonb_build_object("product_id", headers.c.value["product_id"], "member_id", headers.c.value["member_id"], "multiplicity", headers.c.value["multiplicity"], "support", func.ops.ddo_rich_support_population(headers.c.value["support"])).label("item")).where(headers.c.value["role"].astext == _value("role_name", Text())).subquery("population")
    p.add("ddo_rich_role_population", (("basis", "jsonb"), ("role_name", "text")), select(func.coalesce(func.jsonb_agg(aggregate_order_by(population.c.item, func.convert_to(func.data.canonical_json(population.c.item), "UTF8"))), _json([]))), returns="jsonb", sql=True, immutable=True, strict=True, definer=False)
    products, members = p.table("kb.data_product"), p.table("kb.data_product_member")
    selected, bound = _value("selected"), _value("bound")
    bound_roles = _items(_field(basis, "roles")[1], "bound_role")
    p.add("ddo_rich_selected_value", (("project", "text"), ("basis", "jsonb"), ("role_name", "text"), ("selected", "jsonb")), (
        SelectInto(select(bound_roles.c.value).where(_text(bound_roles.c.value, "role") == _value("role_name", Text()), _text(bound_roles.c.value, "product_id") == selected["product_id"].astext, _field(bound_roles.c.value, "member_id") == _json(["null"])), ("bound",), strict=True),
        _reject(_field(bound, "support").is_distinct_from(func.data.ddo_normalize(func.data.ddo_json_meaning(func.jsonb_strip_nulls(selected["support_references"])))), "rich selection differs from actual whole-role support"),
        p.lookup("product", "kb.data_product", products.c.id == selected["product_id"].astext, products.c.project_id == _value("project", Text())),
        If(selected["member_id"].astext.is_(None), (
            _reject(p.row("product", "kb.data_product", "kind_contract").is_distinct_from(selected["kind_contract"].astext), "rich whole selection differs from its actual kind"), Return(p.row("product", "kb.data_product", "canonical_body")),
        )),
        p.lookup("member", "kb.data_product_member", members.c.product_id == p.row("product", "kb.data_product", "id"), members.c.member_id == selected["member_id"].astext),
        _reject(p.row("member", "kb.data_product_member", "kind_contract").is_distinct_from(selected["kind_contract"].astext), "rich nominal member differs from its actual whole-report kind"),
        Return(p.row("member", "kb.data_product_member", "body")),
    ), (p.local("bound"), p.local("product", "kb.data_product"), p.local("member", "kb.data_product_member")), returns="jsonb")
    episodes, outputs, receipts, requests, definitions, intents = (p.table(name) for name in ("ops.data_derivation", "ops.data_derivation_output", "ops.data_publication_receipt", "ops.data_request", "sem.data_operation_definition", "ops.data_completion_intent"))
    evidence = _items(selected["support_references"], "reference")
    contract, payload = p.row("definition", "sem.data_operation_definition", "support_contract"), p.row("intent", "ops.data_completion_intent", "payload")
    p.add("ddo_rich_producing_request", (("project", "text"), ("selected", "jsonb"), ("operation_name", "text"), ("factory_name", "text"), ("output_role", "text"), ("requires_cpu", "boolean")), (
        SelectInto(select(core_relation_row(episodes)).select_from(episodes.join(outputs, outputs.c.derivation_id == episodes.c.id).join(receipts, and_(receipts.c.derivation_id == episodes.c.id, receipts.c.intent_id == episodes.c.intent_id))).where(
            outputs.c.product_id == selected["product_id"].astext, outputs.c.member_id.is_(None), or_(_value("output_role", Text()).is_(None), outputs.c.role == _value("output_role", Text())), outputs.c.multiplicity == 1, episodes.c.outcome == "success",
            select(1).select_from(evidence).where(evidence.c.value["kind"].astext == "computation", evidence.c.value["derivation_id"].astext == episodes.c.id).exists(),
        ), ("producer",), strict=True),
        p.lookup("request", "ops.data_request", requests.c.id == p.row("producer", "ops.data_derivation", "request_id"), requests.c.project_id == _value("project", Text())),
        p.lookup("definition", "sem.data_operation_definition", definitions.c.release_id == p.row("request", "ops.data_request", "release_id"), definitions.c.operation_id == p.row("request", "ops.data_request", "operation_id")),
        p.lookup("intent", "ops.data_completion_intent", intents.c.id == p.row("producer", "ops.data_derivation", "intent_id")),
        _reject(or_(
            and_(_value("operation_name", Text()).is_not(None), p.row("definition", "sem.data_operation_definition", "operation_id").is_distinct_from(_value("operation_name", Text()))),
            and_(_value("factory_name", Text()).is_not(None), contract["capabilities"]["prepared_factory"]["entrypoint"].astext.is_distinct_from(_value("factory_name", Text()))),
            contract["capabilities"]["prepared_factory"]["source_digest"].astext.op("~")("^[0-9a-f]{64}$").is_not(True),
            p.row("definition", "sem.data_operation_definition", "implementation_revision").like("implementation-slice:%").is_not(True),
            payload["implementation_revision"].astext.is_distinct_from(p.row("definition", "sem.data_operation_definition", "implementation_revision")),
            p.row("producer", "ops.data_derivation", "recipe").is_distinct_from(p.row("definition", "sem.data_operation_definition", "recipe")),
            p.row("request", "ops.data_request", "recipe").is_distinct_from(p.row("definition", "sem.data_operation_definition", "recipe")),
            and_(_value("requires_cpu", Boolean()), or_(p.row("definition", "sem.data_operation_definition", "profile").is_distinct_from("derivation"), contract["effects"].is_distinct_from(_json([])), func.jsonb_array_length(func.coalesce(payload["execution_evidence"]["cpu_receipts"], _json([]))) != 1)),
        ), "rich selection lacks its actual admitted producer and CPU/common receipt"),
        Return(p.row("request", "ops.data_request")),
    ), (p.local("request", "ops.data_request"), p.local("producer", "ops.data_derivation"), p.local("definition", "sem.data_operation_definition"), p.local("intent", "ops.data_completion_intent")), returns="ops.data_request")
    artifacts = p.table("sem.artifact")
    archive = _value("archive")
    kinds = _items(archive["kinds"], "kind")
    identities = _items(archive["identities"], "identity")
    p.add("ddo_rich_family_contract", (("p_release", "text"), ("local_name", "text")), (
        SelectInto(select(cast(func.convert_from(artifacts.c.content, "UTF8"), JSONB())).where(artifacts.c.release_id == _value("p_release", Text()), artifacts.c.artifact_name == "data_operations.json"), ("archive",), strict=True),
        SelectInto(select(identities.c.value["key"].astext).select_from(kinds.join(identities, identities.c.value["owner"].astext == kinds.c.value["semantic_id"].astext)).where(kinds.c.value["name"].astext == _value("local_name", Text()), kinds.c.value["category"].astext == "class", kinds.c.value["complete"] == _json(True), identities.c.value["domain"].astext == "kind"), ("result",), strict=True),
        Return(_value("result", Text())),
    ), (p.local("archive"), p.local("result", "text")), returns="text")
    context = func.ops.ddo_rich_role_headers(_value("consolidation_basis")).table_valued(column("value", JSONB())).render_derived(name="context_input")
    consumed = _value("consumed")
    located = func.ops.ddo_rich_role_headers(_value("located_basis")).table_valued(column("value", JSONB())).render_derived(name="located")
    p.add("ddo_rich_require_proposal_context", (("consolidation_basis", "jsonb"), ("located_basis", "jsonb")), (
        SelectInto(select(located.c.value).where(located.c.value["role"].astext == "packet"), ("consumed",), strict=True),
        _reject(or_(consumed["member_id"].astext.is_not(None), ~select(1).select_from(context).where(context.c.value["role"].astext == "proposal_contexts", context.c.value["product_id"].astext == consumed["product_id"].astext, context.c.value["member_id"].astext.is_(None), func.ops.ddo_rich_support_population(context.c.value["support"]) == func.ops.ddo_rich_support_population(consumed["support"])).exists()), "rich located proposal differs from actual consumed whole packet/context support"),
    ), (p.local("consumed"),), immutable=True, strict=True, definer=False)
    packet = _value("packet")
    normalized = func.data.ddo_normalize(packet, type_=JSONB())
    p.add("ddo_rich_carried_reading", (("packet", "jsonb"), ("known_packets", "jsonb")), select(func.coalesce(and_(_field(packet, "body", "member_type") == _json(["string", "source-reading-assertion"]), _value("known_packets")[func.ops.ddo_digest(normalized)] == normalized), False)), returns="boolean", sql=True, immutable=True, strict=True, definer=False)


def _rich_producer_programs(p):
    definitions, kinds, requests, episodes, intents = (p.table(name) for name in ("sem.data_operation_definition", "sem.data_kind_contract", "ops.data_request", "ops.data_derivation", "ops.data_completion_intent"))
    contract = p.row("definition", "sem.data_operation_definition", "support_contract")
    definition_op = p.row("definition", "sem.data_operation_definition", "operation_id")
    effects = [{"name": "native-rich-knowledge-admission", "authorization": ["exact-rich-consolidation-and-record-policy"], "idempotency": "request-generation/exact-input-population", "fulfillment": "native-publication-receipt"}]
    p.add("ddo_rich_command_eligible", (("definition", "sem.data_operation_definition"),), select(and_(
        definition_op == "rich.admit", p.row("definition", "sem.data_operation_definition", "profile") == "command", contract["capabilities"]["preparation"].astext == "native-publication", contract["capabilities"]["forms"] == _json(["scalar"]), contract["capabilities"]["prepared_factory"]["entrypoint"].astext == "corpus_structure.methods.rich_knowledge.RichKnowledgeAdmission.acquire_port", contract["effects"] == _json(effects), contract["capabilities"]["prepared_factory"]["source_digest"].astext.op("~")("^[0-9a-f]{64}$"), p.row("definition", "sem.data_operation_definition", "implementation_revision").like("implementation-slice:%"),
    )), returns="boolean", sql=True, immutable=True, strict=True, definer=False)
    operation = p.row("r", "ops.data_request", "operation_id")
    completion, output = _value("completion"), _value("output")
    binding = p.row("r", "ops.data_request", "binding")
    preparations = {
        "prepare.external_extraction": ("corpus_structure.methods.external_extraction.RichExtractionInputOperation.acquire_port", "result", "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoExternalExtractionPacket"),
        "locate.external_extraction": ("corpus_structure.methods.external_extraction.RichExtractionPlacementOperation.acquire_port", "result", "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoLocatedExternalExtraction"),
        "rich.consolidate": ("corpus_structure.methods.rich_knowledge.RichKnowledgeConsolidation.acquire_port", "consolidated", "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichConsolidation"),
    }
    producer_selection = (Raise("rich preparation requires its actual operation owner", "23514"),)
    for name, (factory, role, kind) in reversed(tuple(preparations.items())):
        producer_selection = (If(operation == name, (Assign("factory", literal(factory)), Assign("output_role", literal(role)), Assign("output_kind", literal(kind))), producer_selection),)
    output_shape = or_(output["member_id"].astext.is_not(None), cast(output["position"].astext, Integer()).is_distinct_from(0), cast(output["multiplicity"].astext, Integer()).is_distinct_from(1))
    p.add("ddo_rich_require_preparation_producer", (("r", "ops.data_request"), ("completion", "jsonb")), (
        *producer_selection,
        p.lookup("definition", "sem.data_operation_definition", definitions.c.release_id == p.row("r", "ops.data_request", "release_id"), definitions.c.operation_id == operation),
        _reject(or_(
            p.row("definition", "sem.data_operation_definition", "profile").is_distinct_from("derivation"), contract["effects"].is_distinct_from(_json([])), contract["capabilities"]["prepared_factory"]["entrypoint"].astext.is_distinct_from(_value("factory", Text())), contract["capabilities"]["prepared_factory"]["source_digest"].astext.op("~")("^[0-9a-f]{64}$").is_not(True), p.row("definition", "sem.data_operation_definition", "implementation_revision").like("implementation-slice:%").is_not(True), completion["implementation_revision"].astext.is_distinct_from(p.row("definition", "sem.data_operation_definition", "implementation_revision")), p.row("r", "ops.data_request", "recipe").is_distinct_from(p.row("definition", "sem.data_operation_definition", "recipe")), and_(operation == "rich.consolidate", p.row("r", "ops.data_request", "original_source").is_not(None)), completion["inputs"].is_distinct_from(binding["inputs"]), completion["support"].is_distinct_from(binding["support"]), func.jsonb_array_length(func.coalesce(completion["execution_evidence"]["cpu_receipts"], _json([]))) != 1,
        ), "rich preparation requires actual derivation/factory/CPU and declared inputs"),
        _reject(or_(completion["outcome"].astext.is_distinct_from("success"), func.jsonb_array_length(completion["outputs"]) != 1), "rich preparation requires one exact successful conclusion"),
        Assign("output", completion["outputs"][0]),
        _reject(or_(output["role"].astext.is_distinct_from(_value("output_role", Text())), output_shape, ~select(1).select_from(kinds).where(kinds.c.kind_contract == output["product"]["kind_contract"].astext, kinds.c.kind == _value("output_kind", Text()), kinds.c.universe == "ordinary").exists()), "rich preparation differs from its actual whole nominal output"),
    ), (p.local("definition", "sem.data_operation_definition"), p.local("output"), *(p.local(name, "text") for name in ("factory", "output_role", "output_kind"))))
    inputs = _items(binding["inputs"], "input")
    p.add("ddo_rich_require_admission_producer", (("r", "ops.data_request"), ("completion", "jsonb")), (
        p.lookup("definition", "sem.data_operation_definition", definitions.c.release_id == p.row("r", "ops.data_request", "release_id"), definitions.c.operation_id == operation),
        _reject(or_(
            ~func.coalesce(p.row("definition", "sem.data_operation_definition", "command_class") == "rich", False), completion["implementation_revision"].astext.is_distinct_from(p.row("definition", "sem.data_operation_definition", "implementation_revision")), p.row("r", "ops.data_request", "recipe").is_distinct_from(p.row("definition", "sem.data_operation_definition", "recipe")), p.row("r", "ops.data_request", "original_source").is_not(None), completion["inputs"].is_distinct_from(binding["inputs"]), completion["support"].is_distinct_from(binding["support"]), func.jsonb_array_length(func.coalesce(completion["execution_evidence"]["cpu_receipts"], _json([]))) != 1,
        ), "rich admission requires actual command/effect/factory/CPU and whole declared inputs"),
        _reject(or_(completion["outcome"].astext.is_distinct_from("success"), func.jsonb_array_length(completion["outputs"]) != 1), "rich admission requires one exact successful conclusion"),
        Assign("output", completion["outputs"][0]),
        _reject(or_(output["role"].astext.is_distinct_from("admission"), output_shape,
            ~select(1).select_from(kinds).where(kinds.c.kind_contract == output["product"]["kind_contract"].astext, kinds.c.kind == "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/DdoRichAdmission", kinds.c.universe == "ordinary").exists(),
            select(func.count()).select_from(inputs).where(inputs.c.value["role"].astext == "consolidation").scalar_subquery() != 1,
            select(1).select_from(inputs).where(or_(inputs.c.value["member_id"].astext.is_not(None), cast(inputs.c.value["multiplicity"].astext, Integer()).is_distinct_from(1), inputs.c.value["role"].astext.not_in(("consolidation", "records", "readings", "policy_authorizations")))).exists(),
        ), "rich admission differs from its actual whole populations and nominal output"),
    ), (p.local("definition", "sem.data_operation_definition"), p.local("output")))
    p.add("ddo_rich_admission_dependencies_valid", (("episode", "text"),), (
        CatchDependencyInvalidity((
            SelectInto(select(core_relation_row(requests)).select_from(requests.join(episodes, episodes.c.request_id == requests.c.id)).where(episodes.c.id == _value("episode", Text())), ("r",), strict=True),
            If(operation.not_in(("rich.admit", "rich.consolidate", "prepare.external_extraction", "locate.external_extraction")), (Return(literal(True)),)),
            p.lookup("producing", "ops.data_derivation", episodes.c.id == _value("episode", Text())),
            If(p.row("producing", "ops.data_derivation", "outcome").is_distinct_from("success"), (Return(literal(False)),)),
            p.lookup("intent", "ops.data_completion_intent", intents.c.id == p.row("producing", "ops.data_derivation", "intent_id")),
            Assign("r", func.ops.ddo_require_episode_correspondence(p.row("producing", "ops.data_derivation"), p.row("intent", "ops.data_completion_intent"))),
            Return(literal(True)),
        ), (Return(literal(False)),)),
    ), (p.local("r", "ops.data_request"), p.local("producing", "ops.data_derivation"), p.local("intent", "ops.data_completion_intent")), returns="boolean")


def _retained_completion(p, request_name, reference):
    episodes, intents = p.table("ops.data_derivation"), p.table("ops.data_completion_intent")
    support = _items(reference["support_references"], "support")
    return SelectInto(select(intents.c.payload).select_from(episodes.join(intents, intents.c.id == episodes.c.intent_id)).where(
        episodes.c.request_id == p.row(request_name, "ops.data_request", "id"),
        select(1).select_from(support).where(support.c.value["derivation_id"].astext == episodes.c.id).exists(),
    ), ("item",), strict=True)


def _selected_reference(selected):
    return func.jsonb_build_object("product_id", selected["product_id"].astext, "member_id", literal(None), "kind_contract", selected["kind_contract"].astext, "support_references", selected["support"], type_=JSONB())


def _rich_preparation_programs(p):
    operation = p.row("r", "ops.data_request", "operation_id")
    request, completion = p.row("r", "ops.data_request"), _value("completion")
    p.add("ddo_require_rich_preparation_completion", (("r", "ops.data_request"), ("completion", "jsonb")), (
        If(operation.not_in(("prepare.external_extraction", "locate.external_extraction", "rich.consolidate")), (Return(),)),
        Perform(func.ops.ddo_rich_require_preparation_producer(request, completion)),
        _reject(func.ops.ddo_cpu_reply_output(request, completion).is_distinct_from(func.data.ddo_normalize(completion["outputs"][0]["product"]["body"])), "rich preparation differs from actual original CPU reply and input basis"),
        If(operation == "rich.consolidate", (Perform(func.ops.ddo_rich_require_proposal_inputs(p.row("r", "ops.data_request", "project_id"), func.ops.ddo_cpu_input_basis(request))),)),
    ))
    selected, reference, item = (_value(name) for name in ("selected", "reference", "item"))
    basis, project = _value("basis"), _value("project", Text())
    headers = func.ops.ddo_rich_role_headers(basis).table_valued(column("value", JSONB())).render_derived(name="header")
    loops = []
    for role, request_name, operation_name, factory, message in (
        ("proposals", "located_request", "locate.external_extraction", "corpus_structure.methods.external_extraction.RichExtractionPlacementOperation.acquire_port", "rich proposal differs from actual located CPU output"),
        ("proposal_contexts", "packet_request", "prepare.external_extraction", "corpus_structure.methods.external_extraction.RichExtractionInputOperation.acquire_port", "rich proposal context differs from actual prepared CPU packet"),
    ):
        body = (
            Assign("reference", _selected_reference(selected)),
            Assign(request_name, func.ops.ddo_rich_producing_request(project, reference, operation_name, factory, "result", True)),
            _retained_completion(p, request_name, reference),
            Perform(func.ops.ddo_require_rich_preparation_completion(p.row(request_name, "ops.data_request"), item)),
            _reject(item["outputs"][0]["product"]["body"].is_distinct_from(func.ops.ddo_rich_selected_value(project, basis, role, reference)), message),
        )
        if role == "proposals":
            body += (Perform(func.ops.ddo_rich_require_proposal_context(basis, func.ops.ddo_cpu_input_basis(p.row(request_name, "ops.data_request")))),)
        loops.append(ForQuery(("selected",), select(headers.c.value).where(headers.c.value["role"].astext == role), body))
    p.add("ddo_rich_require_proposal_inputs", (("project", "text"), ("basis", "jsonb")), tuple(loops), (
        *(p.local(name) for name in ("selected", "reference", "item")), p.local("located_request", "ops.data_request"), p.local("packet_request", "ops.data_request"),
    ))


def rich_admission_native_sql(*, target_metadata=None) -> str:
    programs = _RichPrograms(target_metadata)
    _rich_input_programs(programs)
    _rich_producer_programs(programs)
    _rich_preparation_programs(programs)
    return native_sql_script((*programs.output, _rich_completion_sql()))


def _rich_completion_sql() -> str:
    """Remaining exact completion traversals; input and producer authority is model-owned."""
    return r"""




CREATE OR REPLACE FUNCTION ops.ddo_require_rich_admission_completion(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE basis jsonb; admission_meaning jsonb; admission jsonb; consolidated_meaning jsonb; consolidated jsonb;
 consolidation_request ops.data_request; consolidation_basis jsonb; selected jsonb; authorization_request ops.data_request;
 resolution_request ops.data_request; known_request ops.data_request; authorization_episode text;
 resolution_basis jsonb; reference jsonb; decision jsonb; raw_meaning jsonb; resolved_meaning jsonb; known_episode text;
 raw_record jsonb; resolved_record jsonb; resolution_meaning jsonb; report jsonb; policy_meaning jsonb; policy jsonb;
 events jsonb; event jsonb; reports jsonb:='{}'; raw_reports jsonb:='{}'; policies jsonb:='{}'; known_packets jsonb:='{}'; item jsonb; packet jsonb; raw_digest text;
 raw_comparison jsonb; resolved_comparison jsonb; assertion jsonb; family_contract text;
 known_meaning jsonb; known_graph jsonb;
BEGIN
 IF r.operation_id IS DISTINCT FROM 'rich.admit' THEN
 IF EXISTS(SELECT FROM sem.data_operation_definition definition CROSS JOIN LATERAL jsonb_array_elements(definition.support_contract->'effects') effect
 WHERE definition.release_id=r.release_id AND definition.operation_id=r.operation_id AND effect->>'name'='native-rich-knowledge-admission') THEN
 RAISE EXCEPTION 'rich admission effect requires its actual operation owner' USING ERRCODE='23514'; END IF;
 RETURN; END IF;
 PERFORM ops.ddo_rich_require_admission_producer(r,completion);
 basis:=ops.ddo_cpu_input_basis(r);
 admission_meaning:=data.ddo_normalize(completion->'outputs'->0->'product'->'body');
 -- The shared owner authenticates original bytes against result_digest and the
 -- child's independently reconstructed typed basis. No free accepted flag,
 -- regenerated reply text, or preserved receipt with another body is sufficient.
 IF ops.ddo_cpu_reply_output(r,completion) IS DISTINCT FROM admission_meaning THEN
 RAISE EXCEPTION 'rich admission differs from exact CPU decision and graph projection' USING ERRCODE='23514'; END IF;
 admission:=data.ddo_json(admission_meaning);
 consolidated_meaning:=ops.ddo_rich_selected_value(r.project_id,basis,'consolidation',admission->'consolidation');
 consolidated:=data.ddo_json(consolidated_meaning);
 consolidation_request:=ops.ddo_rich_producing_request(r.project_id,admission->'consolidation','rich.consolidate',
 'corpus_structure.methods.rich_knowledge.RichKnowledgeConsolidation.acquire_port','consolidated',true);
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=consolidation_request.id AND EXISTS(SELECT FROM jsonb_array_elements(admission->'consolidation'->'support_references') support WHERE support->>'derivation_id'=producer.id);
 IF ops.ddo_cpu_reply_output(consolidation_request,item) IS DISTINCT FROM consolidated_meaning THEN
 RAISE EXCEPTION 'rich consolidation differs from actual original CPU graph reply' USING ERRCODE='23514'; END IF;
 consolidation_basis:=ops.ddo_cpu_input_basis(consolidation_request);
 IF consolidated->>'version' IS DISTINCT FROM 'rich-consolidation-1' OR consolidated->>'standing' IS DISTINCT FROM 'private-consolidated'
 OR admission->>'version' IS DISTINCT FROM 'rich-admission-1' OR admission->>'standing' IS DISTINCT FROM 'accepted'
 OR ops.ddo_rich_role_population(basis,'records') IS DISTINCT FROM ops.ddo_rich_role_population(consolidation_basis,'records')
 OR ops.ddo_rich_role_population(basis,'readings') IS DISTINCT FROM ops.ddo_rich_role_population(consolidation_basis,'readings') THEN
 RAISE EXCEPTION 'rich admission changes actual consolidated records/readings population or producer custody' USING ERRCODE='23514'; END IF;
 IF admission->>'eligibility_policy_digest' IS NULL
 OR admission->>'eligibility_policy_digest' !~ '^[0-9a-f]{64}$'
 OR admission->>'eligibility_policy_digest' IS DISTINCT FROM consolidated->'eligibility'->>'eligibility_policy_digest'
 OR admission->'selected_fact_ids' IS DISTINCT FROM consolidated->'eligibility'->'selected_fact_ids'
 OR admission->'selected_occurrence_ids' IS DISTINCT FROM consolidated->'eligibility'->'selected_occurrence_ids'
 OR admission->'scientific_representatives' IS DISTINCT FROM consolidated->'eligibility'->'scientific_representatives' THEN
 RAISE EXCEPTION 'rich admission changes actual rule eligibility or its checked policy basis' USING ERRCODE='23514'; END IF;
 PERFORM ops.ddo_rich_require_proposal_inputs(r.project_id,consolidation_basis);
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(consolidation_basis) header(value) WHERE value->>'role'='known_universe' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 known_request:=ops.ddo_rich_producing_request(r.project_id,reference,'rich.admit',
 'corpus_structure.methods.rich_knowledge.RichKnowledgeAdmission.acquire_port','admission',false);
 SELECT producer.id INTO STRICT known_episode FROM ops.data_derivation producer
 WHERE producer.request_id=known_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 IF NOT ops.ddo_rich_admission_dependencies_valid(known_episode) THEN
 RAISE EXCEPTION 'rich known universe lacks actual sealed native admission authority' USING ERRCODE='23514'; END IF;
 SELECT canonical_body INTO STRICT known_meaning FROM kb.data_product
 WHERE id=reference->>'product_id' AND project_id=r.project_id;
 known_graph:=data.ddo_json(known_meaning);
 IF known_graph->>'eligibility_policy_digest' IS DISTINCT FROM admission->>'eligibility_policy_digest'
 OR jsonb_typeof(known_graph->'selected_reading_ids') IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'rich known eligibility requires its actual current policy basis and selection' USING ERRCODE='23514'; END IF;
 -- A previous accepted graph retains its own source/interpretation/support
 -- attribution. Index only exact reading packets after genuine native authority
 -- has been established; these are not new current raw/resolved decisions.
 FOR packet IN SELECT value FROM jsonb_array_elements(data.ddo_field(known_meaning,'members')->1)
 WHERE data.ddo_field(data.ddo_field(value,'body'),'member_type')='["string","source-reading-assertion"]'::jsonb
 AND known_graph->'selected_reading_ids' ? (data.ddo_field(value,'member_id')->>1) LOOP
 known_packets:=known_packets||jsonb_build_object(ops.ddo_digest(data.ddo_normalize(packet)),data.ddo_normalize(packet));
 END LOOP;
 END LOOP;
 -- Exact tagged packet membership preserves every retained field, evidence,
 -- alternative and context. The approved CPU graph owner selects closed
 -- dependencies; native does not implement a second lowering algorithm.
 IF EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(admission_meaning,'members')->1) member
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(consolidated_meaning,'members')->1) original
 WHERE data.ddo_normalize(original)=data.ddo_normalize(member)))
 OR EXISTS(SELECT FROM jsonb_array_elements(admission->'members') member GROUP BY member->>'member_id' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'rich admission changes actual consolidated graph members' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(admission->'policy_authorizations') IS DISTINCT FROM jsonb_array_length(ops.ddo_rich_role_population(basis,'policy_authorizations')) THEN
 RAISE EXCEPTION 'rich policy population differs from actual declared authorizations' USING ERRCODE='23514'; END IF;
 FOR reference IN SELECT value FROM jsonb_array_elements(admission->'policy_authorizations') LOOP
 IF reference->>'member_id' IS NOT NULL OR policies ? (reference->>'product_id') THEN
 RAISE EXCEPTION 'rich policy requires unique whole issued authorizations' USING ERRCODE='23514'; END IF;
 policy_meaning:=ops.ddo_rich_selected_value(r.project_id,basis,'policy_authorizations',reference);
 authorization_request:=ops.ddo_rich_producing_request(r.project_id,reference,'record_policy.authorize',
 'corpus_structure.methods.record_policy.RecordPolicyAuthorization.acquire_port','authorization',false);
 IF NOT EXISTS(SELECT FROM sem.data_kind_contract kind WHERE kind.kind_contract=reference->>'kind_contract'
 AND kind.kind='https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization' AND kind.universe='ordinary') THEN
 RAISE EXCEPTION 'rich policy is not the actual public authorization contract' USING ERRCODE='23514'; END IF;
 SELECT producer.id INTO STRICT authorization_episode FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=authorization_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 -- Consume the sealed public conclusion under its exact selected native issuer.
 -- The evaluator-only completion guard authorizes new issuance, not consumption.
 IF ops.ddo_policy_authority_leaf(authorization_episode) IS NOT TRUE THEN
 RAISE EXCEPTION 'rich policy lacks its authentic issued public authorization' USING ERRCODE='23514'; END IF;
 policies:=policies||jsonb_build_object(reference->>'product_id',jsonb_build_object('reference',reference,'body',data.ddo_json(policy_meaning)));
 END LOOP;
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(consolidation_basis) header(value) WHERE value->>'role'='records' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 PERFORM ops.ddo_rich_producing_request(r.project_id,reference,NULL,NULL,NULL,true);
 SELECT ops.ddo_digest(canonical_body) INTO STRICT raw_digest FROM kb.data_product WHERE id=selected->>'product_id' AND project_id=r.project_id;
 raw_reports:=raw_reports||jsonb_build_object(selected->>'product_id',raw_digest);
 END LOOP;
 -- Prepare each distinct whole resolution report/event index once. All these
 -- dependencies are declared roles and enter the existing canonical lock union.
 FOR selected IN SELECT value FROM ops.ddo_rich_role_headers(consolidation_basis) header(value) WHERE value->>'role'='readings' LOOP
 reference:=jsonb_build_object('product_id',selected->>'product_id','member_id',NULL,'kind_contract',selected->>'kind_contract','support_references',selected->'support');
 resolution_request:=ops.ddo_rich_producing_request(r.project_id,reference,'resolve.m1_readings/declared',
 'corpus_structure.methods.reading_resolution.ReadingResolutionOperation.acquire_port','result',true);
 resolution_basis:=ops.ddo_cpu_input_basis(resolution_request);
 resolution_meaning:=ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'readings',reference);
 SELECT intent.payload INTO STRICT item FROM ops.data_derivation producer
 JOIN ops.data_completion_intent intent ON intent.id=producer.intent_id
 WHERE producer.request_id=resolution_request.id AND EXISTS(SELECT FROM jsonb_array_elements(reference->'support_references') support WHERE support->>'derivation_id'=producer.id);
 IF ops.ddo_cpu_reply_output(resolution_request,item) IS DISTINCT FROM resolution_meaning THEN
 RAISE EXCEPTION 'rich final-event report differs from actual original reading CPU reply' USING ERRCODE='23514'; END IF;
 report:=data.ddo_json(resolution_meaning);
 events:=(report->>'diagnostics_json')::jsonb->'record_policy_events';
 IF jsonb_typeof(events) IS DISTINCT FROM 'array'
 OR EXISTS(SELECT FROM jsonb_array_elements(events) event_row GROUP BY event_row->>'record_id',event_row->>'interpretation_id' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'rich resolution requires unique actual final-event attribution' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_object_agg(data.canonical_json(jsonb_build_array(event_row->>'record_id',event_row->>'interpretation_id')),event_row),'{}') INTO events FROM jsonb_array_elements(events) event_row;
 reports:=reports||jsonb_build_object(reference->>'product_id',jsonb_build_object(
 'inputs',(SELECT coalesce(jsonb_agg(header),'[]') FROM ops.ddo_rich_role_headers(resolution_basis) header),'release_id',resolution_request.release_id,'recipe',resolution_request.recipe,'events',events));
 END LOOP;
 -- The decision census covers every actual raw record AND resolved record,
 -- including explicit unavailable resolutions and uncheckable/low-score events.
 -- An empty report has no fake record member.
 IF EXISTS(SELECT FROM ops.ddo_rich_role_headers(consolidation_basis) bound
 JOIN kb.data_product_member member ON member.product_id=bound->>'product_id'
 WHERE bound->>'role'='records' AND data.ddo_field(member.body,'candidate_type')='["string","record"]'::jsonb
 AND (SELECT count(*) FROM jsonb_array_elements(admission->'reading_decisions') judgment
 WHERE judgment->'original'->>'product_id'=member.product_id AND judgment->'original'->>'member_id'=member.member_id)<>1) THEN
 RAISE EXCEPTION 'rich decision census omits or duplicates actual raw records' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM ops.ddo_rich_role_headers(consolidation_basis) bound
 JOIN kb.data_product_member member ON member.product_id=bound->>'product_id'
 WHERE bound->>'role'='readings' AND data.ddo_field(member.body,'candidate_type')='["string","record"]'::jsonb
 AND (SELECT count(*) FROM jsonb_array_elements(admission->'reading_decisions') judgment
 WHERE judgment->'resolved'->>'product_id'=member.product_id AND judgment->'resolved'->>'member_id'=member.member_id)<>1) THEN
 RAISE EXCEPTION 'rich decision census omits or duplicates actual resolved records' USING ERRCODE='23514'; END IF;
 FOR decision IN SELECT value FROM jsonb_array_elements(admission->'reading_decisions') LOOP
 raw_meaning:=ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'records',decision->'original');
 raw_record:=data.ddo_json(raw_meaning);
 IF raw_record->>'candidate_type' IS DISTINCT FROM 'record' OR decision->'original'->>'member_id' IS NULL
 OR raw_record->>'record_id' IS DISTINCT FROM decision->>'record_id'
 OR raw_record->>'interpretation_id' IS DISTINCT FROM decision->>'source_interpretation_id' THEN
 RAISE EXCEPTION 'rich decision relabels actual original record attribution' USING ERRCODE='23514'; END IF;
 IF decision->'resolution'='null'::jsonb OR decision->'resolved'='null'::jsonb THEN
 IF decision->'resolution' IS DISTINCT FROM 'null'::jsonb OR decision->'resolved' IS DISTINCT FROM 'null'::jsonb
 OR decision->>'outcome' IS DISTINCT FROM 'not-checkable' OR decision->>'reason_code' IS DISTINCT FROM 'resolution-unavailable'
 OR decision->>'assertion_member_id' IS NOT NULL THEN
 RAISE EXCEPTION 'rich missing resolution must remain explicitly uncheckable' USING ERRCODE='23514'; END IF;
 CONTINUE; END IF;
 resolved_meaning:=ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'readings',decision->'resolved');
 PERFORM ops.ddo_rich_selected_value(r.project_id,consolidation_basis,'readings',decision->'resolution');
 resolved_record:=data.ddo_json(resolved_meaning);
 report:=reports->(decision->'resolution'->>'product_id');
 IF report IS NULL OR decision->'resolved'->>'product_id' IS DISTINCT FROM decision->'resolution'->>'product_id'
 OR decision->'resolution'->>'member_id' IS NOT NULL OR decision->'original'->>'member_id' IS NULL OR decision->'resolved'->>'member_id' IS NULL
 OR raw_record->>'candidate_type' IS DISTINCT FROM 'record' OR resolved_record->>'candidate_type' IS DISTINCT FROM 'record'
 OR raw_record->>'record_id' IS DISTINCT FROM decision->>'record_id' OR resolved_record->>'record_id' IS DISTINCT FROM decision->>'record_id'
 OR raw_record->>'interpretation_id' IS DISTINCT FROM decision->>'source_interpretation_id'
 OR resolved_record->>'interpretation_id' IS DISTINCT FROM decision->>'interpretation_id'
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(report->'inputs') input
 WHERE input->>'role'='candidates' AND input->>'product_id'=decision->'original'->>'product_id'
 AND input->>'member_id' IS NULL
 AND ops.ddo_rich_support_population(input->'support')=ops.ddo_rich_support_population(decision->'original'->'support_references')) THEN
 RAISE EXCEPTION 'rich decision relabels actual raw/resolved member and producing report custody' USING ERRCODE='23514'; END IF;
 SELECT jsonb_build_array('mapping',jsonb_agg(pair ORDER BY (pair->>0) COLLATE "C")) INTO raw_comparison FROM jsonb_array_elements(raw_meaning->1) pair WHERE pair->>0 NOT IN ('interpretation_id','computation_dependencies');
 SELECT jsonb_build_array('mapping',jsonb_agg(pair ORDER BY (pair->>0) COLLATE "C")) INTO resolved_comparison FROM jsonb_array_elements(resolved_meaning->1) pair WHERE pair->>0 NOT IN ('interpretation_id','computation_dependencies');
 IF raw_comparison IS DISTINCT FROM resolved_comparison
 OR NOT (data.ddo_field(resolved_meaning,'computation_dependencies')->1 @>
 jsonb_build_array(jsonb_build_array('string','raw-candidate-result:'||(raw_reports->>(decision->'original'->>'product_id')))))
 OR EXISTS(
 SELECT FROM jsonb_array_elements(data.ddo_field(raw_meaning,'computation_dependencies')->1) dependency
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(resolved_meaning,'computation_dependencies')->1) retained WHERE retained=dependency)) THEN
 RAISE EXCEPTION 'rich resolved reading changes complete original fields/evidence/alternatives' USING ERRCODE='23514'; END IF;
 IF decision->'authorization'<>'null'::jsonb
 AND decision->'authorization' IS DISTINCT FROM policies->(decision->'authorization'->>'product_id')->'reference' THEN
 RAISE EXCEPTION 'rich decision references authority outside actual declared issuer population' USING ERRCODE='23514'; END IF;
 IF decision->>'outcome' IN ('accepted','below-threshold') THEN
 policy:=policies->(decision->'authorization'->>'product_id')->'body';
 event:=report->'events'->data.canonical_json(jsonb_build_array(decision->>'record_id',decision->>'interpretation_id'));
 family_contract:=ops.ddo_rich_family_contract(report->>'release_id',resolved_record->>'contract');
 IF policy IS NULL OR decision->'authorization' IS DISTINCT FROM policies->(decision->'authorization'->>'product_id')->'reference'
 OR event IS NULL OR event->>'outcome' IS DISTINCT FROM 'completed'
 OR event->>'feature_input_digest' IS DISTINCT FROM decision->>'feature_input_digest'
 OR event->>'feature_instance_digest' IS DISTINCT FROM decision->>'feature_instance_digest'
 OR event->>'event_procedure' IS DISTINCT FROM decision->>'event_procedure'
 OR policy->>'feature_instance_digest' IS DISTINCT FROM decision->>'feature_instance_digest'
 OR policy->>'event_procedure' IS DISTINCT FROM decision->>'event_procedure'
 OR policy->>'family' IS DISTINCT FROM resolved_record->>'family'
 OR policy->>'family_contract' IS DISTINCT FROM family_contract
 OR family_contract IS DISTINCT FROM ops.ddo_rich_family_contract(r.release_id,resolved_record->>'contract')
 OR policy->>'reading_recipe' IS DISTINCT FROM report->>'recipe'
 OR policy->'applicability'->>'project_id' IS DISTINCT FROM r.project_id
 OR encode(sha256(convert_to(event->>'feature_input_canonical_json','UTF8')),'hex') IS DISTINCT FROM event->>'feature_input_digest' THEN
 RAISE EXCEPTION 'rich decision lacks exact issued policy/current family/recipe and unique sealed feature event' USING ERRCODE='23514'; END IF;
 END IF;
 IF decision->>'outcome'='accepted' THEN
 SELECT member INTO STRICT assertion FROM jsonb_array_elements(admission->'members') member WHERE member->>'member_id'=decision->>'assertion_member_id';
 IF assertion->'body'->>'member_type' IS DISTINCT FROM 'source-reading-assertion'
 OR assertion->'body'->'original' IS DISTINCT FROM decision->'original'
 OR assertion->'body'->'resolution' IS DISTINCT FROM decision->'resolution'
 OR assertion->'body'->'resolved' IS DISTINCT FROM decision->'resolved'
 OR assertion->'body'->>'record_id' IS DISTINCT FROM decision->>'record_id'
 OR assertion->'body'->>'source_interpretation_id' IS DISTINCT FROM decision->>'source_interpretation_id'
 OR assertion->'body'->>'interpretation_id' IS DISTINCT FROM decision->>'interpretation_id' THEN
 RAISE EXCEPTION 'rich accepted assertion differs from actual complete reading decision' USING ERRCODE='23514'; END IF;
 ELSIF decision->>'assertion_member_id' IS NOT NULL THEN
 RAISE EXCEPTION 'rich rejected reading cannot retain an accepted assertion' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(data.ddo_field(admission_meaning,'members')->1) member_meaning
 WHERE data.ddo_field(data.ddo_field(member_meaning,'body'),'member_type')='["string","source-reading-assertion"]'::jsonb
 AND (SELECT count(*) FROM jsonb_array_elements(admission->'reading_decisions') judgment WHERE judgment->>'outcome'='accepted' AND judgment->>'assertion_member_id'=data.ddo_field(member_meaning,'member_id')->>1)<>1
 AND NOT ops.ddo_rich_carried_reading(member_meaning,known_packets)) THEN
 RAISE EXCEPTION 'rich accepted graph has no exact actual reading decision' USING ERRCODE='23514'; END IF;
 IF jsonb_typeof(admission->'selected_reading_ids') IS DISTINCT FROM 'array'
 OR (SELECT coalesce(jsonb_agg(member->>'member_id' ORDER BY (member->>'member_id') COLLATE "C"),'[]')
 FROM jsonb_array_elements(admission->'members') member
 WHERE member->'body'->>'member_type'='source-reading-assertion') IS DISTINCT FROM
 (SELECT coalesce(jsonb_agg(value ORDER BY value COLLATE "C"),'[]')
 FROM jsonb_array_elements_text(admission->'selected_reading_ids')) THEN
 RAISE EXCEPTION 'rich selected readings differ from actual retained assertion packets' USING ERRCODE='23514'; END IF;
END $rich$;

REVOKE ALL ON FUNCTION ops.ddo_require_rich_admission_completion(ops.data_request,jsonb) FROM PUBLIC;
"""
