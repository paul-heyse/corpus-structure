"""Independent section/order and submitted-coordinate controls; no model inference."""
import json,pathlib,hashlib
from importlib.resources import files
from docling_core.types.doc import DoclingDocument,GroupLabel,DocItemLabel,ProvenanceItem,BoundingBox,Size
from corpus_structure.ingest.pdf import PdfConversion,publication_payload
from corpus_structure.ingest.pdf_hierarchy import snapshot,project_section
from corpus_structure.ingest.pdf_reconciliation import select_pdf_integration,map_pdf_observation

def main():
 out=pathlib.Path('/home/paul/corpus-structure/docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/runtime')
 actual=next((out/'pages').glob('**/page-00085/attempt-00001/observation-000.json'))
 original=b'%PDF-1.7\n%%EOF\n';recipe=b'{}'
 schema=files('corpus_structure').joinpath('model/semantic/docling-validation.schema.json').read_bytes()
 def item(doc,text,y,parent):
  return doc.add_text(label=DocItemLabel.TEXT,text=text,parent=parent,prov=ProvenanceItem(page_no=1,bbox=BoundingBox(l=10,t=y,r=100,b=y+10,coord_origin='TOPLEFT'),charspan=(0,len(text))))
 def native(with_list=False):
  d=DoclingDocument(name='Independent order control');d.add_page(page_no=1,size=Size(width=200,height=300))
  s=d.add_group(label=GroupLabel.SECTION,name='1 Section')
  if with_list:
   l=d.add_list_group(parent=s);d.add_list_item(text='one',parent=l,prov=ProvenanceItem(page_no=1,bbox=BoundingBox(l=10,t=10,r=100,b=20,coord_origin='TOPLEFT'),charspan=(0,3)))
  else:item(d,'one',10,s)
  item(d,'three',80,s)
  return publication_payload(PdfConversion(hashlib.sha256(original).hexdigest(),recipe,snapshot(d),'success',(),(),(),None),product_key='native',schema_digest=hashlib.sha256(schema).hexdigest(),section_refs=frozenset({s.self_ref})),s.self_ref
 def observation(raw):
  o=json.loads(actual.read_bytes());o['artifact_digest']=hashlib.sha256(original).hexdigest();o['recipe_digest']=hashlib.sha256(recipe).hexdigest()
  o['observation']['raw_response_digest']=hashlib.sha256(raw).hexdigest();o['observation']['image'].update(page_no=1,width=200,height=300)
  o['observation']['image']['transform'].update(page_width=200.,page_height=300.,page_rotation=0,crop_left=0.,crop_top=0.,crop_right=200.,crop_bottom=300.,affine=[1.,0.,0.,1.,0.,0.])
  o['occurrences']=[{'occurrence_id':'block-0','kind':'text','address_space':'recognized_text','precision':'block','text':'middle','page_no':1}]
  return o
 raw=b'<x_0.05><y_0.14>middle<x_0.5><y_0.17><class_Text>'
 results={}
 for flag in (False,True):
  n,s=native(flag);o=observation(raw)
  p=select_pdf_integration(n,{'task_id':1,'product_key':'native','content_digest':'0'*64},[({'task_id':2,'product_key':'a','content_digest':'1'*64},o,raw)],original,recipe,schema)
  d=DoclingDocument.model_validate(p.values()['content']['document'])
  projected=project_section(d,snapshot(d).digest,s,'descendant',section_refs=frozenset({s})).text
  results['list' if flag else 'paragraph']={'section_projection':projected,'passed':projected=='one\nmiddle\nthree'}
 raw=b'<x_0.1><y_0.1>edge<x_1.2><y_0.2><class_Text>'
 m=map_pdf_observation(observation(raw),raw);b=m.document.texts[0].prov[0].bbox
 results['overshoot']={'bbox':b.model_dump(mode='json'),'dispositions':list(m.dispositions),'passed':(b.l,b.t,b.r,b.b)==(20,30,200,60)}
 (out/'review-kernel-rerun.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
 assert all(r['passed'] for r in results.values()),results
if __name__=='__main__':main()
