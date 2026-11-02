"""Shared fixed-table projection of the trusted physical LinkML module.

Release definitions are rows in these tables. Compiling a candidate release never mutates
this MetaData and never creates a table. Migration, publication and queries share these objects.
"""

from __future__ import annotations

import re
import struct
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

import yaml
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import MetaData, Table

from corpus_structure.schema.relational import compile_metadata

PHYSICAL_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "physical.yaml"


def physical_model_id(root: Path) -> str:
    """Identify the named trusted local import closure with unambiguous framing."""
    sources = {}

    def visit(path: Path):
        name = path.relative_to(root.parent).as_posix()
        if name in sources:
            return
        content = path.read_bytes()
        sources[name] = content
        for imported in yaml.safe_load(content).get("imports", ()):
            if ":" not in imported:  # package-owned linkml:types is toolchain input
                visit(path.parent / (imported + ".yaml"))

    visit(root)
    return physical_sources_id(sources)


def physical_sources_id(sources: dict[str, bytes]) -> str:
    """The same identity recipe for an explicitly retained source closure, with no I/O."""
    digest = sha256(b"corpus-physical-sources-1\0")
    for name, content in sorted(sources.items()):
        encoded = name.encode()
        digest.update(struct.pack(">Q", len(encoded)))
        digest.update(encoded)
        digest.update(struct.pack(">Q", len(content)))
        digest.update(content)
    return "physical:" + digest.hexdigest()


PHYSICAL_MODEL_ID = physical_model_id(PHYSICAL_MODEL)
metadata = compile_metadata(SchemaView(str(PHYSICAL_MODEL)), target="semantic")
metadata.info["physical_model_id"] = PHYSICAL_MODEL_ID
tables = MappingProxyType(dict(metadata.tables))
SCHEMAS = frozenset({"sem", "data", "ops", "kb", "eval"})
_DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


_read_metadata = MetaData()
_selected_product = metadata.tables["ops.native_document_product"].to_metadata(
    _read_metadata, name="pdf_selected_product"
)


_published_items = metadata.tables["kb.native_document_item"].to_metadata(
    _read_metadata, name="pdf_published_item", schema="ops"
)
_published_regions = metadata.tables["kb.native_document_region"].to_metadata(
    _read_metadata, name="pdf_published_region", schema="ops"
)

_published_coverage = metadata.tables["kb.native_document_coverage"].to_metadata(
    _read_metadata, name="pdf_published_coverage", schema="ops"
)


def table(name: str) -> Table:
    """Return a shared, explicitly schema-qualified Table."""
    if name == "ops.pdf_selected_product":
        return _selected_product
    if name == "ops.pdf_published_item":
        return _published_items
    if name == "ops.pdf_published_region":
        return _published_regions
    if name == "ops.pdf_published_coverage":
        return _published_coverage
    return tables[name]


def decimal_projection(lexical: str) -> Decimal | None:
    """Losslessly project finite decimal text only inside PostgreSQL NUMERIC's bounds.

    The caller persists ``lexical`` regardless of this result. ``None`` means exact numeric
    operations are unavailable; it never means that the original value is absent or rounded.
    """
    if not _DECIMAL.fullmatch(lexical):
        raise ValueError("not a finite decimal lexical value")
    try:
        value = Decimal(lexical)
    except InvalidOperation:
        # A syntactically valid exponent may exceed even Decimal's exponent range.
        return None
    digits = value.as_tuple()
    exponent = digits.exponent
    if not isinstance(exponent, int):
        raise ValueError("not a finite decimal lexical value")
    if max(len(digits.digits) + exponent, 0) > 131072 or max(-exponent, 0) > 16383:
        return None
    return value
