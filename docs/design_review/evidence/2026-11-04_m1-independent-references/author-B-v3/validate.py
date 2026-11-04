"""Pure frozen-input validation. Never reads production predictions or references."""
from pathlib import Path
import json,sys,traceback
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import author
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.evaluate.record_references import decode_authored,decode_frame
_,_,_,prepared=prepare_pack(Path('domains/statistics'))
assert prepared.release_id=='release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd',prepared.release_id
print('release',prepared.release_id)
failed=0
for n in range(1,12):
 packet=author.UNITS[n]
 frame=decode_frame(packet['source_frame'])
 views=packet['source_frame']['source_views']
 coords=[]
 for v in views:
  pin=frame.pin
  pointers=set()
  for p in v['projection']['pieces']:
   if p.get('kind')=='synthetic_separator':continue
   ptr=p['item_ref']
   if p.get('source_field')=='cell_text':ptr+=f"/data/table_cells/{p['cell_index']}"
   pointers.add(ptr)
  for ptr in sorted(pointers):coords.append(dict(pin=pin,space='selected_projection',pointer=ptr,text=v['projection']['text']))
 path=ROOT/f'unit-{n}.json'
 try:
  payload=decode_authored(prepared,path.read_bytes(),frame,coordinate_texts=coords)
  print('passed',path.name,len(payload['records']))
 except Exception:
  failed+=1;print('failed',path.name);traceback.print_exc()
if failed:raise SystemExit(1)
print('passed all11units frozen-contract-source-coordinates')
