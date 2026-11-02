"""Source-qualified OCR word geometry and inventory semantics at native publication."""

from __future__ import annotations

from collections import defaultdict
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


class _SourceIndex:
    """Invocation-local native facts, retaining every region and original pointer."""

    def __init__(self, product):
        self.document = product["document"]
        self.items = {item["pointer"]: item for item in product["items"]}
        self.regions = defaultdict(list)
        for region in product.get("regions", ()):
            self.regions[region["pointer"], region["page_no"]].append(region)
        self._ancestry = {}
        self._prose = {}

    def ancestors(self, pointer):
        if pointer not in self._ancestry:
            current, seen = pointer, set()
            while current in self.items and current not in seen:
                seen.add(current)
                current = self.items[current].get("parent_pointer")
            self._ancestry[pointer] = frozenset(seen)
        return self._ancestry[pointer]

    def selected(self, pointer, scope):
        if scope["membership"] == "direct":
            return pointer == scope["section_pointer"] or (
                self.items[pointer].get("section_pointer") == scope["section_pointer"]
            )
        return scope["section_pointer"] in self.ancestors(pointer)

    def native(self, pointer):
        value = self.document
        for part in pointer[2:].split("/"):
            value = value[int(part)] if isinstance(value, list) else value[part]
        return value

    def prose(self, pointer):
        if pointer not in self._prose:
            node = self.native(pointer)
            children = node.get("children", ())
            self._prose[pointer] = node.get("label") in {
                "text",
                "list_item",
                "caption",
                "footnote",
            } and (
                bool(node.get("text", "").strip())
                if not children
                else (
                    bool(node.get("orig", "").strip())
                    and any(
                        self.native(child["$ref"]).get("label") == "inline" for child in children
                    )
                )
            )
        return self._prose[pointer]


def _validate_ocr_page(page, size):
    number = page["page_no"]
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
        lines = region.get("lines")
        if lines is None:
            raise ValueError(
                "OCR region line inventory metadata is unavailable; retain observed lines"
            )
        line_indices = set()
        for line in lines:
            line_index = line["line_index"]
            if line_index in line_indices:
                raise ValueError("duplicate OCR line index")
            line_indices.add(line_index)
            covered = set()
            previous_end = 0
            word_indices = set()
            line_words = line.get("words")
            if line_words is None:
                raise ValueError(
                    "OCR line word inventory metadata is unavailable; retain observed words"
                )
            for word in line_words:
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
            abs(actual - expected) > 1e-6 for actual, expected in zip(box, _box(word), strict=True)
        ):
            raise ValueError("OCR candidate differs from its estimated word")
    regions = page.get("ocr_regions", ())
    return {
        **{
            key: page[key]
            for key in ("has_words", "has_vectors", "native_text_quality")
            if key in page
        },
        # None means no observed OCR regions: retain the native-word fallback,
        # rather than equate an empty observation inventory with complete OCR.
        "ocr_regions_complete": all(region["outcome"] == "complete" for region in regions)
        if regions
        else None,
    }


def _validate_ocr_coverage(product, pages, index):
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
    if not rows:
        return
    # Index only requested complete scopes, rather than rescan all native regions
    # and resolve the same prose/ancestor path for each coverage declaration.
    required = {(row["section_pointer"], row["membership"]): set() for row in rows}
    direct = {pointer for pointer, membership in required if membership == "direct"}
    descendants = defaultdict(set)
    for pointer, membership in required:
        if membership != "direct":
            descendants[pointer].add(membership)
    for pointer, number in index.regions:
        direct_scopes = (
            direct.intersection({pointer, index.items[pointer].get("section_pointer")})
            if direct
            else ()
        )
        descendant_scopes = (
            index.ancestors(pointer).intersection(descendants) if descendants else ()
        )
        if not (direct_scopes or descendant_scopes) or not index.prose(pointer):
            continue
        for scope in direct_scopes:
            required[scope, "direct"].add(number)
        for scope in descendant_scopes:
            for membership in descendants[scope]:
                required[scope, membership].add(number)
    for numbers in required.values():
        for number in numbers:
            page = pages.get(number)
            if page is None or not page.get("has_vectors"):
                raise ValueError("complete OCR discovery policy lacks native vector inventory")
            complete = page["ocr_regions_complete"]
            usable = (
                complete
                if complete is not None
                else (page["has_words"] and page.get("native_text_quality") != "broken")
            )
            if not usable:
                raise ValueError("complete OCR discovery policy lacks complete word inventory")


def _require_inline_parent(product, reports):
    if reports and not all(
        product.get(key) is not None
        for key in ("parent_task_id", "parent_product_key", "parent_digest")
    ):
        raise ValueError("inline alignment report requires its original parent product")


def _validate_inline_report(product, report, page, index, seen, unresolved):
    items = index.items
    key = report["page_no"], report["candidate_index"]
    if (
        key in seen
        or page is None
        or not 0 <= report["candidate_index"] < len(page.get("candidates", ()))
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
            for region in index.regions.get((pointer, report["page_no"]), ())
        ):
            raise ValueError("inline alignment report item differs from candidate page geometry")
        unresolved.add(pointer)


def _validate_inline_coverage(product, unresolved, index):
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
        if any(index.selected(pointer, row) for pointer in unresolved):
            raise ValueError("complete inline coverage contains unresolved source correspondence")


def validate_pdf_cell_coverage(product: Mapping[str, Any]) -> None:
    """Complete cell scopes require every meaningful cell to be assessed and resolved."""
    scopes = [
        row
        for row in product.get("recognition_coverage", ())
        if row["universe"] == "cell" and row["outcome"] == "complete"
    ]
    health = product["health"]
    if health.get("cell_coverage") == "complete":
        scopes += [
            dict(section_pointer=pointer, membership=health["cell_membership"])
            for pointer in health.get("cell_scope", ())
        ]
    if not scopes:
        return
    index = _SourceIndex(product)
    reports = {
        (row["table_pointer"], row["cell_index"]): row for row in product.get("cell_reports", ())
    }
    for pointer, item in index.items.items():
        if item["label"] != "table" or not any(index.selected(pointer, scope) for scope in scopes):
            continue
        cells = index.native(pointer).get("data", {}).get("table_cells", ())
        for cell_index, cell in enumerate(cells):
            report = reports.get((pointer, cell_index))
            if report is None:
                if cell.get("text", "").strip() or (cell.get("ref") or {}).get("$ref"):
                    raise ValueError("complete scoped cell coverage omits a native cell assessment")
            elif report["classification"] == "unknown" or (
                report["classification"] == "math" and report["outcome"] != "succeeded"
            ):
                raise ValueError(
                    "complete scoped cell coverage contains unresolved recognition/classification"
                )


def validate_pdf_ocr_pages(product: Mapping[str, Any]) -> None:
    """Validate observed raster/PDF transforms without claiming original glyph positions."""
    pages = {}
    for page in product.get("inline_candidate_pages", ()):
        number = page["page_no"]
        if number in pages or str(number) not in product["document"].get("pages", {}):
            raise ValueError("inline candidate page is duplicate or outside native scope")
        pages[number] = _validate_ocr_page(page, product["document"]["pages"][str(number)]["size"])
    _validate_ocr_coverage(product, pages, _SourceIndex(product))


def validate_pdf_inline_reports(
    product: Mapping[str, Any], *, page_lookup: Mapping[int, Any] | None = None
) -> None:
    """Keep unresolved source correspondence explicit, without inventing text offsets."""
    reports = list(product.get("inline_alignment_reports", ()))
    if not reports:
        return
    _require_inline_parent(product, reports)
    pages = (
        page_lookup
        if page_lookup is not None
        else {page["page_no"]: page for page in product.get("inline_candidate_pages", ())}
    )
    index = _SourceIndex(product)
    seen, unresolved = set(), set()
    for report in reports:
        _validate_inline_report(
            product, report, pages.get(report["page_no"]), index, seen, unresolved
        )
    _validate_inline_coverage(product, unresolved, index)


def validate_pdf_page_payloads(product: Mapping[str, Any]) -> None:
    """Validate each streamed page once, fusing its OCR and inline-report work.

    Only availability and unresolved-pointer summaries survive a page; complete-set
    coverage and original candidate uniqueness remain whole-operation checks.
    """
    reports_by_page = defaultdict(list)
    for report in product.get("inline_alignment_reports", ()):
        reports_by_page[report["page_no"]].append(report)
    _require_inline_parent(product, reports_by_page)
    index = _SourceIndex(product)
    pages, seen, unresolved = {}, set(), set()
    for page in product.get("inline_candidate_pages", ()):
        number = page["page_no"]
        if number in pages or str(number) not in product["document"].get("pages", {}):
            raise ValueError("inline candidate page is duplicate or outside native scope")
        pages[number] = _validate_ocr_page(page, product["document"]["pages"][str(number)]["size"])
        for report in reports_by_page.pop(number, ()):
            _validate_inline_report(product, report, page, index, seen, unresolved)
    if reports_by_page:
        raise ValueError("inline alignment report has duplicate or unavailable candidate")
    _validate_ocr_coverage(product, pages, index)
    _validate_inline_coverage(product, unresolved, index)
