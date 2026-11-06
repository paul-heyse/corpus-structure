import json,hashlib
from pathlib import Path
ROOT=Path(__file__).parent
SRC=ROOT.parent.parent/'source-packets'

def write_packet(first,entries,gaps=()):
 p=SRC/f'grinstead-snell-physical{first}-{first+9}.json'
 raw=p.read_bytes(); d=json.loads(raw); cases=[]; covered=set()
 for number,e in enumerate(entries,1):
  quote,facet,distinction,*rest=e
  opts=rest[0] if rest else {}
  matches=[(v,v['passage']['text'].find(quote)) for v in d['views'] if quote in v['passage']['text']]
  assert len(matches)==1,(first,quote,len(matches))
  v,start=matches[0];end=start+len(quote);text=v['passage']['text'];assert text[start:end]==quote
  pages=set()
  for piece in v['native_context']['pieces']:
   if piece['start']<end and piece['end']>start:
    item=next((i for i in v['native_context']['items'] if i.get('self_ref')==piece.get('item_ref')),None)
    if item:
     pages.update(first+pr['page_no']-1 for pr in item.get('prov',[]))
  if not pages: pages=set(d['parent_physical_pages'])
  covered.update(pages)
  relation=opts.get('relation')
  cases.append({'id':f'A-{first}-{number:03d}','parent_physical_pages':sorted(pages),'source_ref':v['passage']['source_ref'],'evidence_spans':[{'source_view_id':v['source']['source_view_id'],'start':start,'end':end,'text':quote,'role':opts.get('role','support'),'coordinate_space':'projection'}],'facet':facet,'semantic_distinction':distinction,'proposed_relation':relation,'source_state':opts.get('source_state','stated'),'judgment':opts.get('judgment','supported'),'reason':opts.get('reason','This exact source passage states the distinction; this is a source attribution, not a claim of scientific truth.'),'missing_facets':opts.get('missing_facets',[])})
 coverage=[]
 for v in d['views']:
  pages=sorted({first+pr['page_no']-1 for item in v['native_context']['items'] for pr in item.get('prov',[])})
  coverage.append({'source_view_id':v['source']['source_view_id'],'region':{'coordinate_space':'projection','start':0,'end':len(v['passage']['text'])},'parent_physical_pages':pages,'inspection':'full projection read; selective semantic cases; figures not visually inspected'})
 result={'protocol':'gs120-source-author-1','author':'A','input_sha256':hashlib.sha256(raw).hexdigest(),'source_packet':str(p),'parent_physical_pages':d['parent_physical_pages'],'coverage':coverage,'cases':cases,'remaining_gaps':list(gaps)+['Projection-only inspection: formulas, figures and flattened tables can retain recognition/association damage; no visual source adjudication was performed. Inventory is substantial and selective, not an exhaustive census.']}
 out=ROOT/f'physical{first}-{first+9}.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(out,len(cases),sorted(covered))
