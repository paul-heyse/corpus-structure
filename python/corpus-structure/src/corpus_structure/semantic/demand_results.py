"""Pinned current result reads and exact detached replay over native demand custody.

The native reader alone acquires authorization, visibility and sorted trust locks.
This owner projects retained selections; it never consults a latest run, schedules
work, copies task identities or changes the producing episode of a reused value.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Generator, Iterator, Mapping
from contextlib import closing, contextmanager, nullcontext, suppress
from dataclasses import dataclass, field
from functools import cached_property
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, cast

from sqlalchemy.exc import DBAPIError

from ._data_operation_wire import WireCutSelection
from .data_operation_identity import body_identity, contextual_product_identity
from .data_operation_json import json_bytes, native_json_loads, wire_json_loads
from .data_operation_model import SubjectContext, validate_replicate_selection
from .data_operation_partitions import (
    PartitionCommitment,
    partition_commitment_header,
    partition_group_digests,
    partition_packet,
)
from .data_operation_values import decode_semantic_value
from .owned_json import FrozenObject, freeze_json, thaw_json
from .refusal_types import ReadLimit
from .selected_graph_budget import SelectedGraphBudgetExceeded

if TYPE_CHECKING:
    from ._data_operation_wire import WireReadDemandResultRequest, WireReadDemandResultResult


def _read_request(value):
    from .data_operation_wire import validate_native_wire

    # This is the explicit public ingress: the captured field correspondence gives
    # demand/read strings their nominal request roles after runtime Draft7 admission.
    return cast(
        "WireReadDemandResultRequest", validate_native_wire("read_demand_result", "input", value)
    )


_PIN_FIELDS = tuple(WireCutSelection.__annotations__)


@contextmanager
def selected_read_snapshot(engine, *, cancellation=None):
    """One snapshot allowing the native read's acquisition and trust-lock custody.

    Read purpose roles and protected native entrypoints own authority. PostgreSQL
    READ ONLY would forbid both the read receipt and its required trust locks.
    """
    with (
        engine.connect().execution_options(
            isolation_level="REPEATABLE READ",
            postgresql_readonly=False,
        ) as connection,
        cancellation.borrow(connection) if cancellation is not None else nullcontext(),
        connection.begin(),
    ):
        yield connection
        if cancellation is not None:
            cancellation.check_active()


@dataclass(frozen=True)
class CutSelection:
    """Exact interpreted selection and native visibility/current trust boundary."""

    content: bytes

    def __post_init__(self):
        record = self.record
        if set(record) != set(_PIN_FIELDS) or any(
            not record[key]
            for key in (
                "demand_id",
                "project_id",
                "release_id",
                "runtime_id",
                "read_id",
                "read_snapshot",
                "frontier_at",
            )
        ):
            raise ValueError("cut selection requires every explicit native interpretation pin")

    @cached_property
    def _record(self):
        from .demand_wire import decode_wire_cut
        from .native_source_view import freeze_native

        return freeze_native(decode_wire_cut(self.content))

    @property
    def record(self) -> dict[str, Any]:
        from .native_source_view import thaw_native

        return thaw_native(self._record)

    @property
    def identity(self) -> str:
        return "cut-selection:" + sha256(self.content).hexdigest()

    @classmethod
    def from_native(cls, page: Mapping[str, Any]) -> CutSelection:
        return cls(json_bytes({key: page[key] for key in _PIN_FIELDS}))


@dataclass(frozen=True)
class DemandResult:
    """A bounded native page with exact retained bytes and an owned live snapshot."""

    content: bytes
    request: bytes = b"{}"
    reader_schema: bytes | None = None
    _native_snapshot: FrozenObject | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_native(cls, native: WireReadDemandResultResult, request: bytes) -> DemandResult:
        """Own the result admitted by the native transport, without schema replay."""
        snapshot = freeze_json(native)
        if type(snapshot) is not FrozenObject:
            raise TypeError("native demand acquisition requires an object")
        page = cls(json_bytes(native), request)
        object.__setattr__(page, "_native_snapshot", snapshot)
        return page

    @cached_property
    def projection_snapshot(self) -> FrozenObject:
        """Reuse live admission; raw detached bytes retain strict generated decoding."""
        if self._native_snapshot is not None:
            return self._native_snapshot
        from .demand_wire import decode_wire_demand_result

        snapshot = freeze_json(decode_wire_demand_result(self.content))
        if type(snapshot) is not FrozenObject:
            raise TypeError("demand projection requires an object")
        return snapshot

    @cached_property
    def _page(self):
        from .data_operation_json import decode_retained_json_object
        from .demand_wire import interpret_demand_record

        parsed, cut_content = decode_retained_json_object(self.content, _PIN_FIELDS)
        interpreted = interpret_demand_record(
            parsed, None if self.reader_schema is None else native_json_loads(self.reader_schema)
        )
        return freeze_json(interpreted), cut_content

    @cached_property
    def _record(self):
        return self._native_snapshot if self._native_snapshot is not None else self._page[0]

    @property
    def record(self) -> dict[str, Any]:
        record = thaw_json(self._record)
        if type(record) is not dict:
            raise TypeError("demand result requires an object")
        return record

    @cached_property
    def cut(self) -> CutSelection:
        # Exact retained member bytes own the cut identity, including ordinary
        # float exponent spelling. Interpretation never rewrites this custody.
        if self._native_snapshot is not None:
            fields = dict(self._native_snapshot.fields)
            return CutSelection(json_bytes({key: thaw_json(fields[key]) for key in _PIN_FIELDS}))
        return CutSelection(self._page[1])

    @property
    def continuation(self) -> dict[str, Any] | None:
        return self.record["continuation"]

    def members(self) -> tuple[dict[str, Any], ...]:
        """Project actual selected packets without opening any other product body."""
        from .demand_query_projection import selected_members
        from .value_codec import decimal_digit_limit

        return selected_members(self.record, decimal_fixed_point_digits=decimal_digit_limit())

    def report(self) -> dict[str, Any]:
        page = self.record
        return dict(
            version="demand-result-v1",
            cut_id=self.cut.identity,
            cut=self.cut.record,
            complete=page["continuation"] is None,
            state=page.get("state", "active"),
            obligations=page["obligations"],
            uses=page["uses"],
            populations=page["populations"],
            original_source_admissions=page.get("original_source_admissions", []),
            attempt_failures=page.get("attempt_failures", []),
            support_page=page.get("support_page"),
            continuation=page["continuation"],
        )


def read_demand_result(
    connection,
    demand_id: str,
    *,
    project_id: str,
    continuation=None,
    cut: CutSelection | None = None,
    limit: int = 100,
    max_bytes: int = 8 * 1024 * 1024,
    view: Literal["frontier", "products", "support"] = "products",
    scope: Mapping[str, Any] | None = None,
    recheck_bodies: bool = False,
) -> DemandResult:
    """Acquire or continue one explicit target, with no default project or run lookup."""
    from .data_operation_storage import DataOperationStorage

    if not demand_id or not project_id:
        raise ValueError("current result reads require explicit demand and project")
    request = dict(continuation or {"demand_id": demand_id})
    if request.get("demand_id") != demand_id:
        raise ValueError("continuation belongs to another demand")
    if continuation is not None and request.get("view") != view:
        raise ValueError("continuation belongs to another result projection")
    if continuation is not None and scope is not None and request.get("scope", {}) != dict(scope):
        raise ValueError("continuation belongs to another examined scope")
    request.update(limit=limit, max_bytes=max_bytes, view=view)
    if recheck_bodies:
        if view != "frontier":
            raise ValueError("body recheck requires its narrow frontier view")
        request["recheck_bodies"] = True
    if continuation is None:
        request["scope"] = dict(scope or {})
    # Generated named transport validates the current Draft7 ingress and exact JSON.
    native = DataOperationStorage(connection).read_demand_result(_read_request(request))
    if native["project_id"] != project_id:
        raise ValueError("demand belongs to another project")
    page = DemandResult._from_native(native, json_bytes(request))
    if cut is not None and page.cut.content != cut.content:
        raise ValueError("continuation differs from the pinned cut selection")
    return page


def acquire_selected_cut(
    connection,
    demand_id: str,
    *,
    project_id: str,
    read_id: str | None = None,
    scope: Mapping[str, Any] | None = None,
    max_bytes: int = 8 * 1024 * 1024,
) -> CutSelection:
    """Acquire or reopen a full selected cut without examining output addresses."""
    from .data_operation_storage import DataOperationStorage

    if not demand_id or not project_id:
        raise ValueError("selected cut requires explicit demand and project")
    request: dict[str, Any] = dict(
        demand_id=demand_id, project_id=project_id, scope=dict(scope or {}), max_bytes=max_bytes
    )
    if read_id is not None:
        request["read_id"] = read_id
    cut = CutSelection.from_native(DataOperationStorage(connection)._acquire_read_context(request))
    record = cut.record
    if record["demand_id"] != demand_id or record["project_id"] != project_id:
        raise ValueError("native selected cut differs from its demand or project")
    if read_id is not None and record["read_id"] != read_id:
        raise ValueError("native selected cut differs from its exact acquisition")
    return cut


def read_selected_answer(
    connection,
    program: Literal[
        "read_selected_outputs",
        "read_selected_partitions",
        "read_selected_derivation_facts",
        "read_selected_proofs",
    ],
    demand_id: str,
    *,
    project_id: str,
    read_id: str | None = None,
    scope: Mapping[str, Any] | None = None,
    after: list | None = None,
    limit: int = 100,
    max_bytes: int = 8 * 1024 * 1024,
    **filters,
) -> dict:
    """Execute a native answer program on a new cut or on its exact continuation."""
    from .data_operation_storage import DataOperationStorage

    if program not in {
        "read_selected_outputs",
        "read_selected_partitions",
        "read_selected_derivation_facts",
        "read_selected_proofs",
    }:
        raise ValueError("unknown native selected answer program")
    if after is not None and read_id is None:
        raise ValueError("a selected answer continuation requires its acquired cut")
    request: dict[str, Any] = dict(
        filters,
        demand_id=demand_id,
        project_id=project_id,
        limit=limit,
        max_bytes=max_bytes,
        scope=dict(scope or {}),
    )
    if read_id is not None:
        request["read_id"] = read_id
    if after is not None:
        request["answer_after"] = after
    try:
        result = DataOperationStorage(connection)._invoke(program, request)
    except DBAPIError as error:
        diagnostic = getattr(error.orig, "diag", None)
        message = "native selected answer exceeds examined address bound"
        if (
            getattr(error.orig, "sqlstate", None) == "P0001"
            and getattr(diagnostic, "message_primary", None) == message
        ):
            raise ReadLimit(message, reason="examined_addresses") from error
        raise
    return require_selected_answer_capacity(result)


def require_selected_answer_capacity(result):
    if result["oversized"] is not None:
        raise ReadLimit(
            f"selected answer row exceeds max_bytes: {result['oversized']!r}", reason="row_bytes"
        )
    return result


def stream_demand_result(
    connection,
    demand_id: str,
    *,
    project_id: str,
    limit=100,
    max_bytes=8 * 1024 * 1024,
    scope: Mapping[str, Any] | None = None,
    read_id: str | None = None,
    expected_cut: str | None = None,
) -> Iterator[DemandResult]:
    """Same-session bounded pages retain the acquisition and its transaction locks."""
    if (read_id is None) != (expected_cut is None):
        raise ValueError("pinned result stream requires both read_id and expected_cut")
    continuation = (
        None
        if read_id is None
        else dict(demand_id=demand_id, read_id=read_id, scope=dict(scope or {}), view="products")
    )
    cut = None
    while True:
        page = read_demand_result(
            connection,
            demand_id,
            project_id=project_id,
            continuation=continuation,
            cut=cut,
            limit=limit,
            max_bytes=max_bytes,
            scope=scope,
        )
        cut = page.cut
        if expected_cut is not None and cut.identity != expected_cut:
            raise ValueError("selected stream differs from its requested cut/trust assessment")
        yield page
        continuation = page.continuation
        if continuation is None:
            break


def read_selected_operation_frontier(
    connection,
    demand_id,
    *,
    project_id,
    scope,
    read_id=None,
    expected_cut=None,
    max_bytes=8388608,
    max_records=100000,
):
    """Read the lightweight operation headers actually included in a response."""
    request = (
        None
        if read_id is None
        else dict(demand_id=demand_id, read_id=read_id, scope=dict(scope), view="frontier")
    )
    cut, retained = None, 0
    identities = {
        "obligations": "obligation_id",
        "uses": "use_id",
    }
    selected = {name: {} for name in identities}
    while True:
        page = read_demand_result(
            connection,
            demand_id,
            project_id=project_id,
            continuation=request,
            cut=cut,
            scope=scope,
            view="frontier",
            limit=100,
            max_bytes=max_bytes,
        )
        cut = page.cut
        if expected_cut is not None and cut.identity != expected_cut:
            raise ValueError("selected resource belongs to another cut/trust assessment")
        native = page.record
        for name, identity in identities.items():
            for row in native.get(name, ()):
                encoded = json_bytes(row)
                previous = selected[name].get(row[identity])
                if previous is not None and previous != encoded:
                    raise ValueError("selected frontier identity changed within its pinned read")
                if previous is None:
                    selected[name][row[identity]] = encoded
                    retained += len(encoded)
        if sum(map(len, selected.values())) > max_records or retained > max_bytes:
            raise SelectedGraphBudgetExceeded(
                "selected frontier exceeds examined capacity", cut=cut
            )
        request = page.continuation
        if request is None:
            break
    frontier = {
        name: [wire_json_loads(value) for _, value in sorted(rows.items())]
        for name, rows in selected.items()
    }
    content = json_bytes(frontier)
    if len(content) > max_bytes:
        raise SelectedGraphBudgetExceeded("selected frontier exceeds examined capacity", cut=cut)
    return cut, frontier


def stream_selected_archive(
    connection,
    cut: CutSelection,
    *,
    max_bytes: int = 8 * 1024 * 1024,
    batch_rows: int = 64,
    consume_populations=None,
) -> Generator[dict[str, Any]]:
    """Stream one transaction-owned native archive selection in bounded batches.

    The native owner computes the closure once and keeps only identity keys.
    Successful exhaustion closes it explicitly. An interrupted transaction owns
    cleanup through rollback or its ON COMMIT DROP temporary relations.
    """
    handle = _open_selected_archive(connection, cut, max_bytes=max_bytes, batch_rows=batch_rows)
    yield from _stream_selected_archive_records(connection, handle)
    if consume_populations is not None:
        consume_populations(handle)
    _close_selected_archive(connection, handle)


def _stream_selected_archive_records(connection, handle):
    from sqlalchemy import Text, bindparam, cast, func, select

    fetch = select(
        cast(func.ops.fetch_selected_archive(bindparam("archive_handle", type_=Text)), Text)
    )
    previous = None
    while True:
        content = connection.scalar(fetch, {"archive_handle": handle})
        if not isinstance(content, str):
            raise ValueError("native archive batch returned malformed JSON")
        batch = native_json_loads(content)
        if (
            not isinstance(batch, dict)
            or not isinstance(batch.get("records"), list)
            or type(batch.get("complete")) is not bool
            or (not batch["records"] and not batch["complete"])
        ):
            raise ValueError("native archive batch has no complete bounded shape")
        for record in batch["records"]:
            key = record.get("key") if isinstance(record, dict) else None
            if not isinstance(key, str) or (previous is not None and key <= previous):
                raise ValueError("native archive record keys did not advance")
            previous = key
            yield dict(record)
        if batch["complete"]:
            break


def _open_selected_archive(
    connection, cut: CutSelection, *, max_bytes: int, batch_rows: int
) -> str:
    from sqlalchemy import BigInteger, Integer, Text, bindparam, cast, func, select
    from sqlalchemy.dialects.postgresql import JSONB

    opened = connection.scalar(
        select(
            cast(
                func.ops.begin_selected_archive(
                    cast(bindparam("archive_cut", type_=Text), JSONB),
                    bindparam("archive_rows", type_=Integer),
                    bindparam("archive_bytes", type_=BigInteger),
                ),
                Text,
            )
        ),
        {
            "archive_cut": json_bytes(cut.record).decode(),
            "archive_rows": batch_rows,
            "archive_bytes": max_bytes,
        },
    )
    if not isinstance(opened, str):
        raise ValueError("native archive acquisition returned malformed JSON")
    acquired = native_json_loads(opened)
    handle = acquired.get("handle") if isinstance(acquired, dict) else None
    if not isinstance(handle, str) or not handle:
        raise ValueError("native archive acquisition omitted its handle")
    return handle


def _close_selected_archive(connection, handle):
    from sqlalchemy import Text, bindparam, func, select

    connection.scalar(
        select(func.ops.close_selected_archive(bindparam("archive_handle", type_=Text))),
        {"archive_handle": handle},
    )


def stream_selected_archive_population(connection, handle, *, items, partition=None):
    """Fetch typed rows from the same authenticated scratch handle without JSON assembly."""
    from sqlalchemy import BigInteger, Boolean, Text, bindparam, func, select

    from .selected_population_archive import KEY_FIELDS, population_fields

    statement = select(
        func.ops.read_selected_archive_population(
            bindparam("handle", type_=Text()),
            bindparam("items", type_=Boolean()),
            bindparam("product", type_=Text()),
            bindparam("collection", type_=Text()),
            bindparam("partition", type_=Text()),
            bindparam("ordinal", type_=BigInteger()),
            bindparam("selected_product", type_=Text()),
            bindparam("selected_collection", type_=Text()),
            bindparam("selected_partition", type_=Text()),
        )
        .table_valued(*population_fields(), "fits")
        .alias("selected_population")
    )
    after = (None, None, None, None)
    product, collection, key = (None, None, None) if partition is None else partition
    while True:
        rows = (
            connection.execute(
                statement,
                dict(
                    handle=handle,
                    items=items,
                    selected_product=product,
                    selected_collection=collection,
                    selected_partition=key,
                    **dict(
                        zip(("product", "collection", "partition", "ordinal"), after, strict=True)
                    ),
                ),
            )
            .mappings()
            .all()
        )
        if not rows:
            break
        for row in rows:
            if row["fits"] is not True:
                raise ValueError("selected archive population row exceeds max_bytes")
            current = (*(row[name] for name in KEY_FIELDS), row["ordinal"])
            if after[0] is not None and current <= after:
                raise ValueError("selected archive population keys did not advance")
            after = current
        yield rows


def stream_selected_support(
    connection,
    page: DemandResult,
    *,
    whole_read: bool = False,
    obligation_id: str | None = None,
    facts_only: bool = False,
) -> Iterator[dict[str, Any]]:
    """Read the page or whole scoped cut closure in bounded native keyset pages."""
    from .data_operation_storage import DataOperationStorage

    cut = page.cut
    request = {
        key: value
        for key, value in cut.record.items()
        if key not in {"project_id", "release_id", "runtime_id"}
    }
    original_request = wire_json_loads(page.request)
    for key in ("after", "limit", "max_bytes", "obligation_id"):
        if key in original_request:
            request[key] = original_request[key]
    request["view"] = "support"
    if facts_only:
        request["support_facts"] = True
    if obligation_id is not None:
        if whole_read or obligation_id not in {
            row["obligation_id"] for row in page.record["obligations"]
        }:
            raise ValueError("selected support obligation is outside its acquired page")
        request["obligation_id"] = obligation_id
        request.pop("after", None)
    if whole_read:
        request["support_scope"] = "read"
        request.pop("after", None)
    while True:
        native = DataOperationStorage(connection).read_demand_result(_read_request(request))
        if CutSelection.from_native(native).content != cut.content:
            raise ValueError("support continuation differs from its selected result")
        support = native["support_page"]
        if not isinstance(support, dict):
            raise ValueError("native support projection is unavailable")
        yield from (dict(record) for record in support["records"])
        if support["complete"]:
            break
        if not support["after"] or support["after"] == request.get("support_after"):
            raise ValueError("native support cursor did not advance")
        request["support_after"] = support["after"]


@contextmanager
def acquired_selected_relations(
    connection,
    demand_id,
    *,
    project_id,
    scope,
    read_id=None,
    expected_cut=None,
    max_bytes=8388608,
    page_rows=100,
    max_total_bytes=64 * 1024**2,
    max_total_records=None,
    capture_frontier=False,
    obligation_ids=None,
    use_ids=None,
    retain_population_items=True,
):
    """Acquire bounded Arrow support in one pinned native cut."""
    from .acquired_selected_relations import LiveSelectedRelations
    from .selected_population_archive import LivePopulationArchive

    if max_total_records is not None and (
        type(max_total_records) is not int or max_total_records < 0
    ):
        raise ValueError("selected record bound must be a nonnegative integer")
    if use_ids is not None and obligation_ids is not None:
        raise ValueError("select uses or obligations, rather than both")
    remaining_uses = None if use_ids is None else set(use_ids)
    if remaining_uses is not None and (
        not remaining_uses
        or any(not isinstance(value, str) or not value for value in remaining_uses)
    ):
        raise ValueError("selected uses require nonempty use identities")
    selected = (None,) if obligation_ids is None else tuple(dict.fromkeys(obligation_ids))
    if not selected or any(
        value is not None and (not isinstance(value, str) or not value) for value in selected
    ):
        raise ValueError("selected record acquisition requires nonempty obligation identities")
    if (obligation_ids is not None or use_ids is not None) and (
        read_id is None or expected_cut is None
    ):
        raise ValueError("selected uses or obligations require an authenticated pinned cut")
    cut = None
    with closing(LiveSelectedRelations()) as index:
        populations = None
        try:
            for obligation_id in selected:
                continuation = (
                    None
                    if read_id is None
                    else dict(
                        demand_id=demand_id, read_id=read_id, scope=dict(scope), view="frontier"
                    )
                )
                if obligation_id is not None:
                    assert continuation is not None
                    continuation["obligation_id"] = obligation_id
                while True:
                    page = read_demand_result(
                        connection,
                        demand_id,
                        project_id=project_id,
                        continuation=continuation,
                        cut=cut,
                        scope=scope,
                        limit=page_rows,
                        max_bytes=max_bytes,
                        view="frontier",
                    )
                    cut = page.cut
                    if expected_cut is not None and cut.identity != expected_cut:
                        raise ValueError(
                            "selected resource belongs to another cut/trust assessment"
                        )
                    selected_page = True
                    support_obligations: tuple[str | None, ...] = (None,)
                    frontier = (
                        page.record if capture_frontier or remaining_uses is not None else None
                    )
                    if remaining_uses is not None:
                        assert frontier is not None
                        uses = [row for row in frontier["uses"] if row["use_id"] in remaining_uses]
                        selected_page = bool(uses)
                        remaining_uses.difference_update(row["use_id"] for row in uses)
                        selected_ids = dict.fromkeys(row["obligation_id"] for row in uses)
                        obligations = frontier["obligations"]
                        support_obligations = (
                            (None,)
                            if selected_ids.keys() == {row["obligation_id"] for row in obligations}
                            else tuple(selected_ids)
                        )
                        frontier["uses"] = uses
                        frontier["obligations"] = [
                            row for row in obligations if row["obligation_id"] in selected_ids
                        ]
                    if capture_frontier and selected_page and frontier is not None:
                        index.append_page(frontier)
                    if max_total_bytes is not None and index.retained_bytes > max_total_bytes:
                        raise SelectedGraphBudgetExceeded(
                            "selected graph examined frontier exceeds byte bound", cut=cut
                        )
                    if max_total_records is not None and index.retained_records > max_total_records:
                        raise SelectedGraphBudgetExceeded(
                            "selected graph examined frontier exceeds record bound", cut=cut
                        )
                    continuation = page.continuation
                    # A selected obligation's support belongs to its exact frontier
                    # page. The full-cut route acquires its whole closure once.
                    if selected_page and (
                        use_ids is not None or obligation_ids is not None or continuation is None
                    ):
                        for support_obligation in support_obligations:
                            whole_read = obligation_ids is None and use_ids is None
                            if whole_read:
                                populations = LivePopulationArchive(
                                    connection, index, cut, max_bytes
                                )
                                index.population_archive = populations
                                stream = _stream_selected_archive_records(
                                    connection, populations._handle()
                                )
                            else:
                                stream = stream_selected_support(
                                    connection,
                                    page,
                                    whole_read=whole_read,
                                    obligation_id=support_obligation,
                                )
                            for record in stream:
                                index.append_record(record, allow_equal=True)
                                if (
                                    max_total_records is not None
                                    and index.retained_records > max_total_records
                                ):
                                    raise SelectedGraphBudgetExceeded(
                                        "selected graph examined closure exceeds record bound",
                                        cut=cut,
                                    )
                                if (
                                    max_total_bytes is not None
                                    and index.retained_bytes > max_total_bytes
                                ):
                                    raise SelectedGraphBudgetExceeded(
                                        "selected graph examined closure exceeds byte bound",
                                        cut=cut,
                                    )
                    if remaining_uses is not None and not remaining_uses:
                        break
                    if continuation is None:
                        if remaining_uses:
                            raise ValueError("selected use is absent from its exact frontier cut")
                        break
                    if obligation_id is not None:
                        continuation = {**continuation, "obligation_id": obligation_id}
            assert cut is not None
            if not retain_population_items:
                if populations is not None:
                    populations.close()
                    populations = None
                index.population_archive = None
            elif populations is None:
                populations = LivePopulationArchive(connection, index, cut, max_bytes)
                index.population_archive = populations
            index.freeze()
            yield cut, index
        except BaseException:
            # An aborted transaction releases its temporary relations on rollback.
            if populations is not None:
                with suppress(DBAPIError):
                    populations.close()
            raise
        else:
            if populations is not None:
                populations.close()


def verify_detached_result(
    record: Mapping[str, Any],
    *,
    records=(),
    index=None,
    wire_schema=None,
    kinds=None,
    definitions=None,
    models=None,
    runtimes=None,
    source_artifacts=None,
    authority_schema=None,
    execution_evidence_schema=None,
    validate_closure=True,
) -> DemandResult:
    """Verify links and exact value identities against an explicit captured closure.

    Export verification authenticates the captured contracts/runtime and trusted
    manifest first. A page alone establishes neither authenticity nor current trust.
    """
    from .data_operation_wire import DRAFT7, validate_native_wire, validate_wire_schema
    from .schema_validation import prepared_schema_validator
    from .selected_population_archive import (
        POPULATION_HEADERS,
        POPULATION_ITEMS,
        verify_population_partition,
    )

    def captured_kind_validator(schema):
        # Captured native kind fragments use the native Draft7 contract even when
        # a primitive fragment omits its optional dialect keyword. Keep the
        # authenticated fragment unchanged; the reader declares its evaluator.
        return prepared_schema_validator(json_bytes({"$schema": DRAFT7, **schema}))

    admitted = (
        validate_native_wire("read_demand_result", "output", dict(record))
        if wire_schema is None
        else validate_wire_schema(wire_schema, dict(record))
    )
    page = DemandResult(
        json_bytes(admitted), reader_schema=None if wire_schema is None else json_bytes(wire_schema)
    )
    closure = {}
    if index is None:
        for row in records:
            relation = row["relation"]
            key = row["key"]
            previous = closure.setdefault(relation, {}).get(key)
            if previous is not None and previous != row["record"]:
                raise ValueError("detached support key has conflicting records")
            closure[relation][key] = row["record"]

    def rows(name):
        return closure.get(name, {}).values() if index is None else index.rows(name)

    def rows_for(name, **fields):
        return (
            (row for row in rows(name) if all(row[key] == value for key, value in fields.items()))
            if index is None
            else index.rows_for(name, **fields)
        )

    def row_map(name, *fields):
        if index is not None:
            return index.mapping(name, fields)
        return {
            (row[fields[0]] if len(fields) == 1 else tuple(row[field] for field in fields)): row
            for row in rows(name)
        }

    actual_kinds = {}
    for value in rows("sem.data_kind_contract"):
        key = value["kind_contract"]
        if key in actual_kinds:
            raise ValueError("detached records repeat a nominal identity")
        if kinds is not None and kinds.get(key) != value:
            raise ValueError("detached kind differs from its captured release contract")
        actual_kinds[key] = value

    def checked_context(context, *, release_id=None, subject_definition=None):
        from .data_operation_model import validate_subject_context

        if models is None:
            if context.original_source is None:
                raise ValueError("nullable subject source requires its captured checked model")
            return
        release = record["release_id"] if release_id is None else release_id
        if release not in models:
            raise ValueError("detached subject scope lacks its captured release model")
        validate_subject_context(models[release], context, subject_definition=subject_definition)

    products = row_map("kb.data_product", "id")
    product_headers = {}
    member_relation = "kb.data_product_member"
    members = row_map(member_relation, "product_id", "member_id")
    partition_relation = "kb.data_product_partition"
    population_archive = None if index is None else getattr(index, "population_archive", None)
    seen_partition_count = 0
    seen_typed_partition_count = 0
    seen_member_count = 0
    for product in rows("kb.data_product") if validate_closure else ():
        if product["id"] in product_headers:
            raise ValueError("detached records repeat a nominal identity")
        kind = actual_kinds[product["kind_contract"]]
        decoded = decode_semantic_value(product["canonical_body"])
        if (
            source_artifacts is not None
            and product["artifact_digest"] is not None
            and product["artifact_digest"] not in source_artifacts
        ):
            raise ValueError("detached selected product artifact bytes are missing")
        captured_kind_validator(kind["meaning_schema"]).validate(product["canonical_body"])
        captured_kind_validator(kind["body_schema"]).validate(decoded)
        packets_by_member = None
        seen_members = set()
        for member in rows_for(member_relation, product_id=product["id"]):
            if packets_by_member is None:
                packets_by_member = defaultdict(list)
                for packet in decoded.get("members", ()) if isinstance(decoded, dict) else ():
                    packets_by_member[packet["member_id"]].append(packet)
            member_id = member["member_id"]
            if member_id in seen_members:
                raise ValueError("detached records repeat a nominal identity")
            seen_members.add(member_id)
            checked_context(
                SubjectContext(
                    product["project_id"],
                    member["subject"],
                    member["original_source"],
                    json_bytes(member["analyzed_scope"]),
                    subject_definition=member["subject_definition"],
                )
            )
            member_kind = actual_kinds[member["kind_contract"]]
            captured_kind_validator(member_kind["meaning_schema"]).validate(member["body"])
            member_body = decode_semantic_value(member["body"])
            captured_kind_validator(member_kind["body_schema"]).validate(member_body)
            context = dict(
                subject=member["subject"],
                subject_definition=member["subject_definition"],
                original_source=member["original_source"],
                analyzed_scope=member["analyzed_scope"],
            )
            if not any(
                packet["kind_contract"] == member["kind_contract"]
                and packet["body"] == member_body
                and packet["context"] == context
                for packet in packets_by_member[member_id]
            ):
                raise ValueError("detached member differs from its canonical container")
        seen_member_count += len(seen_members)
        if kind.get("member_schema", {"not": {}}) != {"not": {}} and any(
            packet["member_id"] not in seen_members for packet in decoded["members"]
        ):
            raise ValueError(
                "detached canonical container member is missing from its support closure"
            )
        collections = kind.get("collections", {})
        declarations = {
            name: declaration
            for name, declaration in collections.get("declarations", {}).items()
            if declaration["unit"] == "partitioned"
        }
        commitments: dict[str, list[PartitionCommitment]] = {name: [] for name in declarations}
        for partition in rows_for(partition_relation, product_id=product["id"]):
            name = partition["collection"]
            if name not in declarations:
                raise ValueError("detached partition has no declared parent collection")
            seen_partition_count += 1
            items = decode_semantic_value(partition["body"])
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise ValueError("detached partition requires an item sequence")
            schemas = collections["schemas"][name]
            item_meaning = captured_kind_validator(schemas["meaning_schema"])
            item_body = captured_kind_validator(schemas["body_schema"])
            for tagged, item in zip(partition["body"][1], items, strict=True):
                item_meaning.validate(tagged)
                item_body.validate(item)
            packet = partition_packet(
                name,
                partition["partition_key"],
                partition["ordinal"],
                partition["placement"]["start"],
                partition["placement"]["end"],
                items,
            )
            if (
                packet["partition_digest"] != partition["partition_digest"]
                or partition["item_count"] != len(items)
                or partition["group_digests"]
                != partition_group_digests(items, declarations[name]["field_groups"])
            ):
                raise ValueError("detached partition differs from its content identity")
            commitments[name].append(
                PartitionCommitment(
                    name,
                    packet["partition_key"],
                    packet["ordinal"],
                    packet["placement"]["start"],
                    packet["placement"]["end"],
                    packet["partition_digest"],
                    len(items),
                )
            )
        if population_archive is not None:
            headers = list(population_archive.rows(POPULATION_HEADERS, product_id=product["id"]))
            for partition in headers:
                name = partition["collection"]
                if name not in declarations:
                    raise ValueError("detached typed population has no declared parent collection")
                seen_typed_partition_count += 1
                schemas = collections["schemas"][name]
                items = population_archive.rows(
                    POPULATION_ITEMS,
                    product_id=product["id"],
                    collection=name,
                    partition_key=partition["partition_key"],
                )
                commitments[name].append(
                    verify_population_partition(
                        partition,
                        items,
                        declarations[name],
                        captured_kind_validator(schemas["meaning_schema"]),
                        captured_kind_validator(schemas["body_schema"]),
                    )
                )
        for name, values in commitments.items():
            if partition_commitment_header(values) != decoded.get(name):
                raise ValueError("detached partition collection differs from its parent header")
        body = body_identity(decoded).key
        context = SubjectContext(
            product["project_id"],
            product["subject"],
            product["original_source"],
            json_bytes(product["analyzed_scope"]),
            subject_definition=product["subject_definition"],
        )
        checked_context(context)
        if (
            body != product["body_digest"]
            or contextual_product_identity(
                kind=product["kind_contract"], context=context, body=body
            ).key
            != product["id"]
        ):
            raise ValueError("detached product differs from its semantic identity")
        product_headers[product["id"]] = {
            "project_id": product["project_id"],
            "kind_contract": product["kind_contract"],
        }
    if validate_closure and seen_partition_count != len(
        row_map(partition_relation, "product_id", "collection", "partition_key")
    ):
        raise ValueError("detached partition has no disclosed parent or repeats an identity")
    if (
        validate_closure
        and population_archive is not None
        and seen_typed_partition_count != population_archive.header_count
    ):
        raise ValueError("detached typed population has no disclosed parent")
    if validate_closure and seen_member_count != len(members):
        raise ValueError("detached member has no disclosed parent")
    actual_definitions = row_map("sem.data_operation_definition", "release_id", "operation_id")
    if definitions is not None:
        from .metadata import table
        from .native_definition_projection import NativeOperationProjection

        # Public rows retain archived operation and parameter declarations.
        # Derived placement facts stay in native custody.
        stored_fields = set(table("sem.data_operation_definition").c.keys())
        exported_fields = stored_fields & {
            "release_id",
            "parameter_definitions",
            *NativeOperationProjection.__required_keys__,
        }
        for key, value in actual_definitions.items():
            expected = definitions.get(key)
            if expected is None or value != {name: expected[name] for name in exported_fields}:
                raise ValueError("detached operation differs from its captured release contract")
    target_definitions = actual_definitions if definitions is None else definitions
    requests = row_map("ops.data_request", "id")
    episodes = row_map("ops.data_derivation", "id")
    if validate_closure:
        # Request placement and its active generation are mutable and deliberately
        # absent from the public projection. Each immutable episode owns the
        # producing release/runtime/recipe used to validate that request's meaning.
        for episode in episodes.values():
            if (
                runtimes is not None
                and (episode["release_id"], episode["runtime_id"]) not in runtimes
            ):
                raise ValueError("detached producing episode lacks its exact runtime archive")
            request = requests[episode["request_id"]]
            definition = actual_definitions[episode["release_id"], request["operation_id"]]
            if episode["recipe"] != request["recipe"] or definition["recipe"] != episode["recipe"]:
                raise ValueError("detached producing recipe differs from captured definition")
            validate_replicate_selection(
                definition["support_contract"]["replicate_policy"],
                request["replicate"],
                owner=request["operation_id"],
            )
            context = SubjectContext(
                request["project_id"],
                request["subject"],
                request["original_source"],
                json_bytes(request["analyzed_scope"]),
                subject_definition=definition["subject_definition"],
            )
            checked_context(
                context,
                release_id=episode["release_id"],
                subject_definition=definition["subject_definition"],
            )
    uses = row_map("ops.demand_use", "id")
    originals = row_map("ops.original_source_admission", "id")
    output_edges = row_map("ops.data_derivation_output", "derivation_id", "role", "position")
    populations = row_map("ops.data_population", "id")
    intents = row_map("ops.data_completion_intent", "id")
    receipts = row_map("ops.data_publication_receipt", "derivation_id")
    from .execution_evidence_leaf import (
        NativeExecutionEvidenceLeaf,
        combine_execution_evidence_leaves,
        validate_execution_evidence_leaf,
    )

    selected_execution_leaves: list[NativeExecutionEvidenceLeaf] = []
    for value in rows("ops.data_execution_evidence_leaf"):
        if validate_closure and (definitions is None or runtimes is None):
            raise ValueError(
                "bounded execution evidence requires captured release/runtime contracts"
            )
        if execution_evidence_schema is not None:
            prepared_schema_validator(json_bytes(execution_evidence_schema)).validate(value)
        leaf = (
            validate_execution_evidence_leaf(
                value,
                products=products,
                requests=requests,
                derivations=episodes,
                receipts={receipt["id"]: receipt for receipt in receipts.values()},
                definitions=actual_definitions,
                runtimes=runtimes,
                outputs=output_edges.values(),
                uses=uses,
            )
            if validate_closure
            else NativeExecutionEvidenceLeaf.model_validate_json(json_bytes(value))
        )
        if leaf.intent_id in intents:
            raise ValueError("bounded execution evidence also discloses its private whole intent")
        selected_execution_leaves.append(leaf)
    execution_leaves = combine_execution_evidence_leaves(selected_execution_leaves)
    supports = row_map("ops.data_derivation_support", "derivation_id", "occurrence")
    original_supports = row_map(
        "ops.data_derivation_original_support", "derivation_id", "occurrence"
    )
    from .authority_leaf import NativeAuthorityLeaf, validate_authority_leaf

    authorities = {}
    for value in rows("ops.data_authority_leaf"):
        leaf = (
            validate_authority_leaf(
                value,
                products=products,
                kinds=kinds,
                definitions=definitions,
                runtimes=runtimes,
                schema=authority_schema,
            )
            if validate_closure
            else NativeAuthorityLeaf.model_validate(value)
        )
        key = (leaf.derivation_id, leaf.use_id)
        if key in authorities and authorities[key] != leaf:
            raise ValueError("detached bounded authority repeats conflicting custody")
        if leaf.derivation_id in episodes or (leaf.use_id is not None and leaf.use_id in uses):
            raise ValueError("detached bounded authority also discloses its hidden episode or use")
        authorities[key] = leaf

    if validate_closure:
        from .declared_structural_admission import validate_structural_report_support

        # A public structural issuer can disclose its one explicitly requested
        # ordinary report edge without disclosing the protected issuer episode.
        # No other support edge may originate outside the acquired episode set.
        for edge in supports.values():
            if edge["derivation_id"] in episodes:
                continue
            matching = tuple(
                leaf
                for (derivation_id, _), leaf in authorities.items()
                if derivation_id == edge["derivation_id"]
            )
            if not matching:
                raise ValueError(
                    "detached support edge lacks its producing episode or structural authority"
                )
            validate_structural_report_support(
                edge,
                leaf=matching[0],
                products=products,
                kinds=actual_kinds,
                uses=uses,
                episodes=episodes,
                outputs=output_edges.values(),
                requests=requests,
                definitions=actual_definitions,
                intents=intents,
                receipts=receipts.values(),
            )

    def authority_reference(reference):
        if reference.get("kind") in {"original-source", "authored"}:
            return None
        use = reference.get("admission_use_id")
        return next(
            (
                leaf
                for (episode, selected), leaf in authorities.items()
                if (episode == reference.get("derivation_id") and (use is None or use == selected))
            ),
            None,
        )

    def required(mapping, key, label):
        value = mapping.get(key)
        if value is None:
            raise ValueError("detached " + label + " is missing from its support closure")
        return value

    def support_reference(reference):
        kind = reference.get("kind", "computation")
        if kind in {"original-source", "authored"}:
            original = required(originals, reference["admission_id"], "original support")
            if original["source_reference"] != reference["source_reference"]:
                raise ValueError("detached original support names another source")
        elif authority_reference(reference) is None:
            episode = required(episodes, reference["derivation_id"], "support episode")
            if reference.get("admission_use_id") is not None:
                selected = required(uses, reference["admission_use_id"], "support use")
                if selected["derivation_id"] != episode["id"]:
                    raise ValueError("detached support use names another producing episode")
        return kind

    def binding_endpoints(binding):
        for selected_input in binding.get("inputs", ()):
            required(product_headers, selected_input["product_id"], "selected input product")
            if selected_input.get("member_id") is not None:
                required(
                    members,
                    (selected_input["product_id"], selected_input["member_id"]),
                    "selected input member",
                )
        for reference in binding.get("support", ()):
            support_reference(reference)
        for reference in binding.get("populations", ()):
            required(populations, reference["population_id"], "selected population")

    if validate_closure:
        from collections import Counter

        for episode in episodes.values():
            request = required(requests, episode["request_id"], "producing request")
            receipt = required(receipts, episode["id"], "publication receipt")
            if episode["intent_id"] in execution_leaves:
                # This native assertion preserves the selected completion facts.
                # Its hidden whole reply cannot be independently replayed here.
                leaf, payload = execution_leaves[episode["intent_id"]]
                if receipt["intent_id"] != leaf.intent_id or leaf.derivation_id != episode["id"]:
                    raise ValueError("bounded execution evidence names another publication")
            else:
                intent = required(intents, episode["intent_id"], "completion intent")
                if receipt["intent_id"] != intent["id"] or any(
                    intent[name] != episode[name]
                    for name in (
                        "request_id",
                        "generation",
                        "runtime_id",
                        "producer_task_id",
                        "producer_attempt",
                    )
                ):
                    raise ValueError(
                        "detached producing episode differs from its completion/publication custody"
                    )
                payload = intent["payload"]
            definition = actual_definitions[episode["release_id"], request["operation_id"]]
            collections = {
                role["name"]: role["collection"] for role in definition.get("input_roles", ())
            }

            def input_signature(row, collections=collections):
                return (
                    row["role"],
                    row["product_id"],
                    row.get("member_id"),
                    row.get("occurrence_label"),
                    row["multiplicity"],
                    row["position"] if collections.get(row["role"]) == "sequence" else None,
                )

            if Counter(map(input_signature, payload["inputs"])) != Counter(
                map(
                    input_signature,
                    rows_for("ops.data_derivation_input", derivation_id=episode["id"]),
                )
            ):
                raise ValueError("detached input roles differ from the sealed completion")
            expected_outputs = set()
            output_products = {}
            for output in payload["outputs"]:
                edge_key = (episode["id"], output["role"], output["position"])
                edge = required(output_edges, edge_key, "producing output edge")
                expected_outputs.add(edge_key)
                produced = output["product"]
                context = SubjectContext(
                    request["project_id"],
                    request["subject"],
                    request["original_source"],
                    json_bytes(request["analyzed_scope"]),
                    subject_definition=definition["subject_definition"],
                )
                checked_context(
                    context,
                    release_id=episode["release_id"],
                    subject_definition=definition["subject_definition"],
                )
                product_key = contextual_product_identity(
                    kind=produced["kind_contract"],
                    context=context,
                    body=body_identity(decode_semantic_value(produced["body"])).key,
                ).key
                if (
                    edge["product_id"] != product_key
                    or edge["member_id"] != output.get("member_id")
                    or edge["multiplicity"] != output["multiplicity"]
                ):
                    raise ValueError("detached output role differs from the sealed completion")
                output_products[(output["role"], output["position"])] = product_key
            actual_outputs = {
                (row["derivation_id"], row["role"], row["position"])
                for row in rows_for("ops.data_derivation_output", derivation_id=episode["id"])
            }
            if actual_outputs != expected_outputs:
                raise ValueError("detached output inventory differs from the sealed completion")
            targets = definition["support_contract"].get("reference_targets")
            if targets:
                from .detached_reference_resolution import require_detached_output_references

                require_detached_output_references(
                    row_map=row_map,
                    rows_for=rows_for,
                    derivation_id=episode["id"],
                    project_id=request["project_id"],
                    targets=targets,
                    input_roles=definition["input_roles"],
                    outputs=payload["outputs"],
                    product_headers=product_headers,
                    population_archive=population_archive,
                    output_products=output_products,
                )
            for occurrence, reference in enumerate(payload["support"]):
                kind = support_reference(reference)
                original = kind in {"original-source", "authored"}
                edge = required(
                    original_supports if original else supports,
                    (episode["id"], occurrence),
                    "producing support edge",
                )
                expected = dict(
                    role=reference.get("role", "support"),
                    position=reference.get("position", occurrence),
                )
                expected.update(
                    {
                        name: reference.get(name)
                        for name in (
                            ("admission_id", "source_reference")
                            if original
                            else ("admission_use_id",)
                        )
                    }
                )
                if "derivation_id" in reference:
                    expected["support_derivation_id"] = reference["derivation_id"]
                if any(edge[name] != value for name, value in expected.items()):
                    raise ValueError("detached support edge differs from the sealed completion")
            if sum(
                1 for _ in rows_for("ops.data_derivation_support", derivation_id=episode["id"])
            ) + sum(
                1
                for _ in rows_for(
                    "ops.data_derivation_original_support", derivation_id=episode["id"]
                )
            ) != len(payload["support"]):
                raise ValueError(
                    "detached support closure inventory differs from the sealed completion"
                )
    if validate_closure and source_artifacts is not None:
        for admission in originals.values():
            reference = admission["reference"]
            if (
                reference.get("kind") == "original-document"
                and reference["content_hash"] not in source_artifacts
            ):
                raise ValueError("detached selected original bytes are missing")
    if validate_closure:
        from .data_operation_identity import SemanticRequestKey

        for retained in uses.values():
            if retained["request_id"] is None:
                continue
            request = requests.get(retained["request_id"])
            if request is None:
                # An unsettled use has no producing episode. Its request is not
                # needed as semantic evidence, and its fate remains explicit.
                if retained["derivation_id"] is not None:
                    raise ValueError("settled use lacks its semantic request")
                binding_endpoints(retained["selection"])
                continue
            if retained["derivation_id"] is not None:
                episode = required(
                    episodes, retained["derivation_id"], "selected producing episode"
                )
                if episode["request_id"] != retained["request_id"]:
                    raise ValueError("detached selected episode names another semantic request")
                definition = actual_definitions[episode["release_id"], request["operation_id"]]
            else:
                # A pending request has semantic selection, not producing custody.
                # Check that meaning against its captured target definition without
                # borrowing a historical generation's execution basis.
                definition = required(
                    target_definitions,
                    (record["release_id"], request["operation_id"]),
                    "pending request target definition",
                )
                validate_replicate_selection(
                    definition["support_contract"]["replicate_policy"],
                    request["replicate"],
                    owner=request["operation_id"],
                )
            context = SubjectContext(
                request["project_id"],
                request["subject"],
                request["original_source"],
                json_bytes(request["analyzed_scope"]),
                subject_definition=definition["subject_definition"],
            )
            binding = retained["selection"]
            binding_endpoints(binding)
            expected = SemanticRequestKey(
                request["recipe"],
                request["subject"],
                decode_semantic_value(binding["request_inputs"]),
                decode_semantic_value(binding["parameters"]),
                binding["inference"],
                subject_context=context,
                execution_scope=(
                    retained["demand_id"]
                    if not definition["support_contract"]["reuse_eligible"]
                    else None
                ),
            ).identity.key
            if expected != request["request_key"]:
                raise ValueError("detached request differs from its exact selected meaning")
    for use in record["uses"]:
        authority = authorities.get((use["derivation_id"], use["use_id"]))
        if use["selection"].get("kind") == "native-authority":
            if (
                authority is None
                or use["selection"]
                != {"kind": "native-authority", "protected_dependencies": "undisclosed"}
                or use["request_id"] is not None
                or use["generation"] is not None
                or use["historical_fate"] != "fulfilled"
                or use["fate"] != ("fulfilled" if authority.standing == "valid" else "unavailable")
                or use["completion_state"] != "success"
                or use.get("rebind_derivation") is not None
                or len(use["products"]) != 1
            ):
                raise ValueError("detached public issuer differs from its native authority leaf")
            product = use["products"][0]
            actual = products.get(authority.product_id)
            definition = target_definitions.get((authority.release_id, authority.issuer_operation))
            declared_roles = () if definition is None else definition["output_roles"]
            if (
                actual is None
                or product["product_id"] != authority.product_id
                or product["kind_contract"] != authority.kind_contract
                or product["member_id"] is not None
                or product["position"] != 0
                or product["multiplicity"] != 1
                or not any(
                    role["name"] == product["role"]
                    and role["kind_contract"] == authority.kind_contract
                    for role in declared_roles
                )
                or any(
                    product[name] != actual[name]
                    for name in (
                        "subject",
                        "subject_definition",
                        "original_source",
                        "analyzed_scope",
                    )
                )
                or ("body" in product and product["body"] != actual["canonical_body"])
            ):
                raise ValueError(
                    "detached public issuer output differs from its authenticated conclusion"
                )
            continue
        if authority is not None:
            raise ValueError("detached public issuer discloses an unauthenticated full binding")
        retained = uses.get(use["use_id"])
        if (
            retained is None
            or retained["demand_id"] != record["demand_id"]
            or any(
                retained[key] != use[key]
                for key in (
                    "obligation_id",
                    "request_id",
                    "derivation_id",
                    "selection",
                    "trust_snapshot",
                )
            )
        ):
            raise ValueError("detached selected use differs from its retained episode binding")
        if use["derivation_id"] is None:
            if use["products"]:
                raise ValueError("detached unsettled use cannot supply produced outputs")
        else:
            required(episodes, use["derivation_id"], "selected producing episode")
        request = requests.get(retained["request_id"])
        if request is not None:
            # Every page keeps target admission separate from original production;
            # transitive support uses above retain their own producing contracts.
            target = target_definitions.get((record["release_id"], request["operation_id"]))
            if target is None or target["recipe"] != request["recipe"]:
                raise ValueError("detached selected recipe is not admitted by its target release")
            definition = (
                actual_definitions[
                    episodes[use["derivation_id"]]["release_id"], request["operation_id"]
                ]
                if use["derivation_id"] is not None
                else target
            )
            validate_replicate_selection(
                target["support_contract"]["replicate_policy"],
                request["replicate"],
                owner=request["operation_id"],
            )
            checked_context(
                SubjectContext(
                    request["project_id"],
                    request["subject"],
                    request["original_source"],
                    json_bytes(request["analyzed_scope"]),
                    subject_definition=definition["subject_definition"],
                ),
                release_id=record["release_id"],
                subject_definition=target["subject_definition"],
            )
        for product in use["products"]:
            edge = required(
                output_edges,
                (use["derivation_id"], product["role"], product["position"]),
                "selected output edge",
            )
            if any(
                edge[name] != product[name] for name in ("product_id", "member_id", "multiplicity")
            ):
                raise ValueError("detached selected output differs from its authentic role edge")
            actual = products.get(product["product_id"])
            if actual is None or (
                "body" in product and actual["canonical_body"] != product["body"]
            ):
                raise ValueError("detached selected body differs from its support closure")
    if validate_closure:
        for population in populations.values():
            evidence = population["evidence"]
            if evidence.get("admission_use_id") is not None:
                selected = required(uses, evidence["admission_use_id"], "population producing use")
                if (
                    selected["derivation_id"] != evidence["derivation_id"]
                    or selected["demand_id"] != population["demand_id"]
                ):
                    raise ValueError("detached population producer differs from its selected use")
            parent = evidence.get("selection", {}).get("parent_population_id")
            if parent is not None:
                required(populations, parent, "parent population")
    from itertools import chain

    for edge in (
        chain(rows("ops.data_derivation_input"), rows("ops.data_derivation_output"))
        if validate_closure
        else ()
    ):
        if (
            edge["derivation_id"] not in episodes
            or edge["product_id"] not in product_headers
            or (
                edge["member_id"] is not None
                and (edge["product_id"], edge["member_id"]) not in members
            )
        ):
            raise ValueError("detached role edge has an absent endpoint")
    for edge in rows("ops.data_derivation_support") if validate_closure else ():
        authority = authority_reference(
            dict(
                kind="computation",
                derivation_id=edge["support_derivation_id"],
                admission_use_id=edge["admission_use_id"],
            )
        )
        # The earlier independent structural check authenticates the sole
        # selectively disclosed report edge originating at a hidden issuer.
        disclosed_issuer = any(
            leaf.derivation_id == edge["derivation_id"] for leaf in authorities.values()
        )
        if (edge["derivation_id"] not in episodes and not disclosed_issuer) or (
            authority is None
            and (
                edge["support_derivation_id"] not in episodes
                or (edge["admission_use_id"] is not None and edge["admission_use_id"] not in uses)
            )
        ):
            raise ValueError("detached support closure is incomplete")
    for edge in rows("ops.data_derivation_original_support") if validate_closure else ():
        if edge["derivation_id"] not in episodes or edge["admission_id"] not in originals:
            raise ValueError("detached original support closure is incomplete")
    return page
