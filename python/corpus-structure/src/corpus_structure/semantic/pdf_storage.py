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
    membership: str = "direct",
    pointer: str | None = None,
    after: int = -1,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Read a pinned page of item projections; an incorrect pin always refuses."""
    if not 1 <= limit <= 1000 or after < -1 or membership not in {"direct", "descendants"}:
        raise ValueError("native item page requires limit 1..1000 and after >= -1")
    product = table("ops.native_document_product")
    actual = conn.execute(
        select(
            product.c.content_digest,
            product.c.contract_digest,
            product.c.schema_digest,
            product.c.release_id,
        ).where(
            product.c.task_id == task_id,
            product.c.product_key == product_key,
        )
    ).one()
    if actual.content_digest != content_digest:
        raise ValueError("native product digest differs from selected pin")
    from .pdf_contracts import pdf_context_for_task

    contexts = conn.info.setdefault("native_reader_contexts", {})
    if actual.release_id not in contexts:
        contexts[actual.release_id] = pdf_context_for_task(conn, task_id)
    context = contexts[actual.release_id]
    if (
        actual.contract_digest != context.contract_digest
        or actual.schema_digest != context.native_schema_digest
        or actual.schema_digest != _reader_schema_digest()
    ):
        raise NativeDocumentUnavailable(
            "native contract/schema requires a qualified archived reader"
        )
    item = table("kb.native_document_item")
    query = select(*[c for c in item.columns if c.name != "native_json"]).where(
        item.c.task_id == task_id, item.c.product_key == product_key, item.c.ordinal > after
    )
    if section_pointer is not None:
        if membership == "direct":
            query = query.where(item.c.section_pointer == section_pointer)
        else:
            query = query.where(
                item.c.pointer.in_(
                    native_descendant_pointers(
                        task_id=task_id, product_key=product_key, section_pointer=section_pointer
                    )
                )
            )
    if pointer is not None:
        query = query.where(item.c.pointer == pointer)
    return [
        dict(row) for row in conn.execute(query.order_by(item.c.ordinal).limit(limit)).mappings()
    ]


def native_descendant_pointers(*, task_id: int, product_key: str, section_pointer: str):
    """An indexed containment selection, preserving native ordinals in its caller."""
    item = table("kb.native_document_item")
    members = (
        select(item.c.pointer)
        .where(
            item.c.task_id == task_id,
            item.c.product_key == product_key,
            item.c.pointer == section_pointer,
        )
        .cte("native_members", recursive=True)
    )
    children = item.alias("native_children")
    members = members.union_all(
        select(children.c.pointer)
        .join(members, children.c.parent_pointer == members.c.pointer)
        .where(children.c.task_id == task_id, children.c.product_key == product_key)
    )
    return select(members.c.pointer)


def selected_native_ancestry(run_id: int):
    """Selected products and their exact immutable input pins, never ambient project products."""
    views, selected, products = map(
        table, ("kb.source_view", "ops.run_source_view", "ops.native_document_product")
    )
    pins = (
        select(
            views.c.native_task_id.label("task_id"),
            views.c.native_product_key.label("product_key"),
            views.c.native_content_digest.label("content_digest"),
        )
        .join(selected, selected.c.source_view_id == views.c.id)
        .where(selected.c.run_id == run_id)
        .distinct()
        .cte("selected_native_ancestry", recursive=True)
    )
    pins = pins.union(
        select(products.c.parent_task_id, products.c.parent_product_key, products.c.parent_digest)
        .join(
            pins,
            (products.c.task_id == pins.c.task_id)
            & (products.c.product_key == pins.c.product_key)
            & (products.c.content_digest == pins.c.content_digest),
        )
        .where(products.c.parent_task_id.is_not(None))
    )
    return pins


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
