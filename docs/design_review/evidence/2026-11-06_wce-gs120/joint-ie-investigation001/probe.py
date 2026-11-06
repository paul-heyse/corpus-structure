"""I01: compare joint typed graph decoding on actual failed independent-role windows."""
from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
import json,os,time
from corpus_structure.methods.gliner import GlinerProfile,load_model
from corpus_structure.semantic.observations import source_python
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
body=json.loads((ROOT/'assessment/run139-final001/task-544.json').read_bytes())['body']
detail=source_python(body['parse_detail'])
reports=[]
for report in detail['raw_reports']:
    raw=json.loads(report['raw_json'])
    if raw.get('relation_extraction',{}).get('term is defined or explained by'):
        reports.append(report)
    if len(reports)==3:break
assert len(reports)==3
profile=json.loads((ROOT/'baseline003/gs120-all120-pages/configuration.json').read_bytes())['definition']['profile']
profile['snapshot']=Path(profile['snapshot']);profile['artifact_hashes']=tuple(tuple(x) for x in profile['artifact_hashes'])
profile=GlinerProfile(**profile)
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
inputs=[dict(passage_id=r['passage_id'],window_start=r['window_start'],window_end=r['window_end'],text=r['preparation']['consumed_text'],baseline_raw=json.loads(r['raw_json'])) for r in reports]
(OUT/'inputs.json').write_text(json.dumps(inputs,ensure_ascii=False)+'\n')
from gliner2.joint_ie import JointIE,JointIEConfig
model,effective=load_model(profile)
joint=JointIE(model)
schema=(joint.create_schema().entities(['defined term or expression','defining text or formula']).relation('term is defined or explained by','defined term or expression','defining text or formula').no_self_loops())
config=JointIEConfig(optimizer='beam',beam_size=32,top_k_entities=32,top_k_roles=12,relation_pair_cap=128,max_len=None)
results=[]
try:
 for item in inputs:
    started=time.monotonic();result=joint.extract(item['text'],schema,config=config)
    value=result.to_dict()
    for entity in result.entities:
        assert item['text'][entity.start:entity.end]==entity.text
    record=dict(passage_id=item['passage_id'],window_start=item['window_start'],window_end=item['window_end'],inference_seconds=time.monotonic()-started,result=value)
    results.append(record)
    print(json.dumps(dict(passage_id=item['passage_id'],entities=len(result.entities),relations=len(result.relations),feasible=result.feasible)),flush=True)
 (OUT/'result.json').write_text(json.dumps(dict(outcome='passed',checkpoint=profile.checkpoint,revision=profile.revision,effective_profile=json.loads(effective),configuration=asdict(config),schema=schema.to_dict(),results=results,scope='Actual selected invalid-role windows; coherence/software only, source correctness and efficacy unassessed'),ensure_ascii=False)+'\n')
except BaseException as error:
 (OUT/'failure.json').write_text(json.dumps(dict(outcome='failed',type=type(error).__name__,message=str(error),completed=results),ensure_ascii=False)+'\n');raise
