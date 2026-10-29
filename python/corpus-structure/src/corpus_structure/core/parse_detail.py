"""A build's diagnostics: the `parse_detail` payload (`kb.rendition_build.parse_detail`; D4 M01).

The classes live in `core`, beside the other payload shapes, and ingest builds them. They are
generated from the `ParseDetail` payload class of `model/system.yaml` and its nested classes
(`_model/shapes.py`, Stage B, P0-M-5) and re-exported here. The payload is registered as
`parse_detail` in the payload-schema registry, so O1's rendition write finds its schema. These are
parser-dependent diagnostics: they never enter segment attributes or the content digest (D1 §3.2).

This module imports only the generated shapes, so the core schema generator can take its JSON
Schema without loading the HTML parser.
"""

from __future__ import annotations

from corpus_structure.core._model.shapes import (
    ExcludedElement,
    MathAnomaly,
    OrphanRun,
    ParseDetail,
    ParserError,
    RoleConflict,
    UnicodeChange,
)

__all__ = [
    "ExcludedElement", "MathAnomaly", "OrphanRun", "ParseDetail", "ParserError", "RoleConflict",
    "UnicodeChange",
]  # fmt: skip
