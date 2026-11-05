"""Exercise the actual predecessor SELECT against rollback-only native SQL fixtures.

Two historical immutable origins have one envelope identity. Only the origin
selected in the publication cut is applicable. This is query mechanics, not source
semantic quality or whole public-admission qualification.
"""
from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import text
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

sql_path=Path('python/corpus-structure/src/corpus_structure/semantic/sql/structural_publication.sql')
source=sql_path.read_text();start=source.index('    SELECT origin.id,result.body');end=source.index(';',start)
statement=source[start:end].replace(' INTO STRICT upstream','')
for name in ('cut_task','task_result','task','run'):
    statement=statement.replace('ops.'+name+' ', 'pg_temp.fixture_'+name+' ')
for name in ('p_cut','p_run','p_release','p_project'):
    statement=statement.replace(name, ':'+name)
statement=statement.replace("member->>'relation_product_id'", "CAST(:member AS jsonb)->>'relation_product_id'")
checks={}
with open_runtime_engine(Settings(),'pce-dossier-predecessor-control',purpose='maintenance') as engine:
    with engine.connect() as conn:
        tx=conn.begin()
        try:
            conn.execute(text('CREATE TEMP TABLE fixture_run(id bigint, project_id text) ON COMMIT DROP'))
            conn.execute(text('CREATE TEMP TABLE fixture_task(id bigint,run_id bigint,release_id text,status text,unit_type text,reused_task_id bigint) ON COMMIT DROP'))
            conn.execute(text('CREATE TEMP TABLE fixture_cut_task(cut_id bigint,task_id bigint,origin_task_id bigint) ON COMMIT DROP'))
            conn.execute(text('CREATE TEMP TABLE fixture_task_result(task_id bigint,body jsonb) ON COMMIT DROP'))
            conn.execute(text("INSERT INTO fixture_run VALUES (1,'control'),(2,'control'),(3,'control')"))
            conn.execute(text("INSERT INTO fixture_task VALUES (101,1,'release-control','done','run',NULL),(102,2,'release-control','done','run',NULL),(201,3,'release-control','reused','run',102)"))
            conn.execute(text('INSERT INTO fixture_cut_task VALUES (99,201,102)'))
            product={'kind':'qualified_comparison','inputs':{'scope':'fixture','sources':[]}}
            conn.execute(text('INSERT INTO fixture_task_result VALUES (101,CAST(:body AS jsonb)),(102,CAST(:body AS jsonb))'),{'body':canonical_bytes({'structural_product':product}).decode()})
            identity=conn.scalar(text("SELECT 'structural:'||encode(sha256(convert_to(data.canonical_json(CAST(:product AS jsonb)),'UTF8')),'hex')"),{'product':canonical_bytes(product).decode()})
            params=dict(p_cut=99,p_run=3,p_release='release-control',p_project='control',member=json.dumps({'relation_product_id':identity}))
            historical=conn.scalar(text("SELECT count(*) FROM fixture_task_result WHERE 'structural:'||encode(sha256(convert_to(data.canonical_json(body->'structural_product'),'UTF8')),'hex')=:identity"),{'identity':identity})
            assert historical==2
            selected=conn.execute(text(statement),params).mappings().all()
            assert [row['id'] for row in selected]==[102]
            checks['two_historical_origins_one_exact_selected']=True
            assert conn.execute(text(statement),{**params,'p_cut':100}).mappings().all()==[]
            checks['missing_selected_predecessor_refuses']=True
            conn.execute(text("UPDATE fixture_run SET project_id='foreign' WHERE id=2"))
            assert conn.execute(text(statement),params).mappings().all()==[]
            checks['foreign_origin_project_refuses']=True
            conn.execute(text("UPDATE fixture_run SET project_id='control' WHERE id=2"))
            conn.execute(text('UPDATE fixture_task SET reused_task_id=101 WHERE id=201'))
            assert conn.execute(text(statement),params).mappings().all()==[]
            checks['selected_origin_disagreement_refuses']=True
        finally:
            tx.rollback()
result=dict(outcome='passed',checks=checks,scope='production predecessor SELECT with native rollback-only controlled relations; no public quality claim')
with Path(__file__).with_name('raw').joinpath('dossier-predecessor-148.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
