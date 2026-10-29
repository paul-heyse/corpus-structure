"""Protected automated hold fencing and cancellation keep the durable first result."""
from types import SimpleNamespace
import pytest
from sqlalchemy import select,text,update,insert
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding,OperationConflict,create_run,record_method,create_task,claim_tasks,hold_agent_result,end_source_run


def test_native_hold_fences_cancellation_and_refuses_forged_error_seed(semantic_db_engine,semantic_writer_engine):
    from .test_operations import setup
    prepared=setup(semantic_db_engine);engine=semantic_writer_engine;t=table('ops.task')
    with engine.begin() as conn:
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'z',0,b'{}'),kind='full',options={},code_commit='test')
        cfg=record_method(conn,SimpleNamespace(name='agent',version='1',family='agent',tier='agent',confidence_source=None),'default',{},'agent-cfg')
        task=create_task(conn,run_id=run,config_id=cfg,stage='propose',unit_type='run',input_hash='input',packet_hash='packet',agent=True)
        claim=claim_tasks(conn,run_id=run,config_id=cfg,holder='agent:first',agent=True)[0]
    with engine.begin() as conn:
        assert hold_agent_result(conn,task_id=task,attempt=claim['attempt'],holder='agent:first',packet_hash='packet',clean=False,result={'issues':['uncertain']})
        with pytest.raises(DBAPIError) as blocked:
            with engine.begin() as cancellation:
                cancellation.execute(text("SET LOCAL lock_timeout='100ms'"))
                end_source_run(cancellation,run)
        assert blocked.value.orig.sqlstate=='55P03'
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:conn.execute(update(t).where(t.c.id==task).values(error=None))
    with pytest.raises(DBAPIError,match='protected submission'):
        with engine.begin() as conn:conn.execute(insert(t).values(run_id=run,release_id=prepared.release_id,method_config_id=cfg,stage='propose',unit_type='run',input_hash='forged',packet_hash='packet',attempt=0,status='awaiting_agent',cost={},priority=0,created_at=text('clock_timestamp()'),error={'semantic_proposal_first_result':{}}))
    with engine.begin() as conn:
        assert end_source_run(conn,run)==1
        assert conn.execute(select(t.c.error).where(t.c.id==task)).scalar_one()['semantic_proposal_first_result']['result']['issues']==['uncertain']
    with pytest.raises(OperationConflict):
        with engine.begin() as conn:hold_agent_result(conn,task_id=task,attempt=claim['attempt'],holder='agent:first',packet_hash='packet',clean=False,result={})
