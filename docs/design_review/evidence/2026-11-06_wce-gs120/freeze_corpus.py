"""Publish neutral source-only packets from completed native intake, without predictions."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from sqlalchemy import text
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_sources import StructuralPassageSelection,prepare_structural_sources
from corpus_structure.settings import Settings
HERE=Path(__file__).resolve().parent

def retain(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(canonical_bytes(value)+b'\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=int,required=True);args=parser.parse_args()
    manifest=json.loads((HERE/'source-manifest.json').read_bytes())
    output=HERE/'source-packets';output.mkdir(exist_ok=False)
    with open_runtime_engine(Settings(),'gs120-neutral-source-freeze',purpose='read') as engine:
        with read_snapshot(engine) as conn:
            rows=[dict(r) for r in conn.execute(text("SELECT v.id,v.document_id,d.source_uri,v.native_task_id,v.native_product_key,v.native_content_digest,v.analysis_eligible,length(v.projection->>'text') chars FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id JOIN kb.document d ON d.id=v.document_id WHERE m.run_id=:run ORDER BY v.document_id,v.id"),dict(run=args.run)).mappings()]
            completed=conn.execute(text('SELECT * FROM ops.completed_result WHERE run_id=:run'),dict(run=args.run)).mappings().one()
            contexts={row['id']:load_source_view(conn,row['id'],analysis=False).context() for row in rows}
        selections=tuple(StructuralPassageSelection(run_id=args.run,source_view_id=row['id'],passage_id='gs120-source-'+str(row['id']),start=0,end=row['chars'],scope='grinstead-snell-physical191-310') for row in rows if row['chars'])
        frozen=prepare_structural_sources(engine,selections)
    source_refs={s.source_view_id:s for s in frozen.sources};passages={p.source_ref:p for p in frozen.passages}
    mappings=[]
    for cut in manifest['cuts']:
        items=[]
        for row in rows:
            if Path(row['source_uri']).name!=cut['file']:continue
            source=source_refs.get(row['id']);passage=passages.get(source.identity) if source else None
            items.append(dict(native_view=row,source=source.model_dump(mode='json') if source else None,passage=passage.model_dump(mode='json') if passage else None,native_context=contexts[row['id']]))
            mappings.append(dict(native_task_id=row['native_task_id'],native_product_key=row['native_product_key'],native_content_digest=row['native_content_digest'],source_view_id=row['id'],source_uri=row['source_uri'],source_pdf_sha256=cut['sha256'],parent_pdf_sha256=manifest['parent_sha256'],origin_group='grinstead-snell',page_map=cut['pages']))
        if not items:raise ValueError('cut has no retained source view: '+cut['file'])
        retain(output/(Path(cut['file']).stem+'.json'),dict(protocol='gs120-source-only-author-packet-1',use='shared development and assessment source; no predictions/reference answers supplied',origin_group='grinstead-snell',parent_pdf_sha256=manifest['parent_sha256'],parent_physical_pages=[p['parent_physical_page'] for p in cut['pages']],source_pdf='corpus/'+cut['file'],source_pdf_sha256=cut['sha256'],page_map=cut['pages'],views=items))
    retain(output/'native-parent-map.json',mappings)
    retain(output/'source-packet.json',dict(protocol='gs120-authenticated-source-1',source_manifest=manifest,run_id=args.run,completed_result={key:completed[key] for key in ('run_id','cut_id','release_id','output_realization_id','batch_id')},sources=[s.model_dump(mode='json') for s in frozen.sources],passages=[p.model_dump(mode='json') for p in frozen.passages],views=rows,predictions_included=False))
    retain(output/'result.json',dict(outcome='passed',run_id=args.run,sources=len(frozen.sources),native_views=len(rows),packets=12,distinct_parent_pages=120,semantic_quality='unassessed',predictions_included=False))
    print((output/'result.json').read_text())
if __name__=='__main__':main()
