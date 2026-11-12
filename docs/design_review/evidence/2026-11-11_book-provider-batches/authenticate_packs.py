"""Authenticate native production-schema members and apply unchanged exact thresholds."""
import json
from pathlib import Path

from corpus_structure.methods.model_observation import installed_policy
from corpus_structure.methods.pm2_gliner_classification import ClassificationProfile, authenticated_gliner_report, classification_product
from corpus_structure.methods.m1_source import M1Config
import yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def main():
 data=json.loads((HERE/'raw/production-packs.json').read_text())
 config=yaml.safe_load((ROOT/'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['default']
 profile=ClassificationProfile(provider='gliner',device='cpu',profile=M1Config.model_validate(config).profile(),threshold=.5)
 inference=installed_policy()[0]['inference']
 results=[]
 for name,pack in data['packs'].items():
  for call in pack['calls']:
   for member,item,envelope in zip(call['members'],call['inputs'],call['reports'],strict=True):
    request=dict(pack=pack['pack'],item=item,threshold=.5,inference=inference)
    report=authenticated_gliner_report(request,envelope,profile)
    row=dict(family=name,members=call['members'],member=member,ordinal=report.member_ordinal,authenticated=True)
    if name=='character_gliner_function_v1':
     q=pack['family']['questions'][0]
     request.update(question_key=q['key'],label_keys=[o['key'] for o in q['options']],assessed_scope=dict(probe_context=item['context_id'],projection_extent=[0,len(item['text'])]),question_family=name)
     product=classification_product(request,envelope,profile)
     body=product.value
     scores=body['native_answer']['scores']
     assert list(body['selected_keys']) == [label for label in request['label_keys'] if label in scores and scores[label] >= request['threshold']]
     row['product']=body
    results.append(row)
 (HERE/'raw/production-authentication.json').write_text(json.dumps(results,indent=2,default=str))
 print('authenticated members',len(results))

if __name__=='__main__':main()
