"""Authenticated private source-record envelopes; knowledge publication remains separate."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Connection, func, select

from .metadata import table
from .product_reference import ProductReference
from .record_contracts import bind_record_candidates
from .types import PreparedRelease

_CELL = re.compile(r"^(#/tables/(?:0|[1-9][0-9]*))/data/table_cells/(0|[1-9][0-9]*)$")


def _address(pointer: str) -> tuple[str, int | None]:
    cell = _CELL.fullmatch(pointer)
    return (cell[1], int(cell[2])) if cell else (pointer, None)


def authenticated_coordinate_texts(
    conn: Connection,
    prepared: PreparedRelease,
    task: Mapping[str, Any],
    source: str,
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Resolve only selected persisted custody, never caller-supplied coordinate text."""
    views, selected = table("kb.source_view"), table("ops.run_source_view")
    if task["unit_type"] != "source_view":
        raise ValueError("private records require a source-view task")
    view = (
        conn.execute(
            select(views)
            .join(selected, selected.c.source_view_id == views.c.id)
            .where(
                views.c.id == task["unit_id"],
                selected.c.run_id == task["run_id"],
            )
        )
        .mappings()
        .one()
    )
    if source not in {task["unit_key"], view["key"]}:
        raise ValueError("record logical source differs from its task or selected view")
    expected_pin = dict(
        source=source,
        native_product_task_id=view["native_task_id"],
        product_key=view["native_product_key"],
        product_digest=view["native_content_digest"],
        projection_digest=view["projection_digest"],
        recipe_digest=view["recipe_digest"],
        source_view_id=view["id"],
    )
    validated = tuple(
        prepared.validate_python("SourceRecord", record).model_dump(mode="python")
        for record in records
    )
    if any(record["standing"] == "accepted" for record in validated):
        raise ValueError("private record custody does not admit accepted whole records")
    if any(record["pin"] != expected_pin for record in validated):
        raise ValueError("private record pin differs from its exact persisted source view")
    from .pdf_record_reader import published_record_reader
    from .published_document import PublishedDocumentBinding
    from .releases import open_release

    reference = ProductReference(
        view["native_task_id"], view["native_product_key"], view["native_content_digest"]
    )
    reader = published_record_reader(
        conn, reference, projection_context=open_release(conn, view["release_id"])
    )
    if reader is None:
        raise ValueError("private record source lacks a published document placement")
    PublishedDocumentBinding.from_revision(reference, reader.revision).require_placement(view)
    anchors = tuple(anchor for record in validated for anchor in record["anchors"])
    pointers = tuple(dict.fromkeys(_address(anchor["pointer"])[0] for anchor in anchors))
    allowed = set(view["projection"]["items"]) | set(view["projection"].get("ancestors", ()))
    if not set(pointers) <= allowed:
        raise ValueError("private record anchor is outside the selected source view")
    native = reader.selected_native_items(pointers) if pointers else {}
    contexts = {}
    for anchor in anchors:
        if anchor["pin"] != expected_pin:
            raise ValueError("private record anchor differs from its persisted source pin")
        pointer, cell = _address(anchor["pointer"])
        node = native[pointer]
        if cell is not None:
            cells = node.get("data", {}).get("table_cells", ())
            if cell >= len(cells):
                raise ValueError("private record cell index is outside its native table")
            node = cells[cell]
        native_text = node.get("text")
        space = anchor["space"]
        if space == "selected_projection":
            actual = view["projection"]["text"]
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
                        for piece in view["projection"]["pieces"]
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
            key = (space, anchor["pointer"])
            contexts[key] = dict(
                pin=expected_pin, space=space, pointer=anchor["pointer"], text=actual
            )
    return tuple(contexts.values())


@dataclass(frozen=True)
class PrivateRecordReport:
    selected_task_id: int
    origin_task_id: int
    release_id: str
    # None preserves predecessor absence; an explicit new empty collection is ().
    records: tuple[BaseModel, ...] | None


def read_private_record_report(reader, task_id: int) -> PrivateRecordReport:
    """Read one completed selected task under the reader's exact run/cut and release."""
    from .contracts import require_bound_operation

    require_bound_operation(reader.prepared, "read_source_view")
    selected, origin, results = (
        table("ops.task"),
        table("ops.task").alias("origin"),
        table("ops.task_result"),
    )
    statement = (
        select(selected.c.id.label("selected_task_id"), origin, results.c.body)
        .select_from(selected)
        .join(origin, origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id))
        .join(results, results.c.task_id == origin.c.id)
        .where(
            selected.c.id == task_id,
            selected.c.run_id == reader.run_id,
            selected.c.release_id == reader.prepared.release_id,
            origin.c.release_id == reader.prepared.release_id,
            selected.c.status.in_(("done", "empty", "reused")),
        )
    )
    if reader.cut_id is not None:
        cut = table("ops.cut_task")
        statement = statement.join(cut, cut.c.task_id == selected.c.id).where(
            cut.c.cut_id == reader.cut_id,
            cut.c.origin_task_id == origin.c.id,
        )
    task = reader.conn.execute(statement).mappings().one()
    envelope = task["body"]
    records = None
    if "records" in envelope:
        # JSON decoding rehydrates tuple fields through the archived generated adapter.
        records_data = tuple(
            reader.prepared.validate_json("SourceRecord", json.dumps(record)).model_dump(
                mode="python"
            )
            for record in envelope["records"]
        )
        contexts = authenticated_coordinate_texts(
            reader.conn, reader.prepared, task, envelope["source"], records_data
        )
        records = bind_record_candidates(
            reader.prepared,
            source=envelope["source"],
            records=records_data,
            coordinate_texts=contexts,
        )
    return PrivateRecordReport(task_id, task["id"], reader.prepared.release_id, records)
