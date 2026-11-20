"""Exact declaration correspondence, separate facets, and explicit unknown populations."""

from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.semantic.identity_exclusion_comparison import (
    ConstraintSnapshot,
    compare_constraint_snapshots,
)
from corpus_structure.semantic.refusal_types import RichQueryRefused


def entry(local="separate"):
    return dict(
        member_id="constraint:actual",
        source=dict(
            product_id="source-product",
            member_id="identity_exclusion:" + local,
            kind_contract="kind:proposal",
            support_references=[
                dict(
                    kind="computation",
                    derivation_id="source-episode",
                    admission_use_id="source-use",
                )
            ],
        ),
        declaration=dict(
            local_id=local,
            unit_ref="unit:actual",
            left={"kind": "local", "target": "mention:A"},
            right={"kind": "local", "target": "mention:B"},
            reason="source distinguishes both",
        ),
        evidence=[dict(role="primary", outcome="located", locator="native:source", start=2, end=9)],
        endpoint_contracts={"urn:actual:Entity": "kind:entity"},
        resolution=dict(
            left_entity_id="A",
            right_entity_id="B",
            outcome="located",
            reason="actual resolved endpoints",
        ),
    )


def snapshot(*entries):
    from corpus_structure.semantic.identity import canonical_bytes

    grouped = {}
    for row in entries:
        source = row["source"]
        grouped.setdefault(
            canonical_bytes([source["product_id"], source["member_id"]]).decode(), []
        ).append(row)
    # Controlled observations for this pure comparator only; no prepared model,
    # publication receipt, CPU authority or native result is invented.
    return ConstraintSnapshot(
        reference={"product_id": "root"},
        context={"project_id": "p", "subject": "universe"},
        producer={"definition": "definition:actual", "recipe": "recipe:actual"},
        constraint_contract="kind:constraint",
        policy="policy:actual",
        entries=grouped,
    )


def changes(left, right, **kwargs):
    return [item.value for item in compare_constraint_snapshots(left, right, **kwargs)]


def test_resolution_changes_do_not_relabel_source_meaning_or_collapse_endpoint_pairs():
    old = entry()
    new = deepcopy(old)
    new["resolution"]["left_entity_id"] = "A-resolved-differently"
    other = entry("another-declaration")
    result = changes(snapshot(old, other), snapshot(new, other))
    assert (
        len(result) == 1
        and result[0]["outcome"] == "changed"
        and result[0]["facets"] == ["resolution"]
    )
    assert result[0]["declaration_address"] == '["source-product","identity_exclusion:separate"]'
    assert result[0]["original_source_change"] == "not-established"
    assert changes(snapshot(other, old), snapshot(old, other)) == []


@pytest.mark.parametrize(
    "change,outcome",
    [
        ("scope", "incomparable_scope"),
        ("contract", "incomparable_contracts"),
        ("definition", "incomparable_contracts"),
        ("policy", "different_policy"),
        ("unlocated", "unresolved_observation"),
        ("ambiguous", "ambiguous_projection"),
    ],
)
def test_changed_context_unknown_evidence_and_conflicting_materializations_remain_explicit(
    change, outcome
):
    old = entry()
    new = deepcopy(old)
    left = snapshot(old)
    right = snapshot(new)
    if change == "scope":
        right = replace(right, context={"project_id": "p", "subject": "other-universe"})
    elif change == "contract":
        right = replace(right, constraint_contract="kind:other-constraint")
    elif change == "definition":
        right = replace(
            right, producer={"definition": "other-definition", "recipe": "other-recipe"}
        )
    elif change == "policy":
        right = replace(right, policy="different-policy")
    elif change == "unlocated":
        new["resolution"]["outcome"] = "unlocated"
        right = snapshot(new)
    else:
        new["resolution"]["right_entity_id"] = "C"
        right = snapshot(old, new)
    result = changes(left, right)
    assert result[0]["outcome"] == outcome and result[0]["unknowns"]


def test_changed_source_support_is_attributed_and_new_addresses_never_prove_addition_or_removal():
    old = entry()
    new = deepcopy(old)
    new["source"]["support_references"][0]["derivation_id"] = "other-source-episode"
    result = changes(snapshot(old), snapshot(new))
    assert result[0]["outcome"] == "changed" and result[0]["facets"] == ["support"]
    new["source"]["product_id"] = "other-source-product"
    result = changes(snapshot(old), snapshot(new))
    assert len(result) == 2 and all(row["outcome"] == "unmatched_unassessed" for row in result)
    assert not any(row["outcome"] in {"added", "removed"} for row in result)


def test_same_immutable_address_with_changed_source_projection_is_a_bounded_diagnostic():
    old = entry()
    new = deepcopy(old)
    new["declaration"]["reason"] = "different projected source reason"
    new["evidence"][0]["start"] = 3
    result = changes(snapshot(old), snapshot(new))
    assert result[0]["outcome"] == "inconsistent_projection"
    assert (
        result[0]["facets"] == ["declaration", "evidence"]
        and result[0]["before"] == [old]
        and result[0]["after"] == [new]
    )
    with pytest.raises(RichQueryRefused, match="examined declaration"):
        changes(snapshot(old, entry("other")), snapshot(new), max_entries=1)
