"""Finite original target/vector custody for the actual applicability consumer."""

from sqlalchemy import Text, and_, func, or_, select

from .contextual_admission_native import (
    _ContextualPrograms,
    _field,
    _items,
    _json,
    _plain,
    _reject,
    _text,
    _value,
)
from .native_program import Assign, Perform, Return, SelectInto, core_relation_row
from .validity_programs import input_role, selected_family


def contextual_definition_native_sql(*, target_metadata=None) -> str:
    p = _ContextualPrograms(target_metadata)
    episodes, requests, receipts, outputs, intents = (
        p.table(name)
        for name in (
            "ops.data_derivation",
            "ops.data_request",
            "ops.data_publication_receipt",
            "ops.data_derivation_output",
            "ops.data_completion_intent",
        )
    )
    selected, operation = _value("selected_input"), _value("operation_name", Text())
    supports = _items(_plain(_field(selected, "support")), "reference")
    original = (
        episodes.join(
            requests,
            and_(
                requests.c.id == episodes.c.request_id,
                selected_family(
                    p.model, requests.c.release_id, requests.c.operation_id, "contextual"
                ),
                input_role(p.model, requests.c.release_id, requests.c.operation_id, operation),
            ),
        )
        .join(
            receipts,
            and_(
                receipts.c.derivation_id == episodes.c.id,
                receipts.c.intent_id == episodes.c.intent_id,
            ),
        )
        .join(outputs, outputs.c.derivation_id == episodes.c.id)
    )
    p.add(
        "ddo_contextual_origin_basis",
        (("selected_input", "jsonb"), ("operation_name", "text")),
        (
            SelectInto(
                select(core_relation_row(episodes))
                .select_from(original)
                .where(
                    outputs.c.product_id == _text(selected, "product_id"),
                    or_(
                        outputs.c.member_id.is_(None),
                        outputs.c.member_id == _text(selected, "member_id"),
                    ),
                    outputs.c.multiplicity == 1,
                    episodes.c.outcome == "success",
                    episodes.c.id.in_(
                        select(supports.c.value["derivation_id"].astext).where(
                            supports.c.value["kind"].astext == "computation"
                        )
                    ),
                ),
                ("episode",),
                strict=True,
            ),
            _reject(
                ~func.ops.ddo_contextual_dependencies_valid(
                    p.row("episode", "ops.data_derivation", "id")
                ),
                "contextual definition lineage lacks its authentic sealed producer",
            ),
            p.lookup(
                "request",
                "ops.data_request",
                requests.c.id == p.row("episode", "ops.data_derivation", "request_id"),
            ),
            p.lookup(
                "intent",
                "ops.data_completion_intent",
                intents.c.id == p.row("episode", "ops.data_derivation", "intent_id"),
                intents.c.request_id == p.row("episode", "ops.data_derivation", "request_id"),
                intents.c.generation == p.row("episode", "ops.data_derivation", "generation"),
            ),
            *p.restore("request", "episode", "intent"),
            Return(func.ops.ddo_cpu_input_basis(p.row("request", "ops.data_request"))),
        ),
        (
            p.local("episode", "ops.data_derivation"),
            p.local("request", "ops.data_request"),
            p.local("intent", "ops.data_completion_intent"),
        ),
        returns="jsonb",
    )
    basis, producer_basis, row = (
        _value(name) for name in ("basis", "producer_basis", "selected_row")
    )
    component, relationship, component_id = (
        _value("component_row"),
        _value("relationship_row"),
        _value("component_id", Text()),
    )
    values = _items(_field(producer_basis, "roles")[1], "selected_role")
    p.add(
        "ddo_require_contextual_definition_lineage",
        (("r", "ops.data_request"), ("completion", "jsonb")),
        (
            p.bind(),
            Assign("basis", func.ops.ddo_cpu_input_basis(p.row("original", "ops.data_request"))),
            Assign("component_id", _text(basis, "parameters", "component_id")),
            p.role(basis, "components", "component_row"),
            p.role(basis, "relationship", "relationship_row"),
            _reject(
                or_(
                    component_id.is_(None),
                    _field(component, "member_id").is_distinct_from(_json(["null"])),
                    _field(relationship, "member_id").is_distinct_from(_json(["null"])),
                ),
                "contextual applicability requires exact whole component and relationship inputs",
            ),
            Perform(func.ops.ddo_definition_component_basis(component)),
            Assign(
                "producer_basis",
                func.ops.ddo_contextual_origin_basis(relationship, "vectors"),
            ),
            p.role(producer_basis, "vectors", "selected_row"),
            Assign(
                "producer_basis",
                func.ops.ddo_contextual_origin_basis(row, "targets"),
            ),
            SelectInto(
                select(values.c.value).where(
                    _text(values.c.value, "role") == "targets",
                    _text(values.c.value, "body", "vector", "object_id") == component_id,
                ),
                ("selected_row",),
                strict=True,
            ),
            Assign(
                "producer_basis",
                func.ops.ddo_contextual_origin_basis(row, "target"),
            ),
            p.role(producer_basis, "target", "selected_row"),
            Assign(
                "producer_basis",
                func.ops.ddo_contextual_origin_basis(row, "target"),
            ),
            p.role(producer_basis, "target", "selected_row"),
            Assign(
                "producer_basis",
                func.ops.ddo_contextual_origin_basis(row, "report"),
            ),
            _reject(
                func.ops.ddo_rich_role_population(producer_basis, "report").is_distinct_from(
                    func.ops.ddo_rich_role_population(basis, "components")
                ),
                "contextual applicability substitutes the original component report/member/producer support",
            ),
        ),
        (
            p.local("original", "ops.data_request", p.row("r", "ops.data_request")),
            *(
                p.local(name)
                for name in (
                    "basis",
                    "producer_basis",
                    "selected_row",
                    "component_row",
                    "relationship_row",
                )
            ),
            p.local("component_id", "text"),
        ),
    )
    return p.script()
