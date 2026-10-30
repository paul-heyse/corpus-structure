"""Activate only the explicitly completed and selected final releases through native CAS."""
import json
from sqlalchemy import select
from corpus_structure.settings import Settings
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.releases import load_release, activate_release
from corpus_structure.semantic.authored_sql import has_authored_sql, analyze_archived_sql

settings=Settings()
receipts=[]
for project,run_id in [('production-efficiency',4),('production-efficiency-transfer',5),('production-efficiency-frame',6)]:
    with open_runtime_engine(settings,'efficiency-final-release',purpose='read') as engine, engine.connect() as conn:
        run=conn.execute(select(table('ops.run')).where(table('ops.run').c.id==run_id,table('ops.run').c.project_id==project)).mappings().one()
        assert run['status']=='finished' and run['result_realization_id']
        prepared=load_release(conn,run['release_id'])
        sql=analyze_archived_sql(conn,prepared.release_id) if has_authored_sql(prepared) else {}
    with open_runtime_engine(settings,'efficiency-final-activate',purpose='admit') as engine, engine.begin() as conn:
        projects=table('data.project')
        parent=conn.execute(select(projects).where(projects.c.project_id==project)).mappings().one()
        assert parent['selected_result_run_id']==run_id
        token=activate_release(conn,project,prepared.release_id,expected_parent=parent['active_release_id'],expected_generation=parent['generation'],sql_admissions=sql)
        receipts.append({'project':project,'run_id':run_id,'release_id':token.release_id,'generation':token.generation})
print(json.dumps(receipts,indent=2))
