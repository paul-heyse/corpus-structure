"""Current rich assembly, evaluation and proposed admission over explicit bound values."""

from dataclasses import asdict

from .data_operation_identity import canonical_identity, semantic_value
from .data_operation_json import json_loads
from .data_operation_model import validate_subject_context
from .data_operation_ports import _untrusted_value
from .identity import canonical_bytes
from .rich_decisions import (
    DdoRichEligibility,
    DdoRichOccurrenceDecision,
    DdoRichScientificRepresentative,
)
from .rich_fact_graph import RichFactGraph
from .rich_graph_validation import (
    RichWholeInput,
    _body_id,
    index_rich_assembly,
    read_retained_rich_graph,
    read_rich_graph,
)
from .rich_knowledge_contracts import (
    DdoRichAdmission,
    DdoRichAlternative,
    DdoRichAuthoredProposition,
    DdoRichAuthoredPropositions,
    DdoRichConsolidation,
    DdoRichContext,
    DdoRichDiagnostic,
    DdoRichEntity,
    DdoRichFact,
    DdoRichOccurrence,
    DdoRichPacket,
    DdoRichSourceReadingAssertion,
    RichGraphAssembly,
    read_rich_context_pin,
    rich_reference_key,
)
from .rich_policy_binding import (
    require_rich_policy,
    rich_context_profile,
    rich_eligibility_policy_digest,
)

_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-rich-knowledge/"


class RichAssembly:
    def __init__(self, prepared, model, inputs):
        self.prepared, self.model, self.inputs = prepared, model, inputs
        self.context = inputs.context
        validate_subject_context(model, self.context)
        if (
            model.subject_definition(self.context.subject_definition).scope != "project"
            or self.context.original_source is not None
        ):
            raise ValueError("rich assembly requires its actual checked project knowledge subject")
        self.ids = {item.owner: item.key for item in model.identities if item.domain == "kind"}
        self.kinds = {
            item.key: kind
            for kind in model.kinds
            for item in model.identities
            if item.domain == "kind" and item.owner == kind.semantic_id
        }
        self.references = tuple(
            {
                rich_reference_key(inputs.reference(role)): inputs.reference(role)
                for role in inputs.roles
            }.values()
        )
        self.wholes = tuple(
            RichWholeInput(inputs.reference(role), role.body) for role in inputs.roles
        )
        self.retained = tuple(
            RichWholeInput(inputs.reference(role), role.body)
            for role in inputs.selected("known_universe")
        )
        self.policy = require_rich_policy(prepared, model, inputs.scalar("policy").body)
        self.profile = rich_context_profile(prepared)
        self.policy_digest = rich_eligibility_policy_digest(self.policy, self.model)
        self.packets = {}
        self.source_contexts = []
        self._source_context_index = {}
        self.entities = {}
        self.known = {}
        self.facts = set()
        self.retained_states = []
        for whole in self.retained:
            state = read_retained_rich_graph(
                prepared,
                model,
                context=self.context,
                retained=whole,
                inputs=self.references,
                whole_inputs=self.wholes,
            )
            if state.graph.eligibility_policy_digest != self.policy_digest:
                raise ValueError(
                    "known rich selection requires regeneration under the actual current eligibility policy"
                )
            self.retained_states.append(state)
            for packet in state.graph.members:
                self.insert(packet)
                if isinstance(packet.body, DdoRichEntity):
                    entity = packet.body
                    self.entities[entity.entity_id] = frozenset(
                        self.kinds[contract].semantic_id for contract in entity.class_contracts
                    )
                    from .rich_knowledge import RichKnownEntity, RichKnownEntityIdentity

                    bases = []
                    for basis in entity.identities:
                        definition = state.definition(basis.class_contract)
                        fields = {
                            state.property(field.property_contract, definition.iri)[
                                1
                            ].name: state.property_value(
                                field.value_id,
                                definition,
                                state.property(field.property_contract, definition.iri)[1],
                            )
                            for field in basis.fields
                        }
                        bases.append(
                            RichKnownEntityIdentity(
                                definition.iri,
                                fields,
                                None
                                if basis.source_context is None
                                else read_rich_context_pin(basis.source_context),
                                basis.label,
                            )
                        )
                    self.known[entity.entity_id] = RichKnownEntity(tuple(bases))
                elif isinstance(packet.body, DdoRichFact):
                    self.facts.add(packet.body.fact_id)
        self.values = RichFactGraph(
            prepared,
            model,
            context=self.context,
            entities=self.entities,
            known_fact_ids=frozenset(self.facts),
        )
        from .rich_graph_validation import _VALUES

        for packet in self.packets.values():
            if isinstance(packet.body, _VALUES):
                self.values._retain(packet.body)
            elif isinstance(packet.body, DdoRichFact):
                self.values._facts[packet.body.fact_id] = packet.body

    def insert(self, packet):
        old = self.packets.get(packet.member_id)
        if old is not None and canonical_bytes(
            semantic_value(_untrusted_value(old))
        ) != canonical_bytes(semantic_value(_untrusted_value(packet))):
            raise ValueError("rich member identity has conflicting actual immutable contents")
        self.packets[packet.member_id] = packet

    def add(self, body):
        self.insert(
            DdoRichPacket(
                member_id=_body_id(body),
                kind_contract=self.ids[_NAMESPACE + type(body).__name__],
                context=DdoRichContext(
                    subject=self.context.subject,
                    subject_definition=self.context.subject_definition,
                    original_source=None,
                    analyzed_scope=json_loads(self.context.analyzed_scope),
                ),
                body=body,
            )
        )
        return _body_id(body)

    def add_source_context(self, value):
        key = rich_reference_key(value.original)
        previous = self._source_context_index.get(key)
        if previous is not None and previous != value:
            raise ValueError("one actual source member has conflicting interpretation contexts")
        if previous is None:
            self._source_context_index[key] = value
            self.source_contexts.append(value)

    def diagnostic(self, code, reason, refs):
        identifier = canonical_identity(
            "rich-diagnostic",
            [self.context.identity_record, code, reason, [_untrusted_value(ref) for ref in refs]],
        ).key
        self.add(
            DdoRichDiagnostic(
                member_type="diagnostic",
                diagnostic_id=identifier,
                code=code,
                reason=reason,
                source_members=tuple(refs),
            )
        )

    def flush(self):
        for body in (*self.values.values, *self.values.facts):
            self.add(body)

    def graph(self):
        self.flush()
        return RichGraphAssembly(
            members=tuple(self.packets[key] for key in sorted(self.packets)),
            input_population=self.references,
        )

    def authored(self):
        from .rich_scientific import RichScientificSourceContext

        for role in self.inputs.selected("authored"):
            whole = DdoRichAuthoredPropositions.model_validate(role.body)
            read_rich_graph(
                self.prepared,
                self.model,
                context=self.context,
                graph=whole,
                inputs=(),
                whole_inputs=(),
            )
            parent = self.inputs.reference(role)
            for packet in whole.members:
                body = packet.body
                if isinstance(body, DdoRichAuthoredProposition):
                    original = parent.model_copy(
                        update={
                            "member_id": packet.member_id,
                            "kind_contract": packet.kind_contract,
                        }
                    )
                    identifier = canonical_identity(
                        "rich-authored-occurrence",
                        [
                            self.context.identity_record,
                            _untrusted_value(original),
                            body.proposition_id,
                        ],
                    ).key
                    self.add(
                        DdoRichOccurrence(
                            member_type="source-occurrence",
                            occurrence_id=identifier,
                            fact_id=body.fact_id,
                            original=original,
                            statement=None,
                            observed_qualification_value=body.observed_qualification_value,
                            dependencies=body.dependencies,
                            establishment="stated",
                            statement_kind=None,
                            statement_role=None,
                            evidence_count=0,
                        )
                    )
                    self.add_source_context(
                        RichScientificSourceContext(
                            original=original, context=parent, macros=whole.macros
                        )
                    )
                else:
                    self.insert(DdoRichPacket.model_validate(_untrusted_value(packet)))
                    if isinstance(body, DdoRichEntity):
                        self.entities[body.entity_id] = frozenset(
                            self.kinds[contract].semantic_id for contract in body.class_contracts
                        )
                    elif isinstance(body, DdoRichFact):
                        self.facts.add(body.fact_id)
            self.values.entities.update(self.entities)
            self.values._known_facts.update(self.facts)
            from .rich_graph_validation import _VALUES

            for packet in whole.members:
                if isinstance(packet.body, _VALUES):
                    self.values._retain(packet.body)
                elif isinstance(packet.body, DdoRichFact):
                    self.values._facts[packet.body.fact_id] = packet.body

    def readings(self, check_active):
        from .rich_reading_inputs import select_rich_readings
        from .rich_record_readings import rich_source_reading_assertion

        for selection in select_rich_readings(self.prepared, self.inputs):
            check_active()
            if selection.row is None:
                self.diagnostic(
                    "resolution-unavailable",
                    "Actual raw reading has no corresponding resolved report member",
                    (selection.original,),
                )
                continue
            try:
                assertion = rich_source_reading_assertion(
                    self.prepared,
                    self.model,
                    context=self.context,
                    selection=selection,
                    values=self.values,
                )
                self.add(assertion)
            except ValueError as error:
                self.diagnostic(
                    "incomplete-source-reading",
                    str(error),
                    (selection.original, selection.resolution, selection.resolved),
                )


def consolidate_rich_knowledge(prepared, model, *, inputs, check_active):
    from .rich_proposal_lowering import lower_rich_proposals
    from .rich_relations import RichRelationKernel
    from .rich_rule_evaluation import evaluate_rich_rules
    from .rich_rules import prepared_rich_rule_policy
    from .rich_scientific import assess_rich_scientific

    builder = RichAssembly(prepared, model, inputs)
    builder.authored()
    lower_rich_proposals(builder, check_active=check_active)
    builder.readings(check_active)
    graph = builder.graph()
    policy = prepared_rich_rule_policy(prepared)
    index = index_rich_assembly(
        prepared, model, context=inputs.context, graph=graph, inputs=builder.references,
        whole_inputs=builder.wholes, retained_states=tuple(builder.retained_states),
    )
    scientific = assess_rich_scientific(
        prepared,
        model,
        context=inputs.context,
        graph=graph,
        inputs=builder.references,
        policy=policy,
        context_profile=builder.profile,
        source_contexts=tuple(builder.source_contexts),
        whole_inputs=builder.wholes,
        retained_graphs=builder.retained,
        _index=index,
    )
    for assessment in scientific:
        builder.add(assessment)
    # A decisive comparison of distinct values creates an actual alternative in
    # the same functional slot; unknown comparisons remain scientific unknowns.
    occurrences = {
        packet.member_id: packet.body
        for packet in graph.members
        if isinstance(packet.body, DdoRichOccurrence)
    }
    facts = {
        packet.member_id: packet.body
        for packet in graph.members
        if isinstance(packet.body, DdoRichFact)
    }
    facts_by_slot = {}
    for fact in facts.values():
        slot = (fact.subject_entity, fact.property_contract, fact.qualification_meaning)
        facts_by_slot.setdefault(slot, []).append(fact.fact_id)
    slots = {}
    for assessment in scientific:
        if assessment.outcome != "different":
            continue
        selected = tuple(occurrences[identifier] for identifier in assessment.occurrences)
        left = facts[selected[0].fact_id]
        slot = (left.subject_entity, left.property_contract, left.qualification_meaning)
        slots[slot] = tuple(sorted(set(facts_by_slot[slot])))
    for slot, ids in sorted(slots.items()):
        identifier = canonical_identity(
            "rich-value-disagreement", [inputs.context.identity_record, slot, ids]
        ).key
        builder.add(
            DdoRichAlternative(
                member_type="alternative",
                alternative_id=identifier,
                fact_ids=ids,
                completeness="complete",
                origin="value-disagreement",
                faithful=True,
                reason="Actual functional values differ under the captured scientific comparison",
                source_members=tuple(
                    {
                        rich_reference_key(ref): ref
                        for assessment in scientific
                        if assessment.outcome == "different"
                        for ref in assessment.evidence_members
                    }.values()
                ),
            )
        )
    graph = builder.graph()
    index = index_rich_assembly(
        prepared, model, context=inputs.context, graph=graph, inputs=builder.references,
        whole_inputs=builder.wholes, retained_states=tuple(builder.retained_states),
    )
    with RichRelationKernel(
        property_ids=frozenset(
            prop.iri for definition in prepared.definitions for prop in definition.properties
        ),
        threads=1,
        memory_limit="2GB",
        check_active=check_active,
    ) as relations:
        result = evaluate_rich_rules(
            prepared,
            model,
            context=inputs.context,
            graph=graph,
            inputs=builder.references,
            policy=policy,
            relations=relations,
            context_profile=builder.profile,
            consolidation_policy=builder.policy,
            source_contexts=tuple(builder.source_contexts),
            scientific_assessments=scientific,
            whole_inputs=builder.wholes,
            retained_graphs=builder.retained,
            _index=index,
        )
    for assessment in result.assessments:
        builder.add(assessment)
    for decision in result.decisions:
        fields = asdict(decision)
        identifier = canonical_identity(
            "rich-occurrence-decision", [inputs.context.identity_record, fields]
        ).key
        builder.add(
            DdoRichOccurrenceDecision(
                member_type="occurrence-decision", decision_id=identifier, **fields
            )
        )
    representatives = tuple(
        DdoRichScientificRepresentative(**asdict(value))
        for value in result.scientific_representatives
    )
    eligibility = DdoRichEligibility(
        eligibility_policy_digest=result.eligibility_policy_digest,
        selected_fact_ids=tuple(sorted(result.selected_fact_ids)),
        selected_occurrence_ids=tuple(sorted(result.selected_occurrence_ids)),
        scientific_representatives=representatives,
    )
    assembled = builder.graph()
    output = DdoRichConsolidation(
        version="rich-consolidation-1",
        standing="private-consolidated",
        members=assembled.members,
        input_population=assembled.input_population,
        eligibility=eligibility,
    )
    return read_rich_graph(
        prepared,
        model,
        context=inputs.context,
        graph=output,
        inputs=builder.references,
        whole_inputs=builder.wholes,
        retained_graphs=builder.retained,
        _retained_states=tuple(builder.retained_states),
    ).graph


def admit_rich_knowledge(prepared, model, *, inputs, check_active):
    from .rich_graph_subset import admitted_rich_members
    from .rich_reading_admission import rich_reading_decisions

    check_active()
    role = inputs.scalar("consolidation")
    consolidation = DdoRichConsolidation.model_validate(role.body)
    decisions = rich_reading_decisions(prepared, model, inputs=inputs, consolidation=consolidation)
    accepted = frozenset(
        value.assertion_member_id
        for value in decisions
        if value.outcome == "accepted" and value.assertion_member_id is not None
    )
    # Genuine inherited known reading packets have already passed native current
    # producer/selection custody. Their exact member identities remain unchanged.
    current_pairs = {
        (
            rich_reference_key(value.original),
            rich_reference_key(value.resolution),
            rich_reference_key(value.resolved),
        )
        for value in decisions
        if value.resolution is not None and value.resolved is not None
    }
    inherited = {
        packet.body.reading_id
        for packet in consolidation.members
        if isinstance(packet.body, DdoRichSourceReadingAssertion)
        and (
            rich_reference_key(packet.body.original),
            rich_reference_key(packet.body.resolution),
            rich_reference_key(packet.body.resolved),
        )
        not in current_pairs
    }
    members = admitted_rich_members(consolidation, accepted_readings=accepted | inherited)
    eligibility = consolidation.eligibility
    output = DdoRichAdmission(
        version="rich-admission-1",
        standing="accepted",
        eligibility_policy_digest=eligibility.eligibility_policy_digest,
        selected_fact_ids=eligibility.selected_fact_ids,
        selected_occurrence_ids=eligibility.selected_occurrence_ids,
        selected_reading_ids=tuple(sorted(accepted | inherited)),
        scientific_representatives=eligibility.scientific_representatives,
        members=members,
        consolidation=inputs.reference(role),
        policy_authorizations=tuple(
            inputs.reference(role) for role in inputs.selected("policy_authorizations")
        ),
        reading_decisions=decisions,
    )
    check_active()
    return output
