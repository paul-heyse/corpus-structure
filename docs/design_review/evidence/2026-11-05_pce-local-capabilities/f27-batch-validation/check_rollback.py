"""Exercise only the two F27 native functions in the working DB, then roll back."""
from pathlib import Path
import json
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.local_semantic_admission import semantic_assertion_identity
from corpus_structure.settings import Settings

source = Path('python/corpus-structure/src/corpus_structure/semantic/sql/record_publication.sql').read_text()
engine = create_engine(make_url(Settings().database.sqlalchemy_url).set(username='paul'))
with engine.connect() as conn:
    tx = conn.begin()
    try:
        for name in ('local_semantic_publication_candidates', 'validate_local_semantic_assertions'):
            start = source.index('CREATE OR REPLACE FUNCTION data.' + name + '(')
            end = source.index('END $semantic$;', start) + len('END $semantic$;')
            conn.exec_driver_sql(source[start:end])
        current = conn.execute(text('SELECT a.*,c.run_id FROM data.local_semantic_assertion a JOIN ops.input_cut c ON c.id=a.cut_id ORDER BY a.evaluation_id DESC LIMIT 1')).mappings().one()
        run = conn.execute(text('SELECT * FROM ops.run WHERE id=:id'),dict(id=current['run_id'])).mappings().one()
        rows = conn.scalar(text('SELECT data.local_semantic_publication_candidates(:p,:r,:run,:cut)'),dict(p=run['project_id'],r=run['release_id'],run=run['id'],cut=current['cut_id']))
        conn.exec_driver_sql('CREATE TEMP TABLE sp_local_semantic_assertion ON COMMIT DROP AS SELECT * FROM data.local_semantic_assertion WHERE false')
        conn.exec_driver_sql('ALTER TABLE sp_local_semantic_assertion DROP COLUMN release_id, DROP COLUMN realization_id')
        columns = list(rows[0])
        conn.execute(text('INSERT INTO pg_temp.sp_local_semantic_assertion ('+','.join(columns)+') VALUES ('+','.join(':'+c for c in columns)+')'),rows)
        conn.execute(text('SELECT data.validate_local_semantic_assertions(:r,:z)'),dict(r=run['release_id'],z=run['result_realization_id']))
        rejected = []
        for field, value in {
            'unit_id': rows[0]['unit_id'] + 1000000,
            'pass_id': rows[0]['pass_id'] + 1000000,
            'frame_id': rows[0]['frame_id'] + 1000000,
            'cut_id': rows[0]['cut_id'] + 1000000,
            'origin_task_id': rows[0]['origin_task_id'] + 1000000,
            'selected_task_id': rows[0]['selected_task_id'] + 1000000,
            'evaluation_id': rows[0]['evaluation_id'] + 1000000,
            'evaluation_digest': '0' * 64,
            'case_id': 'foreign-case',
            'statement_json': '{"target_id":"forged"}',
        }.items():
            savepoint = conn.begin_nested()
            try:
                changed = rows[0] | {field: value}
                changed['assertion_id'] = semantic_assertion_identity({key: val for key, val in changed.items() if key != 'assertion_id'})
                conn.execute(text('UPDATE pg_temp.sp_local_semantic_assertion SET '+field+'=:value,assertion_id=:new WHERE assertion_id=:old'),
                             dict(value=value,new=changed['assertion_id'],old=rows[0]['assertion_id']))
                try:
                    conn.execute(text('SELECT data.validate_local_semantic_assertions(:r,:z)'),dict(r=run['release_id'],z=run['result_realization_id']))
                except DBAPIError:
                    rejected.append(field)
                else:
                    raise AssertionError('malformed mixed batch was accepted: ' + field)
            finally:
                savepoint.rollback()
        print(json.dumps(dict(outcome='passed',candidate_count=len(rows),run_id=run['id'],cut_id=current['cut_id'],rejected_mixed_batch_fields=rejected,scope='rollback-only two-function existing native witness smoke and malformed controls')))

    finally:
        tx.rollback()
engine.dispose()
