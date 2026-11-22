"""Shared immutable original native source selection, separate from execution custody."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel

from corpus_structure.caches import declare

from .identity import canonical_bytes
from .original_documents import original_document_subject
from .types import PreparationProfile, PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-source.yaml"


def source_product_inputs(
    bundle: SourceBundle, *, profile: PreparationProfile | None = None
) -> SourceBundle:
    """Capture the one common nominal source model, reusing existing selectors."""
    from .characterization import characterization_inputs
    from .data_product_reference import reference_inputs

    names = {source.name for source in bundle.sources}
    if "data_operation_source" in names:
        if (
            next(
                source.content
                for source in bundle.sources
                if source.name == "data_operation_source"
            )
            != _MODEL.read_bytes()
        ):
            raise ValueError("shared native source model differs from installed owner")
        return reference_inputs(bundle)
    bundle = reference_inputs(characterization_inputs(bundle, profile=profile))
    root = "data_operation_source_root"
    if root in names:
        raise ValueError("native source model uses a reserved root name")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact("data_operation_source", _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:data-operation-source-root",
                        "name": root,
                        "imports": [bundle.root, "data_operation_source"],
                    }
                ).encode(),
            ),
        ),
    )


def _values(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_unset=True)


def native_projection_identity(text: str, pieces, items, recognition=(), ancestors=()) -> str:
    """Hash actual projected source meaning, excluding legacy diagnostic/task custody."""
    return sha256(
        canonical_bytes(
            {
                "text": text,
                "pieces": list(pieces),
                "items": list(items),
                "ancestors": list(ancestors),
                "recognition": list(recognition),
            }
        )
    ).hexdigest()


def source_subject(source: Mapping[str, Any]) -> str:
    """One original source address shared by independent characterization producers."""
    return "source-native:" + sha256(canonical_bytes(source)).hexdigest()


def _native_atoms(items):
    """Retain declared language/hierarchy/grid context; PDF geometry stays original-owned."""
    atoms = []
    for item in items:
        atom = {
            name: item[name]
            for name in (
                "self_ref",
                "label",
                "text",
                "orig",
                "name",
                "level",
                "content_layer",
                "marker",
                "enumerated",
            )
            if name in item
        }
        if isinstance(item.get("parent"), Mapping) and "$ref" in item["parent"]:
            atom["parent"] = item["parent"]["$ref"]
        for name in ("children", "captions", "footnotes", "references"):
            if name in item:
                atom[name] = [reference["$ref"] for reference in item[name]]
        atom["prov"] = [
            {"page_no": row["page_no"]} for row in item.get("prov", ()) if "page_no" in row
        ]
        if "data" in item and "table_cells" in item["data"]:
            data = item["data"]
            cells = []
            for cell in data["table_cells"]:
                retained = {
                    name: cell[name]
                    for name in (
                        "text",
                        "row_span",
                        "col_span",
                        "start_row_offset_idx",
                        "end_row_offset_idx",
                        "start_col_offset_idx",
                        "end_col_offset_idx",
                        "column_header",
                        "row_header",
                        "row_section",
                        "fillable",
                    )
                    if name in cell
                }
                if cell.get("ref") is not None:
                    retained["ref"] = cell["ref"]["$ref"]
                cells.append(retained)
            atom["data"] = {
                **{
                    name: data[name]
                    for name in ("num_rows", "num_cols", "orientation")
                    if name in data
                },
                "table_cells": cells,
            }
        atoms.append(atom)
    return atoms


def _record_field(record, key, default):
    if key not in record:
        return default
    return record[key]


def native_selector_facts(items, ancestors):
    """Derive parent and page facts without adding ancestry to the selected atoms."""
    parents = {
        item["self_ref"]: _record_field(item, "parent", None) for item in (*items, *ancestors)
    }
    pages = {
        item["self_ref"]: frozenset(row["page_no"] for row in _record_field(item, "prov", ()))
        for item in items
    }
    return parents, pages


def _native_selector_matches_ptr(parents, selector, pointer):
    target = _record_field(selector, "native_pointer", None)
    if target is None:
        return True
    seen = set()
    current = pointer
    while current is not None:
        if current == target:
            return True
        if current in seen or current not in parents:
            return None
        seen |= {current}
        current = parents[current]
    return False


def native_selector_covers_extent(parents, pages, selectors, extent, text_length):
    """Check one extent against original page, ancestry and selected text bounds."""
    pointer = extent["native_pointer"]
    if pointer not in pages:
        return False
    start, end = extent["start"], extent["end"]
    if start > end:
        return False
    item_pages = pages[pointer]
    if "page" in extent and item_pages != {extent["page"]}:
        return False
    return any(
        _native_selector_matches_ptr(parents, selector, pointer) is True
        and ("page" not in selector or item_pages == {selector["page"]})
        and _record_field(selector, "start", 0)
        <= start
        <= end
        <= _record_field(selector, "end", text_length)
        for selector in selectors
    )


@dataclass(frozen=True)
class NativeSourceSelectorIndex:
    """One immutable parent lookup; unknown ancestry never becomes non-membership."""

    parents: Mapping[str, str | None]
    selected: frozenset[str]
    pages: Mapping[str, frozenset[int]]

    @classmethod
    def from_value(cls, value):
        parents, pages = native_selector_facts(value["items"], value.get("ancestors", ()))
        return cls(
            MappingProxyType(parents),
            frozenset(pages),
            MappingProxyType(pages),
        )

    def matches(self, selector: Mapping[str, Any], pointer: str) -> bool | None:
        """Only captured selected atoms are candidates; ancestry is context, never expansion."""
        if pointer not in self.selected:
            raise ValueError("native selector candidate is outside captured selected items")
        return _native_selector_matches_ptr(self.parents, selector, pointer)


def selected_source_ranges(value, selectors, *, selector_index=None, include_unknown=False):
    """Merge selected projection intervals under captured pointer/page membership."""
    ancestry = selector_index or NativeSourceSelectorIndex.from_value(value)
    return native_selected_ranges(
        value, selectors, ancestry.parents, ancestry.pages, include_unknown=include_unknown
    )


def native_selected_ranges(value, selectors, parents, pages, *, include_unknown=False):
    """Lower selectors against exact original parent, page and projected-piece facts."""
    intervals = []
    for selector in selectors:
        start = _record_field(selector, "start", 0)
        end = _record_field(selector, "end", len(value["text"]))
        if selector["projection"] != value["source"]["projection"] or not 0 <= start <= end <= len(
            value["text"]
        ):
            raise ValueError("selected source interval differs from original projection")
        if "native_pointer" not in selector and "page" not in selector:
            intervals.append((start, end))
            continue
        for piece in value["pieces"]:
            if piece["kind"] != "native_text":
                continue
            pointer = piece["item_ref"]
            if pointer not in pages:
                raise ValueError("native selector candidate is outside captured selected items")
            match = _native_selector_matches_ptr(parents, selector, pointer)
            if (match is not True and not (include_unknown and match is None)) or (
                "page" in selector and pages[pointer] != {selector["page"]}
            ):
                continue
            intervals.append((max(start, piece["start"]), min(end, piece["end"])))
    merged = []
    for start, end in sorted((a, b) for a, b in intervals if a < b):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return tuple(merged)


def native_selected_unprojected_atoms(value, selectors, parents, pages, *, include_unknown=False):
    """Lower whole-source selectors to exact original unprojected formula atoms."""
    projected = {piece["item_ref"] for piece in value["pieces"] if piece["kind"] == "native_text"}
    unprojected = {
        item["self_ref"]
        for item in value["items"]
        if _record_field(item, "label", None) == "formula"
    } - projected
    selected = set()
    for selector in selectors:
        # The formal owner cannot locate an unprojected atom in a partial text range.
        if "start" in selector and (selector["start"], _record_field(selector, "end", None)) != (
            0,
            len(value["text"]),
        ):
            continue
        for pointer in unprojected:
            if pointer not in pages:
                raise ValueError("native selector candidate is outside captured selected items")
            match = _native_selector_matches_ptr(parents, selector, pointer)
            if (match is True or (include_unknown and match is None)) and (
                "page" not in selector or selector["page"] in pages[pointer]
            ):
                selected |= {pointer}
    return frozenset(selected)


def _projection_body(
    *, document, section_pointer, membership, text, pieces, items, ancestors=(), recognition=()
):
    atoms = _native_atoms(items)
    context = _native_atoms(ancestors)
    narrowed_pieces = [
        {
            name: piece[name]
            for name in ("kind", "start", "end", "item_ref", "source_field", "cell_index")
            if name in piece
        }
        for piece in pieces
    ]
    outcomes = [{"pointer": row["pointer"], "outcome": row["outcome"]} for row in recognition]
    projection = native_projection_identity(text, narrowed_pieces, atoms, outcomes, context)
    return dict(
        source=dict(
            document=document,
            document_subject=original_document_subject(document),
            section_pointer=section_pointer,
            membership=membership,
            projection=projection,
        ),
        text=text,
        pieces=narrowed_pieces,
        items=atoms,
        ancestors=context,
        recognition=outcomes,
    )


@declare("native-source-decoder", "model_entries", key=lambda prepared: prepared.release_id)
def _native_source_decoder(prepared):
    return sha256(
        canonical_bytes(prepared.adapter("DdoSelectedNativeSource").json_schema())
    ).digest()


@dataclass(frozen=True)
class _NativeSourcePayload:
    content: bytes
    value: Mapping[str, Any]


@declare(
    "native-source-payloads",
    "runtime_bytes",
    key=lambda content, decoder, prepared=None, selected=None: (
        sha256(content).digest(), decoder,
        sha256(selected.meaning).digest() if selected is not None else None,
    ),
    weight=lambda payload: len(payload.content),
)
def _native_source_payload(content, decoder, prepared=None, selected=None):
    """Retain immutable interpretation only; occurrence indexes stay invocation-owned."""
    from .native_source_view import freeze_native

    if prepared is None:
        return _NativeSourcePayload(content, freeze_native(json.loads(content)))
    checked = _values(prepared.validate_json("DdoSelectedNativeSource", content))
    if selected is not None:
        from .data_operation_values import semantic_value

        if canonical_bytes(semantic_value(checked)) != selected.meaning:
            raise ValueError("selected native source display differs from its typed meaning")
    if "document_subject" in checked["source"] and checked["source"][
        "document_subject"
    ] != original_document_subject(checked["source"]["document"]):
        raise ValueError("selected source document address differs from its original key")
    text, pieces, items = checked["text"], checked.get("pieces", []), checked.get("items", [])
    ancestors = checked.get("ancestors", [])
    if len({item["self_ref"] for item in ancestors}) != len(ancestors):
        raise ValueError("selected native source repeats an ancestor")
    shared = {item["self_ref"]: item for item in items}
    if any(item["self_ref"] in shared and shared[item["self_ref"]] != item for item in ancestors):
        raise ValueError("selected native ancestor differs from original atom")
    checked["ancestors"] = ancestors
    pointers = {item["self_ref"] for item in items}
    if len(pointers) != len(items):
        raise ValueError("selected native source repeats a native atom")
    checked["pieces"], checked["items"] = pieces, items
    previous = 0
    for piece in pieces:
        if not previous == piece["start"] < piece["end"] <= len(text):
            raise ValueError("selected native source pieces overlap or exceed text")
        previous = piece["end"]
        if piece["kind"] == "native_text" and (
            piece.get("item_ref") not in pointers or not piece.get("source_field")
        ):
            raise ValueError("selected native native piece requires its original atom/field")
    if previous != len(text):
        raise ValueError("selected native pieces do not partition the original text")
    recognition = checked.get("recognition", [])
    if len({row["pointer"] for row in recognition}) != len(recognition) or any(
        row["pointer"] not in pointers for row in recognition
    ):
        raise ValueError("selected native recognition must name distinct original atoms")
    checked["recognition"] = recognition
    projection = native_projection_identity(text, pieces, items, recognition, ancestors)
    if checked["source"]["projection"] != projection:
        raise ValueError("selected native projection differs from actual source meaning")
    ancestry = NativeSourceSelectorIndex.from_value(checked)
    for selector in checked["selectors"]:
        if selector["projection"] != projection:
            raise ValueError("selected native scope has another projection")
        if not 0 <= selector.get("start", 0) <= selector.get("end", len(text)) <= len(text):
            raise ValueError("selected native scope exceeds original text")
        if "native_pointer" in selector and not any(
            ancestry.matches(selector, pointer) is True for pointer in pointers
        ):
            raise ValueError("selected native scope names no captured atom/ancestor descendant")
    return _NativeSourcePayload(canonical_bytes(checked), freeze_native(checked))


@dataclass(frozen=True, init=False)
class FrozenNativeSource:
    """Owned source bytes validated against the acquired nominal declaration."""

    content: bytes
    _validation: ClassVar[tuple[bytes, bytes | None]]
    _payload: ClassVar[_NativeSourcePayload]

    def __init__(self, *args, **kwargs):
        raise TypeError("native sources require validating acquisition or sealed worker acceptance")

    @classmethod
    def _from_payload(cls, payload, decoder):
        source = object.__new__(cls)
        object.__setattr__(source, "content", payload.content)
        object.__setattr__(source, "_validation", (payload.content, decoder))
        object.__setattr__(source, "_payload", payload)
        return source

    @classmethod
    def _accept_parent_validated(cls, content):
        """Accept source bytes only within an authenticated parent CPU packet."""
        if type(content) is not bytes:
            raise TypeError("sealed native source requires bytes")
        return cls._from_payload(_native_source_payload(content, None), None)

    def _require_acquired(self):
        if (
            type(self) is not FrozenNativeSource
            or "_validation" not in vars(self)
            or self._validation[0] is not self.content
        ):
            raise TypeError("native source lacks its validating acquisition")

    @classmethod
    def acquire(
        cls, prepared: PreparedRelease, value: Mapping[str, Any] | FrozenNativeSource
    ) -> FrozenNativeSource:
        decoder = _native_source_decoder(prepared)
        if isinstance(value, FrozenNativeSource):
            value._require_acquired()
            if value._validation[1] == decoder:
                return value
            value = value.value
        payload = _native_source_payload(canonical_bytes(value), decoder, prepared)
        return cls._from_payload(payload, decoder)

    @classmethod
    def acquire_selected(cls, prepared: PreparedRelease, selected) -> FrozenNativeSource:
        """Acquire the exact retained display bytes under their tagged nominal meaning."""
        from .data_operation_consumers import SelectedConsumerValue

        if type(selected) is not SelectedConsumerValue:
            raise TypeError("selected native source requires its acquired member carrier")
        SelectedConsumerValue._require_acquired(selected)
        if selected.partitioned is not None:
            raise ValueError("selected native source requires one unpartitioned member")
        decoder = _native_source_decoder(prepared)
        return cls._from_payload(
            _native_source_payload(selected.content, decoder, prepared, selected), decoder
        )

    @classmethod
    def from_projection(
        cls,
        prepared: PreparedRelease,
        *,
        document: str,
        section_pointer: str,
        membership: str,
        text: str,
        pieces,
        items,
        ancestors=(),
        recognition=(),
        selectors=None,
    ) -> FrozenNativeSource:
        """Build from an authenticated original or computed native projection.

        This constructor grants no source-fact admission or computation provenance.
        Its caller retains that origin separately; the language value is identical.
        """
        value = _projection_body(
            document=document,
            section_pointer=section_pointer,
            membership=membership,
            text=text,
            pieces=pieces,
            items=items,
            ancestors=ancestors,
            recognition=recognition,
        )
        value["selectors"] = (
            list(selectors)
            if selectors is not None
            else [{"projection": value["source"]["projection"]}]
        )
        return cls.acquire(prepared, value)

    def selector_index(self) -> NativeSourceSelectorIndex:
        return self._selector_index

    @cached_property
    def _selector_index(self) -> NativeSourceSelectorIndex:
        return NativeSourceSelectorIndex.from_value(self._value)

    def native_items(self) -> tuple[Mapping[str, Any], ...]:
        """Exact immutable original items/ancestor context for pure native owners."""
        return self._native_items

    @cached_property
    def _native_items(self) -> tuple[Mapping[str, Any], ...]:
        from .native_source_view import freeze_native

        value = self.value
        by_pointer = {item["self_ref"]: item for item in (*value["items"], *value["ancestors"])}
        rows: list[dict[str, Any]] = []
        for item in by_pointer.values():
            restored = {
                **item,
                **({"parent": {"$ref": item["parent"]}} if "parent" in item else {}),
            }
            for name in ("children", "captions", "footnotes", "references"):
                if name in item:
                    restored[name] = [{"$ref": pointer} for pointer in item[name]]
            if "data" in item:
                restored["data"] = {
                    **item["data"],
                    "table_cells": [
                        {**cell, **({"ref": {"$ref": cell["ref"]}} if "ref" in cell else {})}
                        for cell in item["data"]["table_cells"]
                    ],
                }
            rows.append(restored)
        return freeze_native(rows)

    @property
    def _value(self):
        return self._payload.value

    @cached_property
    def view(self):
        from .native_source_view import NativeSourceView

        return NativeSourceView.from_acquired(self)

    @property
    def value(self) -> Mapping[str, Any]:
        return self._value
