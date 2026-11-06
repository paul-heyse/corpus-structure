"""Current registered annotation products on bounded retained-native source sections.

No PDF, recognition or M1 extraction model runs. New source identities stay explicit;
old identities are retained only as comparison provenance after exact projection checks.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import yaml
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated
from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig,decode_definition_components,retained_annotation_components
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.orchestrate.registry import MethodRegistry,MethodsFile
from corpus_structure.orchestrate.runner import Graph,Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId,ReleaseId,RealizationId
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import BoundReader,OperationBinding,seal_cut
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view,selected_source_views
from corpus_structure.semantic.structural_sources import StructuralPassageSelection,prepare_structural_sources
from corpus_structure.semantic.structural_products import StructuralInput,StructuralPassage
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'fresh-annotations'


def retain(name,value):
    p=OUTPUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical_bytes(value)+b'\n')


def main():
    OUTPUT.mkdir(exist_ok=False);settings=Settings()
    frozen=json.loads((HERE/'attempt002/freeze.json').read_bytes());inputs=StructuralInput.model_validate(frozen['inputs'])
    release=json.loads((HERE/'attempt002/release.json').read_bytes())['release_id']
    baseline=source_python(json.loads((HERE/'attempt002/raw-producer-envelope.json').read_bytes())['parse_detail'])
    old_views={};groups={};references={};runs=[];maps=[]
    try:
        with open_runtime_engine(settings,'wce-f37-current-annotation-context',purpose='read') as engine,read_snapshot(engine) as conn:
            prepared=open_release(conn,release)
            for source in inputs.sources:
                view=load_source_view(conn,source.source_view_id,analysis=False)
                old_views[source.source_view_id]=view
                document=conn.execute(select(table('kb.document')).where(table('kb.document').c.id==view.ref.document_id)).mappings().one()
                groups.setdefault(source.project_id,[]).append((source,view,dict(document)))
        for project,items in groups.items():
            source,_,document=items[0]
            registry=MethodRegistry((IngestPdfIntegrated(),M1Annotations()),MethodsFile(configs={IngestPdfIntegrated.name:{'retained':dict(originals=[document['source_uri']],integrated_product=dict(task_id=source.native_task_id,product_key=source.native_product_key,content_digest=source.native_content_digest),sections=[view.ref.section_pointer for _,view,_ in items],membership='descendants')},M1Annotations.name:{'default':{}}}))
            realization='wce04-f37-annotation-input:'+project+':'+release
            with open_runtime_engine(settings,'wce-f37-annotation-project',purpose='write') as engine,engine.begin() as conn:initialize_source_project(conn,project_id=ProjectId(project),release_id=ReleaseId(release),realization_id=RealizationId(realization),projection_context=prepared)
            with open_runtime_engine(settings,'wce-f37-fresh-annotations',purpose='write') as engine:
                with engine.connect() as conn:revision=conn.scalar(select(table('data.realization').c.data_revision).where(table('data.realization').c.release_id==release,table('data.realization').c.realization_id==realization))
                result=run_source_methods(engine,project_id=project,prepared=prepared,binding=OperationBinding(release,realization,revision,canonical_bytes({'fixed_source_views':[source.source_view_id for source,_,_ in items],'source_freeze':frozen['source_packet_sha256']})),registry=registry,graph=Graph(((Stage.INGEST,(Step(IngestPdfIntegrated.name+'/retained'),)),(Stage.EXTRACT,(Step(M1Annotations.name+'/default',upstream=(IngestPdfIntegrated.name,)),))),policy_propose=False),method_settings=MethodSettings(data_dir=OUTPUT/project/'data',model_cache=Path.home()/'.cache/docling/models'),guideline='Regenerate current linguistic products only for exact retained F37 source sections; no PDF/recognition/GLiNER.',kind='full')
                retain(project+'/run.json',result.model_dump(mode='json'))
                if result.status!='source_ready':raise ValueError('fresh annotation run did not reach source_ready')
                with engine.begin() as conn:cut=seal_cut(conn,result.run_id,'fixed-f37-current-annotations',final=True)
                consolidate_cut(engine,cut,'wce04-f37-annotation-result:'+str(result.run_id))
                with read_snapshot(engine) as conn:
                    new_refs=selected_source_views(conn,result.run_id)
                    for original,old_view,_ in items:
                        matches=[]
                        for new_ref in new_refs:
                            view=load_source_view(conn,new_ref.id,analysis=False)
                            if view.text==old_view.text and view.ref.section_pointer==old_view.ref.section_pointer:
                                matches.append(view)
                        if len(matches)!=1:raise ValueError('retained-native adoption did not preserve a unique original projection')
                        current=matches[0]
                        assert canonical_bytes(current.pieces)==canonical_bytes(old_view.pieces),'native source pieces differ'
                        annotations=BoundReader(conn,result.run_id,prepared,cut).source_result(current.ref.id,M1Annotations.name)
                        retain(project+'/source-'+str(original.source_view_id)+'-annotations.json',annotations)
                        references[original.identity]=(result.run_id,current.ref.id)
                        maps.append(dict(original_source=original.model_dump(mode='json'),new_annotation_run=result.run_id,new_annotation_cut=cut,new_source=asdict(current.ref),full_text_identical=True,native_pieces_identical=True,original_membership=old_view.ref.membership,new_membership=current.ref.membership))
                runs.append(dict(project=project,run_id=result.run_id,cut_id=cut))
        retain('source-mapping.json',maps)
        selections=tuple(StructuralPassageSelection(run_id=references[p.source_ref][0],source_view_id=references[p.source_ref][1],passage_id=p.passage_id,start=p.start,end=p.end,scope=p.scope,effective_version=p.effective_version,parent=p.parent) for p in inputs.passages)
        with open_runtime_engine(settings,'wce-f37-fresh-source-preparation',purpose='read') as engine:new=prepare_structural_sources(engine,selections)
        fresh_inputs=inputs.model_copy(update={'sources':new.sources,'passages':new.passages})
        cfg=DefinitionComponentsConfig.model_validate(json.loads((HERE/'attempt002/configuration.json').read_bytes()))
        rules=[];model=[];metadata=[]
        with open_runtime_engine(settings,'wce-f37-linguistic-composition',purpose='read') as engine,read_snapshot(engine) as conn:
            reader=BoundReader(conn,runs[0]['run_id'],prepared)
            for passage in fresh_inputs.passages:
                if passage.passage_id not in cfg.target_ids:continue
                named=retained_annotation_components(reader,fresh_inputs,passage,cfg)
                rules.extend(named.components);metadata.extend(named.operations)
            for raw in baseline['raw_reports']:
                original=next(p for p in inputs.passages if p.passage_id==raw['passage_id'])
                updated=next(p for p in fresh_inputs.passages if p.passage_id==raw['passage_id'])
                window=StructuralPassage(passage_id=updated.passage_id,source_ref=updated.source_ref,start=raw['window_start'],end=raw['window_end'],text=original.text[raw['window_start']-original.start:raw['window_end']-original.start],scope=updated.scope,effective_version=updated.effective_version,parent=updated.parent)
                try:model.extend(decode_definition_components(json.loads(raw['raw_json']),window,cfg))
                except ValueError as error:metadata.append(dict(model_replay='same frozen decoder refusal',passage_id=updated.passage_id,error=str(error)))
        combined={c.component_id:c for c in (*rules,*model)}
        retain('linguistic-components.json',[c.model_dump(mode='json') for c in rules]);retain('model-components.json',[c.model_dump(mode='json') for c in model]);retain('composed-components.json',[c.model_dump(mode='json') for c in combined.values()]);retain('operation-inventory.json',metadata)
        retain('result.json',dict(outcome='passed',runs=runs,source_mappings=len(maps),fixed_targets=len(cfg.target_ids),linguistic_components=len(rules),model_components=len(model),composed_components=len(combined),GLiNER_reexecuted=False,PDF_read=False,recognition_run=False,original_source_identities_retained_as_provenance=True,scope='Exposed fixed targets; current role/attachment proposals require independent support and are not usage applicability classifications.'))
        print((OUTPUT/'result.json').read_text())
    except BaseException as error:
        retain('failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error),completed_runs=runs))
        raise


if __name__=='__main__':main()
