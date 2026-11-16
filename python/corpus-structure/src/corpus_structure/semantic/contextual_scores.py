"""Exact native score observations consumed separately from CPU RRF/relationships."""

from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass
from typing import Any

SCORE_VERSION = "contextual-native-scores-2"


def score_product(inputs, query, rows, *, linguistic_observation):
    """Retain actual PostgreSQL float8 observations without a JSON number conversion."""
    from .contextual_linguistics import checked_linguistic_observation, linguistic_source_value

    observation = checked_linguistic_observation(linguistic_observation)
    membership = tuple(sorted(row.target_id for row in rows if row.kind == "membership"))
    if membership != inputs.inventory.target_ids:
        raise ValueError("eligible inventory vector membership is incomplete or duplicated")
    hits = []
    for row in rows:
        if row.kind == "membership":
            continue
        if (
            row.kind != "hit"
            or row.channel not in {"alias", "lexical", "dense"}
            or row.score is None
            or not math.isfinite(row.score)
        ):
            raise ValueError("native retrieval hit lacks its finite channel score")
        hits.append(
            dict(
                channel=row.channel,
                target_id=row.target_id,
                rank=row.rank,
                score_float8_hex=struct.pack(">d", row.score).hex(),
            )
        )
    return dict(
        version=SCORE_VERSION,
        inventory_id=inputs.inventory.inventory_id,
        profile_id=inputs.profile.profile_id,
        occurrence_id=query["occurrence_id"],
        query_vector_id=inputs.query_vector.vector_id,
        lexical_query=query["lexical_query"],
        linguistic_observation=linguistic_source_value(observation),
        membership=list(membership),
        hits=hits,
    )


def query_contextual_scores(connection, inputs, query, policy, *, numerical_policy):
    from pgvector.sqlalchemy import VECTOR
    from sqlalchemy import Integer, Text, bindparam, cast, literal
    from sqlalchemy.dialects.postgresql import ARRAY

    from .contextual_retrieval import contextual_score_statement
    from .contextual_linguistics import observe_linguistic_context

    numerical_policy.require_runtime(connection)
    observation = observe_linguistic_context(connection)
    if not query["lexical_query"].strip() or not 1 <= policy["budget"] <= policy["channel_budget"]:
        raise ValueError("native scores require a nonempty query and bounded candidate budgets")
    statement = contextual_score_statement(
        inputs.relation,
        inventory_id=bindparam("inventory_id", inputs.inventory.inventory_id, type_=Text),
        profile_id=bindparam("profile_id", inputs.profile.profile_id, type_=Text),
        target_ids=bindparam("target_ids", list(inputs.inventory.target_ids), type_=ARRAY(Text)),
        query_vector=cast(
            bindparam(
                "query_vector",
                list(inputs.query_vector.values),
                type_=VECTOR(inputs.profile.dimension),
            ),
            VECTOR(inputs.profile.dimension),
        ),
        lexical_query=bindparam("lexical_query", query["lexical_query"], type_=Text),
        channel_budget=bindparam("channel_budget", policy["channel_budget"], type_=Integer),
        text_configuration=literal(numerical_policy.text_configuration),
    )
    # An explicitly empty inventory has a declared empty relation; SQL VALUES
    # requires a row type, so no query is needed for its proven empty population.
    rows = tuple(connection.execute(statement)) if inputs.inventory.targets else ()
    return score_product(inputs, query, rows, linguistic_observation=observation.model_dump())


def candidates_from_scores(inputs, scores, query, policy, *, numerical_policy):
    from .contextual_retrieval import ChannelHit, fuse_candidates
    from .contextual_linguistics import checked_linguistic_observation
    from .observations import source_python

    if set(scores) != {
        "version",
        "inventory_id",
        "profile_id",
        "occurrence_id",
        "query_vector_id",
        "lexical_query",
        "linguistic_observation",
        "membership",
        "hits",
    } or (
        scores["version"],
        scores["inventory_id"],
        scores["profile_id"],
        scores["occurrence_id"],
        scores["query_vector_id"],
        scores["lexical_query"],
        tuple(scores["membership"]),
    ) != (
        SCORE_VERSION,
        inputs.inventory.inventory_id,
        inputs.profile.profile_id,
        query["occurrence_id"],
        inputs.query_vector.vector_id,
        query["lexical_query"],
        inputs.inventory.target_ids,
    ):
        raise ValueError(
            "native scores differ from exact selected query/profile/inventory membership"
        )
    checked_linguistic_observation(source_python(scores["linguistic_observation"]))
    channels = {name: [] for name in ("alias", "lexical", "dense")}
    previous = None
    for hit in scores["hits"]:
        if (
            set(hit) != {"channel", "target_id", "rank", "score_float8_hex"}
            or hit["channel"] not in channels
        ):
            raise ValueError("native score row differs from the declared scoring channels")
        key = hit["channel"], hit["rank"], hit["target_id"]
        if previous is not None and key <= previous:
            raise ValueError("native score channels differ from exact ordered membership")
        previous = key
        channel = channels[hit["channel"]]
        lexical = hit["score_float8_hex"]
        if (
            type(lexical) is not str
            or not re.fullmatch(r"[0-9a-f]{16}", lexical)
            or (type(hit["rank"]) is not int or hit["rank"] != len(channel) + 1)
        ):
            raise ValueError("native score lacks its exact float8 observation/contiguous rank")
        score = struct.unpack(">d", bytes.fromhex(lexical))[0]
        if not math.isfinite(score):
            raise ValueError("native score is nonfinite")
        channel.append(ChannelHit(hit["target_id"], score))
    return fuse_candidates(
        occurrence_id=query["occurrence_id"],
        query=inputs.query_vector,
        inventory=inputs.inventory,
        channels=channels,
        budget=policy["budget"],
        channel_budget=policy["channel_budget"],
        lexical_query=query["lexical_query"],
        numerical_policy=numerical_policy,
    )


def execute_contextual_retrieval_kernel(
    input_basis: list, numerical_policy: dict, *, witnessed: bool, check_active
) -> dict:
    from .contextual_numerics import RetrievalNumericalPolicy
    from .contextual_operations import finish_contextual_retrieval, prepare_contextual_retrieval
    from .contextual_witnesses import STANDING, contextual_input_reference
    from .data_operation_cpu_basis import cpu_authority_reply, cpu_basis_values

    expected_roles = {"query", "inventory", "vectors", "policy", "scores"} | (
        {"witnesses"} if witnessed else set()
    )
    roles, context = cpu_basis_values(input_basis, scalar_roles=tuple(sorted(expected_roles)), set_roles=())
    values = {name: rows[0].body for name, rows in roles.items()}
    query, scores = values.pop("query"), values.pop("scores")
    binding = values.pop("witnesses") if witnessed else None
    pin = query["source_pin"]
    query_context = roles["query"][0].context
    if query_context != context or (pin["project_id"], pin["original_source"]) != (
        query_context.project_id,
        query_context.original_source,
    ):
        raise ValueError(
            "contextual query differs from its actual selected product/original context"
        )
    inputs = prepare_contextual_retrieval(query=query, **values, check_active=check_active)
    if binding is not None:
        from dataclasses import replace

        from pydantic import TypeAdapter

        from .contextual_links import RelationshipWitness
        from .declared_structural_references import DeclaredProductRef
        from .observations import source_python

        if (
            binding["standing"] != STANDING
            or binding["support_state"] != "unassessed"
            or (
                DeclaredProductRef.model_validate(binding["query_input"])
                != contextual_input_reference(roles["query"][0])
                or DeclaredProductRef.model_validate(binding["inventory_input"])
                != contextual_input_reference(roles["inventory"][0])
            )
        ):
            raise ValueError(
                "authored witness binding differs from exact query/inventory or private unassessed standing"
            )
        witnesses = TypeAdapter(tuple[RelationshipWitness, ...]).validate_python(
            source_python(binding["witnesses"])
        )
        if any(value.support_state != "unassessed" for value in witnesses):
            raise ValueError(
                "authored witness assertion cannot manufacture assessed source support"
            )
        inputs = replace(inputs, witnesses=witnesses)
    numerics = RetrievalNumericalPolicy.model_validate(numerical_policy)
    candidates = candidates_from_scores(
        inputs, scores, query, values["policy"], numerical_policy=numerics
    )
    product = finish_contextual_retrieval(inputs, candidates, query, check_active=check_active)
    if binding is not None:
        product.update(
            witness_input=contextual_input_reference(roles["witnesses"][0]).model_dump(
                mode="python", exclude_none=True
            ),
            witness_standing=STANDING,
            support_state="unassessed",
        )
    return cpu_authority_reply(input_basis, product)


def execute_scoring_profile(receiver, query, inventory, vectors, policy):
    return receiver.execute(query, inventory, vectors, policy)


@dataclass
class ContextualScoringPlan:
    prepared: Any
    numerical_policy: Any
    port: Any = None

    def plan(self, arguments, *, binding, check_active, execution_owner):
        from corpus_structure.core.method import PreparedWork

        from .contextual_operations import prepare_contextual_retrieval
        from .data_operation_json import json_bytes
        from .data_operation_prepared_call import PreparedCallResult

        values = {
            name: arguments.arguments[name] for name in ("query", "inventory", "vectors", "policy")
        }
        inputs = prepare_contextual_retrieval(**values, check_active=check_active)

        def compute():
            self.port._verify()
            check_active()
            with execution_owner.engine.begin() as connection:
                product = query_contextual_scores(
                    connection,
                    inputs,
                    values["query"],
                    values["policy"],
                    numerical_policy=self.numerical_policy,
                )
            check_active()
            self.port._verify()
            checked = self.prepared.validate_json(
                "DdoContextualNativeScores", json_bytes(product)
            ).model_dump(mode="python", exclude_unset=True)
            # This is a native observation, authenticated at completion. A thread
            # executing the Core query is not presented as a CPU receipt.
            return PreparedCallResult(checked)

        (result,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        return result


def resolve_scoring_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.contextual_scoring import ContextualScoringOperation

    from .contextual_numerics import RetrievalNumericalPolicy
    from .contextual_operations import (
        contextual_numerical_asset,
        contextual_operation_sources,
        contextual_retrieval_assets,
    )
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if (
        selected.semantic_id != ContextualScoringOperation.__data_operation__["id"]
        or selected.numerical_policy is None
    ):
        raise PortRefusal("native scoring lacks its actual declared producer/numerical policy")
    numerics = RetrievalNumericalPolicy.model_validate_json(selected.numerical_policy.body)
    receiver = ContextualScoringOperation(None)
    plan = ContextualScoringPlan(prepared, numerics)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.contextual_scores.ContextualScoringPlan.plan",
        authorize,
        (contextual_retrieval_assets(), contextual_numerical_asset(numerics)),
        contextual_operation_sources(numerics),
        functions=(
            (
                "corpus_structure.semantic.contextual_scores.query_contextual_scores",
                query_contextual_scores,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
