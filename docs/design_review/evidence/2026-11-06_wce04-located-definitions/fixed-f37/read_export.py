"""Authenticate retained component and exercise portable current-only source closure."""
import argparse
import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import RetainedComponentRef, StructuralProductReport
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, verify_review_bundle
from corpus_structure.serve.structural_products import StructuralRequest
from corpus_structure.settings import Settings


def main():
    parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
    output=Path(__file__).parent/args.attempt
    inspected=json.loads((output/'inspection.json').read_text())
    report=StructuralProductReport.model_validate(inspected['reports'][0])
    task=inspected['task_ids'][0]
    settings=Settings()
    with open_runtime_engine(settings,'wce-definition-ref',purpose='read') as engine,read_snapshot(engine) as conn:
        row=conn.execute(text('''SELECT job.project_id,job.runtime_id,batch.data_revision,method.name,method.version FROM ops.run job JOIN ops.completed_result completed ON completed.run_id=job.id JOIN data.batch batch ON batch.release_id=completed.release_id AND batch.realization_id=completed.output_realization_id AND batch.batch_id=completed.batch_id JOIN ops.task task ON task.run_id=job.id JOIN ops.method_config config ON config.id=task.method_config_id JOIN ops.method method ON method.id=config.method_id WHERE job.id=:run AND task.id=:task'''),dict(run=inspected['run_id'],task=task)).mappings().one()
        ref=RetainedComponentRef(product_id=report.product_id,component_id=report.definition_components.components[0].component_id,operation_id=row['name'],operation_version=row['version'],project_id=row['project_id'],run_id=inspected['run_id'],cut_id=inspected['cut_id'],release_id=inspected['release_id'],result_revision=row['data_revision'],selected_task_id=task,origin_task_id=task,runtime_fingerprint=row['runtime_id'],dependencies=report.inputs.dependencies)
        resolved=conn.scalar(text('SELECT ops.resolve_retained_component(CAST(:ref AS jsonb))'),dict(ref=canonical_bytes(ref.model_dump(mode='json')).decode()))
        assert resolved['component']['component_id']==ref.component_id
    (output/'component-reference.json').write_bytes(canonical_bytes(ref.model_dump(mode='json'))+b'\n')
    selection=ReviewSelection(structural_selections=(StructuralRequest(run_id=inspected['run_id'],kind='definition_components'),))
    exported=export_review_bundle(selection,output/'review-bundle',settings)
    verified=verify_review_bundle(output/'review-bundle')
    (output/'export-receipt.json').write_bytes(canonical_bytes(exported)+b'\n')
    (output/'export-verification.json').write_bytes(canonical_bytes(verified)+b'\n')
    print(json.dumps({'outcome':'passed','component_reference':ref.model_dump(mode='json'),'bundle_verification':verified}))


if __name__=='__main__':
    main()
