"""Independent source projections and exact production option checks."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def main():
 data=json.loads((HERE/'raw/nested-production.json').read_text())
 count=0;occurrences=0
 for name,pack in data['packs'].items():
  expected='nested' if name=='character_gliner_cues_v1' else 'flat'
  assert pack['overlap_policy']==expected
  for call in pack['calls']:
   for member,request,report,projected in zip(call['members'],call['requests'],call['reports'],call['projected'],strict=True):
    receipt=json.loads(report['batch_receipt_json'])
    assert receipt['header']['overlap']==expected
    assert receipt['header']['threshold']=='0.5'
    assert request['item']['context_id']==report['context_id']
    if expected=='nested':
     assert request['item']['operation'].startswith('text.model_characterization/2:')
     for occurrence in projected['occurrences'].values():
      for extent in occurrence['extents']:
       assert extent['source_view_id']==11+member
       assert extent['native_pointer']=='#/texts/0' and not extent['synthetic']
       assert extent['text']==data['texts'][member][extent['start']:extent['end']]
       occurrences+=1
    else:
     assert request['item']['operation'].startswith('extract.pm2_gliner_classification/2:')
     assert projected['assessed_scope']==request['assessed_scope']
     scores=projected['native_answer']['scores']
     assert list(projected['selected_keys'])==[key for key in request['label_keys'] if key in scores and scores[key]>=request['threshold']]
    count+=1
  if expected=='nested':
   first=pack['calls'][0]['requests'][0]['item'];third=pack['calls'][2]['requests'][0]['item']
   assert first['text']==third['text'] and first['context_id']!=third['context_id']
 assert count==26
 summary=json.loads((HERE/'raw/nested-production-summary.json').read_text())
 results={name:dict(overlap_policy=pack['overlap_policy'],discrete_mismatches=sum(len(c['discrete_mismatches']) for c in pack['comparisons']),max_float_abs_difference=max(c['max_float_abs_difference'] for c in pack['comparisons'])) for name,pack in summary.items()}
 output=dict(outcome='passed',projected_members=count,independently_checked_occurrence_extents=occurrences,results=results)
 (HERE/'raw/nested-projection-check.json').write_text(json.dumps(output,indent=2))
 print(json.dumps(output))

if __name__=='__main__':main()
