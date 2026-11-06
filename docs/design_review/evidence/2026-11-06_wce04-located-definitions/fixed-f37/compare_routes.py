"""Compare frozen exposed events, preserving different semantic operation scopes."""
from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig,decode_definition_components
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import StructuralInput,StructuralPassage,StructuralProductReport

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
OLD=ROOT/'docs/design_review/evidence/2026-11-05_pce-structural-products/raw'


def read(path):
    return json.loads(path.read_bytes())


def retain(name,value):
    (HERE/name).write_bytes(canonical_bytes(value)+b'\n')


def main():
    old=read(OLD/'independent-automatic-C-001.json')
    current=StructuralProductReport.model_validate(read(HERE/'constructive001/inspection.json')['reports'][0])
    original=StructuralInput.model_validate(read(HERE/'attempt002/freeze.json')['inputs'])
    cfg=DefinitionComponentsConfig.model_validate(read(HERE/'attempt002/configuration.json'))
    rawfile=HERE/'attempt002/raw-producer-envelope.json'
    rawhash=sha256(rawfile.read_bytes()).hexdigest()
    details=source_python(read(rawfile)['parse_detail'])
    rules=current.definition_components.components
    model=[];refusals=[];locations=[]
    for raw in details['raw_reports']:
        p=next(p for p in current.inputs.passages if p.passage_id==raw['passage_id'])
        before=next(p for p in original.passages if p.passage_id==raw['passage_id'])
        assert p.text==before.text and (p.start,p.end)==(before.start,before.end)
        window=StructuralPassage(passage_id=p.passage_id,source_ref=p.source_ref,start=raw['window_start'],end=raw['window_end'],text=p.text[raw['window_start']-p.start:raw['window_end']-p.start],scope=p.scope,effective_version=p.effective_version,parent=p.parent)
        locations.append(dict(passage_id=p.passage_id,located_proposal_count=raw['located_proposal_count']))
        try:model.extend(decode_definition_components(json.loads(raw['raw_json']),window,cfg))
        except ValueError as error:refusals.append(dict(passage_id=p.passage_id,error=str(error)))
    combined={c.component_id:c for c in (*rules,*model)}
    targets=cfg.target_ids
    arms=[]
    for target in targets:
        arms.append(dict(passage_id=target,linguistic=[c.model_dump(mode='json') for c in rules if c.term.passage_id==target],target_local_model=[c.model_dump(mode='json') for c in model if c.term.passage_id==target],composition=[c.model_dump(mode='json') for c in combined.values() if c.term.passage_id==target],definition_support='unassessed',usage_applicability='not_run'))
    cells=[]
    for case in old['cases']:
        for cell in case['cells']:
            local=[c.model_dump(mode='json') for c in combined.values() if c.term.passage_id==cell['target_id']]
            positive=cell['independent_disposition']=='supported' and cell['observed_category']=='applicable_definition'
            cells.append(dict(cell_id=cell['cell_id'],historical_run_id=case['run_id'],historical_cut_id=case['cut_id'],historical_task_id=case['task_id'],historical_cell=cell,current_local_components=local,current_usage_applicability='not_run',comparison_disposition='whole_usage_target_question_unresolved_by_this_operation',historical_wrong_whole_pair_corrected=False,previously_supported_definition_source_facet=('constructed_private_unassessed' if local else 'missed') if positive else 'not_this_cell',current_component_independent_assessment='not_run',limit='A local term/content proposal does not classify the original usage-target relation; retained historical negatives and wrong positives are not converted to current corrections.'))
    assert len(cells)==20 and len({c['cell_id'] for c in cells})==20
    assert len(rules)==1 and rules[0].term.passage_id=='nist-mean-definition'
    assert (rules[0].term.start,rules[0].term.end,rules[0].term.text)==(371,379,'the mean')
    assert (rules[0].content.start,rules[0].content.end,rules[0].content.text)==(383,446,'the sum of the data points divided by the number of data points')
    assert sha256(rawfile.read_bytes()).hexdigest()==rawhash
    source_origins=read(HERE/'attempt002/original-native-origin-partitions.json')
    retain('route-comparison.json',dict(date='2026-11-06',scope='Exposed fixed F37 development comparison; no heldout benefit or publication adoption claim.',frozen_model_run=132,frozen_model_body_sha256=rawhash,registered_linguistic_run=136,registered_linguistic_cut=174,registered_linguistic_task=331,registered_linguistic_method_version='4',model_reexecuted=False,original_sources=6,current_annotation_source_mappings=read(HERE/'fresh-annotations/source-mapping.json'),source_origin_partitions=source_origins,arms=arms,model_locations=locations,model_attachment_refusals=refusals,linguistic_operation_inventory=source_python(read(HERE/'constructive001/raw-producer-envelope.json')['parse_detail'])['named_rule_operations'],events=dict(original_unavailable_linguistic_run=132,fresh_linguistic_before_recipe='fresh-annotations/result.json',fresh_linguistic_after_recipe_run=136),counts=dict(fixed_target_windows=len(targets),old_usage_target_cells=len(cells),old_supported=sum(c['historical_cell']['independent_disposition']=='supported' for c in cells),old_wrong=sum(c['historical_cell']['independent_disposition']=='wrong_applicability' for c in cells),initial_components=0,fresh_annotations_before_recipe_components=0,linguistic_components=len(rules),target_local_model_components=len(model),composed_components=len(combined),new_components_independently_supported=0,new_components_independently_rejected=0,new_components_unassessed=len(combined),previously_supported_positive_source_facets_constructed=sum(c['previously_supported_definition_source_facet']=='constructed_private_unassessed' for c in cells),previously_supported_positive_source_facets_missed=sum(c['previously_supported_definition_source_facet']=='missed' for c in cells),old_wrong_whole_pairs_corrected=0,current_whole_pair_questions_not_run=len(cells)),limits=['The normal-location explanation remains a known uncaptured explanatory facet; missing components are not source absence.','The other ten selected targets yielded no components; no exhaustive definition coverage or negative semantic assessment follows.','Model span extraction succeeded for ten windows and was empty for one; located spans alone remain useful private evidence.','The mean model reply lacked defining-content spans and proposed an alias-like mean/average edge; the source-valid decoder refused endpoint roles.','Constructive verbal definition is retained without claiming formula attachment, arithmetic correctness, applicability, or independent adoption.']))
    retain('comparison-cells.json',cells)
    print(json.dumps(read(HERE/'route-comparison.json')['counts']))


if __name__=='__main__':main()
