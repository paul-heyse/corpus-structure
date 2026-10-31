"""PDF canvas units and coordinate origins survive the rendering boundary."""
from io import BytesIO

import pytest
from PIL import Image
import pypdfium2 as pdfium

from corpus_structure.serve.native_regions import render_pdf_region


def original():
    document=pdfium.PdfDocument.new()
    try:
        page=document.new_page(200,300)
        page.close()
        output=BytesIO()
        document.save(output)
        return output.getvalue()
    finally:
        document.close()


def test_pdf_point_region_origins_and_dimensions():
    source=original()
    region=dict(page_no=1,page_width=200,page_height=300,left=20,right=80,top=30,bottom=70,origin='top_left')
    first=render_pdf_region(source,region,scale=2)
    alternate=dict(region,top=270,bottom=230,origin='bottom_left')
    assert render_pdf_region(source,alternate,scale=2)==first
    with Image.open(BytesIO(first)) as image:
        assert image.size==(120,80)
    with pytest.raises(ValueError,match='dimensions'):
        render_pdf_region(source,dict(region,page_width=201))
    with pytest.raises(ValueError,match='invalid'):
        render_pdf_region(source,dict(region,left=-1))
