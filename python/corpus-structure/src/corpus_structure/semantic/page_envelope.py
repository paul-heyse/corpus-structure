"""Finite selected-page presentation over acquired envelopes and ordinal rows.

Array policies describe a direct row or one owned collection field, with optional
stable ordering and value projection. They never accept executable callbacks.
"""

from __future__ import annotations

from dataclasses import dataclass

from .continuation_codec import encode_cursor


@dataclass
class PageObservations:
    """Diagnostics observed by the same rich row stream used for the page."""

    unknowns: list


@dataclass(frozen=True)
class PageReuseRefusal:
    """The acquired, bounded explanation for withholding reuse handles."""

    module: str | None
    line: int
    reason: str
    omitted: int


@dataclass(frozen=True)
class PageEnvelope:
    """Fixed envelope and finite output-array/cursor policies for one acquired cut."""

    header: dict
    cursor_basis: dict
    cursor_field: str = "continuation"
    position_field: str = "ordinal"
    following_cursor: str | None = None
    arrays: tuple[tuple[str, str | None, str | None, str | None], ...] = (
        ("items", None, None, None),
    )
    include_knowledge: bool = False
    include_page_complete: bool = False
    observations: PageObservations | None = None
    reuse_refusal: PageReuseRefusal | None = None


def row_array(row, source: str | None, value_field: str | None):
    """Project one indivisible row for exact output-array width accounting."""
    values = (row,) if source is None else row[source]
    return tuple(values) if value_field is None else tuple(value[value_field] for value in values)


def apply_page_reuse_refusal(record: dict, refusal: PageReuseRefusal | None) -> dict:
    if refusal is None:
        return record
    result = dict(record)
    for field in ("cursor", "continuation", "next_cursor", "resource_handle"):
        if field in result:
            result[field] = None
    result["reuse"] = dict(
        eligible=False,
        reason="incomplete_code_identity",
        unknowns=[dict(module=refusal.module, line=refusal.line, reason=refusal.reason)],
        omitted=refusal.omitted,
    )
    return result


def render_envelope(envelope: PageEnvelope, end: int, has_rows: bool, more: bool) -> dict:
    continuation = (
        encode_cursor(dict(envelope.cursor_basis, **{envelope.position_field: end}))
        if more
        else envelope.following_cursor
    )
    result = dict(envelope.header)
    result.update({name: [] for name, _, _, _ in envelope.arrays})
    result[envelope.cursor_field] = continuation
    if envelope.include_knowledge:
        result["knowledge"] = "observed" if has_rows else "unknown"
    if envelope.include_page_complete:
        result["page_complete"] = continuation is None
    if envelope.observations is not None:
        result["unknowns"] = envelope.observations.unknowns
    return apply_page_reuse_refusal(result, envelope.reuse_refusal)


def render_page(envelope: PageEnvelope, end: int, values: list, more: bool) -> dict:
    result = render_envelope(envelope, end, bool(values), more)
    for name, source, value_field, order_by in envelope.arrays:
        entries = [entry for row in values for entry in ((row,) if source is None else row[source])]
        if order_by is not None:
            entries.sort(key=lambda entry: entry[order_by])
        result[name] = entries if value_field is None else [entry[value_field] for entry in entries]
    return result
