"""Explicit v1 assembly derivation and native global/enrichment replay, no page inference."""
from dataclasses import replace,asdict
from pathlib import Path
from hashlib import sha256
import json
import time

from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.base_models import Page,InputFormat
from docling.datamodel.document import ConversionResult,InputDocument

from corpus_structure.ingest.pdf import PdfRecipe,PdfConverter
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_assembly import derive_v1_assembly_types
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool,StreamingPdfResult,_atomic_json
from corpus_structure.ingest.pdf_stream_types import PdfReplayRef


def main():
    root=Path('build/pdf-remaining-native-finalization-fourth').resolve();root.mkdir(exist_ok=False)
    started=time.monotonic()
    recipe=PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8','ecedbe111d15c2dc60bfd4a823cbe80127b58af4',recipe_id='docling-standard-pdf-stream-v1')
    assets=prepare_pdf_assets(recipe,cache=Path.home()/'.cache/docling/models',offline=True)
    recipe=replace(recipe,model_artifacts=assets.files,model_revisions=assets.repositories)
    spool=PdfStreamSpool(root/'derived-pages')
    journal=[PdfReplayRef(Path(r['path']),r['digest'],r['byte_length'],r['family'],r['rows']) for r in map(json.loads,Path('build/pdf-remaining-native-book/replay.jsonl').read_text().splitlines())]
    original=Path('docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf')
    raster_source=InputDocument(path_or_stream=original,format=InputFormat.PDF,backend=ThreadedDoclingParseDocumentBackend)
    from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
    native_scale=CodeFormulaVlmModel.images_scale
    refs_by_name={ref.path.name:ref for ref in journal}
    for backend in raster_source._backend.iter_pages():
        ref=refs_by_name[f"page-{backend.page_no:06}.json"]
        ref.verify();raw=json.loads(ref.path.read_bytes())
        raw['assembly_types']=derive_v1_assembly_types(raw['page']['assembled'])
        raw['derived_from']={'sha256':ref.digest,'profile':'docling-page-assembly-v1','rerender':'exact original Docling backend full raster at actual CodeFormulaVlmModel.images_scale'}
        image=backend.get_page_image(scale=native_scale)
        raster_path=spool.root/f"rerender-{raw['page']['page_no']:06}.png"
        image.save(raster_path,format='PNG');image.close();backend.unload()
        raw['raster']={'path':str(raster_path),'digest':sha256(raster_path.read_bytes()).hexdigest(),'byte_length':raster_path.stat().st_size}
        raw['scale']=native_scale
        spool.pages[raw['page']['page_no']]=_atomic_json(spool.root/ref.path.name,raw)
        if len(spool.pages)%200==0:print('rerendered',len(spool.pages),flush=True)
    raster_source.release()
    print('derived pages and exact native-scale rerenders',len(spool.pages),flush=True)
    for path in Path('build/pdf-remaining-native-book/pages').glob('candidate-*.json'):
        spool.candidates[int(path.stem.split('-')[1])]=PdfReplayRef(path.resolve(),sha256(path.read_bytes()).hexdigest(),path.stat().st_size,'candidate')
    assert len(spool.pages)==1589
    source=InputDocument(path_or_stream=Path('docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf'),format=InputFormat.PDF,backend=ThreadedDoclingParseDocumentBackend)
    source.file=Path('original.pdf') # Restore the actual owned-source name used by page inference.
    result=ConversionResult(input=source);result.pages=[Page(page_no=n) for n in sorted(spool.pages)]
    result._pdf_outline=source._backend.get_document_outline()
    converter=PdfConverter(recipe,assets=assets,stream_spool=spool)
    try:
        converter._prepare()
        pipeline=next(iter(converter._converter.initialized_pipelines.values()))
        pipeline._assemble_document(result)
        print('assembled',len(result.document.texts),len(result.document.tables),flush=True)
        print('enrichment scales',[(type(m).__name__,getattr(m,'images_scale',None),getattr(getattr(m,'native',None),'images_scale',None)) for m in pipeline.enrichment_pipe],flush=True)
        pipeline._enrich_document(result)
        print('enriched',len(converter._formula.outcomes),flush=True)
        result.document.validate_document()
        stream=StreamingPdfResult(result.document,spool,'success',tuple(str(x) for x in result.errors),recipe.to_bytes(),tuple(converter._formula.outcomes))
        refs=stream.write_record_batches(root/'records',build_id='replayed-native-book',release_id='standalone-provider-qualification',source_digest='e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9')
        receipt={'scope':'actual retained1589page inference + explicit type-preserving assembly derivation/nativeglobal/enrichment replay; no database publication', 'pages':len(spool.pages),'texts':len(result.document.texts),'tables':len(result.document.tables),'formula_outcomes':len(converter._formula.outcomes),'errors':[str(x) for x in result.errors], 'elapsed_seconds':time.monotonic()-started,'replays':[asdict(x) for x in refs]}
        (root/'receipt.json').write_text(json.dumps(receipt,default=str,indent=2)+'\n')
        print(json.dumps({k:v for k,v in receipt.items() if k!='replays'}),flush=True)
    finally:
        source.release();converter._page_lifetime.clear()


if __name__=='__main__':main()
