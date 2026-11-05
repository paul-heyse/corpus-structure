"""Cold/warm actual encoder comparison; no corpus correctness or performance claim."""
import json
from dataclasses import replace
from pathlib import Path

from corpus_structure.methods.contextual_embeddings import E5,QWEN,ContextInput,encode_contexts
from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input

if __name__=='__main__':
    root=Path(__file__).parent/'raw'
    _, targets=registry_input((RegistryTarget(target_id='target:normal',label='normal distribution',
        description='A Gaussian probability distribution.'),))
    target=targets[0]
    inputs=(ContextInput('usage:normal','constructed:cpu-cache','query','normal distribution',
                'The normal distribution has a bell-shaped density.',4,23),
            ContextInput(target.target_id,target.source_binding,'document',target.label,
                target.label+'\n'+target.description,0,len(target.label),
                representation_digest=target.representation_digest))
    for profile in (E5,QWEN):
        name='e5' if profile is E5 else 'qwen'
        try:
            cold=encode_contexts(inputs,profile)
            document=next(v for v in cold.vectors if v.object_id==target.target_id)
            warm=encode_contexts(inputs,profile,cached_vectors=(document,))
            assert len(cold.vectors)==2 and len(warm.vectors)==1
            assert warm.reused_vector_ids==(document.vector_id,)
            assert warm.vectors[0].values==cold.vectors[0].values
            mismatch=encode_contexts(inputs,profile,cached_vectors=(replace(document,input_digest='0'*64),))
            assert len(mismatch.vectors)==2 and mismatch.reused_vector_ids==()
            result=dict(outcome='passed',profile_id=profile.profile_id,implementation=cold.implementation,
                        cold_encoded=2,warm_encoded=1,warm_reused=warm.reused_vector_ids,
                        mismatch_encoded=2,mismatch_reused=0,
                        scope='Constructed native cache boundary only; original task/runtime admission is separately native-tested.')
        except Exception as error:
            result=dict(outcome='failed',error=f'{type(error).__name__}: {error}')
        with (root/f'contextual-encoder-cache-{name}-001.json').open('x') as out:
            out.write(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
