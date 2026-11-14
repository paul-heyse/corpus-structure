"""Native stream publication is atomic at terminal evidence, including empty output."""

from dataclasses import replace

import pytest
from sqlalchemy import text

from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError, NativeDemandExecutor
from corpus_structure.semantic.data_operation_demands import DemandPlanner, OperationSelection, RootSubject, freeze_demand
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_kernel_support import EXECUTION


def stream_recipe():
    declaration = source_declaration()
    declaration['id'] = 'urn:ddo-stream:answer'
    declaration['roles'][0].update(kind='primitive:integer', minimum=0, presence='optional')
    declaration['parameters'] = {'value': {'value_type': 'integer', 'default': 2}}
    declaration['capabilities'].update(forms=['stream'], cancellation='call-boundary', stream_settlement={'mode': 'terminal-atomic', 'output_role': 'result', 'terminal_outcome': 'success'})
    declaration['opaque'] = [{'reference': 'collections.abc.Iterator', 'contract': 'python-iterator-annotation', 'role': 'annotation', 'content_digest': 'a' * 64}]
    broken = {**declaration, 'id': 'urn:ddo-stream:broken'}
    source = ('from collections.abc import Iterator\n'
              'def answer(*, value: int = 2) -> Iterator[int]:\n'
              '    for index in range(value):\n'
              '        yield index + 10\n'
              f'answer__data_operation__ = {declaration!r}\n'
              'def broken(*, value: int = 2) -> Iterator[int]:\n'
              '    yield value\n'
              '    yield "invalid-prefix-success"\n'
              f'broken__data_operation__ = {broken!r}\n')
    name = 'ddo_native_stream_fixture'
    return replace(EXECUTION, name='native-stream', manifest_text=EXECUTION.manifest_text.replace('ddo_execution_fixture', name), python_sources=((name, name+'.py', source.encode()),))


STREAM = stream_recipe()
pytestmark = pytest.mark.parametrize('ddo_kernel', [STREAM], indirect=True, ids=['native-stream'])


@pytest.fixture
def stream_execution(ddo_kernel, monkeypatch):
    preparation = ddo_kernel.preparation
    monkeypatch.syspath_prepend(str(preparation.directory))
    sources = PythonSourceCollection(tuple(PythonSource(module, content, filename) for module, filename, content in STREAM.python_sources))
    locations = {module: preparation.directory / filename for module, filename, _ in STREAM.python_sources}
    executor = NativeDemandExecutor(ddo_kernel.engine, ddo_kernel.prepared, preparation.runtime, sources, runtime_locations=locations, schema=preparation.bundle)
    return ddo_kernel, executor


def register(kernel, operation, value=2, *, extra_targets=()):
    intent = freeze_demand(kernel.model, roots=(RootSubject('stream:one', 'original:one', b'{}'),), targets=(operation, *extra_targets), selections=(OperationSelection(operation, canonical_bytes({'value': value})),), inference='exact', execution_profile='execution:test')
    with kernel.engine.begin() as connection:
        return DemandPlanner(kernel.model, DataOperationStorage(connection)).register(intent, project='execution', release=kernel.prepared.release_id, runtime=kernel.runtime)['demand_id']


@pytest.mark.parametrize('count', [0, 2])
def test_native_stream_terminal_publishes_exact_order_and_settled_resume(stream_execution, count):
    kernel, executor = stream_execution
    demand = register(kernel, 'urn:ddo-stream:answer', count)
    result = executor.run(demand)
    assert result.receipt_count == 1
    with kernel.engine.begin() as connection:
        snapshot = DataOperationStorage(connection).invoke('read_demand_result', {'demand_id': demand, 'view': 'products'})
        assert snapshot['uses'][0]['fate'] == 'fulfilled'
        assert [product['body'] for product in snapshot['uses'][0]['products']] == [['integer', str(index + 10)] for index in range(count)]
        before = connection.execute(text('SELECT count(*) FROM ops.data_derivation UNION ALL SELECT count(*) FROM ops.data_completion_intent UNION ALL SELECT count(*) FROM ops.data_publication_receipt')).scalars().all()
        assert before == [1, 1, 1]
        retained = dict(connection.execute(text('SELECT id AS intent_id, request_id, generation, producer_task_id AS task_id, producer_attempt AS attempt, producer_holder AS holder FROM ops.data_completion_intent')).mappings().one())
        replayed = DataOperationStorage(connection).invoke('publish_data_derivation', retained)
        import json
        original = json.loads(result.receipts[0])
        assert replayed == {**original, 'replayed': True}
    resumed = executor.run(demand)
    assert resumed.receipt_count == 0
    with kernel.engine.connect() as connection:
        assert connection.execute(text('SELECT count(*) FROM ops.data_derivation UNION ALL SELECT count(*) FROM ops.data_completion_intent UNION ALL SELECT count(*) FROM ops.data_publication_receipt')).scalars().all() == before
    assert executor.budget.used_bytes == 0


def test_native_invalid_stream_prefix_has_no_product_intent_or_fulfillment(stream_execution):
    kernel, executor = stream_execution
    demand = register(kernel, 'urn:ddo-stream:broken')
    with pytest.raises(NativeDemandExecutionError):
        executor.run(demand)
    with kernel.engine.begin() as connection:
        assert connection.execute(text('SELECT count(*) FROM kb.data_product UNION ALL SELECT count(*) FROM ops.data_derivation UNION ALL SELECT count(*) FROM ops.data_completion_intent UNION ALL SELECT count(*) FROM ops.data_publication_receipt')).scalars().all() == [0, 0, 0, 0]
        snapshot = DataOperationStorage(connection).invoke('read_demand_result', {'demand_id': demand, 'view': 'products'})
        assert not any(use['fate'] == 'fulfilled' for use in snapshot['uses'])
    assert executor.budget.used_bytes == 0



def test_cancelled_demand_preserves_live_cross_demand_stream_and_original_episode(stream_execution, monkeypatch):
    from corpus_structure.semantic import data_operation_stream

    kernel, executor = stream_execution
    first = register(kernel, 'urn:ddo-stream:answer')
    second = register(kernel, 'urn:ddo-stream:answer', extra_targets=('urn:ddo-stream:broken',))
    assert first != second
    ready = []
    with kernel.engine.begin() as connection:
        planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
        for demand in (first, second):
            snapshot = planner.resume(demand)
            selected = planner.ready(snapshot, authorization=b'{}')
            ready.append(next(item for item in selected if item.operation == 'urn:ddo-stream:answer'))
    import json
    assert json.loads(ready[0].native)['request_id'] == json.loads(ready[1].native)['request_id']
    original_pull = data_operation_stream.OwnedCPUStream.pull
    cancellations = []

    def cancel_after_prefix(stream):
        if stream.ordinal == 1 and not cancellations:
            with kernel.engine.begin() as connection:
                cancellations.append(DataOperationStorage(connection).invoke('cancel_data_demand', {'demand_id': first, 'reason': 'selected-cancellation'}))
        return original_pull(stream)

    monkeypatch.setattr(data_operation_stream.OwnedCPUStream, 'pull', cancel_after_prefix)
    result = executor.run(first)
    assert result.receipt_count == 1
    assert cancellations and cancellations[0]['requests'][0]['interest'] == 'shared'
    with kernel.engine.begin() as connection:
        storage = DataOperationStorage(connection)
        assert storage.invoke('read_demand_result', {'demand_id': first})['state'] == 'cancelled'
        surviving = storage.invoke('read_demand_result', {'demand_id': second, 'view': 'products'})
        use = next(use for use in surviving['uses'] if use['request_id'] == json.loads(ready[1].native)['request_id'])
        assert use['fate'] == 'fulfilled'
        assert [product['body'] for product in use['products']] == [['integer', '10'], ['integer', '11']]
        assert connection.scalar(text('SELECT count(*) FROM ops.data_derivation')) == 1
    assert executor.budget.used_bytes == 0



def test_uncertain_stream_submission_settles_only_after_drain_and_can_resume(stream_execution, monkeypatch):
    from corpus_structure.semantic.cpu_execution import CPUExecutionScope

    kernel, executor = stream_execution
    demand = register(kernel, 'urn:ddo-stream:answer')
    original = CPUExecutionScope.submit_closed_python_stream
    scopes = []

    def acknowledgement_lost(cpu, *args, **kwargs):
        scopes.append(cpu)
        original(cpu, *args, **kwargs)
        raise RuntimeError('stream transport acknowledgement lost')

    with monkeypatch.context() as changed:
        changed.setattr(CPUExecutionScope, 'submit_closed_python_stream', acknowledgement_lost)
        with pytest.raises(NativeDemandExecutionError) as failure:
            executor.run(demand)
    assert any('acknowledgement lost' in str(error) for error in failure.value.failures)
    assert scopes and all(scope._physical_retired for scope in scopes)
    with kernel.engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM ops.data_attempt_failure')) == 1
        assert connection.scalar(text('SELECT count(*) FROM ops.data_completion_intent')) == 0
    assert executor.budget.used_bytes == 0
    resumed = executor.run(demand)
    assert resumed.receipt_count == 1
    with kernel.engine.connect() as connection:
        assert connection.scalar(text('SELECT count(*) FROM ops.data_derivation')) == 1
    assert executor.budget.used_bytes == 0
