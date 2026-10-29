"""The database projection (model and projections §3.4; ADR-0020; D3).

`metadata` is the generated `MetaData` of `_tables.py` with the physical overlay applied: importing
this package binds `overlay.py` to the generated tables by name and fails on a missing table or
column, or on a composite foreign key without a supporting index. `metadata.create_all` first
asserts the expected extension versions and creates the four schemas. Migration 0001 is generated
once from this and frozen (P0-F-4); it never imports this package.
"""

from __future__ import annotations

from corpus_structure.core.db._tables import metadata
from corpus_structure.core.db.overlay import OVERLAY, Overlay, OverlayBindingError

__all__ = ["OVERLAY", "Overlay", "OverlayBindingError", "metadata"]
