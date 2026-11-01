"""Shared fixed-table projection of the trusted physical LinkML module.

Release definitions are rows in these tables. Compiling a candidate release never mutates
this MetaData and never creates a table. Migration, publication and queries share these objects.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import Table, MetaData

from corpus_structure.schema.relational import compile_metadata

PHYSICAL_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "physical.yaml"
PHYSICAL_MODEL_ID = "physical:" + sha256(PHYSICAL_MODEL.read_bytes()).hexdigest()
metadata = compile_metadata(SchemaView(str(PHYSICAL_MODEL)), target="semantic")
metadata.info["physical_model_id"] = PHYSICAL_MODEL_ID
tables = MappingProxyType(dict(metadata.tables))
SCHEMAS = frozenset({"sem", "data", "ops", "kb", "eval"})
_DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


_read_metadata = MetaData()
_selected_product = metadata.tables["ops.native_document_product"].to_metadata(
    _read_metadata, name="pdf_selected_product"
)


def table(name: str) -> Table:
    """Return a shared, explicitly schema-qualified Table."""
    if name == "ops.pdf_selected_product":
        return _selected_product
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
