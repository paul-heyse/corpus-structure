"""Actual pinned CPU encoder boundary check; constructed inputs, not corpus quality evidence."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from huggingface_hub import snapshot_download
from corpus_structure.methods.contextual_embeddings import E5,QWEN,ContextInput,encode_contexts

from corpus_structure.semantic.contextual_retrieval import target_representation

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    attempt=parser.parse_args().attempt
    if not attempt.isdigit():
        parser.error('attempt must contain digits')
    root=Path(__file__).parent/'raw'
    target=target_representation('target:normal','constructed:cpu-contract','normal distribution',
        'normal distribution: Gaussian family of probability distributions.')
    for profile in (E5,QWEN):
        name='e5' if profile is E5 else 'qwen'
        try:
            snapshot_download(profile.model,revision=profile.revision,
                allow_patterns=['*.json','*.safetensors','*.txt','1_Pooling/*','2_Normalize/*'])
            result=encode_contexts((ContextInput('usage:normal','constructed:cpu-contract','query',
                'normal distribution','The normal distribution has a bell-shaped density.',4,23),
                ContextInput('target:normal','constructed:cpu-contract','document','normal distribution',
                'normal distribution: Gaussian family of probability distributions.',0,19,
                representation_digest=target.representation_digest)),profile)
            report={'outcome':'passed','profile':asdict(profile),'implementation':result.implementation,
                    'inputs':[asdict(i) for i in result.inputs],
                    'vectors':[{'vector_id':v.vector_id,'dimension':len(v.values),'norm':sum(x*x for x in v.values)**.5}
                               for v in result.vectors],
                    'scope':'Constructed native CPU boundary only; no source-corpus retrieval or quality claim.'}
        except Exception as error:
            report={'outcome':'failed','profile':asdict(profile),'error':f'{type(error).__name__}: {error}'}
        with (root/f'contextual-encoder-{name}-{attempt}.json').open('x') as output:
            output.write(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
