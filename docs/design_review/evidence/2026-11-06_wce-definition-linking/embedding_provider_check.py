"""Actual E5 execution/reuse over retained statistics text; no semantic grade."""
from dataclasses import asdict
from pathlib import Path
import json
from corpus_structure.methods.contextual_embeddings import ContextInput, E5, encode_contexts, identity

HERE=Path(__file__).resolve().parent

def main():
    source=json.loads((HERE/'normal-native-view-53.json').read_bytes())
    result=json.loads((HERE.parent/'2026-11-06_wce04-located-definitions/annotation-composition-result.json').read_bytes())
    component=result['components'][0]
    literal=component['term']['text']
    context=source['text']
    start=context.index(literal)
    binding=identity('retained-source-provider-input',source['ref'])
    representation=identity('located-definition-representation',component)
    query_start=context.index('standard normal')
    query_literal='standard normal'
    items=(
        ContextInput('source-usage:'+str(query_start),binding,'query',query_literal,context,query_start,query_start+len(query_literal)),
        ContextInput(component['component_id'],binding,'document',literal,context,start,start+len(literal),representation_digest=representation),
    )
    encoded=encode_contexts(items,E5,local_files_only=True)
    replay=encode_contexts(items,E5,local_files_only=True,cached_vectors=encoded.vectors)
    # EncoderResult emits fresh vectors separately from authenticated reused IDs.
    replay_ids={v.vector_id for v in replay.vectors} | set(replay.reused_vector_ids)
    assert replay_ids=={v.vector_id for v in encoded.vectors}
    assert set(replay.reused_vector_ids)=={v.vector_id for v in encoded.vectors if v.object_id==component['component_id']}
    output=dict(outcome='passed',profile=asdict(E5),result=asdict(encoded),replay=asdict(replay),
                scope='actual provider and representation-vector reuse only; native target binding and semantic relationship assessment are separate obligations')
    (HERE/'embedding-provider-result.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'outcome':'passed','vectors':len(encoded.vectors),'dimension':E5.dimension,'reused':len(replay.reused_vector_ids)}))

if __name__=='__main__':main()
