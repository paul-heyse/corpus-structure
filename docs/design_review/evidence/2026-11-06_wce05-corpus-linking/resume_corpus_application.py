"""Resume completed actual linking at inspection/applicability; never repeat encoder work."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select, text

from corpus_native_journey import metadata, save
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_applicability import DefinitionApplicabilityMethod
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import ExternalSourceRef, StructuralInput
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions, export_contribution_selection
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    parser.add_argument('--run', type=int, required=True)
    args = parser.parse_args()
    output = HERE / args.attempt
    output.mkdir(exist_ok=False)
    settings = Settings()
    try:
        with open_runtime_engine(settings, 'wce05-resume-inspection', purpose='read') as engine, read_snapshot(engine) as conn:
            run = conn.execute(select(table('ops.run')).where(table('ops.run').c.id == args.run)).mappings().one()
            prepared = open_release(conn, run['release_id'])
            page = serve_contributions(conn, ContributionRequest(run_id=args.run, method='retrieve.contextual', include_details=True))
            save(output, 'inspection.json', page.model_dump(mode='json'))
            export_contribution_selection(conn, ContributionRequest(run_id=args.run, method='retrieve.contextual'), output / 'contributions')
            tasks, results, configs, methods = (table(n) for n in ('ops.task', 'ops.task_result', 'ops.method_config', 'ops.method'))
            row = conn.execute(select(tasks.c.id, results.c.body).join(results, results.c.task_id == tasks.c.id).join(configs, configs.c.id == tasks.c.method_config_id).join(methods, methods.c.id == configs.c.method_id).where(tasks.c.run_id == args.run, methods.c.name == 'retrieve.contextual')).mappings().one()
            body = row['body']
            save(output, 'linker-result.json', body)
            completed, revision, runtime = metadata(conn, args.run)
            dependencies = json.loads(bytes(run['dependencies']))
        source = ExternalSourceRef.model_validate(dependencies['selected_sources'][0])
        operation = next(op for op in body['contribution_operations'] if 'contextual_enrichment' in op)
        enrichment = operation['contextual_enrichment']
        selected = [(d, edge) for d in enrichment['relationship_decisions'] for edge in d['selected_edges'] if edge['relation'] == 'defined-by']
        summary = dict(outcome='passed' if selected else 'partial', run_id=args.run, cut_id=completed['cut_id'], release_id=prepared.release_id,
            counts=enrichment['product_counts'], selected_defined_by=len(selected),
            private_target_representations=sum(len(i['targets']) for i in enrichment['inventories']),
            semantic_target_meanings=sum(len(i['semantic_groups']) for i in enrichment['inventories']),
            query_population='actual retained definition-term occurrences', actual_provider='E5',
            nomination_budget_unit='private target representations', quality_claim='not_established')
        save(output, 'linking-result.json', summary)
        if not selected:
            save(output, 'result.json', summary)
            return
        if len(selected) != 1:
            raise ValueError('This source-local journey requires one unambiguous defining relationship')
        (decision, edge), = selected
        occurrence = next(c for c in body['contributions'] if c['semantic_type'] == 'contextual.located_mention' and c['occurrence_id'] == decision['occurrence_id'])
        link = RetainedRelationshipDecisionRef(project_id=source.project_id, run_id=args.run,
            cut_id=completed['cut_id'], release_id=prepared.release_id, result_revision=revision,
            selected_task_id=row['id'], origin_task_id=row['id'], runtime_fingerprint=runtime,
            operation_key=operation['operation_key'], decision_id=decision['decision_id'], edge_id=edge['edge_id'], occurrence_contribution_id=occurrence['contribution_id'])
        save(output, 'relationship-reference.json', link.model_dump(mode='json'))
        with open_runtime_engine(settings, 'wce05-resume-component', purpose='read') as engine, read_snapshot(engine) as conn:
            retained = conn.execute(text('SELECT ops.resolve_retained_relationship_decision(CAST(:ref AS jsonb))'), {'ref': link.model_dump_json()}).scalar_one()
            component_ref = retained['component_target']['reference']
            original = conn.execute(text('SELECT ops.resolve_retained_component(CAST(:ref AS jsonb))'), {'ref': json.dumps(component_ref)}).scalar_one()
        component = original['component']
        target_passage = next(p for p in original['report']['inputs']['passages'] if p['passage_id'] == component['term']['passage_id'])
        usage = dict(target_passage, passage_id='actual-defined-term', start=component['term']['start'], end=component['term']['end'], text=component['term']['text'])
        inputs = StructuralInput(question='Assess source-local introduction applicability', scope=component['scope'], inventory_id='actual-normal-definition-terms', policy_id='definition-introduction-1', sources=(source,), passages=(target_passage, usage), dependencies=(component_ref['product_id'], decision['decision_id']))
        cfg = dict(inputs=inputs.model_dump(mode='json'), structural_input_digest=inputs.identity, usage_id='actual-defined-term', selection_refs=[link.model_dump(mode='json')], applicability_scope='defining_occurrence')
        save(output, 'applicability-configuration.json', cfg)
        method = DefinitionApplicabilityMethod()
        with open_runtime_engine(settings, 'wce05-resume-applicability', purpose='write') as engine:
            app = run_source_methods(engine, project_id=source.project_id, prepared=prepared,
                binding=OperationBinding(prepared.release_id, completed['output_realization_id'], revision, b'{}'),
                registry=MethodRegistry((method,), MethodsFile(configs={method.name: {'default': cfg}})),
                graph=Graph(((Stage.ASSEMBLE, (Step(method.name + '/default'),)),), policy_propose=False),
                method_settings=MethodSettings(data_dir=output / 'data', model_cache=Path.home() / '.cache/docling/models'),
                selected_sources=(source,))
            save(output, 'applicability-run.json', app.model_dump(mode='json'))
            finalize_bound_run(engine, app.run_id, 'wce05-applicability-result:' + str(app.run_id))
        with open_runtime_engine(settings, 'wce05-resume-app-read', purpose='read') as engine, read_snapshot(engine) as conn:
            app_page = serve_structural_products(conn, StructuralRequest(run_id=app.run_id))
            save(output, 'applicability-inspection.json', app_page.model_dump(mode='json'))
        summary.update(applicability_run=app.run_id, applicability_outcomes=[reading.outcome for report in app_page.reports for reading in report.definition.readings],
            scope='actual source-role projection, real E5, native current relationship and applicability retention, completed ordinary read/export; independent assessment/publication separate')
        save(output, 'result.json', summary)
        print(canonical_bytes(summary).decode())
    except BaseException as error:
        save(output, 'failure.json', dict(outcome='failed', error_type=type(error).__name__, reason=str(error)))
        raise


if __name__ == '__main__':
    main()
