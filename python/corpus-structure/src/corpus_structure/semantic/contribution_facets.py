"""Joined current interpretation/assessment facets, without granting new standing."""

from collections import defaultdict

from .data_operation_identity import semantic_value
from .identity import canonical_bytes
from .rich_decisions import DdoRichOccurrenceDecision
from .rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichAssessment,
    DdoRichEntity,
    DdoRichFact,
    DdoRichIdentityExclusion,
    DdoRichIdentityResolution,
    DdoRichOccurrence,
    DdoRichSourceReadingAssertion,
)
from .rich_proposals import FAMILIES, read_rich_proposals
from .rich_queries import RichGraphIndex, RichQueryRefused, RichQueryRow

PROPOSAL_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-rich-proposals/"
LOCATED_KIND = "https://corpus-structure.dev/semantic/data-operation-external-extraction/DdoLocatedExternalExtraction"


def _position(selected, population, member):
    return canonical_bytes(
        [
            selected.use_id,
            selected.output["role"],
            selected.output["position"],
            selected.reference.product_id,
            population,
            member,
        ]
    ).decode()


def _reference(selected, member_id, kind_contract):
    # The actual whole output admits its own declared member projection. This is
    # a result reference, never a manufactured frozen input binding.
    return selected.reference.model_copy(
        update={"member_id": member_id, "kind_contract": kind_contract}
    ).model_dump(mode="python")


def graph_facets(
    selected,
    state,
    *,
    interpretation,
    assessment,
    member_id=None,
    max_members=100000,
    max_nested_members=1000,
):
    index = RichGraphIndex(state, max_members=max_members, max_nested_members=max_nested_members)
    by_occurrence = defaultdict(list)
    decisions = defaultdict(list)
    for body in state.members.values():
        if isinstance(body, DdoRichAssessment):
            for occurrence in body.occurrences:
                by_occurrence[occurrence].append(body)
        elif isinstance(body, DdoRichOccurrenceDecision):
            decisions[body.occurrence_id].append(body)
    root = state.graph
    readings = defaultdict(list)
    if isinstance(root, DdoRichAdmission):
        for decision in root.reading_decisions:
            readings[decision.assertion_member_id].append(decision)
    for identifier, packet in sorted(state.packets.items()):
        if member_id is not None and identifier != member_id:
            continue
        body = packet.body
        # Auxiliary exact values remain reachable from their actual typed roots;
        # they are not silently promoted to independent source contributions.
        if body.member_type in {
            "scalar-value",
            "entity-value",
            "record-value",
            "collection-value",
            "casefold-text",
            "qualification-meaning",
        }:
            continue
        target = _reference(selected, identifier, packet.kind_contract)
        base = dict(
            reference=target,
            context=packet.context.model_dump(mode="python"),
            nominal=type(body).__name__,
            standing=root.standing,
            retained_roots=[
                item.model_dump(mode="python") for item in state.retained_sources(identifier)
            ],
            selection_scope="admitted-root-conclusions"
            if isinstance(root, DdoRichAdmission)
            else "private-fact-occurrence-eligibility",
        )
        selected_ids = (
            index.selected_facts
            if isinstance(body, DdoRichFact)
            else index.selected_occurrences
            if isinstance(body, DdoRichOccurrence)
            else index.selected_readings
            if isinstance(body, DdoRichSourceReadingAssertion)
            and isinstance(root, DdoRichAdmission)
            else None
        )
        contribution = dict(
            base, conclusion_selection=None if selected_ids is None else identifier in selected_ids
        )
        yield RichQueryRow(
            dict(population="contribution", row=contribution),
            _position(selected, "contribution", identifier),
        )
        if interpretation:
            if isinstance(body, DdoRichFact):
                meaning = index.claim_record(identifier)
            elif isinstance(body, DdoRichOccurrence):
                meaning = dict(
                    occurrence=body.model_dump(mode="python"),
                    claim=index.claim_record(body.fact_id),
                )
            elif isinstance(body, DdoRichEntity):
                meaning = index.entity_record(identifier)
            elif isinstance(body, DdoRichSourceReadingAssertion):
                meaning = dict(
                    assertion=body.model_dump(mode="python"),
                    reading=semantic_value(
                        index.state.value(body.reading_value).model_dump(
                            mode="python", exclude_unset=True
                        )
                    ),
                    values=index.values((body.reading_value,)),
                    scientific_truth="not-established",
                )
            else:
                meaning = body.model_dump(mode="python")
            yield RichQueryRow(
                dict(
                    population="interpretation",
                    row=dict(base, meaning=meaning, availability="observed"),
                ),
                _position(selected, "interpretation", identifier),
            )
        if assessment:
            occurrences = (
                (identifier,)
                if isinstance(body, DdoRichOccurrence)
                else tuple(item.occurrence_id for item in index.by_fact[identifier])
                if isinstance(body, DdoRichFact)
                else ()
            )
            judgments = {
                item.assessment_id: item
                for occurrence in occurrences
                for item in by_occurrence[occurrence]
            }
            rules = {
                item.decision_id: item
                for occurrence in occurrences
                for item in decisions[occurrence]
            }
            if isinstance(body, DdoRichAssessment):
                judgments[body.assessment_id] = body
            if isinstance(body, DdoRichOccurrenceDecision):
                rules[body.decision_id] = body
            if max(len(judgments), len(rules), len(readings[identifier])) > max_nested_members:
                raise RichQueryRefused(
                    "one contribution assessment exceeds its nested judgment bound"
                )
            actual = dict(
                judgments=[judgments[key].model_dump(mode="python") for key in sorted(judgments)],
                occurrence_decisions=[
                    rules[key].model_dump(mode="python") for key in sorted(rules)
                ],
                reading_decisions=[item.model_dump(mode="python") for item in readings[identifier]],
                identity_resolution=body.model_dump(mode="python")
                if isinstance(body, DdoRichIdentityResolution)
                else None,
                identity_constraint=body.model_dump(mode="python")
                if isinstance(body, DdoRichIdentityExclusion)
                else None,
            )
            observed = any(actual.values())
            yield RichQueryRow(
                dict(
                    population="assessment",
                    row=dict(
                        base,
                        availability="observed" if observed else "unknown",
                        scope="captured-native-producer-judgments",
                        reason=None if observed else "no-associated-judgment-in-this-selected-root",
                        **actual,
                    ),
                ),
                _position(selected, "assessment", identifier),
            )
    if assessment and member_id is None and isinstance(root, DdoRichAdmission):
        # Rejected/uncheckable readings have no assertion member. Their genuine
        # adjudication must not disappear merely because they produced no value.
        for position, decision in enumerate(readings[None]):
            yield RichQueryRow(
                dict(
                    population="assessment",
                    row=dict(
                        reference=selected.reference.model_dump(mode="python"),
                        standing=root.standing,
                        availability="observed",
                        scope="captured-native-producer-judgments",
                        reading_decision=decision.model_dump(mode="python"),
                    ),
                ),
                _position(selected, "reading-decision", str(position)),
            )


def proposal_facets(
    selected,
    prepared,
    model,
    *,
    interpretation,
    assessment,
    member_id=None,
    max_nested_members=1000,
):
    kinds = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    if kinds.get(LOCATED_KIND) != selected.reference.kind_contract:
        raise RichQueryRefused(
            "located proposal root lacks its actual current-compatible nominal contract"
        )
    report = read_rich_proposals(prepared, selected.body)
    types = {tag: PROPOSAL_NAMESPACE + name for _, tag, name in FAMILIES}
    members = {item["member_id"]: item for item in report["members"]}
    for identifier, packet in sorted(members.items()):
        if member_id is not None and identifier != member_id:
            continue
        body = packet["body"]
        if packet["kind_contract"] != kinds[types[body["proposal_type"]]]:
            raise RichQueryRefused(
                "located contribution body differs from its actual nominal member kind"
            )
        base = dict(
            reference=_reference(selected, identifier, packet["kind_contract"]),
            context=packet["context"],
            standing="private_proposed",
            nominal=types[body["proposal_type"]],
        )
        yield RichQueryRow(
            dict(population="contribution", row=base),
            _position(selected, "contribution", identifier),
        )
        if interpretation:
            related = []
            if body["proposal_type"] == "alternative":
                if len(body["claims"]) > max_nested_members:
                    raise RichQueryRefused(
                        "source alternative exceeds its nested member-reference bound"
                    )
                related = [
                    _reference(
                        selected, ref["member_id"], members[ref["member_id"]]["kind_contract"]
                    )
                    for ref in body["claims"]
                ]
            yield RichQueryRow(
                dict(
                    population="interpretation",
                    row=dict(
                        base,
                        availability="observed",
                        source_pin=report["source_pin"],
                        unit_ref=report["unit_ref"],
                        meaning=semantic_value(body),
                        related=related,
                        known_reference_standing=report["known_reference_standing"],
                        scientific_truth="not-established",
                    ),
                ),
                _position(selected, "interpretation", identifier),
            )
        if assessment:
            yield RichQueryRow(
                dict(
                    population="assessment",
                    row=dict(
                        base,
                        availability="unknown",
                        scope="captured-native-producer-judgments",
                        reason="source-proposal-has-no-computed-acceptance-judgment",
                    ),
                ),
                _position(selected, "assessment", identifier),
            )
    for coverage in report["coverage"]:
        yield RichQueryRow(
            dict(
                population="coverage",
                row=dict(
                    reference=selected.reference.model_dump(mode="python"),
                    coverage=coverage,
                    source_scope="supplied-authored-response",
                    original_source_completeness="unknown",
                ),
            ),
            _position(selected, "coverage", coverage["family"]),
        )
