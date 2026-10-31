"""Actual final spawned native worker: one owner, three fixed one-page OCR inputs."""
from __future__ import annotations
import argparse
import dataclasses
import json
import time
from pathlib import Path
from corpus_structure.ingest.pdf import PdfRecipe, publication_payload
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_worker import PdfWorker

HERE = Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=HERE/'raw')
    output=parser.parse_args().output
    output.mkdir(parents=True,exist_ok=True)
    if any(output.glob('*-native.json')):
        raise FileExistsError('retained native outputs already exist; select a fresh --output directory')
    recipe = PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8', 'ecedbe111d15c2dc60bfd4a823cbe80127b58af4', parser_threads=2)
    assets = prepare_pdf_assets(recipe, cache=Path.home()/'.cache/docling/models')
    recipe = dataclasses.replace(recipe, model_artifacts=assets.files, model_revisions=assets.repositories)
    worker = PdfWorker(recipe, assets=assets)
    results=[]
    try:
        for name in ('raster-only', 'broken-visible', 'broken-invisible'):
            started=time.monotonic()
            original=(HERE/'inputs'/f'{name}.pdf').read_bytes()
            converted=worker.convert_bytes(original,name=f'{name}.pdf')
            record=dict(name=name,seconds=time.monotonic()-started,pid=worker.pid,status=converted.conversion_status,
                errors=converted.errors,candidates=[p.to_wire() for p in converted.inline_candidates],
                native_digest=converted.native.digest,packages=converted.packages,runtime=converted.runtime)
            (output/f'{name}-native.json').write_bytes(converted.native.payload)
            from docling_core.types.doc import DoclingDocument
            (output/f'{name}-schema.json').write_text(json.dumps(DoclingDocument.model_json_schema()))
            (output/f'{name}-recipe.json').write_bytes(converted.recipe)
            (output/f'{name}-report.json').write_text(json.dumps(record,indent=2))
            print(json.dumps(record),flush=True)
            results.append(record)
    finally:
        pid=worker.pid
        worker.close()
        print(json.dumps(dict(event='child_closed',pid=pid,closed=worker.closed,live_pid=worker.pid)),flush=True)
    assert len({r['pid'] for r in results})==1
    assert all(r['status']=='success' for r in results)
    for record in results:
        native=json.loads((output/f"{record['name']}-native.json").read_bytes())
        text='\n'.join(item.get('text','') for item in native['texts'])
        assert 'Controlled raster input 314159.' in text, (record['name'],text)
        assert 'A second independent line.' in text,(record['name'],text)
        page=record['candidates'][0]
        assert page['native_text_quality']==('broken' if record['name']=='broken-visible' else 'not_flagged')
        assert page['ocr_regions']
        assert all(r['outcome']=='complete' for r in page['ocr_regions'])
        assert sum(len(line['words']) for region in page['ocr_regions'] for line in region['lines'])==8
    print('passed controlled native OCR triplet; no universal OCR fidelity claim',flush=True)

if __name__=='__main__':
    main()
