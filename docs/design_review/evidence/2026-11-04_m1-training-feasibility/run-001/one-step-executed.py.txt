"""One authorized native CPU/FP32 optimizer step over a complete fit positive."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
import json
import math
import random
import sys
import time
from dataclasses import asdict,fields
from datetime import datetime,timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import torch
from torch.optim.optimizer import register_optimizer_step_pre_hook,register_optimizer_step_post_hook
from gliner2.processor import SamplingConfig
from gliner2.training.data import InputExample,TrainingDataset
from gliner2.training.trainer import ExtractorTrainer,TrainingConfig
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.gliner import load_model

HERE=Path(__file__).resolve().parent
ALIGN=HERE.parent/'2026-11-04_m1-training-alignment'
OUT=HERE/'run-001'
OUT.mkdir(exist_ok=False)
EVENTS=OUT/'events.jsonl'
START=time.perf_counter()
def emit(kind,**values):
    row=dict(kind=kind,utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-START,**values)
    with EVENTS.open('a') as stream:stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(row,ensure_ascii=False,allow_nan=False),flush=True)
def file_receipt(path):
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
def tensor_digest(tensor):
    value=tensor.detach().cpu().contiguous()
    return sha256(value.view(torch.uint8).numpy().tobytes()).hexdigest()
def parameter_receipt(model):
    result=[]
    for name,p in model.named_parameters():
        result.append(dict(name=name,shape=list(p.shape),dtype=str(p.dtype),sha256=tensor_digest(p)))
    digest=sha256(json.dumps(result,separators=(',',':')).encode()).hexdigest()
    return result,digest

rows=[json.loads(x) for x in (ALIGN/'training-targets.jsonl').read_text().splitlines()]
origins=[json.loads(x) for x in (ALIGN/'training-target-origins.jsonl').read_text().splitlines()]
prepared=[json.loads(x) for x in (ALIGN/'deterministic-native-targets.jsonl').read_text().splitlines()]
selected=min(prepared,key=lambda x:(x['subwords'],x['ordinal']))
row=rows[selected['ordinal']];origin=origins[selected['ordinal']]
assert origin['source_view_id']==23 and not origin['excluded_overlaps']
assert all(g['pass_id']==24 for g in origin['gold_records'])
validation=TrainingDataset([InputExample.from_dict(row)]).validate()
(OUT/'selected-input.jsonl').write_text(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
(OUT/'selected-origin.json').write_text(json.dumps(origin,ensure_ascii=False,indent=2))
configuration=json.loads((ALIGN/'source-reconstruction.json').read_text())[1]['params']
cfg=M1Config.model_validate(configuration)
start_receipt=dict(executed_script=file_receipt(Path(__file__)),inputs=[file_receipt(ALIGN/name) for name in ('training-targets.jsonl','training-target-origins.jsonl','deterministic-native-targets.jsonl','source-reconstruction.json')],selection_policy='minimum verified deterministic subwords then ordinal among complete safe positive rows; independent of model output',selected=selected,origin=origin,validation=validation,versions={k:version(k) for k in ('gliner2','torch','transformers')},seed=0,model=asdict(cfg.profile()),no_evaluation=True,no_heldout=True)
# Convert only the profile acquisition Path; source strings and schema order stay exact.
start_receipt['model']['snapshot']=str(cfg.snapshot)
(OUT/'input-receipt.json').write_text(json.dumps(start_receipt,ensure_ascii=False,indent=2))
emit('load_start',selected_ordinal=selected['ordinal'],source_view_id=23,context_id=origin['context_id'],family=origin['family'],records=len(origin['gold_records']),deterministic_subwords=selected['subwords'])
model,effective=load_model(cfg.profile())
assert not torch.cuda.is_available()
assert all(p.device.type=='cpu' and p.dtype==torch.float32 for p in model.parameters())
model.processor.sampling_config=SamplingConfig(**{f.name:False if f.type is bool or f.name.startswith('shuffle') else 0.0 for f in fields(SamplingConfig) if f.name!='max_num_labels'})
before,before_digest=parameter_receipt(model)
(OUT/'parameters-before.json').write_text(json.dumps(before))
emit('model_loaded',parameters=sum(p.numel() for p in model.parameters()),parameter_digest=before_digest,threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads(),effective_profile=json.loads(effective))

calls=dict(forward=0,optimizer_pre=0,optimizer_post=0)
forward_receipts=[]
def forward_pre(module,args):
    calls['forward']+=1
    assert calls['forward']==1
    batch=args[0]
    spec=next(iter(batch.record_specs[0].values()))
    native_records=batch.targets.records[0]
    batch_receipt=dict(original_texts=batch.original_texts,original_schemas=batch.original_schemas,schema_tokens=batch.schema_tokens_list,text_tokens=batch.text_tokens,start_mappings=batch.start_mappings,end_mappings=batch.end_mappings,record_specs={k:asdict(v) for k,v in batch.record_specs[0].items()},native_records=[asdict(r) for r in native_records],subwords=batch.original_lengths,text_word_counts=batch.text_word_counts,description_retained=all(d in batch.schema_tokens_list[0][0][2] for d in row['output']['json_descriptions'][origin['family']].values()),record_count_equal=len(native_records)==len(origin['gold_records']))
    assert batch.original_schemas==[row['output']]
    assert batch_receipt['record_count_equal']
    assert [f.name for f in spec.fields]==list(row['output']['json_structures'][0][origin['family']])
    (OUT/'actual-forward-batch.json').write_text(json.dumps(batch_receipt,ensure_ascii=False,indent=2))
    emit('forward_start',subwords=batch.original_lengths,description_retained=batch_receipt['description_retained'],records=len(native_records))
def forward_post(module,args,output):
    loss=output.get('total_loss')
    losses={k:float(v.detach().cpu()) for k,v in (getattr(output,'losses',None) or {}).items() if isinstance(v,torch.Tensor) and v.numel()==1}
    result=dict(total_loss=float(loss.detach().cpu()),requires_grad=loss.requires_grad,loss_finite=bool(torch.isfinite(loss.detach()).all()),loss_components=losses)
    assert result['loss_finite'] and result['requires_grad']
    forward_receipts.append(result)
    emit('forward_complete',**result)
def optimizer_pre(optimizer,args,kwargs):
    calls['optimizer_pre']+=1
    assert calls['optimizer_pre']==1
    grads=[p.grad for group in optimizer.param_groups for p in group['params'] if p.grad is not None]
    assert grads and all(bool(torch.isfinite(g).all()) for g in grads)
    nonzero=sum(bool(torch.count_nonzero(g)) for g in grads)
    assert nonzero>0
    emit('optimizer_pre',gradient_tensors=len(grads),nonzero_gradient_tensors=nonzero,all_gradients_finite=True)
def optimizer_post(optimizer,args,kwargs):
    calls['optimizer_post']+=1
    assert calls['optimizer_post']==1
    steps=sorted({int(state['step']) for state in optimizer.state.values() if 'step' in state})
    assert steps==[1]
    emit('optimizer_post',optimizer_state_step_values=steps)

handles=[model.register_forward_pre_hook(forward_pre),model.register_forward_hook(forward_post),register_optimizer_step_pre_hook(optimizer_pre),register_optimizer_step_post_hook(optimizer_post)]
config=TrainingConfig(output_dir=str(OUT/'native'),experiment_name='m1-positive-one-step-feasibility',num_epochs=1,max_steps=1,batch_size=1,eval_batch_size=1,gradient_accumulation_steps=1,encoder_lr=1e-5,task_lr=5e-4,weight_decay=0.01,scheduler_type='constant',warmup_ratio=0.0,warmup_steps=0,fp16=False,bf16=False,eval_strategy='no',save_best=False,early_stopping=False,num_workers=0,pin_memory=False,seed=0,validate_data=False,max_len=None,strict_training=True,on_capacity_exceeded='raise',allow_invalid_samples=False,skip_step_errors=False,ignore_nonfinite_losses=False,use_lora=False,report_to_wandb=False,group_by_length=False,compile_model=False,gradient_checkpointing=False,fused_optimizer=False,allow_tf32=False,float32_matmul_precision='highest',log_proposal_metrics=False,diagnostics_every_n_steps=0,profile_first_n_steps=0,dry_run_recall_steps=0)
emit('trainer_start',config=asdict(config),save_policy='native trainer has no no-save switch; its unconditional final full checkpoint is retained separately')
trainer=ExtractorTrainer(model,config)
assert trainer.device.type=='cpu' and not config.fp16 and not config.bf16
result=trainer.train(train_data=[row],eval_data=None)
for handle in handles:handle.remove()
assert calls==dict(forward=1,optimizer_pre=1,optimizer_post=1)
assert trainer.global_step==1 and result['total_steps']==1
assert bool(torch.isfinite(trainer._last_grad_norm))
after,after_digest=parameter_receipt(model)
(OUT/'parameters-after.json').write_text(json.dumps(after))
changed=[b['name'] for b,a in zip(before,after,strict=True) if b['sha256']!=a['sha256']]
assert changed and before_digest!=after_digest
assert all(bool(torch.isfinite(p).all()) for p in model.parameters())
final_files=[file_receipt(p) for p in sorted((OUT/'native'/'final').rglob('*')) if p.is_file()]
result['best_metric']=None if not math.isfinite(result['best_metric']) else result['best_metric']
summary=dict(outcome='passed',scope='one native CPU FP32 forward/backward/optimizer update on one complete protected feature-fit positive; no efficacy claim',selected_ordinal=selected['ordinal'],origin=origin,calls=calls,total_steps=trainer.global_step,forward=forward_receipts,gradient_norm=float(trainer._last_grad_norm),all_gradients_finite=True,all_final_parameters_finite=True,parameters_before_digest=before_digest,parameters_after_digest=after_digest,changed_parameter_count=len(changed),changed_parameters=changed,trainer_result=result,checkpoint_files=final_files,total_wall_seconds=time.perf_counter()-START,thread_policy=dict(model=4,parent=1,interop=1),no_evaluation=True,no_heldout=True,no_product_adoption=True)
(OUT/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False))
emit('finished',outcome='passed',changed_parameter_count=len(changed),total_steps=trainer.global_step,result_path=str(OUT/'result.json'))
