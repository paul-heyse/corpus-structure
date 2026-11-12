"""Independent CUDA identity, question/option/source cardinality and native variation checks."""
import ast
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent

def decoded(reply,key):return json.loads(ast.literal_eval(reply[key]))

def compare(a,b):
 if isinstance(a,float) and isinstance(b,float):return 0,abs(a-b)
 if type(a) is not type(b):return 1,0
 if isinstance(a,dict):
  if a.keys()!=b.keys():return 1,0
  children=[compare(a[k],b[k]) for k in a]
 elif isinstance(a,list):
  if len(a)!=len(b):return 1,0
  children=[compare(x,y) for x,y in zip(a,b,strict=True)]
 else:return int(a!=b),0
 return sum(d for d,n in children),max([n for d,n in children],default=0)

def validate(request,native):
 assert list(native['native']['answers'])==list(request['questions'])
 assert json.loads(native['rendered_state'])==request['state']
 fields=[f for f in native['state_fields'] if f[2]=='/source'];assert len(fields)==1
 start,end,_=fields[0]
 assert json.loads('"'+native['rendered_state'][start:end]+'"')==request['state']['source']
 for key,question in request['questions'].items():
  answer=native['native']['answers'][key]
  assert answer['type']==question['type']
  if answer['type']=='choice':
   assert set(answer['probabilities'])==set(question['criteria'])
   assert set(answer.get('choices',()))<=set(question['criteria'])
   assert all(math.isfinite(p) and 0<=p<=1 for p in answer['probabilities'].values())


def main():
 data=json.loads((HERE/'raw/cuda.json').read_text());assert data['outcome']=='passed' and data['device']=='cuda'
 single={};comparisons=[];members=0
 for call in data['calls']:
  startup=decoded(call['reply'],'startup_content');body=decoded(call['reply'],'payload_content')
  assert startup['device'].startswith('cuda') and startup['dtype']=='torch.bfloat16' and startup['set_size']==16
  assert startup['native_threads']=={'intra_op':4,'inter_op':1}
  assert len(body['batch'])==len(call['members'])
  for ordinal,(member,request,native,projection) in enumerate(zip(call['members'],call['requests'],body['batch'],call['projected'],strict=True)):
   validate(request,native);assert native['batch_receipt']['version']==2 and native['batch_receipt']['member_ordinal']==ordinal
   for occurrence in projection['occurrences'].values():
    for extent in occurrence['extents']:
     assert extent['source_view_id']==101+member and not extent['synthetic']
     assert extent['text']==data['texts'][member][extent['start']:extent['end']]
   if len(call['members'])==1:single[member]=native['native']
   difference,numeric=compare(single[member],native['native'])
   comparisons.append(dict(members=call['members'],member=member,discrete_differences=difference,max_float_abs_difference=numeric))
   members+=1
 assert data['calls'][0]['requests'][0]['state']==data['calls'][2]['requests'][0]['state']
 assert data['calls'][0]['requests'][0]['interpretation']['assessed_scope']['pin']!=data['calls'][2]['requests'][0]['interpretation']['assessed_scope']['pin']
 mixed=decoded(data['calls'][3]['reply'],'payload_content')
 assert mixed['batch_receipt']['members'][0]!=mixed['batch_receipt']['members'][2]
 for ordinal,call in enumerate(data['coalesced_logical_jobs']):
  body=decoded(call['reply'],'payload_content');assert len(body['batch'])==1
  validate(call['request'],body['batch'][0]);assert body['batch'][0]['batch_receipt']['version']==2 and body['batch'][0]['batch_receipt']['member_ordinal']==ordinal
  for occurrence in call['occurrences'].values():
   for extent in occurrence['extents']:
    assert extent['source_view_id']==101+ordinal and not extent['synthetic']
    assert extent['text']==data['texts'][ordinal][extent['start']:extent['end']]
 literal=data['literal_call'];body=decoded(literal['reply'],'payload_content')
 for request,native in zip(literal['requests'],body['batch'],strict=True):validate(request,native)
 staged=data['staged_call']
 if 'requests' in staged:
  assert staged['requests'][0]['state']['prior_answers']=={'functions':data['calls'][0]['projected'][0]['prior']['functions']}
  validate(staged['requests'][0],decoded(staged['reply'],'payload_content')['batch'][0])
 assert data['stage_without_prior_refused'] and data['active_cancel']['owned_child_stopped']
 assert data['gpu_custody_reacquired'] and data['owned_bytes_after_close']==0
 summary=dict(outcome='passed',function_members=members,coalesced_logical_jobs=2,literal_members=2,staged_native='requests' in staged,startup=startup,comparisons=comparisons,discrete_differences=sum(c['discrete_differences'] for c in comparisons),max_float_abs_difference=max(c['max_float_abs_difference'] for c in comparisons),active_cancel=True,gpu_custody_reacquired=True)
 (HERE/'raw/summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in {'startup','comparisons'}}))

if __name__=='__main__':main()
