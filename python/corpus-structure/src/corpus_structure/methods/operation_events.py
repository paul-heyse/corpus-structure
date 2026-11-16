"""Current selected operation-event frame, protected fit and native parameter issuance."""

from typing import ClassVar

class OperationEventFrame:
    __data_operation__: ClassVar[dict] = {'id': 'operation_event.frame',
     'profile': 'derivation',
     'subject': 'fitted-operation-event',
     'subject_definition': {'id': 'fitted-operation-event', 'identifier_kind': 'string', 'scope': 'project'},
     'discovery_relation': 'role-associated',
     'context': ['exact-selected-component-events', 'protected-independent-output-first-C'],
     'entrypoints': ['run'],
     'roles': [{'name': 'question',
                'kind': 'https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventQuestion',
                'direction': 'input',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required',
                'parameter': 'question',
                'support': {'provenance': 'exact',
                            'source': 'independent-output-first-C',
                            'identity_requirements': ['original-source'],
                            'coverage': {'role': 'question', 'description': 'exact-current-event-question'},
                            'origins': ['authored']}},
               {'name': 'reports',
                'kind': 'urn:corpus:structural:DeclaredDefinitionComponentsReport',
                'direction': 'input',
                'minimum': 1,
                'maximum': None,
                'collection': 'set',
                'presence': 'required',
                'parameter': 'reports',
                'subject_target': 'source-set',
                'support': {'provenance': 'exact',
                            'source': 'frozen-source-set',
                            'identity_requirements': ['episode'],
                            'coverage': {'role': 'reports', 'description': 'exact-current-event-reports'},
                            'source_set': 'operation-event-reports'}},
               {'name': 'sources',
                'kind': 'https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource',
                'direction': 'input',
                'minimum': 1,
                'maximum': None,
                'collection': 'set',
                'presence': 'required',
                'parameter': 'sources',
                'subject_target': 'source-set',
                'support': {'provenance': 'exact',
                            'source': 'frozen-source-set',
                            'identity_requirements': ['episode'],
                            'coverage': {'role': 'sources', 'description': 'exact-current-event-sources'},
                            'source_set': 'operation-event-sources'}},
               {'name': 'frame',
                'kind': 'https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFrame',
                'direction': 'output',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required'}],
     'applicability': [{'kind': 'documentation', 'text': 'current-selected-definition-attachment-frame'}],
     'invariants': [{'kind': 'documentation', 'text': 'exact-current-input-custody-and-finite-disclosure'}],
     'coverage': {'binding': 'self',
                  'result_owners': [{'kind': 'implementation', 'reference': 'self'}],
                  'description': 'current-selected-definition-attachment-frame'},
     'outcomes': ['success'],
     'precision_description': 'current-selected-definition-attachment-frame',
     'dependencies': [],
     'effects': [],
     'parameters': {},
     'capabilities': {'forms': ['scalar'],
                      'preparation': 'resource',
                      'prepared_factory': 'acquire_port',
                      'cancellation': 'cooperative',
                      'ownership': 'invocation-owned-cpu'},
     'behavior': 'current-selected-definition-attachment-frame',
     'binding': {'operator': 'all',
                 'children': [{'operator': 'scan', 'roles': ['question']},
                              {'operator': 'collection', 'roles': ['reports'], 'collection': 'set'},
                              {'operator': 'collection', 'roles': ['sources'], 'collection': 'set'}]},
     'opaque': [{'reference': 'corpus_structure.evaluate.declared_operation_events.execute_frame_profile',
                 'contract': 'operation-events/computation-assets',
                 'role': 'current-selected-definition-attachment-frame'}],
     'assets': [{'reference': 'operation-events',
                 'contract': 'operation-events/computation-assets',
                 'role': 'exact-current-event-contracts-and-numerical-kernel'}]}

    def run(self, question: dict, reports: list[dict], sources: list[dict]) -> dict:
        from corpus_structure.evaluate.declared_operation_events import execute_frame_profile

        return execute_frame_profile(self, question, reports, sources)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.evaluate.declared_operation_events import acquire_frame_port

        return acquire_frame_port(prepared, model, operation, identity=identity, authorize=authorize, custody=custody, sources=sources)


class OperationEventFit:
    __data_operation__: ClassVar[dict] = {'id': 'operation_event.fit',
     'profile': 'derivation',
     'subject': 'fitted-operation-event',
     'subject_definition': {'id': 'fitted-operation-event', 'identifier_kind': 'string', 'scope': 'project'},
     'discovery_relation': 'role-associated',
     'context': ['exact-selected-component-events', 'protected-independent-output-first-C'],
     'entrypoints': ['run'],
     'roles': [{'name': 'frame',
                'kind': 'https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFrame',
                'direction': 'input',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required',
                'parameter': 'frame',
                'subject_target': 'source-set',
                'support': {'provenance': 'exact',
                            'source': 'frozen-source-set',
                            'identity_requirements': ['episode'],
                            'coverage': {'role': 'frame', 'description': 'exact-current-event-frame'},
                            'source_set': 'operation-event-frames'}},
               {'name': 'specification',
                'kind': 'https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFitSpecification',
                'direction': 'input',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required',
                'parameter': 'specification',
                'support': {'provenance': 'exact',
                            'source': 'independent-output-first-C',
                            'identity_requirements': ['original-source'],
                            'coverage': {'role': 'specification',
                                         'description': 'exact-current-event-specification'},
                            'origins': ['authored']}},
               {'name': 'fit',
                'kind': 'https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFit',
                'direction': 'output',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required'}],
     'applicability': [{'kind': 'documentation', 'text': 'actual-selected-frame-numerical-fit'}],
     'invariants': [{'kind': 'documentation', 'text': 'exact-current-input-custody-and-finite-disclosure'}],
     'coverage': {'binding': 'self',
                  'result_owners': [{'kind': 'implementation', 'reference': 'self'}],
                  'description': 'actual-selected-frame-numerical-fit'},
     'outcomes': ['success'],
     'precision_description': 'actual-selected-frame-numerical-fit',
     'dependencies': [],
     'effects': [],
     'parameters': {},
     'capabilities': {'forms': ['scalar'],
                      'preparation': 'resource',
                      'prepared_factory': 'acquire_port',
                      'cancellation': 'cooperative',
                      'ownership': 'invocation-owned-cpu'},
     'behavior': 'actual-selected-frame-numerical-fit',
     'binding': {'operator': 'scan', 'roles': ['frame', 'specification']},
     'opaque': [{'reference': 'corpus_structure.evaluate.declared_operation_events.execute_fit_profile',
                 'contract': 'operation-events/computation-assets',
                 'role': 'actual-selected-frame-numerical-fit'}],
     'assets': [{'reference': 'operation-events',
                 'contract': 'operation-events/computation-assets',
                 'role': 'exact-current-event-contracts-and-numerical-kernel'}]}

    def run(self, frame: dict, specification: dict) -> dict:
        from corpus_structure.evaluate.declared_operation_events import execute_fit_profile

        return execute_fit_profile(self, frame, specification)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.evaluate.declared_operation_events import acquire_fit_port

        return acquire_fit_port(prepared, model, operation, identity=identity, authorize=authorize, custody=custody, sources=sources)


class OperationEventAuthorization:
    __data_operation__: ClassVar[dict] = {'id': 'operation_event.authorize',
     'profile': 'command',
     'subject': 'fitted-operation-event',
     'subject_definition': {'id': 'fitted-operation-event', 'identifier_kind': 'string', 'scope': 'project'},
     'discovery_relation': 'role-associated',
     'context': ['exact-selected-component-events', 'protected-independent-output-first-C'],
     'entrypoints': ['run'],
     'roles': [{'name': 'basis',
                'kind': 'https://corpus-structure.dev/semantic/operation-events/protected/DdoOperationEventFit',
                'direction': 'input',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required',
                'parameter': 'basis',
                'support': {'provenance': 'exact',
                            'source': 'same-original',
                            'identity_requirements': ['episode'],
                            'coverage': {'role': 'basis', 'description': 'exact-current-event-basis'}}},
               {'name': 'parameters',
                'kind': 'urn:corpus:kind:operation-event:parameters',
                'direction': 'output',
                'minimum': 1,
                'maximum': 1,
                'collection': 'scalar',
                'presence': 'required'}],
     'applicability': [{'kind': 'documentation', 'text': 'finite-exact-operation-event-parameters'}],
     'invariants': [{'kind': 'documentation', 'text': 'exact-current-input-custody-and-finite-disclosure'}],
     'coverage': {'binding': 'self',
                  'result_owners': [{'kind': 'implementation', 'reference': 'self'}],
                  'description': 'finite-exact-operation-event-parameters'},
     'outcomes': ['success'],
     'precision_description': 'finite-exact-operation-event-parameters',
     'dependencies': [],
     'effects': [{'name': 'native-evaluator-operation-event-authorization',
                  'authorization': ['native-purpose:evaluator', 'exact-protected-operation-event-fit'],
                  'idempotency': 'request-generation/exact-fit',
                  'fulfillment': 'native-publication-receipt'}],
     'parameters': {},
     'capabilities': {'forms': ['scalar'],
                      'preparation': 'native-publication',
                      'prepared_factory': 'acquire_port',
                      'cancellation': 'cooperative',
                      'ownership': 'invocation-owned-cpu'},
     'behavior': 'finite-exact-operation-event-parameters',
     'binding': {'operator': 'scan', 'roles': ['basis']},
     'opaque': [{'reference': 'corpus_structure.evaluate.declared_operation_events.execute_authorize_profile',
                 'contract': 'operation-events/computation-assets',
                 'role': 'finite-exact-operation-event-parameters'}],
     'assets': [{'reference': 'operation-events',
                 'contract': 'operation-events/computation-assets',
                 'role': 'exact-current-event-contracts-and-numerical-kernel'}]}

    def run(self, basis: dict) -> dict:
        from corpus_structure.evaluate.declared_operation_events import execute_authorize_profile

        return execute_authorize_profile(self, basis)

    @staticmethod
    def acquire_port(prepared, model, operation, *, identity, authorize, custody, sources):
        from corpus_structure.evaluate.declared_operation_events import acquire_authorize_port

        return acquire_authorize_port(prepared, model, operation, identity=identity, authorize=authorize, custody=custody, sources=sources)


