from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import (
    candidate_admission_sql,
    prepare_series_candidate,
    series_native_definitions,
)
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    admit_native,
    execute_native_sql,
    native_owner,
)
from corpus_structure.semantic.operations import OperationBinding, create_run, end_source_run
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.source_view_native import _admission_descriptor
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

OUT = Path('build/um87-author-attempt-001')
OUT.mkdir(exist_ok=False)
SRC = Path('python/corpus-structure/src/corpus_structure')
VERSIONS = Path('python/corpus-structure/semantic_alembic/versions')

def sources():
    return {
        str(path): sha256(path.read_bytes()).hexdigest()
        for path in sorted(SRC.rglob('*'))
        if path.is_file() and path.suffix in {'.py', '.yaml', '.json', '.sql'}
    }

captured = sources()
bundle = SourceBundle('um86', (SourceArtifact('um86', b'''id: https://example.org/um86
name: um86
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Report:
  attributes:
   text: {required: true}
'''),))
dependencies = composed_dependencies(ResolvedDependencies())
profile = PreparationProfile(version='semantic-2')
prepared = prepare_release(bundle, dependencies, profile)
legacy_dependencies = ResolvedDependencies()
legacy_profile = PreparationProfile()
legacy = prepare_release(bundle, legacy_dependencies, legacy_profile)
assert legacy.execution_model_id is None
execution = json.loads(next(row.body for row in prepared.registry_rows if row.kind == 'execution_model'))
assert execution['inputs']['compiler_version'] == '23', execution['inputs']['compiler_version']
print('Current compiler23 finalized release:', prepared.release_id, flush=True)
print('Genuine unbound semantic-1 release:', legacy.release_id, flush=True)
engine = create_engine('postgresql+psycopg:///cs_sem_pdf68_author_20261101_44132f1db0?host=/var/run/postgresql&port=5434')
with engine.connect() as conn:
    transaction = conn.begin()
    try:
        provenance = conn.execute(text("SELECT oid,pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")).one()
        assert provenance[0] == 14010645 and provenance[1] == 'paul' and '1dbfc2773c354652b64626aaa56eac35' in provenance[2], provenance
        assert current_revision(conn) == 'semantic_pdf_retire_20261101'
        upgrade(conn, 'semantic_um_core_20261102')
        with native_owner(conn, 'corpus_sem_publisher'):
            persist_release(conn, bundle, dependencies, profile, prepared)
            persist_release(conn, bundle, legacy_dependencies, legacy_profile, legacy)
        print('Archived actual current/semantic-1 releases under frozen86 fence', flush=True)
        with native_owner(conn, 'corpus_sem_publisher'):
            previous_epoch = conn.scalar(text('SELECT ops.pdf_validation_contract(:release)'),dict(release=prepared.release_id))
        candidate, authoring = prepare_series_candidate(conn, owned_authoring=True)
        assert candidate.upgrade_ops is not None
        native = [op for op in candidate.upgrade_ops.ops if isinstance(op, NativeTransitionOp)]
        ordinary = [op for op in candidate.upgrade_ops.ops if not isinstance(op, NativeTransitionOp)]
        assert not ordinary, ordinary
        assert len(authoring.desired) == 61, len(authoring.desired)
        admission = candidate_admission_sql(conn, series_native_definitions(conn), authoring.desired)
        old = _admission_descriptor((VERSIONS / 'semantic_um_core_20261102_admission.sql').read_text())
        new = _admission_descriptor(admission)
        assert new['physical_id'] == old['physical_id'], (new['physical_id'], old['physical_id'])
        state = dict(version=1, predecessor='semantic_um_core_20261102', operations=[op.payload() for op in native], desired=[obj.payload() for obj in authoring.desired])
        transitions = tuple(NativeTransitionOp.from_payload(payload) for payload in state['operations'])
        operations = Operations(MigrationContext.configure(conn))
        for operation in transitions:
            operations.invoke(operation)
        admit_native(conn, authoring.desired)
        with native_owner(conn, 'corpus_sem_publisher'):
            conn.execute(text('SELECT data.require_execution_release(:release)'), dict(release=prepared.release_id))
        print('PASSED actual finalized current23 release admission', flush=True)
        receipt_reader = next(op for op in transitions if op.after is not None and op.after.identity.name == 'read_pdf_published_validation')
        assert receipt_reader.before is None and receipt_reader.after.catalog_version == 2
        try:
            with conn.begin_nested():
                operations.invoke(receipt_reader)
        except NativeAuthoringError as error:
            assert 'stale native before-state' in str(error)
            print('PASSED repeated receipt-reader create refuses stale before-state', flush=True)
        else:
            raise AssertionError('repeated receipt-reader create accepted existing identity')
        from corpus_structure.semantic._operation_calls import read_pdf_published_validation
        from corpus_structure.semantic._operation_ids import TaskId, ProductKey, ContentDigest
        with native_owner(conn, 'corpus_sem_publisher'):
            assert read_pdf_published_validation(conn,task_id=TaskId(-1),product_key=ProductKey('missing'),content_digest=ContentDigest('0'*64)) is None
            current_epoch = conn.scalar(text('SELECT ops.pdf_validation_contract(:release)'),dict(release=prepared.release_id))
            assert current_epoch != previous_epoch and len(current_epoch)==64
        print('PASSED deployed SQL-standard helper optional-row ABI and v4->v5 epoch separation', flush=True)
        try:
            with conn.begin_nested(), native_owner(conn, 'corpus_sem_publisher'):
                execute_native_sql(conn, 'ALTER TABLE kb.source_view ALTER COLUMN native_build_id DROP NOT NULL')
                conn.execute(text('SELECT data.require_execution_release(:release)'), dict(release=prepared.release_id))
        except DBAPIError as error:
            assert getattr(error.orig, 'sqlstate', None) == '23514' and 'native source frame projection differs: kb.source_view' in str(error.orig), error
            print('PASSED independent wrong-nullability native admission refusal', flush=True)
        else:
            raise AssertionError('wrong column admitted')
        with native_owner(conn, 'corpus_sem_publisher'):
            conn.execute(text('SELECT data.require_execution_release(:release)'), dict(release=prepared.release_id))
        assert transaction.is_active and conn.scalar(text('SELECT current_user')) == 'paul'
        assert sources() == captured, 'source window changed'
        for filename, content in [('native.json', canonical_bytes(state)), ('admission.sql', admission.encode()), ('sources.json', canonical_bytes(captured))]:
            (OUT / filename).write_bytes(content)
        report = dict(predecessor=state['predecessor'], release=prepared.release_id, desired=len(authoring.desired), native_operations=len(transitions), ordinary_operations=0, physical_alias=False, sql_standard_bodies=sum(obj.catalog_version == 2 for obj in authoring.desired), artifacts={path.name: sha256(path.read_bytes()).hexdigest() for path in OUT.iterdir()})
        (OUT / 'result.json').write_bytes(canonical_bytes(report))
        print(json.dumps(report), flush=True)
    finally:
        transaction.rollback()
    assert current_revision(conn) == 'semantic_pdf_retire_20261101'
    assert conn.scalar(text('SELECT current_user')) == 'paul'
    print('PASSED outer rollback restored82 + caller role; book target untouched', flush=True)
engine.dispose()
