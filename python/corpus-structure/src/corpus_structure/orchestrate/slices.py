"""Immutable native PDF section scopes for the current acquisition pipeline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from corpus_structure.core.canonical import digest


class SliceError(ValueError):
    """A source selection is unavailable or outside current PDF semantics."""


def records(
    docs: Sequence[Mapping[str, Any]],
    selectors: Mapping[str, Any],
    *,
    slice: str | None,
    scope: str | None,
    corpus: str | None,
):
    """Resolve immutable source selection without access to held-out references."""

    if not docs or not all(document.get("mime") == "application/pdf" for document in docs):
        raise SliceError("source acquisition requires immutable PDF originals")
    if corpus is not None:
        raise SliceError(
            "PDF source acquisition selects registered originals; corpus selectors are retired"
        )
    if slice is not None and scope is not None:
        raise SliceError("choose slice or scope, not both")
    name = slice or scope
    selected_sections = []
    if name is not None:
        entries = selectors.get(name)
        if not isinstance(entries, list):
            raise SliceError(f"unknown native PDF scope {name!r}")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"native_sections"}:
                raise SliceError("native PDF scopes require native_sections selections")
            values = entry["native_sections"]
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(v, str) and v for v in values)
            ):
                raise SliceError("native section selection requires nonempty headings")
            selected_sections.extend(values)
    corpus_record = {
        "name": "pdf-originals",
        "locators": [],
        "documents": [document["key"] for document in docs],
        "hash": digest([(document["key"], document["content_hash"]) for document in docs]),
    }
    scope_record = (
        None
        if name is None
        else {
            "kind": "native_sections",
            "name": name,
            "sections": list(dict.fromkeys(selected_sections)),
            "include_descendants": True,
            "hash": digest(selected_sections),
        }
    )
    return corpus_record, scope_record
