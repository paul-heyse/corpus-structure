#!/usr/bin/env bash
# Run from the repository root; recovered verbatim invocation body.
# Original completed-command timestamp: 2026-11-01T07:47:28.005Z
set -euo pipefail
uv run python - <<'PY' > /tmp/pdf22-native-differential.log 2>&1
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import json,runpy
from corpus_structure.ingest.pdf import PdfRecipe,PdfConverter
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_streaming import StreamingPdfProducer,PdfStreamSpool
from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
from corpus_structure.semantic.pdf_records import _difference
base=PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8','ecedbe111d15c2dc60bfd4a823cbe80127b58af4')
a=prepare_pdf_assets(base,cache=Path.home()/'.cache/docling/models',offline=True)
base=replace(base,model_artifacts=a.files,model_revisions=a.repositories)
stream=replace(base,recipe_id='docling-standard-pdf-stream-v1')
with TemporaryDirectory(prefix='pdf22-differential-') as root:
 p=Path(root)
 with OwnedPdfSource.acquire(Path('fixtures/toy/corpus/toy.pdf'),p/'source') as source:
  expected=json.loads(PdfConverter(base,assets=a).convert(source.path,page_range=(1,2)).native.payload)
  actual=StreamingPdfProducer(stream,assets=a).run(source,PdfStreamSpool(p/'spool'),page_range=(1,2))
  actual_dict=actual.document.export_to_dict()
  difference=_difference(expected,actual_dict)
  print('FIRST DIFFERENCE',difference,flush=True)
  assert difference is None,difference
  authored=runpy.run_path('fixtures/toy/build_pdf.py')['SECTIONS'][:2]
  expected_text=[text for title,paragraphs in authored for text in (title,*paragraphs)]
  actual_text=[' '.join(item.text.split()) for item in actual.document.texts]
  assert actual_text==expected_text,(actual_text,expected_text)
  print('PASSED exact complete native export/tree/order/provenance equality without exclusions; independent five authored text values match',flush=True)
PY
