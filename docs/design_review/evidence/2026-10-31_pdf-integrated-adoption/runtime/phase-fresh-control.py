"""Actual bounded lifecycle control; coordinator owns publication acceptance."""
from pathlib import Path
import dataclasses
import importlib.util
import json
import subprocess
import time

def main():
    from corpus_structure.ingest.pdf_methods import IngestPdf,PdfRuntimeConfig
    from corpus_structure.ingest.pdf_worker import PdfWorker
    from corpus_structure.ingest.pdf_recognition import NemotronRecipe,PreparedRecognitionSource,RecognitionWorker
    out=Path('/home/paul/corpus-structure/docs/design_review/evidence/2026-10-31_pdf-integrated-adoption/runtime')
    from corpus_structure.ingest.pdf_capacity import native_before_nemotron
    def gpu():
        return subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip()
    events=[]
    source=PreparedRecognitionSource.prepare(Path('/home/paul/corpus-structure/fixtures/toy/corpus/toy.pdf').read_bytes())
    recipe,assets=IngestPdf()._runtime(PdfRuntimeConfig())
    events.append({'stage':'before_sleep','gpu_memory_mib':gpu()})
    with native_before_nemotron('http://127.0.0.1:8035/v1'):
        events.append({'stage':'sleep_acknowledged','gpu_memory_mib':gpu()})
        child=PdfWorker(recipe,assets=assets)
        try:
            conversion=child.convert_bytes(source.original,name='toy.pdf')
            events.append({'stage':'standard_finished','status':conversion.conversion_status,'pid':child.pid,'gpu_memory_mib':gpu(),'runtime':dict(conversion.runtime),'pages':len(json.loads(conversion.native.payload)['pages'])})
            if conversion.conversion_status!='success':raise RuntimeError(conversion.errors)
        finally:
            child.close()
        events.append({'stage':'native_child_closed','pid':child.pid,'gpu_memory_mib':gpu()})
    events.append({'stage':'wake_acknowledged','gpu_memory_mib':gpu()})
    manifest=json.loads((out/'model-manifest.json').read_bytes())
    recognize=NemotronRecipe(manifest['artifacts']['model.safetensors'],manifest['artifacts']['tokenizer.json'])
    worker=RecognitionWorker(python=Path('/home/paul/.cache/corpus-structure/nemotron-runtime-py312/bin/python'),script=Path('/home/paul/corpus-structure/services/nemotron-parse/worker.py'),endpoint='http://127.0.0.1:8035/v1',receipts=out/'toy-pages')
    for page in worker.recognize_pages(source,recognize,[1,2,3],concurrency=3):
        events.append({'stage':'triple_finished','page':page.page_no,'outcome':page.result['outcome'],'requests':len(list(page.requests())),'directory':str(page.directory)})
        if not page.succeeded:raise RuntimeError(page.result)
    (out/'phase-fresh-control.json').write_text(json.dumps({'date':'2026-10-31','outcome':'passed','scope':'sleep -> actual CUDA Standard toy -> close child -> wake -> real triple; no database publication claim','events':events},indent=2)+'\n')
    print(json.dumps(events,indent=2),flush=True)
if __name__=='__main__':main()
