"""Shared fixed-table projection of the trusted physical LinkML module.

Release definitions are rows in these tables. Compiling a candidate release never mutates
this MetaData and never creates a table. Migration, publication and queries share these objects.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType

from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import Table

from corpus_structure.schema.physical import physical_source_closure, physical_sources_id
from corpus_structure.schema.relational import compile_metadata

PHYSICAL_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "physical.yaml"


def physical_model_id(root: Path) -> str:
    """Identify the named trusted local import closure with unambiguous framing."""
    return physical_sources_id(
        physical_source_closure(root.name, lambda name: root.with_name(name).read_bytes())
    )


PHYSICAL_MODEL_ID = physical_model_id(PHYSICAL_MODEL)
metadata = compile_metadata(SchemaView(str(PHYSICAL_MODEL)), target="semantic")
metadata.info["physical_model_id"] = PHYSICAL_MODEL_ID
tables = MappingProxyType(dict(metadata.tables))
SCHEMAS = frozenset({"sem", "data", "ops", "kb", "eval"})
_DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


# Released view/record projections are modeled separately from stored-table authority.
# Alembic and physical admission consume only metadata above, never this read selection.
READ_MODEL = PHYSICAL_MODEL.with_name("read-projections.yaml")
_read_metadata = compile_metadata(SchemaView(str(READ_MODEL)), target="semantic-read")


def table(name: str) -> Table:
    """Return a shared, explicitly qualified stored relation or owned read shape."""
    if name in _read_metadata.tables:
        return _read_metadata.tables[name]
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
