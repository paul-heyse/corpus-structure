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


def test_native_source_view_is_real_unit_with_exact_context(semantic_db_engine,semantic_writer_engine,tmp_path):
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
    conversion=PdfConversion(sha256(original).hexdigest(),recipe,snapshot(doc),'success',(),(),(),None)
    payload=publication_payload(conversion,product_key='native',schema_digest=sha256(schema).hexdigest(),section_refs=frozenset({section.self_ref}))
    product=prepare_pdf_product(payload,original,schema,recipe)
    with semantic_writer_engine.begin() as conn:
        run=create_run(conn,project_id='p',binding=OperationBinding(prepared.release_id,'z',0,b'{}'),kind='full',options={},code_commit='source-view-test')
        config=record_method(conn,SimpleNamespace(name='pdf.view-fixture',version='1',family='ingest',tier='deterministic',confidence_source=None,unit_type='document',Config=create_model('ViewFixture')), 'default',{},'view-fixture')
        path=tmp_path/'source.pdf';path.write_bytes(original)
        document=register_document(conn,project_id='p',source_uri='file:source-view-fixture',original_path=str(path),original=original)
        task=create_task(conn,run_id=run,config_id=config,stage='ingest',unit_type='document',unit_id=document,unit_key='view-source',input_hash=sha256(original).hexdigest())
        claim=claim_tasks(conn,run_id=run,config_id=config,holder='view-fixture')[0]
        store_pdf_original(conn,task_id=task,attempt=claim.attempt,holder='view-fixture',original=original,recipe_bytes=recipe)
    with semantic_writer_engine.begin() as conn:
        store_pdf_product(conn,task_id=task,attempt=claim.attempt,holder='view-fixture',product=product)
        draft=SourceViewDraft('view-independent',document,ProductReference(task,'native',product.digest),section.self_ref,'direct','Independent source.',
            ({'item_ref':paragraph.self_ref,'start':0,'end':19,'kind':'native_text','source_field':'text'},),
            (section.self_ref,paragraph.self_ref),(),dict(payload['health'],formula_outcomes=[]),b'{"recipe":"section-view-fixture"}')
        identity=store_source_view(conn,run_id=run,task_id=task,attempt=claim.attempt,holder='view-fixture',draft=draft,position=0)
        assert selected_source_views(conn,run)[0].id==identity
        loaded=load_source_view(conn,identity)
        assert loaded.text=='Independent source.'
        assert [i['self_ref'] for i in loaded.items]==[section.self_ref,paragraph.self_ref]
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
