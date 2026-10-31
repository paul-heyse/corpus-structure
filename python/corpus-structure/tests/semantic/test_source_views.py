"""Real native section custody, with independent source text and invalid selections."""
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from dataclasses import asdict,replace

import pytest
from pydantic import create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.semantic.operations import OperationBinding,create_run,create_task,record_method,register_document,claim_tasks
from corpus_structure.semantic.parsing_products import ProductReference
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product,store_pdf_original,store_pdf_product
from corpus_structure.semantic.source_views import store_source_view,load_source_view,selected_source_views,store_native_source_frame
from .test_operations import setup


def test_native_source_view_is_real_unit_with_exact_context(semantic_db_engine,semantic_writer_engine,tmp_path,monkeypatch):
    from docling_core.types.doc import DoclingDocument,DocItemLabel,GroupLabel
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.ingest.pdf import PdfConversion,publication_payload
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.identity import canonical_bytes

    prepared=setup(semantic_db_engine,observations=True,composed=True)
    original=b'%PDF-1.7\nindependent source view fixture'
    recipe=b'{"recipe":"native-scope-fixture"}'
    schema=files('corpus_structure').joinpath('model/semantic/docling-validation.schema.json').read_bytes()
    doc=DoclingDocument(name='Independent view')
    section=doc.add_group(label=GroupLabel.SECTION,name='Independent')
    paragraph=doc.add_text(label=DocItemLabel.TEXT,text='Independent source.',orig='Independent source.',parent=section)
    formula=doc.add_formula(text='x+1',orig='x+1',parent=section)
    from corpus_structure.ingest.pdf_health import FormulaOutcome
    conversion=PdfConversion(sha256(original).hexdigest(),recipe,snapshot(doc),'success',(),(FormulaOutcome(formula.self_ref,'succeeded'),),(),None)
    payload=publication_payload(conversion,product_key='native',schema_digest=sha256(schema).hexdigest(),section_refs=frozenset({section.self_ref}))
    product=prepare_pdf_product(payload,original,schema,recipe)
    with semantic_writer_engine.begin() as conn:
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'z',0,b'{}'),kind='full',options={},code_commit='source-view-test')
        config=record_method(conn,SimpleNamespace(name='pdf.view-fixture',version='1',family='ingest',tier='deterministic',confidence_source=None,unit_type='document',Config=create_model('ViewFixture')), 'default',{},'view-fixture')
        path=tmp_path/'source.pdf';path.write_bytes(original)
        document=register_document(conn,project_id='p',source_uri='file:source-view-fixture',original_path=str(path),original=original,mime='application/pdf')
        task=create_task(conn,run_id=run,config_id=config,stage='ingest',unit_type='document',unit_id=document,unit_key='view-source',input_hash=sha256(original).hexdigest())
        claim=claim_tasks(conn,run_id=run,config_id=config,holder='view-fixture')[0]
        store_pdf_original(conn,task_id=task,attempt=claim.attempt,holder='view-fixture',original=original,recipe_bytes=recipe)
    with semantic_writer_engine.begin() as conn:
        store_pdf_product(conn,task_id=task,attempt=claim.attempt,holder='view-fixture',product=product)
        draft=SourceViewDraft('view-independent',document,ProductReference(task,'native',product.digest),section.self_ref,'direct','Independent source.\nx+1',
            ({'item_ref':paragraph.self_ref,'start':0,'end':19,'kind':'native_text','source_field':'text'},{'start':19,'end':20,'kind':'synthetic_separator'},{'item_ref':formula.self_ref,'start':20,'end':23,'kind':'native_text','source_field':'text'}),
            (section.self_ref,paragraph.self_ref,formula.self_ref),(),payload['health'],b'{"recipe":"section-view-fixture"}')
        identity=store_source_view(conn,run_id=run,task_id=task,attempt=claim.attempt,holder='view-fixture',draft=draft,position=0)
        assert selected_source_views(conn,run)[0].id==identity
        loaded=load_source_view(conn,identity)
        assert loaded.text=='Independent source.\nx+1'
        assert [i['self_ref'] for i in loaded.items]==[section.self_ref,paragraph.self_ref,formula.self_ref]
        with pytest.raises((ValueError,DBAPIError)),conn.begin_nested():
            store_source_view(conn,run_id=run,task_id=task,attempt=claim.attempt,holder='view-fixture',draft=replace(draft,key='wrong-membership',items=(paragraph.self_ref,)),position=1)
        frame=native_source_frame(loaded,[('s1',0,19)])
        packet_hash='a'*64
        agent_config=record_method(conn,SimpleNamespace(name='native.packet-fixture',version='1',family='agent',tier='agent',confidence_source=None,unit_type='source_view',Config=create_model('NativePacketFixture')),'default',{},'native-packet-fixture')
        agent_task=create_task(conn,run_id=run,config_id=agent_config,stage='agent',unit_type='source_view',unit_id=identity,unit_key=draft.key,input_hash='packet-input',packet_hash=packet_hash,agent=True)
        store_native_source_frame(conn,task_id=agent_task,packet_hash=packet_hash,frame=asdict(frame))
        assert conn.execute(text('SELECT count(*) FROM ops.native_source_frame_sentence WHERE task_id=:task'),{'task':agent_task}).scalar_one()==1
        invalid=asdict(frame);invalid['native_context']=canonical_bytes(dict(loaded.context(),items=[])).decode()
        with pytest.raises(DBAPIError),conn.begin_nested():
            store_native_source_frame(conn,task_id=agent_task,packet_hash=packet_hash,frame=invalid)
        assert conn.execute(text('SELECT count(*) FROM ops.rendition_build WHERE task_id=:task'),{'task':task}).scalar_one()==0

    from corpus_structure.semantic.native_requests import request_source_view
    lexical=request_source_view(semantic_writer_engine,source_run_id=run,source_view_id=identity,demand='lexical',pointer=formula.self_ref,code_commit='request-fixture')
    assert lexical.status=='source_ready'
    assert lexical.result['items'][0]['recognized_latex']=='x+1'
    assert lexical.result['items'][0]['lexical']
    from corpus_structure.methods.math import native
    def forbidden(*args,**kwargs):raise AssertionError('reused native request must not execute its kernel')
    with monkeypatch.context() as patch:
        patch.setattr(native,'native_request_analysis',forbidden)
        repeated=request_source_view(semantic_writer_engine,source_run_id=run,source_view_id=identity,demand='lexical',pointer=formula.self_ref,code_commit='request-fixture')
    assert repeated.status=='source_ready' and repeated.result==lexical.result
    calls=[]
    def timed_out(*args,**kwargs):
        calls.append(1)
        return native.NativeAnalysisPayload(source_view_id=identity,native_product=loaded.ref.native_product.values(),projection_digest=loaded.ref.projection_digest,recipe_digest=loaded.ref.recipe_digest,demand='syntax',items=({'pointer':formula.self_ref,'failure':{'category':'timeout'},'stages':{'syntax':{'work':'failed','diagnostic':'budget exhausted'}}},))
    with monkeypatch.context() as patch:
        patch.setattr(native,'native_request_analysis',timed_out)
        for _ in range(2):
            failed=request_source_view(semantic_writer_engine,source_run_id=run,source_view_id=identity,demand='syntax',pointer=formula.self_ref,seconds=.01,code_commit='request-fixture')
            assert failed.status=='failed' and failed.cut_id is None and failed.result['items'][0]['failure']['category']=='timeout'
            with semantic_writer_engine.connect() as conn:
                assert conn.execute(text('SELECT status FROM ops.task WHERE id=:task'),{'task':failed.task_id}).scalar_one()=='failed'
    assert len(calls)==2


@pytest.mark.parametrize('seconds',[float('inf'),float('-inf'),float('nan'),0,-1])
def test_native_request_budget_is_finite_and_positive(seconds):
    from corpus_structure.semantic.native_requests import NativeRequestLimits
    with pytest.raises(ValueError):NativeRequestLimits(seconds=seconds)
