"""Complete retained source and annotation custody without running extraction models."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.m1 import (
    M1, bind_retained_document, registry, retained_document,
)
from corpus_structure.orchestrate.phase0 import bind_pdf_source
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql, analyze_archived_sql, has_authored_sql,
)
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
PACK = Path('domains/statistics')


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_name')
    args = parser.parse_args()
    output = HERE / args.output_name
    output.mkdir(exist_ok=False)
    (output / 'executed-runner.py.txt').write_bytes(Path(__file__).read_bytes())
    settings = Settings()
    bundle, deps, profile, prepared = prepare_pack(PACK)
    with open_runtime_engine(settings, 'm1-preparation-release', purpose='admit') as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, deps, profile, prepared)
        if has_authored_sql(prepared):
            with open_runtime_engine(settings, 'm1-preparation-sql', purpose='read') as reader_engine, reader_engine.connect() as reader:
                analyzed = analyze_archived_sql(reader, prepared.release_id)
            with engine.begin() as conn:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
        with engine.begin() as conn:
            admit_release(prepared, connection=conn)
    original = json.loads((HERE.parent / '2026-11-04_m1-source-populations/intake001/grinstead-snell/result.json').read_bytes())
    product = original['source_freeze']['pins'][0]['native_product']
    reference = ProductReference(product['task_id'], product['product_key'], product['content_digest'])
    project_id = 'm1-source-grinstead-snell'
    realization_id = 'm1-preparation:' + args.output_name + ':' + prepared.release_id
    with open_runtime_engine(settings, 'm1-preparation-owned-run', purpose='write') as engine:
        with engine.begin() as conn:
            initialize_source_project(conn, project_id=ProjectId(project_id),
                release_id=ReleaseId(prepared.release_id), realization_id=RealizationId(realization_id),
                projection_context=prepared)
            realization, document = table('data.realization'), table('kb.document')
            input_revision = conn.execute(select(realization.c.data_revision).where(realization.c.realization_id == realization_id)).scalar_one()
            documents = [dict(row) for row in conn.execute(select(document).where(document.c.project_id == project_id)).mappings()]
            selected = retained_document(conn, reference, prepared=prepared, project_id=project_id, documents=documents)
            corpus_record, scope_record = records([row for row in documents if row['id'] == selected.id], {},
                slice=None, scope=None, corpus=None)
        selected_registry = bind_retained_document(bind_pdf_source(registry(PACK), reference,
            method_name='ingest.pdf_integrated', input_role='integrated'), selected)
        # The existing owned executor supports bounded method graphs; no new product profile.
        graph = replace(M1, stages=(M1.stages[0], (Stage.EXTRACT, (M1.stages[1][1][0],))))
        report = run_source_methods(engine, project_id=project_id, prepared=prepared,
            binding=OperationBinding(prepared.release_id, realization_id, input_revision,
                canonical_bytes(dict(domain='statistics', release=prepared.release_id))),
            registry=selected_registry, graph=graph,
            method_settings=MethodSettings(data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache),
            domain='statistics', corpus_record=corpus_record, scope_record=scope_record,
            guideline=(PACK / 'm1-guideline.md').read_text(), extraction_policy='m1-candidate',
            extraction_policy_config=(PACK / 'm1-methods.yaml').read_text())
        with engine.begin() as conn:
            cut = seal_cut(conn, report.run_id, 'm1-source-annotation-final', final=True)
        published = consolidate_cut(engine, cut, 'm1-preparation-result:' + str(report.run_id) + ':' + prepared.release_id)
    result = dict(outcome='passed', scope='actual_retained_source_and_annotation_only',
        report=report.model_dump(mode='json'), publication=asdict(published),
        source_run_id=int(report.run_id), source_cut_id=int(cut), release_id=prepared.release_id,
        native_product=product, model_execution='not_run', pdf_conversion='not_run',
        contextual_inputs='generated separately; no consumed candidate model reports asserted')
    (output / 'completed-result.json').write_bytes(canonical_bytes(result))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
