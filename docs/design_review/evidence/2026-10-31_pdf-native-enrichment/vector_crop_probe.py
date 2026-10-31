"""Recognize the already captured native vector-gap regions; no second document conversion."""
import dataclasses,json,traceback
from pathlib import Path
from hashlib import sha256
from corpus_structure.ingest.pdf import PdfRecipe,PdfConverter
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets
from corpus_structure.ingest.pdf_candidates import CandidatePage,InlineCandidate
from corpus_structure.ingest.pdf_enrichment import positioned_inline_candidates,enrich_inline,PdfRegionRenderer
from corpus_structure.ingest.pdf_hierarchy import NativeSnapshot,load_snapshot,native_nodes
RAW=Path(__file__).resolve().parent/'raw'
try:
    recipe=PdfRecipe.from_bytes((RAW/'recipe.json').read_bytes())
    assets=prepare_pdf_assets(recipe,cache=Path.home()/'.cache/docling/models')
    worker=PdfConverter(recipe,assets=assets)
    stage=worker.formula_stage()
    candidate=json.loads((RAW/'vector-candidates.json').read_text())
    page=CandidatePage(candidate['page_no'],candidate['has_words'],candidate['has_chars'],
        tuple(InlineCandidate(**r) for r in candidate['candidates']),candidate['has_vectors'])
    payload=(RAW/'page85.document.json').read_bytes()
    native=NativeSnapshot(payload,sha256(payload).hexdigest(),'1.10.0')
    document=load_snapshot(native)
    selected=frozenset(p for p,n in native_nodes(document).items() if n.content_layer.value=='body')
    positioned=positioned_inline_candidates(document,(page,),selected)
    original=Path('/home/paul/corpus-structure/docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf').read_bytes()
    with PdfRegionRenderer(original) as renderer:
        enriched=enrich_inline(native,positioned,stage=stage,render_region=renderer)
    (RAW/'page85.vector-inline.document.json').write_bytes(enriched.native.payload)
    (RAW/'page85.vector-mappings.json').write_text(json.dumps(enriched.mappings,indent=2))
    doc=load_snapshot(enriched.native)
    result={'outcome':'passed','scope':'demanded vector-gap crops physical page85; no fullbook/fidelity claim',
        'positioned':len(positioned),'outcomes':[dataclasses.asdict(o) for o in enriched.outcomes],
        'recognized':[{'pointer':o.item_ref,'text':o.item_ref and native_nodes(doc)[o.item_ref].text} for o in enriched.outcomes]}
except Exception as error:
    (RAW/'vector-crop-failure.txt').write_text(traceback.format_exc())
    result={'outcome':'failed','error':str(error),'scope':'native vector-gap crop recognition'}
(RAW/'vector-crop-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
