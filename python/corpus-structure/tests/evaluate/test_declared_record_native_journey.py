"""Actual current protected grade/fitting journeys; controlled extraction only."""

from pathlib import Path

from evaluate.declared_record_native_support import policy_recipe


def test_current_record_policy_journey_recipe_has_real_closed_producers(tmp_path):
    from semantic.data_operation_kernel_support import prepare_kernel
    recipe = policy_recipe(tmp_path)
    captured = recipe.captured_inputs
    assert captured is not None
    preparation = prepare_kernel(recipe)
    model = preparation.model
    assert {'fixture.record_candidates', 'resolve.m1_readings/declared', 'record_policy.grade', 'record_policy.fit', 'record_policy.authorize'} <= {item.semantic_id for item in model.operations}
    assert all(item.complete for item in model.implementation_slices)
    assert model.operation('record_policy.grade').subject == model.operation('record_policy.fit').subject
    # Check the controlled extractor and independently authored reference values
    # against the actual compiled current family before the native journey runs.
    # These local unadmitted values establish kernel semantics only.
    from types import SimpleNamespace
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.data_operation_model import SubjectContext, json_context_meaning
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.record_contracts import bind_record_candidates
    from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame, whole_reading_correct
    from evaluate.declared_record_native_support import SourceChoice, reference_records
    from evaluate.declared_record_candidate_fixture import candidate_values
    selected = DeclaredStructuralSource(source='["unadmitted-source",null]',source_product='unadmitted-source',
        subject='unadmitted-subject',subject_definition=model.operation('fixture.record_candidates').subject,
        document='unadmitted-original',original_source='unadmitted-original',projection_digest='a'*64,
        section_pointer='#/tables/0',membership='direct',project_id=PROJECT,analyzed_scope_meaning=json_context_meaning(b'{}').decode(),
        kind_contract=next(item.key for item in model.identities if item.domain=='kind' and item.owner=='https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource'))
    pin = selected.model_dump(mode='json',exclude_none=True)
    body = {'items':[{'label':'table','self_ref':'#/tables/0','data':{'table_cells':[{'text':'12'},{'text':'12'}]}}]}
    context=SubjectContext(PROJECT,selected.subject,selected.original_source,b'{}',subject_definition=selected.subject_definition)
    fake_journey=SimpleNamespace(kernel=SimpleNamespace(prepared=preparation.prepared,model=model))
    references,coordinates=reference_records(fake_journey,SourceChoice(selected,body,context))
    candidates,actual_coordinates=candidate_values(preparation.prepared,body,pin,model=model,check_active=lambda:None)
    assert actual_coordinates==coordinates
    bind_record_candidates(preparation.prepared,model=model,source=selected.source,records=candidates,coordinate_texts=coordinates)
    frame=RecordEvaluationFrame(unit='controlled-kernel-only',release_id=preparation.prepared.release_id,
        guideline_version='complete-native-cell-source-only-1',reference_policy_version='independent-source-reference-1',
        prediction_policy_version='m1-grouped-reading-logistic-1',pin=pin,
        anchor_ids=frozenset(anchor['anchor_id'] for row in references for anchor in row['anchors']))
    actual=[whole_reading_correct(preparation.prepared,row,references,frame,reference_model=model,prediction_model=model,coordinate_texts=coordinates) for row in candidates]
    assert actual==[True,False,True,False]


import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from evaluate.declared_record_native_support import (
    current_record_policy as current_record_policy,
    complete_policy_fit, copy_grade, retain_references, run_readings, run_grade, PROJECT,
)


def test_actual_grade_fit_authorization_and_restricted_fitter_custody(current_record_policy):
    """Real native publications and purposes; extraction remains controlled."""
    from typing import cast
    from corpus_structure.evaluate.declared_record_policy import reacquire_record_feature_grade
    from corpus_structure.semantic.record_policy_authority import DdoRecordPolicyAuthorization, DdoFittedRecordPolicy
    from corpus_structure.semantic._data_operation_wire import WireReadRecordFeatureFitFrameRequest, WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identity import canonical_bytes
    fitted = complete_policy_fit(current_record_policy)
    journey = fitted.journey
    authorization = DdoRecordPolicyAuthorization.model_validate_json(canonical_bytes(fitted.authorization))
    assert authorization.family_contract == fitted.feature.grade.frame.family_contract
    assert authorization.reading_recipe == fitted.feature.grade.frame.reading_recipe
    assert authorization.source_release_id == fitted.feature.grade.frame.prediction_release_id
    private = DdoFittedRecordPolicy.model_validate_json(canonical_bytes(fitted.fitted))
    assert authorization.policy_instance_digest == private.instance.digest
    assert 'fit' not in fitted.authorization and 'frame' not in fitted.authorization and 'instance' not in fitted.authorization
    with journey.kernel.purpose('fit').begin() as connection:
        acquired = reacquire_record_feature_grade(connection, fitted.feature.selection)
    assert acquired == fitted.feature.grade
    assert len(acquired.frame.events) == 8 and {row.correct for row in acquired.frame.events} == {True, False}
    assert len({row.origin_group for row in acquired.frame.events}) == 2
    assert all(row.exposed_outputs == () for row in acquired.frame.reference_passes)
    assert {row.author for row in acquired.frame.reference_passes} == {'controlled operator'}
    assert fitted.calibration.grade.frame.held_out_from == (acquired.frame_digest,)
    assert set(row.source.original_source for row in acquired.frame.events).isdisjoint(row.source.original_source for row in fitted.calibration.grade.frame.events)

    # The actual evaluator login and a privileged login using SET ROLE are both
    # refused; a role label does not become the restricted fitting capability.
    with journey.kernel.purpose('evaluate').begin() as connection:
        with pytest.raises(DBAPIError, match='restricted actual fitting principal'):
            with connection.begin_nested():
                reacquire_record_feature_grade(connection, fitted.feature.selection)
    with journey.kernel.engine.begin() as connection:
        connection.exec_driver_sql('SET LOCAL ROLE corpus_sem_fitter')
        with pytest.raises(DBAPIError, match='restricted actual fitting principal'):
            with connection.begin_nested():
                reacquire_record_feature_grade(connection, fitted.feature.selection)
    with journey.kernel.purpose('fit').begin() as connection:
        with pytest.raises(DBAPIError, match='feature fit'):
            with connection.begin_nested():
                reacquire_record_feature_grade(connection, fitted.calibration.selection)
        payload = fitted.feature.selection.model_dump(mode='json')
        payload['expected_cut'] = 'cut-selection:' + '0' * 64
        payload['max_bytes'] = 8388608
        with pytest.raises(DBAPIError, match='cut bytes or native pins'):
            with connection.begin_nested():
                DataOperationStorage(connection).read_record_feature_fit_frame(cast(WireReadRecordFeatureFitFrameRequest, payload))

    # Ordinary authored bodies remain authored. The maintained protected
    # authoring service accepts reference/specification inputs, never conclusions
    # or an authored lookalike of a native source product.
    from corpus_structure.evaluate.declared_record_policy import author_record_policy_inputs, PROTECTED_NAMESPACE
    from corpus_structure.semantic.refusals import SemanticRefusal
    from evaluate.declared_record_native_support import authored, project_context, request
    context = project_context(journey, 'record_policy.grade')
    for kind, body in (
        (PROTECTED_NAMESPACE + 'DdoRecordGrade', fitted.feature.grade.model_dump(mode='json')),
        ('https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource', journey.sources[0].body),
    ):
        fact = authored(journey, 'unsupported-authored-conclusion', body, kind=kind, context=context)
        malformed = request(journey, ('record_policy.grade',), (context,), originals=(fact,), inference='authored-lookalike-refusal')
        with pytest.raises(SemanticRefusal, match='only source-only references and exact specifications'):
            author_record_policy_inputs(journey.kernel.purpose('evaluate'), journey.kernel.prepared, request=malformed)

    # This is an actual different captured CPU producer/common receipt, carrying
    # exactly the same protected body. It is deliberately not a grade authority.
    copied = copy_grade(journey, fitted.feature)
    with journey.kernel.purpose('fit').begin() as connection:
        with pytest.raises(DBAPIError, match='actual admitted protected grade implementation'):
            with connection.begin_nested():
                reacquire_record_feature_grade(connection, copied.selection)

    # An actually completed empty carrier is a known no-output opportunity,
    # preserving its source and product outside the scored-event denominator.
    empty_sources = journey.sources[:1]
    passes, facts = retain_references(journey, empty_sources, partition='development')
    specification, predictions = run_readings(journey, empty_sources, policy=None,
        inference='actual-completed-empty-carrier', empty_sources=(empty_sources[0].pin.source,))
    empty = run_grade(journey, empty_sources, passes, facts, specification, predictions, inference='actual-empty-carrier-grade')
    assert empty.grade.frame.events == ()
    (coverage,) = empty.grade.frame.coverage
    assert coverage.outcome == 'no_output' and coverage.event_ids == ()
    assert len(coverage.outputs) == 1 and coverage.source == empty_sources[0].pin

    # Current trust gates both the restricted original grade and the genuine
    # authorization's transitive support; historical equal bodies do not repair it.
    with journey.kernel.purpose('evaluate').begin() as connection:
        _, products, _, episodes, outputs = journey.selected_products(journey.kernel.purpose('evaluate'), fitted.demand_id,
            kind='https://corpus-structure.dev/semantic/data-operation-record-policy/DdoRecordPolicyAuthorization')
        product, _ = products[0]
        (issuer,) = [row['derivation_id'] for row in outputs if row['product_id'] == product['id'] and row['role'] == 'authorization']
    with journey.kernel.engine.begin() as connection:
        assert connection.scalar(text('SELECT ops.ddo_support_valid(:episode)'), {'episode': issuer}) is True
        source = journey.sources[0].pin
        DataOperationStorage(connection).revoke_data_support(cast(WireRevokeDataSupportRequest, dict(
            project_id=PROJECT, original_source=source.original_source, selector_kind='product', selector=source.source_product,
            reason='controlled exact source-product revocation',
        )))
        assert connection.scalar(text('SELECT ops.ddo_support_valid(:episode)'), {'episode': issuer}) is False
    with journey.kernel.purpose('fit').begin() as connection:
        with pytest.raises(DBAPIError, match='trust|selected support'):
            reacquire_record_feature_grade(connection, fitted.feature.selection)
