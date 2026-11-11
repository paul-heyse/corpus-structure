"""Refine page provenance by exact native containment; never infer adjacent pages."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_reader import published_record_reader
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from account_book import BASE, RELEASE, HERE, captured_rows, write


def main():
    source=json.loads((HERE/'source-coverage.json').read_bytes())
    rows={row['pointer']:row for line in (HERE/'raw'/'native-item-coverage.jsonl').read_bytes().splitlines() if (row:=json.loads(line))}
    def locate(pointer):
        chain=[]
        while pointer:
            if pointer in chain:
                raise ValueError('native ownership cycle')
            row=rows.get(pointer)
            if row is None:
                raise ValueError('recorded native parent is absent from published inventory')
            chain.append(pointer)
            if row['pages']:
                return row['pages'],chain
            pointer=row['parent_pointer']
        return [],chain
    counts=Counter();labels=defaultdict(Counter);pages=defaultdict(lambda:dict(own_text_pieces=0,inherited_text_pieces=0,own_text_chars=0,inherited_text_chars=0))
    nonempty_unmapped=[]
    with (HERE/'raw'/'native-page-ownership.jsonl').open('wb') as output:
        for pointer,row in rows.items():
            actual,chain=locate(pointer)
            state='own_recorded_region' if row['pages'] else 'recorded_ancestor_region' if actual else 'unmapped_structural_ancestry'
            counts[state]+=1;labels[state][row['label']]+=1
            if not actual and (row['text_chars'] or row['real_projected_chars']):
                nonempty_unmapped.append(row)
            output.write(canonical_bytes(dict(pointer=pointer,own_pages=row['pages'],ancestor_pages=actual if not row['pages'] else [],region_owner=chain[-1] if actual else None,ownership_chain=chain,page_state=state))+b'\n')
            field='own' if row['pages'] else 'inherited'
            for page in actual:
                pages[page][field+'_text_pieces']+=row['real_text_pieces']
                pages[page][field+'_text_chars']+=row['real_projected_chars']
    # Inspect actual original nodes for the pages whose directly region-bearing
    # containers had no own text. This is a bounded source lookup, not annotation.
    target_pages={row['page_no'] for row in source['pages'] if row['disposition']!='selected_text_scope_present'}
    selected=[pointer for pointer in rows if set(locate(pointer)[0]) & target_pages]
    with open_runtime_engine(Settings(),'tc11-source-page-ownership',purpose='read') as engine,engine.connect() as conn:
        reader=published_record_reader(conn,BASE,projection_context=open_release(conn,RELEASE))
        field_counts=Counter()
        original_formula_pieces=[]
        for view in captured_rows(conn):
            for piece in view['projection']['pieces']:
                if piece['kind']!='native_text':continue
                field_counts[piece['source_field']]+=1
                item=rows[piece['item_ref']]
                if item['label']=='formula' and item['text_chars']!=item['real_projected_chars']:
                    original_formula_pieces.append(dict(source_view_id=view['id'],piece=piece,selected_text=view['projection']['text'][piece['start']:piece['end']]))
        originals=reader.selected_native_items(list(dict.fromkeys([*selected,*(r['piece']['item_ref'] for r in original_formula_pieces)])))
    for row in original_formula_pieces:
        native=originals[row['piece']['item_ref']]
        row['native']=native
        if row['piece']['source_field']!='orig' or row['selected_text']!=native['orig']:
            raise ValueError('formula source-field substitution differs from exact original orig')
    write('raw/source-field-selection.json',dict(native_piece_source_fields=dict(field_counts),formula_text_length_differences=original_formula_pieces,qualification='Field counts are retained projection facts. Container text length is not a cell/figure projection denominator. Exact orig correspondence does not establish complete formula recognition.'))
    detail=[]
    for pointer in selected:
        row=rows[pointer];node=originals[pointer];actual,chain=locate(pointer)
        detail.append(dict(pointer=pointer,label=row['label'],content_layer=row['content_layer'],own_pages=row['pages'],ancestor_pages=actual if not row['pages'] else [],region_owner=chain[-1],focal_views=row['focal_views'],real_text_pieces=row['real_text_pieces'],real_projected_chars=row['real_projected_chars'],native_text=node.get('text'),native_orig=node.get('orig'),native_children=node.get('children',[])))
    write('raw/previously-textless-page-source-items.json',detail)
    reports=[]
    for page in sorted(target_pages):
        reports.append(dict(page_no=page,original_own_region_disposition=next(row['disposition'] for row in source['pages'] if row['page_no']==page),**pages[page]))
    result=dict(version='tc11-source-page-ownership-1',acquired_at=datetime.now(timezone.utc).isoformat(),base_document=BASE.values(),native_items=len(rows),page_mapping_states=dict(counts),labels_by_mapping_state={key:dict(value) for key,value in labels.items()},nonempty_items_without_own_or_ancestor_region=nonempty_unmapped,previously_textless_pages=reports,pages=[dict(page_no=page,**pages[page]) for page in range(1,519)],interpretation_limit='Own region and exact native-container region are separate provenance. Ancestor page sets do not assign a child bounding box or a unique page within a multi-page parent. Structural nodes without text remain unmapped; no neighboring-page inference or source-completeness claim.')
    write('source-page-ownership.json',result)
    print(json.dumps({key:result[key] for key in ('page_mapping_states','labels_by_mapping_state','nonempty_items_without_own_or_ancestor_region','previously_textless_pages')},indent=2))


if __name__=='__main__':
    main()
