"""Pure rich kernels over explicitly unadmitted authored input values.

No native admission or CPU evidence is fabricated; native journeys cover custody.
"""

from decimal import Decimal

from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_ports import _untrusted_value
from corpus_structure.semantic.data_operation_support import AuthoredFactSupportReference
from corpus_structure.semantic.rich_consolidation import consolidate_rich_knowledge
from corpus_structure.semantic.rich_cpu_inputs import RichKernelInputs
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAlternative,
    DdoRichAuthoredPacket,
    DdoRichAuthoredProposition,
    DdoRichAuthoredPropositions,
    DdoRichEntity,
    DdoRichOccurrence,
)
from corpus_structure.semantic.rich_policy_binding import rich_policy_value
from semantic.test_rich_scientific import graph_inputs
from semantic.test_rich_scientific import scientific as scientific


def authored_inputs(scientific, values):
    prepared, model, _, _ = scientific
    inputs = graph_inputs(scientific, values)
    context = inputs["context"]
    kinds = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    namespace = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"
    members = []
    for packet in inputs["graph"].members:
        body = packet.body
        if isinstance(body, DdoRichEntity):
            body = body.model_copy(update={"source_members": ()})
        elif isinstance(body, DdoRichOccurrence):
            identifier = canonical_identity(
                "rich-authored-proposition",
                [
                    context.identity_record,
                    body.fact_id,
                    body.observed_qualification_value,
                    sorted(set(body.dependencies)),
                ],
            ).key
            body = DdoRichAuthoredProposition(
                member_type="authored-proposition",
                proposition_id=identifier,
                fact_id=body.fact_id,
                observed_qualification_value=body.observed_qualification_value,
                dependencies=body.dependencies,
            )
        identifier = (
            body.proposition_id
            if isinstance(body, DdoRichAuthoredProposition)
            else packet.member_id
        )
        members.append(
            DdoRichAuthoredPacket(
                member_id=identifier,
                kind_contract=kinds[namespace + type(body).__name__],
                context=packet.context,
                body=body,
            )
        )
    authored = DdoRichAuthoredPropositions(
        version="rich-authored-propositions-1",
        standing="authored-propositions",
        members=tuple(members),
        macros={},
    )
    support = (
        AuthoredFactSupportReference(
            admission_id="authored-domain", source_reference="operator-domain-propositions"
        ),
    )
    roles = (
        CPUInputRole(
            "authored",
            None,
            1,
            "authored-product",
            None,
            kinds[namespace + "DdoRichAuthoredPropositions"],
            context,
            _untrusted_value(authored),
            support,
            producer_output=None,
        ),
        CPUInputRole(
            "policy",
            None,
            1,
            "policy-product",
            None,
            kinds[namespace + "DdoRichConsolidationPolicy"],
            context,
            _untrusted_value(rich_policy_value(prepared, model)),
            support,
            producer_output=None,
        ),
    )
    recipe = next(
        item.key
        for item in model.identities
        if item.domain == "recipe" and item.owner == "rich.consolidate"
    )
    return (
        prepared,
        model,
        RichKernelInputs(recipe, context, roles, parameters=b'["mapping",[]]', replicate=None),
    )


def test_actual_authored_proposition_is_evaluated_and_selected_with_real_authored_origin(
    scientific,
):
    prepared, model, inputs = authored_inputs(
        scientific, ({"kind": "number", "number": Decimal("1")},)
    )
    value = consolidate_rich_knowledge(prepared, model, inputs=inputs, check_active=lambda: None)
    assert len(value.eligibility.selected_fact_ids) == 1
    assert len(value.eligibility.selected_occurrence_ids) == 1
    occurrence = next(
        packet.body for packet in value.members if isinstance(packet.body, DdoRichOccurrence)
    )
    assert occurrence.original.product_id == "authored-product"
    assert occurrence.original.support_references[0].kind == "authored"
    assert (
        occurrence.establishment == "stated"
        and occurrence.statement is None
        and occurrence.evidence_count == 0
    )


def test_actual_scientific_disagreement_creates_complete_alternative_and_withholds_selection(
    scientific,
):
    prepared, model, inputs = authored_inputs(
        scientific,
        ({"kind": "number", "number": Decimal("1")}, {"kind": "number", "number": Decimal("2")}),
    )
    value = consolidate_rich_knowledge(prepared, model, inputs=inputs, check_active=lambda: None)
    alternatives = [
        packet.body for packet in value.members if isinstance(packet.body, DdoRichAlternative)
    ]
    assert len(alternatives) == 1 and alternatives[0].completeness == "complete"
    assert alternatives[0].origin == "value-disagreement" and len(alternatives[0].fact_ids) == 2
    assert value.eligibility.selected_fact_ids == value.eligibility.selected_occurrence_ids == ()
