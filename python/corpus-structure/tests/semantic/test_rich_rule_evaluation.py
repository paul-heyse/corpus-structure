"""Independent rule outcomes over real compiled rich graphs and actual typed views.

Source references are unadmitted controlled values. Native producer/custody
qualification remains a separate boundary; no publication receipt is fabricated.
"""

from pathlib import Path
from dataclasses import asdict

import pytest
import yaml

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.analysis_contracts import acquire_analysis_context_profile
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichAdmission, DdoRichAlternative, DdoRichContext, DdoRichFact, DdoRichOccurrence, DdoRichPacket, DdoRichSelectedMember,
    RichGraphAssembly,
)
from corpus_structure.semantic.rich_knowledge_sources import rich_knowledge_declarations, rich_knowledge_inputs
from corpus_structure.semantic.rich_policy_binding import rich_policy_value
from corpus_structure.semantic.rich_relations import RichRelationKernel
from corpus_structure.semantic.rich_rule_evaluation import RichRuleEvaluationRefused, evaluate_rich_rules
from corpus_structure.semantic.rich_decisions import DdoRichScientificRepresentative
from corpus_structure.semantic.rich_graph_validation import RichWholeInput
from corpus_structure.semantic.rich_rules import RichRulePolicy
from corpus_structure.semantic.rich_scientific import assess_rich_scientific
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.data_operation_declaration_support import contract, declarations
from semantic.record_contracts_support import release_inputs
from semantic.test_rich_scientific import formula, graph_inputs

PREFIX = 'https://corpus-structure.dev/semantic/data-operation-rich-knowledge/'


@pytest.fixture(scope='module')
def rules():
    root = Path(__file__).resolve().parents[4]
    profile = acquire_analysis_context_profile()
    policy = {
        'rules': [
            {'id': 'check.reject', 'severity': 'error', 'check': "claim.value&.v != 'reject'"},
            {'id': 'check.warn', 'severity': 'warning', 'check': "claim.value&.v != 'warn'"},
            {'id': 'check.unrelated', 'applies_to': 'stat:has_distribution', 'check': 'false'},
            {'id': 'check.conditions', 'when': "claim.value&.v == 'unknown'", 'check': 'claim.condition_nodes.is_empty'},
            {'id': 'check.premise', 'when': "claim.value&.v == 'conclusion'", 'check': '$any([p in claim.claim_refs for p in claim.statement_premises])'},
        ],
        # Guideline status comes from its declared section, not an ID prefix.
        'guideline': [{'id': 'review.warn', 'severity': 'error', 'check': "claim.value&.v != 'warn'"}],
    }
    bundle, dependencies = rich_knowledge_inputs(
        release_inputs()[0], ResolvedDependencies(), domain_rules=yaml.safe_dump(policy).encode(),
        core_rules=(root / 'domains/core/schema/rules.yaml').read_bytes(), context_profile=profile,
        qualification_class='StatisticsQualification', statement_class='SourceStatement',
    )
    source = SourceArtifact('rich-rule-example', b'''id: urn:rich-scientific
name: rich_rule_example
imports: [SOURCE_ROOT]
prefixes: {r: 'urn:rich-scientific:'}
default_prefix: r
classes:
  ScientificSubject:
    is_a: Entity
    attributes:
      value:
        range: Value
        inlined: true
        multivalued: true
        annotations: {cs:constraint_scope: accepted_value, cs:role: predicate, cs:functional: true}
      annotation:
        range: Value
        inlined: true
        annotations: {cs:constraint_scope: accepted_value}
'''.replace(b'SOURCE_ROOT', bundle.root.encode()))
    bundle = SourceBundle(source.name, (*bundle.sources, source))
    operation = contract(subject='knowledge-universe', subject_definition={'id': 'knowledge-universe', 'identifier_kind': 'string', 'scope': 'project'})
    model = compile_data_operations(bundle, declarations=(*rich_knowledge_declarations(dependencies), *declarations(operation)))
    prepared = prepare_release(bundle, dependencies)
    return prepared, model, profile, RichRulePolicy(prepared)


def evaluate(rules, inputs, *, scientific=(), policy=None):
    prepared, model, profile, compiled = rules
    actual = {key: value for key, value in inputs.items() if key != 'source_contexts'}
    with RichRelationKernel(property_ids=frozenset(prop.iri for definition in prepared.definitions for prop in definition.properties),
                            threads=1, memory_limit='128MB', check_active=lambda: None) as relations:
        return evaluate_rich_rules(prepared, model, policy=compiled if policy is None else policy,
                                   relations=relations, context_profile=profile,
                                   consolidation_policy=rich_policy_value(prepared, model),
                                   source_contexts=inputs['source_contexts'], scientific_assessments=scientific, **actual)


def source_values(*values):
    return tuple({'kind': 'text', 'text': value} for value in values)


@pytest.mark.parametrize('value,status,failed,severity', [
    ('good', 'accepted', (), None),
    ('warn', 'accepted', ('check.warn', 'review.warn'), 'warning'),
    ('reject', 'rejected', ('check.reject',), 'error'),
])
def test_actual_rule_warning_and_error_standing_remain_distinct(rules, value, status, failed, severity):
    inputs = graph_inputs(rules, source_values(value))
    result = evaluate(rules, inputs)
    assert len(result.decisions) == 1
    decision = result.decisions[0]
    assert decision.status == status
    findings = {finding.rule: finding for finding in decision.findings}
    assert findings['check.unrelated'].outcome == 'not-applicable'
    assert tuple(sorted(finding.rule for finding in decision.findings if finding.outcome == 'failed')) == failed
    assessments = [item for item in result.assessments if item.outcome == 'invalid']
    assert {item.severity for item in assessments} == ({severity} if failed else set())
    assert result.selected_occurrence_ids == (frozenset({decision.occurrence_id}) if status == 'accepted' else frozenset())
    assert result.selected_fact_ids == (frozenset({decision.fact_id}) if status == 'accepted' else frozenset())


def test_uninterpreted_condition_is_unknown_not_empty_pass_or_refutation(rules):
    inputs = graph_inputs(rules, source_values('unknown'), qualifications=({'modality': 'asserted', 'polarity': True,
                                                                          'condition': {'kind': 'escape', 'text': 'as yet uninterpreted', 'reason': 'unread source condition'}},))
    result = evaluate(rules, inputs)
    decision = result.decisions[0]
    finding = next(item for item in decision.findings if item.rule == 'check.conditions')
    assert decision.status == 'candidate'
    assert finding.outcome == 'not-checkable' and finding.assessment_id is not None
    assert next(item for item in result.assessments if item.assessment_id == finding.assessment_id).outcome == 'undecided'
    assert result.selected_fact_ids == frozenset()


def test_duplicate_reports_of_one_fact_do_not_compete_and_source_alternatives_remain_explicit(rules):
    duplicate = evaluate(rules, graph_inputs(rules, source_values('good', 'good')))
    assert {item.status for item in duplicate.decisions} == {'accepted'}
    assert len(duplicate.selected_fact_ids) == 1 and len(duplicate.selected_occurrence_ids) == 2
    inputs = graph_inputs(rules, source_values('first', 'second'))
    prepared, model, _, _ = rules
    facts = tuple(sorted(packet.body.fact_id for packet in inputs['graph'].members if isinstance(packet.body, DdoRichFact)))
    body = DdoRichAlternative(member_type='alternative', alternative_id=canonical_identity('controlled-alternative', facts).key,
                              fact_ids=facts, origin='source-proposal', faithful=True, reason='actual supplied alternative members',
                              source_members=tuple(item.original for item in inputs['source_contexts']))
    kind = next(item.key for item in model.identities if item.domain == 'kind' and item.owner == PREFIX + 'DdoRichAlternative')
    packet = DdoRichPacket(member_id=body.alternative_id, kind_contract=kind,
                           context=DdoRichContext(subject=inputs['context'].subject, subject_definition=inputs['context'].subject_definition,
                                                  original_source=None, analyzed_scope={}), body=body)
    inputs['graph'] = RichGraphAssembly(members=(*inputs['graph'].members, packet), input_population=inputs['graph'].input_population)
    alternatives = evaluate(rules, inputs)
    assert {item.status for item in alternatives.decisions} == {'ambiguous'}
    assert alternatives.selected_fact_ids == frozenset()


def test_scientific_equivalence_uses_real_assessments_and_never_merges_fact_identity(rules):
    inputs = graph_inputs(rules, source_values('Gaussian', ' GAUSSIAN '))
    prepared, model, profile, policy = rules
    scientific = assess_rich_scientific(prepared, model, policy=policy, context_profile=profile, **inputs)
    assert len(scientific) == 1 and scientific[0].outcome == 'equivalent'
    result = evaluate(rules, inputs, scientific=scientific)
    assert len(result.selected_fact_ids) == 2
    assert {item.representative_fact_id for item in result.scientific_representatives} == {min(result.selected_fact_ids)}
    assert {item.fact_id for item in result.scientific_representatives} == result.selected_fact_ids
    assert len({item.component_id for item in result.scientific_representatives}) == 1


def test_actual_undecided_scientific_reading_is_candidate_not_inequality(rules):
    inputs = graph_inputs(rules, (formula('x', 'unresolved'), formula('x+0', 'unresolved')))
    prepared, model, profile, policy = rules
    scientific = assess_rich_scientific(prepared, model, policy=policy, context_profile=profile, **inputs)
    assert len(scientific) == 1 and scientific[0].outcome == 'undecided'
    result = evaluate(rules, inputs, scientific=scientific)
    assert {item.status for item in result.decisions} == {'candidate'}
    assert result.selected_fact_ids == frozenset()
    assert result.scientific_representatives == ()
    assert not any(item.outcome == 'different' for item in result.assessments)


def test_mathematical_rule_reading_uses_actual_captured_profile_and_context(rules):
    inputs = graph_inputs(rules, (formula('x+x'),))
    actual = evaluate(rules, inputs)
    assert actual.decisions[0].status == 'accepted'
    unavailable = evaluate(rules, {**inputs, 'source_contexts': ()})
    assert unavailable.decisions[0].status == 'candidate'
    assert any(item.rule == 'operation.not_checkable' and item.outcome == 'undecided' for item in unavailable.assessments)


def statement_inputs(rules, *, shared=True, global_premise=False):
    preliminary = graph_inputs(rules, source_values('premise'), qualifications=({'modality': 'supposed', 'polarity': True},))
    fact = next(packet.body.fact_id for packet in preliminary['graph'].members if isinstance(packet.body, DdoRichOccurrence))
    inputs = graph_inputs(rules, source_values('premise', 'conclusion'), qualifications=(
        {'modality': 'supposed', 'polarity': True},
        {'modality': 'asserted', 'polarity': True, 'condition': {'kind': 'claim', 'ref': fact}},
    ))
    _, model, _, _ = rules
    kind = next(item.key for item in model.identities if item.domain == 'kind' and item.owner == 'https://corpus-structure.dev/semantic/data-operation-rich-proposals/DdoRichStatementProposal')
    support = (ComputationalSupportReference(derivation_id='controlled:statement-episode'),)
    first = DdoRichSelectedMember(product_id='controlled:statements', member_id='statement:first', kind_contract=kind, support_references=support)
    second = first if shared else first.model_copy(update={'member_id': 'statement:other'})
    inputs['inputs'] = (*inputs['inputs'], first, *((second,) if second != first else ()))
    packets = []
    for packet in inputs['graph'].members:
        if isinstance(packet.body, DdoRichOccurrence):
            is_first = packet.body.occurrence_id == 'occurrence:0'
            body = packet.body.model_copy(update={'statement': first if is_first else second,
                                                  'statement_kind': 'assumption' if is_first and global_premise else 'theorem',
                                                  'statement_role': 'premise' if is_first else 'conclusion'})
            packet = packet.model_copy(update={'body': body})
        packets.append(packet)
    inputs['graph'] = RichGraphAssembly(members=tuple(packets), input_population=inputs['inputs'])
    return inputs


@pytest.mark.parametrize('shared,global_premise,expected', [(True, False, 'passed'), (False, False, 'failed'), (False, True, 'passed')])
def test_premise_relations_use_actual_statement_context_and_canonical_fact_refs(rules, shared, global_premise, expected):
    result = evaluate(rules, statement_inputs(rules, shared=shared, global_premise=global_premise))
    conclusion = next(item for item in result.decisions if item.occurrence_id == 'occurrence:1')
    assert next(item for item in conclusion.findings if item.rule == 'check.premise').outcome == expected


@pytest.mark.parametrize('error_type', [ValueError, KeyError])
def test_unexpected_rule_execution_errors_keep_their_identity(rules, error_type):
    prepared, _, _, policy = rules
    actual = error_type('unexpected rule implementation defect')
    class BrokenCheck:
        def evaluate(self, values):
            raise actual
    changed = RichRulePolicy(prepared)
    raw, when, _ = next(row for row in changed.rules if row[0]['id'] == 'check.reject')
    changed.rules = [(raw, when, BrokenCheck())]
    with pytest.raises(error_type) as caught:
        evaluate(rules, graph_inputs(rules, source_values('good')), policy=changed)
    assert caught.value is actual


def retained_inputs(rules, *, changed_policy=False, unselected_structural=False):
    inputs = graph_inputs(rules, source_values('not selected') if unselected_structural else (formula('x+x'),),
                          property_name='annotation' if unselected_structural else 'value')
    actual = evaluate(rules, inputs)
    _, model, _, _ = rules
    ids = {item.owner: item.key for item in model.identities if item.domain == 'kind'}
    support = (ComputationalSupportReference(derivation_id='unadmitted:prior-episode'),)
    consolidation = DdoRichSelectedMember(product_id='unadmitted:prior-consolidation', member_id=None,
                                          kind_contract=ids[PREFIX + 'DdoRichConsolidation'], support_references=support)
    # An explicitly unadmitted typed-root control. The native owner separately
    # authenticates actual producer/effect/CPU/common receipts and source trust.
    prior = DdoRichAdmission(
        version='rich-admission-1', standing='accepted', members=inputs['graph'].members,
        consolidation=consolidation, policy_authorizations=(), reading_decisions=(),
        eligibility_policy_digest='0' * 64 if changed_policy else actual.eligibility_policy_digest,
        selected_fact_ids=() if unselected_structural else tuple(sorted(actual.selected_fact_ids)),
        selected_occurrence_ids=() if unselected_structural else tuple(sorted(actual.selected_occurrence_ids)),
        selected_reading_ids=(), scientific_representatives=() if unselected_structural else tuple(DdoRichScientificRepresentative(**asdict(item)) for item in actual.scientific_representatives),
    )
    reference = DdoRichSelectedMember(product_id='unadmitted:other-policy-root' if changed_policy else 'unadmitted:prior-root', member_id=None,
                                      kind_contract=ids[PREFIX + 'DdoRichAdmission'], support_references=support)
    selected = RichWholeInput(reference, prior)
    return actual, {
        'context': inputs['context'], 'graph': RichGraphAssembly(members=prior.members, input_population=(reference,)),
        'inputs': (reference,), 'whole_inputs': (selected,), 'retained_graphs': (selected,), 'source_contexts': (),
    }


def test_exact_known_eligibility_is_preserved_without_historical_context_rerating(rules):
    prior, inputs = retained_inputs(rules)
    actual = evaluate(rules, inputs)
    assert actual.decisions == ()
    assert actual.selected_fact_ids == prior.selected_fact_ids
    assert actual.selected_occurrence_ids == prior.selected_occurrence_ids
    assert actual.scientific_representatives == prior.scientific_representatives


def test_known_selection_cannot_claim_current_eligibility_under_other_policy_basis(rules):
    _, inputs = retained_inputs(rules, changed_policy=True)
    with pytest.raises(RichRuleEvaluationRefused, match='different actual policy basis'):
        evaluate(rules, inputs)


def test_known_structural_packets_do_not_gain_selection_from_retained_presence(rules):
    current, inputs = retained_inputs(rules, unselected_structural=True)
    assert len(current.selected_fact_ids) == 1
    assert len(current.selected_occurrence_ids) == 1
    retained = evaluate(rules, inputs)
    assert retained.selected_fact_ids == frozenset()
    assert retained.selected_occurrence_ids == frozenset()
    assert retained.scientific_representatives == ()
