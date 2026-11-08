from io import BytesIO

import pytest
from PIL import Image

from corpus_structure.ingest.pdf_chandra import parse_chandra_response
from corpus_structure.ingest.pdf_recognition import transform_point
from corpus_structure.semantic.pdf_visual_mapping import map_visual_result, render_visual_input

from .test_pdf_recognition import landmark_pdf


def test_visual_crop_rotation_preserves_original_landmark():
    original = landmark_pdf()
    region = {
        "page_no": 2,
        "page_width": 400.0,
        "page_height": 300.0,
        "left": 300.0,
        "top": 20.0,
        "right": 370.0,
        "bottom": 70.0,
        "origin": "top_left",
    }
    png, frame = render_visual_input(original, 2, region, rotation=90)
    with Image.open(BytesIO(png)) as image:
        assert image.size == (100, 140)
        assert image.getpixel((60, 60)) == (255, 0, 0)
    assert transform_point(frame["affine"], 90, 170) == pytest.approx((60, 60))


def test_mapped_child_table_inherits_picture_region_without_exact_cell_geometry():
    raw = (
        '<div data-label="Figure" data-bbox="100 200 700 800">'
        "<table><tr><th>Heading</th></tr><tr><td>value</td></tr></table></div>"
    )
    parsed = parse_chandra_response(raw, image_size=(200, 400), page_no=2)
    assert parsed.document is not None
    result = map_visual_result(
        parsed.document,
        page_no=2,
        transform={"affine": [2, 0, 0, 2, 0, 0], "page_width": 100, "page_height": 200},
        image_size=(200, 400),
    )
    picture, child = result.rows
    assert picture.kind == "picture" and child.kind == "table"
    assert picture.source_region is not None and child.source_region is not None
    assert child.source_region.enclosing_occurrence_id == picture.occurrence_id
    assert (child.source_region.left, child.source_region.top) == (10, 40)
    assert [cell.text for cell in child.cells] == ["Heading", "value"]
