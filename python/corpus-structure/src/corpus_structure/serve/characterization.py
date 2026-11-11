"""Pin-native enriched-document inspection; source and analysis remain separate."""

from __future__ import annotations

import base64
import json
from hashlib import sha256
from heapq import heappush_max, heappushpop_max
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, model_validator

from corpus_structure.semantic.characterization import AnnotationReference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.refusals import SemanticRefusal


class CharacterizationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int = Field(strict=True, gt=0)
    task_id: int = Field(strict=True, gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern="^[0-9a-f]{64}$")
    view: Literal["summary", "annotations", "membership", "terms", "reading", "coverage"] = (
        "summary"
    )
    layer_key: str | None = None
    annotation_id: str | None = None
    family: str | None = None
    kind: str | None = None
    page: int | None = Field(default=None, strict=True, gt=0)
    choices: tuple[str, ...] = ()
    external_choices: tuple[AnnotationReference, ...] = ()
    cursor: str | None = Field(default=None, max_length=8192)
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=1_048_576, strict=True, ge=1, le=8_388_608)

    @model_validator(mode="after")
    def selection(self):
        if self.view == "coverage" and any(
            (self.layer_key, self.annotation_id, self.family, self.kind, self.page)
        ):
            raise ValueError("coverage inspection requires the whole view without node filters")
        if self.view == "membership" and not self.annotation_id:
            raise ValueError("membership inspection requires annotation_id")
        if (self.choices or self.external_choices) and (
            self.view != "reading" or not self.layer_key
        ):
            raise ValueError("choice selection requires reading inspection and an exact layer_key")
        if self.view == "reading" and (not self.layer_key or not self.annotation_id):
            raise ValueError("reading inspection requires layer_key and annotation_id root")
        if self.family and self.view != "annotations":
            raise ValueError("family filter requires annotation inspection")
        if self.kind and self.view != "annotations":
            raise ValueError("kind filter requires annotation inspection")
        if self.page is not None and self.view not in {"annotations", "membership"}:
            raise ValueError("page selection requires annotation or membership inspection")
        if self.annotation_id and self.view not in {"membership", "terms", "reading"}:
            raise ValueError("annotation_id is not used by this inspection")
        if len(set(self.choices)) != len(self.choices):
            raise ValueError("choice selection contains duplicates")
        return self

    def reference(self) -> ProductReference:
        return ProductReference(self.task_id, self.product_key, self.content_digest)


class CharacterizationResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    format: Literal["enriched-document-inspection-v1"] = "enriched-document-inspection-v1"
    reference: dict[str, JsonValue]
    base_document: dict[str, JsonValue]
    profile: str
    coverage: tuple[dict[str, JsonValue], ...]
    coverage_total: int = Field(ge=0, description="Exact number of retained coverage rows.")
    coverage_truncated: bool = Field(
        description=(
            "Inline coverage omits retained rows; view=coverage returns exact rows in items."
        )
    )
    coverage_continuation: str | None = Field(
        default=None,
        description=(
            "Continue inline coverage with the same product/run, view=coverage, no node "
            "filters, and cursor=this value. Coverage-view items use continuation instead."
        ),
    )
    items: tuple[dict[str, JsonValue], ...]
    continuation: str | None = None
    standing: Literal["private_analyses"] = "private_analyses"
    membership_scope: Literal["complete_recorded_members", "selected_annotations", "not_requested"]
    source_items: dict[str, JsonValue] = Field(default_factory=dict)


def _pin(value):
    return ProductReference(**value)


def _selection_key(request):
    value = request.model_dump(mode="json", exclude={"cursor", "limit", "max_bytes"})
    return sha256(canonical_bytes(value)).hexdigest()


def _page(rows, request):
    """A cursor binds immutable products and selectors, independently of page size."""
    selection = _selection_key(request)
    offset = 0
    if request.cursor is not None:
        parts = request.cursor.split(":")
        if len(parts) != 2 or parts[0] != selection or not parts[1].isdigit():
            raise SemanticRefusal("enriched-document continuation differs from selection")
        offset = int(parts[1])
    if offset > len(rows):
        raise SemanticRefusal("enriched-document continuation is outside membership")
    end = min(offset + request.limit, len(rows))
    return tuple(rows[offset:end]), f"{selection}:{end}" if end < len(rows) else None


_COVERAGE_ROW = TypeAdapter(dict[str, JsonValue])


def _coverage_cursor(request, offset):
    selection = request.model_copy(
        update={
            "view": "coverage",
            "layer_key": None,
            "annotation_id": None,
            "family": None,
            "kind": None,
            "page": None,
            "choices": (),
            "external_choices": (),
        }
    )
    return f"{_selection_key(selection)}:{offset}"


def _response(view, request, *, items, continuation, membership_scope):
    """One bounded response contract for native reads and detached inspection."""
    coverage = view.get("coverage", ())
    total = len(coverage)
    response = CharacterizationResponse(
        reference=request.reference().values(),
        base_document=view["base_document"],
        profile=view["profile"],
        coverage=(),
        coverage_total=total,
        coverage_truncated=bool(total),
        coverage_continuation=(
            _coverage_cursor(request, total) if total and request.view != "coverage" else None
        ),
        items=items,
        continuation=continuation,
        membership_scope=membership_scope,
    )
    return _with_inline_coverage(response, coverage, request)


def _with_inline_coverage(response, coverage, request):
    total = response.coverage_total
    response = response.model_copy(
        update={
            "coverage": (),
            "coverage_truncated": bool(total),
            "coverage_continuation": (
                _coverage_cursor(request, total) if total and request.view != "coverage" else None
            ),
        }
    )
    if request.view != "coverage":
        # Reserve the largest possible offset and the extra byte of `false`.
        remaining = request.max_bytes - len(response.model_dump_json().encode()) - 1
        prefix = []
        for row in coverage:
            if len(prefix) >= request.limit:
                break
            length = len(_COVERAGE_ROW.dump_json(row)) + bool(prefix)
            if length > remaining:
                break
            prefix.append(row)
            remaining -= length
        truncated = len(prefix) < total
        response = response.model_copy(
            update={
                "coverage": tuple(prefix),
                "coverage_truncated": truncated,
                "coverage_continuation": _coverage_cursor(request, len(prefix))
                if truncated
                else None,
            }
        )
    if len(response.model_dump_json().encode()) > request.max_bytes:
        raise SemanticRefusal("enriched-document response exceeds byte budget; narrow the page")
    return response


def _node_position(request) -> tuple[int, str, str] | None:
    if request.cursor is None:
        return None
    try:
        selection, encoded = request.cursor.split(":")
        if selection != _selection_key(request):
            raise ValueError("selection differs")
        after = json.loads(base64.b64decode(encoded, altchars=b"-_", validate=True))
        if (
            not isinstance(after, list)
            or len(after) != 3
            or type(after[0]) is not int
            or after[0] < 1
            or any(not isinstance(value, str) or not value for value in after[1:])
        ):
            raise ValueError("invalid position")
        return after[0], after[1], after[2]
    except (ValueError, TypeError) as error:
        raise SemanticRefusal("enriched-document continuation differs from selection") from error


def _node_cursor(request, after):
    if after is None:
        return None
    encoded = base64.urlsafe_b64encode(canonical_bytes(after)).decode()
    cursor = f"{_selection_key(request)}:{encoded}"
    if len(cursor) > 8192:
        raise SemanticRefusal("enriched-document continuation exceeds bound")
    return cursor


def _node_key(row):
    node = row.get("membership", row.get("annotation", row.get("term")))
    return row["layer"]["task_id"], row["layer"]["product_key"], node["local_id"]


class _NodePage:
    """Keep the earliest requested nodes plus one continuation witness."""

    def __init__(self, request):
        self.request = request
        self.after = _node_position(request)
        self.rows = []
        self.ordinal = 0

    def append(self, row):
        key = _node_key(row)
        if self.after is not None and key <= self.after:
            return
        entry = (key, self.ordinal, row)
        self.ordinal += 1
        if len(self.rows) <= self.request.limit:
            heappush_max(self.rows, entry)
        else:
            heappushpop_max(self.rows, entry)

    def page(self):
        rows = [entry[2] for entry in sorted(self.rows)]
        items = tuple(rows[: self.request.limit])
        continuation = (
            _node_cursor(self.request, _node_key(items[-1])) if len(rows) > len(items) else None
        )
        return items, continuation


def _reading_dependencies(layer, layers):
    from corpus_structure.semantic.characterization import LayerReport

    reports = {}
    pending = [_pin(value) for value in layer.get("dependencies", ())]
    while pending:
        pin = pending.pop()
        if pin in reports:
            continue
        key = (pin.task_id, pin.product_key, pin.content_digest)
        if key not in layers:
            raise SemanticRefusal("enriched-document layer closure is incomplete")
        body = layers[key]
        reports[pin] = LayerReport(canonical_bytes(body))
        pending.extend(_pin(value) for value in body.get("dependencies", ()))
    return reports


def _outside_page(occurrences, page):
    if page is None:
        return False
    pages = [extent.get("page") for occurrence in occurrences for extent in occurrence["extents"]]
    if page in pages:
        return False
    return None if not pages or None in pages else True


def inspect_captured_characterization(view, layers, request):
    """Inspect already validated retained objects; never run linguistic inference."""
    if sha256(canonical_bytes(view)).hexdigest() != request.content_digest:
        raise SemanticRefusal("enriched-document payload differs from requested pin")
    node_page = request.view in {"membership", "annotations", "terms"}
    rows = _NodePage(request) if node_page else []
    membership_scope = "not_requested"
    if request.view == "coverage":
        items, continuation = _page(view.get("coverage", ()), request)
        return _response(
            view,
            request,
            items=items,
            continuation=continuation,
            membership_scope=membership_scope,
        )
    if request.view == "summary":
        rows = [
            dict(
                layer=reference,
                active=reference in view.get("active_layers", view.get("layers", ())),
            )
            for reference in view.get("layers", ())
            if request.layer_key is None or reference["product_key"] == request.layer_key
        ]
    else:
        for reference in (
            view.get("layers", ())
            if request.layer_key
            else view.get("active_layers", view.get("layers", ()))
        ):
            if request.layer_key is not None and reference["product_key"] != request.layer_key:
                continue
            key = (reference["task_id"], reference["product_key"], reference["content_digest"])
            if key not in layers:
                raise SemanticRefusal("enriched-document layer closure is incomplete")
            layer = layers[key]
            if layer["base_document"] != view["base_document"]:
                raise SemanticRefusal("enriched-document layer belongs to another source")
            if request.family and request.family not in layer["operation"]["produced_families"]:
                continue
            occurrences = {item["local_id"]: item for item in layer.get("occurrences", ())}
            annotations = {item["local_id"]: item for item in layer.get("annotations", ())}

            def visible(ids, occurrences=occurrences):
                return request.page is None or any(
                    extent.get("page") == request.page
                    for identity in ids
                    for extent in occurrences.get(identity, {}).get("extents", ())
                )

            if request.view == "annotations":
                membership_scope = "selected_annotations"
                for annotation in annotations.values():
                    if request.family and annotation["family"] != request.family:
                        continue
                    if request.kind and annotation["kind"] != request.kind:
                        continue
                    ids = annotation.get("occurrences", ())
                    if visible(ids):
                        rows.append(
                            dict(
                                layer=reference,
                                annotation=annotation,
                                occurrences=[occurrences[i] for i in ids],
                            )
                        )
            elif request.view == "membership":
                membership_scope = "complete_recorded_members"
                for member in layer.get("memberships", ()):
                    if member["group"] != request.annotation_id:
                        continue
                    ids = member.get("occurrences", ())
                    rows.append(
                        dict(
                            layer=reference,
                            membership=member,
                            occurrences=[occurrences[i] for i in ids],
                            outside_selection=_outside_page(
                                [occurrences[i] for i in ids], request.page
                            ),
                        )
                    )
            elif request.view == "reading":
                from corpus_structure.semantic.characterization import LayerReport, project_reading

                reading = project_reading(
                    LayerReport(canonical_bytes(layer)),
                    request.annotation_id,
                    choices=request.choices,
                    dependencies=_reading_dependencies(layer, layers),
                    external_choices=request.external_choices,
                )
                ids = {i for term in reading["terms"] for i in term.get("occurrences", ())}
                rows.append(
                    dict(
                        layer=reference,
                        reading=reading,
                        occurrences=[occurrences[i] for i in sorted(ids)],
                    )
                )
            else:
                for term in layer.get("terms", ()):
                    if (
                        request.annotation_id is not None
                        and term["local_id"] != request.annotation_id
                    ):
                        continue
                    rows.append(
                        dict(
                            layer=reference,
                            term=term,
                            occurrences=[occurrences[i] for i in term.get("occurrences", ())],
                            choices=sorted(
                                [
                                    group
                                    for group in layer.get("choices", ())
                                    if any(
                                        member["root"] == term["local_id"]
                                        or member["local_id"] in term.get("required_choices", ())
                                        for member in group["members"]
                                    )
                                ],
                                key=lambda group: group["local_id"],
                            ),
                            roles=sorted(
                                [
                                    role
                                    for role in layer.get("roles", ())
                                    if term["local_id"] in (role["owner"], role["member"])
                                ],
                                key=lambda role: role["local_id"],
                            ),
                        )
                    )
    if isinstance(rows, _NodePage):
        items, continuation = rows.page()
    else:
        rows.sort(key=canonical_bytes)
        items, continuation = _page(rows, request)
    return _response(
        view,
        request,
        items=items,
        continuation=continuation,
        membership_scope=membership_scope,
    )


def inspect_characterization(conn, request: CharacterizationRequest):
    from corpus_structure.semantic.characterization_store import (
        read_layer,
        read_memberships,
        read_nodes,
        read_view,
    )

    view = read_view(conn, request.reference(), run_id=request.run_id).payload
    if request.view == "membership":
        assert request.annotation_id is not None
        page = read_memberships(
            conn,
            request.reference(),
            (request.annotation_id,),
            run_id=request.run_id,
            after=_node_position(request),
            limit=request.limit,
            max_bytes=request.max_bytes,
            layer_key=request.layer_key,
        )
        rows = page["memberships"]
        for row in rows:
            row["outside_selection"] = _outside_page(row["occurrences"], request.page)
        items = tuple(rows)
        continuation = _node_cursor(request, page["next_after"])
        response = _response(
            view,
            request,
            items=items,
            continuation=continuation,
            membership_scope="complete_recorded_members",
        )
        return _source_context(conn, view, response, request)
    if request.view in {"annotations", "terms"}:
        page = read_nodes(
            conn,
            request.reference(),
            request.view,
            run_id=request.run_id,
            selectors={
                key: value
                for key, value in {
                    "layer_key": request.layer_key,
                    "family": request.family,
                    "annotation_kind": request.kind,
                    "page": request.page,
                    "local_id": request.annotation_id,
                }.items()
                if value is not None
            },
            after=_node_position(request),
            limit=request.limit,
            max_bytes=request.max_bytes,
        )
        rows = []
        for item in page["nodes"]:
            row = dict(layer=item["layer"], occurrences=item["occurrences"])
            if request.view == "annotations":
                row["annotation"] = item["node"]
            else:
                row.update(term=item["node"], choices=item["choices"], roles=item["roles"])
            rows.append(row)
        response = _response(
            view,
            request,
            items=tuple(rows),
            continuation=_node_cursor(request, page["next_after"]),
            membership_scope="selected_annotations"
            if request.view == "annotations"
            else "not_requested",
        )
        return _source_context(conn, view, response, request)
    layers = {}
    remaining = request.max_bytes
    if request.view not in {"summary", "coverage"}:
        for reference in view.get("layers", ()):
            pin = _pin(reference)
            if request.layer_key is None or pin.product_key == request.layer_key:
                report = read_layer(conn, pin, run_id=request.run_id, max_bytes=request.max_bytes)
                remaining -= len(report.content)
                layers[(pin.task_id, pin.product_key, pin.content_digest)] = report.payload
        if request.view == "reading":
            pending = [dep for body in layers.values() for dep in body.get("dependencies", ())]
            allowed = {_pin(pin) for pin in view.get("layers", ())}
            while pending:
                pin = _pin(pending.pop())
                key = (pin.task_id, pin.product_key, pin.content_digest)
                if key in layers:
                    continue
                if pin not in allowed or remaining <= 0:
                    raise SemanticRefusal(
                        "reading dependency closure exceeds selected view or byte budget"
                    )
                report = read_layer(conn, pin, run_id=request.run_id, max_bytes=remaining)
                remaining -= len(report.content)
                layers[key] = report.payload
                pending.extend(report.payload.get("dependencies", ()))
    return _source_context(
        conn, view, inspect_captured_characterization(view, layers, request), request
    )


def _source_context(conn, view, response, request):
    """Batch only selected native items and their ancestor frontier under the same pin."""
    from corpus_structure.semantic.pdf_record_reader import (
        PublishedReadBudget,
        published_record_reader,
    )
    from corpus_structure.semantic.releases import open_release

    if not _source_pointers(response):
        return response
    reader = published_record_reader(
        conn,
        _pin(view["base_document"]),
        projection_context=open_release(conn, view["release_id"]),
        read_budget=PublishedReadBudget(10000, request.max_bytes),
    )
    if reader is None:
        raise SemanticRefusal("enriched-document base is unavailable")
    return add_source_context(response, request, reader.selected_native_items)


def _source_pointers(response):
    return {
        extent["native_pointer"]
        for row in response.items
        for occurrence in row.get("occurrences", ())
        for extent in occurrence["extents"]
        if "native_pointer" in extent
    }


def add_source_context(response, request, fetch):
    """Live and detached reads hydrate the same selected native ancestor frontier."""
    pointers = _source_pointers(response)
    items = {}
    while pointers:
        batch = fetch(tuple(sorted(pointers)))
        items.update(batch)
        pointers = {
            item["parent"]["$ref"]
            for item in batch.values()
            if item.get("parent") and item["parent"]["$ref"] not in items
        }
    response = response.model_copy(update={"source_items": items})
    return _with_inline_coverage(response, response.coverage, request)
