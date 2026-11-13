"""Shared immutable original native source selection, separate from execution custody."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from .identity import canonical_bytes
from .types import PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-source.yaml"


def source_product_inputs(bundle: SourceBundle) -> SourceBundle:
    """Capture the one common nominal source model, reusing existing selectors."""
    from .characterization import characterization_inputs

    bundle = characterization_inputs(bundle)
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


def native_projection_identity(text: str, pieces, items, recognition=()) -> str:
    """Hash actual projected source meaning, excluding legacy diagnostic/task custody."""
    return sha256(
        canonical_bytes(
            {
                "text": text,
                "pieces": list(pieces),
                "items": list(items),
                "recognition": list(recognition),
            }
        )
    ).hexdigest()


def source_subject(source: Mapping[str, Any]) -> str:
    """One original source address shared by independent characterization producers."""
    return "source-native:" + sha256(canonical_bytes(source)).hexdigest()


@dataclass(frozen=True)
class FrozenNativeSource:
    """Owned source bytes validated against the acquired nominal declaration."""

    content: bytes

    @classmethod
    def acquire(cls, prepared: PreparedRelease, value: Mapping[str, Any]) -> FrozenNativeSource:
        checked = _values(prepared.validate_json("DdoSelectedNativeSource", canonical_bytes(value)))
        text, pieces, items = checked["text"], checked.get("pieces", []), checked.get("items", [])
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
        projection = native_projection_identity(text, pieces, items, recognition)
        if checked["source"]["projection"] != projection:
            raise ValueError("selected native projection differs from actual source meaning")
        for selector in checked["selectors"]:
            if selector["projection"] != projection:
                raise ValueError("selected native scope has another projection")
            if not 0 <= selector.get("start", 0) <= selector.get("end", len(text)) <= len(text):
                raise ValueError("selected native scope exceeds original text")
            if "native_pointer" in selector and selector["native_pointer"] not in pointers:
                raise ValueError("selected native scope names no original atom")
        return cls(canonical_bytes(checked))

    @classmethod
    def from_source_view(
        cls, prepared: PreparedRelease, view, *, document: str, selectors
    ) -> FrozenNativeSource:
        """Narrow an already acquired original view; this performs no selection/read.

        ``document`` is its authenticated semantic source identity supplied by the
        acquisition owner. The physical legacy ref remains with that owner's custody.
        """
        atoms = []
        for item in view.items:
            atoms.append(
                {
                    **{
                        name: item[name]
                        for name in ("self_ref", "label", "text", "orig")
                        if name in item
                    },
                    **(
                        {"parent": item["parent"]["$ref"]}
                        if isinstance(item.get("parent"), dict) and "$ref" in item["parent"]
                        else {}
                    ),
                    "prov": [
                        {"page_no": row["page_no"]}
                        for row in item.get("prov", ())
                        if "page_no" in row
                    ],
                }
            )
        pieces = [
            {
                name: piece[name]
                for name in ("kind", "start", "end", "item_ref", "source_field", "cell_index")
                if name in piece
            }
            for piece in view.pieces
        ]
        recognition = [
            {"pointer": row["pointer"], "outcome": row["outcome"]}
            for row in view.health.get("formula_outcomes", ())
        ]
        projection = native_projection_identity(view.text, pieces, atoms, recognition)
        if any(selector["projection"] != view.ref.projection_digest for selector in selectors):
            raise ValueError("selected native scope differs from acquired legacy projection")
        selected = [{**selector, "projection": projection} for selector in selectors]
        return cls.acquire(
            prepared,
            dict(
                source=dict(
                    document=document,
                    section_pointer=view.ref.section_pointer,
                    membership=view.ref.membership,
                    projection=projection,
                ),
                text=view.text,
                pieces=pieces,
                items=atoms,
                recognition=recognition,
                selectors=selected,
            ),
        )

    @property
    def value(self) -> dict[str, Any]:
        return json.loads(self.content)
