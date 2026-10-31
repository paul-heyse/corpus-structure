"""Retained run4 source discovery/recovery only; no native model inference or publication."""
from pathlib import Path
import json
import argparse
import copy
from hashlib import sha256
from importlib.resources import files
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product
from corpus_structure.semantic.pdf_ocr_contracts import validate_pdf_inline_reports
import time
from sqlalchemy import create_engine,text
from docling_core.types.doc import DoclingDocument
from corpus_structure.ingest.pdf_candidates import CandidatePage,InlineCandidate,rediscover_candidates
from corpus_structure.ingest.pdf_enrichment import positioned_inline_candidates

HERE=Path(__file__).resolve().parent
root=HERE.parents[3]
parser=argparse.ArgumentParser()
parser.add_argument('--admit',action='store_true')
args=parser.parse_args()
output=HERE/('raw/inline-discovery-run4-qualified-final.json' if args.admit else 'raw/inline-discovery-run4-ordered.json')
if output.exists():
    raise FileExistsError('retained probe output exists; use a distinct evidence destination')
started=time.monotonic()
engine=create_engine('postgresql+psycopg://corpus_sem_writer@/corpus_pdf_20261031?host=/var/run/postgresql&port=5434')
with engine.connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    sources=c.execute(text("SELECT v.id,v.section_pointer,v.projection FROM kb.source_view v JOIN ops.run_source_view s ON s.source_view_id=v.id WHERE s.run_id=4 AND v.analysis_eligible ORDER BY s.position")).mappings().all()
    selected=frozenset(pointer for view in sources for pointer in view['projection']['items'])
    raw_payload=c.execute(text("SELECT payload FROM ops.native_document_product WHERE task_id=2 AND product_key='organized'")).scalar_one() if args.admit else None
    pages=c.execute(text("SELECT elem FROM ops.native_document_product p CROSS JOIN LATERAL jsonb_array_elements(convert_from(p.payload,'UTF8')::jsonb->'inline_candidate_pages') elem WHERE p.task_id=2 AND p.product_key='organized' AND p.content_digest='f89813cf6ce20c9dd3105838674766862211742629ec6d3a44f706064efe7cba'")).scalars().all()
engine.dispose()
document=DoclingDocument.model_validate_json((HERE/'raw/book-export.docling-json').read_bytes())
assert document.texts[513].text.startswith('Usually, the sets under discussion')
candidates={page['page_no']:CandidatePage(page['page_no'],page['has_words'],page['has_chars'],tuple(InlineCandidate.from_wire(row) for row in page['candidates']),page.get('has_vectors',False),page.get('native_text_quality','unassessed'),tuple(page.get('ocr_regions',()))) for page in pages}
initial=positioned_inline_candidates(document,tuple(candidates.values()),selected)
repair=sorted({row.page_no for row in initial.reports if row.basis=='unmatched-native-text' and not candidates[row.page_no].ocr_regions})
original=(root/'docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf').read_bytes()
for page in rediscover_candidates(original,tuple(repair),parser_threads=8):
    candidates[page.page_no]=page
final=positioned_inline_candidates(document,tuple(candidates.values()),selected)
report={'outcome':'passed','scope':'run4 selected source views; candidate discovery only, no layout/OCR/formula model inference or publication','discovery_seconds':time.monotonic()-started,'source_views':[v['id'] for v in sources],'selected_items':len(selected),'initial_aligned':len(initial.candidates),'initial_unresolved':[row.to_wire() for row in initial.reports],'backend_repair_pages':repair,'final_aligned':len(final.candidates),'final_unresolved':[dict(**row.to_wire(),candidate=candidates[row.page_no].candidates[row.candidate_index].to_wire(),native_texts={pointer:document.texts[int(pointer.rsplit('/',1)[1])].text for pointer in row.item_pointers}) for row in final.reports],'page20_contexts':[row.to_wire() for row in candidates[20].candidates]}
assert not any('#/texts/513' in row.item_pointers and candidates[row.page_no].candidates[row.candidate_index].before=='specified set' for row in final.reports)
if args.admit:
    payload=json.loads(bytes(raw_payload))
    original_digest=sha256(original).hexdigest()
    assert original_digest==payload['artifact_digest']
    recipe=canonical_bytes({'recipe_id':'native-scoped-math-v2-discovery-control','native_recipe':'docling-standard-pdf-v3','inline_alignment_policy':'native-prose-context-order-v1','operation':'backend-only; no inference','source_product_digest':'f89813cf6ce20c9dd3105838674766862211742629ec6d3a44f706064efe7cba'})
    payload.update(product_key='alignment-discovery-control',recipe_digest=sha256(recipe).hexdigest(),parent_task_id=2,parent_product_key='organized',parent_digest='f89813cf6ce20c9dd3105838674766862211742629ec6d3a44f706064efe7cba',inline_candidate_pages=[page.to_wire() for page in candidates.values()],inline_alignment_reports=[row.to_wire() for row in final.reports])
    payload.pop('runtime_report',None)
    payload['health'].update(inline_coverage='unknown',candidate_policy='native-font-token-vector-ocr-word-v3')
    payload['recognition_coverage']=[dict(section_pointer=view['section_pointer'],membership='descendants',universe='inline',outcome='partial',policy='native-font-token-vector-ocr-word-v3') for view in sources]
    schema=files('corpus_structure').joinpath('model/semantic/docling-validation.schema.json').read_bytes()
    prepared=prepare_pdf_product(payload,original,schema,recipe)
    report['admission']={'outcome':'passed','digest':prepared.digest,'contract_digest':prepared.contract_digest}
    invalid=copy.deepcopy(payload)
    unresolved={pointer for row in final.reports for pointer in row.item_pointers}
    affected=next(view for view in sources if unresolved & set(view['projection']['items']))
    next(row for row in invalid['recognition_coverage'] if row['section_pointer']==affected['section_pointer'])['outcome']='complete'
    try:
        validate_pdf_inline_reports(invalid)
    except ValueError as error:
        assert 'unresolved' in str(error).lower() and 'correspondence' in str(error).lower(),str(error)
        report['incomplete_scope_refusal']={'outcome':'passed','boundary':'shared production inline-report crossguard','diagnostic':str(error)}
    else:
        raise AssertionError('unresolved alignment was admitted as complete')
report['total_seconds']=time.monotonic()-started
with output.open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({key:value for key,value in report.items() if key not in {'initial_unresolved','final_unresolved','page20_contexts'}},indent=2))
print('initial_unresolved',len(initial.reports),'final_unresolved',len(final.reports))
