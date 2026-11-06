"""Check immutable independent inputs and refuse borrowing narrow support for larger effects."""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, create_run, create_task, start_run
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
RAW=Path('/home/paul/corpus-structure/docs/design_review/evidence/2026-11-06_wce-definition-linking')


def quoted_spans(value,text,path=()):
    findings=[]
    if isinstance(value,dict):
        if {'start','end','text'} <= value.keys() and type(value['start']) is int and type(value['end']) is int and isinstance(value['text'],str):
            findings.append(dict(path=list(path),start=value['start'],end=value['end'],exact=0 <= value['start'] < value['end'] <= len(text) and text[value['start']:value['end']]==value['text']))
        for k,v in value.items():findings.extend(quoted_spans(v,text,(*path,k)))
    elif isinstance(value,list):
        for i,v in enumerate(value):findings.extend(quoted_spans(v,text,(*path,i)))
    return findings


def main():
    output=HERE/'publication001'
    inputs={name:json.loads((RAW/name).read_bytes()) for name in ('author-a.json','author-b.json','author-c.json','output-author-a.json','output-author-b.json','output-author-c.json','source-author-input.json')}
    hashes={name:sha256((RAW/name).read_bytes()).hexdigest() for name in inputs}
    parent_checks=[]
    for name in ('author-c.json','output-author-c.json'):
        for parent in inputs[name]['parent_authors']:
            filename=Path(parent['path']).name
            assert hashes[filename]==parent['sha256'],'independent parent raw bytes changed'
            parent_checks.append(dict(adjudicator=name,parent=filename,sha256=hashes[filename],matched=True))
    source_text=inputs['source-author-input.json']['passages'][0]['text']
    quote_checks={name:quoted_spans(payload,source_text) for name,payload in inputs.items() if name!='source-author-input.json'}
    # Preserve an author's unrelated source-reference mistakes rather than silently repair them.
    # Every quote used for the narrow expected attachment was checked by the importer itself.
    manifest=dict(raw_file_sha256=hashes,parent_checks=parent_checks,quote_checks=quote_checks,quote_mismatches={name:[q for q in checks if not q['exact']] for name,checks in quote_checks.items()},mapping=dict(original_source_view=48,retained_source_view=53,source_text_identity=True,original_author_product='structural:45099b3cbac95b355fda831369def0d264e466155d7cf466f19ac197f4e923e1',final_product='structural:eb4201f8a571319f953f1194f85fa04b61d0742a9246e9cb0dfdc37e4abc7b71',component_payload_identical=True,scope='Only identical located component; whole-report stages and unassessed facets not promoted.'))
    (output/'independent-input-provenance.json').write_bytes(canonical_bytes(manifest)+b'\n')
    receipt=json.loads((output/'result.json').read_bytes());frame=json.loads((output/'frame.json').read_bytes());settings=Settings()
    with open_runtime_engine(settings,'wce-component-native-refusal',purpose='write') as engine:
        controls=[]
        for name,changes in (('component-support-cannot-authorize-applicability',dict(policy_id='independent-witnessed-applicability-1')),('wrong-component-cannot-borrow-support',dict(component_id='0'*64))):
            with engine.begin() as conn:
                job=dict(conn.execute(select(table('ops.run')).where(table('ops.run').c.id==120)).mappings().one());task=dict(conn.execute(select(table('ops.task')).where(table('ops.task').c.id==309)).mappings().one())
                prepared=open_release(conn,job['release_id']);runtime=runtime_binding_for_run(conn,120,prepared)
                positive=conn.scalar(select(table('ops.run').c.dependencies).where(table('ops.run').c.id==receipt['publication_run']))
                admission=dict(json.loads(bytes(positive))['structural_admission'][0])
                admission.update(changes);dependencies=json.loads(bytes(job['dependencies']));dependencies['structural_admission']=[admission]
                run=create_run(conn,project_id=job['project_id'],binding=OperationBinding(job['release_id'],job['input_realization_id'],job['input_revision'],canonical_bytes(dependencies)),kind='full',options=job['options'],code_commit=job['code_commit'],guideline=job['guideline'],phase=job['phase'],prepared=prepared,runtime_binding=runtime)
                start_run(conn,run,prepared=prepared)
                selected=create_task(conn,run_id=run,config_id=task['method_config_id'],stage=task['stage'],unit_type=task['unit_type'],input_hash=task['input_hash'],unit_id=task['unit_id'],unit_key=task['unit_key'],packet_hash=task['packet_hash'])
                assert conn.scalar(select(table('ops.task').c.reused_task_id).where(table('ops.task').c.id==selected))==309
            try:
                finalize_bound_run(engine,run,'wce04-refused-component-publication:'+str(run))
            except DBAPIError as error:
                reason=str(error.orig).splitlines()[0]
                expected_reason='policy is not released' if name=='component-support-cannot-authorize-applicability' else 'cannot resolve exact current custody'
                assert expected_reason in reason,'refusal did not isolate the intended native guard'
                controls.append(dict(control=name,outcome='refused',run_id=run,selected_task=selected,origin_task=309,sqlstate=getattr(error.orig,'sqlstate',None),reason=str(error.orig).splitlines()[0]))
            else:
                raise AssertionError('native publication wrongly accepted '+name)
            with engine.connect() as conn:
                count=conn.execute(select(table('data.structural_assertion').c.assertion_id).where(table('data.structural_assertion').c.selected_task_id==selected)).all()
                assert not count
        (output/'native-refusal-controls.json').write_bytes(canonical_bytes(dict(outcome='passed',controls=controls,producer_reexecuted=False))+b'\n')
        print(json.dumps(dict(outcome='passed',controls=controls,quote_mismatch_counts={n:len(v) for n,v in manifest['quote_mismatches'].items()})))


if __name__=='__main__':main()
