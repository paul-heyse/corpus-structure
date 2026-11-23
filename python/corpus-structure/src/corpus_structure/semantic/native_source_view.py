"""Invocation-owned immutable native projection and its ordered access paths."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import Any, overload


def merge_touching_spans(spans) -> tuple[tuple[int, int], ...]:
    """Coalesce overlapping or touching coordinates in source order."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if start > end:
            raise ValueError("span start exceeds its end")
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


class FrozenJsonArray(tuple):
    """An immutable JSON array, distinguishable from a caller's Python tuple."""


@overload
def freeze_native(value: Mapping[str, Any]) -> Mapping[str, Any]: ...


@overload
def freeze_native(value: list[Any] | tuple[Any, ...]) -> tuple[Any, ...]: ...


@overload
def freeze_native(value: Any) -> Any: ...


def freeze_native(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_native(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenJsonArray(freeze_native(item) for item in value)
    return value


@overload
def thaw_native(value: Mapping[str, Any]) -> dict[str, Any]: ...


@overload
def thaw_native(value: tuple[Any, ...]) -> list[Any]: ...


@overload
def thaw_native(value: Any) -> Any: ...


def thaw_native(value: Any) -> Any:
    """Explicit detached JSON representation for serializers and public mapping APIs."""
    if isinstance(value, Mapping):
        return {key: thaw_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw_native(item) for item in value]
    return value


def matches_positioned_source_extent(pieces, ends, native_pieces, native_ends, extent):
    """Match an extent to the exact retained piece and its original native pointer."""
    start, end = extent["start"], extent["end"]
    index = bisect_left(ends, end)
    if index == len(pieces):
        return False
    piece = pieces[index]
    if not piece["start"] <= start <= end <= piece["end"]:
        return False
    if "item_ref" in piece and piece["item_ref"] is not None:
        pointer = piece["item_ref"]
    else:
        nearest = bisect_left(native_ends, start)
        if nearest == len(native_pieces):
            return False
        pointer = native_pieces[nearest]["item_ref"]
    return extent["native_pointer"] == pointer and extent["synthetic"] == (
        start == end or piece["kind"] != "native_text"
    )


@dataclass(frozen=True)
class NativeSourceView:
    """One authenticated projection; never a cross-request authority cache."""

    value: Mapping[str, Any]
    columns: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        from .source_products import native_projection_identity

        # The owner may supply its already frozen snapshot. Projection identity
        # consumes a detached JSON representation; frozen containers remain internal.
        value = thaw_native(self.value)
        if (
            native_projection_identity(
                value["text"],
                value["pieces"],
                value["items"],
                value.get("recognition", ()),
                value.get("ancestors", ()),
            )
            != value["source"]["projection"]
        ):
            raise ValueError("declared native projection differs from its selected source")
        position = 0
        for piece in value["pieces"]:
            if (
                type(piece.get("start")) is not int
                or type(piece.get("end")) is not int
                or piece["start"] != position
                or not position < piece["end"] <= len(value["text"])
            ):
                raise ValueError("source pieces must partition the pinned projection")
            position = piece["end"]
        if position != len(value["text"]):
            raise ValueError("source pieces do not cover the pinned projection")
        frozen = freeze_native(value)
        object.__setattr__(self, "value", frozen)
        object.__setattr__(self, "columns", freeze_native(self.columns) if self.columns else frozen)
        self._check_columns()

    @classmethod
    def from_acquired(cls, source, columns=None):
        """Reuse the source owner's immutable validated payload without a second hash."""
        from .source_products import FrozenNativeSource

        FrozenNativeSource._require_acquired(source)
        result = object.__new__(cls)
        object.__setattr__(result, "value", source.value)
        object.__setattr__(
            result, "columns", source.value if columns is None else freeze_native(columns)
        )
        result._check_columns()
        return result

    def _check_columns(self):
        pointers = (
            *self.items_by_ref,
            *(item.get("self_ref", item.get("pointer")) for item in self.ancestors),
        )
        if any(
            not isinstance(pointer, str) or not pointer.startswith("#/") for pointer in pointers
        ):
            raise ValueError("source context has unsupported native pointers")
        for piece in self.pieces:
            if piece.get("kind") == "native_text":
                if piece.get("item_ref") not in self.items_by_ref:
                    raise ValueError("source piece has no retained native item")
            elif piece.get("kind") != "synthetic_separator":
                raise ValueError("unsupported or lossy native projection piece")

    @property
    def text(self) -> str:
        return self.value["text"]

    @property
    def projection(self) -> str:
        return self.value["source"]["projection"]

    @property
    def pieces(self) -> tuple[Mapping[str, Any], ...]:
        return self.columns["pieces"]

    @property
    def items(self) -> tuple[Mapping[str, Any], ...]:
        return self.columns["items"]

    @property
    def ancestors(self) -> tuple[Mapping[str, Any], ...]:
        return self.columns.get("ancestors", ())

    @cached_property
    def starts(self) -> tuple[int, ...]:
        return tuple(piece["start"] for piece in self.pieces)

    @cached_property
    def ends(self) -> tuple[int, ...]:
        return tuple(piece["end"] for piece in self.pieces)

    @cached_property
    def native_pieces(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(piece for piece in self.pieces if piece["kind"] == "native_text")

    @cached_property
    def native_ends(self) -> tuple[int, ...]:
        return tuple(piece["end"] for piece in self.native_pieces)

    @cached_property
    def items_by_ref(self) -> Mapping[str, Mapping[str, Any]]:
        return MappingProxyType(
            {item.get("self_ref", item.get("pointer")): item for item in self.items}
        )

    @cached_property
    def context_items_by_ref(self) -> Mapping[str, Mapping[str, Any]]:
        return MappingProxyType(
            {
                item.get("self_ref", item.get("pointer")): item
                for item in (*self.items, *self.ancestors)
            }
        )

    @cached_property
    def piece_indices_by_item(self) -> Mapping[str, tuple[int, ...]]:
        indices: dict[str, list[int]] = {}
        for index, piece in enumerate(self.pieces):
            if (pointer := piece.get("item_ref")) is not None:
                indices.setdefault(pointer, []).append(index)
        return MappingProxyType({key: tuple(value) for key, value in indices.items()})

    @cached_property
    def pieces_by_item(self) -> Mapping[str, tuple[Mapping[str, Any], ...]]:
        return MappingProxyType(
            {
                pointer: tuple(
                    self.pieces[index]
                    for index in indices
                    if self.pieces[index]["kind"] == "native_text"
                )
                for pointer, indices in self.piece_indices_by_item.items()
            }
        )

    @cached_property
    def item_piece_ends(self) -> Mapping[str, tuple[int, ...]]:
        return MappingProxyType(
            {
                pointer: tuple(piece["end"] for piece in pieces)
                for pointer, pieces in self.pieces_by_item.items()
            }
        )

    def containing_piece(self, pointer: str, start: int, end: int) -> Mapping[str, Any] | None:
        """Exact native-item containment, including zero-width construction anchors."""
        pieces = self.pieces_by_item.get(pointer, ())
        index = bisect_left(self.item_piece_ends.get(pointer, ()), end)
        if index < len(pieces) and pieces[index]["start"] <= start <= end <= pieces[index]["end"]:
            return pieces[index]
        return None

    def matches_occurrence_extent(self, extent: Mapping[str, Any]) -> bool:
        """Match construction coordinates to one retained projection piece."""
        return matches_positioned_source_extent(
            self.pieces, self.ends, self.native_pieces, self.native_ends, extent
        )

    def native_gap(self, start: int, end: int) -> bool:
        """Whether an open interval contains no native text, by its ordered end index."""
        index = bisect_right(self.native_ends, start)
        return index == len(self.native_pieces) or self.native_pieces[index]["start"] >= end

    def selected_pieces(self, start: int, end: int) -> Iterator[Mapping[str, Any]]:
        # Zero-width construction anchors choose the left piece at a shared boundary.
        index = bisect_left(self.ends, start) if start == end else bisect_right(self.ends, start)
        while index < len(self.pieces):
            piece = self.pieces[index]
            if piece["start"] > end or (start != end and piece["start"] >= end):
                break
            yield piece
            index += 1

    @cached_property
    def item_ordinals(self) -> Mapping[str, int]:
        return MappingProxyType({pointer: index for index, pointer in enumerate(self.items_by_ref)})

    def selected_items(self, start: int, end: int) -> tuple[tuple[str, Mapping[str, Any]], ...]:
        selected = {
            piece["item_ref"]
            for piece in self.selected_pieces(start, end)
            if piece.get("item_ref") in self.items_by_ref
        }
        return tuple(
            (pointer, self.items_by_ref[pointer])
            for pointer in sorted(selected, key=self.item_ordinals.__getitem__)
        )
