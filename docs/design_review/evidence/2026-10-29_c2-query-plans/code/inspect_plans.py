"""Restore Q4's retained rows and read production query SQL plans, without planner forcing."""
from __future__ import annotations
import gzip,json,os,subprocess,shutil,traceback
from pathlib import Path
import psycopg
from sqlalchemy import create_engine,event,text,select,insert
from sqlalchemy.schema import CreateColumn,CreateIndex
from corpus_structure.core.db import metadata
from corpus_structure.schema.compile import compile_schema
from corpus_structure.schema.pack import DOMAINS,load_pack
from corpus_structure.serve.protocol import QueryContext
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry

HERE=Path(__file__).resolve().parents[1]
REPO=HERE.parents[3]
DUMP=REPO/'docs/design_review/evidence/2026-10-28_phase0-model-probes/results/q4/raw/p0q_fk_dataset.sql.gz'
DB=f'ci_c2plans_{os.getpid()}'
report={'restore_comment_omission':'COMMENT ON EXTENSION omitted because cs_template extensions are owned by postgres; rows and indexes unchanged','database':DB,'source':str(DUMP.relative_to(REPO)),'adaptations':[],'page_demand':'max_rows=5 plus one-row lookahead; row_batch=6','queries':{},'errors':[]}
maintenance=psycopg.connect('dbname=postgres port=5434',autocommit=True)
try:
    maintenance.execute(psycopg.sql.SQL('CREATE DATABASE {} TEMPLATE cs_template').format(psycopg.sql.Identifier(DB)))
    with (HERE/'raw/restore.log').open('wb') as log:
        proc=subprocess.Popen(['psql','-X','-v','ON_ERROR_STOP=1','-p','5434','-d',DB],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
        with gzip.open(DUMP,'rb') as source:
            for line in source:
                if not line.startswith(b'COMMENT ON EXTENSION '):
                    proc.stdin.write(line)
        proc.stdin.close()
        if proc.wait()!=0:raise RuntimeError('Q4 restore failed; see restore.log')
    engine=create_engine(f'postgresql+psycopg:///{DB}?port=5434')
    with engine.begin() as conn:
        report['server']=conn.execute(text('SELECT version()')).scalar_one()
        # Model-additive columns affect projection width, never Q4's data or cardinality.
        for table in metadata.tables.values():
            if table.schema not in ('meta','ops','kb','eval') or getattr(table,'is_view',False) or table.info.get('is_view'):continue
            existing=set(conn.execute(text('SELECT column_name FROM information_schema.columns WHERE table_schema=:s AND table_name=:t'),{'s':table.schema,'t':table.name}).scalars())
            if not existing:continue
            for col in table.c:
                if col.name not in existing:
                    # Inspect a SELECT-compatible current projection. Preserve old rows as unknown.
                    rendered=str(CreateColumn(col).compile(dialect=conn.dialect)).replace(' NOT NULL','')
                    if 'GENERATED' in rendered:continue
                    sql=f'ALTER TABLE {table.fullname} ADD COLUMN {rendered}'
                    conn.execute(text(sql));report['adaptations'].append(sql)
        bm25=next(i for i in metadata.tables['kb.segment'].indexes if i.name=='segment_bm25')
        current_bm25=str(CreateIndex(bm25).compile(dialect=conn.dialect))
        conn.execute(text('DROP INDEX kb.segment_bm25'))
        conn.execute(text(current_bm25))
        report['adaptations'].append('Rebuilt legacy BM25 predicate from current generated overlay: '+current_bm25)
        # Q4 predates entity_identity. Build the current relation, retaining entity/claim/edge counts.
        metadata.tables['kb.entity_identity'].create(conn,checkfirst=True)
        mappings={'DistributionFamily':'stat:DistributionFamily','RandomVariable':'stat:FamilyParameter'}
        for old,new in mappings.items():
            conn.execute(text('UPDATE kb.entity SET type=:new WHERE type=:old'),{'old':old,'new':new})
        conn.execute(text("UPDATE kb.entity SET scope='global',scope_segment_id=NULL WHERE type='stat:FamilyParameter'"))
        conn.execute(text("INSERT INTO kb.entity_identity(entity_id,slot,value_entity_id) SELECT e.id,'stat:family',f.id FROM kb.entity e JOIN LATERAL (SELECT id FROM kb.entity f WHERE f.run_id=e.run_id AND f.type='stat:DistributionFamily' ORDER BY id OFFSET (e.id%10) LIMIT 1) f ON true WHERE e.type='stat:FamilyParameter' ON CONFLICT DO NOTHING"))
        report['adaptations'].append('Current synthetic identity projection: volume RandomVariable rows become global FamilyParameter rows with stat:family identities distributed among ten same-run DistributionFamily rows; family/parameter class names are prefixed; legacy Statement names and their CHECK stay unchanged; existing entity/claim/reference cardinalities and IDs retained. This is physical-plan data, not semantic acceptance data.')
        def condition_form(node):
            if not isinstance(node,dict):return node
            node=dict(node)
            op=node.get('op')
            if op in ('and','or'):
                node['args']=[condition_form(x) for x in node.get('args',[])]
            elif op=='not':node['arg']=condition_form(node['arg'])
            elif op=='forall':node['body']=condition_form(node['body'])
            elif op=='pred':node['args']=[{'ref':x['ref']} if isinstance(x,dict) and x.get('t')=='entity' else x for x in node.get('args',[])]
            return node
        changed=[]
        for id_,q in conn.execute(text('SELECT id,qualifiers FROM kb.claim')):
            revised=dict(q)
            for field in ('conditions','core:conditions'):
                if field in revised:revised[field]=condition_form(revised[field])
            if revised!=q:changed.append({'id':id_,'q':json.dumps(revised)})
        if changed:
            conn.execute(text('UPDATE kb.claim SET qualifiers=CAST(:q AS jsonb) WHERE id=:id'),changed)
        report['adaptations'].append(f'Projected {len(changed)} legacy condition payloads: predicate entity args {{t:entity,ref}} become generated {{ref}}; references and relational rows unchanged.')
        report['counts']={n:conn.execute(text(f'SELECT count(*) FROM {n}')).scalar_one() for n in ('kb.entity','kb.claim','kb.claim_ref','kb.claim_entity_ref')}
        run=conn.execute(text('SELECT run_id FROM kb.claim GROUP BY run_id ORDER BY count(*) DESC LIMIT 1')).scalar_one()
        inserted=conn.execute(text("INSERT INTO ops.task(run_id,stage,unit_type,unit_id,unit_key,method_config_id,input_hash,status,reused_task_id,finished_at) SELECT :r,'ingest','document',unit_id,unit_key,method_config_id,'c2-plan-ingest-'||id,'reused',id,now() FROM ops.task WHERE stage='ingest' AND status IN ('done','reused') AND run_id=(SELECT min(run_id) FROM ops.task WHERE stage='ingest' AND status IN ('done','reused'))"),{'r':run}).rowcount
        report['adaptations'].append(f'Added {inserted} ingest reuse tasks to the volume run, so production run_rendition mapping can read its inherited source renditions.')
        conn.execute(text('ANALYZE'))
    compiled=compile_schema([load_pack(DOMAINS/'statistics')])
    captured=[]
    def capture(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith(('SELECT','WITH')):
            captured.append((statement,parameters))
    event.listen(engine,'before_cursor_execute',capture)
    cases={'entity':{'label':'normal'},'claims':{},'statement':{'locator':'special/Normal.html#rel1'},'evidence':{},'find':{'text':'normally distributed'},'unsupported':{},'family_profile':{'family':'normal'},'families_where':{'predicate':'stat:has_distribution'},'relations_between':{'a':'normal','b':'lognormal'},'transformations_of':{'family':'normal'},'parameter_mapping':{'construction':'location-scale family','family':'normal'},'construction_profile':{'construction':'location-scale family'}}
    with engine.connect() as conn:
        key=conn.execute(text('SELECT key FROM kb.claim WHERE run_id=:r ORDER BY key LIMIT 1'),{'r':run}).scalar_one()
        cases['evidence']={'key':key}
        family=conn.execute(text("SELECT key FROM kb.entity WHERE run_id=:r AND type='stat:DistributionFamily' ORDER BY id LIMIT 1"),{'r':run}).scalar_one()
        statement=conn.execute(text("SELECT key FROM kb.entity WHERE run_id=:r AND kind IS NOT NULL ORDER BY id LIMIT 1"),{'r':run}).scalar_one()
        cases['statement']={'key':statement}
        for params in cases.values():
            for field in ('family','construction','a','b'):
                if field in params:params[field]=family
        for name,params in cases.items():
            captured.clear()
            ctx=QueryContext(run,conn,row_batch=6);ctx.reader.__dict__['compiled']=compiled
            query=build_registry(GENERIC,DOMAINS/'statistics')[name]
            try:
                gen=query.rows(ctx,query.params.model_validate(params))
                for i,row in enumerate(gen):
                    if i==2:break
                gen.close()
            except Exception as exc:
                report['errors'].append({'query':name,'error':type(exc).__name__,'detail':str(exc),'traceback':traceback.format_exc()})
            statements=list(captured)
            conn.rollback()
            plans=[]
            raw=conn.connection.driver_connection
            for sql,bindings in statements:
                if not any(t in sql for t in ('kb.claim','kb.entity','kb.segment')):continue
                try:
                    with raw.cursor() as cur:
                        cur.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+sql,bindings)
                        plans.append({'sql':sql,'bindings':bindings,'plan':cur.fetchone()[0]})
                except Exception as exc:
                    conn.rollback()
                    report['errors'].append({'query':name,'explain_error':str(exc)})
            if name=='find' and plans:
                original=plans[0]
                base_sql=original['sql']
                import re
                variants={
                    'native_limit':re.sub(r'FETCH FIRST \(%\(param_2\)s::INTEGER\) ROWS WITH TIES','LIMIT %(param_2)s',base_sql),
                    'without_score_filter':re.sub(r" AND \(kb.segment.text <@> to_bm25query\(%\(query\)s, 'kb.segment_bm25'\)\) < %\(param_1\)s::INTEGER",'',base_sql),
                    'prepared_renditions':re.sub(r'kb.segment.rendition_id IN \(SELECT kb.run_rendition.rendition_id\s+FROM kb.run_rendition\s+WHERE kb.run_rendition.run_id = %\(run_id_1\)s::BIGINT\)', 'kb.segment.rendition_id = ANY(%(renditions)s)',base_sql)}
                report['find_variants']={}
                renditions=list(conn.execute(text('SELECT DISTINCT rendition_id FROM kb.run_rendition WHERE run_id=:r'),{'r':run}).scalars())
                for variant,sql in variants.items():
                    bindings=dict(original['bindings'])|{'renditions':renditions}
                    with raw.cursor() as cur:
                        cur.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+sql,bindings)
                        report['find_variants'][variant]={'sql':sql,'bindings':bindings,'plan':cur.fetchone()[0]}
            report['queries'][name]=plans
            conn.rollback()
    event.remove(engine,'before_cursor_execute',capture)
    engine.dispose()
except Exception as exc:
    report['errors'].append({'fatal_error':type(exc).__name__,'detail':str(exc),'traceback':traceback.format_exc()})
    raise
finally:
    if 'engine' in locals(): engine.dispose()
    maintenance.execute(psycopg.sql.SQL('DROP DATABASE IF EXISTS {}').format(psycopg.sql.Identifier(DB)))
    maintenance.close()
    report['database_dropped']=True
    (HERE/'raw/plans.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print(json.dumps({'counts':report.get('counts'),'errors':[{'query':e.get('query'),'error':e.get('error',e.get('explain_error',''))} for e in report['errors']],'queries':{k:len(v) for k,v in report['queries'].items()}}))
