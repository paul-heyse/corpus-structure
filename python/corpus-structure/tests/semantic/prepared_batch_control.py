"""A genuinely executed integral prepared batch control, with no provider claim."""
from typing import ClassVar


def run_controlled_batch(receiver, index):
    return tuple(value + 1 for value in index)


class ControlledBatchOperation:
    __data_operation__: ClassVar[dict] = {'id': 'urn:controlled:prepared-batch-add-one',
 'profile': 'derivation',
 'subject': 'controlled-value',
 'subject_definition': {'id': 'controlled-value', 'identifier_kind': 'string', 'scope': 'project'},
 'discovery_relation': 'role-associated',
 'context': ['controlled-exact-integer'],
 'entrypoints': ['run'],
 'roles': [{'name': 'index',
            'parameter': 'index',
            'kind': 'integer',
            'direction': 'input',
            'minimum': 1,
            'maximum': 1,
            'collection': 'scalar',
            'presence': 'required',
            'support': {'provenance': 'exact',
                        'source': 'explicit-authored-control-value',
                        'coverage': {'role': 'index', 'description': 'one-controlled-integer'},
                        'origins': ['authored'],
                        'identity_requirements': ['original-source']}},
           {'name': 'result',
            'kind': 'integer',
            'direction': 'output',
            'minimum': 1,
            'maximum': 1,
            'collection': 'scalar',
            'presence': 'required'}],
 'applicability': [],
 'invariants': [],
 'coverage': {'binding': 'self',
              'result_owners': [{'kind': 'implementation', 'reference': 'self'}],
              'description': 'one-exact-integer'},
 'outcomes': ['success'],
 'precision_description': None,
 'replicate_policy': 'explicit-replicates',
 'dependencies': [],
 'effects': [],
 'capabilities': {'forms': ['batch'],
                  'preparation': 'resource',
                  'prepared_factory': 'acquire_port',
                  'cancellation': 'cooperative',
                  'ownership': 'existing-invocation-cpu-owner'},
 'behavior': 'exact-integer-add-one',
 'parameters': {},
 'binding': {'operator': 'scan', 'roles': ['index']},
 'opaque': [{'reference': 'semantic.prepared_batch_control.run_controlled_batch',
             'contract': 'controlled-batch/algorithm',
             'role': 'original-exact-integer-computation'}],
 'assets': [{'reference': 'integer-algorithm',
             'contract': 'controlled-batch/algorithm',
             'role': 'actual-controlled-integer-owner'}]}

    def __init__(self, execute):
        self.execute = execute

    def run(self, index: tuple[int, ...]) -> tuple[int, ...]:
        return run_controlled_batch(self, index)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        return resolve_controlled_port(prepared, model, operation, identity=identity,
            authorize=authorize, custody=custody, sources=sources)


def controlled_sources():
    from pathlib import Path
    from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
    from corpus_structure.semantic.types import SourceArtifact
    from corpus_structure.semantic.identity import canonical_bytes
    path = Path(__file__).resolve()
    return PythonSourceCollection((PythonSource(__name__, path.read_bytes(), str(path)),),
        boundary_contracts=(SourceArtifact('controlled-batch/algorithm', canonical_bytes(
            dict(arithmetic='exact-integer-add-one', source=path.read_bytes().hex()))),))


def controlled_kernel(members: tuple[dict, ...], *, check_active) -> dict:
    from corpus_structure.semantic.data_operation_identity import decode_semantic_value
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_batch_reply
    values = []
    for member in members:
        check_active()
        basis = decode_semantic_value(member['input_basis'])
        rows = basis['roles']
        if len(rows) != 1 or rows[0]['role'] != 'index' or type(rows[0]['body']) is not int:
            raise ValueError('controlled integer batch requires each actual input')
        values.append(rows[0]['body'])
    outputs = ControlledBatchOperation(None).run(tuple(values))
    check_active()
    return cpu_authority_batch_reply(members, outputs)


class ControlledBatchPlan:
    def __init__(self):
        from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort
        self.port: PreparedOriginalCallPort | None = None

    def plan(self, members, *, check_active, execution_owner):
        import inspect
        from corpus_structure.semantic.data_operation_prepared_call import PreparedBatchCallResult
        from corpus_structure.semantic.identity import canonical_bytes
        assert self.port is not None
        bound = inspect.signature(controlled_kernel).bind(members=members, check_active=check_active)
        reply = yield from self.port.plan_cpu_reply(controlled_kernel, bound, controlled_sources(),
            check_active=check_active, execution_owner=execution_owner)
        return PreparedBatchCallResult(reply.content, canonical_bytes(reply.execution_receipt.record()))


def resolve_controlled_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.semantic.data_operation_prepared_call import PreparedOriginalCallPort
    plan = ControlledBatchPlan()
    expected = controlled_sources()
    receiver = ControlledBatchOperation(None)
    port = PreparedOriginalCallPort(identity, model, model.operation(operation), sources, custody,
        receiver.run, plan.plan, __name__ + '.ControlledBatchPlan.plan', authorize,
        expected.boundary_contracts, expected, functions=((__name__ + '.controlled_kernel', controlled_kernel),),
        retain_cpu_reply=True)
    plan.port = port
    return port


def controlled_recipe():
    from pathlib import Path
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle, ResolvedDependencies, PreparationProfile
    from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
    root = Path(__file__).resolve().parents[2]
    bundle = SourceBundle('core', (SourceArtifact('core',
        (root / 'src/corpus_structure/model/semantic/core.yaml').read_bytes()),))
    dependencies = data_operation_dependencies(ResolvedDependencies(), python_sources=controlled_sources())
    return KernelRecipe('actual-prepared-batch-control', '', None, '',
        captured_inputs=CapturedKernelInputs(bundle, dependencies, PreparationProfile(version='semantic-2')))
