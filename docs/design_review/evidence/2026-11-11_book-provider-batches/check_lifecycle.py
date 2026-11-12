"""Independent expected correlation/ordinal and bounded lifetime checks on native replies."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def main():
 summary=[]
 for provider,scenarios in [('hanlp',('stale','cancel','crash')),('gliner',('stale','cancel','crash','invalid','words'))]:
  for scenario in scenarios:
   d=json.loads((HERE/'raw'/f'lifecycle-{provider}-{scenario}.json').read_text())
   assert d['outcome']=='passed' and d['budget_after_close']==0 and d['owned_child_stopped']
   if scenario=='stale':
    stale,survivor=d['responses'];assert stale['stopped'] and not survivor['stopped']
    assert survivor['correlation']=='1' and survivor['error_type'] is None
    if provider=='hanlp':
     assert survivor['payload']['native']['tok']==[['The','mean','is','five','.']]
     assert survivor['payload']['batch_receipt']['member_ordinals']==[1]
     assert survivor['payload']['preparation'][0]['batch_receipt']['member_ordinal']==1
    else:
     (report,)=survivor['reports'];assert report['context_id']=='source-1' and report['member_ordinal']==1
     assert len(json.loads(report['batch_receipt_json'])['members'])==2
   elif scenario in ('invalid','words'):
    invalid,survivor=d['responses'];assert invalid['correlation']=='0' and invalid['error_type']=='GlinerRefused'
    assert survivor['correlation']=='1' and survivor['error_type'] is None
    (report,)=survivor['reports'];assert report['context_id']=='source-1' and report['member_ordinal']==0
    assert len(json.loads(report['batch_receipt_json'])['members'])==1
   else:assert d['responses'][0]['error_type']
   summary.append(dict(provider=provider,scenario=scenario,outcome='passed',budget_after_close=0,owned_child_stopped=True))
 (HERE/'raw/lifecycle-summary.json').write_text(json.dumps(summary,indent=2))
 print('native lifecycle scenarios passed',len(summary))

if __name__=='__main__':main()
