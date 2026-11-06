"""Actual retained corpus roles → E5 → authenticated target → private relationship/applicability.

No source labels or evaluator references are used as mention inputs. The sole query
population is produced by the owned retained-component term-location operation.
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidates
from corpus_structure.methods.definition_terms import DefinitionTermsMethod
from corpus_structure.methods.definition_applicability import DefinitionApplicabilityMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import ExternalSourceRef, RetainedComponentRef, StructuralInput
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.observations import source_python
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions, export_contribution_selection
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent


def save(root, name, value):
    (root / name).write_bytes(canonical_bytes(value) + b'\n')


def metadata(conn, run):
    completed = conn.execute(select(table('ops.completed_result')).where(table('ops.completed_result').c.run_id == run)).mappings().one()
    batch = conn.execute(select(table('data.batch')).where(table('data.batch').c.batch_id == completed['batch_id'], table('data.batch').c.release_id == completed['release_id'], table('data.batch').c.realization_id == completed['output_realization_id'])).mappings().one()
    runtime = conn.scalar(select(table('ops.run').c.runtime_id).where(table('ops.run').c.id == run))
    return completed, batch['data_revision'], runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    parser.add_argument('--component-reference', type=Path, required=True)
    parser.add_argument('--link-only', action='store_true')
    args = parser.parse_args()
    output = HERE / args.attempt
    output.mkdir(exist_ok=False)
    settings = Settings()
    try:
        reference = RetainedComponentRef.model_validate_json(args.component_reference.read_bytes())
        save(output, 'component-reference.json', reference.model_dump(mode='json'))
        with open_runtime_engine(settings, 'wce05-original-component', purpose='read') as engine, engine.connect() as conn:
            original = conn.execute(text('SELECT ops.resolve_retained_component(CAST(:ref AS jsonb))'), {'ref': reference.model_dump_json()}).scalar_one()
        component, original_report = original['component'], original['report']
        term_passage = next(p for p in original_report['inputs']['passages'] if p['passage_id'] == component['term']['passage_id'])
        source = next(ExternalSourceRef.model_validate(s) for s in original_report['inputs']['sources'] if ExternalSourceRef.model_validate(s).identity == term_passage['source_ref'])
        save(output, 'original-source.json', source.model_dump(mode='json'))
        assert source.run_id == 113 and source.cut_id == 141 and source.source_view_id == 53
        producer = DefinitionTermsMethod()
        linker = ContextualCandidates()
        configs = {
            producer.name: {'default': dict(component_refs=[reference.model_dump(mode='json')], source_product_digest=source.native_content_digest, source_projection_digest=source.projection_digest)},
            linker.name: {'default': dict(source_dependency_method=producer.name, profile='e5',
                source_product_digest=source.native_content_digest, source_projection_digest=source.projection_digest,
                scope=component['scope'], effective_version=component.get('effective_version'),
                target_components=[dict(reference=reference.model_dump(mode='json'), label=component['term']['text'], description=component['content']['text'], scope=component['scope'], effective_version=component.get('effective_version'))],
                relationship_constraints=[dict(constraint_id='retained-definition-binding-1', relation_kinds=['defined-by'], occurrence_role='defined_term', target_role='definition_component', multiplicity='one', exhaustive=False)])},
        }
        save(output, 'configuration.json', configs)
        bundle, dependencies, profile = compose_pack_inputs((acquire_pack(DOMAINS / 'statistics'),))
        prepared = prepare_release(bundle, dependencies, profile)
        save(output, 'release.json', {'release_id': prepared.release_id})
        with open_runtime_engine(settings, 'wce05-release', purpose='admit') as engine, engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, prepared)
        analyzed = None
        if has_authored_sql(prepared):
            with open_runtime_engine(settings, 'wce05-sql', purpose='read') as engine, engine.connect() as conn:
                analyzed = analyze_archived_sql(conn, prepared.release_id)
        with open_runtime_engine(settings, 'wce05-admit', purpose='admit') as engine, engine.begin() as conn:
            if analyzed:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
            admit_release(prepared, connection=conn)
        realization = 'wce05-normal-input:' + args.attempt + ':' + prepared.release_id
        with open_runtime_engine(settings, 'wce05-project', purpose='write') as engine, engine.begin() as conn:
            initialize_source_project(conn, project_id=ProjectId(source.project_id), release_id=ReleaseId(prepared.release_id), realization_id=RealizationId(realization), projection_context=prepared)
            revision = conn.scalar(select(table('data.realization').c.data_revision).where(table('data.realization').c.release_id == prepared.release_id, table('data.realization').c.realization_id == realization))
        method_settings = MethodSettings(data_dir=output / 'data', model_cache=Path.home() / '.cache/docling/models')
        with open_runtime_engine(settings, 'wce05-real-provider-native', purpose='write') as engine:
            result = run_source_methods(engine, project_id=source.project_id, prepared=prepared,
                binding=OperationBinding(prepared.release_id, realization, revision, b'{}'),
                registry=MethodRegistry((producer, linker), MethodsFile(configs=configs)),
                graph=Graph(((Stage.EXTRACT, (Step(producer.name + '/default'),)), (Stage.LINK, (Step(linker.name + '/default'),))), policy_propose=False),
                method_settings=method_settings, selected_sources=(source,),
                guideline='Project actual retained definition-term roles; real E5 nomination; no independent semantic support claim.')
            save(output, 'run.json', result.model_dump(mode='json'))
            finalize_bound_run(engine, result.run_id, 'wce05-normal-result:' + str(result.run_id))
        with open_runtime_engine(settings, 'wce05-inspection', purpose='read') as engine, read_snapshot(engine) as conn:
            page = serve_contributions(conn, ContributionRequest(run_id=result.run_id, method=linker.name, include_details=True))
            save(output, 'inspection.json', page.model_dump(mode='json'))
            export_contribution_selection(conn, ContributionRequest(run_id=result.run_id, method=linker.name), output / 'contributions')
            tasks, results, methods, method_configs = (table(n) for n in ('ops.task', 'ops.task_result', 'ops.method', 'ops.method_config'))
            row = conn.execute(select(tasks.c.id, results.c.body).join(results, results.c.task_id == tasks.c.id).join(method_configs, method_configs.c.id == tasks.c.method_config_id).join(methods, methods.c.id == method_configs.c.method_id).where(tasks.c.run_id == result.run_id, methods.c.name == linker.name)).mappings().one()
            body = row['body']
            save(output, 'linker-result.json', body)
            completed, linked_revision, runtime = metadata(conn, result.run_id)
        operation = next(op for op in body['contribution_operations'] if 'contextual_enrichment' in op)
        report = operation['contextual_enrichment']
        decisions = report['relationship_decisions']
        selected = [(decision, edge) for decision in decisions for edge in decision['selected_edges'] if edge['relation'] == 'defined-by']
        summary = dict(outcome='passed' if selected else 'partial', run_id=result.run_id, cut_id=completed['cut_id'], release_id=prepared.release_id, physical_source=source.model_dump(mode='json'), profile='real E5', query_population='actual retained definition-term occurrences', counts=report['product_counts'], private_target_representations=sum(len(inv['targets']) for inv in report['inventories']), semantic_target_meanings=sum(len(inv['semantic_groups']) for inv in report['inventories']), nomination_budget_unit='distinct private target representations; equivalent origins can consume separate vector/candidate budget', selected_defined_by=len(selected), independent_assessment='not_run', public_admission='not_run')
        save(output, 'result.json', summary)
        if selected:
            if len(selected) != 1:
                raise ValueError('This source-local journey requires one unambiguous defining relationship')
            (decision, edge), = selected
            occurrence = next(c for c in body['contributions'] if c['semantic_type'] == 'contextual.located_mention' and c['occurrence_id'] == decision['occurrence_id'])
            link_ref = RetainedRelationshipDecisionRef(project_id=source.project_id, run_id=result.run_id, cut_id=completed['cut_id'], release_id=prepared.release_id, result_revision=linked_revision, selected_task_id=row['id'], origin_task_id=row['id'], runtime_fingerprint=runtime, operation_key=operation['operation_key'], decision_id=decision['decision_id'], edge_id=edge['edge_id'], occurrence_contribution_id=occurrence['contribution_id'])
            save(output, 'relationship-reference.json', link_ref.model_dump(mode='json'))
            if args.link_only:
                summary.update(applicability='not_run: separately retained relationship is ready for applicability')
                save(output, 'result.json', summary)
                print(json.dumps(summary))
                return
            passage = dict(term_passage, passage_id='actual-defined-term', start=component['term']['start'], end=component['term']['end'], text=component['term']['text'])
            inputs = StructuralInput(question='Assess scope of actual retained defining occurrence', scope=component['scope'], inventory_id='actual-normal-definition-terms', policy_id='definition-introduction-1', sources=(source,), passages=(term_passage, passage), dependencies=(reference.product_id, decision['decision_id']))
            app = DefinitionApplicabilityMethod()
            app_cfg = dict(inputs=inputs.model_dump(mode='json'), structural_input_digest=inputs.identity, usage_id='actual-defined-term', selection_refs=[link_ref.model_dump(mode='json')], applicability_scope='defining_occurrence')
            save(output, 'applicability-configuration.json', app_cfg)
            with open_runtime_engine(settings, 'wce05-applicability', purpose='write') as engine:
                app_run = run_source_methods(engine, project_id=source.project_id, prepared=prepared, binding=OperationBinding(prepared.release_id, 'wce05-normal-result:' + str(result.run_id), linked_revision, b'{}'), registry=MethodRegistry((app,), MethodsFile(configs={app.name: {'default': app_cfg}})), graph=Graph(((Stage.ASSEMBLE, (Step(app.name + '/default'),)),), policy_propose=False), method_settings=method_settings, selected_sources=(source,))
                save(output, 'applicability-run.json', app_run.model_dump(mode='json'))
                finalize_bound_run(engine, app_run.run_id, 'wce05-applicability-result:' + str(app_run.run_id))
            with open_runtime_engine(settings, 'wce05-applicability-read', purpose='read') as engine, read_snapshot(engine) as conn:
                app_page = serve_structural_products(conn, StructuralRequest(run_id=app_run.run_id))
                save(output, 'applicability-inspection.json', app_page.model_dump(mode='json'))
            summary.update(applicability_run=app_run.run_id, applicability_outcomes=[reading.outcome for report in app_page.reports for reading in report.definition.readings], quality_claim='not_established; source-only independent reference work separate')
            save(output, 'result.json', summary)
        print(json.dumps(summary))
    except BaseException as error:
        save(output, 'failure.json', dict(outcome='failed', error_type=type(error).__name__, reason=str(error)))
        raise


if __name__ == '__main__':
    main()
