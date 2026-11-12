"""Exact producer request factories and projections: nested cues, flat functions."""
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import yaml

from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.model_observation import installed_policy
from corpus_structure.methods.pm2_gliner_classification import ClassificationProfile, classification_request, classification_product
from corpus_structure.methods.gliner import GlinerPack, GlinerInput
from corpus_structure.semantic.interpretation_questions import CHARACTERIZATION_QUESTION_INPUT, compile_question_families, declared_families
from corpus_structure.semantic.model_characterization import prepare_model_scope, gliner_cue_request, project_gliner_cues
from corpus_structure.semantic.types import SourceArtifact
from compare import difference

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'python/corpus-structure/tests'))
from semantic.test_model_characterization import scope as fixture_scope, builder as fixture_builder


def main():
 source=ROOT/'python/corpus-structure/src/corpus_structure/model/semantic/characterization-questions.yaml'
 families=declared_families(compile_question_families((SourceArtifact(CHARACTERIZATION_QUESTION_INPUT,source.read_bytes()),)))
 config=yaml.safe_load((ROOT/'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['default']
 profile=ClassificationProfile(provider='gliner',device='cpu',profile=M1Config.model_validate(config).profile(),threshold=.5)
 inference=installed_policy()[0]['inference']
 texts=['Every random variable may have a mean, but not every variable has a finite variance.','Definition: The expectation of a discrete random variable is the sum of its values weighted by their probabilities. For example, a fair die has expectation 3.5.','Every random variable may have a mean, but not every variable has a finite variance.']
 scopes=[]
 for index,text in enumerate(texts):
  original=fixture_scope(text)
  view=replace(original.view,ref=replace(original.view.ref,id=11+index,key='batch-source-'+str(index)))
  scopes.append(prepare_model_scope(view,(0,len(text)),(0,len(text))))
 groups=[[0],[1],[2],[0,1,2],[2,1,0],[0,2],[1,0]]
 output=dict(texts=texts,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),profile=asdict(profile.profile),inference=inference,packs={})
 worker=GlinerWorker(profile.profile)
 try:
  for name in ('character_gliner_cues_v1','character_gliner_function_v1'):
   family=families[name];cue=name.endswith('cues_v1');overlap='nested' if cue else 'flat';requests=[]
   for scope in scopes:
    if cue:
     pack,item=gliner_cue_request('bep-nested-production-probe',family,scope)
     request=dict(pack=asdict(pack),item=asdict(item),threshold=.5,inference=inference)
    else:
     request=classification_request('bep-nested-production-probe',family,family.questions[0].key,scope.mapping,profile,inference,characterization_family=name)
    requests.append(request)
   result=dict(family=family.model_dump(mode='json'),overlap_policy=overlap,calls=[])
   output['packs'][name]=result
   for group in groups:
    pack=GlinerPack(**requests[group[0]]['pack']);items=tuple(GlinerInput(**requests[i]['item']) for i in group)
    assert all(requests[i]['pack']==requests[group[0]]['pack'] for i in group)
    reports=worker.extract(pack,items,threshold=.5,overlap_policy=overlap)
    assert len(reports)==len(group)
    projected=[]
    for ordinal,(member,item,report) in enumerate(zip(group,items,reports,strict=True)):
     assert report.context_id==item.context_id and report.context_digest==item.context_digest and report.member_ordinal==ordinal
     receipt=json.loads(report.batch_receipt_json)
     assert receipt['header']['overlap']==overlap and len(receipt['members'])==len(group)
     if cue:
      builder=fixture_builder(scopes[member])
      project_gliner_cues(builder,family,scopes[member],pack,item,report,profile.profile,inference,threshold=.5)
      values=dict(annotations=builder.annotations,occurrences=builder.occurrences,memberships=builder.memberships)
      for spans in report.raw['entities'].values():
       for span in spans:assert texts[member][span['start']:span['end']]==span['text'] and span['confidence']>=.5
     else:
      values=classification_product(requests[member],asdict(report),profile).value
      scores=values['native_answer']['scores']
      assert list(values['selected_keys'])==[k for k in requests[member]['label_keys'] if k in scores and scores[k]>=requests[member]['threshold']]
     projected.append(values)
    result['calls'].append(dict(members=group,requests=[requests[i] for i in group],reports=[asdict(r) for r in reports],projected=projected))
    (HERE/'raw/nested-production.json').write_text(json.dumps(output,indent=2,default=str))
    print(name,overlap,group,'projected',flush=True)
 finally:worker.close()
 summary={}
 for name,result in output['packs'].items():
  singles={c['members'][0]:json.loads(c['reports'][0]['raw_json']) for c in result['calls'][:3]};comparisons=[]
  for call in result['calls']:
   for member,report in zip(call['members'],call['reports'],strict=True):
    discrete,numeric=difference(singles[member],json.loads(report['raw_json']))
    comparisons.append(dict(members=call['members'],member=member,discrete_mismatches=discrete,max_float_abs_difference=numeric))
  summary[name]=dict(overlap_policy=result['overlap_policy'],comparisons=comparisons)
 (HERE/'raw/nested-production-summary.json').write_text(json.dumps(summary,indent=2))
 print('projected members',sum(len(c['members']) for p in output['packs'].values() for c in p['calls']))

if __name__=='__main__':main()
