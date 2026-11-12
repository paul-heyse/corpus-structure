"""Actual D1 CUDA/BF16 released question, cohort and cancellation qualification."""
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from corpus_structure.ingest.pdf_capacity import pdf_gpu_slot
from corpus_structure.methods.characterization_resources import ProviderExecution, PM2Selection, PM2Work
from corpus_structure.methods.pm2_worker import Pm2Worker, preflight_pm2_runtime
from corpus_structure.semantic.cpu_execution import CPUExecutionPolicy, OwnedByteBudget
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import CHARACTERIZATION_QUESTION_INPUT, compile_question_families, declared_families
from corpus_structure.semantic.model_characterization import compile_question_stage, prepare_model_scope
from corpus_structure.semantic.types import SourceArtifact

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'python/corpus-structure/tests'))
from semantic.test_model_characterization import scope as fixture_scope, builder as fixture_builder


def main():
 source=ROOT/'python/corpus-structure/src/corpus_structure/model/semantic/characterization-questions.yaml'
 families=declared_families(compile_question_families((SourceArtifact(CHARACTERIZATION_QUESTION_INPUT,source.read_bytes()),)))
 texts=['A random variable has an expected value. Its variance measures dispersion.','Independent observations form a sample. The sample mean estimates the population mean.','A random variable has an expected value. Its variance measures dispersion.']
 scopes=[]
 for index,text in enumerate(texts):
  scope=fixture_scope(text);view=replace(scope.view,ref=replace(scope.view.ref,id=101+index,key='d1-cuda-source-'+str(index)))
  scopes.append(prepare_model_scope(view,(0,len(text)),(0,len(text))))
 function=families['character_function_v1'];literal=families['character_scope_v1']
 # Real source-first question factories: preserve full question/option order and original state.
 requests=[compile_question_stage(function,scope,0) for scope in scopes]
 literal_requests=[compile_question_stage(literal,scope,0) for scope in scopes[:2]]
 stage_guard=False
 try:compile_question_stage(function,scopes[0],1,prior={})
 except ValueError:stage_guard=True
 assert stage_guard,'stage1 unexpectedly admitted without frozen stage0 answers'
 script=ROOT/'python/corpus-structure/src/corpus_structure/methods/pm2_native.py';python=ROOT/'.venv/bin/python';assets=ROOT/'build/models/pm2'
 checked=preflight_pm2_runtime(python=python,script=script,project=ROOT,provider='d1',assets=assets)
 profile=canonical_bytes(dict(provider='d1',device='cuda',assets=str(assets),runtime_identity=checked['runtime_identity'],threads=4,interop_threads=1))
 selection=PM2Selection('d1',python,script,ROOT,assets,profile,canonical_bytes(checked['runtime_identity']),canonical_bytes(checked['assets']),device='cuda')
 policy=CPUExecutionPolicy();budget=OwnedByteBudget(policy.max_owned_bytes);owner=ProviderExecution(budget,policy);owner.coalescing_providers=frozenset({'d1'})
 output=dict(device='cuda',texts=texts,question_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),selection=asdict(selection),stage_without_prior_refused=stage_guard,calls=[])
 serial=0;builders={}
 def execute(selected, prior_builder=None):
  nonlocal serial
  correlation='cuda-probe-'+str(serial);serial+=1
  request=PM2Work(selection,canonical_bytes(dict(batch=[r.payload for r in selected])),correlation,(lambda:None,))
  handle=owner.try_submit(request);assert handle is not None;handle.flush();handle.future.result(timeout=180)
  reply=handle.collect();assert reply is not None and reply.correlation==correlation
  startup=reply.startup;assert startup['device'].startswith('cuda') and startup['dtype']=='torch.bfloat16' and startup['set_size']==16
  body=reply.payload;assert len(body['batch'])==len(selected)
  projected=[]
  for ordinal,(question,native) in enumerate(zip(selected,body['batch'],strict=True)):
   assert list(native['native']['answers'])==list(question.payload['questions'])
   assert native['batch_receipt']['member_ordinal']==ordinal
   assert json.loads(native['rendered_state'])==question.payload['state']
   assert len([f for f in native['state_fields'] if f[2]=='/source'])==1
   builder=prior_builder if prior_builder is not None else fixture_builder(question.scope);builder.operation['version']='2'
   prior=builder.d1(question,native,runtime=startup)
   for occurrence in builder.occurrences.values():
    for extent in occurrence['extents']:
     assert extent['source_view_id']==question.scope.view.ref.id
     assert extent['text']==question.scope.view.text[extent['start']:extent['end']]
   builders[(correlation,ordinal)]=builder
   projected.append(dict(prior=prior,annotations=list(builder.annotations),occurrences=dict(builder.occurrences)))
  result=dict(correlation=correlation,requests=[r.payload for r in selected],source_view_ids=[r.scope.view.ref.id for r in selected],reply=asdict(reply),projected=projected)
  handle.retire();return result
 try:
  for members in ([0],[1],[2],[0,1,2],[2,1,0],[0,2],[1,0]):
   result=execute([requests[i] for i in members]);result['members']=members;output['calls'].append(result)
   (HERE/'raw/cuda.json').write_text(json.dumps(output,indent=2,default=str));print('cuda functions',members,'projected',flush=True)
  output['literal_call']=execute(literal_requests)
  # Qualify actual prior-state propagation only when native stage0 supplies its prerequisite.
  initial=output['calls'][0]['projected'][0]['prior']
  if initial.get('functions',{}).get('state')=='proposed':
   staged=compile_question_stage(function,scopes[0],1,prior=initial)
   assert staged.payload['state']['prior_answers']=={'functions':initial['functions']}
   output['staged_call']=execute([staged],prior_builder=builders[(output['calls'][0]['correlation'],0)])
  else:output['staged_call']=dict(outcome='not_run',reason='native prerequisite did not propose functions')
  sent,release=Event(),Event();owned=[];original=Pm2Worker._read_frame
  def gated(worker,deadline,active,phase):
   if phase=='inference':
    owned.append(worker._process);sent.set();assert release.wait(60)
   return original(worker,deadline,active,phase)
  with patch.object(Pm2Worker,'_read_frame',gated):
   work=PM2Work(selection,canonical_bytes(dict(batch=[requests[0].payload])),'cuda-active-cancel',(lambda:None,))
   handle=owner.try_submit(work);assert handle is not None;handle.flush();assert sent.wait(60)
   errors=[]
   def close():
    try:owner.close()
    except BaseException as error:errors.append(str(error))
   thread=Thread(target=close);thread.start();assert owner._stop.wait(10);release.set()
   cancelled=handle.future.result(timeout=60);assert cancelled.error_type
   thread.join(60);assert not thread.is_alive() and not errors
   assert owned[0].poll() is not None
   output['active_cancel']=dict(reply=asdict(cancelled),owned_child_stopped=True)
 finally:owner.close()
 assert budget.used_bytes==0
 with pdf_gpu_slot(lambda:None):output['gpu_custody_reacquired']=True
 output['owned_bytes_after_close']=budget.used_bytes;output['outcome']='passed'
 (HERE/'raw/cuda.json').write_text(json.dumps(output,indent=2,default=str))
 print('CUDA/BF16 native batch and lifecycle probe passed',flush=True)

if __name__=='__main__':main()
