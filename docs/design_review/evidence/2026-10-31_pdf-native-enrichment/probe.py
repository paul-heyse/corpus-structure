"""One partial page85 conversion and demanded native math crops, not full-book qualification."""
from __future__ import annotations
import dataclasses
import argparse
import json
import traceback
from pathlib import Path
from corpus_structure.ingest.pdf import PdfConverter,PdfRecipe,enrich_cells
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_enrichment import PdfRegionRenderer,table_candidates,positioned_inline_candidates,enrich_inline
from corpus_structure.ingest.pdf_hierarchy import load_snapshot,native_nodes

HERE=Path(__file__).resolve().parent
RAW=HERE/'raw'
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
SOURCE=parser.parse_args().source
recipe=PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8','ecedbe111d15c2dc60bfd4a823cbe80127b58af4',timeout_seconds=600)
try:
    assets=prepare_pdf_assets(recipe,cache=Path.home()/'.cache/docling/models')
    recipe=dataclasses.replace(recipe,model_artifacts=assets.files,model_revisions=assets.repositories)
    (RAW/'recipe.json').write_bytes(recipe.to_bytes())
    (RAW/'assets.manifest.json').write_bytes(assets.manifest)
    original=SOURCE.read_bytes()
    worker=PdfConverter(recipe,assets=assets)
    conversion=worker.convert_bytes(original,name='Full.pdf',page_range=(85,85))
    (RAW/'page85.document.json').write_bytes(conversion.native.payload)
    (RAW/'page85.candidates.json').write_text(json.dumps([dataclasses.asdict(p) for p in conversion.inline_candidates],indent=2))
    (RAW/'page85.effective-options.json').write_bytes(conversion.effective_options)
    result={'conversion':'passed','scope':'physical page85 only; no full-book or source fidelity claim',
        'status':conversion.conversion_status,'errors':conversion.errors,'runtime':dict(conversion.runtime),
        'packages':dict(conversion.packages),'candidate_pages':len(conversion.inline_candidates),
        'inline_candidates':sum(len(p.candidates) for p in conversion.inline_candidates)}
    (RAW/'result.json').write_text(json.dumps(result,indent=2))
    doc=load_snapshot(conversion.native)
    selected=frozenset(p for p,n in native_nodes(doc).items() if n.content_layer.value=='body')
    stage=worker.formula_stage()
    with PdfRegionRenderer(original) as render:
        cells=table_candidates(doc,selected)
        enriched=enrich_cells(conversion.native,cells,stage=stage,render_region=render)
        (RAW/'page85.cells.document.json').write_bytes(enriched.native.payload)
        result.update(cell_enrichment='passed',selected_nonempty_cells=len(cells),cell_outcomes=[dataclasses.asdict(o) for o in enriched.outcomes])
        (RAW/'result.json').write_text(json.dumps(result,indent=2))
        try:
            inline=positioned_inline_candidates(doc,conversion.inline_candidates,selected)
            enriched_inline=enrich_inline(enriched.native,inline,stage=stage,render_region=render)
            (RAW/'page85.inline.document.json').write_bytes(enriched_inline.native.payload)
            result.update(inline_enrichment='passed',positioned_inline=len(inline),inline_outcomes=[dataclasses.asdict(o) for o in enriched_inline.outcomes])
        except Exception as error:
            (RAW/'inline-failure.txt').write_text(traceback.format_exc())
            result.update(inline_enrichment='failed',inline_error=str(error))
    (RAW/'result.json').write_text(json.dumps(result,indent=2))
except Exception as error:
    (RAW/'failure.txt').write_text(traceback.format_exc())
    result={'outcome':'failed','error':str(error),'scope':'single partial page85 native enrichment attempt'}
    (RAW/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
