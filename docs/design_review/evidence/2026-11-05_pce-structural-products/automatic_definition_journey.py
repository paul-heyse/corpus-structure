"""Bounded actual GLiNER applicability component; normal RUN execution is separate."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import time

from corpus_structure.methods.definition_applicability import pair_input, decode_applicability
from corpus_structure.methods.gliner import GlinerPack
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralInput

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]

def component(attempt):
    import yaml
    frozen=json.loads((HERE/'raw/production-input-002.json').read_bytes())
    inputs=StructuralInput.model_validate(frozen['inputs'])
    config=json.loads((HERE.parent/'2026-11-05_pce-local-capabilities/raw/parser-corpus-003-configuration.json').read_bytes())['configs']['extract.m1_candidates']
    profile=M1Config.model_validate(config).profile()
    path=ROOT/'python/corpus-structure/src/corpus_structure/model/semantic/observations.yaml'
    enum=yaml.safe_load(path.read_text())['enums']['StructuralDefinitionReadingOutcomeValue']['permissible_values']
    labels={name:item.get('description',name) for name,item in enum.items()}
    pack=GlinerPack.from_declaration('unreleased-component:'+sha256(path.read_bytes()).hexdigest(),{'classifications':[{'task':'applicability','labels':labels}]},version='native-combined-v2')
    pairs=(('gs-normal-usage','nist-normal-location'),('nist-sample-mean-usage','nist-mean-definition'),('nist-sample-mean-usage','forbes-independence-definition'))
    requests=tuple(pair_input(inputs,u,t,pack) for u,t in pairs)
    started=time.perf_counter()
    worker=GlinerWorker(profile)
    try:
        reports=worker.extract(pack,requests)
    finally:
        worker.close()
    result={'outcome':'passed','scope':'actual GLiNER classification component, not ordinary registered/native task qualification','profile':asdict(profile),'pack':asdict(pack),'requests':[asdict(r) for r in requests],'reports':[asdict(r) for r in reports],'readings':[decode_applicability(r.raw,target_id=t,usage_id=u,allowed=frozenset(labels)).model_dump(mode='json') for (u,t),r in zip(pairs,reports,strict=True)],'elapsed_seconds':time.perf_counter()-started,'quality_claim':'not_independently_assessed','worker_settled':worker.pid is None}
    from pydantic_core import to_jsonable_python
    target=HERE/f'raw/automatic-component-{attempt}.json'
    with target.open('xb') as out:out.write(canonical_bytes(to_jsonable_python(result))+b'\n')
    print(json.dumps({'outcome':result['outcome'],'elapsed_seconds':result['elapsed_seconds'],'categories':[r['outcome'] for r in result['readings']],'worker_settled':result['worker_settled']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='001');args=parser.parse_args();component(args.attempt)
