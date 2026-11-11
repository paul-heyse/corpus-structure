"""Dated read-only whole-book source/family account over exact retained products.

No inference, reference-answer access or production selection. Source accounting can run
before primary completion. Primary accounting requires the exact final book-result.json.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import func, select

from corpus_structure.semantic.characterization import characterization_profiles
from corpus_structure.semantic.characterization_store import read_layer_manifest, read_view
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
CAPTURE = 496
CUT = 614
PROJECT = 'nce-grinstead-snell-full-book'
RELEASE = 'release:c9939039081ddcfbc382e9dc323e12e31f9b3683fb479c773ea3fd72ac6a6189'
BASE = ProductReference(1627,'integrated','35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb')


def write(name, value):
    path = HERE / name
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(canonical_bytes(value) + b'\n')


def captured_rows(conn):
    source, membership = table('kb.source_view'), table('ops.run_source_view')
    rows = list(conn.execute(
        select(source).join(membership,membership.c.source_view_id==source.c.id)
        .where(membership.c.run_id==CAPTURE).order_by(membership.c.position,source.c.id)
    ).mappings())
    if len(rows)!=316 or len({row['id'] for row in rows})!=316:
        raise ValueError('capture membership differs from declared316direct views')
    for row in rows:
        if (row['native_task_id'],row['native_product_key'],row['native_content_digest']) != (BASE.task_id,BASE.product_key,BASE.content_digest):
            raise ValueError('capture mixes native documents')
        if row['membership']!='direct':
            raise ValueError('whole-book account requires declared direct memberships')
    return rows


def source_account(conn):
    prepared=open_release(conn,RELEASE)
    reader=published_record_reader(conn,BASE,projection_context=prepared)
    if reader is None:
        raise ValueError('exact whole-book native publication is absent')
    header=next(reader.iter_rows('header'))
    root=next(reader.iter_rows('native',{'record_id':header['root_id']}))
    page_shape=json.loads(root['structure_json'])['fields']['pages']
    pages=[int(row['member_key']) for row in reader.iter_rows('membership',{'parent_id':header['root_id'],'field_name':'pages'})]
    if page_shape['length']!=518 or len(pages)!=518 or sorted(pages)!=list(range(1,519)):
        raise ValueError('native physical-page map does not exactly account for1..518')
    health=list(reader.iter_companions('health'))
    views=captured_rows(conn)
    focal=defaultdict(set)
    ancestors=defaultdict(set)
    real_piece_counts=Counter()
    real_char_counts=Counter()
    view_reports=[]
    for row in views:
        projection=row['projection']
        for pointer in projection['items']:
            focal[pointer].add(row['id'])
        for pointer in projection['ancestors']:
            ancestors[pointer].add(row['id'])
        piece_kinds=Counter(piece['kind'] for piece in projection['pieces'])
        for piece in projection['pieces']:
            if piece['kind']=='native_text':
                real_piece_counts[piece['item_ref']]+=1
                real_char_counts[piece['item_ref']]+=piece['end']-piece['start']
        view_reports.append(dict(source_view_id=row['id'],unit_key=row['key'],section_pointer=row['section_pointer'],
            membership=row['membership'],analysis_eligible=row['analysis_eligible'],
            projection_digest=row['projection_digest'],recipe_digest=row['recipe_digest'],
            projected_text_chars=len(projection['text']),zero_text=not projection['text'],
            whitespace_only=bool(projection['text']) and not projection['text'].strip(),
            focal_native_items=len(projection['items']),context_ancestors=len(projection['ancestors']),
            piece_kinds=dict(piece_kinds),health=projection['health']))
    item_rows={}
    region_pages=defaultdict(set)
    after=-1
    raw=HERE/'raw'/'native-item-coverage.jsonl'
    with raw.open('wb') as output:
        while True:
            batch=reader.item_page(after=after,limit=500)
            if not batch:
                break
            region_rows=reader.selected_regions([row['pointer'] for row in batch])
            for region in region_rows:
                region_pages[region['pointer']].add(region['page_no'])
            for row in batch:
                pointer=row['pointer']
                entry=dict(pointer=pointer,label=row['label'],content_layer=row['content_layer'],
                           parent_pointer=row['parent_pointer'],ordinal=row['ordinal'],
                           section_pointer=row['section_pointer'],text_chars=len(row.get('text') or ''),
                           pages=sorted(region_pages[pointer]),focal_views=sorted(focal[pointer]),
                           context_views=sorted(ancestors[pointer]),real_text_pieces=real_piece_counts[pointer],
                           real_projected_chars=real_char_counts[pointer])
                item_rows[pointer]=entry
                output.write(canonical_bytes(entry)+b'\n')
            next_after=batch[-1]['ordinal']
            if next_after<=after:
                raise ValueError('native item continuation did not advance')
            after=next_after
    by_page={page:dict(page_no=page,retained_native_page=True,focal_source_views=set(),
                      body_items=0,furniture_items=0,image_items=0,selected_real_text_pieces=0,
                      unselected_body_items=0) for page in pages}
    for item in item_rows.values():
        for page in item['pages']:
            if page not in by_page:
                raise ValueError('native region escaped exact physical-page map')
            tally=by_page[page]
            if item['content_layer']=='furniture':tally['furniture_items']+=1
            elif item['content_layer']=='body':tally['body_items']+=1
            if item['label']=='picture':tally['image_items']+=1
            tally['focal_source_views'].update(item['focal_views'])
            tally['selected_real_text_pieces']+=item['real_text_pieces']
            if item['content_layer']=='body' and not item['focal_views']:
                tally['unselected_body_items']+=1
    for tally in by_page.values():
        tally['focal_source_views']=sorted(tally['focal_source_views'])
        tally['disposition']=(
            'selected_text_scope_present' if tally['selected_real_text_pieces'] else
            'retained_images_without_selected_text' if tally['image_items'] else
            'retained_body_without_selected_text' if tally['body_items'] else
            'furniture_only_in_recorded_regions' if tally['furniture_items'] else
            'native_page_present_without_recorded_regions'
        )
    view_pages=defaultdict(set)
    for pointer,ids in focal.items():
        for identity in ids:view_pages[identity].update(region_pages[pointer])
    for report in view_reports:
        report['recorded_region_pages']=sorted(view_pages[report['source_view_id']])
        report['page_mapping_basis']='exact recorded item regions only; missing regions are not inferred from nearby pages'
    counts=dict(
        native_items=len(item_rows),source_views=len(views),
        zero_text_views=sum(report['zero_text'] for report in view_reports),
        whitespace_only_views=sum(report['whitespace_only'] for report in view_reports),
        focal_native_items=sum(bool(row['focal_views']) for row in item_rows.values()),
        context_only_native_items=sum(bool(row['context_views']) and not row['focal_views'] for row in item_rows.values()),
        furniture_items=sum(row['content_layer']=='furniture' for row in item_rows.values()),
        image_items=sum(row['label']=='picture' for row in item_rows.values()),
        unselected_body_items=sum(row['content_layer']=='body' and not row['focal_views'] for row in item_rows.values()),
        native_items_without_recorded_page_region=sum(not row['pages'] for row in item_rows.values()),
        focal_pointers_absent_from_native_access=sorted(set(focal)-set(item_rows)),
        real_text_pointers_absent_from_native_access=sorted(set(real_piece_counts)-set(item_rows)),
    )
    result=dict(version='tc11-source-coverage-1',acquired_at=datetime.now(timezone.utc).isoformat(),
                project=PROJECT,capture_run=CAPTURE,source_cut=CUT,base_document=BASE.values(),
                source_revision=reader.revision,physical_page_presence='passed',
                expected_physical_pages=518,retained_native_pages=len(pages),
                counts=counts,page_dispositions=dict(Counter(row['disposition'] for row in by_page.values())),
                pages=[by_page[page] for page in sorted(pages)],source_views=view_reports,
                inherited_health=health,
                interpretation_limit='Native page presence and retained scopes do not establish complete text recognition or frozen-union assurance. Inherited source health is reported without diagnosing text corruption.')
    write('source-coverage.json',result)
    print(json.dumps({'source_account':'written','pages':len(pages),'counts':counts,'page_dispositions':result['page_dispositions']}))


def primary_account(conn):
    path=EVIDENCE/'book-result.json'
    if not path.exists():
        raise ValueError('final exact book-result.json is not yet available; primary account not_run')
    results=json.loads(path.read_bytes())
    if len(results)!=1:
        raise ValueError('whole-book account expects one exact composed document')
    result=results[0]
    pin=ProductReference(**result['view'])
    view=read_view(conn,pin)
    if view.base_document!=BASE:
        raise ValueError('combined view belongs to another book')
    body=view.payload
    active=[ProductReference(**value) for value in body.get('active_layers',body['layers'])]
    all_layers={ProductReference(**value) for value in body['layers']}
    if not set(active)<=all_layers or len(set(active))!=len(active):
        raise ValueError('combined active selection differs from retained closure')
    sources={row['id']:row for row in captured_rows(conn)}
    if set(body['source_scope']['source_view_ids'])!=set(sources):
        raise ValueError('combined view does not select the full frozen capture membership')
    prepared=open_release(conn,body['release_id'])
    required_families=tuple(characterization_profiles(prepared)['full_characterization'])
    observed_families=set()
    coverage_by_scope=defaultdict(list)
    projection_owners=defaultdict(set)
    for identity, source in sources.items():
        projection_owners[source['projection_digest']].add(identity)
    layer_meta=[]
    raw=HERE/'raw'/'family-scopes.jsonl'
    with raw.open('wb') as output:
        for layer_pin in active:
            manifest=read_layer_manifest(conn,layer_pin)
            header=manifest.payload
            declared=header['source_scope']['source_view_ids']
            if set(declared)-set(sources):
                raise ValueError('active layer scope escapes exact captured source views')
            declared_pins={source['source_view_id']:source for source in header['source_scope']['source_views']}
            if any(declared_pins[identity]['projection_digest'] != sources[identity]['projection_digest']
                   or declared_pins[identity]['recipe_digest'] != sources[identity]['recipe_digest']
                   for identity in declared):
                raise ValueError('active layer uses another captured projection/recipe')
            layer_meta.append(dict(reference=layer_pin.values(),release_id=header['release_id'],
                                   operation=header['operation'],source_view_ids=declared,outcome=header['outcome']))
            for coverage in header['coverage']:
                observed_families.add(coverage['family'])
                # Retain complete original selectors once. Per-view attribution uses only
                # exact source IDs/projection pins, never text equality or a bounding span.
                record=dict(layer=layer_pin.values(),operation=header['operation']['key'],
                            declared_source_views=declared,coverage=coverage)
                output.write(canonical_bytes(record)+b'\n')
                for field in ('eligible','examined','unexamined'):
                    for selector in coverage.get(field,[]):
                        owners=projection_owners.get(selector['projection'],set()) & set(declared)
                        if len(owners)!=1:
                            raise ValueError('coverage selector lacks a unique exact captured projection owner')
                for identity in declared:
                    projection=sources[identity]['projection_digest']
                    def matching(values):
                        return [selector for selector in values if selector['projection']==projection]
                    scope=dict(reference=layer_pin.values(),operation=header['operation']['key'],
                               outcome=coverage['outcome'],availability=coverage['availability'],
                               eligible=matching(coverage.get('eligible',[])),examined=matching(coverage.get('examined',[])),
                               unexamined=matching(coverage.get('unexamined',[])),reason=coverage.get('reason'),
                               declared_scope=True)
                    coverage_by_scope[(identity,coverage['family'])].append(scope)
    families=tuple(sorted(set(required_families)|observed_families))
    missing=[]; noncomplete=[]; totals=Counter()
    with (HERE/'raw'/'source-view-family-account.jsonl').open('wb') as output:
        for identity in sources:
            for family in families:
                rows=coverage_by_scope.get((identity,family),[])
                attributed=[row for row in rows if any(row[field] for field in ('eligible','examined','unexamined'))]
                state=('not_recorded' if family in required_families else 'not_selected_for_view') if not rows else 'declared_layer_without_attributed_selectors' if not attributed else 'complete_or_empty' if all(row['outcome'] in {'complete','empty'} for row in attributed) else 'incomplete'
                record=dict(source_view_id=identity,family=family,required_family=family in required_families,state=state,operations=rows)
                output.write(canonical_bytes(record)+b'\n')
                totals[state]+=1
                if not rows and family in required_families:missing.append(dict(source_view_id=identity,family=family))
                elif rows and state!='complete_or_empty':noncomplete.append(dict(source_view_id=identity,family=family,outcomes=[row['outcome'] for row in rows]))
    task,run=table('ops.task'),table('ops.run')
    owner=conn.execute(select(task.c.run_id,run.c.project_id).join(run,run.c.id==task.c.run_id).where(task.c.id==pin.task_id)).one()
    if owner.project_id!=PROJECT:
        raise ValueError('combined output belongs to another project')
    task_counts=dict(conn.execute(select(task.c.status,func.count()).where(task.c.run_id.in_(result['runs'])).group_by(task.c.status)).all())
    final=dict(version='tc11-primary-coverage-1',acquired_at=datetime.now(timezone.utc).isoformat(),
               project=PROJECT,base_document=BASE.values(),view=pin.values(),producing_run=owner.run_id,
               book_result_sha256=sha256(path.read_bytes()).hexdigest(),
               coverage_attribution='exact unique projection digest within declared source scope; original selectors retained',
               source_views=len(sources),required_families=list(required_families),selected_families=sorted(observed_families),
               accounted_families=list(families),required_scope_pairs=len(sources)*len(required_families),accounted_scope_pairs=len(sources)*len(families),
               active_layers=len(active),retained_dependency_layers=len(all_layers)-len(active),
               source_view_family_states=dict(totals),missing_scope_pairs=missing,incomplete_scope_pairs=noncomplete,
               operations=layer_meta,run_ids=result['runs'],task_status_counts=task_counts,
               demand_readiness=result['readiness'],demand_missing_families=result['missing_families'],
               qualification_limit='This is execution/coverage accounting, not semantic grades, inferred English completeness, knowledge admission or a claim that all source recognition succeeded.')
    write('primary-coverage.json',final)
    print(json.dumps({'view':pin.values(),'source_views':len(sources),'families':len(families),'scope_states':dict(totals),'task_status_counts':task_counts}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['source','primary'])
    args=parser.parse_args()
    with open_runtime_engine(Settings(),'tc11-whole-book-account',purpose='read') as engine,engine.connect() as conn:
        (source_account if args.action=='source' else primary_account)(conn)
