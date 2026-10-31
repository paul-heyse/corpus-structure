"""Rebuild final-source access rows from the retained conversion, with no model inference."""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path
from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_health import FormulaOutcome
from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot

RAW=Path(__file__).resolve().parent/'raw'
result=json.loads((RAW/'result.json').read_text())
payload=(RAW/'page85.document.json').read_bytes()
conversion=PdfConversion(result['original_digest'],(RAW/'recipe.json').read_bytes(),
    NativeSnapshot(payload,sha256(payload).hexdigest(),result['native_schema_version']),
    result['status'],tuple(result['errors']),
    tuple(FormulaOutcome(**row) for row in result['formula_outcomes']),
    tuple(result['packages'].items()),(85,85),tuple(result['runtime'].items()),
    (RAW/'page85.effective-options.json').read_bytes())
projected=publication_payload(conversion,product_key='page85-native-probe',
    schema_digest=sha256((RAW/'native-validation.schema.json').read_bytes()).hexdigest())
(RAW/'page85.final-projection.payload.json').write_text(json.dumps(projected,indent=2))
print(json.dumps({'outcome':'passed','scope':'final-source pure projection of retained physical page85',
                  'items':len(projected['items']),'regions':len(projected['regions'])}))
