"""Native run bindings, terminal fences and immutable consolidation cuts."""
from types import SimpleNamespace
import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic import SourceBundle, SourceArtifact, prepare_release
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, OperationConflict, create_run,record_method,create_task,claim_tasks,complete_task,seal_cut,cut_observations


def setup(engine):
    p=prepare_release(SourceBundle('m',(SourceArtifact('m',b'''id: https://example/m
name: m
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
 Report:
  attributes:
   text: {required: true}
'''),)))
    with engine.begin() as c:
        c.execute(insert(table('sem.release')).values(release_id=p.release_id,content_digest='test',profile='test',prepared_bytes=b'{}',manifest_bytes=b'{}'))
        c.execute(insert(table('data.project')).values(project_id='p'))
        c.execute(insert(table('data.realization')).values(realization_id='z',release_id=p.release_id,project_id='p'))
    return p


def test_native_terminal_fence_replay_and_sealed_cut(semantic_db_engine,semantic_writer_engine):
    p=setup(semantic_db_engine); e=semantic_writer_engine
    binding=OperationBinding(p.release_id,'z',0,b'{}')
    with e.begin() as c:
        run=create_run(c,project_id='p',binding=binding,kind='full',options={},code_commit='test')
        config=record_method(c,SimpleNamespace(name='read',version='1',family='ingest',tier='deterministic',confidence_source=None),'default',{},'config:one')
        task=create_task(c,run_id=run,config_id=config,stage='ingest',unit_type='run',input_hash='same')
        claim=claim_tasks(c,run_id=run,config_id=config,holder='worker')[0]
    observations=[{'payload_definition':'Report','item_key':'a','payload':{'text':'same'},'kind':'reading'}, {'payload_definition':'Report','item_key':'b','payload':{'text':'same'},'kind':'reading'}]
    with e.begin() as c:
        ids=complete_task(c,task_id=task,attempt=claim['attempt'],holder='worker',prepared=p,observations=observations)
    with e.begin() as c:
        assert complete_task(c,task_id=task,attempt=claim['attempt'],holder='worker',prepared=p,observations=observations)==ids
        pending=create_task(c,run_id=run,config_id=config,stage='ingest',unit_type='run',input_hash='late')
        later=claim_tasks(c,run_id=run,config_id=config,holder='late')[0]
        cut=seal_cut(c,run,'final',final=True)
        assert seal_cut(c,run,'final',final=True)==cut
        rows=cut_observations(c,cut)
        assert [r['payload'] for r in rows]==[{'text':'same'},{'text':'same'}]
        assert len({r['observation_key'] for r in rows})==2
    with pytest.raises(DBAPIError):
        with e.begin() as c:
            complete_task(c,task_id=pending,attempt=later['attempt'],holder='late',prepared=p,observations=observations)
    with pytest.raises(DBAPIError):
        with e.begin() as c:c.execute(table('kb.observation').insert().values(task_id=task))


def test_binding_revision_and_wrong_attempt(semantic_db_engine,semantic_writer_engine):
    p=setup(semantic_db_engine);e=semantic_writer_engine
    with pytest.raises(OperationConflict):
        with e.begin() as c:create_run(c,project_id='p',binding=OperationBinding(p.release_id,'z',1,b'{}'),kind='full',options={},code_commit='test')
    with e.begin() as c:
        run=create_run(c,project_id='p',binding=OperationBinding(p.release_id,'z',0,b'{}'),kind='full',options={},code_commit='test')
        config=record_method(c,SimpleNamespace(name='read',version='1',family='ingest',tier='deterministic',confidence_source=None),'default',{},'config:one')
        task=create_task(c,run_id=run,config_id=config,stage='ingest',unit_type='run',input_hash='same')
        claim_tasks(c,run_id=run,config_id=config,holder='worker')
    with pytest.raises(DBAPIError):
        with e.begin() as c:complete_task(c,task_id=task,attempt=2,holder='worker',prepared=p,observations=[],outcome='empty')
    with e.connect() as c:assert not c.execute(select(table('kb.observation'))).first()
