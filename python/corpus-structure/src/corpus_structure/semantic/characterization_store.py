"""Protected immutable characterization publication and pin-native set reads.

Canonical release-typed payloads are authority. Native projection rows are derived in
one transaction with task completion; no inference or publication occurs on reads.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError

from ._operation_ids import RunId, TaskAttempt, TaskId
from .characterization import EnrichedDocumentView, LayerReport
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
    max_bytes: int = 8388608,
) -> LayerReport:
    return _read(connection, reference, "layer", run_id, LayerReport, max_bytes)


def read_view(
    connection: Connection,
    reference: ProductReference,
    *,
    run_id: int | None = None,
    max_bytes: int = 8388608,
) -> EnrichedDocumentView:
    return _read(connection, reference, "view", run_id, EnrichedDocumentView, max_bytes)


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
