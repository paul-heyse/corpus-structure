"""Bounded native-document reads through shared fixed metadata.

Publication is owned by pdf_contracts and the existing task lease. These readers
never initialize a converter or hydrate the native whole-document payload.
"""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import Any

from sqlalchemy import Connection, select

from .metadata import table


class NativeDocumentUnavailable(ValueError):
    """The pinned product has no qualified reader for its archived contract."""


@lru_cache(maxsize=1)
def _reader_schema_digest() -> str:
    return sha256(
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    ).hexdigest()


def read_native_items(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    section_pointer: str | None = None,
    pointer: str | None = None,
    after: int = -1,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Read a pinned page of item projections; an incorrect pin always refuses."""
    if not 1 <= limit <= 1000 or after < -1:
        raise ValueError("native item page requires limit 1..1000 and after >= -1")
    product = table("ops.native_document_product")
    actual = conn.execute(
        select(product.c.content_digest, product.c.contract_digest, product.c.schema_digest).where(
            product.c.task_id == task_id,
            product.c.product_key == product_key,
        )
    ).one()
    if actual.content_digest != content_digest:
        raise ValueError("native product digest differs from selected pin")
    from .pdf_contracts import PDF_CONTRACT_DIGEST

    if (
        actual.contract_digest != PDF_CONTRACT_DIGEST
        or actual.schema_digest != _reader_schema_digest()
    ):
        raise NativeDocumentUnavailable(
            "native contract/schema requires a qualified archived reader"
        )
    item = table("kb.native_document_item")
    query = select(item).where(
        item.c.task_id == task_id, item.c.product_key == product_key, item.c.ordinal > after
    )
    if section_pointer is not None:
        query = query.where(item.c.section_pointer == section_pointer)
    if pointer is not None:
        query = query.where(item.c.pointer == pointer)
    return [
        dict(row) for row in conn.execute(query.order_by(item.c.ordinal).limit(limit)).mappings()
    ]


def read_native_regions(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    pointer: str,
) -> list[dict[str, Any]]:
    """Resolve only regions attached to a pinned native occurrence."""
    if not read_native_items(
        conn,
        task_id=task_id,
        product_key=product_key,
        content_digest=content_digest,
        pointer=pointer,
        limit=1,
    ):
        raise ValueError("native occurrence unavailable")
    region = table("kb.native_document_region")
    return [
        dict(row)
        for row in conn.execute(
            select(region)
            .where(
                region.c.task_id == task_id,
                region.c.product_key == product_key,
                region.c.pointer == pointer,
            )
            .order_by(region.c.region_index)
        ).mappings()
    ]
