"""Scoped producer facts for admitted binding rows, with no protected input bodies."""

from sqlalchemy import Text, and_, case, column, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by


def producer_cpu_witness(profile, effects, payload):
    """The same declared CPU basis serves native enforcement and observation."""
    empty = literal("[]").cast(JSONB)
    return and_(
        profile.is_not_distinct_from("derivation"),
        effects.is_not_distinct_from(empty),
        func.jsonb_array_length(func.coalesce(payload["execution_evidence"]["cpu_receipts"], empty))
        == 1,
    )


def selected_producer_contract(metadata, selected, *, body_eligible):
    """Observe only the producer of a row already bounded by native read authority.

    Return identifiers and correspondence facts. Protected bodies, receipt payloads,
    invocation parameters and transitive support stay with their existing owners.
    """
    episodes = metadata.tables["ops.data_derivation"].alias("observed_producer_episode")
    requests = metadata.tables["ops.data_request"].alias("observed_producer_request")
    definitions = metadata.tables["sem.data_operation_definition"].alias(
        "observed_producer_definition"
    )
    intents = metadata.tables["ops.data_completion_intent"].alias("observed_producer_intent")
    receipts = metadata.tables["ops.data_publication_receipt"].alias("observed_producer_receipt")
    grants = metadata.tables["sem.data_operation_effect_grant"].alias("observed_producer_grant")
    receipt = (
        select(1)
        .select_from(receipts)
        .where(
            receipts.c.derivation_id == episodes.c.id,
            receipts.c.intent_id == episodes.c.intent_id,
        )
        .correlate(episodes)
        .exists()
    )
    effects = (
        select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(grants.c.effect, grants.c.effect)),
                literal("[]").cast(JSONB),
            )
        )
        .where(
            grants.c.release_id == definitions.c.release_id,
            grants.c.operation_id == definitions.c.operation_id,
            func.ops.ddo_privileged_effect_admitted(definitions.table_valued(), grants.c.effect),
        )
        .correlate(definitions)
        .scalar_subquery()
    )
    record = func.jsonb_build_object(
        "version",
        "selected-producer-contract-v1",
        "derivation_id",
        episodes.c.id,
        "release_id",
        episodes.c.release_id,
        "runtime_id",
        episodes.c.runtime_id,
        "publication_receipt",
        receipt,
        "cpu_receipt",
        producer_cpu_witness(
            definitions.c.profile, definitions.c.support_contract["effects"], intents.c.payload
        ),
        "admitted_effects",
        effects,
        "validity_families",
        func.to_jsonb(definitions.c.validity_families),
        "reference_inputs",
        _selected_reference_inputs(
            metadata, selected, episodes, requests, definitions, body_eligible
        ),
    )
    return (
        select(record)
        .select_from(
            episodes.join(requests, requests.c.id == episodes.c.request_id)
            .join(
                definitions,
                and_(
                    definitions.c.release_id == episodes.c.release_id,
                    definitions.c.operation_id == requests.c.operation_id,
                ),
            )
            .outerjoin(intents, intents.c.id == episodes.c.intent_id)
        )
        .where(episodes.c.id == selected.c.episode_id)
        .correlate(selected)
        .scalar_subquery()
    )


def _selected_reference_inputs(metadata, selected, episodes, requests, definitions, body_eligible):
    """Expose only scalar original addresses selected by this exact current use."""
    inputs = metadata.tables["ops.data_derivation_input"].alias("reference_producer_input")
    uses = metadata.tables["ops.demand_use"].alias("reference_producer_use")
    products = metadata.tables["kb.data_product"].alias("reference_input_product")
    members = metadata.tables["kb.data_product_member"].alias("reference_input_member")
    empty = literal("[]").cast(JSONB)
    targets = (
        func.jsonb_array_elements(
            func.coalesce(definitions.c.support_contract["reference_targets"], empty)
        )
        .table_valued(column("value", JSONB()))
        .render_derived(name="declared_producer_reference_targets")
    )
    currently_selected = (
        func.jsonb_array_elements(uses.c.selection["inputs"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="current_producer_reference_inputs")
    )
    target = targets.c.value
    declared = (
        select(1)
        .select_from(targets)
        .where(
            target["output_role"].astext == selected.c.output_role,
            target["input_role"].astext == inputs.c.role,
            target["occurrence_field"].astext.is_(None),
        )
        .correlate(selected, definitions, inputs)
        .exists()
    )
    pin = currently_selected.c.value
    exact = (
        select(1)
        .select_from(currently_selected)
        .where(
            pin["role"].astext == inputs.c.role,
            pin["position"].astext == inputs.c.position.cast(Text()),
            pin["product_id"].astext == inputs.c.product_id,
            pin["member_id"].astext.is_not_distinct_from(inputs.c.member_id),
        )
        .correlate(uses, inputs)
        .exists()
    )
    kind = func.coalesce(members.c.kind_contract, products.c.kind_contract)
    body = func.coalesce(members.c.body, products.c.canonical_body)
    record = func.jsonb_build_object(
        "role",
        inputs.c.role,
        "product_id",
        inputs.c.product_id,
        "member_id",
        inputs.c.member_id,
        "kind_contract",
        kind,
        "multiplicity",
        inputs.c.multiplicity,
    )
    return (
        select(
            func.coalesce(
                func.jsonb_agg(aggregate_order_by(record, inputs.c.role, inputs.c.position)), empty
            )
        )
        .select_from(
            inputs.join(
                uses,
                and_(
                    uses.c.id == selected.c.use_id, uses.c.derivation_id == inputs.c.derivation_id
                ),
            )
            .join(products, products.c.id == inputs.c.product_id)
            .outerjoin(
                members,
                and_(
                    members.c.product_id == inputs.c.product_id,
                    members.c.member_id == inputs.c.member_id,
                ),
            )
        )
        .where(
            inputs.c.derivation_id == episodes.c.id,
            uses.c.fate == "fulfilled",
            products.c.project_id == requests.c.project_id,
            case((and_(declared, exact), body_eligible(kind, body)), else_=literal(False)),
        )
        .correlate(selected, episodes, requests, definitions)
        .scalar_subquery()
    )
