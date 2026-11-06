"""Authenticate exact retained product equality before transporting independent judgments."""
from pathlib import Path
from hashlib import sha256
import argparse
import json
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralProductReport

HERE = Path(__file__).resolve().parent

def load(folder):
    manifest_path=folder/'manifest.json'
    manifest=json.loads(manifest_path.read_bytes())
    if manifest['capture_scope']!='completed_sealed_run' or manifest['run']['status']!='finished' or not manifest['run']['sealed']:
        raise ValueError('transport requires completed sealed immutable capture')
    tasks=[t for t in manifest['tasks'] if t['method']=='structure.definition_components' and t['has_task_result']]
    if len(tasks)!=1:
        raise ValueError('require one exact named construction task')
    task=tasks[0]; path=folder/task['raw_file'];content=path.read_bytes()
    if sha256(content).hexdigest()!=task['raw_sha256']:
        raise ValueError('captured raw envelope digest differs')
    raw=json.loads(content)
    report=StructuralProductReport.model_validate(raw['body']['structural_product'])
    return manifest,task,raw,report,dict(path=str(path.relative_to(Path.cwd())),sha256=sha256(content).hexdigest())

def main():
    p=argparse.ArgumentParser();p.add_argument('--current',required=True);p.add_argument('--out',required=True);args=p.parse_args()
    old,ot,ob,op,opin=load(HERE/'run152-current-named001')
    new,nt,nb,np,npin=load(HERE/args.current)
    if canonical_bytes(ob['body']['structural_product'])!=canonical_bytes(nb['body']['structural_product']):
        raise ValueError('actual complete structural product changed; semantic re-authoring required')
    assert op==np and op.product_id==np.product_id
    assert op.definition_components is not None and np.definition_components is not None
    mapping=[dict(original=c.component_id,current=c.component_id,term=c.term.model_dump(mode='json'),content=c.content.model_dump(mode='json'),interpretation=c.interpretation,scope=c.scope) for c in op.definition_components.components]
    receipt=dict(protocol='wce-exact-component-assessment-transport-1',outcome='passed',original=old['run'],current=new['run'],original_cut=old['completed_result'],current_cut=new['completed_result'],original_task=ot,current_task=nt,inputs=[opin,npin],product_id=np.product_id,complete_report_bytes_equal=True,all_original_source_pins_equal=True,all_source_text_and_native_context_equal=True,components=mapping,component_count=len(mapping),semantic_authoring_changed=False,scope='Exact report/source/meaning equality permits explicit frame rebinding only; original authored bytes, source fidelity limits, actors and disagreements remain unchanged. Producing releases/runtimes remain distinct.')
    dest=HERE/args.out
    with dest.open('xb') as stream: stream.write(canonical_bytes(receipt)+b'\n')
    print(json.dumps(dict(outcome='passed',components=len(mapping),product_id=np.product_id,current_run=new['run']['id'])))

if __name__=='__main__':main()
