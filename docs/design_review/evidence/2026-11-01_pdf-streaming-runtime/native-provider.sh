#!/usr/bin/env bash
# Run from the repository root; recovered verbatim invocation body.
# Original completed-command timestamp: 2026-11-01T07:45:34.791Z
set -euo pipefail
uv run python - <<'PY' > /tmp/pdf22-native-provider.log 2>&1
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_streaming import StreamingPdfProducer,PdfStreamSpool
from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
r=PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8','ecedbe111d15c2dc60bfd4a823cbe80127b58af4',recipe_id='docling-standard-pdf-stream-v1')
a=prepare_pdf_assets(r,cache=Path.home()/'.cache/docling/models',offline=True)
r=replace(r,model_artifacts=a.files,model_revisions=a.repositories)
with TemporaryDirectory(prefix='pdf22-provider-') as root:
 p=Path(root)
 with OwnedPdfSource.acquire(Path('fixtures/toy/corpus/toy.pdf'),p/'source') as source:
  spool=PdfStreamSpool(p/'spool')
  result=StreamingPdfProducer(r,assets=a).run(source,spool,page_range=(1,2))
  print('STATUS',result.conversion_status,'PAGES',len(spool.pages),'TEXTS',len(result.document.texts),'TABLES',len(result.document.tables),flush=True)
  assert len(spool.pages)==2
  assert len(result.document.texts)>0
  refs=result.write_record_batches(p/'records',build_id='provider-control',release_id='release',source_digest=source.digest)
  print('BATCHES',len(refs),'ERRORS',result.errors,flush=True)
PY
