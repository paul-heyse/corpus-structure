"""Native PDF frames enter the real proposal, consolidation and evaluator boundaries."""
from hashlib import sha256
from importlib.resources import files
import json
from types import SimpleNamespace

import anyio
from fastmcp import Client
from pydantic import create_model
import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError
import yaml

from corpus_structure.core.method import SourceViewDraft, UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.evaluate.semantic import create_reference_set, record_pass, reference_evaluate, split_documents
from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.semantic import queue_agent
from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, claim_tasks, complete_task, create_run, create_task, record_method, register_document
from corpus_structure.semantic.parsing_products import ProductReference
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product, store_pdf_original, store_pdf_product
from corpus_structure.semantic.proposals import native_source_frame, proposal_inputs
from corpus_structure.semantic.releases import activate_release, persist_release
from corpus_structure.semantic.source_views import load_source_view, store_source_view

from .test_agent_resubmission import lease_and_read


def native_source_task(admin, writer, tmp_path):
    from docling_core.types.doc import DoclingDocument, DocItemLabel, GroupLabel
    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.composed import composed_dependencies

    schema = dict(id='https://example.org/native-person', name='native_person', imports=['core'],
        prefixes={'ex':'https://example.org/'}, default_prefix='ex',
        classes={'Person':{'is_a':'Entity','attributes':{'name':{'range':'string'}}}})
    dependencies=domain_rule_inputs(ResolvedDependencies(),b'rules: []\n')
    dependencies=ResolvedDependencies((*dependencies.artifacts,SourceArtifact('operation/evaluation-split.yaml',
        b'split:\n  seed: 17\n  forced_dev: {source.pdf: independent native source}\ngolden:\n  sizes: {dev: 1, test: 1}\n')),
        dependencies.vocabularies,dependencies.ontology_sources)
    bundle=proposal_inputs(SourceBundle('domain',(SourceArtifact('core',files('corpus_structure').joinpath(
        'model/semantic/core.yaml').read_bytes()),SourceArtifact('domain',yaml.safe_dump(schema).encode()))),dependencies)
    bundle,dependencies=analytical_inputs(bundle,dependencies)
    dependencies=composed_dependencies(dependencies)
    profile=PreparationProfile(version='semantic-2')
    prepared=prepare_release(bundle,dependencies,profile)
    with admin.begin() as conn:
        persist_release(conn,bundle,dependencies,profile,prepared)
        conn.execute(insert(table('data.project')).values(project_id='native-consumer'))
        activate_release(conn,'native-consumer',prepared.release_id,expected_parent=None,expected_generation=0)
        conn.execute(insert(table('data.realization')).values(project_id='native-consumer',realization_id='native-input',release_id=prepared.release_id))
    original=b'%PDF-1.7\nindependent native custody input'
    recipe=b'{"recipe":"native-consumer-fixture"}'
    native_schema=files('corpus_structure').joinpath('model/semantic/docling-validation.schema.json').read_bytes()
    doc=DoclingDocument(name='Independent source')
    section=doc.add_group(label=GroupLabel.SECTION,name='People')
    paragraph=doc.add_text(label=DocItemLabel.TEXT,text='Alice is here.',orig='Alice is here.',parent=section)
    conversion=PdfConversion(sha256(original).hexdigest(),recipe,snapshot(doc),'success',(),(),(),None)
    payload=publication_payload(conversion,product_key='native',schema_digest=sha256(native_schema).hexdigest(),section_refs=frozenset({section.self_ref}))
    product=prepare_pdf_product(payload,original,native_schema,recipe)
    configuration={'model':'automated-native-fixture','mode':'extract','max_units':1,'packet_cap_chars':18000}
    with writer.begin() as conn:
        run=create_run(conn,project_id='native-consumer',binding=OperationBinding(prepared.release_id,'native-input',0,b'{}'),kind='full',
            options={'agent_configs':{'extract':configuration}},code_commit='native-consumer-test')
        config=record_method(conn,SimpleNamespace(name='pdf.consumer-fixture',version='1',family='ingest',tier='deterministic',confidence_source=None,
            unit_type='document',Config=create_model('NativeConsumerFixture')),'default',{},'native-consumer-fixture')
        path=tmp_path/'source.pdf';path.write_bytes(original)
        document=register_document(conn,project_id='native-consumer',source_uri='source.pdf',original_path=str(path),original=original,mime='application/pdf')
        source=create_task(conn,run_id=run,config_id=config,stage='ingest',unit_type='document',unit_id=document,unit_key='source.pdf',input_hash=sha256(original).hexdigest())
        claim=claim_tasks(conn,run_id=run,config_id=config,holder='native-fixture')[0]
        store_pdf_original(conn,task_id=source,attempt=claim.attempt,holder='native-fixture',original=original,recipe_bytes=recipe)
        store_pdf_product(conn,task_id=source,attempt=claim.attempt,holder='native-fixture',product=product)
        draft=SourceViewDraft('native-person-section',document,ProductReference(source,'native',product.digest),section.self_ref,'direct','Alice is here.',
            ({'item_ref':paragraph.self_ref,'start':0,'end':14,'kind':'native_text','source_field':'text'},),
            (section.self_ref,paragraph.self_ref),(),dict(payload['health'],formula_outcomes=[]),b'{"recipe":"native-person-section"}')
        view=store_source_view(conn,run_id=run,task_id=source,attempt=claim.attempt,holder='native-fixture',draft=draft,position=0)
        complete_task(conn,task_id=source,attempt=claim.attempt,holder='native-fixture',prepared=prepared,observations=[],outcome='empty')
        task,=queue_agent(conn,run_id=run,prepared=prepared,configuration=configuration,units=(UnitRef(TaskUnitType.SOURCE_VIEW,view,draft.key),))
    return prepared,run,task,view,draft.key


def authored(unit, sentence, prefix):
    # Independent expected authoring uses source text, never copied prediction entities/claims.
    return {'unit_ref':unit,'entities':[{'id':prefix+'_person','class_iri':'https://example.org/Person','label':'Alice'}],
        'statements':[{'id':prefix+'_statement','kind':'remark','anchor':sentence}],
        'claims':[{'id':prefix+'_name','subject':prefix+'_person','predicate':'https://example.org/name',
            'object':{'kind':'text','text':'Alice'},'qualification':{'modality':'asserted','polarity':True},'establishment':'stated','statement':prefix+'_statement','statement_role':'conclusion',
            'evidence':[{'sentence':sentence,'quote':'Alice is here.','role':'primary'}]}]}


def test_native_proposal_consolidation_and_independent_reference_journey(
        semantic_db_engine,semantic_writer_engine,semantic_evaluator_engine,tmp_path):
    prepared,run,task,view,key=native_source_task(semantic_db_engine,semantic_writer_engine,tmp_path)
    session=SemanticAgentSession(semantic_writer_engine,run)
    async def submit():
        async with Client(build_semantic_server(session)) as client:
            unit=await lease_and_read(client,run,task)
            assert unit['native_source']['source_view_id']==view
            response=await client.call_tool('propose_claims',{'task_id':task,
                'batch':authored(key,unit['native_source']['native_evidence'][0]['handle'],'prediction')})
            assert response.structured_content is not None
            assert response.structured_content['submission_disposition']=='completed_accepted'
    anyio.run(submit)
    finalize_bound_run(semantic_writer_engine,run,'native-result')
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM data.evidence_source WHERE source_view_id=:view AND native_address LIKE \'pdf:%\''),{'view':view})>0
        assert conn.scalar(text('SELECT count(*) FROM kb.rendition'))==0
        source=load_source_view(conn,view)
    frame=native_source_frame(source,[('reference_sentence',0,14)])
    expected=canonical_bytes(authored(key,'native_evidence:0','reference'))
    with semantic_evaluator_engine.begin() as conn:
        split_documents(conn,'native-consumer')
        made=create_reference_set(conn,project_id='native-consumer',source_run_id=run,label='native-independent',split='dev',size=1,forced=(key,))
        unit=made['units'][key]
        assert made['sampling']['source_frame_abi']=='native-source-view-1'
        for kind in ('A','B','C'):
            record_pass(conn,unit_id=unit,pass_kind=kind,actor='automated-independent-'+kind,authored=expected,frame=frame)
        result=reference_evaluate(conn,project_id='native-consumer',run_id=run,set_id=made['set_id'])
        assert result.result['tiers']['full']['matched']==1
        assert result.result['tiers']['full']['reference']==1
        assert result.result['tiers']['full']['prediction']==1
        assert result.reference_snapshot[0]['source_view_id']==view
        sentence=frame.sentences[0]
        valid=json.loads(sentence.locator[4:])
        for invalid in ({**valid,'pointer':'#/texts/forged'},
                        {**valid,'cell_index':999},
                        {**valid,'projection_digest':'f'*64},
                        {**valid,'product_digest':'e'*64},
                        {**valid,'source_view_id':view+100}):
            citations=[dict(start=0,end=14,quote='Alice is here.',locator='pdf:'+canonical_bytes(invalid).decode())]
            with pytest.raises(DBAPIError),conn.begin_nested():
                conn.execute(text('SELECT eval.record_native_reference_pass(:unit,\'C\',\'forged\',:authored,CAST(:citations AS jsonb))'),
                    dict(unit=unit,authored=expected,citations=json.dumps(citations)))

        noncanonical=[dict(start=0,end=14,quote='Alice is here.',locator='pdf:'+json.dumps(valid))]
        with pytest.raises(DBAPIError),conn.begin_nested():
            conn.execute(text("SELECT eval.record_native_reference_pass(:unit,'C','noncanonical',:authored,CAST(:citations AS jsonb))"),
                dict(unit=unit,authored=expected,citations=json.dumps(noncanonical)))


def test_native_cell_evidence_alias_stays_within_its_retained_projection_piece():
    from dataclasses import replace
    from .test_proposals import prepared, batch
    from corpus_structure.semantic.proposals import locate_proposal,native_evidence_entries,ProposalSentence,native_address
    text_value='Alice is here. Bob is there.'
    source=SimpleNamespace(ref=SimpleNamespace(id=7,key='native-cell-unit',native_product=ProductReference(2,'native','a'*64),
        section_pointer='#/groups/0',membership='direct',projection_digest='b'*64,recipe_digest='c'*64),text=text_value,
        pieces=({'kind':'native_text','item_ref':'#/tables/0','cell_index':0,'source_field':'cell_text','start':0,'end':14},
                {'kind':'native_text','item_ref':'#/texts/0','source_field':'text','start':15,'end':len(text_value)}),
        items=({'self_ref':'#/tables/0','label':'table'},{'self_ref':'#/texts/0','label':'text'}),ancestors=(),health={})
    frame=native_source_frame(source,[('s1',0,len(text_value))])
    entries=native_evidence_entries(frame)
    assert entries[0]['handle']=='native_evidence:0' and entries[0]['cell_index']==0
    assert entries[0]['pointer']=='#/tables/0' and entries[0]['text']=='Alice is here.'
    raw=batch();raw['unit_ref']=frame.unit_ref;raw['statements'][0]['anchor']='native_evidence:0'
    citation=raw['claims'][0]['evidence'][0];citation['sentence']='native_evidence:0'
    located=locate_proposal(prepared(),raw,frame)
    assert located.clean
    evidence=located.stored.model_dump(mode='json')['claims'][0]['evidence'][0]
    assert (evidence['start'],evidence['end'],evidence['locator'])==(0,14,entries[0]['locator'])
    citation['sentence']='native_evidence:1'
    refused=locate_proposal(prepared(),raw,frame)
    assert not refused.clean  # The quote exists elsewhere; the named cell/piece cannot relocate.
    wrong=ProposalSentence('native_evidence:0',native_address(frame,start=15,end=len(text_value)),15,len(text_value))
    with pytest.raises(ValueError,match='retained projection piece'):
        replace(frame,sentences=tuple(wrong if row.id==wrong.id else row for row in frame.sentences))
