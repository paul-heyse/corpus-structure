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
        pages[number] = {
            key: page[key]
            for key in ("has_words", "has_vectors", "native_text_quality")
            if key in page
        }
        pages[number]["ocr_regions"] = [
            {"outcome": region["outcome"]} for region in page.get("ocr_regions", ())
        ]
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


def validate_pdf_inline_reports(
    product: Mapping[str, Any], *, page_lookup: Mapping[int, Any] | None = None
) -> None:
    """Keep unresolved source correspondence explicit, without inventing text offsets."""
    reports = product.get("inline_alignment_reports", ())
    if not reports:
        return
    if not all(
        product.get(key) is not None
        for key in ("parent_task_id", "parent_product_key", "parent_digest")
    ):
        raise ValueError("inline alignment report requires its original parent product")
    pages = (
        page_lookup
        if page_lookup is not None
        else {page["page_no"]: page for page in product.get("inline_candidate_pages", ())}
    )
    items = {item["pointer"]: item for item in product["items"]}
    seen = set()
    unresolved = set()
    for report in reports:
        key = report["page_no"], report["candidate_index"]
        page = pages.get(report["page_no"])
        if (
            key in seen
            or page is None
            or report["candidate_index"] >= len(page.get("candidates", ()))
        ):
            raise ValueError("inline alignment report has duplicate or unavailable candidate")
        seen.add(key)
        candidate = page["candidates"][report["candidate_index"]]
        pointers = report["item_pointers"]
        if not pointers or len(pointers) != len(set(pointers)) or not report["detail"].strip():
            raise ValueError("inline alignment report needs distinct items and a diagnostic")
        if (report["basis"] == "ambiguous-native-items" and len(pointers) < 2) or (
            report["basis"] == "unmatched-native-text" and len(pointers) != 1
        ):
            raise ValueError("inline alignment basis differs from its item cardinality")
        x = (candidate["left"] + candidate["right"]) / 2
        y = (candidate["top"] + candidate["bottom"]) / 2
        size = product["document"]["pages"][str(report["page_no"])]["size"]
        if candidate["origin"] == "BOTTOMLEFT":
            y = size["height"] - y
        for pointer in pointers:
            item = items.get(pointer)
            if (
                item is None
                or item["label"] not in {"text", "list_item", "caption", "footnote"}
                or item["content_layer"] != "body"
            ):
                raise ValueError("inline alignment report item is not retained body prose")

            def contains(region, x=x, y=y, size=size):
                top, bottom = region["top"], region["bottom"]
                if region["origin"] == "bottom_left":
                    top, bottom = size["height"] - top, size["height"] - bottom
                return region["left"] <= x <= region["right"] and min(top, bottom) <= y <= max(
                    top, bottom
                )

            if not any(
                region["pointer"] == pointer
                and region["page_no"] == report["page_no"]
                and contains(region)
                for region in product.get("regions", ())
            ):
                raise ValueError(
                    "inline alignment report item differs from candidate page geometry"
                )
            unresolved.add(pointer)
    rows = [
        row
        for row in product.get("recognition_coverage", ())
        if row["universe"] == "inline" and row["outcome"] == "complete"
    ]
    health = product["health"]
    if health.get("inline_coverage") == "complete":
        rows += [
            dict(section_pointer=pointer, membership=health["inline_membership"])
            for pointer in health.get("inline_scope", ())
        ]
    for row in rows:
        for pointer in unresolved:
            if row["membership"] == "direct":
                selected = (
                    pointer == row["section_pointer"]
                    or items[pointer].get("section_pointer") == row["section_pointer"]
                )
            else:
                current = pointer
                visited = set()
                selected = False
                while current in items and current not in visited:
                    if current == row["section_pointer"]:
                        selected = True
                        break
                    visited.add(current)
                    current = items[current].get("parent_pointer")
            if selected:
                raise ValueError(
                    "complete inline coverage contains unresolved source correspondence"
                )
