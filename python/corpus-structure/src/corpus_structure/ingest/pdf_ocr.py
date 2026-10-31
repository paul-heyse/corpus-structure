"""Finite native RapidOCR word observation; recognized geometry is not PDF glyph custody."""

from __future__ import annotations

from math import isfinite
from typing import Any


def observed_rapid_ocr_type(observations: dict[int, dict[str, Any]]) -> type:
    """Build an operation-owned native stage without changing the native line output."""
    import numpy as np
    from docling.models.stages.ocr.rapid_ocr_model import RapidOcrModel
    from docling.utils.orientation import ocr_box_to_bounding_rectangle
    from docling_core.types.doc import BoundingBox, CoordOrigin
    from pydantic import TypeAdapter, ValidationError
    from rapidocr.utils.output import RapidOCROutput

    # RapidOCR's installed field annotation describes one word, but the runtime
    # returns one sequence of words per recognized line. Validate that external
    # nested output explicitly instead of pretending its annotation is accurate.
    word_adapter = TypeAdapter(
        tuple[tuple[tuple[str, float, tuple[tuple[float, float], ...] | None], ...], ...]
    )

    class ObservedRapidOcr(RapidOcrModel):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            if self.options.detect_orientation:
                raise ValueError("word observation admits only unrotated native OCR regions")
            self._regions: list[dict[str, Any]] = []
            self._pending_rects: list[Any] = []

        def get_ocr_rects(self, page: Any) -> Any:
            rects = super().get_ocr_rects(page)
            self._pending_rects = [rect for rect in rects if rect.area() > 0]
            return rects

        def _read(self, image: Any) -> Any:
            rect = self._pending_rects.pop(0)
            result = self.reader(
                np.asarray(image),
                use_det=self.options.use_det,
                use_cls=self.options.use_cls,
                use_rec=self.options.use_rec,
                return_word_box=True,
            )
            region: dict[str, Any] = dict(
                region_index=len(self._regions),
                engine="rapidocr",
                raster_width=image.width,
                raster_height=image.height,
                scale=float(self.scale),
                orientation=0,
                left=float(rect.l),
                top=float(rect.t),
                right=float(rect.r),
                bottom=float(rect.b),
                outcome="unknown",
                lines=[],
            )
            self._regions.append(region)
            if (
                not isinstance(result, RapidOCROutput)
                or result.boxes is None
                or result.txts is None
                or result.scores is None
            ):
                return None
            region["outcome"] = "complete"
            try:
                word_lines = word_adapter.validate_python(result.word_results)
            except ValidationError:
                word_lines = ()
                region["outcome"] = "partial"
            for line_index, text in enumerate(result.txts):
                line = dict(line_index=line_index, text=text, words=[])
                region["lines"].append(line)
                words = word_lines[line_index] if line_index < len(word_lines) else ()
                cursor = 0
                if text.strip() and not words:
                    region["outcome"] = "partial"
                for word_index, (word, confidence, polygon) in enumerate(words):
                    start = text.find(word, cursor)
                    if not word or start < 0 or polygon is None or len(polygon) != 4:
                        region["outcome"] = "partial"
                        continue
                    cursor = start + len(word)
                    points = np.asarray(polygon)
                    box = BoundingBox(
                        l=float(points[:, 0].min()),
                        t=float(points[:, 1].min()),
                        r=float(points[:, 0].max()),
                        b=float(points[:, 1].max()),
                        coord_origin=CoordOrigin.TOPLEFT,
                    )
                    if (
                        not all(
                            isfinite(value) for value in (box.l, box.t, box.r, box.b, confidence)
                        )
                        or not 0 <= confidence <= 1
                        or not 0 <= box.l < box.r <= image.width
                        or not 0 <= box.t < box.b <= image.height
                    ):
                        region["outcome"] = "partial"
                        continue
                    mapped = ocr_box_to_bounding_rectangle(
                        box,
                        original_offset=rect,
                        scale=self.scale,
                        orientation=0,
                        im_size=image.size,
                    ).to_bounding_box()
                    line["words"].append(
                        dict(
                            word_index=word_index,
                            text=word,
                            confidence=float(confidence),
                            start=start,
                            end=cursor,
                            raster_left=box.l,
                            raster_top=box.t,
                            raster_right=box.r,
                            raster_bottom=box.b,
                            left=mapped.l,
                            top=mapped.t,
                            right=mapped.r,
                            bottom=mapped.b,
                        )
                    )
                covered = [False] * len(text)
                for word in line["words"]:
                    covered[word["start"] : word["end"]] = [True] * (word["end"] - word["start"])
                if any(
                    not known and not char.isspace()
                    for char, known in zip(text, covered, strict=True)
                ):
                    region["outcome"] = "partial"
            return list(zip(result.boxes.tolist(), result.txts, result.scores, strict=True))

        def __call__(self, conv_res: Any, page_batch: Any) -> Any:
            for page in page_batch:
                self._regions = []
                for result in super().__call__(conv_res, [page]):
                    observations[page.page_no] = dict(
                        native_text_quality="broken" if page._broken_text_layer else "not_flagged",
                        ocr_regions=tuple(self._regions),
                    )
                    yield result

    return ObservedRapidOcr
