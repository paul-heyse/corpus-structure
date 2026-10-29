"""The packet's short read transaction serializes a concurrent native input publication."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.operations import OperationBinding,OperationConflict,create_run,lock_input_snapshot
from corpus_structure.semantic.publication import PublicationBatch,publish_on_connection,publish_batch
from .test_operations import setup


def test_native_packet_read_blocks_input_publication_then_rejects_stale_run(semantic_db_engine,semantic_writer_engine):
    prepared=setup(semantic_db_engine);engine=semantic_writer_engine
    with engine.begin() as conn:
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'z',0,b'{}'),kind='full',options={},code_commit='test')
    batch=PublicationBatch(prepared.release_id,'z','advance-input')
    with engine.begin() as packet:
        lock_input_snapshot(packet,run)
        with pytest.raises(DBAPIError) as conflict:
            with engine.connect().execution_options(isolation_level='SERIALIZABLE') as publication,publication.begin():
                publication.execute(text("SET LOCAL lock_timeout='100ms'"))
                publish_on_connection(publication,batch)
        assert conflict.value.orig.sqlstate=='55P03'
    assert publish_batch(engine,batch).data_revision==1
    with pytest.raises(OperationConflict,match='snapshot changed'):
        with engine.begin() as conn:lock_input_snapshot(conn,run)


def test_native_task_configuration_matches_frozen_params_and_version(semantic_db_engine,semantic_writer_engine):
    from types import SimpleNamespace
    from corpus_structure.semantic.operations import record_method,create_task
    prepared=setup(semantic_db_engine);engine=semantic_writer_engine
    def operation(name='read',version='1',agent=False):return SimpleNamespace(name=name,version=version,family='agent' if agent else 'ingest',tier='agent' if agent else 'deterministic',confidence_source=None)
    with engine.begin() as conn:
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'z',0,b'{}'),kind='full',options={'configs':{'read':'good'},'agent_configs':{'current-name':{'model':'allowed'}},'operation_versions':{'read':'1','custom.agent':'5'}},code_commit='test')
        good=record_method(conn,operation(),'default',{},'good')
        wrong_params=record_method(conn,operation(),'different',{'different':True},'bad')
        wrong_version=record_method(conn,operation(version='2'),'default',{},'good')
        agent_good=record_method(conn,operation('custom.agent','5',True),'old-alias',{'model':'allowed'},'agent-good')
        agent_bad=record_method(conn,operation('custom.agent','5',True),'other',{'model':'other'},'agent-bad')
    for config in (wrong_params,wrong_version,agent_bad):
        with pytest.raises(DBAPIError,match='immutable run snapshot'):
            with engine.begin() as conn:create_task(conn,run_id=run,config_id=config,stage='test',unit_type='run',input_hash='same')
    with engine.begin() as conn:
        create_task(conn,run_id=run,config_id=good,stage='ingest',unit_type='run',input_hash='source')
        # Named configurations with identical parameters share method_config identity. The
        # first stored alias cannot override this run's current declared parameter meaning.
        create_task(conn,run_id=run,config_id=agent_good,stage='propose',unit_type='run',input_hash='agent',agent=True)
