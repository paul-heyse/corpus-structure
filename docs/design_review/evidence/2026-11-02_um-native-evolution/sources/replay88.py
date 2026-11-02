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

OUT = Path('build/um88-frozen-wrapper')
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
        upgrade(conn, 'semantic_pdf_support_20261102')
        with native_owner(conn, 'corpus_sem_publisher'):
            persist_release(conn, bundle, dependencies, profile, prepared)
            persist_release(conn, bundle, legacy_dependencies, legacy_profile, legacy)
        print('Archived actual current/semantic-1 releases under frozen87 fence', flush=True)
        upgrade(conn, 'semantic_pdf_callback_20261102')
        assert current_revision(conn) == 'semantic_pdf_callback_20261102'
        with native_owner(conn, 'corpus_sem_publisher'):
            conn.execute(text('SELECT data.require_execution_release(:release)'), dict(release=prepared.release_id))
        assert transaction.is_active and conn.scalar(text('SELECT current_user')) == 'paul'
        upgrade(conn, 'semantic_pdf_callback_20261102')
        print('PASSED exact frozen82->83->84->85->86->87->88 wrappers + finalized compiler23 admission + repeated Alembic no-op', flush=True)
        candidate, authoring = prepare_series_candidate(conn, owned_authoring=True)
        assert candidate.upgrade_ops is not None and not candidate.upgrade_ops.ops, candidate.upgrade_ops.ops
        assert len(authoring.desired) == 61
        print('PASSED exact current native/ordinary candidate empty at frozen88', flush=True)
        assert sources() == captured, 'source window changed'
    finally:
        transaction.rollback()
    assert current_revision(conn) == 'semantic_pdf_retire_20261101'
    assert conn.scalar(text('SELECT current_user')) == 'paul'
    print('PASSED caller role + outer rollback restored82; book target untouched', flush=True)
engine.dispose()
