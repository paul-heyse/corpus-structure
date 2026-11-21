"""Scoped producer facts for admitted binding rows, with no protected input bodies."""

from sqlalchemy import and_, func, literal, select
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


def selected_producer_contract(metadata, selected):
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
