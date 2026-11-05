"""Publish exact retained structural origins through ordinary sealed-cut consolidation.

No models run and no judgments are authored here. Explicit frozen native witness
bindings feed the existing common publication batch; project defaults stay unchanged.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from sqlalchemy import text
from corpus_structure.core.provenance import code_commit
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationBinding, create_run, create_task, seal_cut, start_run
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.settings import Settings

RAW = Path(__file__).with_name('raw')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--producer-run',type=int,required=True);parser.add_argument('--bindings',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    references=json.loads((RAW/args.bindings).read_bytes()); witnesses=references['structural_admission']
    with open_runtime_engine(Settings(),'pce-public-ordinary-run',purpose='write') as engine:
        with engine.begin() as conn:
            source=dict(conn.execute(text('SELECT * FROM ops.run WHERE id=:id'),{'id':args.producer_run}).mappings().one())
            if source['status']!='finished' or not source['sealed'] or source['release_id']!=references['release_id']:
                raise ValueError('public witnesses require the completed selected producer release')
            prepared=open_release(conn,source['release_id']); runtime=prepare_runtime_binding(prepared)
            if runtime.runtime_id!=source['runtime_id']:
                raise ValueError('runtime changed; cheaply import retained reports before public qualification')
            persist_runtime_binding(conn,prepared,runtime)
            before=dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':source['project_id']}).mappings().one())
            dependencies=json.loads(source['dependencies']);dependencies['structural_admission']=witnesses
            binding=OperationBinding(source['release_id'],source['input_realization_id'],source['input_revision'],canonical_bytes(dependencies))
            run=create_run(conn,project_id=source['project_id'],binding=binding,kind=source['kind'],options={**source['options'],'structural_private':True},code_commit=code_commit(),prepared=prepared,runtime_binding=runtime)
            start_run(conn,run,prepared=prepared)
            tasks=tuple(dict(row) for row in conn.execute(text("SELECT t.* FROM ops.cut_task member JOIN ops.task t ON t.id=member.task_id JOIN ops.completed_result completed ON completed.cut_id=member.cut_id WHERE completed.run_id=:run AND t.unit_type='run' ORDER BY t.id"),{'run':args.producer_run}).mappings())
            selected=[]
            for task in tasks:
                target=create_task(conn,run_id=run,config_id=task['method_config_id'],stage=task['stage'],unit_type=task['unit_type'],unit_id=task['unit_id'],unit_key=task['unit_key'],packet_hash=task['packet_hash'],input_hash=task['input_hash'])
                actual=conn.execute(text('SELECT status,reused_task_id FROM ops.task WHERE id=:t'),{'t':target}).mappings().one()
                if actual['status']!='reused' or actual['reused_task_id']!=(task['reused_task_id'] or task['id']):
                    raise ValueError('publication did not reuse its exact selected producer origin')
                selected.append({'task_id':target,'origin_task_id':actual['reused_task_id']})
            cut=seal_cut(conn,run,'structural-public-final',final=True)
        result=consolidate_cut(engine,cut,f'pce-structure-public-result:{run}')
        with engine.connect() as conn:
            rows=[dict(row) for row in conn.execute(text('SELECT assertion_id,claim_id,origin_task_id,product_id,product_kind,policy_id,set_id,c_pass_id FROM data.structural_assertion WHERE release_id=:release AND realization_id=:result ORDER BY assertion_id'),{'release':source['release_id'],'result':result.realization_id}).mappings()]
            after=dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':source['project_id']}).mappings().one())
        assert before==after,'publication activated project defaults'
        assert len(rows)==len(witnesses),'missing required selected public statement'
    receipt=dict(outcome='passed',run_id=run,cut_id=cut,producer_run_id=args.producer_run,release_id=source['release_id'],runtime_id=runtime.runtime_id,result_realization_id=result.realization_id,selected_origins=selected,assertions=rows,defaults_activated=False,assessment_scope='independently reviewed exposed-development005; no unseen quality claim')
    with (RAW/args.out).open('xb') as out:out.write(canonical_bytes(receipt)+b'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
