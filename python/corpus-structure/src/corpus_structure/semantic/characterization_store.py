"""Protected immutable characterization publication and pin-native set reads.

Canonical release-typed payloads are authority. Native projection rows are derived in
one transaction with task completion; no inference or publication occurs on reads.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, cast

from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError

from ._operation_ids import RunId, SourceViewId, TaskAttempt, TaskId
from .characterization import (
    EnrichedDocumentView,
    LayerManifest,
    LayerReport,
    _published_layer_manifest,
)
from .identity import canonical_bytes
from .product_reference import ProductReference


def _publish(
    connection: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    layer: LayerReport | None,
    view: EnrichedDocumentView | None,
    cost: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ._operation_calls import publish_characterization as invoke
    from .operations import OperationConflict

    try:
        return cast(
            dict[str, Any],
            invoke(
                connection,
                task_id=TaskId(task_id),
                attempt=TaskAttempt(attempt),
                holder=holder,
                layer=layer.payload if layer else None,
                view=view.payload if view else None,
                cost=json.loads(canonical_bytes(cost)) if cost is not None else None,
            ),
        )
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) == "P0004":
            raise OperationConflict("characterization task attempt lost or run sealed") from exc
        raise


def publish_layer(
    connection: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    layer: LayerReport,
    view: EnrichedDocumentView | None = None,
) -> ProductReference:
    result = _publish(
        connection,
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
        layer=layer,
        view=view,
    )
    return ProductReference(**result["products"]["layer"])


def compose_view(
    connection: Connection, *, task_id: int, attempt: int, holder: str, view: EnrichedDocumentView
) -> ProductReference:
    result = _publish(
        connection,
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
        layer=None,
        view=view,
    )
    return ProductReference(**result["products"]["view"])


def _read[Report: (LayerReport, EnrichedDocumentView)](
    connection: Connection,
    reference: ProductReference,
    kind: str,
    run_id: int | None,
    report_type: type[Report],
    max_bytes: int,
) -> Report:
    from ._operation_calls import read_characterization_product as invoke

    payload = invoke(
        connection,
        task_id=reference.task_id,
        product_key=reference.product_key,
        content_digest=reference.content_digest,
        kind=kind,
        run_id=RunId(run_id) if run_id is not None else None,
        max_bytes=max_bytes,
    )
    report = report_type(canonical_bytes(payload))
    if report.reference(reference.task_id) != reference:
        raise ValueError("characterization payload differs from exact published pin")
    return report


def read_layer(
    connection: Connection,
    reference: ProductReference,
    *,
    run_id: int | None = None,
    max_bytes: int = 67108864,
) -> LayerReport:
    return _read(connection, reference, "layer", run_id, LayerReport, max_bytes)


def read_layer_manifest(
    connection: Connection,
    reference: ProductReference,
    *,
    run_id: int | None = None,
    max_bytes: int = 8388608,
) -> LayerManifest:
    """Read bounded metadata under the exact sealed product's original authority."""
    from ._operation_calls import read_characterization_layer_manifest as invoke

    body = invoke(
        connection,
        task_id=reference.task_id,
        product_key=reference.product_key,
        content_digest=reference.content_digest,
        run_id=RunId(run_id) if run_id is not None else None,
        max_bytes=max_bytes,
    )
    if not isinstance(body, dict):
        raise ValueError("manifest response is not an object")
    if body["reference"] != reference.values() or body["kind"] != "layer":
        raise ValueError("manifest differs from exact published layer pin")
    payload = body["payload"]
    if not isinstance(payload, dict):
        raise ValueError("manifest header is not an object")
    return _published_layer_manifest(reference, payload)


def read_view(
    connection: Connection,
    reference: ProductReference,
    *,
    run_id: int | None = None,
    max_bytes: int = 67108864,
) -> EnrichedDocumentView:
    return _read(connection, reference, "view", run_id, EnrichedDocumentView, max_bytes)


def read_inventory(
    connection: Connection, run_id: int, *, after=None, limit=100, max_bytes=1048576
):
    """Bounded run-selected original pins, including reused products; no latest lookup."""
    from ._operation_calls import read_characterization_inventory

    return cast(
        dict[str, Any],
        read_characterization_inventory(
            connection,
            run_id=RunId(run_id),
            after_task=TaskId(after[0]) if after is not None else None,
            after_key=after[1] if after is not None else None,
            limit=limit,
            max_bytes=max_bytes,
        ),
    )


def read_primary_layers(
    connection,
    run_id,
    source_view_id,
    references,
    *,
    max_bytes=268435456,
    retain: Callable[[ProductReference, LayerReport], LayerReport] | None = None,
):
    """Hydrate complete exact selections in bounded pages under the caller's snapshot."""
    from ._operation_calls import read_primary_characterization

    references = list(dict.fromkeys(references))
    layers = {}

    def read_page(selected):
        try:
            # A refused aggregate must not abort the caller's read transaction.
            with connection.begin_nested():
                page = cast(
                    dict[str, Any],
                    read_primary_characterization(
                        connection,
                        run_id=RunId(run_id),
                        source_view_id=SourceViewId(source_view_id),
                        references=[ref.values() for ref in selected],
                        max_bytes=max_bytes,
                    ),
                )
        except DBAPIError as error:
            if getattr(error.orig, "sqlstate", None) != "54000" or len(selected) < 2:
                raise
            middle = len(selected) // 2
            read_page(selected[:middle])
            read_page(selected[middle:])
            return
        for row in page["layers"]:
            pin = ProductReference(**row["reference"])
            report = LayerReport(canonical_bytes(row["payload"]))
            if report.reference(pin.task_id) != pin:
                raise ValueError("primary product differs from its exact pin")
            layers[pin] = report if retain is None else retain(pin, report)

    # Even an empty selection goes through native authorization and bound checks.
    for start in range(0, max(len(references), 1), 1000):
        read_page(references[start : start + 1000])
    return layers


def read_memberships(
    connection: Connection,
    reference: ProductReference,
    groups: Sequence[str],
    *,
    run_id: int | None = None,
    after: tuple[int, str, str] | None = None,
    layer_key: str | None = None,
    limit: int = 100,
    max_bytes: int = 1048576,
) -> dict[str, Any]:
    """Fetch requested group memberships and their actual occurrence sets in one query."""
    from ._operation_calls import read_characterization_memberships as invoke

    return cast(
        dict[str, Any],
        invoke(
            connection,
            task_id=reference.task_id,
            product_key=reference.product_key,
            content_digest=reference.content_digest,
            groups=list(groups),
            run_id=RunId(run_id) if run_id is not None else None,
            after=list(after) if after is not None else None,
            layer_key=layer_key,
            limit=limit,
            max_bytes=max_bytes,
        ),
    )


def read_nodes(
    connection: Connection,
    reference: ProductReference,
    kind: str,
    *,
    selectors: dict[str, Any] | None = None,
    run_id: int | None = None,
    after: tuple[int, str, str] | None = None,
    limit: int = 100,
    max_bytes: int = 1048576,
) -> dict[str, Any]:
    """Select indexed annotations or terms before hydrating their recorded context."""
    from ._operation_calls import read_characterization_nodes as invoke

    return cast(
        dict[str, Any],
        invoke(
            connection,
            task_id=reference.task_id,
            product_key=reference.product_key,
            content_digest=reference.content_digest,
            kind=kind,
            selectors=selectors or {},
            run_id=RunId(run_id) if run_id is not None else None,
            after=list(after) if after is not None else None,
            limit=limit,
            max_bytes=max_bytes,
        ),
    )
