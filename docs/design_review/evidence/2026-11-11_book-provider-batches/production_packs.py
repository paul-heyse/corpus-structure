"""Actual released question schemas through the native CPU GLiNER batch boundary."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import yaml

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, _json
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.pm2_gliner_classification import ClassificationProfile
from corpus_structure.semantic.interpretation_questions import (
    CHARACTERIZATION_QUESTION_INPUT, compile_question_families, declared_families,
)
from corpus_structure.semantic.types import SourceArtifact
from compare import difference

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent

def main():
    source=ROOT/'python/corpus-structure/src/corpus_structure/model/semantic/characterization-questions.yaml'
    families=declared_families(compile_question_families((SourceArtifact(CHARACTERIZATION_QUESTION_INPUT,source.read_bytes()),)))
    texts=['Every random variable may have a mean, but not every variable has a finite variance.',
           'Definition: The expectation of a discrete random variable is the sum of its values weighted by their probabilities. For example, a fair die has expectation 3.5.',
           'Every random variable may have a mean, but not every variable has a finite variance.']
    config=yaml.safe_load((ROOT/'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['default']
    profile=ClassificationProfile(provider='gliner',device='cpu',profile=M1Config.model_validate(config).profile()).profile
    groups=[[0],[1],[2],[0,1,2],[2,1,0],[0,2],[1,0]]
    output=dict(profile=asdict(profile),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),texts=texts,groups=groups,packs={})
    worker=GlinerWorker(profile)
    try:
        for name in ('character_gliner_cues_v1','character_gliner_function_v1'):
            family=families[name]
            if name.endswith('cues_v1'):
                declaration=dict(entities={q.key:q.instructions for q in family.questions})
                version='native-local-v1'
            else:
                (q,)=family.questions
                declaration=dict(classifications=[dict(task=q.key,prompt=q.instructions,labels={o.key:o.criterion for o in q.options},multi_label=True,cls_threshold=max(.5,q.minimum_probability or 0))])
                version='native-combined-v2'
            pack=GlinerPack('bep-production-schema-probe',_json(declaration),version)
            result=dict(family=family.model_dump(mode='json'),pack=asdict(pack),threshold=.5,overlap_policy='flat',calls=[])
            output['packs'][name]=result
            for group in groups:
                inputs=tuple(GlinerInput('source-context-'+str(i),hashlib.sha256(texts[i].encode()).hexdigest(),texts[i],operation='text.model_characterization/2:'+family.digest) for i in group)
                reports=worker.extract(pack,inputs,threshold=.5,overlap_policy='flat')
                assert len(reports)==len(inputs)
                for ordinal,(item,report) in enumerate(zip(inputs,reports,strict=True)):
                    assert report.context_id==item.context_id and report.context_digest==item.context_digest
                    assert report.member_ordinal==ordinal and report.batch_receipt_json
                result['calls'].append(dict(members=group,inputs=[asdict(x) for x in inputs],reports=[asdict(r) for r in reports]))
                (HERE/'raw/production-packs.json').write_text(json.dumps(output,indent=2,default=str))
                print(name,group,'complete',flush=True)
    finally:
        worker.close()
    summary={}
    for name,result in output['packs'].items():
        singles={c['members'][0]:json.loads(c['reports'][0]['raw_json']) for c in result['calls'][:3]}
        comparisons=[]
        for call in result['calls']:
            for member,report in zip(call['members'],call['reports'],strict=True):
                raw=json.loads(report['raw_json'])
                mismatch,numeric=difference(singles[member],raw)
                comparisons.append(dict(members=call['members'],member=member,discrete_mismatches=mismatch,max_float_abs_difference=numeric))
                if 'entities' in raw:
                    for values in raw['entities'].values():
                        for entity in values:
                            assert texts[member][entity['start']:entity['end']]==entity['text']
                            assert entity['confidence']>=.5
        summary[name]=dict(comparisons=comparisons)
    (HERE/'raw/production-summary.json').write_text(json.dumps(summary,indent=2))
    for name, value in summary.items():
        print(name,'discrete mismatches',sum(len(c['discrete_mismatches']) for c in value['comparisons']),'maxfloat',max(c['max_float_abs_difference'] for c in value['comparisons']))

if __name__=='__main__':main()
