"""Independent reference grades and immutable pass C snapshots on a real native store."""
import copy
import json
import anyio
import pytest
from fastmcp import Client
from sqlalchemy import create_engine,select,text
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import DBAPIError
from corpus_structure.intervene.semantic_server import SemanticAgentSession,build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalFrame,ProposalSentence
from corpus_structure.evaluate.semantic import create_reference_set,record_pass,reference_evaluate,split_documents,agreement,ensure_items,relocate_frame
from .test_agent_resubmission import source_task,lease_and_read

def test_independent_reference_grade_retains_exact_pass_and_qualification(semantic_db_engine,semantic_writer_engine,tmp_path):
    prepared,run,task,locator=source_task(semantic_db_engine,semantic_writer_engine,tmp_path/'source.html')
    source_session=SemanticAgentSession(semantic_writer_engine,run)
    async def source():
        async with Client(build_semantic_server(source_session)) as client:
            unit=await lease_and_read(client,run,task)
            response=await client.call_tool('propose_claims',{'task_id':task,'batch':{
                'unit_ref':locator,'entities':[{'id':'prediction_person','class_iri':'https://example.org/Person','label':'Alice'}],
                'claims':[{'id':'prediction_name','subject':'prediction_person','predicate':'https://example.org/name','object':{'kind':'text','text':'Alice'},'qualification':{'modality':'asserted','polarity':True},'establishment':'stated','evidence':[{'sentence':unit['sentences'][0]['id'],'quote':'Alice is here.','role':'primary'}]}]}})
            assert response.structured_content['submission_disposition']=='completed_accepted'
    anyio.run(source)
    finalize_bound_run(semantic_writer_engine,run,"reference-result")
    # Independent expected authoring: different local names, explicit qualifier and source text.
    authored={'unit_ref':locator,'entities':[{'id':'reference_person','class_iri':'https://example.org/Person','label':'Alice'}],'claims':[{'id':'reference_name','subject':'reference_person','predicate':'https://example.org/name','object':{'kind':'text','text':'Alice'},'qualification':{'modality':'asserted','polarity':True},'establishment':'stated','evidence':[{'sentence':'reference_sentence','quote':'Alice is here.','role':'primary'}]}]}
    frame=ProposalFrame(locator,'Alice is here.',(ProposalSentence('reference_sentence',locator,0,14),))
    evaluator=create_engine(semantic_db_engine.url.set(username='corpus_sem_evaluator'),poolclass=NullPool)
    try:
        with evaluator.begin() as conn:
            split_documents(conn,'resubmit')
            made=create_reference_set(conn,project_id='resubmit',source_run_id=run,label='independent',split='dev')
            uid=next(iter(made['units'].values()))
            raw=('  '+json.dumps(authored)+'\n').encode()
            a=record_pass(conn,unit_id=uid,pass_kind='A',actor='automated-reference-A',authored=raw,frame=frame)
            b=record_pass(conn,unit_id=uid,pass_kind='B',actor='automated-reference-B',authored=json.dumps(authored).encode(),frame=frame)
            assert agreement(conn,uid)['a_to_b']['tiers']['full']['f1']==1
            c=record_pass(conn,unit_id=uid,pass_kind='C',actor='automated-adjudicator',authored=raw,frame=frame)
            stored=ensure_items(conn,c)
            assert stored.authored==raw
            report=reference_evaluate(conn,project_id='resubmit',run_id=run,set_id=made['set_id'])
            for tier in ('core','full','evidence'):
                assert report.result['tiers'][tier]=={'reference':1,'prediction':1,'matched':1,'precision':1.,'recall':1.,'f1':1.}
            assert report.reference_snapshot[0]['pass_id']==c
            first_report=report.id
        # A changed adjudication creates a new grade while the old snapshot stays immutable.
        with evaluator.begin() as conn:
            other=copy.deepcopy(authored);other['claims'][0]['qualification']['polarity']=False
            new_c=record_pass(conn,unit_id=uid,pass_kind='C',actor='automated-adjudicator',authored=json.dumps(other).encode(),frame=frame)
            changed=reference_evaluate(conn,project_id='resubmit',run_id=run,set_id=made['set_id'])
            assert changed.result['tiers']['core']['matched']==1
            assert changed.result['tiers']['full']['matched']==0
            old=conn.execute(select(table('eval.reference_evaluation')).where(table('eval.reference_evaluation').c.id==first_report)).mappings().one()
            assert old['reference_snapshot'][0]['pass_id']==c
            assert changed.reference_snapshot[0]['pass_id']==new_c
            # Native caller cannot forge a grade against an earlier, unselected C snapshot.
            with pytest.raises(DBAPIError,match='incomplete or stale'):
                with conn.begin_nested():
                    conn.execute(text("SELECT eval.record_reference_evaluation(:p,:r,:s,CAST(:snap AS jsonb),'{}'::jsonb)"),{'p':'resubmit','r':run,'s':made['set_id'],'snap':json.dumps(report.reference_snapshot)})
        with semantic_writer_engine.connect() as conn:
            with pytest.raises(DBAPIError):conn.execute(select(table('eval.reference_pass')))
    finally:evaluator.dispose()
