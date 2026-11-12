"""Actual resident-lane cancellation/crash checks at controlled post-send boundaries."""
import argparse
import hashlib
import json
import os
import signal
from dataclasses import asdict
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

import yaml

from corpus_structure.methods.characterization_resources import ProviderExecution, PM2Selection, PM2Work, GLiNERWork
from corpus_structure.methods.gliner import GlinerInput, GlinerPack
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.pm2_gliner_classification import ClassificationProfile
from corpus_structure.methods.pm2_worker import Pm2Worker, preflight_pm2_runtime
from corpus_structure.semantic.cpu_execution import CPUExecutionPolicy, OwnedByteBudget
from corpus_structure.semantic.identity import canonical_bytes

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

class ReadGate:
 def __init__(self):self.sent,self.release=Event(),Event();self.worker=None
 def wait(self,worker):
  self.worker=worker;self.sent.set()
  if not self.release.wait(60):raise RuntimeError('probe controller did not release actual native reply')

class ConnectionGate:
 def __init__(self,connection,gate,worker):self.connection,self.gate,self.worker=connection,gate,worker;self.reads=0
 def send_bytes(self,*args,**kwargs):return self.connection.send_bytes(*args,**kwargs)
 def recv_bytes(self,*args,**kwargs):
  self.reads+=1
  if self.reads==2:self.gate.wait(self.worker)
  return self.connection.recv_bytes(*args,**kwargs)
 def close(self):return self.connection.close()
 def __getattr__(self,name):return getattr(self.connection,name)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('provider',choices=('hanlp','gliner'));parser.add_argument('scenario',choices=('stale','cancel','crash','invalid','words'))
 args=parser.parse_args(); provider,scenario=args.provider,args.scenario
 gate=ReadGate();policy=CPUExecutionPolicy();budget=OwnedByteBudget(policy.max_owned_bytes);owner=ProviderExecution(budget,policy)
 owner.coalescing_providers=frozenset({'hanlp','gliner'})
 if provider=='hanlp':
  python=ROOT/'services/pm2-hanlp/.venv/bin/python';script=ROOT/'python/corpus-structure/src/corpus_structure/methods/pm2_native.py';assets=ROOT/'build/models/pm2'
  checked=preflight_pm2_runtime(python=python,script=script,project=ROOT/'services/pm2-hanlp',provider='hanlp',assets=assets)
  profile=canonical_bytes(dict(provider='hanlp',device='cpu',assets=str(assets),runtime_identity=checked['runtime_identity'],threads=4,interop_threads=1))
  selection=PM2Selection('hanlp',python,script,ROOT/'services/pm2-hanlp',assets,profile,canonical_bytes(checked['runtime_identity']),canonical_bytes(checked['assets']))
  def request(i):return PM2Work(selection,canonical_bytes(dict(sentences=[['The','mean','is','five','.']],admitted_row_tokens=[7])),str(i),(lambda:None,))
  original=Pm2Worker._read_frame
  def read(worker,deadline,active,phase):
   if phase=='inference':gate.wait(worker)
   return original(worker,deadline,active,phase)
  hook=patch.object(Pm2Worker,'_read_frame',read)
 else:
  config=yaml.safe_load((ROOT/'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['default']
  profile=ClassificationProfile(provider='gliner',device='cpu',profile=M1Config.model_validate(config).profile()).profile
  pack=GlinerPack.from_declaration('bep-lifecycle-probe',{'entities':{'term':'A literal technical term.'}},version='native-local-v1')
  def request(i):
   text='x'*32769 if scenario=='invalid' and i==0 else 'word '*600 if scenario=='words' and i==0 else 'The mean is five.'
   item=GlinerInput('source-'+str(i),hashlib.sha256(text.encode()).hexdigest(),text,operation='text.model_characterization/2:probe')
   return GLiNERWork(profile,pack,(item,),.5,'flat',str(i),(lambda:None,))
  original=GlinerWorker._start
  def start(worker):
   original(worker)
   if not isinstance(worker._connection,ConnectionGate):worker._connection=ConnectionGate(worker._connection,gate,worker)
  hook=patch.object(GlinerWorker,'_start',start)
 output=dict(provider=provider,scenario=scenario,events=[],responses=[])
 try:
  with hook:
   handles=[]
   for i in ([1,0] if scenario=='invalid' else range(2 if scenario in ('stale','words') else 1)):
    try:handle=owner.try_submit(request(i))
    except ValueError as error:
     assert scenario=='invalid' and i==0
     output['responses'].append(dict(correlation=str(i),error_type=type(error).__name__,error_message=str(error),early_refusal=True))
    else:
     assert handle is not None
     handles.append(handle)
   assert handles
   handles[0].flush()
   assert gate.sent.wait(60),'native request did not reach post-send reply boundary'
   output['events'].append('actual-native-request-sent')
   process=gate.worker._process
   output['owned_pid']=process.pid
   if scenario=='stale':handles[0].cancel();output['events'].append('one-running-member-stopped')
   if scenario=='crash':os.kill(process.pid,signal.SIGKILL);output['events'].append('owned-native-child-killed')
   closer=None
   if scenario=='cancel':
    closer=Thread(target=owner.close);closer.start();assert owner._stop.wait(10);output['events'].append('operation-stop-observed')
   gate.release.set()
   for handle in handles:
    reply=handle.future.result(timeout=60)
    output['responses'].append(dict(correlation=reply.correlation,error_type=reply.error_type,error_message=reply.error_message,payload=json.loads(reply.payload_content),reports=[asdict(r) for r in reply.reports],stopped=handle.stopped.is_set()))
    handle.retire()
   if closer:closer.join(60);assert not closer.is_alive()
   if scenario=='stale':
    assert handles[0].stopped.is_set() and output['responses'][1]['error_type'] is None
    assert output['responses'][1]['correlation']=='1'
   elif scenario in ('invalid','words'):
    assert output['responses'][0]['error_type'] is not None and output['responses'][1]['error_type'] is None
   else:assert output['responses'][0]['error_type'] is not None
 finally:
  gate.release.set();owner.close()
 output['owned_child_stopped']=(process.poll() is not None) if provider=='hanlp' else (getattr(process,'_closed',False) or not process.is_alive())
 assert output['owned_child_stopped']
 output['budget_after_close']=budget.used_bytes
 assert budget.used_bytes==0
 output['outcome']='passed'
 (HERE/'raw'/('lifecycle-'+provider+'-'+scenario+'.json')).write_text(json.dumps(output,indent=2,default=str))
 print(provider,scenario,'passed',flush=True)

if __name__=='__main__':main()
