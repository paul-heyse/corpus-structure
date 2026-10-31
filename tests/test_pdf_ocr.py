"""Word-observation contracts with independent geometry and incomplete-output controls."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin
from PIL import Image
from rapidocr.utils.output import RapidOCROutput

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_candidates import CandidatePage, capture_candidates
from corpus_structure.ingest.pdf_ocr import observed_rapid_ocr_type


@pytest.mark.parametrize(
    "word_text,word_left,expected",
    [("x", 3, "complete"), ("unmatched", 3, "partial"), ("x", -3, "partial")],
)
def test_observed_words_preserve_native_line_and_qualified_crop_transform(
    word_text, word_left, expected
):
    stage_type = observed_rapid_ocr_type({})
    stage: Any = object.__new__(stage_type)
    stage.options = SimpleNamespace(use_det=True, use_cls=True, use_rec=True)
    stage.scale = 3
    stage._regions = []
    stage._pending_rects = [BoundingBox(l=20, t=30, r=120, b=60, coord_origin=CoordOrigin.TOPLEFT)]
    result = RapidOCROutput(
        boxes=np.asarray([[[0, 0], [90, 0], [90, 30], [0, 30]]]),
        txts=("x",),
        scores=(0.9,),
    )
    # Actual provider's nested line->word shape differs from its shipped annotation.
    result.__dict__["word_results"] = (
        ((word_text, 0.8, [[word_left, 6], [33, 6], [33, 21], [word_left, 21]]),),
    )
    calls = []

    def reader(image, **kwargs):
        calls.append(kwargs)
        return result

    stage.reader = reader
    with Image.new("RGB", (300, 90)) as image:
        lines = stage._read(image)
    assert lines == [([[0, 0], [90, 0], [90, 30], [0, 30]], "x", 0.9)]
    assert calls[0]["return_word_box"] is True
    region = stage._regions[0]
    assert region["outcome"] == expected
    if expected == "complete":
        word = region["lines"][0]["words"][0]
        assert (word["start"], word["end"]) == (0, 1)
        assert (word["left"], word["top"], word["right"], word["bottom"]) == (21, 32, 31, 37)
    else:
        assert region["lines"][0]["words"] == []


def test_incomplete_ocr_words_do_not_become_native_glyph_or_successful_empty_coverage():
    partial = CandidatePage(1, True, False, (), True, "broken", ({"outcome": "partial"},))
    assert partial.usable_words is False
    assert CandidatePage(1, True, False, (), True, "broken").usable_words is False
    assert CandidatePage(
        1, False, False, (), True, "not_flagged", ({"outcome": "complete"},)
    ).usable_words


def test_ocr_token_candidate_has_word_address_and_no_native_font():
    page = SimpleNamespace(
        page_no=1, parsed_page=SimpleNamespace(word_cells=[], has_words=False, has_chars=False)
    )
    observed = dict(
        native_text_quality="broken",
        ocr_regions=(
            {
                "region_index": 0,
                "outcome": "complete",
                "lines": [
                    {
                        "line_index": 0,
                        "text": "a = b",
                        "words": [
                            {
                                "word_index": 1,
                                "text": "=",
                                "start": 2,
                                "end": 3,
                                "left": 10.0,
                                "top": 20.0,
                                "right": 30.0,
                                "bottom": 40.0,
                            }
                        ],
                    }
                ],
            },
        ),
    )
    result = capture_candidates(page, observed)
    (candidate,) = result.candidates
    assert candidate.basis == "ocr-word-token-v1"
    assert (candidate.ocr_region_index, candidate.ocr_line_index, candidate.ocr_word_index) == (
        0,
        0,
        1,
    )
    assert candidate.font is None
    assert "font" not in candidate.to_wire()
    assert candidate.before == "a " and candidate.after == " b"


def test_recipe_v1_archives_remain_decodable_while_v2_changes_observation_identity():
    old = PdfRecipe("a" * 40, "b" * 40, recipe_id="docling-standard-pdf-v1")
    new = PdfRecipe("a" * 40, "b" * 40)
    assert new.recipe_id == "docling-standard-pdf-v3"
    assert old.digest != new.digest
    assert PdfRecipe.from_bytes(old.to_bytes()) == old
    assert old.options().model_dump() == new.options().model_dump()
