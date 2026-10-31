"""CPU-only independent raster/broken-layer sources; no OCR or model inference."""
from __future__ import annotations

import argparse
import ctypes
import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
import pypdfium2 as pdfium
import pypdfium2.raw as raw

from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument
from docling.datamodel.settings import DocumentLimits
from docling.utils.text_quality import is_broken_text_layer

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=HERE/'inputs')
INPUTS=parser.parse_args().output
INPUTS.mkdir(parents=True,exist_ok=True)
if any(INPUTS.iterdir()):
    raise FileExistsError('source destination must be empty; retained fixtures are immutable')
LINES=('Controlled raster input 314159.','A second independent line.')
image=Image.new('RGB',(1400,500),'white')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',54)
draw=ImageDraw.Draw(image)
for index,line in enumerate(LINES):
    draw.text((70,90+index*120),line,font=font,fill='black')
image.save(INPUTS/'expected-raster.png')
image.save(INPUTS/'raster-only.pdf','PDF',resolution=144,quality=100)
image.close()

# A visible rendering mode with white fill preserves the raster while deliberately
# presenting a corrupt native text layer. Invisible text is a separate control:
# Docling correctly excludes that layer from its visible broken-text decision.
for name,invisible in [('broken-visible',False),('broken-invisible',True)]:
    document=pdfium.PdfDocument(INPUTS/'raster-only.pdf')
    page=document[0]
    handle=raw.FPDFPageObj_NewTextObj(document,b'Helvetica',1)
    assert handle
    encoded=('\ufffd'*80+'\0').encode('utf-16-le')
    assert raw.FPDFText_SetText(handle,ctypes.cast(encoded,raw.FPDF_WIDESTRING))
    assert raw.FPDFPageObj_SetFillColor(handle,255,255,255,255)
    if invisible:
        assert raw.FPDFTextObj_SetTextRenderMode(handle,raw.FPDF_TEXTRENDERMODE_INVISIBLE)
    raw.FPDFPageObj_Transform(handle,1,0,0,1,10,10)
    obj=pdfium.PdfObject(handle,pdf=document)
    page.insert_obj(obj)
    page.gen_content()
    document.save(INPUTS/(name+'.pdf'),version=17)
    page.close();document.close()

reports=[]
for name in ('raster-only','broken-visible','broken-invisible'):
    path=INPUTS/(name+'.pdf')
    data=path.read_bytes()
    document=pdfium.PdfDocument(data)
    page=document[0]
    textpage=page.get_textpage()
    pdfium_text=textpage.get_text_range()
    textpage.close()
    bitmap=page.render(scale=1)
    rendered=bitmap.to_pil()
    pixel_digest=sha256(rendered.tobytes()).hexdigest()
    rendered.close();bitmap.close();page.close();document.close()
    source=InputDocument(BytesIO(data),InputFormat.PDF,ThreadedDoclingParseDocumentBackend,
        backend_options=ThreadedDoclingParseBackendOptions(parser_threads=1,render_pages=False),
        filename=path.name,limits=DocumentLimits(page_range=(1,1)))
    try:
        backend=source._backend
        assert isinstance(backend,ThreadedDoclingParseDocumentBackend)
        for native in backend.iter_pages():
            try:
                parsed=native.get_segmented_page()
                assert parsed is not None
                visible=native.get_visible_text_cells() or []
                text='\n'.join(cell.text for cell in visible)
                reports.append(dict(name=name,sha256=sha256(data).hexdigest(),
                    pdfium_text=pdfium_text,native_text='\n'.join(cell.text for cell in parsed.textline_cells),
                    visible_native_text=text,has_words=parsed.has_words,
                    broken_visible_layer=is_broken_text_layer(text),render_pixel_digest=pixel_digest))
            finally:
                native.unload()
    finally:
        source.release()
manifest={'outcome':'prepared_cpu_only','expected_lines':LINES,
    'font_path':font.path,'font_sha256':sha256(Path(font.path).read_bytes()).hexdigest(),'sources':reports}
(INPUTS/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
assert reports[0]['visible_native_text']==''
assert reports[1]['broken_visible_layer'] is True
assert reports[2]['broken_visible_layer'] is False
assert len({report['render_pixel_digest'] for report in reports})==1
