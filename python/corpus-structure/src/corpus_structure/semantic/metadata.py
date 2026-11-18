"""Shared fixed-table projection of the trusted physical LinkML module.

Release definitions are rows in these tables. Compiling a candidate release never mutates
this MetaData and never creates a table. Migration, publication and queries share these objects.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import MetaData, Table

from corpus_structure.model.compiled import running_model
from corpus_structure.schema.physical import physical_source_closure, physical_sources_id

PHYSICAL_MODEL = Path(__file__).resolve().parents[1] / "model" / "semantic" / "physical.yaml"


def physical_model_id(root: Path) -> str:
    """Identify the named trusted local import closure with unambiguous framing."""
    return physical_sources_id(
        physical_source_closure(root.name, lambda name: root.with_name(name).read_bytes())
    )


def get_metadata() -> MetaData:
    return running_model().physical()


def get_physical_model_id() -> str:
    return str(get_metadata().info["physical_model_id"])


_DECIMAL = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$")


# Released view/record projections are modeled separately from stored-table authority.
# Alembic and physical admission consume only metadata above, never this read selection.
READ_MODEL = PHYSICAL_MODEL.with_name("read-projections.yaml")


def table(name: str) -> Table:
    """Return a shared, explicitly qualified stored relation or owned read shape."""
    model = running_model()
    read = model.physical(READ_MODEL.name, target="semantic-read")
    if name in read.tables:
        return read.tables[name]
    return get_metadata().tables[name]


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
