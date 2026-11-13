"""Trusted DDO protocol correspondence, admission and protected native storage ports.

The declaration file is the one operation inventory. Effective source facts and direct
call bindings are derived together; candidate operations cannot choose SQL symbols.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from sqlalchemy import bindparam, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from .contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
from .data_operation_model import MODEL_VERSION
from .identity import canonical_bytes
from .types import SourceArtifact

if TYPE_CHECKING:
    from sqlalchemy import Connection
    from .data_operation_model import EffectiveDataOperationModel
    from .types import PreparedRelease

_ROOT = Path(__file__).resolve().parents[1] / 'model' / 'semantic'
_SQL = Path(__file__).with_name('sql') / 'data_operations.sql'


def native_protocol_sources() -> tuple[SourceArtifact, ...]:
    return (SourceArtifact('native/data-operation-protocol.yaml', (_ROOT / 'data-operation-native.yaml').read_bytes()),
            SourceArtifact('native/data-operations.sql', _SQL.read_bytes()))


def _captured(sources) -> dict[str, bytes]:
    result = {source.name: source.content for source in sources}
    required = {'native/data-operation-protocol.yaml', 'native/data-operations.sql'}
    if not required <= result.keys():
        raise ValueError('target correspondence requires captured native protocol and SQL')
    return result


def _protocol(sources=None) -> tuple[dict[str, str], ...]:
    content = _captured(sources if sources is not None else native_protocol_sources())
    value = yaml.safe_load(content['native/data-operation-protocol.yaml'])
    if value['version'] != 'data-operation-native-v1':
        raise ValueError('unsupported trusted native protocol')
    return tuple(value['operations'])


def native_source_digest(sources=None) -> str:
    content = _captured(sources if sources is not None else native_protocol_sources())
    return sha256(canonical_bytes([content['native/data-operation-protocol.yaml'].decode(),
                                  content['native/data-operations.sql'].decode()])).hexdigest()


def native_sql() -> str:
    return _SQL.read_text().replace('__DDO_SOURCE_DIGEST__', native_source_digest())


def native_operation_declarations(sources=None) -> SourceArtifact:
    """Explicit captured operation facts for compilation into the shared effective IR."""
    operations = []
    for item in _protocol(sources):
        name = item['name']
        operations.append({
            'id': 'data.' + name, 'profile': item['profile'],
            'subject': 'authenticated-native-invocation', 'context': ['release', 'purpose'],
            'roles': [
                {'name': 'request', 'kind': 'json', 'direction': 'input',
                 'minimum': 1, 'maximum': 1, 'collection': 'scalar', 'presence': 'required',
                 'parameter': 'payload', 'support': {'provenance': 'exact',
                     'source': 'authenticated-native-invocation', 'coverage': 'whole-wire',
                     'identity_requirements': ['episode']}},
                {'name': 'result', 'kind': 'json', 'direction': 'output',
                 'minimum': 1, 'maximum': 1, 'collection': 'scalar', 'presence': 'required',
                 'parameter': 'payload'},
            ],
            'applicability': ['native-deployment-admitted'],
            'invariants': ['native-wire-and-purpose', 'native-attempt-fence',
                           'native-source-and-kind-custody'],
            'coverage': 'one-short-native-transaction', 'outcomes': ['returned'],
            'precision': 'exact', 'dependencies': [],
            'effects': ([] if item['profile'] == 'read' else [{
                'name': name, 'authorization': ['native-purpose'],
                'idempotency': 'immutable-receipt-or-explicit-append',
                'fulfillment': 'native-transaction',
            }]),
            'capabilities': {'forms': ['scalar'], 'preparation': 'none',
                'cancellation': 'transaction-boundary', 'ownership': 'native-connection'},
            'behavior': 'ddo-native-v1:' + native_source_digest(sources), 'parameters': {},
            'binding': {'operator': 'scan', 'roles': ['request']},
        })
    return SourceArtifact('native/data-operation-native.yaml', canonical_bytes({
        'version': MODEL_VERSION, 'operations': operations,
    }))


def native_operation_calls(model: EffectiveDataOperationModel | None = None, *, sources=None
                           ) -> tuple[tuple[str, OperationCallBinding], ...]:
    """Resolve the fixed protocol's signatures without accepting candidate SQL names."""
    resolved = OperationFieldType('json_payload', False, False)
    result = []
    owners = {operation.semantic_id for operation in model.operations} if model else None
    for item in _protocol(sources):
        name = item['name']
        owner = 'data.' + name
        if owners is not None and owner not in owners:
            raise ValueError(f'missing captured native protocol operation {owner}')
        result.append((owner, OperationCallBinding(
            id=name, symbol='ops.' + name,
            parameters=(OperationFieldBinding('payload', 'native-wire', False,
                         native_parameter='p_payload', resolved=resolved),),
            result_fields=(OperationFieldBinding('payload', 'native-wire', False,
                           native_field='payload', resolved=resolved),),
            result_class=''.join(word.title() for word in name.split('_')) + 'Result',
            cardinality='one', ordered=False, result_mode='json',
            source_digest=native_source_digest(sources),
        )))
    return tuple(result)


trusted_data_operation_calls = native_operation_calls


def native_calls_from_dependencies(model, dependencies):
    return native_operation_calls(model, sources=dependencies.artifacts)


def native_digest_from_dependencies(dependencies):
    return native_source_digest(dependencies.artifacts)


class DataOperationStorage:
    """Connection-scoped invocation; transaction and commit custody stay with the caller."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def invoke(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if name not in {item['name'] for item in _protocol()}:
            raise ValueError('unknown trusted native data operation')
        value = self.connection.scalar(select(
            getattr(func.ops, name)(bindparam('payload', type_=JSONB))
        ), {'payload': payload})
        if not isinstance(value, dict) or set(value) != {'payload'} or not isinstance(value['payload'], dict):
            raise ValueError('native data operation returned a malformed fixed envelope')
        return value['payload']


def require_data_operation_native(connection: Connection, prepared: PreparedRelease) -> str:
    """Verify the installed native descriptor and required relations before admission."""
    actual = connection.scalar(text('SELECT sem.data_operation_native_descriptor()'))
    if not isinstance(actual, dict) or actual.get('version') != 'data-operation-native-v1' or actual.get('source_digest') != native_source_digest():
        raise ValueError('native data-operation implementation differs from prepared code')
    for schema, name in (('ops', 'data_request'), ('ops', 'data_completion_intent'),
                         ('kb', 'data_product'), ('sem', 'data_operation_definition')):
        if connection.scalar(text('SELECT to_regclass(:name)'), {'name': f'{schema}.{name}'}) is None:
            raise ValueError(f'native data operation relation is absent: {schema}.{name}')
    return native_source_digest()


def _kind_schema(prepared: PreparedRelease, kind) -> dict[str, Any]:
    facts = json.loads(kind.facts)
    if kind.category == 'class' and kind.name in prepared.index.definitions:
        return prepared.json_schema(kind.name)
    primitive = facts.get('primitive', kind.name)
    types = {'string': 'string', 'uri': 'string', 'uriorcurie': 'string',
             'integer': 'integer', 'boolean': 'boolean', 'float': 'string',
             'double': 'string', 'decimal': 'number', 'date': 'string',
             'datetime': 'string', 'bytes': 'string'}
    if primitive == 'json':
        return {'type': ['null', 'boolean', 'string', 'number', 'array', 'object']}
    if primitive in types:
        return {'type': types[primitive]}
    # Unknown Python/class contracts cannot silently become unconstrained JSON.
    raise ValueError(f'no native body schema for effective kind {kind.semantic_id}')


def data_operation_definition_projection(prepared: PreparedRelease,
                                         model: EffectiveDataOperationModel, *,
                                         native_digest: str) -> bytes:
    """Compile the fixed native projection for authenticated release archiving."""
    ids = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    kinds = []
    used = {role.kind for operation in model.operations for role in operation.roles}
    for kind in model.kinds:
        if kind.semantic_id not in used:
            continue
        contract = ids.get((kind.semantic_id, 'kind'))
        if contract is None:
            raise ValueError('cannot admit an incomplete effective kind')
        facts = json.loads(kind.facts)
        kinds.append({'kind_contract': contract, 'kind': kind.semantic_id,
            'body_schema': _kind_schema(prepared, kind),
            'member_schema': {'type': 'object', 'required': ['member_id'],
                              'properties': {'member_id': {'type': 'string', 'minLength': 1}}},
            'families': facts.get('projection_families', []),
            'universe': facts.get('universe', 'ordinary')})
    operations = []
    for operation in model.operations:
        recipe = ids.get((operation.semantic_id, 'recipe'))
        if recipe is None:
            raise ValueError('cannot admit an incomplete implementation recipe')
        roles = []
        for role in operation.roles:
            record = asdict(role)
            record['kind_contract'] = ids[role.kind, 'kind']
            record['identity_requirements'] = list(role.support.identity_requirements) if role.support else []
            roles.append(record)
        operations.append({'operation_id': operation.semantic_id, 'recipe': recipe,
            'profile': operation.profile,
            'implementation_revision': next((identity.key for identity in model.identities
                if identity.owner == operation.implementation_root and identity.domain == 'implementation-slice'), operation.behavior),
            'input_roles': [role for role in roles if role['direction'] == 'input'],
            'output_roles': [role for role in roles if role['direction'] == 'output'],
            'support_contract': {'policy': operation.support_policy,
                'provenance': ('value_substitution' if all(role.support is None or role.support.provenance == 'value_substitution' for role in operation.roles) else 'exact')},
        })
    return canonical_bytes({'model_digest': sha256(model.content).hexdigest(),
                            'native_digest': native_digest,
                            'kinds': kinds, 'operations': operations})


def admit_data_operation_definitions(connection: Connection, prepared: PreparedRelease,
                                    model: EffectiveDataOperationModel) -> str:
    """Install the authenticated exact fixed projection, never caller-shaped contracts."""
    require_data_operation_native(connection, prepared)
    artifacts = [a for a in prepared.artifacts if a.kind == 'data_operation_native_definitions.json']
    if len(artifacts) != 1:
        raise ValueError('release lacks authenticated native definition projections')
    payload = json.loads(artifacts[0].content)
    if payload['model_digest'] != sha256(model.content).hexdigest():
        raise ValueError('native definition projection belongs to another effective model')
    value = connection.scalar(select(func.sem.admit_data_operation_definitions(
        bindparam('payload', type_=JSONB))), {'payload': {
            **payload, 'release_id': prepared.release_id}})
    if not isinstance(value, dict) or value.get('release_id') != prepared.release_id:
        raise ValueError('native definition admission did not return exact release identity')
    return native_source_digest()


def admitted_data_projection(connection: Connection, demand_id: str, operation_id: str,
                            trust_snapshot: dict, model: EffectiveDataOperationModel):
    """Construct SQL bindings only through the demand-pinned native admission reader.

    The query rechecks the trust snapshot when executed. Evidence captures the same
    pins, and contains no claim that a raw product row is admissible evidence.
    """
    from sqlalchemy import BigInteger, String, column
    from .data_operation_bindings import ProjectionBinding, ProjectionField

    operation = model.operation(operation_id)
    # Acquire the exact demand now; execution of the TVF repeats its pin check.
    acquired = DataOperationStorage(connection).invoke('read_demand_result', {
        'demand_id': demand_id, 'trust_snapshot': trust_snapshot,
    })
    if acquired['trust_snapshot'] != trust_snapshot:
        raise ValueError('native binding snapshot differs')
    identities = {(i.owner, i.domain): i.key for i in model.identities}
    kinds = {kind.semantic_id: kind for kind in model.kinds}
    names = ('product', 'kind_contract', 'subject', 'original_source', 'analyzed_scope',
             'coverage', 'support_episodes', 'support_evidence', 'position',
             'multiplicity', 'member', 'provider_identity', 'alternative_identity', 'body')
    json_columns = {'analyzed_scope', 'coverage', 'support_episodes', 'support_evidence', 'body'}
    relation = func.ops.data_binding_rows(demand_id, operation_id,
        bindparam('data_binding_trust', trust_snapshot, type_=JSONB)).table_valued(*(
            column(name, JSONB if name in json_columns else BigInteger
                   if name in {'position', 'multiplicity'} else String)
            for name in names
        ))
    projections = []
    for kind_id in sorted({role.kind for role in operation.roles if role.direction == 'input'}):
        kind = kinds[kind_id]
        contract = identities[kind_id, 'kind']
        fields = [ProjectionField(name, name, 'json' if name in json_columns else
                  'integer' if name in {'position', 'multiplicity'} else 'string')
                  for name in names if name != 'body']
        selected = list(relation.c)
        facts = json.loads(kind.facts)
        for prop in facts.get('properties', []):
            name = prop['name']
            if name in names:
                continue
            value_type = prop.get('range', 'json')
            expression = relation.c.body[name]
            if value_type in {'integer', 'boolean', 'float', 'decimal', 'date', 'datetime'}:
                # SQLAlchemy's typed JSON extraction preserves native comparisons.
                expression = (expression.as_integer() if value_type == 'integer' else
                              expression.as_boolean() if value_type == 'boolean' else
                              expression.as_float() if value_type == 'float' else expression)
            elif value_type in {'string', 'uri', 'uriorcurie'}:
                expression = expression.astext
                value_type = 'string'
            else:
                value_type = 'json'
            selected.append(expression.label(name))
            fields.append(ProjectionField(name, name, value_type))
        scoped = select(*selected).where(relation.c.kind_contract == contract).subquery()
        projections.append(ProjectionBinding(kind_id, scoped, tuple(fields), canonical_bytes({
            'demand_id': demand_id, 'operation_id': operation_id,
            'selection': acquired['selection'], 'trust_snapshot': trust_snapshot,
        })))
    return tuple(projections)


def data_operation_native_definitions(connection):
    """Include every kernel function in normal server-normalized candidate custody."""
    from pglast import ast
    from .native_objects import definition_from_sql
    from .prepared_sql import prepare_sql

    sql = native_sql()
    prepared = prepare_sql(sql, source='data-operations:forward')
    public = {item['name']: item['profile'] for item in _protocol()}
    definitions = []
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        schema, name = (part.sval for part in statement.funcname)
        if name in public:
            roles = ('corpus_sem_reader', 'corpus_sem_writer', 'corpus_sem_evaluator') if public[name] == 'read' else ('corpus_sem_writer', 'corpus_sem_evaluator')
        elif name == 'admit_data_operation_definitions':
            roles = ('corpus_sem_admitter',)
        elif name == 'data_operation_native_descriptor':
            roles = ('corpus_sem_reader', 'corpus_sem_writer', 'corpus_sem_admitter', 'corpus_sem_evaluator')
        elif name == 'data_binding_rows':
            roles = ('corpus_sem_reader', 'corpus_sem_writer', 'corpus_sem_evaluator')
        else:
            roles = ()
        definitions.append(definition_from_sql(connection, prepared.excerpt(index),
            source='data-operations:forward', owner='corpus_sem_publisher',
            grants=tuple((role, 'EXECUTE', False) for role in roles)))
    return tuple(definitions)
