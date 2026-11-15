"""Current native complete-reading authority through actual rich selected consumers.

Source conversion/candidate extraction is controlled. Native task, CPU, selected
read, restricted fitter, issuer and rich-admission receipts remain genuine. These
controls do not qualify provider accuracy or population quality.
"""

from copy import deepcopy

import pytest
from evaluate.declared_record_native_support import (
    PROJECT,
    complete_policy_fit,
    retain_references,
    run_grade,
)
from evaluate.declared_rich_native_support import (
    current_rich_policy as current_rich_policy,
)
from evaluate.declared_rich_native_support import (
    rich_policy_recipe,
    run_rich_admission,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_current_rich_recipe_preserves_actual_producers_and_complete_reading_fields(tmp_path):
    from semantic.data_operation_kernel_support import prepare_kernel

    preparation = prepare_kernel(rich_policy_recipe(tmp_path))
    model = preparation.model
    assert {'fixture.record_candidates', 'resolve.m1_readings/declared', 'record_policy.grade',
            'record_policy.fit', 'record_policy.authorize', 'rich.consolidate', 'rich.admit'} <= {operation.semantic_id for operation in model.operations}
    assert all(implementation.complete for implementation in model.implementation_slices)
    assert {prop.name for prop in preparation.prepared.index.definitions['TableAssertionReading'].properties} == {'id', 'label', 'aliases', 'value', 'location'}
    consolidation = model.operation('rich.consolidate')
    admission = model.operation('rich.admit')
    for operation in (consolidation, admission):
        roles = {role.name: role for role in operation.roles}
        assert roles['records'].collection == roles['readings'].collection == 'set'
        assert roles['records'].support is not None and roles['readings'].support is not None
        assert roles['records'].support.source_set == 'rich-records'
        assert roles['readings'].support.source_set == 'rich-readings'
    assert consolidation.effects == ()
    assert tuple(effect.name for effect in admission.effects) == ('native-rich-knowledge-admission',)


def test_actual_rich_admission_keeps_complete_reading_authority_separate_from_scientific_truth(current_rich_policy, monkeypatch):
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSourceReadingAssertion
    from corpus_structure.semantic.rich_queries import ClaimsQuery, SourceReadingsQuery
    from corpus_structure.serve.rich_queries import RichQueryRequest, serve_rich_query

    journey = current_rich_policy
    fitted = complete_policy_fit(journey)
    _, authorizations, *_ = journey.selected_products(journey.kernel.purpose('write'), fitted.demand_id,
        kind='https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization')
    ((authorization, _),) = authorizations
    source = next(source for source in journey.sources if source.pin == fitted.calibration.grade.frame.coverage[0].source)
    selected = run_rich_admission(journey, fitted.calibration_readings, authorization, selected_source=source,
                                 inference='actual-complete-reading-rich-admission')
    decisions = selected.admission.reading_decisions
    assert len(decisions) == 4
    accepted = tuple(value for value in decisions if value.outcome == 'accepted')
    rejected = tuple(value for value in decisions if value.outcome != 'accepted')
    assert len(accepted) == len(rejected) == 2
    assert {value.reason_code for value in rejected} == {'incomplete-source-reading'}
    assert len(selected.admission.selected_reading_ids) == 2
    assert selected.admission.selected_fact_ids == selected.admission.selected_occurrence_ids == ()
    assertions = tuple(packet.body for packet in selected.admission.members if isinstance(packet.body, DdoRichSourceReadingAssertion))
    assert {row.reading_id for row in assertions} == set(selected.admission.selected_reading_ids)
    for decision in accepted:
        (assertion,) = [row for row in assertions if row.reading_id == decision.assertion_member_id]
        assert (assertion.original, assertion.resolution, assertion.resolved) == (decision.original, decision.resolution, decision.resolved)
        assert assertion.source_interpretation_id == decision.source_interpretation_id
        assert assertion.interpretation_id == decision.interpretation_id
        assert assertion.source_interpretation_id != assertion.interpretation_id
    assert not {value.original.member_id for value in rejected} & {row.original.member_id for row in assertions}

    # Actual direct raw/resolution computation support, never a synthesized agent
    # observation or a guessed member-to-episode relationship.
    with journey.kernel.engine.begin() as connection:
        assert connection.scalar(text('SELECT ops.ddo_support_valid(:episode)'), {'episode': selected.episode}) is True
        for assertion in assertions:
            for reference, operation in ((assertion.original, 'fixture.record_candidates'),
                                         (assertion.resolution, 'resolve.m1_readings/declared')):
                assert len(reference.support_references) == 1
                support = reference.support_references[0]
                assert isinstance(support, ComputationalSupportReference)
                episode = support.derivation_id
                assert connection.scalar(text('SELECT request.operation_id FROM ops.data_derivation episode JOIN ops.data_request request ON request.id=episode.request_id WHERE episode.id=:episode'), {'episode': episode}) == operation
    with journey.kernel.purpose('write').begin() as connection:
        page = serve_rich_query(connection, RichQueryRequest(project_id=PROJECT, demand_id=selected.demand_id,
            product_id=selected.product['id'], query=SourceReadingsQuery(name='source_readings')))
        claims = serve_rich_query(connection, RichQueryRequest(project_id=PROJECT, demand_id=selected.demand_id,
            product_id=selected.product['id'], query=ClaimsQuery(name='claims')))
    assert len(page['rows']) == 2 and claims['rows'] == []
    identity = frozenset(journey.kernel.prepared.index.definitions['TableAssertionReading'].identity_slots)
    assert identity == frozenset({'id'})
    fields = [field for row in page['rows'] for name, field in decode_semantic_value(row['reading']).items() if name not in identity]
    assert len(fields) == 4 and all(field['state'] == 'present' for field in fields)
    assert {row['scientific_truth'] for row in page['rows']} == {'not-established'}

    refuse_grade_label_substitution(fitted, monkeypatch)
    for attack in ("decision", "missing-cpu"):
        refuse_rich_completion_substitution(fitted, authorization, source, monkeypatch, attack=attack)
    refuse_resolution_score_substitution(fitted, authorization, monkeypatch)

    # Current transitive source trust remains required after native admission;
    # original equal bytes and a previously successful read do not repair it.
    from typing import cast

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    with journey.kernel.engine.begin() as connection:
        DataOperationStorage(connection).revoke_data_support(cast(WireRevokeDataSupportRequest, {
            'project_id': PROJECT, 'original_source': source.pin.original_source,
            'selector_kind': 'product', 'selector': source.pin.source_product,
            'reason': 'controlled genuine rich source-product revocation',
        }))
        assert connection.scalar(text('SELECT ops.ddo_support_valid(:episode)'), {'episode': selected.episode}) is False


def refuse_grade_label_substitution(fitted, monkeypatch):
    """Preserve a real CPU receipt while changing a self-consistent typed label."""
    from corpus_structure.evaluate.declared_record_policy import DdoRecordGrade
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_identity import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.record_policy import RecordAlgorithm

    journey = fitted.journey
    sources = tuple(source for source in journey.sources if source.pin in {row.source for row in fitted.feature.grade.frame.coverage})
    populations, references = retain_references(journey, sources, partition='development')
    specification = fitted.feature_readings.specification.model_copy(update={'algorithm': RecordAlgorithm(inverse_regularization=2.0)})
    actual_retain = DataOperationStorage.retain_data_completion_intent
    refused = []
    def substitute(storage, payload):
        if payload['completion']['outputs'] and payload['completion']['outputs'][0]['role'] == 'grade':
            altered = deepcopy(payload)
            original = payload['completion']
            grade = DdoRecordGrade.from_selected_body(decode_semantic_value(original['outputs'][0]['product']['body']))
            assert grade.frame.events
            first, *rest = grade.frame.events
            frame = grade.frame.model_copy(update={'events': (first.model_copy(update={'correct': not first.correct}), *rest)})
            changed = DdoRecordGrade.from_frame(frame)
            altered['completion']['outputs'][0]['product']['body'] = semantic_value(changed.model_dump(mode='python'))
            assert altered['completion']['execution_evidence'] == original['execution_evidence']
            assert len(original['execution_evidence']['cpu_receipts']) == len(original['execution_evidence']['cpu_replies']) == 1
            try:
                return actual_retain(storage, altered)
            except DBAPIError as error:
                refused.append(error)
                raise
        return actual_retain(storage, payload)
    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, 'retain_data_completion_intent', substitute)
        with pytest.raises(NativeDemandExecutionError):
            run_grade(journey, sources, populations, references, specification, fitted.feature_readings.resolved,
                      inference='actual-grade-label-substitution-refusal')
    assert len(refused) == 1
    assert getattr(refused[0].orig, 'sqlstate', None) == '23514'
    assert 'actual CPU result and reference basis' in str(refused[0].orig)


def refuse_rich_completion_substitution(fitted, authorization, source, monkeypatch, *, attack):
    """Neither a body alone nor a substituted decision acquires native authority."""
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_identity import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichAdmission
    from corpus_structure.semantic.rich_policy_binding import rich_policy_value

    journey = fitted.journey
    current_policy = rich_policy_value(journey.kernel.prepared, journey.kernel.model)
    size = 1 if attack == "decision" else 2
    allowed = current_policy.allowed_domain_contracts[:size]
    assert len(current_policy.allowed_domain_contracts) > 2
    actual_retain = DataOperationStorage.retain_data_completion_intent
    refused = []
    requests = []
    def substitute(storage, payload):
        outputs = payload['completion']['outputs']
        if outputs and outputs[0]['role'] == 'admission':
            altered = deepcopy(payload)
            if attack == "missing-cpu":
                # Preserve the genuinely computed complete graph and actual
                # native task fence, but omit computation authority. This is the
                # current counterpart of a plain graph append without admission.
                altered['completion']['execution_evidence']['cpu_receipts'] = []
                altered['completion']['execution_evidence']['cpu_replies'] = []
                assert altered['completion']['outputs'] == payload['completion']['outputs']
            else:
                body = decode_semantic_value(outputs[0]['product']['body'])
                accepted = next(row for row in body['reading_decisions'] if row['outcome'] == 'accepted')
                removed = accepted['assertion_member_id']
                accepted.update(outcome='below-threshold', reason_code='below-threshold', assertion_member_id=None, probability_hex=0.0.hex())
                body['selected_reading_ids'] = [identifier for identifier in body['selected_reading_ids'] if identifier != removed]
                DdoRichAdmission.model_validate(body)
                altered['completion']['outputs'][0]['product']['body'] = semantic_value(body)
                assert altered['completion']['execution_evidence'] == payload['completion']['execution_evidence']
            requests.append(payload['request_id'])
            try:
                return actual_retain(storage, altered)
            except DBAPIError as error:
                refused.append(error)
                raise
        return actual_retain(storage, payload)
    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, 'retain_data_completion_intent', substitute)
        with pytest.raises(NativeDemandExecutionError):
            run_rich_admission(journey, fitted.calibration_readings, authorization, selected_source=source,
                               inference='actual-rich-completion-' + attack + '-refusal', policy_contracts=allowed)
    assert len(refused) == 1
    assert getattr(refused[0].orig, 'sqlstate', None) == '23514'
    assert 'CPU' in str(refused[0].orig)
    assert len(requests) == 1
    with journey.kernel.engine.begin() as connection:
        assert connection.scalar(text('SELECT count(*) FROM ops.data_derivation WHERE request_id=:request'), {'request': requests[0]}) == 0


def refuse_resolution_score_substitution(fitted, authorization, monkeypatch):
    """A real original resolution reply cannot attest a substituted score body."""
    import json

    from evaluate.declared_record_native_support import run_readings

    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_identity import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.observations import source_python, source_value
    from corpus_structure.semantic.reading_resolution_products import (
        RECIPE,
        DeclaredReadingFeatureInstance,
    )
    from corpus_structure.semantic.record_policy_authority import DdoFittedRecordPolicy

    journey = fitted.journey
    private = DdoFittedRecordPolicy.model_validate(fitted.fitted)
    source = next(source for source in journey.sources if source.pin == fitted.feature.grade.frame.coverage[0].source)
    policy = dict(version='reading-feature-policy-2', recipe=RECIPE, subset=private.instance.feature.applicability.subset,
        feature_instances=source_value([DeclaredReadingFeatureInstance(feature=private.instance.feature,
            family_contract=private.family_contract, reading_recipe=private.reading_recipe).model_dump(mode='python')]))
    kind = journey.kernel.identities['https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoResolvedReadingReport', 'kind']
    actual_retain = DataOperationStorage.retain_data_completion_intent
    substituted = []
    def substitute(storage, payload):
        outputs = payload['completion']['outputs']
        if outputs and outputs[0]['product']['kind_contract'] == kind:
            altered = deepcopy(payload)
            body = decode_semantic_value(outputs[0]['product']['body'])
            events = source_python(body['reading_events'])
            event = next(row for row in events if row['outcome'] == 'completed')
            event['final_event_score'] += 1.0
            event['score']['compatibility_potential'] = event['final_event_score']
            body['reading_events'] = source_value(events)
            details = json.loads(body['diagnostics_json'])
            details['record_policy_events'] = events
            body['diagnostics_json'] = json_bytes(details).decode()
            journey.kernel.prepared.validate_json('DdoResolvedReadingReport', json_bytes(body))
            altered['completion']['outputs'][0]['product']['body'] = semantic_value(body)
            assert altered['completion']['execution_evidence'] == payload['completion']['execution_evidence']
            substituted.append(altered)
            return actual_retain(storage, altered)
        return actual_retain(storage, payload)
    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, 'retain_data_completion_intent', substitute)
        readings = run_readings(journey, (source,), policy=policy, inference='actual-original-resolution-score-substitution')
    assert len(substituted) == 1
    actual_retain = DataOperationStorage.retain_data_completion_intent
    refused = []
    def observe(storage, payload):
        try:
            return actual_retain(storage, payload)
        except DBAPIError as error:
            refused.append(error)
            raise
    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, 'retain_data_completion_intent', observe)
        with pytest.raises(NativeDemandExecutionError):
            run_rich_admission(journey, readings, authorization, selected_source=source,
                               inference='actual-forged-resolution-cannot-authorize-rich-knowledge')
    assert len(refused) == 1
    assert getattr(refused[0].orig, 'sqlstate', None) == '23514'
    assert 'CPU' in str(refused[0].orig) and ('reading' in str(refused[0].orig) or 'resolution' in str(refused[0].orig))
