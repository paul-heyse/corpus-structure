"""Three native loss-only forwards, then at most one mixed-batch optimizer step."""
from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
    TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import copy
import json
import logging
import math
import random
import time
import traceback

import torch
from torch.optim.optimizer import register_optimizer_step_pre_hook, register_optimizer_step_post_hook
from gliner2.training.trainer import ExtractorDataset, ExtractorTrainer, TrainingConfig
from corpus_structure.methods.gliner import load_model
from corpus_structure.methods.m1_source import M1Config

from fixed_schema_processor import FixedSchemaProcessor, conditioning, digest

HERE = Path(__file__).resolve().parent
ALIGN = HERE.parent / '2026-11-04_m1-training-alignment'
OUT = HERE / 'run-001'
START = time.perf_counter()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def file_receipt(path):
    with path.open('rb') as stream:
        checksum = __import__('hashlib').file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=checksum)


def emit(kind, **values):
    record = dict(kind=kind, at=datetime.now(timezone.utc).isoformat(),
                  elapsed_seconds=time.perf_counter()-START, **values)
    with (OUT / 'events.jsonl').open('a') as output:
        output.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps(record, ensure_ascii=False, allow_nan=False), flush=True)


def parameter_receipt(model):
    output = []
    for name, parameter in model.named_parameters():
        data = parameter.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()
        output.append(dict(name=name, shape=list(parameter.shape), dtype=str(parameter.dtype),
                           sha256=sha256(data).hexdigest()))
    return output, digest(output)


def make_sample(sample_id, context, family, targets, origin):
    declaration = context['packs'][family]['declaration']
    field_order = [field['name'] for field in declaration['structures'][family]['fields']]
    targets = [{name: target[name] for name in field_order} for target in targets]
    return dict(input=context['text'], output=dict(format=FixedSchemaProcessor.FORMAT,
        sample_id=sample_id, released_schema=declaration, released_schema_digest=digest(declaration),
        family=family, target_records=targets, target_records_digest=digest(targets),
        source=dict(source_view_id=context['source_view_id'], index=context['index'],
                    context_id=context['context_id'], text_sha256=context['text_sha256'],
                    pack_fingerprint=context['packs'][family]['fingerprint'], origin=origin)))


def main():
    OUT.mkdir(exist_ok=False)
    random.seed(0)
    torch.manual_seed(0)
    assert version('gliner2') == '2.1.0'
    contexts = {(item['source_view_id'],item['index']): item for item in rows(ALIGN/'source-contexts.jsonl')}
    saved, origins = rows(ALIGN/'training-targets.jsonl'), rows(ALIGN/'training-target-origins.jsonl')
    assert origins[0]['family'] == 'assertion' and len(saved[0]['output']['json_structures']) == 3
    assert origins[0]['source_view_id'] == 23 and origins[0]['index'] == 4
    assert not origins[0]['excluded_overlaps'] and all(item['pass_id'] == 24 for item in origins[0]['gold_records'])
    positive = make_sample('assertion-three-record-positive', contexts[23,4], 'assertion',
        [item['assertion'] for item in saved[0]['output']['json_structures']], origins[0])
    zero = make_sample('assertion-genuine-zero', contexts[22,0], 'assertion', [],
        dict(pass_id=23, sampling_partition='feature_fit', records=0,
             authority='frozen protected feature-fit alignment'))
    assert zero['input'] == 'Chapter 5'
    assert zero['output']['released_schema'] == positive['output']['released_schema']
    absent_mapping = next(item for item in rows(ALIGN/'mapping-attempts.jsonl') if item.get('errors')
        and all(error['reason'] == 'nonpresent classified role has no strict ChoiceField ABSENT representation'
                for error in item['errors']))
    assert absent_mapping['pass_id'] == 24 and absent_mapping['index'] == 14
    absent_roles = [item['role'] for item in absent_mapping['errors']]
    absent_target = dict(absent_mapping['target'])
    for role in absent_roles:
        assert absent_target[role+'__state']['value'] != 'present' and role not in absent_target
        absent_target[role] = None
    absent = make_sample('definition-actual-classified-role-absent', contexts[23,14], 'definition',
        [absent_target], dict(pass_id=24, content_digest=absent_mapping['content_digest'],
        record_id=absent_mapping['record_id'], absent_roles=absent_roles,
        scope='isolated record loss-only representation control; not promoted to complete training context'))
    declared_training = [positive, zero]
    frozen_training_digest = digest(declared_training)
    # Supported raw-dict dataset route must preserve the independent payload exactly.
    raw_copy = copy.deepcopy(declared_training)
    dataset = ExtractorDataset(raw_copy, shuffle=False, validate=False)
    assert [dict(input=dataset[index][0], output=dataset[index][1]) for index in range(len(dataset))] == declared_training
    assert digest(raw_copy) == frozen_training_digest
    write(OUT/'predeclared-samples.json', dict(loss_only=[zero,absent,positive],
        one_step_batch=declared_training, one_step_batch_digest=frozen_training_digest,
        selection_policy='fixed prior native-target controls; no model outcome selected examples',
        raw_dict_dataset_route='passed unchanged values and insertion order, no sanitation'))
    for path in (Path(__file__), HERE/'fixed_schema_processor.py'):
        (OUT/(path.stem+'-executed.py.txt')).write_bytes(path.read_bytes())
    configuration = json.loads((ALIGN/'source-reconstruction.json').read_text())[0]['params']
    cfg = M1Config.model_validate(configuration)
    assert cfg.parent_threads == 1 and cfg.threads == 4
    checkpoint_config = json.loads((cfg.snapshot/'config.json').read_text())
    assert checkpoint_config['boundary_head']['max_gold_per_query'] == 64
    launch = dict(at=datetime.now(timezone.utc).isoformat(), scripts=[file_receipt(Path(__file__)),
        file_receipt(HERE/'fixed_schema_processor.py')],
        inputs=[file_receipt(ALIGN/name) for name in ('source-contexts.jsonl','source-reconstruction.json',
            'training-targets.jsonl','training-target-origins.jsonl','mapping-attempts.jsonl')],
        versions={name: version(name) for name in ('gliner2','torch','transformers')},
        model_profile=asdict(cfg.profile()), thread_policy=dict(model=4,parent=1,interop=1),
        loss_only_mode=dict(model_training=True,gradients=False,optimizer=False,gold_injection_prob=0.0),
        one_step_policy=dict(batch_size=2,samples=['assertion-three-record-positive','assertion-genuine-zero'],
            steps=1,gradient_accumulation=1,train_only_native_gold_injection='native trainer default schedule; first step1.0',
            no_inference=True,fp32=True,no_sanitation=True,no_truncation=True,max_gold_per_query=64))
    launch['model_profile']['snapshot'] = str(cfg.snapshot)
    write(OUT/'launch-receipt.json', launch)
    emit('raw_dataset_route_passed', samples=2, frozen_training_digest=frozen_training_digest)
    emit('load_start')
    model, effective = load_model(cfg.profile())
    assert not torch.cuda.is_available()
    assert all(parameter.device.type == 'cpu' and parameter.dtype == torch.float32 for parameter in model.parameters())
    wrapper = FixedSchemaProcessor(model.processor, max_gold_per_query=64)
    before, before_digest = parameter_receipt(model)
    write(OUT/'parameters-before.json', before)
    emit('model_loaded', parameters=sum(parameter.numel() for parameter in model.parameters()),
         effective_profile=json.loads(effective),parameter_digest=before_digest)
    warning_records = []
    class CaptureWarnings(logging.Handler):
        def emit(self, record):
            message = record.getMessage()
            if 'dropped' in message.lower() or 'non-finite' in message.lower():
                warning_records.append(dict(name=record.name,level=record.levelname,message=message))
    warnings_handler = CaptureWarnings(level=logging.WARNING)
    logging.getLogger('gliner2').addHandler(warnings_handler)
    counts = dict(forward=0,loss_only_forward=0,training_forward=0,optimizer_pre=0,optimizer_post=0)
    stage = dict(name='not_started')
    forward_results = []
    def forward_pre(module,args,kwargs):
        counts['forward'] += 1
        batch = args[0]
        assert counts['forward'] <= 4
        receipt = copy.deepcopy(wrapper.last_receipt)
        assert receipt['exact_conditioning'] and not receipt['native_processor_is_training']
        assert digest(conditioning(batch)) == receipt['conditioning_digest']
        receipt.update(model_training=module.training,grad_enabled=torch.is_grad_enabled(),
            explicit_gold_injection=kwargs.get('gold_injection_prob'),
            effective_gold_injection=kwargs.get('gold_injection_prob',getattr(module.boundary_head,'_gold_injection_prob',None)))
        write(OUT/(stage['name']+'-actual-batch.json'),receipt)
        emit('forward_start',stage=stage['name'],samples=[sample['sample_id'] for sample in receipt['samples']],
            model_training=module.training,grad_enabled=torch.is_grad_enabled(),
            subwords=batch.original_lengths,conditioning_digest=receipt['conditioning_digest'],
            gold_injection=receipt['effective_gold_injection'])
    def forward_post(module,args,kwargs,output):
        batch = args[0]
        loss = output.get('total_loss')
        assert loss is not None and loss.numel()==1 and bool(torch.isfinite(loss.detach()).all())
        components = {name: float(value.detach().cpu()) for name,value in (getattr(output,'losses',None) or {}).items()
                      if isinstance(value,torch.Tensor) and value.numel()==1}
        assert components and all(math.isfinite(value) for value in components.values())
        is_training = stage['name']=='one-step'
        counts['training_forward' if is_training else 'loss_only_forward'] += 1
        assert bool(loss.requires_grad) == is_training
        anchors = []
        native_records = batch.targets.records or [[] for _ in range(len(batch))]
        for sample_index,records in enumerate(native_records):
            sample = []
            for record in records:
                target = record.field_for_query(record.anchor_query_id)
                spans = [span for alternatives in target.values for span in alternatives]
                available = output.candidates.indices[sample_index,record.anchor_query_id][
                    output.candidates.valid_mask[sample_index,record.anchor_query_id]].tolist()
                sample.append(dict(instance=record.instance_id,anchor_query=record.anchor_query_id,
                    gold_spans=spans,uninjected_or_training_candidate_present=any(list(span) in available for span in spans)))
            anchors.append(sample)
        if any(native_records):
            assert 'record_field_loss' in components, 'native record auxiliary loss was absent/dropped'
        result = dict(stage=stage['name'],total_loss=float(loss.detach().cpu()),finite=True,
            requires_grad=bool(loss.requires_grad),components=components,
            candidate_shape=list(output.candidates.indices.shape),candidate_valid_count=int(output.candidates.valid_mask.sum()),
            native_record_mask=batch.targets.record_targets[2].tolist(),anchor_presence=anchors,
            exact_conditioning=True, samples=wrapper.last_receipt['samples'])
        write(OUT/(stage['name']+'-loss.json'),result)
        forward_results.append(result)
        emit('forward_complete',stage=stage['name'],total_loss=result['total_loss'],components=components)
    def optimizer_pre(optimizer,args,kwargs):
        counts['optimizer_pre']+=1
        assert counts['optimizer_pre']==1 and stage['name']=='one-step'
        gradients=[parameter.grad for group in optimizer.param_groups for parameter in group['params'] if parameter.grad is not None]
        assert gradients and all(bool(torch.isfinite(gradient).all()) for gradient in gradients)
        nonzero=sum(bool(torch.count_nonzero(gradient)) for gradient in gradients)
        assert nonzero>0
        emit('optimizer_pre',gradient_tensors=len(gradients),nonzero_gradient_tensors=nonzero,all_finite=True)
    def optimizer_post(optimizer,args,kwargs):
        counts['optimizer_post']+=1
        assert counts['optimizer_post']==1
        steps=sorted({int(state['step']) for state in optimizer.state.values() if 'step' in state})
        assert steps==[1]
        emit('optimizer_post',state_steps=steps)
    handles=[model.register_forward_pre_hook(forward_pre,with_kwargs=True),
        model.register_forward_hook(forward_post,with_kwargs=True),
        register_optimizer_step_pre_hook(optimizer_pre),register_optimizer_step_post_hook(optimizer_post)]
    try:
        model.train(True)
        for sample in (zero,absent,positive):
            stage['name']='loss-only-'+sample['output']['sample_id']
            wrapper.change_mode(is_training=False)
            batch=wrapper.collate_fn_inference([(sample['input'],sample['output'])],
                architecture='boundary',build_targets=True,max_gold_per_query=64,on_capacity_exceeded='raise')
            with torch.no_grad():
                model(batch,gold_injection_prob=0.0)
            assert not warning_records, warning_records
            assert all(parameter.grad is None for parameter in model.parameters())
        after_loss, after_loss_digest=parameter_receipt(model)
        write(OUT/'parameters-after-loss-only.json',after_loss)
        assert after_loss_digest==before_digest and counts['loss_only_forward']==3
        emit('loss_only_gate_passed',parameters_unchanged=True,forward_count=3)
        config=TrainingConfig(output_dir=str(OUT/'native'),experiment_name='m1-fixed-schema-mixed-one-step',
            num_epochs=1,max_steps=1,batch_size=2,eval_batch_size=2,gradient_accumulation_steps=1,
            encoder_lr=1e-5,task_lr=5e-4,weight_decay=0.01,scheduler_type='constant',warmup_ratio=0.0,warmup_steps=0,
            fp16=False,bf16=False,eval_strategy='no',save_best=False,early_stopping=False,num_workers=0,pin_memory=False,
            seed=0,validate_data=False,max_len=None,strict_training=True,on_capacity_exceeded='raise',
            allow_invalid_samples=False,skip_step_errors=False,ignore_nonfinite_losses=False,use_lora=False,
            report_to_wandb=False,group_by_length=False,compile_model=False,gradient_checkpointing=False,
            fused_optimizer=False,allow_tf32=False,float32_matmul_precision='highest',log_proposal_metrics=False,
            diagnostics_every_n_steps=0,profile_first_n_steps=0,dry_run_recall_steps=0)
        write(OUT/'native-training-config.json',asdict(config))
        stage['name']='one-step'
        emit('trainer_start',processor_seam='ExtractorTrainer(processor=wrapper)',config=asdict(config))
        trainer=ExtractorTrainer(model,config,processor=wrapper)
        assert trainer.processor is wrapper and trainer.device.type=='cpu'
        result=trainer.train(train_data=copy.deepcopy(declared_training),eval_data=None)
        assert counts==dict(forward=4,loss_only_forward=3,training_forward=1,optimizer_pre=1,optimizer_post=1)
        assert trainer.global_step==1 and result['total_steps']==1 and not warning_records
        assert bool(torch.isfinite(trainer._last_grad_norm))
        assert sorted(wrapper.calls[-1]['samples'])==sorted(sample['output']['sample_id'] for sample in declared_training)
        assert wrapper.calls[-1]['entrypoint']=='collate_fn_train'
        after,after_digest=parameter_receipt(model)
        write(OUT/'parameters-after-step.json',after)
        changed=[old['name'] for old,new in zip(before,after,strict=True) if old['sha256']!=new['sha256']]
        assert changed and after_digest!=before_digest
        assert all(bool(torch.isfinite(parameter).all()) for parameter in model.parameters())
        cfg.profile().verify_artifacts()
        checkpoint=[file_receipt(path) for path in sorted((OUT/'native'/'final').rglob('*')) if path.is_file()]
        assert checkpoint
        result['best_metric']=None if not math.isfinite(result['best_metric']) else result['best_metric']
        summary=dict(outcome='passed',at=datetime.now(timezone.utc).isoformat(),
            scope='native fixed-schema three loss-only controls plus exactly one mixed-batch optimizer step',
            counts=counts,loss_only_parameters_unchanged=True,
            parameters_before_digest=before_digest,parameters_after_loss_only_digest=after_loss_digest,
            parameters_after_step_digest=after_digest,changed_parameter_count=len(changed),
            changed_parameters=changed,all_final_parameters_finite=True,
            all_gradients_finite=True,gradient_norm=float(trainer._last_grad_norm),
            fixed_training_batch_digest=frozen_training_digest,forward_results=forward_results,
            wrapper_calls=wrapper.calls,native_warnings=warning_records,trainer_result=result,
            checkpoint_files=checkpoint,total_seconds=time.perf_counter()-START,
            unchanged_base_snapshot=True,source_boundary='unchanged whitespace',
            no_heldout=True,no_db=True,no_pdf=True,no_product_adoption=True,
            limits=['numerical/callable integration only; no efficacy/calibration/generalization claim',
                'loss-only train-mode proposals uninjected; standard training-only gold injection1 at native optimizer step',
                'isolated ABSENT record is a loss-only representation control, not an admitted complete training context',
                'native source capacities retained; no explicit overcapacity experiment',
                'experimental raw payload plus wrapper; stock JSONL/collator unchanged'])
        write(OUT/'result.json',summary)
        emit('finished',outcome='passed',counts=counts,changed_parameter_count=len(changed))
    finally:
        for handle in handles:
            handle.remove()
        logging.getLogger('gliner2').removeHandler(warnings_handler)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        if OUT.exists():
            write(OUT/'failure.json',dict(exception=type(error).__name__,message=str(error),
                traceback=traceback.format_exc(),at=datetime.now(timezone.utc).isoformat()))
        raise
