"""Native row-type evolution preserves declared bodies, ACLs and refusal boundaries."""

from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.operations.ops import AddColumnOp, UpgradeOps
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.cli.schema import _native_candidate_python
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.alembic_privileges import OwnedOperationsOp
from corpus_structure.semantic.native_candidate import _order_row_type_evolution
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    admit_native,
    definition_from_sql,
    native_owner,
    prepare_native_authoring,
)


@pytest.mark.parametrize('control', ['evolve', 'stale', 'undeclared'])
def test_rowtype_alter_recreates_only_frozen_declared_dependents(infrastructure_rollback, control):
    connection = infrastructure_rollback
    schema = 'rowtype_' + uuid4().hex[:10]
    connection.exec_driver_sql(f'CREATE SCHEMA {schema} AUTHORIZATION corpus_sem_publisher')
    with native_owner(connection, 'corpus_sem_publisher'):
        connection.exec_driver_sql(f'CREATE TABLE {schema}.sample(amount integer NOT NULL)')
    definitions = tuple(
        definition_from_sql(connection, sql, source='rowtype regression', owner='corpus_sem_publisher', grants=(('corpus_sem_reader', 'EXECUTE', False),))
        for sql in (
            f'CREATE OR REPLACE FUNCTION {schema}.typed(value {schema}.sample) RETURNS integer LANGUAGE SQL BEGIN ATOMIC SELECT value.amount; END',
            f'''CREATE OR REPLACE FUNCTION {schema}.caller() RETURNS integer LANGUAGE SQL BEGIN ATOMIC SELECT {schema}.typed(jsonb_populate_record(NULL::{schema}.sample, '{{"amount":7}}'::jsonb)); END''',
            f'CREATE OR REPLACE FUNCTION {schema}.unrelated() RETURNS integer LANGUAGE SQL AS $$SELECT 19$$',
        )
    )
    current = prepare_native_authoring(connection, definitions, owned_authoring=True)
    operations = Operations(MigrationContext.configure(connection))
    for item in current.desired:
        operations.invoke(NativeTransitionOp(None, item))
    authoring = prepare_native_authoring(connection, definitions, predecessor=current.desired, owned_authoring=True)
    upgrade = UpgradeOps([
        OwnedOperationsOp('corpus_sem_publisher', [AddColumnOp('sample', Column('scope', JSONB(), nullable=False, server_default=text("'{}'::jsonb")), schema=schema)])
    ])
    # This is the actual PostgreSQL refusal that ordering must fix.
    with pytest.raises(DBAPIError) as refused, connection.begin_nested():
        operations.invoke(upgrade.ops[0])
    assert getattr(refused.value.orig, 'sqlstate', None) == '0A000'
    _order_row_type_evolution(connection, upgrade, authoring)
    transitions = [item for item in upgrade.ops if isinstance(item, NativeTransitionOp)]
    assert [(item.identity.name, item.after is not None) for item in transitions] == [
        ('caller', False), ('typed', False), ('typed', True), ('caller', True)
    ]
    assert all(item.identity.name != 'unrelated' for item in transitions)
    caller = connection.exec_driver_sql('SELECT current_user').scalar_one()
    if control == 'stale':
        with native_owner(connection, 'corpus_sem_publisher'):
            connection.exec_driver_sql(f'ALTER FUNCTION {schema}.caller() STRICT')
    elif control == 'undeclared':
        with native_owner(connection, 'corpus_sem_publisher'):
            connection.exec_driver_sql(f'CREATE FUNCTION {schema}.outside() RETURNS integer LANGUAGE SQL BEGIN ATOMIC SELECT {schema}.caller(); END')
    if control != 'evolve':
        failure = NativeAuthoringError if control == 'stale' else DBAPIError
        with pytest.raises(failure), connection.begin_nested():
            for operation in upgrade.ops:
                operations.invoke(operation)
        assert connection.exec_driver_sql('SELECT current_user').scalar_one() == caller
        assert connection.exec_driver_sql(f'SELECT {schema}.caller()').scalar_one() == 7
        return
    # Exercise Alembic's frozen renderer, rather than only invoking the producer objects.
    namespace = {}
    source = _native_candidate_python(upgrade, '')
    exec(compile(source, 'native-rowtype-regression.py', 'exec'), namespace)
    with Operations.context(MigrationContext.configure(connection)):
        namespace['upgrade']()
    admit_native(connection, authoring.desired)
    assert connection.exec_driver_sql('SELECT current_user').scalar_one() == caller
    assert connection.exec_driver_sql(f'SELECT {schema}.caller()').scalar_one() == 7
    assert connection.exec_driver_sql(f'SELECT {schema}.unrelated()').scalar_one() == 19
    assert connection.exec_driver_sql(f"SELECT count(*) FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='sample' AND column_name='scope' AND is_nullable='NO'").scalar_one() == 1
