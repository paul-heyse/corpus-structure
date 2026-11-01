import gzip,json,time
from pathlib import Path
from corpus_structure.ingest.pdf_retained_stream import iter_retained_pdf_values,derive_retained_native_projection
p=Path('docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/integration/raw/book-task86-prepared.json.gz')
expected='c8f19ca1703206e9007b416eecb7c0d286de57d7ce82b006a605335efe7da524'
t=time.perf_counter();document=None
with gzip.open(p,'rb') as source:
 for family,value in iter_retained_pdf_values(source,expected_sha256=expected):
  if family=='document':document=value
assert document is not None
projected,count=derive_retained_native_projection(document)
assert count>=107
assert len(projected['pages'])==1589 and len(projected['tables'])==107
assert all('grid' not in t['data'] for t in projected['tables'])
assert all('grid' in t['data'] for t in document['tables'])
print(json.dumps({'outcome':'passed','scope':'actual retained exact-envelope computed projection derivation only; no DBwrites/inference','profile':'retained-docling-computed-grid-v1','projected_grid_count':count,'native_pages':len(projected['pages']),'native_tables':len(projected['tables']),'seconds':time.perf_counter()-t},indent=2))
