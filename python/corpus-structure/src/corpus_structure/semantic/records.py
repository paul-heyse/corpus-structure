"""Authenticated private source-record envelopes; knowledge publication remains separate."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import BigInteger, Connection, Text, column, func, select, tuple_, values
from sqlalchemy.dialects.postgresql import JSONB

from .metadata import table
from .product_reference import ProductReference
from .record_contracts import validate_anchor_binding
from .types import PreparedRelease

_CELL = re.compile(r"^(#/tables/(?:0|[1-9][0-9]*))/data/table_cells/(0|[1-9][0-9]*)$")


def source_record_address(pointer: str) -> tuple[str, int | None]:
    """Resolve the finite source-record cell address to its native item and cell index."""
    cell = _CELL.fullmatch(pointer)
    return (cell[1], int(cell[2])) if cell else (pointer, None)


def _reference(view):
    return ProductReference(
        view["native_task_id"], view["native_product_key"], view["native_content_digest"]
    )


def _reader_key(view):
    return _reference(view), view["release_id"]


def _source_pin(view, source):
    return dict(
        source=source,
        native_product_task_id=view["native_task_id"],
        product_key=view["native_product_key"],
        product_digest=view["native_content_digest"],
        projection_digest=view["projection_digest"],
        recipe_digest=view["recipe_digest"],
        source_view_id=view["id"],
    )


def _captured_key(reference, pointer, recognition):
    return json.dumps([reference.values(), pointer, recognition], sort_keys=True)


@dataclass(frozen=True)
class _SourceCoordinatesRequest:
    run_id: int
    source_view_id: int
    records: Sequence[Mapping[str, Any]]


class _RecordSourceScope:
    """Invocation-owned selected custody and set-oriented hydration, never a global cache."""

    def __init__(self, conn, prepared, entries):
        from .pdf_record_reader import published_record_reader
        from .published_document import PublishedDocumentBinding
        from .releases import open_release

        self.conn, self.prepared = conn, prepared
        identities = set()
        anchors = []
        for entry in entries:
            identities.add((entry.run_id, entry.source_view_id))
            for record in entry.records:
                for anchor in record["anchors"]:
                    identities.add((entry.run_id, anchor["pin"].get("source_view_id")))
                    anchors.append((entry.run_id, anchor))
        views, selected, runs = (
            table("kb.source_view"),
            table("ops.run_source_view"),
            table("ops.run"),
        )
        self.views = (
            {
                (row["_selected_run"], row["id"]): row
                for row in conn.execute(
                    select(selected.c.run_id.label("_selected_run"), views)
                    .join(views, selected.c.source_view_id == views.c.id)
                    .join(runs, runs.c.id == selected.c.run_id)
                    .where(
                        tuple_(selected.c.run_id, views.c.id).in_(identities),
                        runs.c.release_id == prepared.release_id,
                    )
                ).mappings()
            }
            if identities
            else {}
        )
        if set(self.views) != identities:
            raise ValueError("source pin is absent, unselected or bound to another release")
        readers, pointers, allowed_by_view = {}, {}, {}
        self.projection_pieces = {}
        for identity, view in self.views.items():
            allowed_by_view[identity] = set(view["projection"]["items"]) | set(
                view["projection"].get("ancestors", ())
            )
            for piece in view["projection"]["pieces"]:
                if piece.get("kind") != "native_text":
                    continue
                cell = piece.get("cell_index") if piece.get("source_field") == "cell_text" else None
                if cell is None and piece.get("source_field", "text") not in {"text", "orig"}:
                    continue
                self.projection_pieces.setdefault((*identity, piece["item_ref"], cell), []).append(
                    piece
                )
            key = _reader_key(view)
            if key not in readers:
                readers[key] = published_record_reader(
                    conn, key[0], projection_context=open_release(conn, view["release_id"])
                )
                if readers[key] is None:
                    raise ValueError("private record source lacks a published document placement")
            PublishedDocumentBinding.from_revision(key[0], readers[key].revision).require_placement(
                view
            )
        captured = {}
        for run_id, anchor in anchors:
            view = self.views[(run_id, anchor["pin"]["source_view_id"])]
            pointer, _ = source_record_address(anchor["pointer"])
            if pointer not in allowed_by_view[(run_id, view["id"])]:
                raise ValueError("private record anchor is outside the selected source view")
            key = _reader_key(view)
            pointers.setdefault(key, set()).add(pointer)
            if anchor["space"] == "captured_recognition":
                recognition = anchor["recognition"]
                captured[_captured_key(key[0], pointer, recognition)] = (
                    key[0].task_id,
                    key[0].product_key,
                    key[0].content_digest,
                    pointer,
                    recognition,
                )
        self.native = {
            key: readers[key].selected_native_items(tuple(sorted(chosen)))
            for key, chosen in pointers.items()
        }
        self.captured = {}
        if captured:
            requested = (
                values(
                    column("coordinate_key", Text()),
                    column("task_id", BigInteger()),
                    column("product_key", Text()),
                    column("digest", Text()),
                    column("pointer", Text()),
                    column("recognition", JSONB()),
                )
                .data([(key, *row) for key, row in captured.items()])
                .alias("requested")
            )
            self.captured = dict(
                conn.execute(
                    select(
                        requested.c.coordinate_key,
                        func.ops.record_captured_recognition_text(
                            requested.c.task_id,
                            requested.c.product_key,
                            requested.c.digest,
                            requested.c.pointer,
                            requested.c.recognition,
                        ),
                    )
                ).all()
            )


def _validated_records(prepared, records):
    return tuple(
        prepared.validate_python("SourceRecord", record).model_dump(mode="python")
        for record in records
    )


def authenticated_coordinate_texts(
    conn: Connection,
    prepared: PreparedRelease,
    task: Mapping[str, Any],
    source: str,
    records: Sequence[Mapping[str, Any]],
    *,
    scope: _RecordSourceScope | None = None,
) -> tuple[dict[str, Any], ...]:
    """Private producer wrapper; no accepted standing or invented logical task alias."""
    if task["unit_type"] != "source_view":
        raise ValueError("private records require a source-view task")
    validated = _validated_records(prepared, records)
    if any(record["standing"] == "accepted" for record in validated):
        raise ValueError("private record custody does not admit accepted whole records")
    scope = scope or _RecordSourceScope(
        conn, prepared, (_SourceCoordinatesRequest(task["run_id"], task["unit_id"], validated),)
    )
    view = scope.views[(task["run_id"], task["unit_id"])]
    if source not in {task["unit_key"], view["key"]}:
        raise ValueError("record logical source differs from its task or selected view")
    return _authenticated_source_record_coordinates(
        conn,
        prepared,
        run_id=task["run_id"],
        source_view_id=task["unit_id"],
        source=source,
        records=validated,
        scope=scope,
    )


def authenticated_contribution_coordinate_texts(conn, prepared, task, source, contributions):
    """Same source custody owner for recordless, typed private contributions."""
    if task["unit_type"] != "source_view":
        raise ValueError("private contributions require a source-view task")
    validated = tuple(
        prepared.validate_python("SourceContribution", row).model_dump(mode="python")
        for row in contributions
    )
    scope = _RecordSourceScope(
        conn, prepared, (_SourceCoordinatesRequest(task["run_id"], task["unit_id"], validated),)
    )
    view = scope.views[(task["run_id"], task["unit_id"])]
    if source not in {task["unit_key"], view["key"]}:
        raise ValueError("contribution logical source differs from selected task/view")
    return _authenticated_source_record_coordinates(
        conn,
        prepared,
        run_id=task["run_id"],
        source_view_id=task["unit_id"],
        source=source,
        records=validated,
        scope=scope,
    )


def _authenticated_source_record_coordinates(
    conn, prepared, *, run_id, source_view_id, source, records, scope
):
    if scope.conn is not conn or scope.prepared is not prepared:
        raise ValueError("record source scope belongs to another invocation/release")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source coordinates require their caller-bound logical source")
    view = scope.views[(run_id, source_view_id)]
    expected_pin = _source_pin(view, source)
    if any(record["pin"] != expected_pin for record in records):
        raise ValueError("record pin differs from its exact persisted source view")
    reference = _reference(view)
    anchors = tuple(anchor for record in records for anchor in record["anchors"])
    if any(
        _reference(scope.views[(run_id, anchor["pin"]["source_view_id"])]) != reference
        for anchor in anchors
    ):
        raise ValueError("related selected context requires the same native product")
    contexts = {}
    for anchor in anchors:
        validate_anchor_binding(anchor, expected_pin)
        selected_view = scope.views[(run_id, anchor["pin"]["source_view_id"])]
        selected_pin = dict(
            source=source if selected_view["id"] == view["id"] else selected_view["key"],
            native_product_task_id=selected_view["native_task_id"],
            product_key=selected_view["native_product_key"],
            product_digest=selected_view["native_content_digest"],
            projection_digest=selected_view["projection_digest"],
            recipe_digest=selected_view["recipe_digest"],
            source_view_id=selected_view["id"],
        )
        if anchor["pin"] != selected_pin:
            raise ValueError("private record anchor differs from its persisted source pin")
        pointer, cell = source_record_address(anchor["pointer"])
        node = scope.native[_reader_key(selected_view)][pointer]
        if cell is not None:
            cells = node.get("data", {}).get("table_cells", ())
            if cell >= len(cells):
                raise ValueError("private record cell index is outside its native table")
            node = cells[cell]
        native_text = node.get("text")
        space = anchor["space"]
        if space == "captured_recognition":
            if cell is not None:
                raise ValueError("captured recognition does not support native cell addresses")
            # The same protected native owner is used by direct completion; Python
            # trace output or supplied strings are never admission authority.
            actual = scope.captured[_captured_key(reference, pointer, anchor["recognition"])]
        elif space == "selected_projection":
            actual = selected_view["projection"]["text"]
            if anchor["precision"] == "exact":
                start, end = anchor.get("start"), anchor.get("end")
                if (
                    start is None
                    or end is None
                    or not any(
                        piece.get("kind") == "native_text"
                        and piece.get("item_ref") == pointer
                        and piece["start"] <= start < end <= piece["end"]
                        and (
                            piece.get("source_field") == "cell_text"
                            and piece.get("cell_index") == cell
                            if cell is not None
                            else piece.get("source_field", "text") in {"text", "orig"}
                        )
                        for piece in scope.projection_pieces.get(
                            (run_id, selected_view["id"], pointer, cell), ()
                        )
                    )
                ):
                    raise ValueError(
                        "private projection anchor crosses synthetic or different source pieces"
                    )
        elif space in {"native", "recognized_text"}:
            actual = native_text
        else:
            raise ValueError("model context cannot authenticate source-record evidence")
        if anchor["precision"] == "exact" and not isinstance(actual, str):
            raise ValueError("exact private record anchor has no native text coordinate")
        if (
            anchor["precision"] != "exact"
            and anchor.get("source_piece") is not None
            and (not isinstance(native_text, str) or anchor["source_piece"] not in native_text)
        ):
            raise ValueError("coarse private record spelling is not present in native source text")
        if isinstance(actual, str):
            key = json.dumps(
                [selected_pin, space, anchor["pointer"], anchor.get("recognition")], sort_keys=True
            )
            coordinate = dict(pin=selected_pin, space=space, pointer=anchor["pointer"], text=actual)
            if "recognition" in anchor:
                coordinate["recognition"] = anchor["recognition"]
            contexts[key] = coordinate
    return tuple(contexts.values())
