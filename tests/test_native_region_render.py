"""PDF canvas units and coordinate origins survive the rendering boundary."""

from io import BytesIO

import pytest
from pdf_region_support import asymmetric_pdf
from PIL import Image

from corpus_structure.serve.native_regions import render_pdf_region


def test_pdf_point_region_origins_and_dimensions():
    source = asymmetric_pdf()
    region = dict(
        page_no=1,
        page_width=200,
        page_height=300,
        left=20,
        right=80,
        top=30,
        bottom=70,
        origin="top_left",
    )
    first = render_pdf_region(source, region, scale=2)
    alternate = dict(region, top=270, bottom=230, origin="bottom_left")
    assert render_pdf_region(source, alternate, scale=2) == first
    with Image.open(BytesIO(first)) as image:
        assert image.size == (120, 80)
        assert image.convert("RGB").getpixel((40, 40)) == (255, 0, 0)
        assert image.convert("RGB").getpixel((100, 20)) == (0, 128, 0)
        assert image.convert("RGB").getpixel((5, 5)) == (255, 255, 255)
    translated = render_pdf_region(source, dict(region, left=80, right=140), scale=2)
    assert translated != first
    with Image.open(BytesIO(translated)) as image:
        assert image.size == (120, 80)
        assert image.convert("RGB").getpixel((40, 40)) == (0, 0, 255)
    with pytest.raises(ValueError, match="dimensions"):
        render_pdf_region(source, dict(region, page_width=201))
    with pytest.raises(ValueError, match="invalid"):
        render_pdf_region(source, dict(region, left=-1))
