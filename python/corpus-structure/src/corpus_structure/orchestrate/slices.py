"""Recorded slice expansion and rendition-bound scope resolution (O2, D6 §8)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from corpus_structure.core.canonical import digest
from corpus_structure.core.locators import LocatorIndex, parse


class SliceError(ValueError):
    """A slice cannot be expanded or resolved; includes locator refusal candidates."""


def expand(
    selectors: Mapping[str, Any],
    name: str,
    documents: Sequence[Mapping[str, Any]],
    stack: tuple[str, ...] = (),
) -> tuple[str, ...]:
    if name in stack:
        raise SliceError(f"slice cycle: {' -> '.join((*stack, name))}")
    if name not in selectors:
        raise SliceError(f"unknown slice {name!r}; available: {sorted(selectors)}")
    entries = selectors[name]
    if not isinstance(entries, list):
        raise SliceError(f"slice {name!r} must be a list")
    out: set[str] = set()
    for entry in entries:
        if isinstance(entry, str):
            out.add(entry)
        elif isinstance(entry, dict) and len(entry) == 1:
            key, value = next(iter(entry.items()))
            if key == "include":
                out.update(expand(selectors, value, documents, (*stack, name)))
            elif key == "pages":
                for child in value:
                    out.update(
                        parse(x).page for x in expand(selectors, child, documents, (*stack, name))
                    )
            elif key == "index":
                out.update(
                    str(d["meta"]["page"])
                    for d in documents
                    if str(d["meta"].get(value, "")).lower() not in ("", "0", "false", "no")
                )
            elif key == "golden_set":
                raise SliceError(
                    "held-out reference sets cannot select extraction source units; "
                    "use explicit source locators"
                )
            else:
                raise SliceError(f"slice {name}: unsupported selector {entry!r}")
        else:
            raise SliceError(f"slice {name}: invalid selector {entry!r}")
    return tuple(sorted(out))


def records(
    docs: Sequence[Mapping[str, Any]],
    selectors: Mapping[str, Any],
    *,
    slice: str | None,
    scope: str | None,
    corpus: str | None,
):
    """Resolve immutable source selection without access to held-out references."""

    def chosen(name: str | None) -> tuple[str, ...]:
        return (
            expand(selectors, name, docs)
            if name
            else tuple(sorted(str(d["meta"]["page"]) for d in docs))
        )

    if slice is not None and scope is not None:
        raise SliceError("choose slice or scope, not both")
    scope_name = slice or scope
    scope_locs = chosen(scope_name) if scope_name else None
    corpus_name = slice or corpus or ("first-pass" if "first-pass" in selectors else None)
    corpus_locs = chosen(corpus_name)
    pages = {parse(x).page for x in corpus_locs}
    known = {str(d["meta"]["page"]) for d in docs}
    scope_pages = {parse(x).page for x in scope_locs or ()}
    if scope_pages - pages:
        raise SliceError(f"scope pages outside corpus: {sorted(scope_pages - pages)}")
    unknown = pages - known
    if unknown:
        raise SliceError(f"unknown corpus pages: {sorted(unknown)}")
    corpus_record = {
        "name": corpus_name,
        "locators": list(corpus_locs),
        "documents": [d["key"] for d in docs if d["meta"]["page"] in pages],
        "hash": digest(corpus_locs),
    }
    scope_record = (
        None
        if scope_locs is None
        else {"name": scope_name, "locators": list(scope_locs), "hash": digest(scope_locs)}
    )
    return corpus_record, scope_record


def selected(index: LocatorIndex, locators: Sequence[str] | None) -> set[str]:
    units = index.annotation_units().units
    if locators is None:
        return {u.key for u in units}
    out: set[str] = set()
    for locator in locators:
        if parse(locator).page != index.page:
            continue
        try:
            segment = index.resolve(locator)
        except ValueError as error:
            raise SliceError(str(error)) from error
        if segment.kind.value not in ("document", "unit", "paragraph"):
            raise SliceError(f"{locator}: scope must select a page, unit or paragraph")
        out.update(
            u.key
            for u in units
            if segment.start <= u.segment.start and u.segment.end <= segment.end
        )
    return out
