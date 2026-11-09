"""Validate Dipo's ordered native trees and locate their retained EDU evidence."""

from __future__ import annotations

from collections.abc import Mapping, Set
from typing import TYPE_CHECKING, Any

from .pm2_products import ParserProduct, ParserProducts
from .pm2_source import (
    MappedSource,
    PM2SourceMap,
    ProviderSpan,
    SourceMapReason,
    SourceMapRefused,
    map_dipo,
)

if TYPE_CHECKING:
    from corpus_structure.semantic.types import PreparedRelease


Range = tuple[int, int]


def _pair(value: Any, limit: int, *, allow_empty: bool = False) -> Range:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(type(point) is not int for point in value)
        or not 0 <= value[0] <= value[1] <= limit
        or (not allow_empty and value[0] == value[1])
    ):
        raise ValueError("invalid Dipo half-open range")
    return value[0], value[1]


def _tree_children(rows: Any, leaves: int) -> dict[Range, tuple[Range, Range]]:
    """Authenticate one complete binary tree over the reported leaf population."""
    if leaves < 1 or not isinstance(rows, (tuple, list)) or len(rows) != leaves - 1:
        raise ValueError("Dipo split count differs from its leaf population")
    parents = {}
    for row in rows:
        left, right = _pair(row["left"], leaves), _pair(row["right"], leaves)
        parent = (left[0], right[1])
        if (
            left[1] != right[0]
            or parent in parents
            or row["nuclearity"] not in ("NN", "NS", "SN")
            or not isinstance(row["relation"], str)
            or not row["relation"]
        ):
            raise ValueError("invalid Dipo ordered split or native label")
        parents[parent] = (left, right)
    seen = set()
    pending = [(0, leaves)]
    while pending:
        span = pending.pop()
        if span in seen:
            raise ValueError("Dipo tree repeats a child")
        seen.add(span)
        if span[1] > span[0] + 1:
            if span not in parents:
                raise ValueError("Dipo tree omits an internal child")
            pending.extend(parents[span])
    if set(parents) - seen:
        raise ValueError("Dipo tree includes disconnected splits")
    return parents


def _locate_edu(
    mapping: PM2SourceMap, extent: Range, prepared: PreparedRelease | None
) -> tuple[MappedSource | SourceMapRefused, dict[str, Any] | None]:
    start, end = extent
    literal = mapping.provider_text[start:end]
    # Native token ranges can assign leading or trailing whitespace to a
    # leaf. Keep that allocation in the report without making it evidence.
    trimmed = literal.strip()
    if not trimmed:
        return mapping.refuse(SourceMapReason.UNMAPPED, "EDU has no non-whitespace source"), None
    start += len(literal) - len(literal.lstrip())
    span = ProviderSpan(start, start + len(trimmed), trimmed)
    try:
        return map_dipo(mapping, (span,), scope_digest=mapping.scope_digest), None
    except SourceMapRefused as error:
        if prepared is None or error.reason != SourceMapReason.SOURCE_REFUSED:
            return error, None
    try:
        located, reading = mapping.map_whitespace_reading(
            span, scope_digest=mapping.scope_digest, prepared=prepared
        )
    except SourceMapRefused as error:
        return error, None
    return located, reading.receipt()


def _validate_boundaries(boundaries: Any, final_ends: list[int], *, layout_forced: bool) -> None:
    if not isinstance(boundaries, (tuple, list)):
        raise ValueError("Dipo boundary provenance must be ordered")
    retained = []
    previous = 0
    for row in boundaries:
        end, learned, forced = row["token_end"], row["learned"], row["forced"]
        disposition = row["disposition"]
        if (
            type(end) is not int
            or not previous < end <= final_ends[-1]
            or type(learned) is not bool
            or type(forced) is not bool
            or not (learned or forced)
            or (forced and not layout_forced)
            or disposition not in ("retained", "merged")
        ):
            raise ValueError("invalid Dipo boundary provenance")
        if disposition == "retained":
            retained.append(end)
        previous = end
    if retained != final_ends:
        raise ValueError("Dipo retained boundary provenance differs from final EDUs")


def dipo_products(
    mapping: PM2SourceMap,
    request: Mapping[str, Any],
    reply: Mapping[str, Any],
    *,
    prepared: PreparedRelease | None = None,
) -> ParserProducts:
    """Bind the native forest, coverage, and located EDUs to one admitted scope."""
    text = mapping.provider_text
    mode = request.get("mode", "learned")
    if request["text"] != text or reply.get("mode", "learned") != mode:
        raise ValueError("Dipo reply differs from its admitted input or mode")
    raw_start, raw_end = 0, len(text)
    supplied: tuple[Range, ...] = ()
    if mode == "supplied_edus":
        reconstruction = reply["reconstruction"]
        raw_start, raw_end = _pair(
            (reconstruction["raw_start"], reconstruction["raw_end"]), len(text)
        )
        supplied = tuple(_pair(extent, len(text)) for extent in request["edu_ranges"])
        if (
            not supplied
            or reconstruction["text"] != text[raw_start:raw_end]
            or raw_start != supplied[0][0]
            or raw_end != supplied[-1][1]
            or set(reply["arms"]) != {"supplied", "predicted"}
        ):
            raise ValueError("Dipo reconstructed input differs from the reviewed source")
        arms = reply["arms"]
    elif mode in ("learned", "layout_forced"):
        arms = {mode: reply}
    else:
        raise ValueError("unsupported Dipo product mode")

    locations: dict[str, MappedSource | SourceMapRefused] = {}
    products: list[ParserProduct] = []
    token_count = reply["post_tokenizer_tokens"]
    if type(token_count) is not int or token_count < 1:
        raise ValueError("invalid Dipo token population")
    for arm, output in arms.items():
        rows = output["edus"]
        _tree_children(output["spans"], len(rows))
        if arm == "supplied" and len(rows) != len(supplied):
            raise ValueError("Dipo supplied EDU count changed")
        position = 0
        raw_extents = []
        members = []
        final_ends = []
        for index, edu in enumerate(rows):
            token_start, token_end = _pair(edu["tokens"], token_count)
            if token_start != position:
                raise ValueError("Dipo EDUs do not partition the native token sequence")
            position = token_end
            final_ends.append(token_end)
            relative_start, relative_end = _pair(
                edu["chars"], raw_end - raw_start, allow_empty=arm == "predicted"
            )
            extent = (relative_start + raw_start, relative_end + raw_start)
            literal = text[extent[0] : extent[1]]
            expected = {
                "supplied": literal,
                "predicted": literal.strip(),
            }.get(arm, " ".join(literal.split()))
            if edu["text"] != expected:
                raise ValueError("Dipo EDU text differs from retained character offsets")
            if arm == "supplied" and extent != supplied[index]:
                raise ValueError("Dipo supplied EDU changed its reviewed extent")
            # predict_both slices by token offsets. Those can overlap after
            # token normalization, independently of a valid token tree.
            if raw_extents and extent[0] < raw_extents[-1][1]:
                if arm != "predicted":
                    raise ValueError("Dipo raw EDU character ranges overlap")
                located = mapping.refuse(
                    SourceMapReason.UNMAPPED, "paired EDU character offsets overlap"
                )
                whitespace = None
            else:
                located, whitespace = _locate_edu(mapping, extent, prepared)
            raw_extents.append(extent)
            key = f"{arm}:edu:{index}"
            location_key = f"{key}:extent"
            locations[location_key] = located
            members.append(key)
            value: dict[str, Any] = {
                "arm": arm,
                "edu": index,
                "tokens": [token_start, token_end],
                "provider_chars": list(extent),
                "location_key": location_key,
            }
            if whitespace is not None:
                value["whitespace_reading"] = whitespace
            products.append(ParserProduct(key, "dipo.edu", value, (location_key,)))
        if position != token_count:
            raise ValueError("Dipo EDU coverage omits native tokens")
        boundaries = output.get("boundaries", [])
        if arm in ("learned", "layout_forced"):
            _validate_boundaries(boundaries, final_ends, layout_forced=arm == "layout_forced")
        gaps = []
        position = 0
        for start, end in raw_extents:
            if start > position:
                gaps.append([position, start])
            position = max(position, end)
        if position < len(text):
            gaps.append([position, len(text)])
        products.append(
            ParserProduct(
                f"{arm}:tree",
                "dipo.tree",
                {
                    "arm": arm,
                    "root": [0, len(rows)],
                    "splits": output["spans"],
                    "provider_gaps": gaps,
                    "boundaries": boundaries,
                },
                tuple(members),
            )
        )
    return ParserProducts(locations, tuple(products))


def dipo_context(
    tree: Mapping[str, Any], *, focal: int, located_edus: Set[int], max_edus: int
) -> dict[str, Any]:
    """Select a bounded sibling subtree by leaf range without rebuilding its text."""
    count = tree["root"][1]
    if (
        type(count) is not int
        or tree["root"] != [0, count]
        or type(focal) is not int
        or not 0 <= focal < count
        or type(max_edus) is not int
        or max_edus < 1
    ):
        raise ValueError("invalid Dipo context request")
    parents = _tree_children(tree["splits"], count)
    if focal not in located_edus:
        return {"outcome": "unsupported", "reason": "focal_edu_unmapped"}
    siblings = []
    parent = (0, count)
    while parent in parents:
        left, right = parents[parent]
        parent, sibling = (left, right) if focal < right[0] else (right, left)
        siblings.append(sibling)
    eligible = []
    omitted = []
    for start, end in reversed(siblings):
        if end - start + 1 > max_edus:
            omitted.append({"range": [start, end], "reason": "context_bound"})
        elif any(edu not in located_edus for edu in range(start, end)):
            omitted.append({"range": [start, end], "reason": "unmapped_edu"})
        else:
            eligible.append((start, end))
    selected = min(eligible, key=lambda span: span[1] - span[0], default=None)
    omitted.extend(
        {"range": list(span), "reason": "wider_than_selected"}
        for span in eligible
        if span != selected
    )
    return {
        "outcome": "succeeded",
        "focal": [focal, focal + 1],
        "sibling": list(selected) if selected is not None else None,
        "omitted": omitted,
    }
