"""Bounded direct CPU RapidOCR word output and known crop-to-PDF geometry; no GPU models."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.pipeline_options import RapidOcrOptions
from docling.models.stages.ocr.rapid_ocr_model import RapidOcrModel
from docling.utils.orientation import ocr_box_to_bounding_rectangle
from docling_core.types.doc import BoundingBox,CoordOrigin
from rapidocr.utils.output import RapidOCROutput

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import prepare_pdf_assets

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=HERE/'raw/cpu-word-output.json')
output=parser.parse_args().output
if output.exists():
    raise FileExistsError('retained CPU output exists; select a fresh --output file')
output.parent.mkdir(parents=True,exist_ok=True)
started=time.monotonic()
recipe=PdfRecipe('8f39ad3c0b4c58e9c2d2c84a38465abf757272d8','ecedbe111d15c2dc60bfd4a823cbe80127b58af4',device='cpu',parser_threads=2)
assets=prepare_pdf_assets(recipe,cache=Path.home()/'.cache/docling/models')
options=recipe.options().ocr_options
assert isinstance(options,RapidOcrOptions)
model=RapidOcrModel(enabled=True,artifacts_path=assets.root,options=options,
    accelerator_options=AcceleratorOptions(num_threads=2,device='cpu'))
with Image.open(HERE/'inputs/expected-raster.png') as image:
    raster=np.asarray(image)
    plain=model.reader(raster,return_word_box=False)
    rich=model.reader(raster,return_word_box=True)
assert isinstance(plain,RapidOCROutput) and isinstance(rich,RapidOCROutput)
assert plain.txts==rich.txts
assert rich.word_results
import pypdfium2
pdf=pypdfium2.PdfDocument(HERE/'inputs/raster-only.pdf')
page=pdf[0]
assert page.get_size()==(700,250)
page.close();pdf.close()
frame=BoundingBox(l=0,t=0,r=700,b=250,coord_origin=CoordOrigin.TOPLEFT)
words=[]
for line_index,line in enumerate(rich.word_results):
    for word_index,(text,confidence,polygon) in enumerate(line):
        assert polygon is not None
        box=np.asarray(polygon)
        bbox=BoundingBox(l=float(box[:,0].min()),t=float(box[:,1].min()),
            r=float(box[:,0].max()),b=float(box[:,1].max()),coord_origin=CoordOrigin.TOPLEFT)
        transformed=ocr_box_to_bounding_rectangle(bbox,original_offset=frame,scale=2,
            orientation=0,im_size=(1400,500)).to_bounding_box()
        assert 0<=transformed.l<transformed.r<=700 and 0<=transformed.t<transformed.b<=250
        words.append(dict(line_index=line_index,word_index=word_index,text=text,confidence=float(confidence),
            raster_box=bbox.model_dump(mode='json'),pdf_box=transformed.model_dump(mode='json'),
            geometry='provider_estimated_word_box; not original PDF glyph custody'))
providers={name:getattr(model.reader,'text_'+name).session.session.get_providers() for name in ('det','cls','rec')}
assert all(value==['CPUExecutionProvider'] for value in providers.values())
value={'outcome':'passed','scope':'one controlled raster; CPU OCR word-output/transform capability, no universal fidelity claim',
       'seconds':time.monotonic()-started,'plain_text':plain.txts,'rich_text':rich.txts,
       'raster_frame':{'width':1400,'height':500,'origin':'top_left','unit':'pixel'},
       'pdf_frame':{'width':700,'height':250,'origin':'top_left','unit':'point'},
       'transform':{'scale':2,'crop_left':0,'crop_top':0,'orientation':0},
       'providers':providers,'words':words}
output.write_text(json.dumps(value,indent=2))
print(json.dumps({key:value for key,value in value.items() if key!='words'},indent=2))
print('word_count',len(words))
