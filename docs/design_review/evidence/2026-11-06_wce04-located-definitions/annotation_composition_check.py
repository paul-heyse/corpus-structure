"""Current domain rules over actual retained native annotation/source products."""
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig, retained_annotation_components
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.structural_products import ExternalSourceRef, StructuralInput, StructuralPassage


def main():
    root=Path(__file__).resolve().parents[4]
    # During isolated implementation the root holds the authenticated read receipts.
    authority=root/'docs/design_review/evidence/2026-11-06_wce-definition-linking'
    if not authority.exists():
        authority=Path('/home/paul/corpus-structure/docs/design_review/evidence/2026-11-06_wce-definition-linking')
    view=json.loads((authority/'normal-native-view-53.json').read_text())
    body=json.loads((authority/'normal-annotations-285.json').read_text())
    ref=dict(view['ref']);ref['native_product']=ProductReference(**ref['native_product'])
    view_obj=SimpleNamespace(**{**view,'ref':SimpleNamespace(**ref)})
    source=ExternalSourceRef(project_id='wce-statistics-normal-20261106',run_id=113,cut_id=141,release_id=body['release_id'],result_revision=1,source_view_id=53,native_task_id=260,native_product_key=ref['native_product'].product_key,native_content_digest=ref['native_product'].content_digest,projection_digest=ref['projection_digest'],recipe_digest=ref['recipe_digest'],coordinate_version=3)
    passage=StructuralPassage(passage_id='normal-native-53',source_ref=source.identity,start=0,end=len(view['text']),text=view['text'],scope='wce-statistics-normal-002')
    inputs=StructuralInput(question='Locate definition structure',scope=passage.scope,inventory_id='actual-normal-source-53',policy_id='located-definition-1',sources=(source,),passages=(passage,),dependencies=('native:260','annotation:285'))
    rules=yaml.safe_load((root/'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['witnessed']['annotation_rules']
    cfg=DefinitionComponentsConfig(annotation_rules=tuple(rules))
    class Reader:
        def source_view(self, source_view_id):
            assert source_view_id == 53
            return view_obj
        def source_result(self, source_view_id, method):
            assert source_view_id == 53 and method == 'extract.m1_annotations'
            return body
    components,reason=retained_annotation_components(Reader(),inputs,passage,cfg)
    result={'outcome':'passed','source_annotation_task':285,'original_run':113,'original_cut':141,'source_view_id':53,'reason':reason,'component_count':len(components),'components':[c.model_dump(mode='json') for c in components],'independent_semantic_assessment':'not_run','native_component_completion':'not_run'}
    (Path(__file__).parent/'annotation-composition-result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'component_count':len(components),'pairs':[(c.term.text,c.content.text) for c in components]},ensure_ascii=False))


if __name__=='__main__':
    main()
