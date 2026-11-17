"""Execute admitted native demands without stage-run or method-name policy.

Semantic readiness and effect permission stay with the native bindings. This owner
connects pure Python capabilities to existing fenced task custody and short native
transactions; provider/prepared capabilities use their separately admitted owners.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from contextvars import copy_context
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any, cast, overload
from uuid import uuid4

from sqlalchemy import Connection, Engine

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.work import (
    PhysicalRetirementUncertain,
    PreparedWork,
    ReadyFrontier,
    drive_prepared_work,
)
from corpus_structure.methods.native_host import NativeRetirementUncertain
from corpus_structure.semantic._data_operation_wire import (
    WireAttemptFence,
    WireClaimDataRequestResult,
    WireClaimDataRequestResultVariant2,
    WireCompletion,
    wire_attempt_fence,
)
from corpus_structure.semantic.claim_lifetime import (
    ClaimFenceLost,
    ClaimSettlementUncertain,
    OwnedClaim,
    maintained_claims,
)
from corpus_structure.semantic.cpu_execution import (
    CapacityExceeded,
    OwnedByteBudget,
)
from corpus_structure.semantic.data_operation_admission import (
    acquire_prepared_execution,
    acquire_python_execution,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_demands import DemandPlanner, ReadyDataRequest
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
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
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
)
from corpus_structure.semantic.identifiers import RuntimeId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection
from corpus_structure.semantic.types import PreparedRelease, SourceArtifact, SourceBundle


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


def _check_batch_active(owner, claims):
    """Keep shared physical work useful without hiding individual claim loss."""
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
    deferred: tuple[Any, ...] = ()


@dataclass(frozen=True)
class _PreparedReady:
    ready: ReadyDataRequest


@dataclass(frozen=True)
class _ClaimedReady:
    ready: ReadyDataRequest
    claim: NativeRequestClaim
    native: WireClaimDataRequestResultVariant2


class _OwnedPythonPool:
    """Bounded retirement of the existing invocation's provider-transport threads."""

    def __init__(self, workers):
        self.pool = ThreadPoolExecutor(max_workers=workers)
        # CPython's worker registry is retained before submit can start a thread.
        self.threads = self.pool._threads
        self.drained = False
        self.closed = False
        self.failed = False

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
        if self.closed:
            return
        self.closed = True
        from corpus_structure.semantic.cpu_execution import (
            _COOPERATIVE_CLOSE_SECONDS,
            _WORKER_EXIT_SECONDS,
        )

        deadline = monotonic() + _COOPERATIVE_CLOSE_SECONDS + _WORKER_EXIT_SECONDS
        stopped = Event()
        failures = []

        def stop():
            try:
                self.pool.shutdown(wait=False, cancel_futures=True)
            except BaseException as error:
                failures.append(error)
            finally:
                stopped.set()

        stopper = Thread(target=stop, name="demand-python-stop", daemon=True)
        stopper.start()
        stopped.wait(max(0, deadline - monotonic()))
        for thread in tuple(self.threads):
            thread.join(max(0, deadline - monotonic()))
        self.drained = (
            stopped.is_set()
            and not failures
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
        self.hydration_error = None
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
            work = _PythonWork(self.invocation.pool.submit(lambda: context.run(owned)), share.release)
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
                if not isinstance(work, tuple) or not all(
                    isinstance(item, PreparedWork) for item in work
                ):
                    raise TypeError("prepared capability must yield declared physical work")

                def capture(item):
                    def submit():
                        from corpus_structure.cli.observation_logging import bound

                        claims = self.claims or ((self.claim,) if self.claim is not None else ())
                        bindings: dict[str, Any] = {"demand_id": getattr(self.invocation.executor, "demand", None)}
                        if len(claims) == 1:
                            claim = claims[0]
                            bindings.update(dict(claim.fence, runtime_id=claim.runtime_id,
                                                 release_id=claim.release_id))
                        elif claims:
                            bindings.update(request_id=None, task_id=None, attempt=None,
                                            logical_requests=[dict(claim.fence) for claim in claims])
                        with bound(**bindings):
                            handle = item.try_submit()
                        if handle is not None:
                            self.handles.append(handle)
                        return handle

                    return PreparedWork(submit, item.abandon)

                try:
                    value = yield tuple(capture(item) for item in work)
                    failure = None
                except BaseException as error:
                    value, failure = None, error
        finally:
            plan.close()

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
        self.physical_retired = False
        self.cpu = resources.cpu
        self.native_hosts = resources.native_hosts
        self.providers = resources.providers
        self.executor = executor
        self._selected_operations = None
        self._target_ports = ()

    def __enter__(self):
        self.executor._preparation_bytes = 0
        for context in self.executor._contexts.values():
            context.cpu, context.prepared_schema = None, False
            context.admitted_operations.clear()
        self.host._execution = self
        return self

    def declare_operations(self, operations, context):
        """Declare frozen native profiles before the shared host starts serving."""
        ports = []
        for operation in operations:
            selected = context.model.operation(operation)
            if (
                operation in self.executor.capability_factories
                or selected.capabilities.prepared_factory is not None
            ):
                port = self.executor._port(operation, context)
                self.native_hosts.declare(port.native_selections)
                ports.append(port)
        return tuple(ports)

    def declare_target_operations(self, operations):
        """Keep one frozen target closure; archived bindings cannot expand it."""
        selected = tuple(sorted(operations))
        if self._selected_operations is not None:
            if selected != self._selected_operations:
                raise PortRefusal("native demand changed its frozen operation closure")
            return self._target_ports
        self._target_ports = self.declare_operations(selected, self.executor._target_context)
        self._selected_operations = selected
        return self._target_ports

    def select_operations(self, operations, context=None):
        """Prepare the attached basis closure before admitting physical request work."""
        ports = (
            self.declare_target_operations(operations)
            if context is None
            else self.declare_operations(operations, context)
        )
        context = self.executor._target_context if context is None else context
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
        if self.executor.policy.max_owned_bytes - self.executor._preparation_bytes < self.executor.reservation:
            raise CapacityExceeded(
                "native preparation and one complete request exceed owned capacity"
            )

    def has_live_requests(self):
        self.requests[:] = [request for request in self.requests if request.running or not request.retired()]
        return bool(self.requests)

    def _release_retired_claims(self):
        owner = getattr(self.executor, "_claim_owner", None)
        if owner is None:
            return
        with owner.lock:
            claims = tuple(
                claim for key, claim in owner.active.items()
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

    def _finish_run(self, *error):
        healthy = (
            not self.uncertain_python and not self.pending_failures
            and not self.pool.failed and not self.cpu._submission_uncertain
            and not self.cpu._admissions and not self.cpu._stream_transports
            and self.providers.retire()
            and all(work.retire() for work in self.python_work)
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
    ):
        if runtime.release_id != prepared.release_id:
            raise ValueError("runtime belongs to another release")
        self.engine, self.prepared, self.runtime, self.sources = engine, prepared, runtime, sources
        self.fitter_engine = fitter_engine
        self.admission_engine = engine if admission_engine is None else admission_engine
        basis = execution_basis or DataExecutionBasis(
            prepared, runtime, sources, schema, declarations, captured_contracts, runtime_locations
        )
        self._host, self._host_run = execution_host, host_run
        self._target_context = execution_host.context(basis) if execution_host is not None else _BasisExecution(basis)
        self._contexts = {basis.key: self._target_context}
        self.source_root = source_root
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

                factory = (
                    resolve_prepared_factory(context.model, basis.sources, operation)
                    if selected.capabilities.prepared_factory is not None
                    else self.capability_factories.get(operation)
                )
                if factory is None:
                    raise PortRefusal("declared prepared capability is not acquired")
                with self.admission_engine.begin() as connection:
                    admission = acquire_prepared_execution(
                        connection,
                        basis.prepared,
                        basis.sources,
                        operation,
                        basis.runtime,
                        schema=basis.schema,
                        declarations=basis.declarations,
                        captured_contracts=basis.captured_contracts,
                    )
                port = factory(
                    basis.prepared,
                    context.model,
                    operation,
                    identity=admission.identity,
                    authorize=admission.authorize,
                    custody=admission.custody,
                    sources=basis.sources,
                )
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
                        basis.sources,
                        operation,
                        port.consumer_receiver,
                        authorize=lambda admission=admission, port=port: admission.authorize(
                            port.identity
                        ),
                    )
            else:
                with self.admission_engine.begin() as connection:
                    admission = acquire_python_execution(
                        connection,
                        basis.prepared,
                        basis.sources,
                        operation,
                        basis.runtime,
                        schema=basis.schema,
                        declarations=basis.declarations,
                        captured_contracts=basis.captured_contracts,
                    )
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
            from corpus_structure.semantic.data_operation_admission import recheck_cached_execution

            with self.admission_engine.begin() as connection:
                recheck_cached_execution(connection, basis.prepared, basis.runtime, context.ports[operation].identity)
            context.admitted_operations.add(operation)
        return context.ports[operation]

    def _basis_context(self, release_id, runtime_id):
        if not runtime_id:
            raise PortRefusal("native execution metadata lacks its authenticated runtime basis")
        key = release_id, runtime_id
        if key not in self._contexts:
            with self.engine.begin() as connection:
                basis = self._host.acquire_basis(
                    self.engine, connection, *key, source_root=self.source_root, token=self._host_run
                )
            self._contexts[key] = self._host.context(basis)
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
        with self.engine.begin() as connection:
            storage = DataOperationStorage(connection)
            request = {
                "demand_id": claimed["binding_demand_id"],
                "read_id": binding["read_id"],
                "limit": 1000,
            }
            while True:
                snapshot = storage.read_demand_result(cast(WireReadDemandResultRequest, request))
                obligations = [
                    row
                    for row in snapshot["obligations"]
                    if row["obligation_id"] == claimed["binding_obligation_id"]
                ]
                if obligations:
                    break
                continuation = snapshot.get("continuation")
                if continuation is None:
                    raise PortRefusal("claimed generation lacks its original pinned obligation")
                request = dict(continuation)
            binding_snapshot = {**snapshot, "obligations": obligations}
            candidates = tuple(
                DemandPlanner(context.model, storage).bound_requests(
                    binding_snapshot, authorization=authorization, retained=True
                )
            )
        if (
            len(candidates) != 1
            or candidates[0].request_id != request_id
            or canonical_bytes(wire_json_loads(candidates[0].binding)) != canonical_bytes(binding)
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
        context = self._ready_context(ready)
        if native["action"] == "reconcile":
            return ready
        if (
            native["release_id"] == self.prepared.release_id
            and native["runtime_id"] == self.runtime.runtime_id
            and native["binding_obligation_id"] == ready.obligation
            and canonical_bytes(native["binding"])
            == canonical_bytes(wire_json_loads(ready.binding))
        ):
            # Native attachment has already validated this exact same-read
            # binding. Preserve its typed roles instead of rebuilding SQL/ASTs.
            original, operations = ready, (ready.operation,)
        else:
            original, operations = self._generation_ready(
                ready, native["request_id"], native, context, authorization
            )
        self._physical.select_operations(operations, context)
        return original

    def _renew(self, connection: Connection, claim: OwnedClaim):
        if not isinstance(claim, NativeRequestClaim):
            raise TypeError("native owner requires a request-generation fence")
        result = DataOperationStorage(connection).renew_data_request(
            {**claim.fence, "lease_seconds": 300}
        )
        if result["state"] == "lost":
            raise ClaimFenceLost(claim, result["reason"])

    def _hydrate(
        self, ready: ReadyDataRequest, execution_owner=None, *, context=None, connection=None
    ):
        context = self._target_context if context is None else context
        from corpus_structure.semantic.data_operation_consumers import (
            BoundConsumerSelection,
            hydrate_consumer_selection,
        )

        pins = wire_json_loads(ready.resolved.trust_evidence)
        with self.engine.begin() if connection is None else nullcontext(connection) as connection:
            selected = hydrate_consumer_selection(
                connection,
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
                        "analyzed_scope": wire_json_loads(value.member.analyzed_scope),
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
        if (
            sum(
                len(value.content) + len(value.meaning or b"") + sum(map(len, value.members))
                for value in answer.outputs
            )
            > self.policy.max_reply_bytes
        ):
            raise ValueError("completion reply exceeds owned reply capacity")
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
                pdf_content=answer.pdf_execution_evidence,
                pdf_observation_content=answer.pdf_observation_evidence,
                provider_content=answer.provider_execution_evidence,
            )
        if len(json_bytes(completion)) > self.policy.max_reply_bytes:
            raise ValueError("completion exceeds owned draft capacity")

        def retain(connection):
            return DataOperationStorage(connection).retain_data_completion_intent(
                {
                    **claim.fence,
                    "runtime_id": RuntimeId(claim.runtime_id),
                    "completion": cast(WireCompletion, completion),
                }
            )

        return owner.retain(claim, retain)["intent_id"]

    def _claim(
        self, ready, owner, *, physical=None
    ) -> (
        tuple[NativeRequestClaim, WireClaimDataRequestResultVariant2]
        | tuple[None, WireClaimDataRequestResult]
    ):
        native = wire_json_loads(ready.native)
        mismatch = None
        with self.engine.begin() as connection:
            claimed = DataOperationStorage(connection).claim_data_request(
                {
                    "request_id": native["request_id"],
                    "generation": native["generation"],
                    "holder": self.holder,
                    "lease_seconds": 300,
                }
            )
            if claimed["state"] != "claimed":
                return None, claimed
            claim = NativeRequestClaim(
                claimed["request_id"], claimed["generation"], claimed["task_id"],
                claimed["attempt"], claimed["holder"], claimed["release_id"],
                datetime.fromisoformat(claimed["lease_until"].replace("Z", "+00:00")),
                runtime_id=claimed["runtime_id"],
            )
            if any(
                claimed[field] != native[field]
                for field in (
                    "request_id", "generation", "release_id", "runtime_id", "binding",
                    "binding_demand_id", "binding_obligation_id",
                )
            ):
                mismatch = PortRefusal("native claim differs from its prepared immutable generation basis")
            elif physical is not None and claimed["action"] != "reconcile":
                context = self._execution_context(claim)
                if context.model.operation(ready.operation).external is None:
                    try:
                        # A refused hydration rolls back only its native reads.
                        # The outer transaction commits the claim before the
                        # existing known-failure path releases that exact attempt.
                        with connection.begin_nested():
                            physical.hydrated_inputs = self._hydrate(
                                ready, physical, context=context, connection=connection
                            )
                    except Exception as error:
                        physical.hydration_error = error
        # Renewal and settlement must never observe a claim before its commit.
        owner.add_claim(claim)
        if mismatch is not None:
            self._known_failure(claim, owner, mismatch, phase="native claim correspondence")
            raise mismatch
        return claim, claimed

    def _publish(self, claim, retained, owner):
        def publish(connection):
            return DataOperationStorage(connection).publish_data_derivation(
                {
                    **claim.fence,
                    "intent_id": retained,
                }
            )

        receipt = canonical_bytes(owner.settle(claim, publish))
        self._receipt_count += 1
        if len(self._receipt_sink) < self._receipt_limit:
            self._receipt_sink.append(receipt)
        return receipt

    def _reconcile(self, claim, retained, owner):
        if not retained:
            raise ValueError("native reconciliation lacks exact retained intent")

        def adopt(connection):
            return DataOperationStorage(connection).adopt_data_completion_intent(
                {
                    **claim.fence,
                    "intent_id": retained,
                }
            )

        owner.retain(claim, adopt)
        return self._publish(claim, retained, owner)

    def _known_failure(self, claim, owner, error, *, phase):
        """Release only a known-retired computation, never uncertain settlement."""
        if claim is None or isinstance(error, (ClaimFenceLost, ClaimSettlementUncertain)):
            return
        try:
            owner.check_claim(claim)
        except ClaimFenceLost:
            return

        # Preserve the actual exception to the caller. The immutable native record
        # describes custody without copying protected values from exception text.
        def release(connection):
            from corpus_structure.semantic.d1_limitation import known_d1_failure

            failure = known_d1_failure(error, fence=claim.fence, runtime_id=claim.runtime_id)
            return DataOperationStorage(connection).release_data_attempt(
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

    def _execute(self, ready, owner, reservation):
        physical = _RequestExecution(self._physical, reservation)
        claim, phase = None, "claim"
        try:
            claim, claimed = self._claim(ready, owner, physical=physical)
            if claim is None:
                return _ExecutionResult()
            physical.claim = claim
            if physical.hydration_error is not None:
                phase = "hydration"
                raise physical.hydration_error
            phase = "reconciliation"
            if claimed["state"] != "claimed":
                raise ValueError("native claim state differs from active claim")
            if claimed["action"] == "reconcile":
                receipt = self._reconcile(claim, claimed.get("retained_intent_id"), owner)
            elif (
                self._execution_context(claim).model.operation(ready.operation).external is not None
            ):
                phase = "external packet custody"

                def retain_packet(connection):
                    return DataOperationStorage(connection).retain_external_data_packet(
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
                inputs = physical.hydrated_inputs
                reservation.reduce_to(
                    2 * physical.hydrated_sizes[ready.obligation] + 3 * self.policy.max_reply_bytes
                )
                answer = yield from physical.relay(
                    port.plan_python(
                        inputs,
                        binding=ready.binding_result,
                        check_active=lambda: owner.check_claim(claim),
                        execution_owner=physical,
                    )
                )
                phase = "settlement"
                retained = self._retain_answer(ready, claim, answer, port, owner, physical=physical)
                receipt = self._publish(claim, retained, owner)
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
            return _ExecutionResult(failures=(error,))
        finally:
            physical.running = False
            reservation.release()

    def _execute_batch(self, ready, owner, reservation, *, retain_claim=lambda item: None):
        physical = _RequestExecution(self._physical, reservation)
        pending, receipts, failures, deferred = [], [], [], []
        hydrated_bytes = 0
        try:
            for index, queued in enumerate(ready):
                item = queued.ready if isinstance(queued, _ClaimedReady) else queued
                claim, phase = None, "claim"
                try:
                    physical.hydrated_inputs, physical.hydration_error = None, None
                    if isinstance(queued, _ClaimedReady):
                        claim, claimed = queued.claim, queued.native
                        owner.check_claim(claim)
                        physical.hydrated_inputs = self._hydrate(
                            item, physical, context=self._execution_context(claim)
                        )
                    else:
                        claim, claimed = self._claim(item, owner, physical=physical)
                    if claim is None:
                        continue
                    if claimed["state"] != "claimed":
                        raise ValueError("native claim state differs from active claim")
                    if physical.hydration_error is not None:
                        phase = "hydration"
                        raise physical.hydration_error
                    if claimed["action"] == "reconcile":
                        phase = "reconciliation"
                        receipts.append(
                            self._reconcile(claim, claimed.get("retained_intent_id"), owner)
                        )
                    else:
                        phase = "computation"
                        context = self._execution_context(claim)
                        physical.cpu = context.cpu or self._physical.cpu
                        port = self._port(item.operation, context)
                        inputs = physical.hydrated_inputs
                        size = physical.hydrated_sizes[item.obligation]
                        if pending and hydrated_bytes + size > self.policy.max_packet_bytes:
                            # One boundary lookahead fits stage A's second input
                            # allowance. Drop every hydrated reference before
                            # reducing this call; keep only its renewed claim and
                            # same pinned binding for the next physical call.
                            physical.hydrated_inputs = inputs = None
                            for retained in (physical.consumer_inputs, physical.consumer_results,
                                             physical.binding_rows, physical.hydrated_sizes):
                                retained.pop(item.obligation, None)
                            boundary = _ClaimedReady(item, claim, claimed)
                            retain_claim(boundary)
                            deferred.extend((boundary, *ready[index + 1:]))
                            break
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
                    failures.append(error)
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
                    failures.append(error)
                pending = tuple(active)
                physical.claims = tuple(row[2] for row in pending)
                try:
                    answer = None
                    if pending:
                        # One original batch remains useful while any member has
                        # authority. Each logical result settles under its own fence.
                        answer = yield from physical.relay(
                            pending[0][4].plan_batch_python(
                                tuple(
                                    PythonBatchMember(
                                        member,
                                        inputs,
                                        item.binding_result,
                                        producer=json_bytes(claim.fence),
                                    )
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
                                failures.append(release_error)
                        else:
                            self._physical.pending_failures.append(
                                (physical, claim, owner, error, "computation")
                            )
                        self._failed_requests.add((claim.request_id, claim.generation))
                    failures.append(error)
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
                            receipts.append(self._publish(claim, retained, owner))
                        except Exception as error:
                            try:
                                self._known_failure(claim, owner, error, phase="settlement")
                            except Exception as release_error:
                                error = release_error
                            self._failed_requests.add((claim.request_id, claim.generation))
                            error.add_note("native obligation: " + item.obligation)
                            failures.append(error)
            return _ExecutionResult(tuple(receipts), tuple(failures), tuple(deferred))
        finally:
            physical.running = False
            reservation.release()

    def _prepare_page(self, snapshot, authorization):
        with self.engine.begin() as connection:
            planner = DemandPlanner(self.model, DataOperationStorage(connection))
            ready = planner.ready(
                snapshot, authorization=authorization,
                excluded_requests=frozenset(self._failed_requests),
            )
            selected = tuple(getattr(planner, "selected_population_ids", ()))
            fulfilled = planner.fulfilled_request_ids
        ready = tuple(
            item for item in ready
            if (wire_json_loads(item.native)["request_id"], wire_json_loads(item.native).get("generation"))
            not in self._failed_requests
        )
        return ready, selected, fulfilled, ()

    def _drive_sweep(self, pages, authorization, owner):
        """One frontier binds bounded compact pages between physical-work ticks."""
        pages = iter(pages)
        pending = deque()
        receipts, failures, selected, fulfilled = [], [], [], []
        exhausted = False

        def plan():
            nonlocal exhausted
            reservations = set()
            held_claims = {}
            active_requests = 0

            def execute(batch, items, reservation):
                nonlocal active_requests
                deferred = ()
                try:
                    result = yield from (
                        self._execute_batch(
                            tuple(item.ready if isinstance(item, _PreparedReady) else item for item in items), owner, reservation,
                            retain_claim=lambda item: held_claims.__setitem__(item.claim.request_id, item),
                        )
                        if batch
                        else self._execute(items[0].ready if isinstance(items[0], _PreparedReady) else items[0], owner, reservation)
                    )
                    receipts.extend(result.receipts)
                    failures.extend(result.failures)
                    deferred = result.deferred
                    for item in items:
                        if isinstance(item, _ClaimedReady):
                            held_claims.pop(item.claim.request_id, None)
                    for item in deferred:
                        if isinstance(item, _ClaimedReady):
                            held_claims[item.claim.request_id] = item
                    pending.extendleft(reversed(tuple(
                        item if isinstance(item, _ClaimedReady) else _PreparedReady(item)
                        for item in deferred
                    )))
                finally:
                    active_requests -= len(items) - sum(
                        isinstance(item, _ClaimedReady) for item in deferred
                    )
                    reservations.discard(reservation)

            def refill():
                nonlocal exhausted
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
                    fulfilled.extend(done)
                    failures.extend(errors)

            def admit():
                nonlocal active_requests
                from corpus_structure.orchestrate.execution_host import ExecutionPreparationDeferred

                def prepare(index):
                    queued = pending[index]
                    if not isinstance(queued, (_PreparedReady, _ClaimedReady)):
                        queued = _PreparedReady(self._prepare_ready(queued, authorization))
                        pending[index] = queued
                    else:
                        ready = queued.ready
                        self._physical.select_operations((ready.operation,), self._ready_context(ready))
                    return queued

                while True:
                    refill()
                    if not pending:
                        return None
                    index = 0
                    try:
                        first = prepare(0)
                        ready = first.ready
                        context = self._ready_context(ready)
                        batch = context.model.operation(ready.operation).capabilities.forms == ("batch",)
                        items, fresh = [], 0
                        for index in range(min(len(pending), self.policy.max_claims)):
                            queued = pending[index]
                            item = queued.ready if isinstance(queued, (_PreparedReady, _ClaimedReady)) else queued
                            native = wire_json_loads(item.native)
                            if items and (not batch or item.operation != ready.operation
                                or (native["release_id"], native["runtime_id"]) != context.basis.key):
                                break
                            is_fresh = not isinstance(queued, _ClaimedReady)
                            if active_requests + fresh + is_fresh > self.policy.max_claims:
                                break
                            items.append(prepare(index))
                            fresh += is_fresh
                    except ExecutionPreparationDeferred:
                        return None
                    except Exception as error:
                        queued = pending[index]
                        item = queued.ready if isinstance(queued, (_PreparedReady, _ClaimedReady)) else queued
                        native = wire_json_loads(item.native)
                        self._failed_requests.add((native["request_id"], native.get("generation")))
                        error.add_note("native obligation: " + item.obligation)
                        failures.append(error)
                        del pending[index]
                        continue
                    if not items:
                        return None
                    # Each physical call, including a batch, has one stage-A charge.
                    reservation = self.budget.try_admit(self.reservation)
                    if reservation is None:
                        return None
                    reservations.add(reservation)
                    active_requests += fresh
                    for _ in items:
                        pending.popleft()
                    return execute(batch, tuple(items), reservation)

            try:
                yield ReadyFrontier(
                    admit, lambda: exhausted and not pending, max_active=self.policy.max_claims
                )
            finally:
                for reservation in reservations:
                    reservation.release()
                # Lookahead claims have no submitted work. Cancellation must
                # release them through the normal confirmed-failure owner.
                for item in held_claims.values():
                    self._known_failure(
                        item.claim, owner, RuntimeError("ready frontier ended before execution"),
                        phase="batch boundary rehydration",
                    )
                close = getattr(pages, "close", None)
                if close is not None:
                    close()

        drive_prepared_work(plan(), owner)
        return tuple(receipts), tuple(selected), tuple(fulfilled), tuple(failures)

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

    def run(self, demand: str, *, authorization: bytes = b"{}", limit: int = 100, max_rounds: int = 100):
        if self._host_run is not None:
            return self._run(demand, authorization=authorization, limit=limit, max_rounds=max_rounds)
        from corpus_structure.orchestrate.execution_host import execution_host_scope

        with execution_host_scope() as host, host.run(self.policy) as token:
            self._host, self._host_run = host, token
            try:
                return self._run(demand, authorization=authorization, limit=limit, max_rounds=max_rounds)
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
        if not self._invocation.acquire(blocking=False):
            raise RuntimeError("execution owner already has an active invocation")
        self.demand = demand
        self._receipt_sink, self._member_failures = [], []
        self._receipt_count, self._receipt_limit = 0, limit
        self._last_snapshot = None
        self._failed_requests = set()
        seen_discovered = set()
        seen_fulfilled = set()
        try:
            with (
                self._report_execution_failure(demand),
                maintained_claims(self.engine, (), self.holder, renew=self._renew) as owner,
                self._host.execution(self, self._host_run) as physical,
            ):
                self._physical = physical
                self._claim_owner = owner
                for _ in range(max_rounds):
                    progress = False
                    def pages():
                        nonlocal progress
                        continuation = None
                        while True:
                            with self.engine.begin() as connection:
                                planner = DemandPlanner(self.model, DataOperationStorage(connection))
                                page = planner.resume(
                                    demand,
                                    limit=limit,
                                    selection=dict(continuation["selection"]) if continuation else None,
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
                            with self.engine.begin() as connection:
                                planner = DemandPlanner(self.model, DataOperationStorage(connection))
                                obligations = {item["obligation_id"]: item for item in page["obligations"]}
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
                                            identity = (
                                                relation["population"],
                                                product["product_id"],
                                                use["derivation_id"],
                                            )
                                            if identity[2] is None:
                                                raise ValueError(
                                                    "discovery product lacks a producing episode"
                                                )
                                            if identity not in seen_discovered:
                                                planner.expand_discovery(
                                                    page,
                                                    population=identity[0],
                                                    product=identity[1],
                                                    derivation=identity[2],
                                                )
                                                seen_discovered.add(identity)
                                                progress = True
                            physical.select_operations(
                                item["operation"] for item in page["selection"]["operations"]
                            )
                            yield page
                            continuation = page.get("continuation")
                            if continuation is None:
                                return

                    settled, selected, fulfilled, errors = self._drive_sweep(
                        pages(), authorization, owner
                    )
                    self._member_failures.extend(errors)
                    if self._last_snapshot and wire_json_loads(self._last_snapshot).get("state") == "cancelled":
                        return self._result(demand, self._last_snapshot)
                    progress = (
                        progress or bool(settled) or bool(selected)
                        or bool(set(fulfilled) - seen_fulfilled)
                    )
                    seen_fulfilled.update(fulfilled)
                    if not progress:
                        break
            with self.engine.begin() as connection:
                final = DemandPlanner(self.model, DataOperationStorage(connection)).resume(
                    demand, limit=limit
                )
            result = self._result(demand, json_bytes(final))
            if self._member_failures:
                raise NativeDemandExecutionError(result, tuple(self._member_failures))
            return result
        finally:
            if not self._quarantined:
                self._contexts = {self._target_context.basis.key: self._target_context}
            self._invocation.release()
