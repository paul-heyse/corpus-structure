"""Materialize B's independent native anchors through the production evidence owner.

Requires root-authenticated actual native unit keys; never invents them from passage aliases.
Offline only. Native protected ingress must still authenticate database custody.
"""
import argparse
import hashlib
import json
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice, evidence_anchor


def main():
    p=argparse.ArgumentParser();p.add_argument('provenance',type=Path);p.add_argument('unit_keys',type=Path);args=p.parse_args()
    rows=json.loads(args.provenance.read_text());keys=json.loads(args.unit_keys.read_text())
    if keys['protocol']!='wce-authenticated-native-unit-keys-1' or keys.get('coordinator_authenticated') is not True:raise ValueError('root-authenticated native unit-key snapshot required')
    rows_out=[]
    for row in rows:
        for role in ['term_anchor','content_anchor']:
            spec=row[role];packet=json.loads(Path(spec['packet']).read_text())
            if hashlib.sha256(Path(spec['packet']).read_bytes()).hexdigest()!=spec['packet_sha256']:raise ValueError('source packet changed')
            v=packet['views'][spec['view_index']];pin=v['source'];key=keys['sources'][str(pin['source_view_id'])]
            if key['source_pin']!=pin:raise ValueError('unit key snapshot differs from exact native source pins')
            native=v['native_view'];source=NativeFrameSource(unit_ref=key['unit_key'],text=v['passage']['text'],sentences=(),source_view_id=pin['source_view_id'],native_product=ProductReference(task_id=pin['native_task_id'],product_key=pin['native_product_key'],content_digest=pin['native_content_digest']),section_pointer=native['section_pointer'],membership=native['membership'],projection_digest=pin['projection_digest'],recipe_digest=pin['recipe_digest'],native_context=canonical_bytes(v['native_context']).decode(),version=pin['coordinate_version'])
            start=spec['piece']['start']+spec['native_start'];end=spec['piece']['start']+spec['native_end']
            ctx=NativeSourceContext(primary=source,related=(),pieces=(SourceSlice(pin['source_view_id'],start,end),),purpose='independent protected B source expectation',policy='wce-independent-source-literal-1',terminal_reason='exact source-authored local span')
            evidence=ctx.map_span(0,len(spec['quote']),literal=spec['quote'])
            if len(evidence)!=1:raise ValueError('B exact independent span unexpectedly crosses source pieces')
            anchor,coordinate=evidence_anchor(ctx,evidence[0],native=True)
            rows_out.append({'case_id':row['case_id'],'role':role,'anchor':anchor,'coordinate':coordinate,'source_pin':pin,'meaning_author':'independent B source literal authoring; produced endpoint anchors were not expectations'})
    print(json.dumps({'outcome':'passed','database_writes':'not_run','unit_key_snapshot_sha256':hashlib.sha256(args.unit_keys.read_bytes()).hexdigest(),'anchor_count':len(rows_out),'anchors':rows_out,'limits':'Production native anchor construction; actual source-key custody relies on authenticated root snapshot and later native ingress. No truth/publication claim.'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
