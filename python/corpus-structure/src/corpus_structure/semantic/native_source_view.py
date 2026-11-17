"""Invocation-owned immutable native projection and its ordered access paths."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import Any


def freeze_native(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_native(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_native(item) for item in value)
    return value


def thaw_native(value):
    """Explicit detached JSON representation for serializers and public mapping APIs."""
    if isinstance(value, Mapping):
        return {key: thaw_native(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_native(item) for item in value]
    return value


@dataclass(frozen=True)
class NativeSourceView:
    """One authenticated projection; never a cross-request authority cache."""

    value: Mapping[str, Any]
    columns: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        from .source_products import native_projection_identity

        value = self.value
        if native_projection_identity(
            value["text"], value["pieces"], value["items"],
            value.get("recognition", ()), value.get("ancestors", ()),
        ) != value["source"]["projection"]:
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
        object.__setattr__(self, "value", freeze_native(value))
        object.__setattr__(self, "columns", freeze_native(self.columns or value))
        pointers = tuple(self.items_by_ref)
        if any(not isinstance(pointer, str) or not pointer.startswith("#/") for pointer in pointers):
            raise ValueError("source context has unsupported native pointers")
        for piece in self.pieces:
            if piece.get("kind") == "native_text":
                if piece.get("item_ref") not in self.items_by_ref:
                    raise ValueError("source piece has no retained native item")
            elif piece.get("kind") != "synthetic_separator":
                raise ValueError("unsupported or lossy native projection piece")

    @property
    def text(self):
        return self.value["text"]

    @property
    def projection(self):
        return self.value["source"]["projection"]

    @property
    def pieces(self):
        return self.columns["pieces"]

    @property
    def items(self):
        return self.columns["items"]

    @property
    def ancestors(self):
        return self.columns.get("ancestors", ())

    @cached_property
    def starts(self):
        return tuple(piece["start"] for piece in self.pieces)

    @cached_property
    def ends(self):
        return tuple(piece["end"] for piece in self.pieces)

    @cached_property
    def native_pieces(self):
        return tuple(piece for piece in self.pieces if piece["kind"] == "native_text")

    @cached_property
    def native_ends(self):
        return tuple(piece["end"] for piece in self.native_pieces)

    @cached_property
    def items_by_ref(self):
        return MappingProxyType({item.get("self_ref", item.get("pointer")): item for item in self.items})

    @cached_property
    def piece_indices_by_item(self):
        indices = {}
        for index, piece in enumerate(self.pieces):
            if (pointer := piece.get("item_ref")) is not None:
                indices.setdefault(pointer, []).append(index)
        return MappingProxyType({key: tuple(value) for key, value in indices.items()})

    def selected_pieces(self, start, end):
        # Zero-width construction anchors choose the left piece at a shared boundary.
        index = bisect_left(self.ends, start) if start == end else bisect_right(self.ends, start)
        while index < len(self.pieces):
            piece = self.pieces[index]
            if piece["start"] > end or (start != end and piece["start"] >= end):
                break
            yield piece
            index += 1

    @cached_property
    def item_ordinals(self):
        return MappingProxyType({pointer: index for index, pointer in enumerate(self.items_by_ref)})

    def selected_items(self, start, end):
        selected = {
            piece["item_ref"] for piece in self.selected_pieces(start, end)
            if piece.get("item_ref") in self.items_by_ref
        }
        return tuple(
            (pointer, self.items_by_ref[pointer])
            for pointer in sorted(selected, key=self.item_ordinals.__getitem__)
        )
