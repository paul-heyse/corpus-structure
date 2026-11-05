"""Apply the authorized additive runtime migration and verify retained-row preservation."""
import json
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from corpus_structure.settings import Settings
from corpus_structure.semantic.migrations import current_revision, upgrade

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'raw/runtime-migrate-working-003.json'
if TARGET.exists():
    raise FileExistsError(TARGET)
engine = create_engine(make_url(Settings().database.sqlalchemy_url).set(username='paul'))
TABLES = (
    'sem.release', 'sem.input', 'sem.artifact', 'sem.registry_row',
    'ops.run', 'ops.task', 'ops.task_result', 'ops.input_cut', 'ops.cut_task',
    'kb.observation', 'kb.source_view', 'kb.document', 'data.project',
)

def snapshot(conn):
    tables = list(TABLES)
    tables.extend('eval.' + name for name in conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='eval' "
        "AND (table_name LIKE 'reference_%' OR table_name LIKE 'evaluation%') "
        "AND table_type='BASE TABLE' ORDER BY table_name"
    )).scalars())
    result = {}
    for name in tables:
        row = conn.exec_driver_sql(
            "SELECT count(*) AS rows, encode(sha256(convert_to(coalesce("
            "string_agg(digest,'' ORDER BY digest),''),'UTF8')),'hex') AS digest FROM ("
            "SELECT encode(sha256(convert_to((to_jsonb(t) - 'runtime_id')::text,"
            "'UTF8')),'hex') AS digest FROM " + name + " t) sealed"
        ).mappings().one()
        result[name] = dict(row)
    return result

try:
    with engine.begin() as conn:
        before_revision = current_revision(conn)
        assert before_revision == 'semantic_pce_foundation_20261105', before_revision
        before = snapshot(conn)
        operations = upgrade(conn, 'semantic_runtime_20261105')
        after_revision = current_revision(conn)
        assert after_revision == 'semantic_runtime_20261105', after_revision
        after = snapshot(conn)
        assert before == after, 'retained archive/data/run/reference rows changed'
        assert conn.exec_driver_sql('SELECT count(*) FROM sem.runtime_binding').scalar_one() == 0
        assert conn.exec_driver_sql(
            'SELECT count(*) FROM ops.run WHERE runtime_id IS NOT NULL'
        ).scalar_one() == 0
    report = dict(outcome='passed', database='configured persistent corpus_structure_dev',
        before_revision=before_revision, after_revision=after_revision,
        before=before, after=after, operations=operations,
        legacy_provenance='unchanged embedded release archives; no current-code backfill',
        selected_defaults='included in unchanged data.project row digest',
        provider_execution=False)
    with TARGET.open('x') as stream:
        json.dump(report, stream, indent=2, default=str)
        stream.write('\n')
    print(json.dumps(dict(outcome='passed', before_revision=before_revision,
        after_revision=after_revision, unchanged_tables=len(before), receipt=str(TARGET))))
finally:
    engine.dispose()
