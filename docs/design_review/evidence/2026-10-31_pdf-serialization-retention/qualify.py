"""One explicit partial-page native conversion through the application preparation boundary."""
from __future__ import annotations

import argparse
import dataclasses
import json
import time
import traceback
from hashlib import sha256
from importlib.resources import files
from pathlib import Path

from corpus_structure.ingest import pdf
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_candidates import CandidatePage,InlineCandidate
from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product

HERE=Path(__file__).resolve().parent
RAW=HERE/'raw'
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['preflight','convert'])
parser.add_argument('--source',type=Path,required=True)
args=parser.parse_args()
started=time.monotonic()
try:
    original=args.source.read_bytes()
    schema=files('corpus_structure').joinpath('model/semantic/docling-validation.schema.json').read_bytes()
    if args.mode=='preflight':
        previous=HERE.parent/'2026-10-31_pdf-native-enrichment'/'raw'
        native_bytes=(previous/'page85.document.json').read_bytes()
        candidate=json.loads((previous/'vector-candidates.json').read_bytes())
        report=json.loads((previous/'result.json').read_bytes())
        conversion=pdf.PdfConversion(sha256(original).hexdigest(),(previous/'recipe.json').read_bytes(),
            NativeSnapshot(native_bytes,sha256(native_bytes).hexdigest(),json.loads(native_bytes)['version']),
            'success',(),(),pdf.pdf_package_versions(),(85,85),tuple(report['runtime'].items()),
            (previous/'page85.effective-options.json').read_bytes(),
            (CandidatePage(candidate['page_no'],candidate['has_words'],candidate['has_chars'],
                tuple(InlineCandidate.from_wire(row) for row in candidate['candidates']),candidate.get('has_vectors',False)),))
    else:
        recipe=pdf.PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8','ecedbe111d15c2dc60bfd4a823cbe80127b58af4')
        assets=prepare_pdf_assets(recipe,cache=Path.home()/'.cache/docling/models')
        recipe=dataclasses.replace(recipe,model_artifacts=assets.files,model_revisions=assets.repositories)
        (RAW/'assets.manifest.json').write_bytes(assets.manifest)
        worker=pdf.PdfConverter(recipe,assets=assets)
        print(json.dumps({'phase':'native-conversion','producer':pdf.__file__,'page_range':[85,85]}),flush=True)
        conversion=worker.convert_bytes(original,name='Full.pdf',page_range=(85,85))
    (RAW/(args.mode+'.native.json')).write_bytes(conversion.native.payload)
    (RAW/(args.mode+'.recipe.json')).write_bytes(conversion.recipe)
    raw_payload=pdf.publication_payload(conversion,product_key='native',schema_digest=sha256(schema).hexdigest(),
                                        include_application_metadata=False)
    raw=prepare_pdf_product(raw_payload,original,schema,conversion.recipe)
    full_payload=pdf.publication_payload(conversion,product_key='qualified',schema_digest=sha256(schema).hexdigest())
    prepared=prepare_pdf_product(full_payload,original,schema,conversion.recipe)
    (RAW/(args.mode+'.payload.json')).write_bytes(prepared.payload)
    (RAW/(args.mode+'.schema.json')).write_bytes(schema)
    result={'outcome':'passed','mode':args.mode,'producer':pdf.__file__,
        'scope':'physical page85 only; no whole-book, source fidelity, or database-publication claim',
        'conversion_status':conversion.conversion_status,'native_digest':conversion.native.digest,
        'raw_product_digest':raw.digest,'application_product_digest':prepared.digest,
        'original_digest':conversion.original_digest,'packages':dict(conversion.packages),
        'runtime':dict(conversion.runtime),'candidate_pages':len(conversion.inline_candidates),
        'candidates':sum(len(page.candidates) for page in conversion.inline_candidates),
        'font_absent':sum(candidate.font is None for page in conversion.inline_candidates for candidate in page.candidates),
        'seconds':time.monotonic()-started}
    if args.mode=='convert':
        result['page_resources_released']=not worker._page_lifetime.pages
        result['confidence']=json.loads(conversion.confidence)
except BaseException as error:
    (RAW/(args.mode+'.failure.txt')).write_text(traceback.format_exc())
    result={'outcome':'failed','mode':args.mode,'error_type':type(error).__name__,'error':str(error)[:1800],
            'seconds':time.monotonic()-started}
    (RAW/(args.mode+'.result.json')).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
    raise
(RAW/(args.mode+'.result.json')).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
