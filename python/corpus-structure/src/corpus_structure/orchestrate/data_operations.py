"""Execute admitted native demands without stage-run or method-name policy.

Semantic readiness and effect permission stay with the native bindings. This owner
connects pure Python capabilities to existing fenced task custody and short native
transactions; provider/prepared capabilities use their separately admitted owners.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import copy_context
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any, Literal, cast, overload
from uuid import uuid4

from sqlalchemy import Engine

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import (
    PhysicalRetirementUncertain,
    PreparedWork,
    ReadyFrontier,
    ReadyGroup,
    drive_prepared_work,
)
from corpus_structure.methods.native_host import NativeRetirementUncertain
from corpus_structure.semantic._data_operation_wire import (
    WireAttemptFence,
    WireClaimDataRequestsClaimedResult,
    WireClaimDataRequestsRequest,
    WireCompletion,
    WireRegisterDataExecutionOriginResult,
    WireRetainDataCompletionIntentRequest,
    wire_attempt_fence,
)
from corpus_structure.semantic.claim_lifetime import (
    ClaimFenceLost,
    ClaimSettlementUncertain,
)
from corpus_structure.semantic.completion_drafts import (
    SUPPORTED_OPERATIONS,
    CompletionDraft,
    CompletionDraftStore,
)
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    OwnedByteBudget,
)
from corpus_structure.semantic.data_operation_admission import (
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import ReadyDataRequest
from corpus_structure.semantic.data_operation_json import (
    json_bytes,
    native_json_loads,
    scope_identity,
    wire_json_loads,
)
from corpus_structure.semantic.data_operation_ports import (
    HydratedRoleValue,
    PortRefusal,
    PythonBatchMember,
    resolve_python_port,
)
from corpus_structure.semantic.data_operation_runtime import RuntimeBinding
from corpus_structure.semantic.data_operation_service import (
    DataExecutionBasis,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.identifiers import RuntimeId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
from corpus_structure.semantic.types import PreparedRelease, SourceArtifact, SourceBundle
from corpus_structure.settings import AnalyticsSettings


@dataclass(frozen=True)
class NativeRequestClaim:
    request_id: str
    generation: int
    task_id: int
    attempt: int
    holder: str
    release_id: str
    deadline: datetime
    runtime_id: str = field(kw_only=True)

    @property
    def fence(self) -> WireAttemptFence:
        return wire_attempt_fence(vars(self))


class _BasisExecution:
    """Invocation-local capabilities for one immutable acquired execution basis."""

    def __init__(self, basis):
        self.basis = basis
        self.model = bound_data_operation_model(basis.prepared)
        self.ports, self.consumer_selectors = {}, {}
        self.cpu = None
        self.prepared_schema = False
        self.admitted_operations = set()


@dataclass(frozen=True)
class DemandAdvance:
    """Native snapshot remains authoritative, including incomplete/awaiting fates."""

    demand_id: str
    snapshot: bytes
    receipts: tuple[bytes, ...]
    receipt_count: int
    snapshot_standing: str = "fresh-read"

    @property
    def receipts_truncated(self) -> bool:
        return self.receipt_count > len(self.receipts)


def _check_claim_active(owner, claim):
    from corpus_structure.core.execution_control import check_execution_active

    check_execution_active()
    owner.check_claim(claim)


def _check_batch_active(owner, claims):
    """Keep shared physical work useful without hiding individual claim loss."""
    from corpus_structure.core.execution_control import check_execution_active

    check_execution_active()
    owner()
    failures = []
    for claim in claims:
        try:
            owner.check_claim(claim)
        except (ClaimFenceLost, ClaimSettlementUncertain) as error:
            failures.append(error)
        else:
            return
    if not failures:
        raise ValueError("batch activity requires at least one claim")
    raise ExceptionGroup("no batch member has confirmed active ownership", failures)


class NativeDemandExecutionError(ExceptionGroup):
    """Useful sibling receipts remain available when an execution sweep fails."""

    def __new__(cls, result: DemandAdvance, failures: tuple[Exception, ...]):
        return super().__new__(
            cls,
            f"native demand {result.demand_id} has {len(failures)} execution failures",
            failures,
        )

    def __init__(self, result: DemandAdvance, failures: tuple[Exception, ...]):
        self.result, self.failures = result, failures
        super().__init__(
            f"native demand {result.demand_id} has {len(failures)} execution failures", failures
        )

    @overload
    def derive[E: Exception](self, exceptions: Sequence[E], /) -> ExceptionGroup[E]: ...

    @overload
    def derive[E: BaseException](self, exceptions: Sequence[E], /) -> BaseExceptionGroup[E]: ...

    def derive(self, exceptions: Sequence[BaseException], /) -> BaseExceptionGroup:
        if all(isinstance(error, Exception) for error in exceptions):
            return NativeDemandExecutionError(
                self.result, tuple(error for error in exceptions if isinstance(error, Exception))
            )
        return BaseExceptionGroup(self.message, exceptions)


@dataclass(frozen=True)
class _ExecutionResult:
    receipts: tuple[bytes, ...] = ()
    failures: tuple[Exception, ...] = ()
    deferred: tuple[_ClaimedReady, ...] = ()


@dataclass(frozen=True)
class _RetainedAnswer:
    intent_id: str
    draft: CompletionDraft | None = None


@dataclass(frozen=True)
class _PreparedReady:
    ready: ReadyDataRequest


@dataclass(frozen=True)
class _RecoveryDisposition:
    """The native claim and selected local recovery step share one lifetime."""

    action: Literal["reconcile", "inspect-draft", "compute"]
    native: WireClaimDataRequestsClaimedResult

    @property
    def retained_intent_id(self):
        return self.native.get("retained_intent_id")


@dataclass(frozen=True)
class _ClaimedReady:
    ready: ReadyDataRequest
    claim: NativeRequestClaim
    native: WireClaimDataRequestsClaimedResult


@dataclass
class _ClaimPreparation:
    ready: ReadyDataRequest
    claim: NativeRequestClaim | None = None
    native: WireClaimDataRequestsClaimedResult | None = None
    error: Exception | None = None
    origin: WireRegisterDataExecutionOriginResult | None = None


class _OwnedPythonPool:
    """Bounded retirement of the existing invocation's provider-transport threads."""

    def __init__(self, workers):
        self.pool = ThreadPoolExecutor(max_workers=workers)
        # CPython's worker registry is retained before submit can start a thread.
        self.threads = self.pool._threads
        self.drained = False
        self.closed = False
        self.failed = False
        self._shutdown_done = Event()
        self._shutdown_errors = []

    def __enter__(self):
        return self

    def submit(self, callback):
        if self.failed:
            raise RuntimeError("provider transport executor retains an uncertain submission")
        try:
            return self.pool.submit(callback)
        except BaseException:
            self.failed = True
            raise

    def close(self):
        if self.drained:
            return
        from corpus_structure.semantic.cpu_execution import (
            _COOPERATIVE_CLOSE_SECONDS,
            _WORKER_EXIT_SECONDS,
        )

        deadline = monotonic() + _COOPERATIVE_CLOSE_SECONDS + _WORKER_EXIT_SECONDS

        def stop():
            try:
                self.pool.shutdown(wait=False, cancel_futures=True)
            except BaseException as error:
                self._shutdown_errors.append(error)
            finally:
                self._shutdown_done.set()

        if not self.closed:
            self.closed = True
            Thread(target=stop, name="demand-python-stop", daemon=True).start()
        self._shutdown_done.wait(max(0, deadline - monotonic()))
        for thread in tuple(self.threads):
            thread.join(max(0, deadline - monotonic()))
        self.drained = (
            self._shutdown_done.is_set()
            and not self._shutdown_errors
            and all(not thread.is_alive() for thread in tuple(self.threads))
        )
        if not self.drained:
            raise PhysicalRetirementUncertain(
                "native demand transport threads did not drain; capacity remains owned"
            )

    def __exit__(self, *error):
        self.close()


class _PythonWork:
    def __init__(self, future: Future, release):
        self.future, self.release = future, release
        self.retired = False
        self.drained = False

    def collect(self):
        return self.future.result()

    def cancel(self):
        self.future.cancel()

    def retire(self):
        # The request retains its own shared lease through publication.
        if not self.future.done():
            return False

        def uncertain(error):
            if isinstance(error, BaseExceptionGroup):
                return any(uncertain(child) for child in error.exceptions)
            if isinstance(error, NativeRetirementUncertain):
                return not self.drained
            return isinstance(error, PhysicalRetirementUncertain)

        if not self.future.cancelled() and uncertain(self.future.exception()):
            return False
        if not self.retired:
            self.release()
            self.retired = True
        return True


class _RequestExecution:
    """One request's shared input/transport/reply/draft credit and physical handles."""

    def __init__(self, invocation, reservation):
        self.invocation, self.reservation = invocation, reservation
        self.cpu, self.native_hosts = invocation.cpu, invocation.native_hosts
        self.providers = invocation.providers
        self.engine = invocation.executor.engine
        self.fitter_engine = invocation.executor.fitter_engine
        self.claim: NativeRequestClaim | None = None
        self.claims: tuple[NativeRequestClaim, ...] = ()
        self.handles = []
        self.running = True
        invocation.requests.append(self)
        self.consumer_inputs = {}
        self.consumer_results = {}
        self.binding_rows = {}
        self.hydrated_sizes = {}
        self.hydrated_inputs = None
        self.uncertain_submission = False

    def submit_python(self, callback):
        if getattr(self.invocation.pool, "failed", False):
            raise RuntimeError("provider transport executor is unavailable before submission")
        share = self.reservation.share()
        completed = Event()
        context = copy_context()

        def owned():
            try:
                return callback()
            finally:
                completed.set()

        try:
            work = _PythonWork(
                self.invocation.pool.submit(lambda: context.run(owned)), share.release
            )
        except BaseException:
            # Submit may have accepted work before losing its acknowledgement.
            # No future is not proof that this reservation is free.
            self.uncertain_submission = True
            self.invocation.uncertain_python.append((completed, share))
            raise
        self.invocation.python_work.append(work)
        return work

    def relay(self, plan):
        """Retain exact submitted handles without inventing a second scheduler."""
        value, failure = None, None
        try:
            while True:
                try:
                    work = plan.throw(failure) if failure is not None else plan.send(value)
                except StopIteration as result:
                    return result.value
                if not isinstance(work, ReadyGroup) and (
                    not isinstance(work, tuple)
                    or not all(isinstance(item, PreparedWork) for item in work)
                ):
                    raise TypeError("prepared capability must yield declared physical work")

                def capture(item):
                    def submit():
                        from corpus_structure.cli.observation_logging import bound

                        claims = self.claims or ((self.claim,) if self.claim is not None else ())
                        bindings: dict[str, Any] = {
                            "demand_id": getattr(self.invocation.executor, "demand", None)
                        }
                        if len(claims) == 1:
                            claim = claims[0]
                            bindings.update(
                                dict(
                                    claim.fence,
                                    runtime_id=claim.runtime_id,
                                    release_id=claim.release_id,
                                )
                            )
                        elif claims:
                            bindings.update(
                                request_id=None,
                                task_id=None,
                                attempt=None,
                                logical_requests=[dict(claim.fence) for claim in claims],
                            )
                        with bound(**bindings):
                            handle = item.try_submit()
                        if handle is not None:
                            self.handles.append(handle)
                        return handle

                    return PreparedWork(submit, item.abandon)

                try:
                    value = yield (
                        ReadyGroup(
                            tuple(self.relay(child) for child in work.plans),
                            max_active=work.max_active,
                        )
                        if isinstance(work, ReadyGroup)
                        else tuple(capture(item) for item in work)
                    )
                    failure = None
                except BaseException as error:
                    value, failure = None, error
        finally:
            plan.close()

    def release_retired_inputs(self):
        """Drop decoded bodies only after reduction and physical retirement."""
        if self.running or not self.retired():
            return False
        self.hydrated_inputs = None
        self.consumer_inputs.clear()
        self.consumer_results.clear()
        self.binding_rows.clear()
        self.hydrated_sizes.clear()
        return True

    def retired(self):
        if self.uncertain_submission and not self.invocation.physical_retired:
            return False
        return all([handle.retire() for handle in self.handles]) and self.cpu.reservation_retired(
            self.reservation
        )


class _RunExecution:
    def __init__(self, executor, host):
        self.host = host
        resources = host.resources
        self.pool, self.python_work = resources.pool, []
        self.uncertain_python = []
        self.pending_failures = []
        self.requests = []
        # Stage-A credit exists before a frontier child starts and constructs
        # its _RequestExecution. It already borrows the prepared generation.
        self.pending_reservations = set()
        self.physical_retired = False
        self.cpu = resources.cpu
        self.native_hosts = resources.native_hosts
        self.providers = resources.providers
        self.executor = executor
        self._selected_operations = None
        self._target_ports = None
        self._prepared_residents = set()

    def __enter__(self):
        self.executor._preparation_bytes = 0
        for context in self.executor._contexts.values():
            context.cpu, context.prepared_schema = None, False
            context.admitted_operations.clear()
        self.host._execution = self
        return self

    def declare_operations(self, operations, context):
        """Declare frozen native profiles before the shared host starts serving."""
        from corpus_structure.methods.native_profiles import shared_host_environment
        from corpus_structure.methods.pm2_worker import preflight_pm2_residents
        from corpus_structure.semantic.data_operation_prepared_products import (
            PreparedProductDiagnostic,
            PreparedProductRefusal,
        )

        ports = []
        residents = []
        for operation in operations:
            selected = context.model.operation(operation)
            if (
                operation in self.executor.capability_factories
                or selected.capabilities.prepared_factory is not None
            ):
                port = self.executor._port(operation, context)
                ports.append(port)
                residents.extend((operation, selection) for selection in port.native_selections)
        if not residents:
            return tuple(ports)
        population = {}
        for operation, selection in residents:
            population.setdefault(selection.identity, (operation, selection))
        pending = [
            (operation, selection)
            for key, (operation, selection) in population.items()
            if key not in self._prepared_residents
        ]
        providers = tuple(dict.fromkeys(selection.provider for _, selection in pending))
        try:
            project, python, script = shared_host_environment(
                selection for _, selection in residents
            )
            observation = (
                preflight_pm2_residents(
                    python=python, script=script, project=project, providers=providers
                )
                if pending
                else {}
            )
        except ValueError as error:
            raise PreparedProductRefusal(
                str(error),
                PreparedProductDiagnostic(
                    ", ".join(dict.fromkeys(selection.provider for _, selection in residents)),
                    None,
                    None,
                    "shared-host-environment",
                ),
            ) from error
        for operation, selection in pending:
            expected = selection.native.runtime_identity
            if observation != expected:
                changed = tuple(
                    key
                    for key in sorted(expected.keys() | observation.keys())
                    if expected.get(key) != observation.get(key)
                )
                field = changed[0]
                raise PreparedProductRefusal(
                    f"{operation}: {selection.provider} shared host runtime changed in "
                    f"{', '.join(changed)}; reacquire the selected release runtime",
                    PreparedProductDiagnostic(
                        f"{selection.provider}.{field}",
                        str(expected.get(field)),
                        str(observation.get(field)),
                        "shared-host-runtime",
                    ),
                )
            selection.declaration()
        self.native_hosts.declare(selection for _, selection in population.values())
        self._prepared_residents.update(population)
        return tuple(ports)

    def prepare_target_hosts(self, operations):
        ports = self._target_ports
        if ports is None:
            ports = self.declare_operations(
                self._selected_operations or operations, self.executor._target_context
            )
            self._target_ports = ports
        return ports

    def freeze_target_operations(self, operations):
        """Keep one frozen target closure without acquiring its capabilities."""
        selected = tuple(sorted(operations))
        if self._selected_operations is not None and selected != self._selected_operations:
            raise PortRefusal("native demand changed its frozen operation closure")
        self._selected_operations = selected

    def select_operations(self, operations, context=None):
        """Prepare the attached basis closure before admitting physical request work."""
        if context is None:
            self.freeze_target_operations(operations)
            context = self.executor._target_context
        target_ports = self.prepare_target_hosts(operations)
        ports = (
            target_ports
            if context is self.executor._target_context
            else self.declare_operations(operations, context)
        )
        self.host.ensure_request_room(self.executor.reservation)
        for port in ports:
            if getattr(port, "requires_prepared_schema", False) and not context.prepared_schema:
                context.cpu = self.host.cpu_for_release(
                    context.basis.prepared, self.executor.reservation
                )
                context.prepared_schema = True
        if context.cpu is None:
            context.cpu = self.cpu
        self.cpu.prepare()
        self.executor._preparation_bytes = self.cpu.preparation_bytes
        if (
            self.executor.policy.max_owned_bytes - self.executor._preparation_bytes
            < self.executor.reservation
        ):
            raise CapacityExceeded(
                "native preparation and one complete request exceed owned capacity"
            )

    def has_live_requests(self):
        self.requests[:] = [
            request for request in self.requests if not request.release_retired_inputs()
        ]
        return bool(self.requests or self.pending_reservations)

    def _release_retired_claims(self):
        owner = getattr(self.executor, "_claim_owner", None)
        if owner is None:
            return
        with owner.lock:
            claims = tuple(
                claim
                for key, claim in owner.active.items()
                if key not in owner.uncertain and key not in owner.lost
            )
        for claim in claims:
            failure = RuntimeError("execution run ended before native settlement")
            self.executor._known_failure(claim, owner, failure, phase="run retirement")
            self.executor._member_failures.append(failure)

    def __exit__(self, *error):
        try:
            return self._finish_run(*error)
        finally:
            self.host._execution = None

    def _discard_retired_bodies(self):
        # Direct callers may retain this executor after run(). Futures and request
        # caches must not keep encoded replies/inputs after their credits retire.
        self.python_work.clear()
        self.uncertain_python.clear()
        self.pending_failures.clear()
        self.requests.clear()
        self.cpu = None

    def _finish_run(self, *error):
        healthy = (
            not self.uncertain_python
            and not self.pending_failures
            and not self.pool.failed
            and not self.cpu._submission_uncertain
            and not self.cpu._admissions
            and not self.cpu._stream_transports
            and self.providers.retire()
            and not any(
                lane.closed or lane.broken is not None for lane in self.providers._lanes.values()
            )
            and all(work.retire() for work in self.python_work)
            and all(request.retired() for request in self.requests)
        )
        if healthy:
            self.physical_retired = True
            self._release_retired_claims()
            self._discard_retired_bodies()
            try:
                self.native_hosts.finish_run(self.executor.policy.native_keep_warm_seconds)
            except BaseException as failure:
                self.host._quarantine = failure
                raise
            return
        failures = []
        try:
            # Submitted cancellation is not retirement. Existing bounded native
            # close/kill/join must complete before its charges or attempts retire.
            self.host.retire_resources()
        except BaseException as failure:
            failures.append(failure)
        native_drained = self.native_hosts.physical_drained
        providers_drained = self.providers.retire()
        if (
            self.pool.drained
            and native_drained
            and providers_drained
            and self.cpu._physical_retired
        ):
            for _, share in self.uncertain_python:
                share.release()
        else:
            self.executor._quarantined = True
        if native_drained and self.pool.drained:
            for work in self.python_work:
                work.drained = True
                work.retire()
                # A worker unwinding after host teardown can finish after this
                # scope exits; its still-owned share retires on actual completion.
                work.future.add_done_callback(lambda _, work=work: work.retire())
        self.physical_retired = (
            native_drained
            and providers_drained
            and self.pool.drained
            and self.cpu._physical_retired
        )
        if self.physical_retired:
            for physical, claim, owner, error, phase in self.pending_failures:
                if physical.retired():
                    try:
                        self.executor._known_failure(claim, owner, error, phase=phase)
                    except Exception as failure:
                        failures.append(failure)
                else:
                    self.executor._quarantined = True
                    failures.append(
                        PhysicalRetirementUncertain(
                            "deferred native attempt still has unretired physical work"
                        )
                    )
        if self.physical_retired:
            self._release_retired_claims()
            self._discard_retired_bodies()
        if failures:
            raise BaseExceptionGroup("native demand physical cleanup failed", failures)


def _database_capacity(engine: Engine, declared: int | None) -> int:
    """Use the owning physical pool or an explicit caller-owned reservation."""
    store = getattr(engine, "_corpus_store", None)
    if store is not None:
        actual = store.pool.max_size
        if declared is not None and (type(declared) is not int or declared > actual):
            raise ValueError("declared database capacity exceeds the owned physical pool")
        capacity = actual if declared is None else declared
    else:
        if declared is None:
            raise ValueError("unmanaged engine requires explicit database_capacity")
        capacity = declared
    if type(capacity) is not int or capacity < 3:
        raise ValueError("database capacity must cover renewal, driver and one port worker")
    return capacity


class NativeDemandExecutor:
    """One invocation's native claims, CPU capacity and exact settlement owner."""

    def __init__(
        self,
        engine: Engine,
        prepared: PreparedRelease,
        runtime: RuntimeBinding,
        sources: PythonSourceCollection,
        *,
        policy: CharacterizationExecutionPolicy | None = None,
        runtime_locations: Mapping[str, Path] | None = None,
        capability_factories: Mapping[str, Callable[..., Any]] | None = None,
        admission_engine: Engine | None = None,
        fitter_engine: Engine | None = None,
        schema: SourceBundle | None = None,
        declarations: tuple[SourceArtifact, ...] | None = None,
        captured_contracts: tuple[SourceArtifact, ...] = (),
        nemotron_endpoint: str | None = None,
        database_capacity: int | None = None,
        source_root: Path | None = None,
        execution_host=None,
        host_run=None,
        execution_basis=None,
        native_io=None,
        completion_drafts: CompletionDraftStore | None = None,
        analytics_settings: AnalyticsSettings | None = None,
    ):
        if runtime.release_id != prepared.release_id:
            raise ValueError("runtime belongs to another release")
        self.engine, self.prepared, self.runtime, self.sources = engine, prepared, runtime, sources
        self.fitter_engine = fitter_engine
        self.admission_engine = engine if admission_engine is None else admission_engine
        from .native_demand_io import NativeDemandIO

        self.native_io = native_io or NativeDemandIO(engine, self.admission_engine)
        basis = execution_basis or DataExecutionBasis(
            prepared, runtime, sources, schema, declarations, captured_contracts, runtime_locations
        )
        self._host, self._host_run = execution_host, host_run
        self._target_context = (
            execution_host.context(basis) if execution_host is not None else _BasisExecution(basis)
        )
        self._contexts = {basis.key: self._target_context}
        from corpus_structure.analytics import configured

        self.analytics_settings = configured() if analytics_settings is None else analytics_settings
        self.source_root = source_root
        self.completion_drafts = completion_drafts
        self._draft_origins = {}
        self.model = self._target_context.model
        self.runtime_locations = runtime_locations
        self.schema = schema
        self.declarations = declarations
        self.captured_contracts = captured_contracts
        self.nemotron_endpoint = nemotron_endpoint
        self.capability_factories = dict(capability_factories or {})
        for operation in self.capability_factories:
            if self.model.operation(operation).capabilities.preparation == "none":
                raise PortRefusal("prepared capability supplied for an unprepared operation")
        self.policy = policy or CharacterizationExecutionPolicy()
        self.database_capacity = _database_capacity(engine, database_capacity)
        # Renewal is established before work starts; the driver remains able to
        # plan/settle while bounded port workers borrow through the same owner.
        self.port_workers = min(self.policy.max_provider_jobs, self.database_capacity - 2)
        if self.port_workers < 1:
            raise ValueError("native demand needs capacity for renewal, driver and one port worker")
        # Parent input + encoded child packet, retained reply + decoded output +
        # publication draft. One transferable charge covers all physical owners.
        self.reservation = 2 * self.policy.max_packet_bytes + 3 * self.policy.max_reply_bytes
        if self.reservation > self.policy.max_owned_bytes:
            raise ValueError("native input, reply and publication draft exceed owned capacity")
        self.budget = OwnedByteBudget(self.policy.max_owned_bytes)
        self._preparation_bytes = 0
        self._invocation = Lock()
        self._quarantined = False
        self._failed_requests = set()
        self.ports = self._target_context.ports
        self.consumer_selectors = self._target_context.consumer_selectors
        self.holder = "demand-owner:" + uuid4().hex

    def _port(self, operation, context=None):
        context = self._target_context if context is None else context
        basis = context.basis
        created = operation not in context.ports
        if created:
            selected = context.model.operation(operation)
            if selected.effects and selected.capabilities.prepared_factory is None:
                raise PortRefusal("effectful operation requires its captured native effect owner")
            if selected.capabilities.preparation != "none":
                from corpus_structure.semantic.data_operation_consumers import (
                    resolve_prepared_factory,
                )

                prepared_sources = basis.prepared_sources
                factory = (
                    resolve_prepared_factory(context.model, prepared_sources, operation)
                    if selected.capabilities.prepared_factory is not None
                    else self.capability_factories.get(operation)
                )
                if factory is None:
                    raise PortRefusal("declared prepared capability is not acquired")
                admission = self.native_io.acquire_execution(basis, operation, prepared=True)
                try:
                    port = factory(
                        basis.prepared,
                        context.model,
                        operation,
                        identity=admission.identity,
                        authorize=admission.authorize,
                        custody=admission.custody,
                        sources=prepared_sources,
                    )
                except ValueError as error:
                    from corpus_structure.cli.observation_logging import logger
                    from corpus_structure.semantic.data_operation_prepared_products import (
                        PreparedProductRefusal,
                    )

                    detail = error.diagnostic if isinstance(error, PreparedProductRefusal) else None
                    logger(__name__).error(
                        "native_demand.prepared_acquisition_refused",
                        operation=operation,
                        resource=detail.resource if detail else None,
                        expected=detail.expected if detail else None,
                        actual=detail.actual if detail else None,
                        prerequisite=detail.prerequisite if detail else "prepared_operation",
                    )
                    raise
                if selected.effects:
                    from corpus_structure.semantic.data_operation_effects import (
                        CapturedEffectPort,
                    )

                    if not isinstance(port, CapturedEffectPort):
                        raise PortRefusal("declared effect has no captured native effect owner")
                admission.authorize(port.identity)
                if port.operation != selected:
                    raise PortRefusal("prepared capability differs from effective operation")
                context.ports[operation] = port
                if selected.consumer_selection is not None:
                    from corpus_structure.semantic.data_operation_consumers import (
                        resolve_consumer_selection,
                    )

                    context.consumer_selectors[operation] = resolve_consumer_selection(
                        context.model,
                        prepared_sources,
                        operation,
                        port.consumer_receiver,
                        authorize=lambda admission=admission, port=port: admission.authorize(
                            port.identity
                        ),
                    )
            else:
                admission = self.native_io.acquire_execution(basis, operation)
                context.ports[operation] = resolve_python_port(
                    context.model,
                    basis.sources,
                    operation,
                    authorize=admission.authorize,
                    runtime_locations=basis.runtime_locations,
                    schema=basis.schema,
                    prepared=basis.prepared,
                    declarations=basis.declarations,
                    captured_contracts=basis.captured_contracts,
                )
                if selected.consumer_selection is not None:
                    from corpus_structure.semantic.data_operation_consumers import (
                        resolve_consumer_selection,
                    )

                    port = context.ports[operation]
                    context.consumer_selectors[operation] = resolve_consumer_selection(
                        context.model,
                        basis.sources,
                        operation,
                        port.consumer_receiver,
                        authorize=lambda admission=admission, port=port: admission.authorize(
                            port.identity
                        ),
                    )
        if created:
            context.admitted_operations.add(operation)
        elif operation not in context.admitted_operations:
            self.native_io.recheck_execution(basis, context.ports[operation].identity)
            context.admitted_operations.add(operation)
        return context.ports[operation]

    def _basis_context(self, release_id, runtime_id):
        if not runtime_id:
            raise PortRefusal("native execution metadata lacks its authenticated runtime basis")
        key = release_id, runtime_id
        if key not in self._contexts:
            host = self._host
            if host is None:
                raise RuntimeError("execution basis acquisition requires its active process host")
            basis = self.native_io.acquire_basis(
                host, *key, source_root=self.source_root, token=self._host_run
            )
            self._contexts[key] = host.context(basis)
            context = self._contexts[key]
            context.admitted_operations.clear()
            context.cpu, context.prepared_schema = None, False
        return self._contexts[key]

    def _execution_context(self, claim):
        return self._basis_context(claim.release_id, claim.runtime_id)

    def _ready_context(self, ready):
        native = wire_json_loads(ready.native)
        return self._basis_context(native["release_id"], native["runtime_id"])

    def _generation_ready(self, ready, request_id, claimed, context, authorization):
        """Reconstruct only the generation's original frozen native read, never latest."""
        from corpus_structure.semantic._data_operation_wire import WireReadDemandResultRequest

        binding = claimed["binding"]
        with self.native_io.transaction() as connection:
            storage = connection.calls
            request = {
                "demand_id": claimed["binding_demand_id"],
                "read_id": binding["read_id"],
                "limit": 1,
                "obligation_id": claimed["binding_obligation_id"],
            }
            snapshot = storage.read_demand_result(cast(WireReadDemandResultRequest, request))
            obligations = snapshot["obligations"]
            if (
                len(obligations) != 1
                or obligations[0]["obligation_id"] != claimed["binding_obligation_id"]
            ):
                raise PortRefusal("claimed generation lacks its original pinned obligation")
            binding_snapshot = {**snapshot, "obligations": obligations}
            candidates = tuple(
                connection.planner(context.model).bound_requests(
                    binding_snapshot, authorization=authorization, retained=True
                )
            )
        if (
            len(candidates) != 1
            or candidates[0].request_id != request_id
            or semantic_value(wire_json_loads(candidates[0].binding)) != semantic_value(binding)
        ):
            raise PortRefusal("claimed generation differs from its original frozen binding")
        bound = candidates[0]
        original = ReadyDataRequest(
            obligation=ready.obligation,
            operation=bound.operation,
            subject=bound.subject,
            request=bound.request,
            admission=bound.admission,
            native=ready.native,
            binding=bound.binding,
            resolved=bound.resolved,
            binding_result=bound.binding_result,
        )
        return original, (bound.operation,)

    def _prepare_ready(self, ready, authorization):
        native = wire_json_loads(ready.native)
        if native["action"] == "reconcile":
            return ready
        context = self._ready_context(ready)
        if (
            native["release_id"] == self.prepared.release_id
            and native["runtime_id"] == self.runtime.runtime_id
            and native["binding_obligation_id"] == ready.obligation
            and semantic_value(native["binding"]) == semantic_value(wire_json_loads(ready.binding))
        ):
            # Native attachment has already validated this exact same-read
            # binding. Preserve its typed roles instead of rebuilding SQL/ASTs.
            original = ready
        else:
            original, _ = self._generation_ready(
                ready, native["request_id"], native, context, authorization
            )
        return original

    def _hydrate(self, ready: ReadyDataRequest, execution_owner=None, *, context=None):
        context = self._target_context if context is None else context
        from corpus_structure.semantic.data_operation_consumers import (
            BoundConsumerSelection,
        )

        pins = wire_json_loads(ready.resolved.trust_evidence)
        with self.native_io.transaction() as connection:
            selected = connection.hydrate(
                context.model,
                BoundConsumerSelection.from_binding(
                    ready.binding_result, operation=ready.operation
                ),
                demand_id=pins.get("demand_id", self.demand),
                read_id=pins["read_id"],
                trust_snapshot=pins["trust"],
                max_bytes=self.policy.max_packet_bytes,
            )
        if context.model.operation(ready.operation).consumer_selection is not None:
            result = context.consumer_selectors[ready.operation].select_hydrated(selected)
            if execution_owner is not None:
                execution_owner.consumer_results[ready.obligation] = result
        if execution_owner is not None:
            execution_owner.hydrated_sizes[ready.obligation] = selected.measured_bytes
            execution_owner.consumer_inputs[ready.obligation] = selected
            execution_owner.binding_rows[ready.obligation] = {
                role: tuple(
                    {
                        "product": value.member.product,
                        "member": value.member.member,
                        "kind_contract": value.member.kind_contract,
                        "project_id": ready.resolved.subject_context.project_id,
                        "subject": value.member.subject,
                        "subject_definition": value.member.subject_definition,
                        "original_source": value.member.original_source,
                        "analyzed_scope": scope_identity(
                            native_json_loads(value.member.analyzed_scope)
                        ),
                        "body": value.value(),
                    }
                    for value in values
                )
                for role, values in selected.values
            }
        roles = {role.name: role for role in context.model.operation(ready.operation).roles}
        identities = {(value.owner, value.domain): value.key for value in context.model.identities}
        values = []
        retained_roles = {role.role: role for role in ready.binding_result.roles}
        for role, members in selected.values:
            if retained_roles[role].state == "known-absent":
                continue
            decoded = tuple(member.value() for member in members)
            if roles[role].collection == "scalar":
                if (
                    not decoded
                    and retained_roles[role].state == "present"
                    and roles[role].minimum == 0
                    and roles[role].presence == "optional"
                ):
                    continue
                if len(decoded) != 1:
                    raise PortRefusal(
                        "scalar input requires one admitted member: "
                        f"{ready.operation}/{role} has {len(decoded)}"
                    )
                value = decoded[0]
            else:
                value = decoded
            values.append(HydratedRoleValue(role, identities[roles[role].kind, "kind"], value))
        return tuple(values)

    def _retain_answer(self, ready, claim, answer, port, owner, *, physical=None):
        context = self._execution_context(claim)
        if answer.operation != ready.operation:
            raise PortRefusal("completion belongs to another operation")
        operation = context.model.operation(ready.operation)
        if operation.output_witnesses:
            from corpus_structure.semantic.data_operation_output_witnesses import (
                validate_output_witnesses,
            )

            if physical is None or ready.obligation not in physical.binding_rows:
                raise PortRefusal(
                    "output witnesses require their authenticated selected input rows"
                )
            bodies = {}
            for value in answer.outputs:
                if value.meaning is None:
                    raise PortRefusal("output witnesses require canonical typed output meaning")
                bodies.setdefault(value.role, []).append(
                    decode_semantic_value(wire_json_loads(value.meaning))
                )
            validate_output_witnesses(operation, bodies, physical.binding_rows[ready.obligation])
        output_bytes = sum(
            len(value.content) + len(value.meaning or b"") + sum(map(len, value.members))
            for value in answer.outputs
        )
        if output_bytes > self.policy.max_reply_bytes:
            raise ValueError(
                f"Completion outputs use {output_bytes} bytes, exceeding the "
                f"{self.policy.max_reply_bytes}-byte reply limit"
            )
        if answer.outcome not in context.model.operation(ready.operation).outcomes:
            raise PortRefusal("completion outcome is outside the declared operation")
        outputs = []
        positions = {}
        for value in answer.outputs:
            position = positions.get(value.role, 0)
            positions[value.role] = position + 1
            if value.meaning is None:
                raise PortRefusal("native output requires canonical typed meaning")
            outputs.append(
                {
                    "role": value.role,
                    "position": position,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": value.kind_contract,
                        "body": json.loads(value.meaning),
                        "members": [wire_json_loads(member) for member in value.members],
                    },
                }
            )
        completion = {
            "outcome": answer.outcome,
            "outputs": outputs,
            "inputs": wire_json_loads(ready.binding)["inputs"],
            "support": wire_json_loads(ready.binding)["support"],
            "implementation_revision": port.identity.implementation,
        }
        if any(
            evidence is not None
            for evidence in (
                answer.execution_evidence,
                answer.product_validation_evidence,
                answer.cpu_execution_evidence,
                answer.pdf_execution_evidence,
                answer.pdf_observation_evidence,
                answer.provider_execution_evidence,
            )
        ):
            from corpus_structure.semantic.data_operation_execution_evidence import (
                bind_execution_evidence,
            )

            completion["execution_evidence"] = bind_execution_evidence(
                answer.execution_evidence,
                fence=claim.fence,
                runtime_id=claim.runtime_id,
                cpu_content=answer.cpu_execution_evidence,
                cpu_reply_content=answer.cpu_execution_reply,
                product_validation_content=answer.product_validation_evidence,
                pdf_content=answer.pdf_execution_evidence,
                pdf_observation_content=answer.pdf_observation_evidence,
                provider_content=answer.provider_execution_evidence,
            )
        draft_bytes = len(json_bytes(completion))
        if draft_bytes > self.policy.max_reply_bytes:
            raise ValueError(
                f"Completion draft uses {draft_bytes} bytes, exceeding the "
                f"{self.policy.max_reply_bytes}-byte reply limit"
            )

        request: WireRetainDataCompletionIntentRequest = {
            **claim.fence,
            "runtime_id": RuntimeId(claim.runtime_id),
            "completion": cast(WireCompletion, completion),
        }
        draft = None
        if self.completion_drafts is not None and ready.operation in SUPPORTED_OPERATIONS:
            from dataclasses import asdict

            from corpus_structure.semantic.data_operation_wire import wire_contracts

            writer_schema = json_bytes(
                wire_contracts(context.basis.captured_contracts)["retain_data_completion_intent"][
                    "input"
                ]
            )
            draft = self.completion_drafts.acknowledge(
                request,
                release_id=claim.release_id,
                operation=ready.operation,
                writer_schema=writer_schema,
                basis=json_bytes(
                    dict(
                        execution_origin=self._draft_origins[(claim.task_id, claim.attempt)][
                            "origin_id"
                        ],
                        identity={
                            name: {"bytes": value.hex()} if isinstance(value, bytes) else value
                            for name, value in asdict(port.identity).items()
                        },
                        binding=wire_json_loads(ready.binding),
                        runtime_manifest_sha256=sha256(context.basis.runtime.manifest).hexdigest(),
                        runtime_archive_sha256=sha256(context.basis.runtime.archive).hexdigest(),
                    )
                ),
                check_active=lambda: _check_claim_active(owner, claim),
            )
            request = draft.native_request()

        def retain(calls):
            return calls.retain_data_completion_intent(request)

        return _RetainedAnswer(owner.retain(claim, retain)["intent_id"], draft)

    def _publish_fresh(self, ready, claim, retained, owner, physical):
        receipt = self._publish(claim, retained.intent_id, owner)
        store = self.completion_drafts
        if retained.draft is not None and store is not None:

            def inspect(request):
                with self.native_io.transaction() as connection:
                    return connection.calls.inspect_data_completion_draft(request)

            try:
                if not physical.retired():
                    return receipt
                store.retire(
                    retained.draft.identity,
                    project_id=ready.resolved.subject_context.project_id,
                    inspect=inspect,
                    confirmed_publication=(retained.draft, retained.intent_id),
                )
            except Exception as error:
                # Publication is already committed. The operator can retry a
                # durable marker; any unproven draft remains in private custody.
                logging.getLogger(__name__).warning(
                    "Completed draft retirement did not finish (%s, %s)",
                    retained.draft.identity,
                    type(error).__name__,
                )
        return receipt

    def _has_draft_path(self, ready):
        return self.completion_drafts is not None and ready.operation in SUPPORTED_OPERATIONS

    def _recovery_disposition(self, ready, native):
        action = (
            "reconcile"
            if native["action"] == "reconcile"
            else "inspect-draft"
            if self._has_draft_path(ready)
            else "compute"
        )
        return _RecoveryDisposition(action, native)

    @staticmethod
    def _observe_recovery(claim, action, *, retained_intent_id=None):
        from corpus_structure.cli.observation_logging import bound, logger

        with bound(**claim.fence, release_id=claim.release_id, runtime_id=claim.runtime_id):
            logger(__name__).info(
                "native_demand.recovery_selected",
                recovery_action=action,
                retained_intent_id=retained_intent_id,
                observation_scope="checked committed claim",
            )

    def _recover_answer(self, ready, claim, owner):
        """Native authority selects whether privately acknowledged bytes may be used."""
        drafts = self.completion_drafts
        if drafts is None or ready.operation not in SUPPORTED_OPERATIONS:
            return None
        from sqlalchemy.exc import DBAPIError

        self._observe_recovery(claim, "inspect-draft")
        origins = self._draft_origins[(claim.task_id, claim.attempt)]
        for candidate in origins["candidates"]:
            for draft in drafts.candidates(candidate["request_id"], candidate["generation"]):
                if wire_json_loads(draft.basis).get("execution_origin") != candidate["origin_id"]:
                    continue
                original = draft.native_request()

                def consume(calls, *, candidate=candidate, draft=draft, original=original):
                    return calls.consume_data_completion_draft(
                        {
                            **claim.fence,
                            "origin_id": candidate["origin_id"],
                            "draft_id": draft.identity,
                            "completion": original["completion"],
                        }
                    )

                try:
                    return owner.retain(claim, consume)["intent_id"]
                except DBAPIError as error:
                    if getattr(error.orig, "sqlstate", None) not in {"P0001", "P0002", "23514"}:
                        raise

                    # A definitive candidate refusal rolled back its entire
                    # transaction. Reuse the native renewal owner to establish
                    # current authority before any fresh computation. Ambiguous
                    # commit custody is ClaimSettlementUncertain and never enters
                    # this DBAPI refusal branch.
                    def current(calls):
                        return calls.renew_data_request({**claim.fence, "lease_seconds": 300})

                    if owner.retain(claim, current)["state"] != "renewed":
                        raise
        return None

    @staticmethod
    def _drop_hydration(physical, ready):
        physical.hydrated_inputs = None
        for retained in (
            physical.consumer_inputs,
            physical.consumer_results,
            physical.binding_rows,
            physical.hydrated_sizes,
        ):
            retained.pop(ready.obligation, None)

    @staticmethod
    def _batch_member(ready, claim, inputs):
        return PythonBatchMember(
            f"{claim.request_id}:{claim.generation}:{claim.attempt}",
            inputs,
            ready.binding_result,
            producer=json_bytes(claim.fence),
        )

    @staticmethod
    def _batch_item_limit(port):
        limit = getattr(port, "batch_max_items", None)
        if limit is not None and (type(limit) is not int or limit < 1):
            raise PortRefusal("batch item bound must be a positive integer")
        return limit

    @staticmethod
    def _batch_inputs_fit(port, members):
        maximum = getattr(port, "batch_max_input_bytes", None)
        measure = getattr(port, "batch_input_bytes", None)
        if maximum is None and measure is None:
            return True
        if type(maximum) is not int or maximum < 1 or not callable(measure):
            raise PortRefusal("batch input limit lacks its exact size owner")
        size = measure(tuple(members))
        if type(size) is not int or size < 0:
            raise PortRefusal("batch input size owner returned an invalid byte count")
        return size <= maximum

    def _claim_many(self, ready, owner):
        preparations = [_ClaimPreparation(item) for item in ready]
        seen = set()
        with self.native_io.transaction() as connection:
            requested = [wire_json_loads(item.native) for item in ready]
            result = connection.calls.claim_data_requests(
                cast(
                    WireClaimDataRequestsRequest,
                    {
                        "holder": self.holder,
                        "lease_seconds": 300,
                        "items": [
                            {"request_id": item["request_id"], "generation": item["generation"]}
                            for item in requested
                        ],
                    },
                )
            )["items"]
            if len(result) != len(preparations):
                raise PortRefusal("native claim set changed its item correspondence")
            for prepared, expected, item in zip(preparations, requested, result, strict=True):
                if item["state"] == "no-work":
                    continue
                if item["state"] == "refused":
                    prepared.error = PortRefusal("native claim refused: " + item["reason"])
                    prepared.error.add_note("SQLSTATE " + item["sqlstate"])
                    continue
                claimed = item["result"]
                key = claimed["request_id"], claimed["generation"]
                if key in seen:
                    continue  # One actual producer for repeated logical attachments.
                seen.add(key)
                prepared.native = claimed
                prepared.claim = NativeRequestClaim(
                    claimed["request_id"],
                    claimed["generation"],
                    claimed["task_id"],
                    claimed["attempt"],
                    claimed["holder"],
                    claimed["release_id"],
                    datetime.fromisoformat(claimed["lease_until"].replace("Z", "+00:00")),
                    runtime_id=claimed["runtime_id"],
                )
                if any(
                    claimed[field] != expected[field]
                    for field in (
                        "request_id",
                        "generation",
                        "release_id",
                        "runtime_id",
                        "binding",
                        "binding_demand_id",
                        "binding_obligation_id",
                    )
                ):
                    prepared.error = PortRefusal(
                        "native claim differs from its prepared immutable generation basis"
                    )
                    continue
                if expected["action"] == "reconcile" and claimed["action"] != "reconcile":
                    prepared.error = PortRefusal(
                        "native reconciliation claim no longer has a retained intent"
                    )
                    continue
                if claimed["action"] != "reconcile" and self._has_draft_path(prepared.ready):
                    prepared.origin = connection.calls.register_data_execution_origin(
                        {
                            **prepared.claim.fence,
                            "runtime_id": RuntimeId(prepared.claim.runtime_id),
                        }
                    )
        # Renewal and settlement only observe committed claims.
        for prepared in preparations:
            if prepared.claim is not None:
                owner.add_claim(prepared.claim)
                if prepared.origin is not None:
                    self._draft_origins[(prepared.claim.task_id, prepared.claim.attempt)] = (
                        prepared.origin
                    )
        return tuple(preparations)

    def _claim(self, ready, owner):
        (prepared,) = self._claim_many((ready,), owner)
        if prepared.claim is None:
            if prepared.error is not None:
                raise prepared.error
            return None, {"state": "no-work"}
        if prepared.error is not None:
            self._known_failure(
                prepared.claim, owner, prepared.error, phase="native claim correspondence"
            )
            raise prepared.error
        if prepared.native is None:
            raise RuntimeError("native claim lacks its result custody")
        return prepared.claim, prepared.native

    def _publish(self, claim, retained, owner):
        def publish(calls):
            return calls.publish_data_derivation(
                {
                    **claim.fence,
                    "intent_id": retained,
                }
            )

        receipt = canonical_bytes(owner.settle(claim, publish))
        self._draft_origins.pop((claim.task_id, claim.attempt), None)
        self._receipt_count += 1
        if len(self._receipt_sink) < self._receipt_limit:
            self._receipt_sink.append(receipt)
        return receipt

    def _reconcile(self, claim, retained, owner):
        if not retained:
            raise ValueError("native reconciliation lacks exact retained intent")

        self._observe_recovery(claim, "reconcile", retained_intent_id=retained)

        def adopt(calls):
            return calls.adopt_data_completion_intent(
                {
                    **claim.fence,
                    "intent_id": retained,
                }
            )

        owner.retain(claim, adopt)
        return self._publish(claim, retained, owner)

    @staticmethod
    def _retained_failure(error, claim=None, *, phase, claims=()):
        """Publish bounded diagnostics before releasing traceback-owned bodies.

        Keep the actual exception and typed recovery/uncertainty attributes. Only
        traceback frame references are removed, including linked/grouped errors;
        physical resource custody remains with the normal owner and quarantine.
        """
        from sqlalchemy.exc import StatementError

        from corpus_structure.cli.observation_logging import bound, logger

        bindings = (
            dict(claim.fence, runtime_id=claim.runtime_id, release_id=claim.release_id)
            if claim is not None
            else {}
        )
        if claim is None and claims:
            bindings.update(
                request_id=None,
                task_id=None,
                attempt=None,
                logical_requests=[dict(value.fence) for value in claims],
            )
        with bound(**bindings):
            logger(__name__).error(
                "native_demand.execution_failed",
                phase=phase,
                exc_info=(type(error), error, error.__traceback__),
                sqlstate=getattr(error, "sqlstate", None)
                or getattr(getattr(error, "orig", None), "sqlstate", None),
            )
        pending, seen = [error], set()
        while pending:
            current = pending.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            if isinstance(current, BaseExceptionGroup):
                pending.extend(current.exceptions)
            pending.extend(
                link for link in (current.__cause__, current.__context__) if link is not None
            )
            original = getattr(current, "orig", None)
            if isinstance(original, BaseException):
                pending.append(original)
            current.__traceback__ = None
            # SQLAlchemy retains the submitted JSON body separately from its
            # traceback. The diagnostic has already been published; preserve the
            # native original/SQLSTATE and typed recovery attributes, not params.
            if isinstance(current, StatementError):
                current.params = None
        return error

    def _known_failure(self, claim, owner, error, *, phase):
        """Release only a known-retired computation, never uncertain settlement."""
        if claim is None:
            return
        self._draft_origins.pop((claim.task_id, claim.attempt), None)
        if isinstance(error, (ClaimFenceLost, ClaimSettlementUncertain)):
            return
        try:
            owner.check_claim(claim)
        except ClaimFenceLost:
            return

        # Preserve the actual exception to the caller. The immutable native record
        # describes custody without copying protected values from exception text.
        def release(calls):
            from corpus_structure.semantic.d1_limitation import known_d1_failure

            failure = known_d1_failure(error, fence=claim.fence, runtime_id=claim.runtime_id)
            return calls.release_data_attempt(
                {
                    **claim.fence,
                    "physical_retirement": "confirmed",
                    "failure": failure
                    if failure is not None
                    else {
                        "code": type(error).__module__ + "." + type(error).__qualname__,
                        "message": phase + " did not complete",
                    },
                }
            )

        try:
            owner.settle(claim, release)
        except Exception as cleanup:
            error.add_note("failed attempt release: " + str(cleanup))
            raise ExceptionGroup(
                "computation and exact attempt release failed", [error, cleanup]
            ) from cleanup

    def _execute(self, queued, owner, reservation):
        ready = queued.ready if isinstance(queued, _ClaimedReady) else queued
        physical = _RequestExecution(self._physical, reservation)
        claim, phase = None, "claim"
        try:
            if isinstance(queued, _ClaimedReady):
                claim, claimed = queued.claim, queued.native
            else:
                claim, claimed = self._claim(ready, owner)
                if claim is None:
                    return _ExecutionResult()
            physical.claim = claim
            owner.check_claim(claim)
            disposition = self._recovery_disposition(ready, claimed)
            if disposition.action == "reconcile":
                phase = "reconciliation"
                return _ExecutionResult(
                    (self._reconcile(claim, disposition.retained_intent_id, owner),)
                )
            if self._execution_context(claim).model.operation(ready.operation).external is not None:
                phase = "external packet custody"

                def retain_packet(calls):
                    return calls.retain_external_data_packet(
                        {
                            **claim.fence,
                            "runtime_id": RuntimeId(claim.runtime_id),
                            "max_bytes": self.policy.max_packet_bytes,
                        }
                    )

                owner.settle(claim, retain_packet)
                # Handoff retires this local claim. Delivery is awaiting work,
                # and supplies no derivation/publication receipt.
                return _ExecutionResult()
            else:
                phase = "computation"
                context = self._execution_context(claim)
                physical.cpu = context.cpu or self._physical.cpu
                port = self._port(ready.operation, context)
                phase = "hydration"
                inputs = self._hydrate(ready, physical, context=context)
                phase = "computation"
                reservation.reduce_to(
                    2 * physical.hydrated_sizes[ready.obligation] + 3 * self.policy.max_reply_bytes
                )
                answer = yield from physical.relay(
                    port.plan_python(
                        inputs,
                        binding=ready.binding_result,
                        check_active=lambda: _check_claim_active(owner, claim),
                        execution_owner=physical,
                    )
                )
                phase = "settlement"
                retained = self._retain_answer(ready, claim, answer, port, owner, physical=physical)
                receipt = self._publish_fresh(ready, claim, retained, owner, physical)
            return _ExecutionResult((receipt,))
        except Exception as error:
            if claim is not None and physical.retired():
                try:
                    self._known_failure(claim, owner, error, phase=phase)
                except Exception as release_error:
                    error = release_error
            elif claim is not None:
                self._physical.pending_failures.append((physical, claim, owner, error, phase))
            self._failed_requests.add(
                (json.loads(ready.native)["request_id"], json.loads(ready.native).get("generation"))
            )
            error.add_note("native obligation: " + ready.obligation)
            return _ExecutionResult(failures=(self._retained_failure(error, claim, phase=phase),))
        finally:
            physical.running = False
            reservation.release()
            physical.release_retired_inputs()

    def _execute_batch(self, ready, owner, reservation, *, retain_claim=lambda item: None):
        physical = _RequestExecution(self._physical, reservation)
        pending, receipts, failures, deferred = [], [], [], []
        hydrated_bytes, overflow = 0, False
        try:
            fresh = not isinstance(ready[0], _ClaimedReady)
            preparations = self._claim_many(ready, owner) if fresh else ()
            for index, queued in enumerate(ready):
                item = queued.ready if isinstance(queued, _ClaimedReady) else queued
                claim, phase = None, "claim"
                try:
                    if isinstance(queued, _ClaimedReady):
                        claim, claimed = queued.claim, queued.native
                    else:
                        prepared = preparations[index]
                        claim, claimed = prepared.claim, prepared.native
                        if prepared.error is not None:
                            raise prepared.error
                    if claim is None:
                        continue
                    if claimed is None:
                        raise RuntimeError("native claim lacks its result custody")
                    owner.check_claim(claim)
                    phase = "reconciliation"
                    # A concurrent retained intent can win even when attachment
                    # saw fresh work. No member hydrates in that case.
                    disposition = self._recovery_disposition(item, claimed)
                    if disposition.action == "reconcile":
                        receipts.append(
                            self._reconcile(claim, disposition.retained_intent_id, owner)
                        )
                    else:
                        phase = "computation"
                        context = self._execution_context(claim)
                        physical.cpu = context.cpu or self._physical.cpu
                        port = self._port(item.operation, context)
                        maximum = self._batch_item_limit(port)
                        # Do not hydrate an item past the declared count limit.
                        if overflow or (maximum is not None and len(pending) >= maximum):
                            boundary = _ClaimedReady(item, claim, claimed)
                            retain_claim(boundary)
                            deferred.append(boundary)
                            continue
                        phase = "hydration"
                        inputs = self._hydrate(item, physical, context=context)
                        size = physical.hydrated_sizes[item.obligation]
                        candidate = self._batch_member(item, claim, inputs)
                        exceeds = hydrated_bytes + size > self.policy.max_packet_bytes
                        if not exceeds:
                            exceeds = not self._batch_inputs_fit(
                                port,
                                (
                                    *(
                                        self._batch_member(row[1], row[2], row[3])
                                        for row in pending
                                    ),
                                    candidate,
                                ),
                            )
                        if exceeds:
                            self._drop_hydration(physical, item)
                            inputs = candidate = None
                            if not pending:
                                raise CapacityExceeded(
                                    "one indivisible batch member exceeds physical input capacity"
                                )
                            boundary = _ClaimedReady(item, claim, claimed)
                            retain_claim(boundary)
                            deferred.append(boundary)
                            overflow = True
                            continue
                        hydrated_bytes += size
                        member = f"{claim.request_id}:{claim.generation}:{claim.attempt}"
                        if item.obligation in physical.consumer_inputs:
                            physical.consumer_inputs[member] = physical.consumer_inputs[
                                item.obligation
                            ]
                            if item.obligation in physical.consumer_results:
                                physical.consumer_results[member] = physical.consumer_results[
                                    item.obligation
                                ]
                        pending.append((member, item, claim, inputs, port))
                except Exception as error:
                    if claim is not None:
                        try:
                            self._known_failure(claim, owner, error, phase=phase)
                        except Exception as release_error:
                            error = release_error
                    self._failed_requests.add(
                        (
                            json.loads(item.native)["request_id"],
                            json.loads(item.native).get("generation"),
                        )
                    )
                    error.add_note("native obligation: " + item.obligation)
                    failures.append(self._retained_failure(error, claim, phase=phase))
            if pending:
                physical.hydrated_inputs = None
                reservation.reduce_to(2 * hydrated_bytes + 3 * self.policy.max_reply_bytes)
                active, rejected = [], []
                for row in pending:
                    try:
                        owner.check_claim(row[2])
                    except ClaimFenceLost as error:
                        rejected.append((row, error))
                    else:
                        active.append(row)
                for (_, _item, claim, _, _), error in rejected:
                    self._failed_requests.add((claim.request_id, claim.generation))
                    failures.append(self._retained_failure(error, claim, phase="claim fence"))
                pending = tuple(active)
                physical.claims = tuple(row[2] for row in pending)
                try:
                    answer = None
                    order_key = getattr(pending[0][4], "batch_order_key", None) if pending else None
                    if order_key is not None:
                        pending = tuple(
                            sorted(
                                pending,
                                key=lambda row: order_key(
                                    self._batch_member(row[1], row[2], row[3])
                                ),
                            )
                        )
                    if pending:
                        # One original batch remains useful while any member has
                        # authority. Each logical result settles under its own fence.
                        answer = yield from physical.relay(
                            pending[0][4].plan_batch_python(
                                tuple(
                                    self._batch_member(item, claim, inputs)
                                    for member, item, claim, inputs, _ in pending
                                ),
                                check_active=lambda: _check_batch_active(
                                    owner, tuple(row[2] for row in pending)
                                ),
                                execution_owner=physical,
                            )
                        )
                    if answer is not None and tuple(
                        member for member, _ in answer.members
                    ) != tuple(row[0] for row in pending):
                        raise ValueError("native batch member correspondence differs")
                except Exception as error:
                    for _, _item, claim, _, _ in pending:
                        if physical.retired():
                            try:
                                self._known_failure(claim, owner, error, phase="computation")
                            except Exception as release_error:
                                failures.append(
                                    self._retained_failure(
                                        release_error, claim, phase="attempt release"
                                    )
                                )
                        else:
                            self._physical.pending_failures.append(
                                (physical, claim, owner, error, "computation")
                            )
                        self._failed_requests.add((claim.request_id, claim.generation))
                    failures.append(
                        self._retained_failure(
                            error,
                            phase="batch computation",
                            claims=tuple(row[2] for row in pending),
                        )
                    )
                else:
                    for (_, item, claim, _, port), (_, result) in zip(
                        pending,
                        answer.members if answer is not None else (),
                        strict=True,
                    ):
                        try:
                            retained = self._retain_answer(
                                item, claim, result, port, owner, physical=physical
                            )
                            receipts.append(
                                self._publish_fresh(item, claim, retained, owner, physical)
                            )
                        except Exception as error:
                            try:
                                self._known_failure(claim, owner, error, phase="settlement")
                            except Exception as release_error:
                                error = release_error
                            self._failed_requests.add((claim.request_id, claim.generation))
                            error.add_note("native obligation: " + item.obligation)
                            failures.append(
                                self._retained_failure(error, claim, phase="settlement")
                            )
            return _ExecutionResult(tuple(receipts), tuple(failures), tuple(deferred))
        finally:
            physical.running = False
            reservation.release()
            physical.release_retired_inputs()

    def _prepare_page(self, snapshot, authorization):
        with self.native_io.transaction() as connection:
            planner = connection.planner(self.model)
            ready = planner.ready(
                snapshot,
                authorization=authorization,
                excluded_requests=frozenset(self._failed_requests),
            )
            selected = tuple(getattr(planner, "selected_population_ids", ()))
            logical_progress = planner.logical_progress
            refusals = planner.refusals
        ready = tuple(
            item
            for item in ready
            if (
                wire_json_loads(item.native)["request_id"],
                wire_json_loads(item.native).get("generation"),
            )
            not in self._failed_requests
        )
        return ready, selected, logical_progress, refusals

    def _drive_sweep(self, pages, authorization, owner):
        """One frontier binds bounded compact pages between physical-work ticks."""
        pages = iter(pages)
        pending: deque[ReadyDataRequest | _PreparedReady | _ClaimedReady] = deque()
        receipts, failures, selected = [], [], []
        logical_progress = 0
        exhausted = False

        def plan():
            nonlocal exhausted
            reservations = set()
            held_claims: dict[str, _ClaimedReady] = {}
            active_requests = 0

            def execute(batch, items, reservation):
                nonlocal active_requests
                # The child now runs synchronously into its request owner before
                # its first yield; that owner carries the physical lifetime.
                self._physical.pending_reservations.discard(reservation)
                for item in items:
                    if isinstance(item, _ClaimedReady):
                        held_claims.pop(item.claim.request_id, None)
                deferred = ()
                try:
                    result = yield from (
                        self._execute_batch(
                            tuple(
                                item.ready if isinstance(item, _PreparedReady) else item
                                for item in items
                            ),
                            owner,
                            reservation,
                            retain_claim=lambda item: held_claims.__setitem__(
                                item.claim.request_id, item
                            ),
                        )
                        if batch
                        else self._execute(
                            items[0].ready if isinstance(items[0], _PreparedReady) else items[0],
                            owner,
                            reservation,
                        )
                    )
                    receipts.extend(result.receipts)
                    failures.extend(result.failures)
                    deferred = result.deferred
                    pending.extendleft(reversed(deferred))
                finally:
                    active_requests -= len(items) - sum(
                        isinstance(item, _ClaimedReady) for item in deferred
                    )
                    reservations.discard(reservation)

            def refill():
                nonlocal exhausted, logical_progress
                # One page plus at most a claim window stays compact. Bodies
                # only exist after stage-A admission, inside an active child.
                while not exhausted and len(pending) < self.policy.max_claims:
                    try:
                        snapshot = next(pages)
                    except StopIteration:
                        exhausted = True
                        break
                    ready, populations, done, errors = self._prepare_page(snapshot, authorization)
                    groups = {}
                    for item in ready:
                        native = wire_json_loads(item.native)
                        key = (native["release_id"], native["runtime_id"], item.operation)
                        groups.setdefault(key, []).append(item)
                    pending.extend(item for group in groups.values() for item in group)
                    selected.extend(populations)
                    logical_progress += done
                    failures.extend(errors)

            def admit():
                nonlocal active_requests
                from corpus_structure.orchestrate.execution_host import ExecutionPreparationDeferred

                def prepare(index):
                    queued = pending[index]
                    if not isinstance(queued, (_PreparedReady, _ClaimedReady)):
                        queued = _PreparedReady(self._prepare_ready(queued, authorization))
                        pending[index] = queued
                    return queued

                def failed(item, error, *, claim=None, phase):
                    if claim is not None:
                        held_claims.pop(claim.request_id, None)
                        try:
                            self._known_failure(claim, owner, error, phase=phase)
                        except Exception as release_error:
                            error = release_error
                    native = wire_json_loads(item.native)
                    self._failed_requests.add((native["request_id"], native.get("generation")))
                    error.add_note("native obligation: " + item.obligation)
                    failures.append(self._retained_failure(error, claim, phase=phase))

                def recover(items):
                    """Commit first, then reconcile or adopt without acquiring a physical port."""
                    nonlocal active_requests
                    if isinstance(items[0], _ClaimedReady):
                        claimed = tuple(
                            _ClaimPreparation(item.ready, item.claim, item.native) for item in items
                        )
                    else:
                        try:
                            claimed = self._claim_many(tuple(item.ready for item in items), owner)
                        except Exception as error:
                            for item in items:
                                pending.popleft()
                                failed(item.ready, error, phase="claim")
                            return []
                        active_requests += sum(item.claim is not None for item in claimed)
                    for _ in items:
                        pending.popleft()
                    compute = []
                    for prepared in claimed:
                        ready, claim, native = prepared.ready, prepared.claim, prepared.native
                        try:
                            if prepared.error is not None:
                                raise prepared.error
                            if claim is None:
                                continue
                            if native is None:
                                raise RuntimeError("native claim lacks its result custody")
                            owner.check_claim(claim)
                            disposition = self._recovery_disposition(ready, native)
                            if disposition.action == "reconcile":
                                receipt = self._reconcile(
                                    claim, disposition.retained_intent_id, owner
                                )
                            elif (
                                disposition.action == "inspect-draft"
                                and (retained := self._recover_answer(ready, claim, owner))
                                is not None
                            ):
                                receipt = self._publish(claim, retained, owner)
                            else:
                                boundary = _ClaimedReady(ready, claim, native)
                                held_claims[claim.request_id] = boundary
                                compute.append(boundary)
                                continue
                            receipts.append(receipt)
                            held_claims.pop(claim.request_id, None)
                        except Exception as error:
                            failed(ready, error, claim=claim, phase="completion recovery")
                        if claim is not None:
                            active_requests -= 1
                    pending.extendleft(reversed(compute))
                    return compute

                while True:
                    refill()
                    if not pending:
                        return None
                    index = 0
                    try:
                        first = prepare(0)
                        ready = first.ready
                        native = wire_json_loads(ready.native)
                        basis = native["release_id"], native["runtime_id"]
                        disposition = self._recovery_disposition(ready, native)
                        reconcile = disposition.action == "reconcile"
                        context = None if reconcile else self._ready_context(ready)
                        operation = (
                            None if context is None else context.model.operation(ready.operation)
                        )
                        batch = (
                            operation is not None
                            and operation.external is None
                            and operation.capabilities.forms == ("batch",)
                        )
                        recovery = disposition.action != "compute"
                        claimed = isinstance(first, _ClaimedReady)
                        item_limit = self.policy.max_claims if batch else 1
                        if not recovery and not claimed and operation is not None:
                            self._physical.prepare_target_hosts((ready.operation,))
                            if operation.external is None:
                                self._physical.select_operations((ready.operation,), context)
                            if batch:
                                item_limit = (
                                    self._batch_item_limit(self._port(ready.operation, context))
                                    or item_limit
                                )
                        items = []
                        for index in range(min(len(pending), self.policy.max_claims, item_limit)):
                            queued = pending[index]
                            item = (
                                queued.ready
                                if isinstance(queued, (_PreparedReady, _ClaimedReady))
                                else queued
                            )
                            next_native = wire_json_loads(item.native)
                            if items and (
                                item.operation != ready.operation
                                or next_native["action"] == "reconcile"
                                or (next_native["release_id"], next_native["runtime_id"]) != basis
                                or isinstance(queued, _ClaimedReady) != claimed
                            ):
                                break
                            if (
                                not claimed
                                and active_requests + len(items) >= self.policy.max_claims
                            ):
                                break
                            items.append(prepare(index))
                    except ExecutionPreparationDeferred:
                        return None
                    except Exception as error:
                        queued = pending[index]
                        item = (
                            queued.ready
                            if isinstance(queued, (_PreparedReady, _ClaimedReady))
                            else queued
                        )
                        claim = queued.claim if isinstance(queued, _ClaimedReady) else None
                        failed(item, error, claim=claim, phase="execution preparation")
                        if claim is not None:
                            active_requests -= 1
                        del pending[index]
                        continue
                    if not items:
                        return None
                    if recovery or claimed:
                        draft_credit = None
                        if self.completion_drafts is not None and not reconcile and recovery:
                            # Native reconciliation and draft intake have no
                            # input packet, CPU capsule or provider reservation.
                            needed = 3 * self.policy.max_reply_bytes
                            self._physical.host.ensure_request_room(needed)
                            draft_credit = self.budget.try_admit(needed)
                            if draft_credit is None:
                                return None
                        try:
                            items = recover(items)
                        finally:
                            if draft_credit is not None:
                                draft_credit.release()
                        if not items:
                            continue
                        try:
                            if operation is not None and operation.external is None:
                                self._physical.select_operations((ready.operation,), context)
                            if batch:
                                limit = self._batch_item_limit(self._port(ready.operation, context))
                                if limit is not None:
                                    items = items[:limit]
                        except ExecutionPreparationDeferred:
                            return None
                        except Exception as error:
                            for item in items:
                                pending.popleft()
                                failed(
                                    item.ready,
                                    error,
                                    claim=item.claim,
                                    phase="execution preparation",
                                )
                            active_requests -= len(items)
                            continue
                    reservation = self.budget.try_admit(self.reservation)
                    if reservation is None:
                        return None
                    reservations.add(reservation)
                    self._physical.pending_reservations.add(reservation)
                    active_requests += sum(not isinstance(item, _ClaimedReady) for item in items)
                    for _ in items:
                        pending.popleft()
                    return execute(batch, tuple(items), reservation)

            try:
                yield ReadyFrontier(
                    admit, lambda: exhausted and not pending, max_active=self.policy.max_claims
                )
            finally:
                for reservation in reservations:
                    self._physical.pending_reservations.discard(reservation)
                    reservation.release()
                # Lookahead claims have no submitted work. Cancellation must
                # release them through the normal confirmed-failure owner.
                for item in held_claims.values():
                    self._known_failure(
                        item.claim,
                        owner,
                        RuntimeError("ready frontier ended before execution"),
                        phase="batch boundary rehydration",
                    )
                close = getattr(pages, "close", None)
                if close is not None:
                    close()

        drive_prepared_work(plan(), owner)
        return tuple(receipts), tuple(selected), logical_progress, tuple(failures)

    def advance(self, demand: str, *, authorization: bytes = b"{}", limit: int = 100):
        """Advance one complete bounded-page sweep, including later independent work."""
        return self.run(demand, authorization=authorization, limit=limit, max_rounds=1)

    def _result(self, demand, snapshot, *, standing="fresh-read"):
        return DemandAdvance(
            demand, snapshot, tuple(self._receipt_sink), self._receipt_count, standing
        )

    @contextmanager
    def _report_execution_failure(self, demand):
        try:
            yield
        except NativeDemandExecutionError:
            raise
        except Exception as error:
            if not self._receipt_count and not self._member_failures:
                raise
            failures = (*self._member_failures, error)
            result = self._result(demand, self._last_snapshot or b"{}", standing="last-pinned")
            raise NativeDemandExecutionError(result, failures) from error

    def run(
        self, demand: str, *, authorization: bytes = b"{}", limit: int = 100, max_rounds: int = 100
    ):
        if self._host_run is not None:
            return self._run(
                demand, authorization=authorization, limit=limit, max_rounds=max_rounds
            )
        from corpus_structure.orchestrate.execution_host import execution_host_scope

        with execution_host_scope() as host, host.run(self.policy) as token:
            self._host, self._host_run = host, token
            try:
                return self._run(
                    demand, authorization=authorization, limit=limit, max_rounds=max_rounds
                )
            finally:
                self._host, self._host_run = None, None

    def _run(
        self, demand: str, *, authorization: bytes = b"{}", limit: int = 100, max_rounds: int = 100
    ):
        """Replenish dependency-ready work until idle or an explicit round bound.

        Every sweep consumes one pinned read, including its continuation pages.
        Publication and governed discovery become visible on the next fresh sweep.
        Idle is not a completeness claim: the returned native snapshot retains
        waiting owners, unresolved inputs, partial populations and failures.
        """
        if type(max_rounds) is not int or max_rounds < 1:
            raise ValueError("round bound must be a positive integer")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("frontier page bound must be between one and 1000")
        if self._quarantined:
            raise PhysicalRetirementUncertain(
                "native demand execution owner retains unproven physical work"
            )
        host = self._host
        if host is None or self._host_run is None:
            raise RuntimeError("native execution requires its active process host run")
        if not self._invocation.acquire(blocking=False):
            raise RuntimeError("execution owner already has an active invocation")
        self.demand = demand
        self._receipt_sink, self._member_failures = [], []
        self._receipt_count, self._receipt_limit = 0, limit
        self._last_snapshot = None
        self._failed_requests = set()
        try:
            with (
                self._report_execution_failure(demand),
                self.native_io.claims(self.holder) as owner,
                host.execution(self, self._host_run) as physical,
            ):
                self._physical = physical
                self._claim_owner = owner
                for _ in range(max_rounds):
                    progress = False

                    def pages():
                        nonlocal progress
                        continuation = None
                        while True:
                            with self.native_io.transaction() as connection:
                                planner = connection.planner(self.model)
                                page = planner.resume(
                                    demand,
                                    limit=limit,
                                    selection=dict(continuation["selection"])
                                    if continuation
                                    else None,
                                    after=continuation["after"] if continuation else None,
                                    trust_snapshot=continuation["trust_snapshot"]
                                    if continuation
                                    else None,
                                    read_id=continuation["read_id"] if continuation else None,
                                )
                                if (page["release_id"], page["runtime_id"]) != (
                                    self.prepared.release_id,
                                    self.runtime.runtime_id,
                                ):
                                    raise PortRefusal(
                                        "execution context differs from native demand custody"
                                    )
                                self._last_snapshot = json_bytes(page)
                                if page.get("state") == "cancelled":
                                    return
                            with self.native_io.transaction() as connection:
                                planner = connection.planner(self.model)
                                obligations = {
                                    item["obligation_id"]: item for item in page["obligations"]
                                }
                                populations = {
                                    (
                                        value["name"],
                                        value["evidence"].get("product_id"),
                                        value["evidence"].get("derivation_id"),
                                        value["evidence"].get("member_role"),
                                    )
                                    for value in page["populations"]
                                }
                                for use in page["uses"]:
                                    if use["fate"] != "fulfilled":
                                        continue
                                    obligation = obligations[use["obligation_id"]]
                                    for relation in page["intent"]["discovery"]:
                                        if relation["producer"] != obligation["operation_id"]:
                                            continue
                                        for product in use["products"]:
                                            if product["role"] != relation["output_role"]:
                                                continue
                                            derivation = use["derivation_id"]
                                            if derivation is None:
                                                raise ValueError(
                                                    "discovery product lacks a producing episode"
                                                )
                                            identity = (
                                                relation["population"],
                                                product["product_id"],
                                                derivation,
                                            )
                                            witness = (*identity, relation["output_role"])
                                            if witness not in populations:
                                                planner.expand_discovery(
                                                    page,
                                                    population=identity[0],
                                                    product=identity[1],
                                                    derivation=identity[2],
                                                )
                                                # A new empty closure can enable an existing
                                                # universal/absence binding without new obligations.
                                                progress = True
                                                populations.add(witness)
                            intent = page["selection"]
                            if intent["version"] != "data-demand-intent-v2":
                                raise ValueError(
                                    "demand execution requires its complete native intent"
                                )
                            physical.freeze_target_operations(
                                item["operation"] for item in intent["operations"]
                            )
                            yield page
                            continuation = page.get("continuation")
                            if continuation is None:
                                return

                    settled, selected, logical_progress, errors = self._drive_sweep(
                        pages(), authorization, owner
                    )
                    self._member_failures.extend(errors)
                    if (
                        self._last_snapshot
                        and wire_json_loads(self._last_snapshot).get("state") == "cancelled"
                    ):
                        return self._result(demand, self._last_snapshot)
                    progress = progress or bool(settled) or bool(selected) or bool(logical_progress)
                    if not progress:
                        break
            with self.native_io.transaction() as connection:
                final = connection.planner(self.model).resume(demand, limit=limit)
            result = self._result(demand, json_bytes(final))
            if self._member_failures:
                raise NativeDemandExecutionError(result, tuple(self._member_failures))
            return result
        finally:
            if not self._quarantined:
                self._contexts = {self._target_context.basis.key: self._target_context}
            self._invocation.release()
