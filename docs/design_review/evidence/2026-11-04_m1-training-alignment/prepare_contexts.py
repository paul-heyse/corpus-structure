"""Reconstruct run-14 input contexts without reading model predictions."""
import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from sqlalchemy import text
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.methods.m1_source import M1Config, configured_packs
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python

HERE=Path(__file__).resolve().parent
RELEASE='release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd'
with open_runtime_engine(Settings(), 'm1-training-alignment-source', purpose='read') as engine, engine.connect() as conn:
    prepared=open_release(conn, RELEASE)
    reader=BoundReader(conn,14,prepared,13,analysis=False)
    contexts=[]; receipts=[]; live_contexts={}; live_packs={}
    for source_id,task_id in ((22,36),(23,37)):
        row=conn.execute(text('SELECT t.input_hash,c.params,c.config_hash FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id WHERE t.id=:task AND t.run_id=14 AND t.unit_id=:source'),dict(task=task_id,source=source_id)).mappings().one()
        cfg=M1Config.model_validate(row['params'])
        profile=AnnotationProfile(cfg.sentences)
        view=reader.source_view(source_id)
        annotations,errors,result=consume_annotations(reader,view,profile)
        product=prepare_source(view,profile=profile,max_chars=cfg.max_context_chars,max_pieces=cfg.max_context_pieces,max_annotation_chars=cfg.max_annotation_chars,reader=reader,persisted_annotations=annotations,annotation_errors=errors)
        packs=configured_packs(prepared,cfg)
        # SQL returns only allowed verification fields. Raw groups never reach Python.
        reports=[]
        outer=conn.execute(text("""SELECT r.ordinality, f->>'name' AS name,f->'value' AS value
          FROM ops.task_result tr CROSS JOIN LATERAL jsonb_array_elements(tr.body->'parse_detail'->'fields') d
          CROSS JOIN LATERAL jsonb_array_elements(d->'value'->'items') WITH ORDINALITY r(value,ordinality)
          CROSS JOIN LATERAL jsonb_array_elements(r.value->'fields') f
          WHERE tr.task_id=:task AND d->>'name'='reports' AND f->>'name' IN ('context','family','outcome')"""),dict(task=task_id)).mappings().all()
        by_report={}
        for r in outer: by_report.setdefault(r['ordinality'],{})[r['name']]=source_python(r['value'])
        inner=conn.execute(text("""SELECT r.ordinality, f->>'name' AS name,f->'value' AS value
          FROM ops.task_result tr CROSS JOIN LATERAL jsonb_array_elements(tr.body->'parse_detail'->'fields') d
          CROSS JOIN LATERAL jsonb_array_elements(d->'value'->'items') WITH ORDINALITY r(value,ordinality)
          CROSS JOIN LATERAL jsonb_array_elements(r.value->'fields') rf
          CROSS JOIN LATERAL jsonb_array_elements(rf->'value'->'fields') f
          WHERE tr.task_id=:task AND d->>'name'='reports' AND rf->>'name'='report'
          AND f->>'name' IN ('context_id','context_digest','pack','preparation','effective_profile_ref')"""),dict(task=task_id)).mappings().all()
        for r in inner: by_report.setdefault(r['ordinality'],{})[r['name']]=source_python(r['value'])
        reports=[by_report[k] for k in sorted(by_report)]
        profile_row=conn.execute(text("SELECT d->'value' FROM ops.task_result tr CROSS JOIN LATERAL jsonb_array_elements(tr.body->'parse_detail'->'fields') d WHERE task_id=:task AND d->>'name'='effective_profiles'"),dict(task=task_id)).scalar_one()
        profiles=source_python(profile_row)
        receipt=dict(source_view_id=source_id,task_id=task_id,input_hash=row['input_hash'],config_hash=row['config_hash'],params=row['params'],annotation_input_hash=result['input_hash'],annotation_dependency=sha256(canonical_bytes(result)).hexdigest(),selections=len(product.selections),regions=[asdict(x) for x in product.regions],annotation_errors=errors,reports=[dict(x) for x in reports],effective_profiles=profiles)
        for index,selection in enumerate(product.selections):
            try:
                context=selection.context(product.source,max_chars=cfg.max_context_chars,max_pieces=cfg.max_context_pieces,related=product.related,preparation=product.preparation)
            except ValueError as error:
                contexts.append(dict(source_view_id=source_id,index=index,selection=asdict(selection),error=str(error))); continue
            live_contexts[source_id,index]=context
            live_packs[source_id,index]=packs
            contexts.append(dict(source_view_id=source_id,index=index,selection=asdict(selection),context_id=context.dependency_digest,text=context.text,text_sha256=sha256(context.text.encode()).hexdigest(),intervals=[asdict(x) for x in context.intervals],packs={f:dict(declaration=json.loads(packs[f].declaration_json),fingerprint=packs[f].fingerprint) for f in selection.families}))
        receipts.append(receipt)
    (HERE/'source-contexts.jsonl').write_text(''.join(canonical_bytes(x).decode()+'\n' for x in contexts))
    (HERE/'source-reconstruction.json').write_bytes(canonical_bytes(receipts))
    print(json.dumps(dict(contexts=len(contexts),sources=[dict(source_view_id=x['source_view_id'],selections=x['selections'],reports=len(x['reports'])) for x in receipts])))
