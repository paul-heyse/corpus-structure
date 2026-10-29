"""Native sealed report cut -> fresh qualified result with independent policy expectations."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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


def fixture(admin,writer,path,*,rules=b'rules: []\n',graph=False,duplicate=False,formulas=(),known=False,local_known=False,nary=False,broken=False,claim_chain=False,cycle=False,condition=None,two_reports=False,authored_alternative=False,integer_alias=False,math=None,second_math=None,source_macros=None):
    core=Path(__file__).parents[2]/'src/corpus_structure/model/semantic/core.yaml'
    schema:dict[str,Any]={'id':'https://example.org/domain','name':'domain','imports':['semantic_core'],
        'prefixes':{'ex':'https://example.org/'},'default_prefix':'ex',
        'classes':{'Person':{'is_a':'Entity','attributes':{'name':{'range':'string'}}}}}
    if integer_alias:
        schema['types']={'SmallCount':{'typeof':'integer'}}
        schema['classes']['Person']['attributes']['name']={'range':'SmallCount','minimum_value':0}
    if two_reports:schema['classes']['Person']['annotations']={'cs:scope':'global','cs:case':'preserve'}
    if known:
        schema['classes']['Person']['unique_keys']={'by_name':{'unique_key_slots':['name']}}
    if graph:
        schema['classes']['Person']['attributes'].update({'parent':{'range':'Person','inverse':'child','multivalued':True},'child':{'range':'Person','multivalued':True}})
    if formulas:
        schema['classes']['Formula']={'is_a':'ExpressionValue','attributes':{'kind':{'equals_string':'formula'}}}
        schema['classes']['Person']['attributes']['name']={'range':'Formula','inlined':True,'annotations':{'cs:role':'predicate','cs:constraint_scope':'accepted_value'}}
    if nary:
        endpoint='Endpoint' if broken else 'Person'
        if broken:schema['classes']['Endpoint']={'is_a':'Entity','attributes':{'business':{'range':'string','required':True}},'unique_keys':{'business_key':{'unique_key_slots':['business']}}}
        schema['classes']['RoleEntry']={'attributes':{'key':{'identifier':True},'target':{'range':endpoint,'required':True},'ref':{'range':'string'}}}
        schema['classes']['NaryValue']={'is_a':'Value','attributes':{'kind':{'equals_string':'nary'},'endpoint':{'range':endpoint,'required':True},'ref':{'range':'string'},'roles':{'range':'RoleEntry','inlined':True,'multivalued':True}}}
        schema['classes']['Person']['attributes']['relation']={'range':'NaryValue','inlined':True}
    deps=domain_rule_inputs(ResolvedDependencies(),rules)
    bundle=SourceBundle('domain',(SourceArtifact('domain',yaml.safe_dump(schema).encode()),SourceArtifact('semantic_core',core.read_bytes())))
    bundle=observation_inputs(proposal_inputs(bundle,deps))
    bundle,deps=analytical_inputs(bundle,deps)
    prepared=prepare_release(bundle,deps)
    with admin.begin() as conn:
        persist_release(conn,bundle,deps,PreparationProfile(),prepared)
        conn.execute(insert(table('data.project')).values(project_id='p'))
        conn.execute(insert(table('data.realization')).values(realization_id='source',project_id='p',release_id=prepared.release_id))
    if known:
        from corpus_structure.semantic.consolidation import assemble,SourceItem
        from corpus_structure.semantic.publication import publish_batch,EvidenceRow,SelectionRow
        evidence=(EvidenceRow('initial-evidence','prior-source','prior#unit','fixture','1'),)
        initial=assemble(prepared,'source','input-knowledge',tuple(SourceItem('known:alice','Person',name,value,{'modality':'asserted','polarity':True},'prior-source',name,'stated',evidence) for name,value in [('id','known:alice'),('name','Alice')]))
        publish_batch(writer,replace(initial,selection=tuple(SelectionRow(f.fact_id) for f in initial.fact)))
    original=b'<p>Alice is here.</p>';path.write_bytes(original)
    with writer.begin() as conn:
        document=register_document(conn,project_id='p',source_uri='page.html',original_path=str(path),original=original,
                                   metadata={'page':'page.html'})
        document_key=conn.execute(select(table('kb.document').c.key).where(table('kb.document').c.id==document)).scalar_one()
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'source',1 if known else 0,b'{}'),
                       kind='full',options={'corpus':{'documents':[document_key]}},code_commit='test')
        cid=record_method(conn,SimpleNamespace(name='agent.opus',version='1',family='agent',tier='agent',confidence_source='agent'),
                          'extract',{'math':math} if math is not None else {},'config')
        task=create_task(conn,run_id=run,config_id=cid,stage='propose',unit_type='document',unit_id=document,
                         unit_key='page#one',input_hash='input')
        lease=claim_tasks(conn,run_id=run,config_id=cid,holder='worker')[0]
        content=RenditionContent(canonical_text='Alice is here.',document=Segment(kind=SegmentKind.DOCUMENT,start=0,end=14),macros=source_macros or {})
        rid=store_rendition(conn,run_id=run,document_id=document,content=content,task_id=task,config_id=cid,parse_detail={})
    raw:dict[str,Any]={'unit_ref':'page#one','entities':[{'id':'person','class_iri':'https://example.org/Person','label':'Alice'}],
         'statements':[{'id':'s','kind':'remark','anchor':'page#one'}],
         'claims':[{'id':'c','subject':'person','predicate':'https://example.org/name',
                    'object':{'kind':'text','text':'Alice'},'qualification':{'modality':'asserted','polarity':True},
                    'establishment':'stated','statement':'s','statement_role':'conclusion',
                    'evidence':[{'sentence':'s1','quote':'Alice is here.','role':'primary'}]}],
         'alternatives':[],'unsupported':[{'id':'u','kind':'uninterpreted','reason':'not expressed by selected schema',
              'text':'Alice is here.','evidence':[{'sentence':'s1','quote':'Alice is here.','role':'primary'}]}]}
    if known:
        if local_known:raw['entities'][0]['attributes']=[{'predicate':'https://example.org/name','value':{'kind':'text','text':'Alice'}}]
        else:
            raw['entities']=[]
            raw['claims'][0]['subject']='known:alice'
    if graph:
        raw['entities'].append({'id':'other','class_iri':'https://example.org/Person','label':'Bob'})
        raw['claims'].append({**raw['claims'][0],'id':'relation','predicate':'https://example.org/parent','object':{'kind':'entity','target':'other'}})
    if duplicate:
        raw['statements'].append({'id':'s2','kind':'theorem','anchor':'page#two'})
        raw['claims'].append({**raw['claims'][0],'id':'duplicate','statement':'s2'})
    if formulas:
        base=raw['claims'][0]
        raw['claims']=[{**base,'id':'formula'+str(i),'object':{'kind':'formula','language':'latex','expression':value}} for i,value in enumerate(formulas)]
    if nary:
        raw['entities'].append({'id':'other','class_iri':'https://example.org/'+('Endpoint' if broken else 'Person'),'reference':{'description':'outside unresolved person'}})
        raw['claims'][0].update(predicate='https://example.org/relation',object={'kind':'nary','endpoint':'other','ref':'other','roles':{'r':{'key':'r','target':'other','ref':'other'}}})
    if claim_chain:
        base=raw['claims'][0]
        raw['claims']=[{**base,'id':'p1'},{**base,'id':'p2'},
            {**base,'id':'d1','qualification':{**base['qualification'],'condition':{'kind':'claim','ref':'p1'}}},
            {**base,'id':'d2','qualification':{**base['qualification'],'condition':{'kind':'claim','ref':'p2'}}}]
    if cycle:
        base=raw['claims'][0]
        raw['claims']=[{**base,'id':'a','qualification':{**base['qualification'],'condition':{'kind':'claim','ref':'b'}}},
            {**base,'id':'b','qualification':{**base['qualification'],'condition':{'kind':'claim','ref':'a'}}}]
    if integer_alias:raw['claims'][0]['object']={'kind':'number','number':4}
    if two_reports:raw['claims'][0]['object']['bindings']=[{'symbol':'x','kind':'free'}]
    if authored_alternative:raw['alternatives']=[{'id':'choice','members':[c['id'] for c in raw['claims']],'faithful':True,'reason':'source explicitly contrasts these possibilities'}]
    if condition is not None:
        for claim in raw['claims']:claim['qualification']={**claim['qualification'],'condition':condition}
    frame=ProposalFrame('page#one','Alice is here.',(ProposalSentence('s1','page#sentence',0,14),))
    located=locate_proposal(prepared,raw,frame,known_classes={'known:alice':('https://example.org/Person',)}) if known else locate_proposal(prepared,raw,frame)
    with writer.begin() as conn:
        complete_task(conn,task_id=task,attempt=lease['attempt'],holder='worker',prepared=prepared,
            observations=[{'payload_definition':'AgentStoredBatch','item_key':'proposal','kind':'claim_proposal',
                           'payload':located.stored.model_dump(mode='python'),'rendition_id':rid}])
        if two_reports:
            import copy
            second=copy.deepcopy(raw)
            second['claims'][0]['object']['bindings']=[{'symbol':'x','kind':'constant'}]
            second_located=locate_proposal(prepared,second,ProposalFrame('page#one','Alice is here.',(ProposalSentence('s1','page#sentence',0,14),)))
            second_config=record_method(conn,SimpleNamespace(name='agent.opus',version='1',family='agent',tier='agent',confidence_source='agent'),'extract',{'variant':'second',**({'math':second_math if second_math is not None else math} if second_math is not None or math is not None else {})},'config-second')
            second_task=create_task(conn,run_id=run,config_id=second_config,stage='propose',unit_type='document',unit_id=document,unit_key='page#one',input_hash='input-second')
            second_lease=claim_tasks(conn,run_id=run,config_id=second_config,holder='worker')[0]
            complete_task(conn,task_id=second_task,attempt=second_lease['attempt'],holder='worker',prepared=prepared,observations=[{'payload_definition':'AgentStoredBatch','item_key':'proposal','kind':'claim_proposal','payload':second_located.stored.model_dump(mode='python'),'rendition_id':rid}])
        cut=seal_cut(conn,run,'final',final=True)
    return prepared,run,cut


def test_actual_cut_publishes_fresh_result_and_preserves_reports(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    result=consolidate_cut(semantic_writer_engine,cut,'evaluated')
    assert result.run_id==run and result.realization_id=='evaluated' and result.reports==1
    assert consolidate_cut(semantic_writer_engine,cut,'evaluated').receipt==result.receipt
    class OtherVersion:
        release_id=prepared.release_id
        version='unsupported-operation-version'
        def evaluate(self,inputs,scope,fused):raise AssertionError('unadmitted policy must not evaluate')
    with pytest.raises(DomainOperationRefused,match='policy version'):
        consolidate_cut(semantic_writer_engine,cut,'evaluated',policy=OtherVersion())
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


@pytest.mark.parametrize(('formulas','outcome','selected'),[(('a+b','b+a'),'equivalent',1),(('a+1','a+2'),'different',0),(('f(x)','g(x)'),'undecided',0)])
def test_native_scientific_comparison_preserves_facts_and_uncertainty(semantic_db_engine,semantic_writer_engine,tmp_path,formulas,outcome,selected):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',formulas=formulas)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        a,f,s=table('data.assessment'),table('data.fact'),table('data.selection')
        rows=conn.execute(select(a).where(a.c.operation_id=='scientific.value_equivalence')).mappings().all()
        assert len(rows)==2 and {r['outcome'] for r in rows}=={outcome}
        assert all('other_fact_id' in r['reason'] for r in rows)
        if outcome=='undecided':assert all(r['uncertainty'] for r in rows)
        assert len(conn.execute(select(f.c.fact_id).where(f.c.property_id=='https://example.org/name')).all())==2
        assert len(conn.execute(select(s.c.fact_id).join(f,f.c.fact_id==s.c.fact_id).where(f.c.property_id=='https://example.org/name')).all())==selected


@pytest.mark.parametrize('local_known',[False,True])
def test_known_input_reference_and_declared_key_converge_with_lineage(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path,local_known):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',known=True,local_known=local_known)
    result=consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        lineage=conn.execute(select(table('data.entity_input'))).mappings().one()
        assert lineage['entity_id']=='known:alice' and lineage['input_entity_id']=='known:alice'
        assert lineage['input_realization_id']=='source' and lineage['input_data_revision']==1 and lineage['run_id']==run
        assert conn.execute(select(table('data.fact').c.subject_id).where(table('data.fact').c.realization_id=='evaluated',table('data.fact').c.property_id=='https://example.org/name')).scalars().all()==['known:alice']
        prior=conn.execute(select(table('data.occurrence').c.realization_id).where(table('data.occurrence').c.source=='prior-source')).scalars().all()
        assert prior and set(prior)=={'source'}
    if not local_known:
        from corpus_structure.semantic.query import read_session
        from corpus_structure.semantic.analytics import load_packet
        uri=semantic_reader_engine.url.set(drivername='postgresql').render_as_string(hide_password=False)
        with read_session(semantic_reader_engine,'evaluated') as session:
            packet=load_packet(session,uri)
        assert packet.relations['entity_input'].to_pylist()[0]['input_data_revision']==1
        assert len(packet.relations['fact_input'].to_pylist())==2
        assert {row['input_realization_id'] for row in packet.relations['fact_input'].to_pylist()}=={'source'}



def test_actual_cut_nested_references_preserve_literal_fields_and_unresolved_source(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path):
    from corpus_structure.semantic.query import read_session,QuerySpec
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',nary=True)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with read_session(semantic_reader_engine,'evaluated') as session:
        cls=session.class_handle('Person')
        result=session.query(QuerySpec(cls,session.property_handle(cls,'relation')))
        obj=result.rows[0].object
        assert obj.ref=='other' and obj.endpoint!='other'
        assert obj.roles['r'].ref=='other' and obj.roles['r'].target==obj.endpoint
        refs=session._entities({obj.endpoint})
        assert refs[obj.endpoint].memberships[0].class_iri=='https://example.org/Person'
    with semantic_writer_engine.connect() as conn:
        assessments=conn.execute(select(table('data.assessment').c.outcome).where(table('data.assessment').c.operation_id=='consolidate.status')).scalars().all()
        assert assessments==['candidate']
    with semantic_reader_engine.connect() as conn:
        assert conn.execute(select(table('data.entity_source'))).all()


def test_required_endpoint_identity_is_not_fabricated(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',nary=True,broken=True)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table('data.fact'))).first()
        coverage=conn.execute(select(table('data.coverage').c.outcome,table('data.coverage').c.reason)).all()
        assert any(row.outcome=='partial' and 'required identifying fields' in (row.reason or '') for row in coverage)
        assert conn.execute(select(table('kb.observation').c.payload)).scalar_one()['entities'][1]['reference']['description']=='outside unresolved person'


def test_claim_references_use_canonical_premise_fact_and_separate_source_view_ids(semantic_db_engine,semantic_writer_engine,tmp_path):
    from corpus_structure.semantic.domain_operations import _cut_input
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',claim_chain=True)
    inputs=_cut_input(semantic_writer_engine,cut,'evaluated')
    by_ref={c.local_id:c for c in inputs.candidates}
    assert by_ref['p1'].fact_id==by_ref['p2'].fact_id
    assert by_ref['d1'].fact_id==by_ref['d2'].fact_id
    assert by_ref['d1'].qualification['condition']['ref']==by_ref['p1'].fact_id
    first,second=by_ref['d1'].rule_qualification,by_ref['d2'].rule_qualification
    assert first is not None and second is not None
    assert first['condition']['ref']==by_ref['p1'].occurrence_id
    assert second['condition']['ref']==by_ref['p2'].occurrence_id
    consolidate_cut(semantic_writer_engine,cut,'evaluated')


def test_cyclic_claim_reference_stays_explicit_unresolved_report(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',cycle=True)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table('data.fact'))).first()
        assert 'cyclic source claim reference' in conn.execute(select(table('data.coverage').c.reason)).scalars().all()


@pytest.mark.parametrize('operator',['compare','not'])
def test_scientific_restriction_profile_never_drops_uninterpreted_domain(semantic_db_engine,semantic_writer_engine,tmp_path,operator):
    comparison={'kind':'compare','relation':'>','lhs':{'kind':'formula','language':'latex','expression':'x'},'rhs':{'kind':'formula','language':'latex','expression':'0'}}
    condition=comparison if operator=='compare' else {'kind':'not','term':comparison}
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',formulas=(r'\sqrt{x^2}','x'),condition=condition)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        rows=conn.execute(select(table('data.assessment').c.outcome,table('data.assessment').c.uncertainty).where(table('data.assessment').c.operation_id=='scientific.value_equivalence')).all()
        assert len(rows)==2
        assert {row.outcome for row in rows}==({'equivalent'} if operator=='compare' else {'undecided'})
        if operator=='not':assert all(row.uncertainty for row in rows)


def test_independent_source_binding_disagreement_persists_one_compact_group(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path):
    from corpus_structure.semantic.query import read_session,QuerySpec
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',formulas=('x',),two_reports=True)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with read_session(semantic_reader_engine,'evaluated') as session:
        cls=session.class_handle('Person');prop=session.property_handle(cls,'name')
        result=session.query(QuerySpec(cls,prop))
        assert len(result.rows)==2 and len({row.source for row in result.rows})==2
        explanation=session.explain(result.rows[0].fact_id)
        assert len(explanation.alternatives)==1
        group=explanation.alternatives[0]
        assert set(group.member_fact_ids)=={row.fact_id for row in result.rows}
        assert __import__('json').loads(group.reason)['generated'][0]['kind']=='qualifier_binding_disagreement'
        assert {row.outcome for row in explanation.assessments if row.operation_id=='consolidate.status'}=={'ambiguous'}
        assert not session.query(QuerySpec(cls,prop,'accepted')).rows
    with semantic_reader_engine.connect() as conn:
        assert len(conn.execute(select(table('data.alternative_member'))).all())==2


@pytest.mark.parametrize('duplicate',[False,True])
def test_authored_alternatives_retain_source_reason_without_duplicate_fact_groups(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path,duplicate):
    from corpus_structure.semantic.query import read_session,QuerySpec
    formulas=('x','x') if duplicate else ('x+1','x+2')
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',formulas=formulas,authored_alternative=True)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with read_session(semantic_reader_engine,'evaluated') as session:
        cls=session.class_handle('Person');prop=session.property_handle(cls,'name')
        rows=session.query(QuerySpec(cls,prop)).rows
        explanation=session.explain(rows[0].fact_id)
        assert len(explanation.alternatives)==(0 if duplicate else 1)
        if not duplicate:
            source=__import__('json').loads(explanation.alternatives[0].reason)['sources'][0]
            assert source=={'observation_key':rows[0].source,'local_id':'choice','faithful':True,'reason':'source explicitly contrasts these possibilities'}
            assert not session.query(QuerySpec(cls,prop,'accepted')).rows
        else:assert len(session.query(QuerySpec(cls,prop,'accepted')).rows)==1


def test_primitive_alias_rule_view_keeps_source_value_kind(semantic_db_engine,semantic_writer_engine,tmp_path):
    rules=b'rules:\n- id: count.literal\n  applies_to: ex:name\n  severity: error\n  at: [finalize]\n  check: "claim.value&.t == \'number\' and claim.value&.v == \'4\'"\n'
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',integer_alias=True,rules=rules)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        statuses=conn.execute(select(table('data.assessment').c.outcome).where(table('data.assessment').c.operation_id=='consolidate.status')).scalars().all()
        assert statuses==['accepted']


@pytest.mark.parametrize(('operand','source_override'),[('fallback',False),('fallback',True),('constant',False)])
def test_recorded_math_fallbacks_constants_and_source_override_drive_science(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path,operand,source_override):
    from corpus_structure.semantic.query import read_session,QuerySpec
    from corpus_structure.core.evidence import MacroDef
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',formulas=((r'\A' if operand=='fallback' else r'e^{\ln x}'),'x'),math={'macros':{r'\A':'100' if source_override else 'x','unused':'z'},'constants':['e',r'\pi']},source_macros={r'\A':MacroDef(body='x')} if source_override else None)
    consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with read_session(semantic_reader_engine,'evaluated') as session:
        cls=session.class_handle('Person');prop=session.property_handle(cls,'name')
        rows=session.query(QuerySpec(cls,prop)).rows
        if operand=='fallback':
            used=next(row.object for row in rows if row.object.expression.startswith(r'\A'))
            assert used.macro_context[r'\A'].body=='x' and 'unused' not in used.macro_context
        assert len(session.query(QuerySpec(cls,prop,'accepted')).rows)==1
        assert {a.outcome for a in session.explain(rows[0].fact_id).assessments if a.operation_id=='scientific.value_equivalence'}=={'equivalent'}


def test_conflicting_recorded_constant_profiles_refuse_cut(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,cut=fixture(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html',formulas=('x',),two_reports=True,math={'constants':['e']},second_math={'constants':[]})
    with pytest.raises(DomainOperationRefused,match='incompatible recorded mathematical constant profiles'):
        consolidate_cut(semantic_writer_engine,cut,'evaluated')
    with semantic_writer_engine.connect() as conn:
        assert not conn.execute(select(table('data.realization')).where(table('data.realization').c.realization_id=='evaluated')).first()
