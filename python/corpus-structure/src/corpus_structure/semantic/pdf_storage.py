"""Bounded native-document reads through shared fixed metadata.

Publication is owned by pdf_contracts and the existing task lease. These readers
never initialize a converter or hydrate the native whole-document payload.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Connection, select

from .metadata import table


class PdfObservationListRequest(BaseModel):
    """One closed source task's immutable recognition-product catalog."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    run_id: int = Field(gt=0)
    task_id: int = Field(gt=0)
    kind: Literal["recognition_observation"] = "recognition_observation"
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)

    def selection_digest(self) -> str:
        return sha256(
            json.dumps(
                self.model_dump(exclude={"cursor", "limit"}),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class PdfObservationPin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["recognition_observation"]
    task_id: int = Field(gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PdfObservationPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    selection: PdfObservationListRequest
    products: tuple[PdfObservationPin, ...]
    next_cursor: str | None = None


def read_pdf_observations(
    conn: Connection, request: PdfObservationListRequest
) -> PdfObservationPage:
    """Discover pins without loading Docling content or observation bodies.

    The existing archived read operation and terminal task lifecycle qualify this read.
    A task from another run/project is never an admitted observation-catalog scope.
    """
    tasks, builds = map(table, ("ops.task", "ops.source_build"))
    task = conn.execute(
        select(tasks.c.status, tasks.c.finished_at)
        .join(builds, builds.c.task_id == tasks.c.id)
        .where(tasks.c.id == request.task_id, tasks.c.run_id == request.run_id)
    ).one_or_none()
    if task is None:
        raise ValueError("source task is unavailable in the requested run/project")
    from .pdf_contracts import pdf_context_for_run

    context = pdf_context_for_run(conn, request.run_id)
    context.execution.require_operation("read_pdf_product")
    states = context.execution.lifecycle("task").states
    terminal = {
        value.value
        for state in states
        if state.terminal
        for value in state.values
        if value.dimension == "status"
    }
    nonterminal = {
        value.value
        for state in states
        if not state.terminal
        for value in state.values
        if value.dimension == "status"
    }
    if task.status not in terminal - nonterminal or task.finished_at is None:
        raise ValueError("recognition catalog requires a finished source task")
    after = ""
    if request.cursor is not None:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(request.cursor))
            if cursor["selection"] != request.selection_digest() or not isinstance(
                cursor["after"], str
            ):
                raise ValueError("cursor selection differs")
            after = cursor["after"]
        except (KeyError, ValueError, TypeError) as error:
            raise ValueError("invalid recognition catalog continuation") from error
    products = table("ops.pdf_product")
    rows = (
        conn.execute(
            select(
                products.c.kind,
                products.c.task_id,
                products.c.product_key,
                products.c.content_digest,
            )
            .where(
                products.c.task_id == request.task_id,
                products.c.kind == request.kind,
                products.c.product_key > after,
            )
            .order_by(products.c.product_key)
            .limit(request.limit + 1)
        )
        .mappings()
        .all()
    )
    more = len(rows) > request.limit
    pins = tuple(PdfObservationPin.model_validate(row) for row in rows[: request.limit])
    continuation = (
        base64.urlsafe_b64encode(
            json.dumps(
                {"selection": request.selection_digest(), "after": pins[-1].product_key}
            ).encode()
        ).decode()
        if more
        else None
    )
    return PdfObservationPage(selection=request, products=pins, next_cursor=continuation)


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
        raise NativeDocumentUnavailable("selected native content is unavailable")
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
    from .pdf_record_reader import published_native_table

    item = published_native_table(conn)
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
                        task_id=task_id,
                        product_key=product_key,
                        section_pointer=section_pointer,
                        conn=conn,
                    )
                )
            )
    if pointer is not None:
        query = query.where(item.c.pointer == pointer)
    return [
        dict(row) for row in conn.execute(query.order_by(item.c.ordinal).limit(limit)).mappings()
    ]


def native_descendant_pointers(
    *, task_id: int, product_key: str, section_pointer: str, conn: Connection | None = None
):
    """An indexed containment selection, preserving native ordinals in its caller."""
    from .pdf_record_reader import published_native_table

    item = published_native_table(conn) if conn is not None else table("kb.native_document_item")
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
    from .pdf_record_reader import published_native_table

    region = published_native_table(conn, "region")
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
    from .pdf_record_reader import published_record_reader
    from .product_reference import ProductReference

    record_reader = published_record_reader(
        conn, ProductReference(task_id, product_key, content_digest)
    )
    if record_reader is not None:
        product = table("ops.pdf_product")
        row = (
            conn.execute(
                select(product).where(
                    product.c.task_id == task_id,
                    product.c.product_key == product_key,
                    product.c.content_digest == content_digest,
                )
            )
            .mappings()
            .one()
        )
        return dict(row)
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
    if identity["kind"] == "native":
        native = table("ops.native_document_product")
        schema_digest = conn.execute(
            select(native.c.schema_digest).where(
                native.c.task_id == task_id,
                native.c.product_key == product_key,
            )
        ).scalar_one_or_none()
        if (
            schema_digest != context.native_schema_digest
            or schema_digest != _reader_schema_digest()
        ):
            raise NativeDocumentUnavailable(
                "native PDF schema requires a qualified archived reader"
            )
    else:
        from .contracts import approved_implementations
        from .types import PreparationError

        try:
            operation = context.execution.require_operation("read_pdf_product")
        except (PreparationError, StopIteration) as error:
            raise NativeDocumentUnavailable(
                "PDF read ABI is unsupported; qualify an archived reader"
            ) from error
        binding = next(
            b for b in context.execution.implementations if b.id == operation.implementation
        )
        implementation = approved_implementations()["read_pdf_product"]
        if (binding.owner, binding.symbol) != (
            implementation.__module__.removeprefix("corpus_structure."),
            implementation.__qualname__,
        ):
            raise NativeDocumentUnavailable("PDF read ABI owner differs from the qualified reader")
        if "PdfIntegratedProduct" not in {d.name for d in context.boundary.definitions}:
            raise NativeDocumentUnavailable(
                "companion contract requires a qualified archived reader"
            )
        descriptor = _pdf_descriptors(conn, [(task_id, product_key, content_digest)])[0][
            "descriptor"
        ]
        # Version 1 is the qualified immutable body/relational read ABI. Changes to helper
        # implementation bytes do not change stored meaning; a new body ABI requires a
        # new declared binding and an explicitly qualified reader.
        if (
            type(descriptor.get("version")) is not int
            or descriptor["version"] != 1
            or descriptor.get("kind") != identity["kind"]
        ):
            raise NativeDocumentUnavailable(
                "PDF body version/kind requires a qualified archived reader"
            )
        if identity["kind"] == "integrated":
            schema_digest = descriptor.get("content_metadata", {}).get("schema_digest")
            if (
                schema_digest != context.native_schema_digest
                or schema_digest != _reader_schema_digest()
            ):
                raise NativeDocumentUnavailable(
                    "selected Docling schema requires a qualified archived reader"
                )
    return dict(identity)


def _pdf_descriptors(conn: Connection, pins: list[tuple[int, str, str]]) -> list[dict[str, Any]]:
    """Compact per-product context; payload and native document columns are never selected."""
    from .pdf_record_reader import published_record_reader
    from .product_reference import ProductReference

    current: list[dict[str, Any]] = []
    archived = []
    for task, key, digest in pins:
        reader = published_record_reader(conn, ProductReference(task, key, digest))
        if reader is None:
            archived.append((task, key, digest))
        else:
            identity = _pdf_product_identity(conn, task, key, digest)
            current.append(
                dict(
                    identity,
                    descriptor=dict(version=2, kind=identity["kind"], revision=reader.revision),
                )
            )
    if not archived:
        return current
    pins = archived
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
    for row in conn.execute(query).mappings():
        value: dict[str, Any] = {column.key: row[column.key] for column in products.columns}
        value["descriptor"] = row["descriptor"]
        current.append(value)
    return sorted(current, key=lambda r: (r["task_id"], r["product_key"]))


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
    from .pdf_record_reader import published_record_reader
    from .product_reference import ProductReference

    record_reader = published_record_reader(
        conn, ProductReference(task_id, product_key, content_digest)
    )
    if record_reader is not None:
        identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
        selected = []
        if occurrence_id is not None:
            selected = list(
                record_reader.iter_rows(
                    "companion", {"family": "occurrence", "local_id": occurrence_id}
                )
            )
            if not selected:
                raise NativeDocumentUnavailable("PDF occurrence is unavailable under exact pin")
        elif pointers is None:
            prior = (
                record_reader._one("companion", {"family": "occurrence", "local_id": after})
                if after
                else None
            )
            rows = record_reader.iter_rows(
                "companion",
                {"family": "occurrence"},
                after=["occurrence", prior["ordinal"], after] if prior is not None else None,
            )
            from itertools import islice

            selected = list(islice(rows, limit))
        chosen = (
            list(pointers)
            if pointers is not None
            else [
                r["body"].get("pointer") for r in selected if r["body"].get("pointer") is not None
            ]
        )
        context = record_reader.source_context(
            chosen, section_pointer or "#/body", row_budget=row_budget
        )
        count = sum(
            len(context[name])
            for name in ("occurrences", "relations", "inputs", "coverage", "mapping_reports")
        )
        count += sum(len(r["endpoints"]) for r in context["relations"])
        if count > row_budget:
            raise ValueError("PDF mandatory companion exceeds requested row budget")
        result = dict(
            context,
            identity=identity,
            cursor=selected[-1]["local_id"] if len(selected) == limit else None,
            manifest={
                "collections": ["inputs", "coverage", "relations", "mapping_reports"],
                "paged": True,
            },
        )
        if include_body:
            import json
            from io import BytesIO

            if identity["kind"] == "native":
                result["body"] = record_reader.native_product_values()
            else:
                sink = BytesIO()
                record_reader.write_integrated_json(sink)
                result["body"] = json.loads(sink.getvalue())["product"]
        return result
    identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
    descriptor = _pdf_descriptors(conn, [(task_id, product_key, content_digest)])[0]["descriptor"]
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
        query = query.where(occurrences.c.pointer.in_(pointers))
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
    if identity["kind"] == "recognition_observation":
        page = descriptor.get("observation", {}).get("image", {}).get("page_no")
        if page is not None:
            pages.add(page)
    scopes = {"whole_document"}
    scopes.update(f"page:{p}" for p in pages)
    scopes.update(f"pages:{p}-{p}" for p in pages)
    if section_pointer is not None:
        scopes.update(section_pointer + ":" + m for m in ("direct", "descendants"))
    coverage_rows = (
        bounded(
            select(coverage)
            .where(
                coverage.c.task_id == task_id,
                coverage.c.product_key == product_key,
                coverage.c.body["scope"].astext.in_(scopes),
            )
            .order_by(coverage.c.coverage_id)
        )
        if rows or identity["kind"] == "recognition_observation"
        else []
    )
    relevant_pins = {
        (e["target_task_id"], e["target_product_key"], e["target_content_digest"])
        for e in endpoint_rows
        if e["role"] != "output"
    }
    supporting_indices = {
        support["input_index"] for c in coverage_rows for support in c["body"].get("supports", ())
    }
    from sqlalchemy import or_, tuple_

    input_rows = (
        bounded(
            select(inputs)
            .where(
                inputs.c.task_id == task_id,
                inputs.c.product_key == product_key,
                or_(
                    tuple_(
                        inputs.c.input_task_id,
                        inputs.c.input_product_key,
                        inputs.c.input_content_digest,
                    ).in_(sorted(relevant_pins)),
                    inputs.c.input_index.in_(sorted(supporting_indices)),
                ),
            )
            .order_by(inputs.c.input_index)
        )
        if relevant_pins or supporting_indices
        else []
    )
    result = {
        "identity": identity,
        "descriptor": descriptor,
        "occurrences": rows,
        "relations": relation_rows,
        "inputs": input_rows,
        "coverage": coverage_rows,
        "mapping_reports": bounded(
            select(table("kb.pdf_mapping_report"))
            .where(
                table("kb.pdf_mapping_report").c.task_id == task_id,
                table("kb.pdf_mapping_report").c.product_key == product_key,
                table("kb.pdf_mapping_report").c.input_index.in_(
                    [i["input_index"] for i in input_rows]
                ),
            )
            .order_by(table("kb.pdf_mapping_report").c.report_index)
        )
        if input_rows
        else [],
        "cursor": rows[-1]["occurrence_id"] if len(rows) == limit else None,
        "manifest": {
            "collections": ["inputs", "coverage", "relations", "mapping_reports"],
            "paged": True,
        },
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
    from .pdf_record_reader import published_record_reader
    from .product_reference import ProductReference

    record_reader = published_record_reader(
        conn, ProductReference(task_id, product_key, content_digest)
    )
    if record_reader is not None:
        pending = [(task_id, product_key, content_digest, occurrence_id)]
        visited = set()
        nodes = []
        while pending:
            task, key, digest, occurrence = pending.pop()
            pin = (task, key, digest, occurrence)
            if pin in visited:
                continue
            visited.add(pin)
            reader = published_record_reader(conn, ProductReference(task, key, digest))
            if reader is None:
                branch = trace_pdf_occurrence(
                    conn,
                    task_id=task,
                    product_key=key,
                    content_digest=digest,
                    occurrence_id=occurrence,
                    limit=limit - len(nodes),
                )
                for node in branch["nodes"]:
                    identity = (
                        node["task_id"],
                        node["product_key"],
                        node["content_digest"],
                        node["occurrence_id"],
                    )
                    if identity not in {
                        (n["task_id"], n["product_key"], n["content_digest"], n["occurrence_id"])
                        for n in nodes
                    }:
                        nodes.append(node)
            else:
                row = reader._one("companion", {"family": "occurrence", "local_id": occurrence})
                identity = _pdf_product_identity(conn, task, key, digest)
                nodes.append(
                    dict(
                        task_id=task,
                        product_key=key,
                        content_digest=digest,
                        occurrence_id=occurrence,
                        body=row["body"],
                        kind=identity["kind"],
                        artifact_digest=reader.revision["source_digest"],
                    )
                )
                pointer = row["body"].get("pointer")
                context = reader.source_context(
                    [pointer] if pointer is not None else [], "#/body", row_budget=limit
                )
                for relation in context["relations"]:
                    if any(
                        e["role"] == "output" and e["occurrence_id"] == occurrence
                        for e in relation["endpoints"]
                    ):
                        pending.extend(
                            (
                                e["target_task_id"],
                                e["target_product_key"],
                                e["target_content_digest"],
                                e["occurrence_id"],
                            )
                            for e in relation["endpoints"]
                            if e["role"] != "output"
                        )
            if len(nodes) > limit:
                raise ValueError("PDF trace exceeds requested node limit")
        pins = sorted({(n["task_id"], n["product_key"], n["content_digest"]) for n in nodes})
        return dict(nodes=nodes, products=_pdf_descriptors(conn, pins), complete=True)
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


def read_pdf_manifest(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    collection: str = "inputs",
    after: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """Page the global companion without raising budgets or loading the content body."""
    if not 1 <= limit <= 1000:
        raise ValueError("PDF manifest limit must be 1..1000")
    from .pdf_record_reader import published_record_reader
    from .product_reference import ProductReference

    record_reader = published_record_reader(
        conn, ProductReference(task_id, product_key, content_digest)
    )
    if record_reader is not None:
        from itertools import islice

        families = {
            "inputs": "input",
            "coverage": "coverage",
            "relations": "relation",
            "mapping_reports": "mapping_report",
        }
        if collection not in families:
            raise ValueError("unknown PDF manifest collection")
        family = families[collection]
        prior = (
            record_reader._one("companion", {"family": family, "local_id": after})
            if after
            else None
        )
        rows = list(
            islice(
                record_reader.iter_rows(
                    "companion",
                    {"family": family},
                    after=[family, prior["ordinal"], after] if prior is not None else None,
                ),
                limit + 1,
            )
        )
        more = len(rows) > limit
        rows = rows[:limit]
        return dict(
            identity=_pdf_product_identity(conn, task_id, product_key, content_digest),
            collection=collection,
            rows=[r["body"] for r in rows],
            cursor=rows[-1]["local_id"] if more else None,
        )
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
    query = select(relation).where(
        relation.c.task_id == task_id, relation.c.product_key == product_key
    )
    if after:
        cursor = int(after) if collection in {"inputs", "mapping_reports"} else after
        query = query.where(relation.c[key] > cursor)
    rows = [
        dict(row)
        for row in conn.execute(query.order_by(relation.c[key]).limit(limit + 1)).mappings()
    ]
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "identity": identity,
        "collection": collection,
        "rows": rows,
        "cursor": str(rows[-1][key]) if more else None,
    }


def integrated_source_context(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    pointers: Sequence[str],
    section_pointer: str,
    membership: str,
) -> dict[str, Any] | None:
    """Selected source's mandatory companion, assembled from bounded occurrence pages."""
    from .pdf_record_reader import published_record_reader
    from .product_reference import ProductReference

    record_reader = published_record_reader(
        conn, ProductReference(task_id, product_key, content_digest)
    )
    if record_reader is not None:
        if membership not in {"direct", "descendants"}:
            raise ValueError("source membership is not qualified")
        identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
        if identity["kind"] == "native":
            return None
        return record_reader.source_context(pointers, section_pointer)
    identity = _pdf_product_identity(conn, task_id, product_key, content_digest)
    if identity["kind"] == "native":
        return None
    if identity["kind"] != "integrated":
        raise NativeDocumentUnavailable("recognition observations are not selected source content")
    if membership not in {"direct", "descendants"}:
        raise ValueError("source membership is not qualified")
    from sqlalchemy import text

    result = conn.execute(
        text(
            "SELECT ops.integrated_source_context(:task,:key,:d"
            "igest,CAST(:pointers AS text[]),:section,:membersh"
            "ip)"
        ),
        dict(
            task=task_id,
            key=product_key,
            digest=content_digest,
            pointers=list(pointers),
            section=section_pointer,
            membership=membership,
        ),
    ).scalar_one()
    if result is None:
        raise NativeDocumentUnavailable("integrated source companion is unavailable")
    return result


def read_pdf_artifact(
    conn: Connection,
    *,
    task_id: int,
    product_key: str,
    content_digest: str,
    artifact_digest: str,
    offset: int = 0,
) -> dict[str, Any]:
    """Read a fixed byte page from the exact product's retained input custody."""
    if type(offset) is not int or offset < 0:
        raise ValueError("PDF artifact offset must be a nonnegative byte offset")
    if len(artifact_digest) != 64 or any(c not in "0123456789abcdef" for c in artifact_digest):
        raise ValueError("PDF artifact requires its SHA-256 digest")
    _pdf_product_identity(conn, task_id, product_key, content_digest)
    from sqlalchemy import func, tuple_

    inputs, custody, artifacts = map(
        table, ("ops.pdf_product_input", "ops.pdf_product_artifact", "kb.source_artifact")
    )
    products = table("ops.pdf_product")
    pins = (
        select(products.c.task_id, products.c.product_key, products.c.content_digest)
        .where(
            products.c.task_id == task_id,
            products.c.product_key == product_key,
            products.c.content_digest == content_digest,
        )
        .cte("artifact_input_custody", recursive=True)
    )
    pins = pins.union(
        select(
            inputs.c.input_task_id, inputs.c.input_product_key, inputs.c.input_content_digest
        ).join(
            pins,
            (inputs.c.task_id == pins.c.task_id) & (inputs.c.product_key == pins.c.product_key),
        )
    )
    member = select(custody.c.artifact_digest).where(
        tuple_(custody.c.task_id, custody.c.product_key).in_(
            select(pins.c.task_id, pins.c.product_key)
        ),
        custody.c.artifact_digest == artifact_digest,
    )
    row = (
        conn.execute(
            select(
                func.octet_length(artifacts.c.content).label("total_bytes"),
                func.substring(artifacts.c.content, offset + 1, 65536).label("content"),
            ).where(
                artifacts.c.artifact_digest == artifact_digest,
                artifacts.c.artifact_digest.in_(member),
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise NativeDocumentUnavailable("artifact is outside the exact PDF input custody")
    if offset > row["total_bytes"]:
        raise ValueError("PDF artifact offset exceeds retained byte length")
    content = bytes(row["content"])
    next_offset = offset + len(content)
    return {
        "artifact_digest": artifact_digest,
        "total_bytes": row["total_bytes"],
        "offset": offset,
        "content": content,
        "next_offset": next_offset if next_offset < row["total_bytes"] else None,
    }
