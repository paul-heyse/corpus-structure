"""Exact pinned checkpoint located attribute/attachment check on retained source text."""
from dataclasses import asdict
from pathlib import Path
import json
import yaml

from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig, definition_pack, decode_definition_components
from corpus_structure.methods.gliner import GlinerInput, GlinerProfile
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.semantic.structural_products import StructuralPassage


def main():
    root=Path(__file__).resolve().parents[4]
    saved=root/'docs/design_review/evidence/2026-11-06_wce-candidate-foundation/raw/source-author-input-002.json'
    source=json.loads(saved.read_text())['passages'][0]
    start=source['text'].index('The normal density function with parameters')
    end=source['text'].index('(In Chapter 6, we will show',start)
    passage=StructuralPassage(passage_id=source['passage_id'],source_ref=source['source_ref'],start=start,end=end,text=source['text'][start:end],scope=source['scope'])
    config=yaml.safe_load((root/'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['default']
    profile=GlinerProfile(snapshot=Path(config['snapshot']),checkpoint=config['checkpoint'],revision=config['revision'],artifact_hashes=tuple(tuple(v) for v in config['artifact_hashes']),timeout_seconds=240)
    cfg=DefinitionComponentsConfig()
    pack=definition_pack('provider-capability-only',cfg)
    result={'source_file':str(saved.relative_to(root)),'passage':passage.model_dump(mode='json'),'profile_fingerprint':profile.fingerprint,'schema':pack.declaration_json,'standing':'private_provider_capability_check','independent_semantic_support':'not_assessed'}
    worker=GlinerWorker(profile)
    try:
        reply,=worker.extract(pack,(GlinerInput('definition-target:'+passage.identity,passage.identity,passage.text),),threshold=0.3,overlap_policy='flat')
        result['raw']=asdict(reply)
        try:
            components=decode_definition_components(reply.raw,passage,cfg)
            result.update(outcome='passed',component_count=len(components),components=[c.model_dump(mode='json') for c in components],claim='Exact public API and source-coordinate adapter executed; output count does not establish semantic benefit.')
        except Exception as error:
            result.update(outcome='failed',error_type=type(error).__name__,error=str(error))
    except Exception as error:
        result.update(outcome='failed',error_type=type(error).__name__,error=str(error))
    finally:
        worker.close()
        (Path(__file__).parent/'provider-result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in {'outcome','error','error_type','component_count'}}))


if __name__=='__main__':
    main()
