"""Fixed protocol compilation and genuine installed native demand/publication controls."""
from __future__ import annotations

import json
import time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from threading import Barrier

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    native_operation_calls,
    native_operation_declarations,
    native_protocol_sources,
    native_source_digest,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.types import SourceArtifact


def test_kernel_protocol_is_captured_effective_meaning_not_an_ambient_catalog():
    captured = native_protocol_sources()
    declaration = native_operation_declarations(captured)
    model = compile_data_operations(declarations=(declaration,))
    calls = native_operation_calls(model, sources=captured)
    assert {owner for owner, _ in calls} == {operation.semantic_id for operation in model.operations}
    assert len(calls) == 12
    assert all(call.parameters[0].native_parameter == 'p_payload' for _, call in calls)
    assert all(call.result_fields[0].native_field == 'payload' for _, call in calls)
    assert all(call.source_digest == native_source_digest(captured) for _, call in calls)
    altered = tuple(replace(source, content=source.content + b'\n-- changed native behavior\n')
                    if source.name.endswith('.sql') else source for source in captured)
    changed = compile_data_operations(declarations=(native_operation_declarations(altered),))
    original = {(i.owner, i.domain): i.key for i in model.identities}
    revised = {(i.owner, i.domain): i.key for i in changed.identities}
    assert original['data.publish_data_derivation', 'recipe'] != revised['data.publish_data_derivation', 'recipe']
    assert native_operation_declarations(captured).content == declaration.content
    with pytest.raises(ValueError, match='captured'):
        native_operation_calls(model, sources=())


def _declaration():
    return {
        'id': 'urn:ddo-test:source', 'profile': 'derivation', 'subject': 'original-occurrence',
        'context': ['project', 'source', 'analyzed-scope'],
        'roles': [{'name': 'result', 'kind': 'integer', 'direction': 'output',
                   'minimum': 1, 'maximum': None, 'collection': 'sequence', 'presence': 'required'}],
        'applicability': ['admitted'], 'invariants': ['integer'], 'coverage': 'declared-scope',
        'outcomes': ['success', 'empty', 'failed'], 'precision': 'exact', 'dependencies': [],
        'effects': [], 'capabilities': {'forms': ['scalar'], 'preparation': 'none',
            'cancellation': 'transaction-boundary', 'ownership': 'one-claim'},
        'behavior': 'native-test-source-v1', 'parameters': {},
        'binding': {'operator': 'all', 'children': []},
    }


@pytest.fixture(scope='module')
def ddo_kernel_template(native_server, semantic_head_template):
    """Install once through normal candidate authoring; genuine sessions share its clone."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from corpus_structure.semantic.native_candidate import prepare_series_candidate
    from corpus_structure.semantic.native_objects import admit_native
    from native_test_support import SemanticTemplate

    name = 'cs_ddo_kernel_' + uuid4().hex[:12]
    with native_server.database(name, semantic_head_template.name,
                                policy=semantic_head_template.policy) as engine:
        with engine.begin() as connection:
            candidate, authoring = prepare_series_candidate(connection, owned_authoring=True)
            assert candidate.upgrade_ops is not None
            for operation in candidate.upgrade_ops.ops:
                Operations(MigrationContext.configure(connection)).invoke(operation)
            admit_native(connection, authoring.desired)
        engine.dispose()
        yield SemanticTemplate(name, native_server.policy(name))


@pytest.fixture
def ddo_kernel_engine(native_server, ddo_kernel_template):
    name = 'cs_ddo_case_' + uuid4().hex[:12]
    with native_server.database(name, ddo_kernel_template.name,
                                policy=ddo_kernel_template.policy) as engine:
        yield engine


@pytest.fixture
def kernel(ddo_kernel_engine, tmp_path):
    """A real target release/runtime, admitted by the normal owners in the installed DB."""
    from corpus_structure.semantic.data_operation_preparation import prepare_data_operation_inputs
    from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
    from corpus_structure.semantic.data_operation_admission import admit_data_operation_release, bound_data_operation_model
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

    (tmp_path / 'schema.yaml').write_text('''id: urn:ddo-test
name: target
prefixes: {t: 'urn:ddo-test:'}
default_prefix: t
classes: {Thing: {}}
''')
    (tmp_path / 'operations.yaml').write_bytes(canonical_bytes({
        'version': 'data-operation-model-v1', 'operations': [_declaration()], 'kinds': [],
    }))
    (tmp_path / 'target.yaml').write_text('''version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}]
declarations: [{name: test-operations, path: operations.yaml}]
''')
    bundle, dependencies, profile, prepared = prepare_data_operation_inputs(tmp_path, 'target.yaml')
    model = bound_data_operation_model(prepared)
    runtime = prepare_data_operation_runtime(prepared, dependencies.artifacts,
        execution_profile='execution:test', observed={})
    with ddo_kernel_engine.begin() as connection:
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
        connection.execute(insert(table('data.project')).values(project_id='ddo-test'))
    identities = {(item.owner, item.domain): item.key for item in model.identities}
    return {
        'engine': ddo_kernel_engine, 'prepared': prepared, 'model': model,
        'runtime': runtime.runtime_id, 'recipe': identities['urn:ddo-test:source', 'recipe'],
        'kind': identities['primitive:integer', 'kind'] if ('primitive:integer', 'kind') in identities
                else next(i.key for i in model.identities if i.domain == 'kind' and
                     any(k.semantic_id == i.owner and k.name == 'integer' for k in model.kinds)),
    }


def attach(kernel, *, subject='subject:one', inference='inference:test'):
    from corpus_structure.semantic.data_operation_demands import freeze_demand, RootSubject

    root = {'subject': subject, 'original_source': 'source:test', 'analyzed_scope': {'page': 1}}
    selected = freeze_demand(kernel['model'], roots=(RootSubject(subject, 'source:test',
        canonical_bytes(root['analyzed_scope'])),), targets=('urn:ddo-test:source',),
        inference=inference, execution_profile='execution:test').record
    with kernel['engine'].begin() as connection:
        storage = DataOperationStorage(connection)
        demand = storage.invoke('register_data_demand', {'project_id': 'ddo-test',
            'release_id': kernel['prepared'].release_id, 'runtime_id': kernel['runtime'],
            'root': [root], 'selection': selected, 'strength': 'value'})
        obligation = storage.invoke('expand_data_obligation', {
            'demand_id': demand['demand_id'], 'operation_id': 'urn:ddo-test:source',
            **root, 'parameters': {},
        })
        request = SemanticRequestKey(kernel['recipe'], subject, {},
                                    {'parameters': {}, 'replicate': None}, inference)
        wire = {'obligation_id': obligation['obligation_id'],
            'request_meaning': json.loads(request.identity.canonical_input),
            'request_key': request.identity.key, 'binding': {'inputs': [], 'support': [],
                'parameters': semantic_value(request.parameters),
                'request_inputs': semantic_value({}), 'inference': inference}, 'replicate': None}
        attached = storage.invoke('attach_data_request', wire)
    return demand, obligation, wire, attached


def claim(kernel, attached, holder='producer', seconds=30):
    with kernel['engine'].begin() as connection:
        result = DataOperationStorage(connection).invoke('claim_data_request', {
            'request_id': attached['request_id'], 'holder': holder, 'lease_seconds': seconds,
        })
    return {name: result[name] for name in ('request_id', 'generation', 'task_id', 'attempt', 'holder')}


def retain(kernel, fence, *, outputs=(1,), outcome='success', mutate=None):
    completion = {'outcome': outcome, 'inputs': [], 'support': [],
        'implementation_revision': 'native-test-source-v1',
        'outputs': [{'role': 'result', 'position': position, 'multiplicity': 1,
            'product': {'kind_contract': kernel['kind'], 'body': semantic_value(value), 'members': []}}
            for position, value in enumerate(outputs)]}
    if mutate:
        mutate(completion)
    with kernel['engine'].begin() as connection:
        intent = DataOperationStorage(connection).invoke('retain_data_completion_intent', {
            **fence, 'runtime_id': kernel['runtime'], 'completion': completion,
        })
    return intent


def publish(kernel, fence, intent):
    with kernel['engine'].begin() as connection:
        return DataOperationStorage(connection).invoke('publish_data_derivation', {
            **fence, 'intent_id': intent['intent_id'],
        })


def test_native_atomic_publication_and_exact_receipt_replay(kernel):
    demand, _, _, attached = attach(kernel)
    fence = claim(kernel, attached)
    intent = retain(kernel, fence, outputs=(1, 2))
    first = publish(kernel, fence, intent)
    assert first['replayed'] is False
    second = publish(kernel, fence, intent)
    assert second == {**first, 'replayed': True}
    with kernel['engine'].connect() as connection:
        result = DataOperationStorage(connection).invoke('read_demand_result', demand)
        assert result['intent']['root_operations'] == ['urn:ddo-test:source']
        assert result['uses'][0]['fate'] == 'fulfilled'
        assert [p['body'] for p in result['uses'][0]['products']] == [['integer', '1'], ['integer', '2']]
        assert connection.scalar(text('SELECT count(*) FROM ops.data_derivation')) == 1
        assert connection.scalar(text('SELECT count(*) FROM ops.data_publication_receipt')) == 1


def test_native_zero_output_has_authentic_fulfillment(kernel):
    demand, _, _, attached = attach(kernel)
    fence = claim(kernel, attached)
    intent = retain(kernel, fence, outputs=(), outcome='empty')
    publish(kernel, fence, intent)
    with kernel['engine'].connect() as connection:
        result = DataOperationStorage(connection).invoke('read_demand_result', demand)
        assert result['uses'][0]['fate'] == 'fulfilled'
        assert result['uses'][0]['products'] == []
        assert result['uses'][0]['derivation_id']


def test_concurrent_attach_uses_one_visible_request_and_existing_task(kernel):
    _, _, wire, original = attach(kernel)
    barrier = Barrier(2)
    def once():
        with kernel['engine'].begin() as connection:
            barrier.wait(timeout=10)
            return DataOperationStorage(connection).invoke('attach_data_request', wire)
    with ThreadPoolExecutor(max_workers=2) as workers:
        a, b = list(workers.map(lambda _: once(), range(2)))
    assert a['request_id'] == b['request_id'] == original['request_id']
    assert a['task_id'] == b['task_id'] == original['task_id']
    with kernel['engine'].connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM ops.data_request')) == 1
        assert connection.scalar(text('SELECT count(*) FROM ops.task WHERE data_request_id IS NOT NULL')) == 1
        assert connection.scalar(text('SELECT count(*) FROM ops.run')) == 0


def test_conflicting_same_attempt_intent_is_rejected(kernel):
    _, _, _, attached = attach(kernel)
    fence = claim(kernel, attached)
    original = retain(kernel, fence)
    assert retain(kernel, fence) == original
    with pytest.raises(DBAPIError, match='immutable'):
        retain(kernel, fence, outputs=(2,))


def test_expired_owner_cannot_publish_but_exact_intent_can_be_adopted(kernel):
    _, _, _, attached = attach(kernel)
    first = claim(kernel, attached, seconds=1)
    intent = retain(kernel, first)
    time.sleep(1.05)
    second = claim(kernel, attached, holder='successor')
    assert second['attempt'] == first['attempt'] + 1
    with pytest.raises(DBAPIError, match='stale'):
        publish(kernel, first, intent)
    with kernel['engine'].begin() as connection:
        adopted = DataOperationStorage(connection).invoke('adopt_data_completion_intent', {
            **second, 'intent_id': intent['intent_id'],
        })
        assert adopted['producer_attempt'] == first['attempt']
    receipt = publish(kernel, second, intent)
    with kernel['engine'].connect() as connection:
        assert connection.execute(text('SELECT producer_attempt,producer_task_id FROM ops.data_derivation')).one() == (first['attempt'], first['task_id'])
        assert connection.scalar(text('SELECT publishing_attempt FROM ops.data_publication_receipt')) == second['attempt']
        inspected = DataOperationStorage(connection).invoke('inspect_data_completion', {
            'request_id': first['request_id'], 'generation': first['generation'],
            'intent_id': intent['intent_id'],
        })
        assert inspected['receipt_id'] == receipt['receipt_id']
        assert inspected['state'] == 'committed'


@pytest.mark.parametrize('bad', ['body', 'kind', 'role', 'member'])
def test_deliberate_invalid_native_output_rolls_back_every_row(kernel, bad):
    _, _, _, attached = attach(kernel)
    fence = claim(kernel, attached)
    def change(payload):
        output = payload['outputs'][0]
        if bad == 'body': output['product']['body'] = ['string', 'not integer']
        elif bad == 'kind': output['product']['kind_contract'] = 'kind:missing'
        elif bad == 'role': output['role'] = 'undeclared'
        else: output['member_id'] = 'missing-local-member'
    intent = retain(kernel, fence, mutate=change)
    with pytest.raises(DBAPIError):
        publish(kernel, fence, intent)
    with kernel['engine'].connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM kb.data_product')) == 0
        assert connection.scalar(text('SELECT count(*) FROM ops.data_derivation')) == 0
        assert connection.scalar(text('SELECT count(*) FROM ops.data_publication_receipt')) == 0
        assert connection.scalar(text("SELECT status FROM ops.task WHERE data_request_id IS NOT NULL")) == 'running'


def test_revoked_receipt_stays_inspectable_while_current_admission_changes_generation(kernel):
    demand, _, wire, attached = attach(kernel)
    first = claim(kernel, attached)
    intent = retain(kernel, first)
    receipt = publish(kernel, first, intent)
    with kernel['engine'].begin() as connection:
        storage = DataOperationStorage(connection)
        revoked = storage.invoke('revoke_data_support', {'project_id': 'ddo-test',
            'original_source': 'source:test', 'selector_kind': 'derivation',
            'selector': receipt['derivation_id'], 'reason': 'independent producer defect'})
        assert revoked['epoch'] == 1
        inspected = storage.invoke('inspect_data_completion', {
            'request_id': first['request_id'], 'generation': first['generation'],
            'intent_id': intent['intent_id']})
        assert inspected['state'] == 'committed'
        result = storage.invoke('read_demand_result', demand)
        assert result['uses'][0]['fate'] == 'unavailable'
        current = storage.invoke('attach_data_request', wire)
        assert current['generation'] == first['generation'] + 1
        assert current['task_id'] != first['task_id']
    assert publish(kernel, first, intent)['receipt_id'] == receipt['receipt_id']


def test_native_discovery_refuses_arbitrary_member_and_completeness_injection(kernel):
    demand, _, _, _ = attach(kernel)
    with kernel['engine'].begin() as connection:
        with pytest.raises(DBAPIError, match='wire fields'):
            DataOperationStorage(connection).invoke('close_data_population', {
                'demand_id': demand['demand_id'], 'name': 'sentences',
                'members': ['invented'], 'complete': True, 'evidence': {'trust': 'me'},
            })


def test_native_frozen_scope_refuses_unrelated_subject(kernel):
    demand, _, _, _ = attach(kernel)
    with kernel['engine'].begin() as connection:
        with pytest.raises(DBAPIError, match='scope'):
            DataOperationStorage(connection).invoke('expand_data_obligation', {
                'demand_id': demand['demand_id'], 'operation_id': 'urn:ddo-test:source',
                'subject': 'invented', 'original_source': 'source:test',
                'analyzed_scope': {'page': 99}, 'parameters': {},
            })
