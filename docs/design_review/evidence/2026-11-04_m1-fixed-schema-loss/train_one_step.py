"""Resume only the authorized one-step integration after an inactive-cap guard correction."""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode=True
os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
    TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')

from dataclasses import asdict
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import copy
import json
import logging
import math
import time
import traceback

import torch
from torch.optim.optimizer import register_optimizer_step_pre_hook,register_optimizer_step_post_hook
from gliner2.training.trainer import ExtractorTrainer,TrainingConfig
from corpus_structure.methods.gliner import load_model
from corpus_structure.methods.m1_source import M1Config

from fixed_schema_processor import FixedSchemaProcessor,conditioning,digest
from run_experiment import file_receipt,parameter_receipt

HERE=Path(__file__).resolve().parent
PRIOR=HERE/'run-001'
OUT=HERE/(sys.argv[1] if len(sys.argv)>1 else 'run-002')
START=time.perf_counter()


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def emit(kind,**values):
    row=dict(kind=kind,at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-START,**values)
    with (OUT/'events.jsonl').open('a') as stream:
        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(row,ensure_ascii=False,allow_nan=False),flush=True)


def main():
    OUT.mkdir(exist_ok=False)
    prior_events=[json.loads(line) for line in (PRIOR/'events.jsonl').read_text().splitlines()]
    gate=next(row for row in prior_events if row['kind']=='loss_only_gate_passed')
    assert gate['parameters_unchanged'] and gate['forward_count']==3
    assert not any(row['kind'].startswith('optimizer_') for row in prior_events)
    assert sum(row['kind']=='forward_complete' for row in prior_events)==3
    before_prior=json.loads((PRIOR/'parameters-before.json').read_text())
    after_loss=json.loads((PRIOR/'parameters-after-loss-only.json').read_text())
    assert before_prior==after_loss
    declared=json.loads((PRIOR/'predeclared-samples.json').read_text())
    training=declared['one_step_batch']
    assert digest(training)==declared['one_step_batch_digest']
    assert sorted(item['output']['sample_id'] for item in training)==['assertion-genuine-zero','assertion-three-record-positive']
    assert sorted(len(item['output']['target_records']) for item in training)==[0,3]
    config_data=json.loads((PRIOR/'native-training-config.json').read_text())
    config_data['output_dir']=str(OUT/'native')
    config=TrainingConfig(**config_data)
    assert config.max_steps==1 and config.batch_size==2 and config.gradient_accumulation_steps==1
    assert config.max_len is None and config.on_capacity_exceeded=='raise' and not config.validate_data
    launch_prior=json.loads((PRIOR/'launch-receipt.json').read_text())
    for path in (Path(__file__),HERE/'fixed_schema_processor.py'):
        (OUT/(path.stem+'-executed.py.txt')).write_bytes(path.read_bytes())
    write(OUT/'launch-receipt.json',dict(at=datetime.now(timezone.utc).isoformat(),
        scripts=[file_receipt(Path(__file__)),file_receipt(HERE/'fixed_schema_processor.py')],
        reused_loss_gate=file_receipt(PRIOR/'parameters-after-loss-only.json'),
        reused_predeclared_batch=file_receipt(PRIOR/'predeclared-samples.json'),
        prior_failure=file_receipt(PRIOR/'failure.json'),
        policy='loss-only receipts reused; fresh unchanged base; one mixed optimizer step only',
        native_config=asdict(config),expected_effective_max_len=4096,no_actual_truncation=True))
    cfg_data=json.loads((HERE.parent/'2026-11-04_m1-training-alignment'/'source-reconstruction.json').read_text())[0]['params']
    cfg=M1Config.model_validate(cfg_data)
    profile=asdict(cfg.profile());profile['snapshot']=str(cfg.snapshot)
    assert json.loads(json.dumps(profile))==launch_prior['model_profile']
    emit('load_start',one_step_batch_digest=declared['one_step_batch_digest'])
    model,effective=load_model(cfg.profile())
    assert not torch.cuda.is_available()
    assert all(parameter.device.type=='cpu' and parameter.dtype==torch.float32 for parameter in model.parameters())
    before,before_digest=parameter_receipt(model)
    assert before==before_prior
    write(OUT/'parameters-before.json',before)
    emit('model_loaded',base_parameters_equal_prior=True,effective_profile=json.loads(effective))
    wrapper=FixedSchemaProcessor(model.processor,max_gold_per_query=64)
    counts=dict(forward=0,optimizer_pre=0,optimizer_post=0)
    forward_results=[]
    native_warnings=[]
    class CaptureWarnings(logging.Handler):
        def emit(self,record):
            if 'dropped' in record.getMessage().lower() or 'non-finite' in record.getMessage().lower():
                native_warnings.append(dict(name=record.name,message=record.getMessage()))
    handler=CaptureWarnings(level=logging.WARNING)
    logging.getLogger('gliner2').addHandler(handler)
    def forward_pre(module,args,kwargs):
        counts['forward']+=1
        assert counts['forward']==1
        batch=args[0];receipt=copy.deepcopy(wrapper.last_receipt)
        assert receipt['entrypoint']=='collate_fn_train'
        assert receipt['requested_max_len']==4096 and receipt['native_cap_inactive'] and not receipt['actual_truncation']
        assert receipt['exact_conditioning'] and not receipt['native_processor_is_training']
        assert digest(conditioning(batch))==receipt['conditioning_digest']
        assert sorted(sample['sample_id'] for sample in receipt['samples'])==sorted(item['output']['sample_id'] for item in training)
        assert sorted(sample['expected_records'] for sample in receipt['samples'])==[0,3]
        receipt.update(model_training=module.training,grad_enabled=torch.is_grad_enabled(),
                       effective_training_gold_injection=getattr(module.boundary_head,'_gold_injection_prob',None))
        write(OUT/'actual-trainer-batch.json',receipt)
        emit('forward_start',model_training=module.training,grad_enabled=torch.is_grad_enabled(),
            max_len=receipt['requested_max_len'],source_word_counts=receipt['source_word_counts'],
            subwords=batch.original_lengths,native_cap_inactive=True,conditioning_exact=True,
            training_gold_injection=receipt['effective_training_gold_injection'])
    def forward_post(module,args,kwargs,output):
        loss=output.get('total_loss')
        assert loss is not None and loss.requires_grad and bool(torch.isfinite(loss.detach()).all())
        components={name:float(value.detach().cpu()) for name,value in (getattr(output,'losses',None) or {}).items()
                    if isinstance(value,torch.Tensor) and value.numel()==1}
        assert 'record_field_loss' in components and all(math.isfinite(value) for value in components.values())
        result=dict(total_loss=float(loss.detach().cpu()),finite=True,requires_grad=True,components=components)
        forward_results.append(result);write(OUT/'forward-loss.json',result)
        emit('forward_complete',**result)
    def optimizer_pre(optimizer,args,kwargs):
        counts['optimizer_pre']+=1;assert counts['optimizer_pre']==1
        gradients=[parameter.grad for group in optimizer.param_groups for parameter in group['params'] if parameter.grad is not None]
        assert gradients and all(bool(torch.isfinite(gradient).all()) for gradient in gradients)
        nonzero=sum(bool(torch.count_nonzero(gradient)) for gradient in gradients)
        assert nonzero>0
        emit('optimizer_pre',gradient_tensors=len(gradients),nonzero_gradient_tensors=nonzero,all_finite=True)
    def optimizer_post(optimizer,args,kwargs):
        counts['optimizer_post']+=1;assert counts['optimizer_post']==1
        steps=sorted({int(state['step']) for state in optimizer.state.values() if 'step' in state})
        assert steps==[1];emit('optimizer_post',state_steps=steps)
    handles=[model.register_forward_pre_hook(forward_pre,with_kwargs=True),
        model.register_forward_hook(forward_post,with_kwargs=True),
        register_optimizer_step_pre_hook(optimizer_pre),register_optimizer_step_post_hook(optimizer_post)]
    try:
        trainer=ExtractorTrainer(model,config,processor=wrapper)
        assert trainer.processor is wrapper and trainer.device.type=='cpu'
        emit('trainer_start',native_config=asdict(config))
        result=trainer.train(train_data=copy.deepcopy(training),eval_data=None)
        assert counts==dict(forward=1,optimizer_pre=1,optimizer_post=1)
        assert trainer.global_step==1 and result['total_steps']==1 and not native_warnings
        assert bool(torch.isfinite(trainer._last_grad_norm))
        after,after_digest=parameter_receipt(model)
        write(OUT/'parameters-after.json',after)
        changed=[old['name'] for old,new in zip(before,after,strict=True) if old['sha256']!=new['sha256']]
        assert changed and before_digest!=after_digest
        assert all(bool(torch.isfinite(parameter).all()) for parameter in model.parameters())
        cfg.profile().verify_artifacts()
        files=[file_receipt(path) for path in sorted((OUT/'native'/'final').rglob('*')) if path.is_file()]
        assert files
        result['best_metric']=None if not math.isfinite(result['best_metric']) else result['best_metric']
        summary=dict(outcome='passed',at=datetime.now(timezone.utc).isoformat(),counts=counts,
            total_optimizer_steps_across_attempts=1,total_loss_only_forwards_across_attempts=3,
            prior_loss_gate_unchanged_parameters=True,base_parameters_equal_prior=True,
            parameters_before_digest=before_digest,parameters_after_digest=after_digest,
            changed_parameter_count=len(changed),changed_parameters=changed,
            all_final_parameters_finite=True,all_gradients_finite=True,
            gradient_norm=float(trainer._last_grad_norm),forward_results=forward_results,
            wrapper_calls=wrapper.calls,native_warnings=native_warnings,
            native_max_len4096_inactive=True,actual_truncation=False,
            strict_native_gold_capacity=64,insertion_order_preserved=True,
            unchanged_source_boundary='whitespace',unchanged_base_snapshot=True,
            checkpoint_files=files,trainer_result=result,seconds=time.perf_counter()-START,
            no_heldout=True,no_db=True,no_pdf=True,no_product_adoption=True,
            limits=['numerical/callable integration only; no efficacy/calibration/generalization claim',
                'loss-only train-mode uninjected candidate pools missed protected gold anchors; native record-field losses zero there',
                'one optimizer step uses native training-only gold injection1; not an inference pool',
                'isolated ABSENT record was loss-only, not a complete admitted training context',
                'no explicit overcapacity batch; exact capacity64/on-error-raise preserved',
                'experimental raw payload and processor wrapper; stock JSONL/collator remain unchanged'])
        write(OUT/'result.json',summary)
        emit('finished',outcome='passed',counts=counts,changed_parameter_count=len(changed))
    finally:
        for handle in handles:handle.remove()
        logging.getLogger('gliner2').removeHandler(handler)


if __name__=='__main__':
    try:main()
    except BaseException as error:
        if OUT.exists():write(OUT/'failure.json',dict(exception=type(error).__name__,message=str(error),
            traceback=traceback.format_exc(),at=datetime.now(timezone.utc).isoformat()))
        raise
