"""Named serving consumers read actual admitted source/result bindings through real roles."""
import base64
import json
from pathlib import Path

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticAgentSession,build_semantic_server
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.analytics import load_packet,SPINE
from corpus_structure.semantic.query import read_session
from corpus_structure.serve.journey import serve_query,StaleToken
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import build_registry
from corpus_structure.serve.explain import explain
from corpus_structure.serve.export import export_packet
from .test_agent_resubmission import source_task,lease_and_read


def completed(admin,writer,tmp_path):
    prepared,run,task,locator=source_task(admin,writer,tmp_path/'source.html',composed=True)
    async def submit():
        async with Client(build_semantic_server(SemanticAgentSession(writer,run))) as client:
            unit=await lease_and_read(client,run,task)
            claims=[{'id':item,'subject':'person2' if name=='Bob' else 'person','predicate':'https://example.org/name','object':{'kind':'text','text':name},'qualification':{'modality':'asserted','polarity':True},'establishment':'stated','evidence':[{'sentence':unit['sentences'][0]['id'],'quote':'Alice is here.','role':'primary'}]} for item,name in [('name1','Alice'),('name2','Alice'),('name3','Bob')]]
            result=await client.call_tool('propose_claims',{'task_id':task,'batch':{'unit_ref':locator,'entities':[{'id':'person','class_iri':'https://example.org/Person'},{'id':'person2','class_iri':'https://example.org/Person'}],'claims':claims}})
            assert result.structured_content['submission_disposition']=='completed_accepted'
    anyio.run(submit)
    finalize_bound_run(writer,run,'served-result')
    return prepared,run,task,locator


def test_named_semantic_pages_explanations_and_source_search(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path):
    prepared,run,task,locator=completed(semantic_db_engine,semantic_writer_engine,tmp_path)
    registry=build_registry(GENERIC)
    with semantic_reader_engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn,conn.begin():
        conn.exec_driver_sql('SET TRANSACTION READ ONLY')
        first=serve_query(conn,registry,'claims',{'predicate':'https://example.org/name'},run=run,max_rows=1)
        assert first.binding.release_id==prepared.release_id
        assert len(first.rows)==1 and first.next_page_token
        second=serve_query(conn,registry,'claims',{'predicate':'https://example.org/name'},run=run,page_token=first.next_page_token,max_rows=1)
        assert {first.rows[0]['fact']['object'],second.rows[0]['fact']['object']}=={'Alice','Bob'}
        assert first.rows[0]['fact']['fact_id']!=second.rows[0]['fact']['fact_id']
        occurrences=serve_query(conn,registry,'claims',{'predicate':'https://example.org/name'},run=run,projection='occurrence')
        assert sorted(row['fact']['object'] for row in occurrences.rows)==['Alice','Alice','Bob']
        assert len({row['fact']['occurrence_id'] for row in occurrences.rows})==3
        explanation=explain(conn,run,'claim',first.rows[0]['fact']['fact_id'])
        assert explanation.detail.supports and explanation.detail.evidence
        assert explanation.detail.evidence[0].source.observation_key
        source=explain(conn,run,'unit',locator)
        assert any(t.included_in_cut for t in source.detail.tasks)
        assert source.detail.observations
        matches=serve_query(conn,registry,'find',{'text':'Alice'},run=run)
        assert any(row['text']=='Alice is here.' for row in matches.rows)
        token=json.loads(base64.urlsafe_b64decode(first.next_page_token))
        token['revision']+=1
        with pytest.raises(StaleToken,match='snapshot'):
            serve_query(conn,registry,'claims',{'predicate':'https://example.org/name'},run=run,page_token=base64.urlsafe_b64encode(json.dumps(token).encode()).decode())
        with pytest.raises(StaleToken,match='projection'):
            serve_query(conn,registry,'claims',{'predicate':'https://example.org/name'},run=run,page_token=first.next_page_token,projection='occurrence')


def test_full_projection_exports_and_cancel_cleanup(semantic_db_engine,semantic_writer_engine,semantic_reader_engine,tmp_path,monkeypatch):
    import pyarrow.parquet as pq
    _,run,_,_=completed(semantic_db_engine,semantic_writer_engine,tmp_path)
    uri=semantic_reader_engine.url.render_as_string(hide_password=False).replace('postgresql+psycopg:','postgresql:')
    with read_session(semantic_reader_engine,'served-result') as session:
        packet=load_packet(session,uri)
    parquet=export_packet(packet,tmp_path/'parquet')
    jsonl=export_packet(packet,tmp_path/'jsonl',format='jsonl')
    assert set(parquet['relations'])==set(jsonl['relations'])==set(SPINE)
    for name,relation in packet.relations.items():
        assert pq.read_table(tmp_path/'parquet'/f'{name}.parquet').equals(relation,check_metadata=True)
        assert len((tmp_path/'jsonl'/f'{name}.jsonl').read_text().splitlines())==relation.num_rows
    original=pq.write_table
    count=0
    def cancel(*args,**kwargs):
        nonlocal count
        count+=1
        if count==2: raise KeyboardInterrupt()
        return original(*args,**kwargs)
    monkeypatch.setattr(pq,'write_table',cancel)
    with pytest.raises(KeyboardInterrupt): export_packet(packet,tmp_path/'cancelled')
    assert not (tmp_path/'cancelled').exists()
    assert not list(tmp_path.glob('.semantic-export-*'))
