"""Recover the GS120 residual scopes through current owned native adoption.

This script does not convert PDFs or invoke GLiNER/recognition. Each registered
source task adopts its exact retained organized product; current linguistic
annotations are produced against the new source-view identity. Original bytes are
read only for the existing source registration/hash custody boundary.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql, analyze_archived_sql, has_authored_sql,
)
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection, prepare_structural_sources,
)
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.settings import Settings

from inventory_sources import inventory_sources, PROJECT, PARENT

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
CORPUS = EVIDENCE / 'corpus'


def retain(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical_bytes(value) + b'\n')


def native_preflight(settings):
    if IngestPdf.version != '3':
        raise ValueError('current ingest.pdf v3 must be integrated before recovery')
    from corpus_structure.ingest.pdf_section_views import published_section_drafts
    if 'native-section-text-v7' not in published_section_drafts.__code__.co_consts:
        raise ValueError('current native source recipev7 must be integrated before recovery')
    with open_runtime_engine(settings, 'gs120-recovery-native-check', purpose='maintenance') as engine:
        with read_snapshot(engine) as conn:
            revision = conn.scalar(text('SELECT version_num FROM semantic_alembic_version'))
            if revision in {'semantic_wce_target_20261106', 'semantic_wce_baseline_20261106'}:
                raise ValueError('current residual-source native migration not installed')
            body = conn.scalar(text(
                "SELECT prosrc FROM pg_proc WHERE oid="
                "'ops.read_pdf_published_section_nodes(bigint,text,text,text,text)'::regprocedure"
            ))
            if '#/body' not in body:
                raise ValueError('deployed source reader lacks authentic residual-body scope')
    return revision


def admit_current(settings, output):
    bundle, dependencies, profile, prepared = prepare_pack(DOMAINS / 'statistics')
    retain(output / 'release.json', {
        'release_id': prepared.release_id,
        'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    with open_runtime_engine(settings, 'gs120-recovery-archive', purpose='admit') as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, prepared)
    analyzed = None
    if has_authored_sql(prepared):
        with open_runtime_engine(settings, 'gs120-recovery-sql', purpose='read') as engine:
            with read_snapshot(engine) as conn:
                analyzed = analyze_archived_sql(conn, prepared.release_id)
    with open_runtime_engine(settings, 'gs120-recovery-admit', purpose='admit') as engine:
        with engine.begin() as conn:
            if analyzed:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
            admit_release(prepared, connection=conn)
    return prepared


def recover_cut(settings, prepared, cut, output, attempt):
    method, annotations = IngestPdf(), M1Annotations()
    registry = MethodRegistry((method, annotations), MethodsFile(configs={
        method.name: {'retained': {
            'originals': [cut['file']],
            'membership': 'descendants',
            'native_product': cut['native_product'],
        }},
        annotations.name: {'default': {}},
    }))
    cfg = registry.resolve(method.name, 'retained').config
    if cfg.native_product is None or cfg.native_product.values() != cut['native_product']:
        raise ValueError('recovery config lost its exact retained native product')
    root = output / Path(cut['file']).stem
    root.mkdir()
    retain(root / 'configuration.json', {
        'method': method.name, 'version': method.version,
        'config': cfg.model_dump(mode='json'),
        'annotation_method': annotations.name, 'annotation_version': annotations.version,
        'input': cut,
    })
    realization = 'gs120-source-recovery:' + attempt + ':' + cut['sha256'] + ':' + prepared.release_id
    with open_runtime_engine(settings, 'gs120-recovery-register', purpose='write') as engine:
        with engine.begin() as conn:
            initialized = init_bound_project(
                conn, domain='statistics', corpus=CORPUS, name=PROJECT,
                release_id=prepared.release_id, realization_id=realization, registry=registry,
            )
            retain(root / 'project.json', initialized.model_dump(mode='json'))
    with open_runtime_engine(settings, 'gs120-recovery-adopt', purpose='write') as engine:
        with read_snapshot(engine) as conn:
            realization_table, documents = table('data.realization'), table('kb.document')
            revision = conn.scalar(select(realization_table.c.data_revision).where(
                realization_table.c.realization_id == realization
            ))
            docs = conn.execute(select(documents).where(documents.c.project_id == PROJECT)).mappings().all()
            corpus_record, _ = records(docs, {}, slice=None, scope=None, corpus=None)
        result = run_source_methods(
            engine, project_id=PROJECT, prepared=prepared,
            binding=OperationBinding(prepared.release_id, realization, revision, canonical_bytes({
                'native_product': cut['native_product'], 'source_pdf_sha256': cut['sha256'],
                'parent_pdf_sha256': PARENT, 'source_recipe': 'native-section-text-v7',
            })),
            registry=registry,
            graph=Graph((
                (Stage.INGEST, (Step(method.name + '/retained'),)),
                (Stage.EXTRACT, (Step(annotations.name + '/default', upstream=(method.name,)),)),
            ), policy_propose=False),
            method_settings=MethodSettings(data_dir=root / 'data', model_cache=Path.home() / '.cache/docling/models'),
            guideline=(DOMAINS / 'statistics/m1-guideline.md').read_text(),
            corpus_record=corpus_record, policy_source=None, kind='full',
        )
        retain(root / 'run.json', result.model_dump(mode='json'))
        if result.status != 'source_ready':
            raise ValueError('registered retained-native source run did not reach source readiness')
        with engine.begin() as conn:
            final_cut = seal_cut(conn, result.run_id, 'gs120-recovered-source-final', final=True)
        retain(root / 'sealed-cut.json', {'run_id': result.run_id, 'cut_id': final_cut, 'output_realization_id': 'gs120-recovered-source-result:' + str(result.run_id)})
        consolidate_cut(engine, final_cut, 'gs120-recovered-source-result:' + str(result.run_id))
    summary = {'file': cut['file'], 'run_id': result.run_id, 'cut_id': final_cut,
               'release_id': prepared.release_id, 'native_product': cut['native_product']}
    retain(root / 'result.json', {'outcome': 'passed', **summary})
    print(json.dumps({'source_run': result.run_id, 'file': cut['file'], 'outcome': 'passed'}), flush=True)
    return summary


def freeze_sources(settings, output, inputs, runs):
    packets = output / 'source-packets'
    packets.mkdir()
    all_rows, contexts, completed_results = [], {}, []
    run_to_cut = {run['run_id']: cut for run, cut in zip(runs, inputs['cuts'], strict=True)}
    with open_runtime_engine(settings, 'gs120-recovery-neutral-freeze', purpose='read') as engine:
        with read_snapshot(engine) as conn:
            for run in runs:
                completed = dict(conn.execute(text(
                    'SELECT * FROM ops.completed_result WHERE run_id=:run'
                ), {'run': run['run_id']}).mappings().one())
                completed_results.append({key: completed[key] for key in (
                    'run_id', 'cut_id', 'release_id', 'output_realization_id', 'batch_id'
                )})
                rows = [dict(row) for row in conn.execute(text(
                    'SELECT v.id,v.document_id,d.source_uri,v.native_task_id,v.native_product_key,'
                    'v.native_content_digest,v.analysis_eligible,length(v.projection->>\'text\') chars,'
                    'v.section_pointer,v.membership '
                    'FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id '
                    'JOIN kb.document d ON d.id=v.document_id WHERE m.run_id=:run ORDER BY v.id'
                ), {'run': run['run_id']}).mappings()]
                for row in rows:
                    row['run_id'] = run['run_id']
                    expected = run_to_cut[run['run_id']]['native_product']
                    if (row['native_task_id'], row['native_product_key'], row['native_content_digest']) != (
                        expected['task_id'], expected['product_key'], expected['content_digest']
                    ):
                        raise ValueError('source recovery changed native source product custody')
                    view = load_source_view(conn, row['id'], analysis=False)
                    contexts[row['id']] = view.context()
                    row['recipe_digest'] = view.ref.recipe_digest
                    all_rows.append(row)
        selections = tuple(StructuralPassageSelection(
            run_id=row['run_id'], source_view_id=row['id'],
            passage_id='gs120-recovered-source-' + str(row['id']),
            start=0, end=row['chars'], scope='grinstead-snell-physical191-310',
        ) for row in all_rows if row['chars'])
        frozen = prepare_structural_sources(engine, selections)
    refs = {source.source_view_id: source for source in frozen.sources}
    passages = {passage.source_ref: passage for passage in frozen.passages}
    mappings, coverage = [], []
    seen_fields = set()
    for cut in inputs['cuts']:
        page_map = {row['excerpt_physical_page']: row['parent_physical_page'] for row in cut['pages']}
        item_pages, text_pages, views = set(), set(), []
        for row in all_rows:
            if Path(row['source_uri']).name != cut['file']:
                continue
            context = contexts[row['id']]
            source = refs.get(row['id'])
            passage = passages.get(source.identity) if source else None
            views.append({'native_view': row, 'source': source.model_dump(mode='json') if source else None,
                          'passage': passage.model_dump(mode='json') if passage else None,
                          'native_context': context})
            nodes = {node['self_ref']: node for node in context['items']}
            for node in nodes.values():
                item_pages.update(page_map[prov['page_no']] for prov in node.get('prov', ()) if prov.get('page_no') in page_map)
            for piece in context['pieces']:
                if piece.get('kind') != 'native_text':
                    continue
                key = (row['native_content_digest'], piece['item_ref'], piece.get('source_field'), piece.get('cell_index'))
                if key in seen_fields:
                    raise ValueError('source text field duplicated by residual/section selection: ' + str(key))
                seen_fields.add(key)
                text_pages.update(page_map[prov['page_no']] for prov in nodes[piece['item_ref']].get('prov', ()) if prov.get('page_no') in page_map)
            mappings.append({'native_task_id': row['native_task_id'], 'native_product_key': row['native_product_key'],
                             'native_content_digest': row['native_content_digest'], 'source_view_id': row['id'],
                             'run_id': row['run_id'], 'source_uri': row['source_uri'], 'source_pdf_sha256': cut['sha256'],
                             'parent_pdf_sha256': PARENT, 'origin_group': 'grinstead-snell', 'page_map': cut['pages']})
        expected_pages = {row['parent_physical_page'] for row in cut['pages']}
        coverage.append({'file': cut['file'], 'parent_pages': sorted(expected_pages),
                         'native_item_pages': sorted(item_pages), 'projected_text_pages': sorted(text_pages),
                         'missing_native_item_pages': sorted(expected_pages - item_pages),
                         'missing_projected_text_pages': sorted(expected_pages - text_pages),
                         'source_views': len(views)})
        retain(packets / (Path(cut['file']).stem + '.json'), {
            'protocol': 'gs120-source-only-author-packet-1',
            'use': 'shared development and assessment source; no predictions or reference answers',
            'origin_group': 'grinstead-snell', 'parent_pdf_sha256': PARENT,
            'parent_physical_pages': sorted(expected_pages), 'source_pdf': '../../corpus/' + cut['file'],
            'source_pdf_sha256': cut['sha256'], 'page_map': cut['pages'], 'views': views,
        })
    retain(packets / 'native-parent-map.json', mappings)
    retain(packets / 'source-packet.json', {
        'protocol': 'gs120-recovered-authenticated-source-1',
        'source_manifest': json.loads((EVIDENCE / 'source-manifest.json').read_bytes()),
        'completed_results': completed_results,
        'sources': [source.model_dump(mode='json') for source in frozen.sources],
        'passages': [passage.model_dump(mode='json') for passage in frozen.passages],
        'views': all_rows, 'predictions_included': False,
    })
    covered = {page for row in coverage for page in row['native_item_pages']}
    text_covered = {page for row in coverage for page in row['projected_text_pages']}
    result = {'outcome': 'passed' if covered == set(range(191, 311)) else 'failed',
              'source_runs': runs, 'source_views': len(all_rows), 'nonempty_sources': len(frozen.sources),
              'native_item_pages': sorted(covered), 'projected_text_pages': sorted(text_covered),
              'missing_native_item_pages': sorted(set(range(191, 311)) - covered),
              'missing_projected_text_pages': sorted(set(range(191, 311)) - text_covered),
              'duplicate_projected_native_text_fields': 0, 'cuts': coverage,
              'semantic_quality': 'unassessed', 'visual_regions': 'uninspected',
              'scope': 'Actual current native source selection coverage; not semantic capture or scientific correctness'}
    retain(output / 'coverage.json', result)
    if result['outcome'] != 'passed':
        raise ValueError('source recovery did not cover all120 parent pages; see retained coverage.json')
    retain(output / 'result.json', result)
    print(json.dumps({key: value for key, value in result.items() if key not in {'source_runs', 'cuts'}}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    args = parser.parse_args()
    output = HERE / ('attempt' + args.attempt)
    output.mkdir(exist_ok=False)
    try:
        settings = Settings()
        revision = native_preflight(settings)
        inputs = inventory_sources()
        retain(output / 'native-inputs.json', inputs)
        retain(output / 'preflight.json', {'outcome': 'passed', 'native_revision': revision,
                                           'ingest_method_version': IngestPdf.version})
        prepared = admit_current(settings, output)
        runs = []
        for cut in inputs['cuts']:
            runs.append(recover_cut(settings, prepared, cut, output, args.attempt))
            retain(output / ('completed-cut-' + str(len(runs)).zfill(2) + '.json'), runs[-1])
        freeze_sources(settings, output, inputs, runs)
    except BaseException as error:
        retain(output / 'failure.json', {'outcome': 'failed', 'type': type(error).__name__, 'message': str(error)})
        raise


if __name__ == '__main__':
    main()
