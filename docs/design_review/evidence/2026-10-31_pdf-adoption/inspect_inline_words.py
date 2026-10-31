"""One retained-source page backend word capture; no layout/OCR/formula inference."""
from io import BytesIO
from pathlib import Path
import json
from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument
from docling.datamodel.settings import DocumentLimits

root=Path(__file__).resolve().parents[4]
data=(root/'docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf').read_bytes()
source=InputDocument(BytesIO(data),InputFormat.PDF,ThreadedDoclingParseDocumentBackend,backend_options=ThreadedDoclingParseBackendOptions(parser_threads=1,render_pages=True),filename='Full.pdf',limits=DocumentLimits(page_range=(20,20)))
rows=[]
try:
    for page in source._backend.iter_pages():
        try:
            parsed=page.get_segmented_page()
            height=page.get_size().height
            for index,word in enumerate(parsed.word_cells):
                box=word.rect.to_bounding_box().to_top_left_origin(height)
                if 485<=box.t<=535:
                    rows.append(dict(index=index,text=word.text,left=box.l,top=box.t,right=box.r,bottom=box.b))
        finally:
            page.unload()
finally:
    source.release()
output=Path(__file__).resolve().parent/'raw/inline-page20-native-words.json'
with output.open('x') as f:json.dump(rows,f,indent=2)
for row in rows:print(row)
