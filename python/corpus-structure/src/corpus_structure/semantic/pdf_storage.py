"""Bounded native-document reads through shared fixed metadata.

Publication is owned by pdf_contracts and the existing task lease. These readers
never initialize a converter or hydrate the native whole-document payload.
"""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import Any
from collections.abc import Sequence

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
    product = table("ops.pdf_selected_product")
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
    ).one_or_none()
    if actual is None:
        raise NativeDocumentUnavailable(
            "selected native content is unavailable"
        )
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
    """Selected products and every direct qualified input, using indexed immutable edges."""
    views, selected, edges = map(
        table, ("kb.source_view", "ops.run_source_view", "ops.pdf_product_input")
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
        select(edges.c.input_task_id, edges.c.input_product_key, edges.c.input_content_digest).join(
            pins, (edges.c.task_id == pins.c.task_id) & (edges.c.product_key == pins.c.product_key)
        )
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


def _pdf_product_identity(conn: Connection, task_id: int, product_key: str, content_digest: str):
    product = table("ops.pdf_product")
    identity = (
        conn.execute(
            select(product).where(
                product.c.task_id == task_id,
                product.c.product_key == product_key,
                product.c.content_digest == content_digest,
            )
        )
        .mappings()
        .one_or_none()
    )
    if identity is None:
        raise NativeDocumentUnavailable("exact PDF product pin is unavailable")
    from .pdf_contracts import pdf_context_for_task

    context = pdf_context_for_task(conn, task_id)
    if identity["contract_digest"] != context.contract_digest:
        raise NativeDocumentUnavailable("PDF product differs from its archived contract")
    if identity["kind"] != "native":
        context.execution.require_operation("read_pdf_product")
        expected = dict(context.execution.implementation_digests)
        root = files("corpus_structure").joinpath("semantic")
        if any(
            expected.get(name) != sha256(root.joinpath(filename).read_bytes()).hexdigest()
            for name, filename in (
                ("pdf/integrated.py", "pdf_integrated.py"),
                ("pdf/storage.py", "pdf_storage.py"),
            )
        ):
            raise NativeDocumentUnavailable(
                "companion implementation requires a qualified archived reader"
            )
        if "PdfIntegratedProduct" not in {d.name for d in context.boundary.definitions}:
            raise NativeDocumentUnavailable(
                "companion contract requires a qualified archived reader"
            )
    return dict(identity)


def _pdf_descriptors(conn: Connection, pins: list[tuple[int, str, str]]) -> list[dict[str, Any]]:
    """Compact per-product context; payload and native document columns are never selected."""
    from sqlalchemy import case, func, tuple_

    products, bodies, native = map(
        table, ("ops.pdf_product", "ops.pdf_product_body", "ops.native_document_product")
    )
    descriptor = case(
        (
            products.c.kind == "native",
            func.jsonb_build_object(
                "health",
                func.jsonb_build_object("conversion", native.c.health["conversion"]),
                "schema_digest",
                native.c.schema_digest,
                "recipe_digest",
                native.c.recipe_digest,
            ),
        ),
        else_=bodies.c.descriptor,
    ).label("descriptor")
    query = (
        select(products, descriptor)
        .outerjoin(
            bodies,
            (bodies.c.task_id == products.c.task_id)
            & (bodies.c.product_key == products.c.product_key),
        )
        .outerjoin(
            native,
            (native.c.task_id == products.c.task_id)
            & (native.c.product_key == products.c.product_key),
        )
        .where(
            tuple_(products.c.task_id, products.c.product_key, products.c.content_digest).in_(pins)
        )
        .order_by(products.c.task_id, products.c.product_key)
    )
    return [dict(row) for row in conn.execute(query).mappings()]


def read_pdf_product(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    occurrence_id: str | None = None,
    pointers: Sequence[str] | None = None,
    section_pointer: str | None = None,
    after: str = "",
    limit: int = 100,
    row_budget: int = 1000,
    include_body: bool = False,
) -> dict[str, Any]:
    """Read a bounded complete companion for the selected occurrence page.

    The aggregate row budget covers occurrences, all selected relationships/endpoints,
    direct input pins and coverage. Exceeding it refuses instead of silently truncating
    provenance. Whole content is an explicit separate materialization demand.
    """
    if not 1 <= limit <= 1000 or not 1 <= row_budget <= 10000:
        raise ValueError("PDF read limit must be 1..1000 and row budget 1..10000")
    identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
    occurrences, relations, endpoints, coverage, inputs = map(
        table,
        (
            "kb.pdf_occurrence",
            "kb.pdf_relation",
            "kb.pdf_relation_endpoint",
            "kb.pdf_product_coverage",
            "ops.pdf_product_input",
        ),
    )
    remaining = row_budget

    def bounded(query):
        nonlocal remaining
        rows = [
            dict(r)
            for r in conn.execute(
                query.limit(
                    min(limit, remaining + 1) if query is occurrence_query else remaining + 1
                )
            ).mappings()
        ]
        if len(rows) > remaining:
            raise ValueError("PDF mandatory companion exceeds requested row budget")
        remaining -= len(rows)
        return rows

    query = select(occurrences).where(
        occurrences.c.task_id == task_id,
        occurrences.c.product_key == product_key,
        occurrences.c.occurrence_id > after,
    )
    if occurrence_id is not None:
        query = query.where(occurrences.c.occurrence_id == occurrence_id)
    if pointers is not None:
        query = query.where(occurrences.c.body["pointer"].astext.in_(pointers))
    occurrence_query = query.order_by(occurrences.c.occurrence_id)
    rows = bounded(occurrence_query)
    if occurrence_id is not None and not rows:
        raise NativeDocumentUnavailable("PDF occurrence is unavailable under the exact pin")
    ids = [r["occurrence_id"] for r in rows]
    relation_ids = select(endpoints.c.relation_id).where(
        endpoints.c.task_id == task_id,
        endpoints.c.product_key == product_key,
        endpoints.c.target_task_id == task_id,
        endpoints.c.target_product_key == product_key,
        endpoints.c.occurrence_id.in_(ids),
    )
    relation_rows = bounded(
        select(
            *[column for column in relations.columns if column.name != "body"],
            relations.c.body.op("-")("endpoints").label("body"),
        )
        .where(
            relations.c.task_id == task_id,
            relations.c.product_key == product_key,
            relations.c.relation_id.in_(relation_ids),
        )
        .order_by(relations.c.relation_id)
    )
    selected_ids = [r["relation_id"] for r in relation_rows]
    endpoint_rows = bounded(
        select(endpoints)
        .where(
            endpoints.c.task_id == task_id,
            endpoints.c.product_key == product_key,
            endpoints.c.relation_id.in_(selected_ids),
        )
        .order_by(endpoints.c.relation_id, endpoints.c.endpoint_index)
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for endpoint in endpoint_rows:
        grouped.setdefault(endpoint["relation_id"], []).append(endpoint)
    for relation in relation_rows:
        relation["endpoints"] = grouped[relation["relation_id"]]
    # Coverage belongs to the materialized occurrence scope. A whole-document manifest
    # uses its own cursor rather than consuming every read's provenance budget.
    pages = {r["body"].get("page_no") for r in rows if r["body"].get("page_no") is not None}
    scopes = {"whole_document"}
    scopes.update(f"page:{p}" for p in pages)
    scopes.update(f"pages:{p}-{p}" for p in pages)
    if section_pointer is not None:
        scopes.update(section_pointer + ":" + m for m in ("direct", "descendants"))
    coverage_rows = bounded(
        select(coverage).where(
            coverage.c.task_id == task_id,
            coverage.c.product_key == product_key,
            coverage.c.body["scope"].astext.in_(scopes),
        ).order_by(coverage.c.coverage_id)
    ) if rows else []
    relevant_pins = {
        (e["target_task_id"], e["target_product_key"], e["target_content_digest"])
        for e in endpoint_rows if e["role"] != "output"
    }
    supporting_indices = {
        support["input_index"]
        for c in coverage_rows for support in c["body"].get("supports", ())
    }
    from sqlalchemy import or_, tuple_
    input_rows = bounded(
        select(inputs).where(
            inputs.c.task_id == task_id,
            inputs.c.product_key == product_key,
            or_(
                tuple_(inputs.c.input_task_id, inputs.c.input_product_key, inputs.c.input_content_digest).in_(sorted(relevant_pins)),
                inputs.c.input_index.in_(sorted(supporting_indices)),
            ),
        ).order_by(inputs.c.input_index)
    ) if relevant_pins or supporting_indices else []
    result = {
        "identity": identity,
        "descriptor": _pdf_descriptors(conn, [(task_id, product_key, content_digest)])[0]["descriptor"],
        "occurrences": rows,
        "relations": relation_rows,
        "inputs": input_rows,
        "coverage": coverage_rows,
        "mapping_reports": bounded(select(table("kb.pdf_mapping_report")).where(
            table("kb.pdf_mapping_report").c.task_id == task_id,
            table("kb.pdf_mapping_report").c.product_key == product_key,
            table("kb.pdf_mapping_report").c.input_index.in_([i["input_index"] for i in input_rows]),
        ).order_by(table("kb.pdf_mapping_report").c.report_index)) if input_rows else [],
        "cursor": rows[-1]["occurrence_id"] if len(rows) == limit else None,
        "manifest": {"collections": ["inputs", "coverage", "relations", "mapping_reports"], "paged": True},
    }
    if include_body:
        import json

        body = table(
            "ops.native_document_product"
            if identity["kind"] == "native"
            else "ops.pdf_product_body"
        )
        result["body"] = json.loads(
            conn.execute(
                select(body.c.payload).where(
                    body.c.task_id == task_id, body.c.product_key == product_key
                )
            ).scalar_one()
        )
    return result


def trace_pdf_occurrence(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    occurrence_id: str,
    limit: int = 1000,
) -> dict[str, Any]:
    """Follow the selected occurrence's attributed inputs, with bounded node materialization."""
    if not 1 <= limit <= 10000:
        raise ValueError("PDF trace limit must be 1..10000")
    _pdf_product_identity(conn, task_id, product_key, content_digest)
    occurrences, endpoints, products = map(
        table, ("kb.pdf_occurrence", "kb.pdf_relation_endpoint", "ops.pdf_product")
    )
    paths = (
        select(
            products.c.task_id,
            products.c.product_key,
            products.c.content_digest,
            occurrences.c.occurrence_id,
        )
        .join(
            occurrences,
            (occurrences.c.task_id == products.c.task_id)
            & (occurrences.c.product_key == products.c.product_key),
        )
        .where(
            products.c.task_id == task_id,
            products.c.product_key == product_key,
            products.c.content_digest == content_digest,
            occurrences.c.occurrence_id == occurrence_id,
        )
        .cte("pdf_trace", recursive=True)
    )
    output, source = endpoints.alias("trace_output"), endpoints.alias("trace_input")
    paths = paths.union(
        select(
            source.c.target_task_id,
            source.c.target_product_key,
            source.c.target_content_digest,
            source.c.occurrence_id,
        )
        .join_from(
            output,
            paths,
            (output.c.target_task_id == paths.c.task_id)
            & (output.c.target_product_key == paths.c.product_key)
            & (output.c.target_content_digest == paths.c.content_digest)
            & (output.c.occurrence_id == paths.c.occurrence_id),
        )
        .join(
            source,
            (source.c.task_id == output.c.task_id)
            & (source.c.product_key == output.c.product_key)
            & (source.c.relation_id == output.c.relation_id),
        )
        .where(output.c.role == "output", source.c.role != "output")
    )
    query = (
        select(paths, occurrences.c.body, products.c.kind, products.c.artifact_digest)
        .join(
            occurrences,
            (occurrences.c.task_id == paths.c.task_id)
            & (occurrences.c.product_key == paths.c.product_key)
            & (occurrences.c.occurrence_id == paths.c.occurrence_id),
        )
        .join(
            products,
            (products.c.task_id == paths.c.task_id)
            & (products.c.product_key == paths.c.product_key)
            & (products.c.content_digest == paths.c.content_digest),
        )
        .limit(limit + 1)
    )
    nodes = [dict(r) for r in conn.execute(query).mappings()]
    if not nodes:
        raise NativeDocumentUnavailable("PDF occurrence is unavailable under the exact pin")
    if len(nodes) > limit:
        raise ValueError("PDF trace exceeds requested node limit")
    pins = sorted(
        {(node["task_id"], node["product_key"], node["content_digest"]) for node in nodes}
    )
    return {"nodes": nodes, "products": _pdf_descriptors(conn, pins), "complete": True}


def read_pdf_manifest(conn: Connection, *, task_id: int, product_key: str,
                      content_digest: str, collection: str = "inputs", after: str = "",
                      limit: int = 100) -> dict[str, Any]:
    """Page the global companion without raising budgets or loading the content body."""
    if not 1 <= limit <= 1000:
        raise ValueError("PDF manifest limit must be 1..1000")
    identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
    choices = {
        "inputs": ("ops.pdf_product_input", "input_index"),
        "coverage": ("kb.pdf_product_coverage", "coverage_id"),
        "relations": ("kb.pdf_relation", "relation_id"),
        "mapping_reports": ("kb.pdf_mapping_report", "report_index"),
    }
    if collection not in choices:
        raise ValueError("unknown PDF manifest collection")
    name, key = choices[collection]
    relation = table(name)
    query = select(relation).where(relation.c.task_id == task_id, relation.c.product_key == product_key)
    if after:
        cursor = int(after) if collection in {"inputs", "mapping_reports"} else after
        query = query.where(relation.c[key] > cursor)
    rows = [dict(row) for row in conn.execute(query.order_by(relation.c[key]).limit(limit + 1)).mappings()]
    more = len(rows) > limit
    rows = rows[:limit]
    return {"identity": identity, "collection": collection, "rows": rows,
            "cursor": str(rows[-1][key]) if more else None}


def integrated_source_context(conn: Connection, *, task_id: int, product_key: str,
                              content_digest: str, pointers: Sequence[str],
                              section_pointer: str, membership: str) -> dict[str, Any] | None:
    """Selected source's mandatory companion, assembled from bounded occurrence pages."""
    identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
    if identity["kind"] == "native":
        return None
    if identity["kind"] != "integrated":
        raise NativeDocumentUnavailable("recognition observations are not selected source content")
    if membership not in {"direct", "descendants"}:
        raise ValueError("source membership is not qualified")
    from sqlalchemy import text
    result = conn.execute(text(
        "SELECT ops.integrated_source_context(:task,:key,:digest,CAST(:pointers AS text[]),:section,:membership)"
    ), dict(task=task_id, key=product_key, digest=content_digest, pointers=list(pointers),
            section=section_pointer, membership=membership)).scalar_one()
    if result is None:
        raise NativeDocumentUnavailable("integrated source companion is unavailable")
    return result
