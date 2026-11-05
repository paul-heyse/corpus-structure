"""Frozen three-source inputs and actual nondefault structural production journey.

Source selection precedes producer execution. Supplied producer interpretations are
not independent references. No semantic quality/admission follows from this script.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text

from corpus_structure.methods.contextual_embeddings import E5
from corpus_structure.methods.structural_retrieval import source_definition_inventory
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import StructuralPassageSelection, prepare_structural_sources
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
RAW=HERE/'raw'
PROJECT='pce-statistics-structural'
SCOPE='statistics-retained-three-source-001'


def write(path,value):
    with path.open('xb') as out:out.write(canonical_bytes(value)+b'\n')


def freeze(attempt):
    source_specs=(
      (45,46,'gs-normal-usage','Whennis relatively large','Geometric Distribution'),
      (45,46,'gs-conditional-example','To see this, let us compute the conditional probability','Negative Binomial Distribution'),
      (15,26,'forbes-marginal-definition','Probabilities associated with a univariate element','Marginal Probability Density Function'),
      (15,27,'forbes-independence-definition','Two univariates are said to be independent','This implies'),
      (15,28,'forbes-conditional-definition','When two univariates are not independent','Conditional Probability Function'),
      (15,28,'forbes-nonzero-condition','provided the denominator Pr[Y','Conditional Probability Function'),
      (13,31,'nist-mean-definition','mean - the mean is the sum','median - the median'),
      (13,31,'nist-normal-location','The normal distribution is a symmetric','The second histogram'),
      (13,31,'nist-cauchy-exception','The Cauchy distribution is a symmetric','Although the Cauchy distribution is an extreme case'),
      (13,32,'nist-sample-mean-usage','where Ȳ is the sample mean','From the formula'),
      (13,32,'nist-ci-definition','Confidence limits for the mean (Snedecor','Confidence limits are expressed'),
      (13,32,'nist-ci-interpretation','As a technical note','Confidence limits are defined as:'),
      (13,32,'nist-ci-rejection','We reject the null hypotheses','In general, there are three possible'),
    )
    settings=Settings()
    with open_runtime_engine(settings,'pce10-source-freeze',purpose='read') as engine:
        with read_snapshot(engine) as conn:
            selected={row['id']:row['body'] for row in conn.execute(text("SELECT id,projection->>'text' body FROM kb.source_view WHERE id=ANY(:ids)"),{'ids':sorted({v for _,v,_,_,_ in source_specs})}).mappings()}
        selections=[]
        for run,view,pid,start_marker,end_marker in source_specs:
            body=selected[view];start=body.index(start_marker);end=body.index(end_marker,start+len(start_marker))
            selections.append(StructuralPassageSelection(run_id=run,source_view_id=view,passage_id=pid,start=start,end=end,scope=SCOPE))
        prepared=prepare_structural_sources(engine,selections)
    initial=StructuralInput(question='Which selected source passages define or explain the normal distribution invoked by the Grinstead-Snell binomial approximation usage, with its scope and remaining parameter/standard-normal limits?',scope=SCOPE,inventory_id='preparing-source-target-inventory',policy_id='source-backed-definition-applicability-1',sources=prepared.sources,passages=prepared.passages,dependencies=(E5.profile_id,'source-selection:three-source-statistics-001'),coverage_limits=('Grinstead-Snell selected view covers chapter5.1 only; no normal-density definition or standard-normal source passage is retained in this selection.','Captured statistical formulas may contain recognition/placement defects; no numerical or scientific-equivalence claim.','This is a deliberately selected development cohort, not random sampling or whole-book coverage.'))
    target_ids=tuple(p.passage_id for p in initial.passages if p.passage_id not in {'gs-normal-usage','nist-sample-mean-usage'})
    inventory=source_definition_inventory(initial,target_ids=target_ids)
    inputs=initial.model_copy(update={'inventory_id':inventory.inventory_id})
    mean_inputs=inputs.model_copy(update={'question':'Which eligible source passage defines the sample mean named in the NIST confidence-limit formula context? Preserve arithmetic sample mean versus population parameter distinctions.'})
    output=dict(mean_inputs=mean_inputs.model_dump(mode='json',exclude_none=True),mean_input_digest=mean_inputs.identity,mean_usage_id='nist-sample-mean-usage',protocol='pce10-source-selection-1',inputs=inputs.model_dump(mode='json',exclude_none=True),input_digest=inputs.identity,usage_id='gs-normal-usage',target_ids=target_ids,questions={'definition':inputs.question,'comparison':'Compare what NIST says about using the mean for normal versus Cauchy distributions. Preserve observed conditions and action differences; report unknown dimensions and do not assert equivalence.','dossier':'Assemble a mean/location dossier from the selected passages, retaining the mean definition, normal applicability and Cauchy exception. Keep the Grinstead-Snell normal-parameter context visibly unresolved; unrelated probability passages do not establish mean/location membership.'},planned_profile=E5.profile_id,source_selection_script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),quality_claim='not_established',producer_executed=False)
    write(RAW/f'production-input-{attempt}.json',output)
    print(json.dumps({'input':str(RAW/f'production-input-{attempt}.json'),'input_digest':inputs.identity,'sources':len(inputs.sources),'passages':len(inputs.passages),'targets':len(target_ids),'producer_executed':False}),flush=True)


def produce(attempt,replay_from=None):
    import time
    from dataclasses import asdict
    from corpus_structure.methods.contextual_embeddings import EncodedVector, verify_encoder_implementation
    from corpus_structure.methods.structural_retrieval import retrieve_source_definitions
    from corpus_structure.methods.structural_products import compare_clauses, assemble_dossier
    from corpus_structure.semantic.structural_products import ClauseField, ClauseReading, DefinitionReading, DossierMember
    selected=json.loads((RAW/f'production-input-{attempt}.json').read_bytes())
    inputs=StructuralInput.model_validate(selected['inputs'])
    mean_inputs=StructuralInput.model_validate(selected['mean_inputs'])
    start=time.perf_counter()
    if replay_from is not None:
        from corpus_structure.methods.structural_retrieval import replay_source_definition_candidates
        from corpus_structure.semantic.structural_products import StructuralProductReport
        original_normal=StructuralProductReport.model_validate_json((RAW/f'production-normal-{replay_from}.json').read_bytes())
        original_mean=StructuralProductReport.model_validate_json((RAW/f'production-mean-{replay_from}.json').read_bytes())
        implementation=json.loads((RAW/f'production-produced-{replay_from}.json').read_bytes())['implementation']
        normal=replay_source_definition_candidates(original_normal,budget=10,readings=original_normal.definition.readings)
        mean=replay_source_definition_candidates(original_mean,budget=10,readings=(DefinitionReading(target_id='nist-mean-definition',outcome='applicable_definition',evidence=('nist-sample-mean-usage','nist-mean-definition'),reason='NIST explicitly names the sample mean in the confidence-limit formula context and separately defines the mean as the sum of data points divided by their count. This does not identify the unknown population mean with its sample estimate.'),))
        assert normal.inputs==inputs and mean.inputs==mean_inputs
        write(RAW/f'production-normal-{attempt}.json',normal.model_dump(mode='json',exclude_none=True))
        write(RAW/f'production-mean-{attempt}.json',mean.model_dump(mode='json',exclude_none=True))
    else:
        implementation=verify_encoder_implementation(E5)
        with open_runtime_engine(Settings(),'pce10-actual-source-retrieval',purpose='read') as engine:
            normal=retrieve_source_definitions(engine,inputs,usage_id=selected['usage_id'],target_ids=selected['target_ids'],budget=5,channel_budget=11,readings=(DefinitionReading(target_id='nist-normal-location',outcome='ambiguous',evidence=('gs-normal-usage','nist-normal-location'),reason='The passage describes normal location properties, but does not establish the binomial approximation parameter mapping or a standard-normal definition.'),))
            write(RAW/f'production-normal-{attempt}.json',normal.model_dump(mode='json',exclude_none=True))
            cached=tuple(EncodedVector(**v) for v in normal.retrieval_report['vectors'])
            mean=retrieve_source_definitions(engine,mean_inputs,usage_id=selected['mean_usage_id'],target_ids=selected['target_ids'],budget=5,channel_budget=11,cached_vectors=cached,readings=(DefinitionReading(target_id='nist-mean-definition',outcome='applicable_definition',evidence=('nist-sample-mean-usage','nist-mean-definition'),reason='NIST explicitly names the sample mean in the confidence-limit formula context and separately defines the mean as the sum of data points divided by their count. This does not identify the unknown population mean with its sample estimate.'),))
            write(RAW/f'production-mean-{attempt}.json',mean.model_dump(mode='json',exclude_none=True))
    comparison_inputs=inputs.model_copy(update={'question':selected['questions']['comparison'],'policy_id':'source-qualified-literal-fields-1'})
    left=ClauseReading(passage_id='nist-normal-location',fields=(ClauseField(dimension='condition',lexical_value='For a normal distribution',evidence=('nist-normal-location',)),ClauseField(dimension='object',lexical_value='the mean',evidence=('nist-normal-location',)),ClauseField(dimension='action',lexical_value='use the mean as the location estimator',evidence=('nist-normal-location',))))
    right=ClauseReading(passage_id='nist-cauchy-exception',fields=(ClauseField(dimension='condition',lexical_value='for the Cauchy distribution',evidence=('nist-cauchy-exception',)),ClauseField(dimension='object',lexical_value='the mean',evidence=('nist-cauchy-exception',)),ClauseField(dimension='action',lexical_value='the mean is useless as a measure of the typical value',evidence=('nist-cauchy-exception',))))
    comparison=compare_clauses(comparison_inputs,left=left,right=right)
    write(RAW/f'production-comparison-{attempt}.json',comparison.model_dump(mode='json',exclude_none=True))
    dossier_inputs=inputs.model_copy(update={'question':selected['questions']['dossier'],'policy_id':'explicit-source-membership-1','dependencies':(*inputs.dependencies,mean.product_id,comparison.product_id,normal.product_id),'coverage_limits':(*inputs.coverage_limits,'Membership/roles below are explicitly supplied producer readings, unassessed unless a separate independent group assessment qualifies them. Upstream product references establish traceability, not membership truth.')})
    members=[]
    for pid,role,sense,upstream in (('nist-mean-definition','definition','sample-arithmetic-mean',mean.product_id),('nist-normal-location','usage','mean-as-location',comparison.product_id),('nist-cauchy-exception','exception','mean-as-location',comparison.product_id),('gs-normal-usage','unresolved_sense','normal-parameter-context',normal.product_id)):
        meaning=dict(passage_id=pid,role=role,sense=sense,scope=SCOPE,relation_product_id=upstream,qualification='proposed')
        members.append(DossierMember(member_id='supplied-membership:'+sha256(canonical_bytes(meaning)).hexdigest(),**meaning))
    dossier=assemble_dossier(dossier_inputs,root_id='provisional-sense:mean-location',members=members)
    write(RAW/f'production-dossier-{attempt}.json',dossier.model_dump(mode='json',exclude_none=True))
    reports=(normal,mean,comparison,dossier)
    result=dict(outcome='passed',scope='retained actual E5/PostgreSQL score replay and deterministic private composition' if replay_from else 'actual E5/PostgreSQL retrieval and deterministic private structural composition only',quality_claim='not_established',public_admission='not_run',implementation=implementation,profile=asdict(E5),wall_seconds=time.perf_counter()-start,products=[dict(product_id=r.product_id,kind=r.kind,input_digest=r.inputs.identity) for r in reports],source_selection_sha256=sha256((RAW/f'production-input-{attempt}.json').read_bytes()).hexdigest(),producer_readings='Explicitly supplied source interpretations; not independent reference answers or C judgments.',defaults_activated=False,retained_score_replay_from=replay_from,provider_execution='not_run' if replay_from else 'passed')
    write(RAW/f'production-produced-{attempt}.json',result)
    print(json.dumps(result),flush=True)


def persist(attempt,release):
    from types import SimpleNamespace
    from corpus_structure.core.evidence import config_key
    from corpus_structure.core.provenance import code_commit
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.structural_products import StructuralProductsConfig, StructuralProductsMethod
    from corpus_structure.orchestrate.registry import canonical_numbers
    from corpus_structure.semantic._operation_calls import initialize_source_project
    from corpus_structure.semantic._operation_ids import ProjectId,RealizationId,ReleaseId
    from corpus_structure.semantic.domain_operations import consolidate_cut
    from corpus_structure.semantic.observations import bind_result
    from corpus_structure.semantic.operations import OperationBinding,create_run,start_run,record_method,create_task,claim_tasks,complete_task,seal_cut,end_source_run
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding
    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
    from corpus_structure.semantic.structural_products import StructuralProductReport
    settings=Settings(); method=StructuralProductsMethod()
    reports=tuple(StructuralProductReport.model_validate_json((RAW/f'production-{name}-{attempt}.json').read_bytes()) for name in ('normal','mean','comparison','dossier'))
    input_realization='pce-structure-input:'+release
    with open_runtime_engine(settings,'pce10-private-production',purpose='write') as engine:
        with engine.begin() as conn:
            prepared=open_release(conn,release)
            runtime=prepare_runtime_binding(prepared)
            persist_runtime_binding(conn,prepared,runtime)
            initialize_source_project(conn,project_id=ProjectId(PROJECT),release_id=ReleaseId(release),realization_id=RealizationId(input_realization),projection_context=prepared)
            before=dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':PROJECT}).mappings().one())
            binding=OperationBinding(release,input_realization,0,canonical_bytes({'structural_cohort':sha256((RAW/f'production-input-{attempt}.json').read_bytes()).hexdigest(),'private_producer_reports':tuple(r.product_id for r in reports)}))
            run=create_run(conn,project_id=PROJECT,binding=binding,kind='full',options={'structural_private':True},code_commit=code_commit(),prepared=prepared,runtime_binding=runtime)
            start_run(conn,run,prepared=prepared)
        tasks=[]
        for index,report in enumerate(reports):
            cfg=StructuralProductsConfig(report=report,structural_input_digest=report.inputs.identity)
            params=cfg.model_dump(mode='json',exclude_none=True)
            key=config_key(method.name,method.version,canonical_numbers(params))
            unit_key=f'structural:{index}:{report.kind}'
            with engine.begin() as conn:
                config=record_method(conn,method,'three-source-'+str(index),params,key,prepared=prepared)
                task=create_task(conn,run_id=run,config_id=config,stage='structural',unit_type='run',unit_key=unit_key,input_hash=sha256(method.input_digest(None,cfg).bytes).hexdigest())
                claim=claim_tasks(conn,run_id=run,config_id=config,holder='pce10-three-source',prepared=prepared)[0]
            ref=UnitRef(TaskUnitType.RUN,unit_key=unit_key)
            result=method.run((SimpleNamespace(ref=ref),),cfg,None)[0]
            with engine.begin() as conn:
                taskrow=conn.execute(text('SELECT input_hash,invocation_key FROM ops.task WHERE id=:id'),{'id':task}).mappings().one()
                envelope=bind_result(prepared,source=unit_key,method=method.name,operation_version=method.version,configuration_hash=key,input_hash=taskrow['input_hash'],invocation_key=taskrow['invocation_key'],result=result).model_dump(mode='json')
                completion=complete_task(conn,task_id=task,attempt=claim.attempt,holder=claim.holder,prepared=prepared,observations=(),outcome='done',envelope=envelope)
            tasks.append(dict(task_id=task,product_id=report.product_id,receipt=completion.model_dump(mode='json')))
        with engine.begin() as conn:
            cut=seal_cut(conn,run,'structural-final',final=True)
            end_source_run(conn,run,prepared=prepared)
        completed=consolidate_cut(engine,cut,f'pce-structure-result:{run}')
        with engine.connect() as conn:
            after=dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':PROJECT}).mappings().one())
        assert before==after,'private production changed defaults'
    result=dict(outcome='passed',run_id=run,cut_id=cut,release_id=release,runtime_id=runtime.runtime_id,tasks=tasks,project_defaults_before=before,project_defaults_after=after,result_realization_id=completed.realization_id,quality_claim='not_established',public_admission='not_run',defaults_activated=False)
    write(RAW/f'production-persisted-{attempt}.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('freeze','produce','persist'));parser.add_argument('--attempt',default='001');parser.add_argument('--release');parser.add_argument('--replay-from');args=parser.parse_args()
    if not args.attempt.isdigit():parser.error('attempt must be digits')
    RAW.mkdir(exist_ok=True)
    if args.phase=='freeze':freeze(args.attempt)
    elif args.phase=='produce':produce(args.attempt,args.replay_from)
    else:
        if not args.release:parser.error('persist requires --release')
        persist(args.attempt,args.release)
