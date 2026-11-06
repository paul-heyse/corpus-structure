"""Read-only ordinary delivery of final model161/cut245, source-partitioned.

No producer/release mutation, provider invocation, historical decoder, or global
contribution inventory. API exports remain atomic; our page stream publishes only
when its complete bounded source selection has been read.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, UTC
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sys
import traceback

from sqlalchemy import text
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions, export_contribution_selection
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, inspect_review_bundle
from corpus_structure.serve.structural_products import StructuralExportRequest, read_structural_export_page
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[3]
CAPTURE=BASE/'assessment/run161-final-model001'
RUN=161
CUT=245
PARENT='763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e'


def digest(path):
    with path.open('rb') as stream:return file_digest(stream,'sha256').hexdigest()


def retain(path,value):
    raw=canonical_bytes(value)+b'\n';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('retained receipt differs: '+str(path))
        return
    with path.open('xb') as stream:stream.write(raw)


def failure(root,phase,error):
    row=dict(outcome='failed',phase=phase,type=type(error).__name__,message=str(error),at=datetime.now(UTC).isoformat())
    index=1
    while (root/f'{phase}-failure{index:03}.json').exists():index+=1
    retain(root/f'{phase}-failure{index:03}.json',row)
    (root/f'{phase}-failure{index:03}.txt').write_text(traceback.format_exc())
    return row


def request(source):
    # The existing ordinary contribution contract caps one selected file at128MiB.
    # Keep it unchanged; the separately declared portable file budget is256MiB.
    return ContributionRequest(run_id=RUN,source_view_id=source,include_interpretation=True,limit=1000,page_bytes=16_000_000,max_bytes=134_217_728)


def validate_export(directory,req):
    manifest=json.loads((directory/'manifest.json').read_bytes())
    if manifest['run_id']!=RUN or manifest['cut_id']!=CUT or manifest['selection']!=req.selection() or digest(directory/manifest['file'])!=manifest['sha256']:
        raise ValueError('existing selected export differs from exact model161 selection')
    return manifest


def export_source(settings,source,output,expected):
    root=output/('source-'+str(source));root.mkdir(exist_ok=True)
    req=request(source)
    pages_path=root/'pages.jsonl'
    page_receipt=root/'page-receipt.json'
    with open_runtime_engine(settings,'gs120-model161-source-delivery',purpose='read') as engine,read_snapshot(engine) as conn:
        if not pages_path.exists():
            partial=root/'pages.jsonl.partial'
            if partial.exists():raise ValueError('prior partial page stream retained; inspect before reattempt')
            cursor=req;counts=Counter();populations=Counter();page_count=0;page_bytes=0;first=None;zero_operations=0
            with partial.open('xb') as stream:
                while True:
                    page=serve_contributions(conn,cursor)
                    if page.run_id!=RUN or page.cut_id!=CUT:raise ValueError('ordinary Reader moved from exact completed cut')
                    row=page.model_dump(mode='json');raw=canonical_bytes(row)+b'\n';page_bytes+=len(raw)
                    if page_bytes>req.max_bytes:raise ValueError('cumulative source page stream exceeds128MiB')
                    stream.write(raw);stream.flush();page_count+=1
                    if first is None:first=page.inventory_counts
                    if page.inventory_counts!=first:raise ValueError('pinned per-source inventory changed across continuation')
                    for item in page.items:
                        populations[item['population']]+=1
                        if item['population']=='operation' and item['row'].get('emitted_count')==0:zero_operations+=1
                    if page.next_cursor is None:break
                    cursor=req.model_copy(update=dict(cursor=page.next_cursor))
            if populations.get('contribution',0)!=first['contributions'] or populations.get('operation',0)!=first['operations'] or populations.get('interpretation',0)!=first['interpretations']:
                raise ValueError('Reader continuation did not cover exact inventory')
            if first['contributions']!=expected['contributions'].get(source,0) or first['operations']!=expected['operations'].get(source,0):raise ValueError('Reader differs from exact normalized cut counts')
            partial.rename(pages_path)
            retain(page_receipt,dict(outcome='passed',run_id=RUN,cut_id=CUT,source_view_id=source,pages=page_count,bytes=page_bytes,sha256=digest(pages_path),inventory_counts=first,populations=dict(populations),zero_output_operations=zero_operations,page_bytes_bound=req.page_bytes,selection_bytes_bound=req.max_bytes,selection=req.selection()))
        receipt=json.loads(page_receipt.read_bytes())
        if receipt['sha256']!=digest(pages_path):raise ValueError('retained page stream changed')
        destination=root/'export'
        manifest=validate_export(destination,req) if destination.exists() else export_contribution_selection(conn,req,destination)
    retain(root/'export.json',manifest)
    result=dict(outcome='passed',run_id=RUN,cut_id=CUT,source_view_id=source,pages=receipt['pages'],page_stream_bytes=receipt['bytes'],inventory_counts=receipt['inventory_counts'],zero_output_operations=receipt['zero_output_operations'],export_bytes=manifest['bytes'],export_items=manifest['items'],export_sha256=manifest['sha256'],interpretation='included',scientific_support='unmodeled',source_completeness='not_established_by_inventory')
    retain(root/'result.json',result)
    print(json.dumps(dict(source_view_id=source,outcome='passed',**result['inventory_counts'])),flush=True)
    return result


def portable(settings,sources,output,manifest):
    groups=[sources[index:index+8] for index in range(0,len(sources),8)]
    specifications=[(f'sources-{index+1:03}',ReviewSelection(selections=tuple(request(s) for s in group),max_bytes=268_435_456),group) for index,group in enumerate(groups)]
    specifications.append(('structural',ReviewSelection(structural_selections=(StructuralExportRequest(run_id=RUN,cut_id=CUT,kind='definition_components',max_bytes=268_435_456),),max_bytes=268_435_456),sources))
    entries=[];found={};source_union=set();materialization_gaps=[]
    for label,selection,group in specifications:
        directory=output/('review-'+label)
        try:
            if not directory.exists():export_review_bundle(selection,directory,settings)
            captured=json.loads((directory/'manifest.json').read_bytes())
            if captured['selection']!=selection.model_dump(mode='json'):raise ValueError('existing portable bundle selection differs')
            inspection=inspect_review_bundle(directory)
            report_ids=[]
            with (directory/'reports.jsonl').open('rb') as stream:
                for line in stream:
                    row=json.loads(json.loads(line)['payload_json']);origin=row['origin_task_id'];body_hash=sha256(canonical_bytes(row['body'])).hexdigest()
                    if origin in found and found[origin]!=body_hash:raise ValueError('raw body differs between portable partitions')
                    found[origin]=body_hash;report_ids.append(origin)
            with (directory/'sources.jsonl').open('rb') as stream:
                for line in stream:
                    row=json.loads(json.loads(line)['payload_json']);source_union.add(row['source_view_id'])
            omissions=directory/'omissions.jsonl'
            if omissions.exists():
                with omissions.open('rb') as stream:materialization_gaps.extend(json.loads(json.loads(line)['payload_json']) for line in stream)
            entry=dict(outcome='passed',label=label,path=str(directory.relative_to(output)),selection_sources=group,manifest_sha256=digest(directory/'manifest.json'),file_bytes=sum(f['bytes'] for relation in captured['relations'].values() for f in relation['files'].values()),raw_report_ids=report_ids,inspection=inspection)
            retain(output/(label+'-portable.json'),entry);entries.append(entry)
            print(json.dumps(dict(portable=label,outcome='passed',raw_reports=len(report_ids),relations=inspection['relations'])),flush=True)
        except Exception as error:
            entries.append(dict(label=label,**failure(output,'portable-'+label,error)))
    expected={t['origin_task_id']:t for t in manifest['tasks']}
    extra=set(found)-set(expected);missing=set(expected)-set(found)
    for origin in sorted(set(found)&set(expected)):
        task=expected[origin];path=CAPTURE/task['raw_file']
        if digest(path)!=task['raw_sha256']:raise ValueError('captured accepted raw file pin differs')
        original=json.loads(path.read_bytes())
        if found[origin]!=sha256(canonical_bytes(original['body'])).hexdigest():raise ValueError('portable raw differs from accepted model161 body')
    result=dict(outcome='passed' if not missing and not extra and not materialization_gaps and all(e['outcome']=='passed' for e in entries) else 'failed',run_id=RUN,cut_id=CUT,groups=entries,declared_source_ids=sources,captured_source_ids=sorted(source_union),expected_raw_reports=len(expected),actual_raw_reports=len(found),missing_raw_report_ids=sorted(missing),extra_raw_report_ids=sorted(extra),materialization_gaps=materialization_gaps,raw_body_hashes=[dict(origin_task_id=k,sha256=v) for k,v in sorted(found.items())],source_extent=dict(physical_pages=list(range(191,311)),parent_pdf_sha256=PARENT,meaning='Declared context closure only; original PDF files remain in GS120/corpus and source manifest, not embedded or claimed complete.'),semantic_quality='unassessed')
    if source_union!=set(sources):result['outcome']='failed';result['source_materialization_gap']=sorted(set(sources)-source_union)
    retain(output/'portable-index.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);parser.add_argument('--phase',choices=('all','sources','portable'),default='all');args=parser.parse_args()
    output=HERE/args.attempt;output.mkdir(exist_ok=True)
    try:
        captured=json.loads((CAPTURE/'manifest.json').read_bytes())
        if captured['run']['id']!=RUN or captured['completed_result']['cut_id']!=CUT or not captured['run']['sealed'] or captured['run']['status']!='finished' or len(captured['tasks'])!=97:raise ValueError('final model run capture differs')
        metadata=json.loads((HERE/'metadata-read001.json').read_bytes());sources=metadata['sources'];assert sources==list(range(109,157))
        expected={key:{r['source_view_id']:r['n'] for r in metadata[key]} for key in ('contributions','operations')}
        settings=Settings();results=[]
        if args.phase in ('all','sources'):
            for source in sources:
                try:results.append(export_source(settings,source,output,expected))
                except Exception as error:results.append(dict(source_view_id=source,**failure(output,'source-'+str(source),error)))
            totals=Counter()
            for row in results:totals.update(row.get('inventory_counts',{}))
            result=dict(outcome='passed' if all(r['outcome']=='passed' for r in results) else 'failed',run_id=RUN,cut_id=CUT,source_count=len(sources),producing_runtime=captured['run']['runtime_id'],producing_code_commit=captured['run']['code_commit'],producing_release=captured['run']['release_id'],inventory_counts=dict(totals),source_results=results,normalized_cut_counts=metadata,zero_output_operations=sum(r.get('zero_output_operations',0) for r in results),limits=dict(page_bytes=16_000_000,ordinary_selected_file_bytes=134_217_728,portable_partition_bytes=268_435_456,global_contribution_inventory_used=False),semantic_quality='unassessed')
            retain(output/'source-results.json',result)
        if args.phase in ('all','portable'):portable(settings,sources,output,captured)
    except BaseException as error:failure(output,'delivery',error);raise


if __name__=='__main__':main()
