"""One bounded production adapter conversion, explicitly physical page85 only."""
from __future__ import annotations
import dataclasses
import json
import traceback
from pathlib import Path
from hashlib import sha256
from corpus_structure.ingest.pdf import PdfRecipe, PdfConverter, publication_payload
from docling_core.types.doc import DoclingDocument

HERE=Path(__file__).resolve().parent
RAW=HERE/'raw'
SOURCE=Path('/home/paul/corpus-structure/docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf')
recipe=PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8',
                 'ecedbe111d15c2dc60bfd4a823cbe80127b58af4',timeout_seconds=600)
(RAW/'recipe.json').write_bytes(recipe.to_bytes())
try:
    converter=PdfConverter(recipe)
    conversion=converter.convert(SOURCE,page_range=(85,85))
    (RAW/'page85.document.json').write_bytes(conversion.native.payload)
    (RAW/'page85.effective-options.json').write_bytes(conversion.effective_options)
    schema=json.dumps(DoclingDocument.model_json_schema(mode='validation'),sort_keys=True,separators=(',',':')).encode()
    (RAW/'native-validation.schema.json').write_bytes(schema)
    payload=publication_payload(conversion,product_key='page85-native-probe',schema_digest=sha256(schema).hexdigest())
    (RAW/'page85.payload.json').write_text(json.dumps(payload,indent=2))
    result={'outcome':'passed','scope':'one physical page85 production adapter conversion; no fullbook, publication, inline/cell coverage or fidelity claim',
            'original_digest':conversion.original_digest,'native_digest':conversion.native.digest,
            'native_schema_version':conversion.native.schema_version,'status':conversion.conversion_status,
            'errors':conversion.errors,'packages':dict(conversion.packages),'runtime':dict(conversion.runtime),
            'formula_outcomes':[dataclasses.asdict(x) for x in conversion.formula_outcomes],
            'items':len(payload['items']),'regions':len(payload['regions'])}
except Exception as error:
    (RAW/'failure.txt').write_text(traceback.format_exc())
    result={'outcome':'failed','exception':str(error),'scope':'single page85 conversion attempt'}
(RAW/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
