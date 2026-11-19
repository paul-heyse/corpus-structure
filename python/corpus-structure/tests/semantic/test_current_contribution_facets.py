"""Independent composite projection controls; no native publication is simulated."""

from types import SimpleNamespace

import pytest

from corpus_structure.semantic.contribution_facets import graph_facets
from corpus_structure.semantic.rich_decisions import (
    DdoRichEligibility,
    DdoRichOccurrenceDecision,
    DdoRichRuleFinding,
)
from corpus_structure.semantic.rich_graph_validation import RichWholeInput, read_rich_graph
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAssessment,
    DdoRichConsolidation,
)
from corpus_structure.semantic.rich_queries import RichGraphIndex, RichQueryIndex, RichQueryRefused
from semantic.test_external_rich_extraction import rich_bundle as rich_bundle
from semantic.test_external_rich_extraction import rich_model as rich_model
from semantic.test_external_rich_extraction import rich_prepared as rich_prepared
from semantic.test_rich_identity_exclusions import constraint
from semantic.test_rich_queries import Graph
from semantic.test_rich_queries import query_source as query_source


def selected(graph, index):
    return SimpleNamespace(
        reference=graph.root_input.reference,
        use_id="selected-use",
        output={"role": "admission", "position": 0},
    )


def case(query_source):
    graph = Graph(query_source, {"A": "DistributionFamily", "B": "DistributionFamily"})
    first = graph.add("supported", "A", "special_case_of", "B")
    second = graph.add("unassessed", "B", "limit_of", "A", selected=False)
    finding = DdoRichAssessment(
        member_type="assessment",
        assessment_id="assessment:captured",
        occurrences=("occurrence:supported",),
        rule="captured-rule:warning",
        severity="warning",
        outcome="invalid",
        reason="retained warning, not a rejection",
        evidence_members=(graph.origin,),
    )
    decision = DdoRichOccurrenceDecision(
        member_type="occurrence-decision",
        decision_id="decision:captured",
        occurrence_id="occurrence:supported",
        fact_id=first,
        status="accepted",
        findings=(
            DdoRichRuleFinding(
                rule=finding.rule,
                outcome="failed",
                severity="warning",
                assessment_id=finding.assessment_id,
            ),
        ),
    )
    exclusion = constraint(graph)
    graph.bodies.update({value.assessment_id: value for value in (finding,)})
    graph.bodies[decision.decision_id] = decision
    graph.bodies[exclusion.exclusion_id] = exclusion
    return graph, graph.index(), first, second, exclusion


def test_joined_facets_preserve_warning_selection_premises_and_exact_source_constraint(
    query_source,
):
    graph, index, first, second, exclusion = case(query_source)
    rows = [
        item.value
        for item in graph_facets(
            selected(graph, index), index.state, interpretation=True, assessment=True
        )
    ]
    claims = [
        item["row"]
        for item in rows
        if item["population"] == "interpretation" and item["row"]["reference"]["member_id"] == first
    ]
    assert len(claims) == 1 and claims[0]["meaning"]["selected"] is True
    assert claims[0]["meaning"]["fact"]["predicate"] == query_source[0].expand_name(
        "stat:special_case_of"
    )
    assessed = next(
        item["row"]
        for item in rows
        if item["population"] == "assessment"
        and item["row"]["reference"]["member_id"] == "occurrence:supported"
    )
    assert assessed["availability"] == "observed"
    assert (
        assessed["judgments"][0]["severity"] == "warning"
        and assessed["judgments"][0]["outcome"] == "invalid"
    )
    assert assessed["occurrence_decisions"][0]["status"] == "accepted"
    unknown = next(
        item["row"]
        for item in rows
        if item["population"] == "assessment" and item["row"]["reference"]["member_id"] == second
    )
    assert (
        unknown["availability"] == "unknown"
        and unknown["reason"] == "no-associated-judgment-in-this-selected-root"
    )
    constraint_row = next(
        item["row"]
        for item in rows
        if item["population"] == "interpretation"
        and item["row"]["reference"]["member_id"] == exclusion.exclusion_id
    )
    assert constraint_row["meaning"]["declaration"]["left"]["target"] == "local:A"
    assert constraint_row["meaning"]["left_entity_id"] == "A"
    assert (
        constraint_row["meaning"]["source_members"][0]["member_id"] == "identity_exclusion:separate"
    )


def test_private_interpretation_keeps_actual_eligibility_without_becoming_public_named_knowledge(
    query_source,
):
    graph, index, _, _, _ = case(query_source)
    accepted = index.state.graph
    reference = graph.root_input.reference
    proof = RichWholeInput(reference, accepted)
    eligibility = DdoRichEligibility(
        eligibility_policy_digest=accepted.eligibility_policy_digest,
        selected_fact_ids=accepted.selected_fact_ids,
        selected_occurrence_ids=accepted.selected_occurrence_ids,
        scientific_representatives=accepted.scientific_representatives,
    )
    private = DdoRichConsolidation(
        version="rich-consolidation-1",
        standing="private-consolidated",
        members=accepted.members,
        input_population=(reference,),
        eligibility=eligibility,
    )
    state = read_rich_graph(
        *query_source,
        context=index.state.context,
        graph=private,
        inputs=(reference,),
        whole_inputs=(proof,),
        retained_graphs=(proof,),
    )
    assert RichGraphIndex(state).selected_facts == index.selected_facts
    with pytest.raises(RichQueryRefused, match="accepted whole"):
        RichQueryIndex(state)
    rows = [
        item.value
        for item in graph_facets(
            selected(graph, index),
            state,
            interpretation=True,
            assessment=True,
            member_id="occurrence:supported",
        )
    ]
    assert {item["population"] for item in rows} == {"contribution", "interpretation", "assessment"}
    assert all(item["row"]["standing"] == "private-consolidated" for item in rows)
    assert all(item["row"]["reference"]["member_id"] == "occurrence:supported" for item in rows)


def test_actual_located_proposals_keep_alternatives_coverage_and_unknown_acceptance(
    rich_prepared, rich_model
):
    from copy import deepcopy

    from corpus_structure.methods.llm.cascade import PlacementPolicy
    from corpus_structure.semantic.contribution_facets import LOCATED_KIND, proposal_facets
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.external_extraction import locate_external_extraction
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
    from semantic.proposals_support import batch
    from semantic.test_external_rich_extraction import packet

    original = packet()
    raw = batch()
    raw["unit_ref"] = original["unit_ref"]
    raw["statements"][0]["anchor"] = original["unit_ref"]
    raw["claims"][0]["evidence"][0]["sentence"] = "native_evidence:0"
    raw["claims"].append(dict(deepcopy(raw["claims"][0]), id="c2"))
    raw["alternatives"] = [
        dict(
            id="either", members=["c1", "c2"], faithful=True, reason="actual authored alternatives"
        )
    ]
    body = locate_external_extraction(
        rich_prepared,
        original,
        raw,
        model=rich_model,
        placement_policy=PlacementPolicy(),
        check_active=lambda: None,
    )
    root_kind = next(
        item.key
        for item in rich_model.identities
        if item.domain == "kind" and item.owner == LOCATED_KIND
    )
    # Controlled projection seam only: actual current placement/schema owners,
    # no native publication or CPU custody claim is made by this pure control.
    source = SimpleNamespace(
        body=body,
        reference=DdoRichSelectedMember(
            product_id="located-product",
            member_id=None,
            kind_contract=root_kind,
            support_references=(
                ComputationalSupportReference(
                    derivation_id="located-episode", admission_use_id="located-use"
                ),
            ),
        ),
        use_id="located-use",
        output={"role": "located", "position": 0},
    )
    rows = [
        row.value
        for row in proposal_facets(
            source, rich_prepared, rich_model, interpretation=True, assessment=True
        )
    ]
    alternative = next(
        row["row"]
        for row in rows
        if row["population"] == "interpretation"
        and row["row"]["reference"]["member_id"] == "alternative:either"
    )
    assert [item["member_id"] for item in alternative["related"]] == ["claim:c1", "claim:c2"]
    assert all(item["product_id"] == "located-product" for item in alternative["related"])
    assert (
        alternative["scientific_truth"] == "not-established"
        and alternative["standing"] == "private_proposed"
    )
    assert all(
        row["row"]["availability"] == "unknown" for row in rows if row["population"] == "assessment"
    )
    coverage = [row["row"] for row in rows if row["population"] == "coverage"]
    assert len(coverage) == 6 and all(
        row["source_scope"] == "supplied-authored-response"
        and row["original_source_completeness"] == "unknown"
        for row in coverage
    )
    with pytest.raises(RichQueryRefused, match="nested member-reference bound"):
        list(
            proposal_facets(
                source,
                rich_prepared,
                rich_model,
                interpretation=True,
                assessment=True,
                max_nested_members=1,
            )
        )
