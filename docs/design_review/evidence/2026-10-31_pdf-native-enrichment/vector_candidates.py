"""One-page native backend geometry qualification; no layout/OCR/formula inference."""
import dataclasses,json
from pathlib import Path
from types import SimpleNamespace
from docling_parse.pdf_parser import DoclingThreadedPdfParser,ThreadedPdfParserConfig
from docling.backend.docling_parse_backend import ThreadedDoclingParsePageBackend
from corpus_structure.ingest.pdf_candidates import capture_candidates
from corpus_structure.ingest.pdf_hierarchy import load_snapshot,NativeSnapshot,native_nodes
from corpus_structure.ingest.pdf_enrichment import positioned_inline_candidates
from hashlib import sha256
RAW=Path(__file__).resolve().parent/'raw'
parser=DoclingThreadedPdfParser(parser_config=ThreadedPdfParserConfig(threads=1))
key=parser.load('/home/paul/corpus-structure/docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf',page_numbers=[85])
result=next(parser.iterate_results())
backend=ThreadedDoclingParsePageBackend(result,rendered=False)
page=SimpleNamespace(page_no=85,size=backend.get_size(),parsed_page=backend.get_segmented_page(),_backend=backend)
print("connected",len(backend.get_connected_shape_bounding_boxes(tolerance=2.0)), [b.model_dump(mode="json") for b in backend.get_connected_shape_bounding_boxes(tolerance=2.0)][:3], flush=True)
candidates=capture_candidates(page)
(RAW/'vector-candidates.json').write_text(json.dumps(dataclasses.asdict(candidates),indent=2))
body=(RAW/'page85.document.json').read_bytes()
doc=load_snapshot(NativeSnapshot(body,sha256(body).hexdigest(),'1.10.0'))
selected=frozenset(p for p,n in native_nodes(doc).items() if n.content_layer.value=='body')
try:
    positioned=positioned_inline_candidates(doc,(candidates,),selected)
    output={'outcome':'passed','candidates':len(candidates.candidates),'positioned':[dataclasses.asdict(p) for p in positioned]}
except Exception as error:
    output={'outcome':'failed','candidates':len(candidates.candidates),'error':str(error)}
(RAW/'vector-positioning.json').write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))
parser.unload(key)
