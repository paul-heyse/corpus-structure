"""Native run bindings, terminal fences and immutable consolidation cuts."""
from types import SimpleNamespace
import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic import SourceBundle, SourceArtifact, prepare_release
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, OperationConflict, create_run,record_method,create_task,claim_tasks,complete_task,seal_cut,cut_observations


def setup(engine, *, observations=False):
    bundle=SourceBundle('m',(SourceArtifact('m',b'''id: https://example/m
name: m
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
 integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
 boolean: {base: bool, uri: 'http://www.w3.org/2001/XMLSchema#boolean'}
classes:
 Report:
  attributes:
   text: {required: true}
'''),))
    if observations:
        from corpus_structure.semantic.observations import observation_inputs
        from pathlib import Path
        core=SourceArtifact('core',(Path(__file__).parents[2]/'src/corpus_structure/model/semantic/core.yaml').read_bytes())
        root=bundle.sources[0]
        bundle=SourceBundle('m',(core,SourceArtifact(root.name,root.content.split(b'types:',1)[0].replace(b'default_prefix: ex',b'default_prefix: ex\nimports: [core]')+b'classes:'+root.content.split(b'classes:',1)[1])))
        bundle=observation_inputs(bundle)
    p=prepare_release(bundle)
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
    with pytest.raises(OperationConflict):
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
    with pytest.raises(OperationConflict):
        with e.begin() as c:complete_task(c,task_id=task,attempt=2,holder='worker',prepared=p,observations=[],outcome='empty')
    with e.connect() as c:assert not c.execute(select(table('kb.observation'))).first()


def test_source_rendition_fidelity_and_original_change(semantic_db_engine,semantic_writer_engine,tmp_path):
    from corpus_structure.semantic.operations import register_document,read_original,store_rendition,read_rendition
    from corpus_structure.core.evidence import Segment,RenditionContent
    from corpus_structure.core.vocab import SegmentKind
    p=setup(semantic_db_engine);e=semantic_writer_engine
    original=tmp_path/'source.html';original.write_bytes(b'<p>source</p>')
    content=RenditionContent(canonical_text='é🙂\n',document=Segment(kind=SegmentKind.DOCUMENT,start=0,end=3,children=(Segment(kind=SegmentKind.PARAGRAPH,start=0,end=2),)))
    with e.begin() as c:
        run=create_run(c,project_id='p',binding=OperationBinding(p.release_id,'z',0,b'{}'),kind='full',options={},code_commit='test')
        cfg=record_method(c,SimpleNamespace(name='read',version='1',family='ingest',tier='deterministic',confidence_source=None),'default',{},'config')
        task=create_task(c,run_id=run,config_id=cfg,stage='ingest',unit_type='run',input_hash='same')
        doc=register_document(c,project_id='p',source_uri='file:source',original_path=str(original),original=original.read_bytes())
        ren=store_rendition(c,run_id=run,document_id=doc,content=content,task_id=task,config_id=cfg,parse_detail={'diagnostic':'kept'})
        assert read_rendition(c,ren)==content
        assert read_original(c,doc)==original.read_bytes()
        assert store_rendition(c,run_id=run,document_id=doc,content=content,task_id=task,config_id=cfg,parse_detail={'diagnostic':'kept'})==ren
    original.write_bytes(b'changed')
    with e.connect() as c:
        with pytest.raises(OperationConflict):read_original(c,doc)


def test_recognizer_terminal_source_boundary_and_coverage(semantic_db_engine,semantic_writer_engine):
    from pydantic import BaseModel
    from corpus_structure.core.method import UnitRef,UnitResult,ObservationDraft,CoverageDraft
    from corpus_structure.core.vocab import TaskUnitType,ObservationOutcome,ObservationKind
    from corpus_structure.semantic.operations import complete_unit_result
    from corpus_structure.semantic.observations import source_python
    class Payload(BaseModel):
        text:str
    p=setup(semantic_db_engine,observations=True);e=semantic_writer_engine
    method=SimpleNamespace(name='read',version='1',family='ingest',tier='deterministic',confidence_source=None)
    with e.begin() as c:
        run=create_run(c,project_id='p',binding=OperationBinding(p.release_id,'z',0,b'{}'),kind='full',options={},code_commit='test')
        cfg=record_method(c,method,'default',{},'config')
        task=create_task(c,run_id=run,config_id=cfg,stage='ingest',unit_type='run',unit_key='unit:1',input_hash='same')
        claimed=claim_tasks(c,run_id=run,config_id=cfg,holder='worker')[0]
    draft=ObservationDraft(kind=ObservationKind.AUTHOR_MARKUP,payload=Payload(text='exact'),payload_class=Payload,payload_version='1')
    result=UnitResult(ref=UnitRef(TaskUnitType.RUN,unit_key='unit:1'),outcome=ObservationOutcome.PRODUCED,observations=(draft,draft),coverage=(CoverageDraft(family='parse',scope='unit:1',outcome='partial',reason='unsupported tail'),))
    with e.begin() as c:
        ids=complete_unit_result(c,task_id=task,attempt=claimed['attempt'],holder='worker',prepared=p,result=result,method=method,configuration_hash='config',source='file:source')
        assert len(ids)==2
        envelope=c.execute(select(table('ops.task_result').c.body)).scalar_one()
        assert envelope['coverage']==[{'family':'parse','scope':'unit:1','outcome':'partial','reason':'unsupported tail'}]
        rows=c.execute(select(table('kb.observation'))).mappings().all()
        assert [source_python(r['payload']['payload']) for r in rows]==[{'text':'exact'},{'text':'exact'}]
        assert len({r['observation_key'] for r in rows})==2


def test_current_ingest_and_profile_graph_on_semantic_storage(semantic_db_engine,semantic_writer_engine,tmp_path):
    from pathlib import Path
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.core.vocab import Stage
    from corpus_structure.ingest.methods import METHODS
    from corpus_structure.methods.math.methods import METHODS as MATH_METHODS
    from corpus_structure.orchestrate.registry import MethodRegistry,MethodsFile
    from corpus_structure.orchestrate.runner import Graph,Step
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.semantic.operations import register_document
    p=setup(semantic_db_engine,observations=True);e=semantic_writer_engine
    raw=tmp_path/'input.html';raw.write_text('<html><body><h1>Source</h1><p>A paragraph with two sentences. Another sentence.</p></body></html>')
    sources=tmp_path/'sources';sources.mkdir()
    (sources/'test.yaml').write_text("version: '1'\nroot: toy\napplies_to: 'toy/*.html'\nlanguage: english\ntitle: h1\nsections: [h1]\n")
    registry=MethodRegistry((*METHODS,*MATH_METHODS),MethodsFile(sections={'math':{'macros':{},'constants':[]},'binders':{'sentence_initial':['let'],'clause':[],'reopen':[],'section_wide':[]}},configs={'ingest.html':{'default':{'source_profile':'test'}},'segment.sentences':{'default':{}},'profile.segments':{'default':{}}}),sources=sources)
    with e.begin() as c:register_document(c,project_id='p',source_uri='toy/input.html',original_path=str(raw),original=raw.read_bytes())
    from corpus_structure.orchestrate.phase0 import PHASE0
    graph=PHASE0
    report=run_source_methods(e,project_id='p',prepared=p,binding=OperationBinding(p.release_id,'z',0,b'{}'),registry=registry,graph=graph,method_settings=MethodSettings(data_dir=tmp_path,model_cache=tmp_path))
    assert report.status=='source_ready' and report.cut_id is not None
    with e.connect() as c:
        assert c.execute(select(table('kb.rendition').c.canonical_text)).scalar_one()=='Source\n\nA paragraph with two sentences. Another sentence.'
        assert c.execute(select(table('ops.measurement').c.metric)).first()
        assert len(c.execute(select(table('ops.cut_task'))).all())==5


def test_reuse_requires_complete_bound_meaning(semantic_db_engine,semantic_writer_engine):
    p=setup(semantic_db_engine);e=semantic_writer_engine
    method=SimpleNamespace(name='read',version='1',family='ingest',tier='deterministic',confidence_source=None)
    def start(c,dependencies):
        run=create_run(c,project_id='p',binding=OperationBinding(p.release_id,'z',0,dependencies),kind='full',options={},code_commit='test')
        cfg=record_method(c,method,'default',{},'config')
        return run,cfg
    with e.begin() as c:
        first,cfg=start(c,b'{}')
        task=create_task(c,run_id=first,config_id=cfg,stage='ingest',unit_type='run',input_hash='same')
        claim_tasks(c,run_id=first,config_id=cfg,holder='worker')
        complete_task(c,task_id=task,attempt=1,holder='worker',prepared=p,observations=[],outcome='empty')
    with e.begin() as c:
        second,cfg=start(c,b'{}')
        same=create_task(c,run_id=second,config_id=cfg,stage='ingest',unit_type='run',input_hash='same')
        changed,cfg=start(c,b'{"policy":"changed"}')
        different=create_task(c,run_id=changed,config_id=cfg,stage='ingest',unit_type='run',input_hash='same')
        t=table('ops.task')
        assert c.execute(select(t.c.status,t.c.reused_task_id).where(t.c.id==same)).one()==('reused',task)
        assert c.execute(select(t.c.status,t.c.reused_task_id).where(t.c.id==different)).one()==('pending',None)
