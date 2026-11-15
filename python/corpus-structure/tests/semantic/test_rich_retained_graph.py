"""Current typed retained-root decoding; native standing/custody is verified separately."""

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.rich_graph_validation import RichWholeInput, read_retained_rich_graph, read_rich_graph
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAdmission, DdoRichAuthoredProposition, DdoRichAuthoredPacket, DdoRichAuthoredPropositions,
    DdoRichConsolidation, DdoRichEntity, DdoRichFact, DdoRichOccurrence, rich_reference_key,
)
from semantic.test_rich_value_graph import source as source, actual_graph

PREFIX = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


def retained(source):
    context, graph, inputs = actual_graph(source)
    prepared, model = source
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    old = inputs[0].model_copy(update={"kind_contract": "historical:opaque-source-kind"})
    packets = []
    for packet in graph.members:
        body = packet.body
        if isinstance(body, DdoRichEntity):
            body = body.model_copy(update={"source_members": (old,)})
        elif isinstance(body, DdoRichOccurrence):
            body = body.model_copy(update={"original": old})
        packets.append(packet.model_copy(update={"body": body}))
    root = DdoRichAdmission(version="rich-admission-1", standing="accepted", members=tuple(packets),
                            consolidation=old.model_copy(update={"member_id": None}), policy_authorizations=(), reading_decisions=())
    reference = inputs[0].model_copy(update={"product_id": "selected:accepted-knowledge", "member_id": None,
                                            "kind_contract": ids[PREFIX + "DdoRichAdmission"]})
    selection = RichWholeInput(reference, root)
    return context, selection


def test_retained_whole_keeps_opaque_provenance_without_inventing_current_inputs(source):
    prepared, model = source
    context, selected = retained(source)
    inputs, wholes = (selected.reference,), (selected,)
    prior = read_retained_rich_graph(prepared, model, context=context, retained=selected, inputs=inputs, whole_inputs=wholes)
    assert prior.graph == selected.value
    output = DdoRichConsolidation(version="rich-consolidation-1", standing="private-consolidated", members=prior.graph.members, input_population=inputs)
    current = read_rich_graph(prepared, model, context=context, graph=output, inputs=inputs, whole_inputs=wholes, retained_graphs=wholes)
    assert current.inputs == {rich_reference_key(selected.reference)}
    assert current.retained_member_ids == {packet.member_id for packet in output.members}
    assert current.retained_roots == wholes
    original = next(packet.body.original for packet in output.members if isinstance(packet.body, DdoRichOccurrence))
    with pytest.raises(ValueError, match="actual selected input"):
        current.external(original)
    current.occurrence_source(original)
    with pytest.raises(ValueError, match="actual selected input"):
        read_rich_graph(prepared, model, context=context, graph=output, inputs=inputs, whole_inputs=wholes)


@pytest.mark.parametrize("defect", ["member-root", "wrong-root-kind", "different-body", "unselected-root", "changed-packet", "foreign-local-kind", "missing-support"])
def test_retained_graph_refuses_unselected_roots_local_contract_changes_and_modified_inherited_provenance(source, defect):
    prepared, model = source
    context, selection = retained(source)
    inputs, wholes = (selection.reference,), (selection,)
    if defect == "member-root":
        selection = RichWholeInput(selection.reference.model_copy(update={"member_id": "not-a-whole"}), selection.value)
    elif defect == "wrong-root-kind":
        selection = RichWholeInput(selection.reference.model_copy(update={"kind_contract": "historical:admission-contract"}), selection.value)
        inputs, wholes = (selection.reference,), (selection,)
    elif defect == "different-body":
        selection = RichWholeInput(selection.reference, selection.value.model_copy(update={"policy_authorizations": (selection.reference,)}))
    elif defect == "unselected-root":
        inputs = ()
    elif defect == "missing-support":
        selection = RichWholeInput(selection.reference.model_copy(update={"support_references": ()}), selection.value)
        inputs, wholes = (selection.reference,), (selection,)
    elif defect == "foreign-local-kind":
        fact = next(packet for packet in selection.value.members if isinstance(packet.body, DdoRichFact))
        altered = fact.model_copy(update={"body": fact.body.model_copy(update={"property_contract": "historical:changed-property"})})
        selection = RichWholeInput(selection.reference, selection.value.model_copy(update={"members": tuple(altered if item.member_id == fact.member_id else item for item in selection.value.members)}))
        wholes = (selection,)
    elif defect == "changed-packet":
        occurrence = next(packet for packet in selection.value.members if isinstance(packet.body, DdoRichOccurrence))
        altered = occurrence.model_copy(update={"body": occurrence.body.model_copy(update={"original": occurrence.body.original.model_copy(update={"product_id": "unselected:new-source"})})})
        output = DdoRichConsolidation(version="rich-consolidation-1", standing="private-consolidated",
                                      members=tuple(altered if item.member_id == occurrence.member_id else item for item in selection.value.members), input_population=inputs)
        with pytest.raises(ValueError, match="actual selected input"):
            read_rich_graph(prepared, model, context=context, graph=output, inputs=inputs, whole_inputs=wholes, retained_graphs=wholes)
        return
    with pytest.raises(ValueError):
        read_retained_rich_graph(prepared, model, context=context, retained=selection, inputs=inputs, whole_inputs=wholes)


def authored(source):
    context, graph, _ = actual_graph(source)
    prepared, model = source
    ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    packets = []
    for packet in graph.members:
        body = packet.body
        if isinstance(body, DdoRichEntity):
            body = body.model_copy(update={"source_members": ()})
        if isinstance(body, DdoRichOccurrence):
            key = canonical_identity("rich-authored-proposition", [context.identity_record, body.fact_id, body.observed_qualification_value, sorted(set(body.dependencies))]).key
            body = DdoRichAuthoredProposition(member_type="authored-proposition", proposition_id=key, fact_id=body.fact_id,
                                             observed_qualification_value=body.observed_qualification_value, dependencies=body.dependencies)
        identifier = body.proposition_id if isinstance(body, DdoRichAuthoredProposition) else packet.member_id
        packets.append(DdoRichAuthoredPacket(member_id=identifier, kind_contract=ids[PREFIX + type(body).__name__], context=packet.context, body=body))
    return context, DdoRichAuthoredPropositions(version="rich-authored-propositions-1", standing="authored-propositions", members=tuple(packets), macros={})


def test_authored_propositions_have_local_meaning_without_fictional_self_origin(source):
    prepared, model = source
    context, graph = authored(source)
    state = read_rich_graph(prepared, model, context=context, graph=graph, inputs=())
    proposition = next(item for item in state.members.values() if isinstance(item, DdoRichAuthoredProposition))
    assert not hasattr(proposition, "original")
    assert not hasattr(proposition, "statement")
    assert proposition.observed_qualification_value in state.members
    assert all(not item.source_members for item in state.members.values() if isinstance(item, DdoRichEntity))
    raw = graph.model_dump(mode="python")
    raw.pop("macros")
    with pytest.raises(ValidationError, match="macros"):
        DdoRichAuthoredPropositions.model_validate(raw)


@pytest.mark.parametrize("defect", ["computed-occurrence", "forged-assessment", "embedded-origin", "wrong-qualification", "forged-identity"])
def test_authored_propositions_refuse_computed_claims_and_unchecked_meaning(source, defect):
    prepared, model = source
    context, graph = authored(source)
    if defect in {"computed-occurrence", "forged-assessment"}:
        from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAssessment
        _, computed, _ = actual_graph(source)
        occurrence = next(packet for packet in computed.members if isinstance(packet.body, DdoRichOccurrence))
        if defect == "computed-occurrence":
            invalid = occurrence.model_dump(mode="python")
        else:
            invalid = {**occurrence.model_dump(mode="python"), "member_id": "assessment:forged", "body": DdoRichAssessment(
                severity=None, member_type="assessment", assessment_id="assessment:forged", occurrences=(occurrence.member_id,), rule="scientific.value_equivalence", outcome="equivalent", reason="authored text is not computation", evidence_members=(),
            ).model_dump(mode="python")}
        with pytest.raises(ValidationError):
            DdoRichAuthoredPropositions.model_validate({**graph.model_dump(mode="python"), "members": (*graph.members, invalid)})
        return
    packets = list(graph.members)
    if defect == "embedded-origin":
        index = next(index for index, packet in enumerate(packets) if isinstance(packet.body, DdoRichEntity))
        old = actual_graph(source)[2][0]
        packets[index] = packets[index].model_copy(update={"body": packets[index].body.model_copy(update={"source_members": (old,)})})
    else:
        index = next(index for index, packet in enumerate(packets) if isinstance(packet.body, DdoRichAuthoredProposition))
        change = {"observed_qualification_value": "value:not-selected"} if defect == "wrong-qualification" else {"proposition_id": "authored-proposition:forged"}
        previous = packets[index].body
        assert isinstance(previous, DdoRichAuthoredProposition)
        body = previous.model_copy(update=change)
        packets[index] = packets[index].model_copy(update={"body": body, "member_id": body.proposition_id})
    with pytest.raises(ValueError):
        read_rich_graph(prepared, model, context=context, graph=graph.model_copy(update={"members": tuple(packets)}), inputs=())
