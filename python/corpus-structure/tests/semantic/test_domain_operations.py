"""Native sealed report cut -> fresh qualified result with independent policy expectations."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from sqlalchemy import insert,select,text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.evidence import RenditionContent,Segment
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.semantic import SourceArtifact,SourceBundle,ResolvedDependencies,PreparationProfile,prepare_release
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.domain_operations import consolidate_cut,domain_rule_inputs,DomainOperationRefused
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.operations import (OperationBinding,create_run,record_method,create_task,claim_tasks,complete_task,
    register_document,store_rendition,seal_cut)
from corpus_structure.semantic.proposals import proposal_inputs,locate_proposal,ProposalFrame,ProposalSentence
from corpus_structure.semantic.releases import persist_release


def fixture(admin,writer,path,*,rules=b'rules: []\n',graph=False,duplicate=False):
    core=Path(__file__).parents[2]/'src/corpus_structure/model/semantic/core.yaml'
    schema={'id':'https://example.org/domain','name':'domain','imports':['semantic_core'],
        'prefixes':{'ex':'https://example.org/'},'default_prefix':'ex',
        'classes':{'Person':{'is_a':'Entity','attributes':{'name':{'range':'string'}}}}}
    if graph:
        schema['classes']['Person']['attributes'].update({'parent':{'range':'Person','inverse':'child','multivalued':True},'child':{'range':'Person','multivalued':True}})
    deps=domain_rule_inputs(ResolvedDependencies(),rules)
    bundle=SourceBundle('domain',(SourceArtifact('domain',yaml.safe_dump(schema).encode()),SourceArtifact('semantic_core',core.read_bytes())))
    bundle=observation_inputs(proposal_inputs(bundle,deps))
    bundle,deps=analytical_inputs(bundle,deps)
    prepared=prepare_release(bundle,deps)
    with admin.begin() as conn:
        persist_release(conn,bundle,deps,PreparationProfile(),prepared)
        conn.execute(insert(table('data.project')).values(project_id='p'))
        conn.execute(insert(table('data.realization')).values(realization_id='source',project_id='p',release_id=prepared.release_id))
    original=b'<p>Alice is here.</p>';path.write_bytes(original)
    with writer.begin() as conn:
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'source',0,b'{}'),
                       kind='full',options={},code_commit='test')
        cid=record_method(conn,SimpleNamespace(name='agent.opus',version='1',family='agent',tier='agent',confidence_source='agent'),
                          'extract',{},'config')
        document=register_document(conn,project_id='p',source_uri='page.html',original_path=str(path),original=original,
                                   metadata={'page':'page.html'})
        task=create_task(conn,run_id=run,config_id=cid,stage='propose',unit_type='document',unit_id=document,
                         unit_key='page#one',input_hash='input')
        claim=claim_tasks(conn,run_id=run,config_id=cid,holder='worker')[0]
        content=RenditionContent(canonical_text='Alice is here.',document=Segment(kind=SegmentKind.DOCUMENT,start=0,end=14))
        rid=store_rendition(conn,run_id=run,document_id=document,content=content,task_id=task,config_id=cid,parse_detail={})
    raw={'unit_ref':'page#one','entities':[{'id':'person','class_iri':'https://example.org/Person','label':'Alice'}],
         'statements':[{'id':'s','kind':'remark','anchor':'page#one'}],
         'claims':[{'id':'c','subject':'person','predicate':'https://example.org/name',
                    'object':{'kind':'text','text':'Alice'},'qualification':{'modality':'asserted','polarity':True},
                    'establishment':'stated','statement':'s','statement_role':'conclusion',
                    'evidence':[{'sentence':'s1','quote':'Alice is here.','role':'primary'}]}],
         'alternatives':[],'unsupported':[{'id':'u','kind':'uninterpreted','reason':'not expressed by selected schema',
              'text':'Alice is here.','evidence':[{'sentence':'s1','quote':'Alice is here.','role':'primary'}]}]}
    if graph:
        raw['entities'].append({'id':'other','class_iri':'https://example.org/Person','label':'Bob'})
        raw['claims'].append({**raw['claims'][0],'id':'relation','predicate':'https://example.org/parent','object':{'kind':'entity','target':'other'}})
    if duplicate:
        raw['statements'].append({'id':'s2','kind':'theorem','anchor':'page#two'})
        raw['claims'].append({**raw['claims'][0],'id':'duplicate','statement':'s2'})
    located=locate_proposal(prepared,raw,ProposalFrame('page#one','Alice is here.',(ProposalSentence('s1','page#sentence',0,14),)))
    with writer.begin() as conn:
        complete_task(conn,task_id=task,attempt=claim['attempt'],holder='worker',prepared=prepared,
            observations=[{'payload_definition':'AgentStoredBatch','item_key':'proposal','kind':'claim_proposal',
                           'payload':located.stored.model_dump(mode='python'),'rendition_id':rid}])
        cut=seal_cut(conn,run,'final',final=True)
    return prepared,run,cut


def test_actual_cut_publishes_fresh_result_and_preserves_reports(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    result=consolidate_cut(semantic_writer_engine,cut,'evaluated')
    assert result.run_id==run and result.realization_id=='evaluated' and result.reports==1
    assert consolidate_cut(semantic_writer_engine,cut,'evaluated').receipt==result.receipt
    with semantic_writer_engine.connect() as conn:
        job=conn.execute(select(table('ops.run')).where(table('ops.run').c.id==run)).mappings().one()
        assert job['status']=='finished' and job['result_realization_id']=='evaluated'
        assert conn.execute(select(table('data.realization').c.data_revision).where(table('data.realization').c.realization_id=='source')).scalar_one()==0
        assert conn.execute(select(table('data.occurrence')).where(table('data.occurrence').c.realization_id=='evaluated')).all()
        assert conn.execute(select(table('data.evidence_source'))).all()
        cover=conn.execute(select(table('data.coverage').c.family,table('data.coverage').c.outcome)).all()
        assert ('unsupported','partial') in cover
        original=conn.execute(select(table('kb.observation').c.payload)).scalar_one()
        assert original['statements'][0]['id']=='s' and original['unsupported'][0]['id']=='u'


def test_released_rule_rejects_scientific_claim_without_erasing_source(semantic_db_engine,semantic_writer_engine,tmp_path):
    rules=b'''rules:
- id: test.reject
  applies_to: ex:name
  at: [finalize]
  severity: error
  check: "claim.value&.v == 'Bob'"
'''
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',rules=rules)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        outcomes=conn.execute(select(table('data.assessment').c.outcome)).scalars().all()
        assert 'rejected' in outcomes and 'refuted' in outcomes
        assert len(conn.execute(select(table('data.occurrence'))).all())>=2
        name=next(p.iri for d in prepared.definitions if d.name=='Person' for p in d.properties if p.name=='name')
        assert not conn.execute(select(table('data.fact').c.fact_id).join(table('data.selection'),
            table('data.selection').c.fact_id==table('data.fact').c.fact_id).where(table('data.fact').c.property_id==name)).first()


def test_atomic_cut_inference_has_distinct_exact_receipts(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',graph=True)
    result=consolidate_cut(semantic_writer_engine,cut,'evaluated')
    assert result.receipt.data_revision==1
    assert result.data_revision==2
    assert len(result.derivation_receipts)==1 and result.derivation_receipts[0].data_revision==2
    assert consolidate_cut(semantic_writer_engine,cut,'evaluated')==result
    with semantic_writer_engine.connect() as conn:
        rows=conn.execute(text("SELECT f.subject_id,f.property_id,v.entity_id FROM data.fact f JOIN data.typed_value v ON (v.release_id,v.realization_id,v.value_id)=(f.release_id,f.realization_id,f.object_value_id) WHERE f.realization_id='evaluated' AND f.property_id IN ('https://example.org/parent','https://example.org/child')")).all()
        parent=next(row for row in rows if row.property_id.endswith('/parent'))
        assert (parent.entity_id,'https://example.org/child',parent.subject_id) in rows
        assert conn.execute(select(table('data.derivation'))).all()


def test_native_finish_refuses_source_occurrence_without_cut_evidence(semantic_db_engine,semantic_writer_engine,tmp_path):
    from corpus_structure.semantic.domain_operations import _cut_input
    from corpus_structure.semantic.publication import publish_on_connection
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    inputs=_cut_input(semantic_writer_engine,cut,'hostile')
    batch=replace(inputs.batch,evidence_source=())
    with pytest.raises(DBAPIError,match='source occurrence has no located evidence'):
        with semantic_writer_engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn,conn.begin():
            conn.execute(text('SELECT data.begin_evaluation(:cut,:out)'),{'cut':cut,'out':'hostile'})
            publish_on_connection(conn,batch)
            conn.execute(text('SELECT data.finish_evaluation(:cut,:out,:batch)'),{'cut':cut,'out':'hostile','batch':batch.batch_id})
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table('data.realization')).where(table('data.realization').c.realization_id=='hostile')).first()
        assert conn.execute(select(table('ops.run').c.result_realization_id).where(table('ops.run').c.id==run)).scalar_one() is None


def test_stage_disposal_refuses_writer_owned_imitation(semantic_writer_engine):
    with pytest.raises(DBAPIError,match='untrusted staging relation sp_entity'):
        with semantic_writer_engine.begin() as conn:
            conn.exec_driver_sql('CREATE TEMP TABLE sp_entity(entity_id text)')
            conn.exec_driver_sql('SELECT data.end_stage()')


def test_same_fact_reports_keep_statement_specific_rule_decisions(semantic_db_engine,semantic_writer_engine,tmp_path):
    rules=b'rules:\n- id: test.statement\n  applies_to: ex:name\n  at: [finalize]\n  severity: error\n  check: "claim.statement_kind == \'theorem\'"\n'
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',rules=rules,duplicate=True)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        o,f,a=table('data.occurrence'),table('data.fact'),table('data.assessment')
        decisions=conn.execute(select(o.c.fact_id,a.c.outcome).join(f,(f.c.fact_id==o.c.fact_id)&(f.c.realization_id==o.c.realization_id))
            .join(a,a.c.occurrence_id==o.c.occurrence_id).where(f.c.property_id=='https://example.org/name',a.c.operation_id=='consolidate.status')).all()
        assert len(decisions)==2 and len({r.fact_id for r in decisions})==1
        assert {r.outcome for r in decisions}=={'accepted','rejected'}
        selected=conn.execute(select(table('data.selection').c.fact_id).where(table('data.selection').c.fact_id==decisions[0].fact_id)).scalar_one()
        assert selected==decisions[0].fact_id
