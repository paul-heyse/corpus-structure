"""Source-qualified OCR word geometry and inventory semantics at native publication."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

OCR_POLICY = "native-font-token-vector-ocr-word-v3"
OCR_ADDRESS = ("ocr_region_index", "ocr_line_index", "ocr_word_index")


def _box(value, prefix=""):
    result = tuple(float(value[prefix + key]) for key in ("left", "top", "right", "bottom"))
    if not all(isfinite(number) for number in result):
        raise ValueError("OCR geometry must be finite")
    return result


def validate_pdf_ocr_pages(product: Mapping[str, Any]) -> None:
    """Validate observed raster/PDF transforms without claiming original glyph positions."""
    document = product["document"]
    pages = {}
    for page in product.get("inline_candidate_pages", ()):
        number = page["page_no"]
        if number in pages or str(number) not in document.get("pages", {}):
            raise ValueError("inline candidate page is duplicate or outside native scope")
        pages[number] = page
        size = document["pages"][str(number)]["size"]
        words = {}
        region_indices = set()
        for region in page.get("ocr_regions", ()):
            region_index = region["region_index"]
            if region_index in region_indices:
                raise ValueError("duplicate OCR region index")
            region_indices.add(region_index)
            left, top, right, bottom = _box(region)
            scale = float(region["scale"])
            width, height = region["raster_width"], region["raster_height"]
            if not (
                isfinite(scale)
                and scale > 0
                and region["orientation"] == 0
                and 0 <= left < right <= size["width"]
                and 0 <= top < bottom <= size["height"]
                and abs((right - left) * scale - width) <= 1
                and abs((bottom - top) * scale - height) <= 1
            ):
                raise ValueError("OCR raster frame differs from its unrotated PDF crop")
            line_indices = set()
            for line in region["lines"]:
                line_index = line["line_index"]
                if line_index in line_indices:
                    raise ValueError("duplicate OCR line index")
                line_indices.add(line_index)
                covered = set()
                previous_end = 0
                word_indices = set()
                for word in line["words"]:
                    word_index = word["word_index"]
                    start, end = word["start"], word["end"]
                    if word_index in word_indices or not (
                        previous_end <= start < end <= len(line["text"])
                        and line["text"][start:end] == word["text"]
                    ):
                        raise ValueError("OCR word differs from its recognized line range")
                    word_indices.add(word_index)
                    previous_end = end
                    covered.update(range(start, end))
                    raster = _box(word, "raster_")
                    projected = _box(word)
                    if not (
                        0 <= raster[0] < raster[2] <= width
                        and 0 <= raster[1] < raster[3] <= height
                        and isfinite(word["confidence"])
                        and 0 <= word["confidence"] <= 1
                        and all(
                            abs(actual - expected) <= 1e-6
                            for actual, expected in zip(
                                projected,
                                (
                                    left + raster[0] / scale,
                                    top + raster[1] / scale,
                                    left + raster[2] / scale,
                                    top + raster[3] / scale,
                                ),
                                strict=True,
                            )
                        )
                    ):
                        raise ValueError("OCR word geometry differs from raster-to-PDF transform")
                    words[region_index, line_index, word_index] = word
                if region["outcome"] == "complete" and any(
                    index not in covered and not char.isspace()
                    for index, char in enumerate(line["text"])
                ):
                    raise ValueError("complete OCR inventory omits recognized line content")
        for candidate in page.get("candidates", ()):
            if (
                candidate["page_no"] != number
                or candidate["origin"] not in {"TOPLEFT", "BOTTOMLEFT"}
                or candidate["basis"]
                not in {
                    "native-math-font-v1",
                    "native-math-token-v1",
                    "native-vector-gap-v1",
                    "ocr-word-token-v1",
                }
            ):
                raise ValueError("inline candidate has an unqualified page/origin/basis")
            box = _box(candidate)
            if not (
                0 <= box[0] <= box[2] <= size["width"]
                and 0 <= min(box[1], box[3]) <= max(box[1], box[3]) <= size["height"]
            ):
                raise ValueError("inline candidate is outside physical page")
            address = tuple(candidate.get(key) for key in OCR_ADDRESS)
            if candidate["basis"] != "ocr-word-token-v1":
                if any(value is not None for value in address):
                    raise ValueError("native candidate cannot relabel OCR word provenance")
                continue
            word = words.get(address)
            if word is None or candidate["origin"] != "TOPLEFT" or "font" in candidate:
                raise ValueError("OCR candidate lacks its complete estimated-word address")
            if candidate["text"] != word["text"] or any(
                abs(actual - expected) > 1e-6
                for actual, expected in zip(box, _box(word), strict=True)
            ):
                raise ValueError("OCR candidate differs from its estimated word")
    rows = [
        row
        for row in product.get("recognition_coverage", ())
        if row["universe"] == "inline"
        and row["policy"] == OCR_POLICY
        and row["outcome"] == "complete"
    ]
    health = product["health"]
    if health.get("candidate_policy") == OCR_POLICY and health.get("inline_coverage") == "complete":
        rows += [
            dict(section_pointer=pointer, membership=health["inline_membership"])
            for pointer in health.get("inline_scope", ())
        ]
    items = {item["pointer"]: item for item in product["items"]}
    for row in rows:

        def selected(pointer, row=row):
            if row["membership"] == "direct":
                return (
                    pointer == row["section_pointer"]
                    or items[pointer].get("section_pointer") == row["section_pointer"]
                )
            seen = set()
            while pointer in items and pointer not in seen:
                if pointer == row["section_pointer"]:
                    return True
                seen.add(pointer)
                pointer = items[pointer].get("parent_pointer")
            return False

        def native(pointer):
            value = document
            for part in pointer[2:].split("/"):
                value = value[int(part)] if isinstance(value, list) else value[part]
            return value

        def prose(pointer, native=native):
            node = native(pointer)
            if node.get("label") not in {"text", "list_item", "caption", "footnote"}:
                return False
            children = node.get("children", ())
            if not children:
                return bool(node.get("text", "").strip())
            return bool(node.get("orig", "").strip()) and any(
                native(child["$ref"]).get("label") == "inline" for child in children
            )

        required = {
            region["page_no"]
            for region in product.get("regions", ())
            if selected(region["pointer"]) and prose(region["pointer"])
        }
        for number in required:
            page = pages.get(number)
            if page is None or not page.get("has_vectors"):
                raise ValueError("complete OCR discovery policy lacks native vector inventory")
            regions = page.get("ocr_regions", ())
            usable = (
                all(region["outcome"] == "complete" for region in regions)
                if regions
                else page["has_words"] and page.get("native_text_quality") != "broken"
            )
            if not usable:
                raise ValueError("complete OCR discovery policy lacks complete word inventory")
