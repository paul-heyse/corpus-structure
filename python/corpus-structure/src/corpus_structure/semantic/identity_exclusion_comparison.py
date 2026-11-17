"""Observational comparison of explicit typed source constraints in two actual roots."""

from collections import defaultdict
from dataclasses import dataclass

from .data_operation_identity import semantic_value
from .identity import canonical_bytes
from .rich_knowledge_contracts import DdoRichAdmission, DdoRichEntity, DdoRichIdentityExclusion
from .rich_queries import RichQueryRefused, RichQueryRow


@dataclass(frozen=True)
class ConstraintSnapshot:
    reference: dict
    context: dict
    producer: dict
    constraint_contract: str
    policy: str
    entries: dict


def constraint_snapshot(scope, selected, state) -> ConstraintSnapshot:
    identity = {(item.owner, item.domain): item.key for item in scope.model.identities}
    operation = scope.model.operation(selected.operation_id)
    episode = scope.index.mapping("ops.data_derivation", ("id",))[selected.derivation_id]
    request = scope.index.mapping("ops.data_request", ("id",))[episode["request_id"]]
    namespace = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    if (namespace + "DdoRichIdentityExclusion", "kind") not in identity:
        raise RichQueryRefused(
            "selected root release lacks a current explicit identity-exclusion projection; regenerate"
        )
    entries = defaultdict(list)
    for identifier, body in state.members.items():
        if not isinstance(body, DdoRichIdentityExclusion):
            continue
        original = body.source_members[0]
        key = canonical_bytes([original.product_id, original.member_id]).decode()
        contracts = {}
        for endpoint in (body.left_entity_id, body.right_entity_id):
            if endpoint is not None:
                entity = state.member(endpoint, DdoRichEntity)
                for contract in entity.class_contracts:
                    contracts[state.definition(contract).iri] = contract
        declaration = body.declaration.model_dump(mode="python")
        evidence = declaration.pop("evidence")
        entries[key].append(
            dict(
                member_id=identifier,
                source=original.model_dump(mode="python"),
                declaration=declaration,
                evidence=evidence,
                endpoint_contracts=contracts,
                resolution=dict(
                    left_entity_id=body.left_entity_id,
                    right_entity_id=body.right_entity_id,
                    outcome=body.outcome,
                    reason=body.reason,
                ),
            )
        )
    root = state.graph
    policy = (
        root.eligibility_policy_digest
        if isinstance(root, DdoRichAdmission)
        else root.eligibility.eligibility_policy_digest
    )
    return ConstraintSnapshot(
        selected.reference.model_dump(mode="python"),
        selected.context.identity_record,
        dict(
            operation_id=selected.operation_id,
            definition=identity[selected.operation_id, "definition"],
            recipe=request["recipe"],
            profile=operation.profile,
        ),
        identity[namespace + "DdoRichIdentityExclusion", "kind"],
        policy,
        dict(entries),
    )


def _meanings(rows, name):
    return frozenset(canonical_bytes(semantic_value(row[name])) for row in rows)


def compare_constraint_snapshots(
    before: ConstraintSnapshot,
    after: ConstraintSnapshot,
    *,
    include_unchanged=False,
    max_entries=10000,
):
    keys = sorted(before.entries.keys() | after.entries.keys())
    if len(keys) > max_entries:
        raise RichQueryRefused(
            "identity exclusion comparison exceeds its examined declaration bound"
        )
    scope_equal = canonical_bytes(semantic_value(before.context)) == canonical_bytes(
        semantic_value(after.context)
    )
    contracts_equal = (
        before.constraint_contract == after.constraint_contract
        and before.producer["definition"] == after.producer["definition"]
    )
    for key in keys:
        left, right = before.entries.get(key, []), after.entries.get(key, [])
        unknowns = []
        facets = []
        if not left or not right:
            outcome = "unmatched_unassessed"
            unknowns.append(
                "different-retained-declaration-populations-do-not-establish-source-absence"
            )
        elif not scope_equal:
            outcome = "incomparable_scope"
            unknowns.append("knowledge-subject-or-context-differs")
        elif not contracts_equal or _meanings(left, "endpoint_contracts") != _meanings(
            right, "endpoint_contracts"
        ):
            outcome = "incomparable_contracts"
            unknowns.append("consumed-constraint-entity-or-producer-definition-differs")
        elif any(
            len(_meanings(rows, name)) > 1
            for rows in (left, right)
            for name in ("declaration", "evidence", "resolution")
        ):
            outcome = "ambiguous_projection"
            unknowns.append("one-source-declaration-has-multiple-materialized-meanings")
        else:
            facets = [
                name
                for name in ("declaration", "evidence", "resolution")
                if _meanings(left, name) != _meanings(right, name)
            ]
            if _meanings(left, "source") != _meanings(right, "source"):
                facets.append("support")
            if "declaration" in facets or "evidence" in facets:
                outcome = "inconsistent_projection"
                unknowns.append(
                    "same-immutable-declaration-address-has-conflicting-source-projection"
                )
            elif before.policy != after.policy:
                outcome = "different_policy"
                unknowns.append("captured-eligibility-policy-differs")
            elif any(row["resolution"]["outcome"] != "located" for row in (*left, *right)):
                outcome = "unresolved_observation"
                unknowns.append(
                    "unlocated-or-unresolved-declaration-does-not-establish-a-constraint"
                )
            else:
                outcome = "changed" if facets else "unchanged"
        if outcome == "unchanged" and not include_unchanged:
            continue
        yield RichQueryRow(dict(
                declaration_address=key,
                outcome=outcome,
                facets=facets,
                before=left,
                after=right,
                unknowns=unknowns,
                interpretation="materialized-source-declaration-and-resolution-observations",
                original_source_change="not-established",
            ))
