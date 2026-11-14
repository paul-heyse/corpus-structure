"""Shared immutable original native source selection, separate from execution custody."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from pydantic import BaseModel

from .identity import canonical_bytes
from .original_documents import original_document_subject
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-source.yaml"


def source_product_inputs(bundle: SourceBundle) -> SourceBundle:
    """Capture the one common nominal source model, reusing existing selectors."""
    from .characterization import characterization_inputs
    from .data_product_reference import reference_inputs

    bundle = reference_inputs(characterization_inputs(bundle))
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
        return bundle
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
        if isinstance(item.get("parent"), dict) and "$ref" in item["parent"]:
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


@dataclass(frozen=True)
class NativeSourceSelectorIndex:
    """One immutable parent lookup; unknown ancestry never becomes non-membership."""

    parents: Mapping[str, str | None]
    selected: frozenset[str]

    @classmethod
    def from_value(cls, value):
        return cls(
            MappingProxyType(
                {
                    item["self_ref"]: item.get("parent")
                    for item in (*value["items"], *value.get("ancestors", []))
                }
            ),
            frozenset(item["self_ref"] for item in value["items"]),
        )

    def matches(self, selector: Mapping[str, Any], pointer: str) -> bool | None:
        """Only captured selected atoms are candidates; ancestry is context, never expansion."""
        if pointer not in self.selected:
            raise ValueError("native selector candidate is outside captured selected items")
        target = selector.get("native_pointer")
        if target is None:
            return True
        seen = set()
        current = pointer
        while current is not None:
            if current == target:
                return True
            if current in seen or current not in self.parents:
                return None
            seen.add(current)
            current = self.parents[current]
        return False


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


@dataclass(frozen=True)
class FrozenNativeSource:
    """Owned source bytes validated against the acquired nominal declaration."""

    content: bytes

    @classmethod
    def acquire(cls, prepared: PreparedRelease, value: Mapping[str, Any]) -> FrozenNativeSource:
        checked = _values(prepared.validate_json("DdoSelectedNativeSource", canonical_bytes(value)))
        if "document_subject" in checked["source"] and checked["source"][
            "document_subject"
        ] != original_document_subject(checked["source"]["document"]):
            raise ValueError("selected source document address differs from its original key")
        text, pieces, items = checked["text"], checked.get("pieces", []), checked.get("items", [])
        ancestors = checked.get("ancestors", [])
        if len({item["self_ref"] for item in ancestors}) != len(ancestors):
            raise ValueError("selected native source repeats an ancestor")
        shared = {item["self_ref"]: item for item in items}
        if any(
            item["self_ref"] in shared and shared[item["self_ref"]] != item for item in ancestors
        ):
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
        return cls(canonical_bytes(checked))

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

    @classmethod
    def from_source_view(
        cls, prepared: PreparedRelease, view, *, document: str, selectors
    ) -> FrozenNativeSource:
        """Adapt exact selected legacy custody into the shared source-value boundary."""
        if any(selector["projection"] != view.ref.projection_digest for selector in selectors):
            raise ValueError("selected native scope differs from acquired legacy projection")
        value = _projection_body(
            document=document,
            section_pointer=view.ref.section_pointer,
            membership=view.ref.membership,
            text=view.text,
            pieces=view.pieces,
            items=view.items,
            ancestors=view.ancestors,
            recognition=view.health.get("formula_outcomes", ()),
        )
        value["selectors"] = [
            {**selector, "projection": value["source"]["projection"]} for selector in selectors
        ]
        return cls.acquire(prepared, value)

    def selector_index(self) -> NativeSourceSelectorIndex:
        return NativeSourceSelectorIndex.from_value(self.value)

    def native_items(self) -> tuple[dict[str, Any], ...]:
        """Exact retained original items/ancestor context for pure native owners."""
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
        return tuple(rows)

    @property
    def value(self) -> dict[str, Any]:
        return json.loads(self.content)
