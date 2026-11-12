"""Invocation-owned, database-free CPU characterization and bounded owned transfer."""

from __future__ import annotations

import json
import multiprocessing
import sys
import threading
from collections.abc import Callable, Generator, Mapping
from concurrent.futures import Future, ProcessPoolExecutor, TimeoutError
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass
from hashlib import sha256
from time import monotonic
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.core.method import SourceViewRef, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType

from .archive_reader import reconstruct_release
from .archive_wire import encode_products
from .characterization import LayerReport, validate_layer
from .identity import canonical_bytes
from .product_reference import ProductReference
from .source_views import PreparedSourceView
from .types import PreparationProfile, PreparedArtifact, PreparedRelease, SourceBundle


class CapacityExceeded(ValueError):
    """The complete owned input cannot fit the selected physical policy."""


class OwnedByteBudget:
    """Encoded retained bodies, not an estimate of interpreter RSS."""

    def __init__(self, limit: int):
        self.limit = limit
        self.used_bytes = 0
        self._lock = threading.Lock()

    def reserve(self, size: int) -> None:
        if type(size) is not int or size < 0:
            raise ValueError("owned byte reservation must be nonnegative")
        with self._lock:
            if size > self.limit - self.used_bytes:
                raise CapacityExceeded("complete regional/CPU state exceeds owned byte capacity")
            self.used_bytes += size

    def release(self, size: int) -> None:
        with self._lock:
            if type(size) is not int or not 0 <= size <= self.used_bytes:
                raise ValueError("owned byte release differs from retained capacity")
            self.used_bytes -= size


def release_capsule(prepared: PreparedRelease) -> bytes:
    return canonical_bytes(
        dict(
            products=encode_products(prepared),
            manifest=prepared.manifest.decode(),
            artifacts=[dict(kind=a.kind, content=a.content.hex()) for a in prepared.artifacts],
        )
    )


def hydrate_capsule(content: bytes) -> PreparedRelease:
    """Rehydrate private trusted-parent transport, never admit an arbitrary archive.

    The owning parent supplies fully verified execution or protected historical products.
    Identity, runtime and artifact checks protect transfer correspondence; they do not
    replace the parent's full release verification or native archive authentication.
    """
    from .determinants import boundary_compatible

    value = json.loads(content)
    manifest = value["manifest"].encode()
    identity = "release:" + sha256(manifest).hexdigest()
    premises = json.loads(manifest)
    if value["products"]["release_id"] != identity:
        raise ValueError("CPU archive identity differs from manifest")
    if not boundary_compatible(premises["libraries"], premises["profile"]["compiler_version"]):
        raise ValueError("CPU archive runtime differs from parent preparation")
    return reconstruct_release(
        value["products"],
        manifest,
        SourceBundle(premises["root"], ()),
        PreparationProfile(**premises["profile"]),
        tuple(PreparedArtifact(a["kind"], bytes.fromhex(a["content"])) for a in value["artifacts"]),
    )


class _SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: dict[str, Any]
    text: str
    pieces: tuple[dict[str, Any], ...]
    items: tuple[dict[str, Any], ...]
    ancestors: tuple[dict[str, Any], ...]
    health: dict[str, Any]
    text_policy: dict[str, str] | None
    analysis_enabled: bool
    integrated_context: dict[str, Any] | None

    def working_view(self):
        from .contracts import TextPreparationPolicy

        ref = dict(self.ref)
        ref["native_product"] = ProductReference(**ref["native_product"])
        return PreparedSourceView(
            SourceViewRef(**ref),
            self.text,
            self.pieces,
            self.items,
            self.ancestors,
            self.health,
            None if self.text_policy is None else TextPreparationPolicy(**self.text_policy),
            self.analysis_enabled,
            self.integrated_context,
        )


class _Dependency(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pin: dict[str, Any]
    content: str


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    run_id: int | None
    claims: tuple[tuple[int, int, str], ...]
    method: Literal["text.formal_evidence", "text.constructions", "text.evaluate_context"]
    release_id: str
    configuration: dict[str, Any]
    operation: dict[str, str]
    document_id: int
    sources: tuple[_SourceInput, ...]
    dependencies: tuple[_Dependency, ...]


@dataclass(frozen=True)
class CPUReply:
    request_digest: str
    content: bytes
    pid: int
    main_thread: bool
    error_type: str | None = None
    error_message: str | None = None
    cost: bytes | None = None
    native_thread_limit: int | None = None
    native_pools: tuple[dict[str, Any], ...] = ()


class _KernelReader:
    """Finite, owned kernel values; deliberately no database/Reader delegation."""

    def __init__(self, prepared, sources, layers, releases):
        self.prepared = prepared
        self._sources = {view.ref.id: view for view in sources}
        self._layers = layers
        self._releases = releases

    def source_view(self, identity):
        return self._sources[identity]

    def source_view_ref(self, identity):
        return self._sources[identity].ref

    def characterization_layers(self, pins):
        return {pin: self._layers[pin] for pin in pins}

    def characterization_release(self, identity):
        return self._releases[identity]


@dataclass(frozen=True)
class _KernelRun:
    reader: _KernelReader


@dataclass(frozen=True)
class _KernelContext:
    check_active: Callable[[], None]
    operation: Mapping[str, str]

    def characterization_operation(self, _ref):
        return self.operation


_WORKER_RELEASES: dict[str, PreparedRelease] = {}
_WORKER_STOP: Any = None
_WORKER_CANCELLATION: Any = None
_WORKER_REQUEST: tuple[int, int] | None = None
_WORKER_NATIVE_THREADS: int | None = None
_WORKER_NATIVE_LIMITER: Any = None
_WORKER_NATIVE_POOLS: tuple[dict[str, Any], ...] = ()


class CPURequestCancelled(RuntimeError):
    """This private logical request was cancelled; sibling requests remain useful."""


def _apply_native_thread_limits() -> None:
    """Refresh after library loads; supported BLAS/OpenMP pools stay limited until exit.

    A fresh controller discovers newly loaded libraries. It cannot constrain unsupported
    native runtimes, Python threads, tokenizers or GPU execution.
    """
    global _WORKER_NATIVE_LIMITER, _WORKER_NATIVE_POOLS
    if _WORKER_NATIVE_THREADS is None:
        return
    from threadpoolctl import threadpool_info, threadpool_limits

    _WORKER_NATIVE_LIMITER = threadpool_limits(limits=_WORKER_NATIVE_THREADS)
    _WORKER_NATIVE_POOLS = tuple(threadpool_info())
    if any(pool.get("num_threads") != _WORKER_NATIVE_THREADS for pool in _WORKER_NATIVE_POOLS):
        raise RuntimeError("CPU native runtime did not apply the selected thread bound")


def _initialize(capsule: bytes, stop, cancellation=None, native_threads: int = 1) -> None:
    import os

    global _WORKER_STOP, _WORKER_CANCELLATION, _WORKER_NATIVE_THREADS
    _WORKER_NATIVE_THREADS = native_threads
    for variable in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "BLIS_NUM_THREADS",
    ):
        os.environ[variable] = str(native_threads)
    _apply_native_thread_limits()
    prepared = hydrate_capsule(capsule)
    _apply_native_thread_limits()
    _WORKER_RELEASES.clear()
    _WORKER_RELEASES[prepared.release_id] = prepared
    _WORKER_STOP = stop
    _WORKER_CANCELLATION = cancellation


def _worker_active() -> None:
    if _WORKER_STOP is not None and _WORKER_STOP.is_set():
        raise CPURequestCancelled("CPU invocation cancelled")
    if _WORKER_CANCELLATION is not None and _WORKER_REQUEST is not None:
        slot, generation = _WORKER_REQUEST
        with _WORKER_CANCELLATION.get_lock():
            if _WORKER_CANCELLATION[slot * 2] != generation or _WORKER_CANCELLATION[slot * 2 + 1]:
                raise CPURequestCancelled("CPU logical request cancelled")


def _compute(content: bytes, capsules: tuple[bytes, ...], max_reply_bytes: int) -> CPUReply:
    import os

    from corpus_structure.core.method import MethodContext, SourceRunContext
    from corpus_structure.methods.construction_characterization import (
        ConstructionCharacterizationMethod,
    )
    from corpus_structure.methods.contextual_interpretation import ContextualInterpretationMethod
    from corpus_structure.methods.formal_evidence import FormalEvidenceMethod

    _apply_native_thread_limits()
    _worker_active()
    packet = _Input.model_validate_json(content)
    releases = dict(_WORKER_RELEASES)
    for capsule in capsules:
        identity = json.loads(capsule)["products"]["release_id"]
        if identity not in releases:
            releases[identity] = hydrate_capsule(capsule)
    prepared = releases[packet.release_id]
    methods = {
        m.name: m
        for m in (
            FormalEvidenceMethod(),
            ConstructionCharacterizationMethod(),
            ContextualInterpretationMethod(),
        )
    }
    method: Any = methods[packet.method]
    cfg = method.Config.model_validate(packet.configuration)
    layers = {
        ProductReference(**item.pin): LayerReport(item.content.encode())
        for item in packet.dependencies
    }
    reader = _KernelReader(
        prepared, tuple(s.working_view() for s in packet.sources), layers, releases
    )
    unit = UnitView(
        UnitRef(TaskUnitType.DOCUMENT, packet.document_id),
        cast(SourceRunContext, _KernelRun(reader)),
    )
    ctx = cast(MethodContext, _KernelContext(_worker_active, packet.operation))
    (result,) = method._run_prepared((unit,), cfg, ctx)
    layer = result.characterization_layer
    if layer is None:
        raise ValueError("CPU kernel did not produce its declared layer")
    if len(layer.content) > max_reply_bytes:
        raise CapacityExceeded("CPU result exceeds admitted reply byte capacity")
    _worker_active()
    return CPUReply(
        sha256(content).hexdigest(),
        layer.content,
        os.getpid(),
        threading.current_thread() is threading.main_thread(),
        cost=None if result.cost is None else result.cost.model_dump_json().encode(),
        native_thread_limit=_WORKER_NATIVE_THREADS,
        native_pools=_WORKER_NATIVE_POOLS,
    )


def _dispatch(
    content: bytes,
    capsules: tuple[bytes, ...],
    max_reply_bytes: int,
    slot: int = -1,
    generation: int = 0,
) -> CPUReply:
    import os

    global _WORKER_REQUEST
    _WORKER_REQUEST = None if slot < 0 else (slot, generation)
    try:
        _worker_active()
        if json.loads(content).get("method") == "private.spacy_annotations":
            from .cpu_annotations import compute_annotations

            content_out = compute_annotations(content, _worker_active)
            if len(content_out) > max_reply_bytes:
                raise CapacityExceeded("CPU annotation result exceeds admitted reply capacity")
            return CPUReply(
                sha256(content).hexdigest(),
                content_out,
                os.getpid(),
                threading.current_thread() is threading.main_thread(),
                native_thread_limit=_WORKER_NATIVE_THREADS,
                native_pools=_WORKER_NATIVE_POOLS,
            )
        return _compute(content, capsules, max_reply_bytes)
    except Exception as error:
        return CPUReply(
            sha256(content).hexdigest(),
            b"",
            os.getpid(),
            True,
            type(error).__name__,
            str(error)[:2048],
        )


@dataclass
class _InputAdmission:
    owner: CPUExecutionScope
    slot: int
    generation: int
    reserved: int
    active: bool = True
    retired: bool = False
    submitted: bool = False


class CPUHandle:
    def __init__(self, owner, admission, future: Future[CPUReply], digest, check_active):
        self.owner, self.admission, self.future = owner, admission, future
        self.digest, self.check_active = digest, check_active
        self._reply = None
        self._error: BaseException | None = None
        self._collected = False
        self._cancelled = False
        self._cancel_pending = False

    def _signal_cancellation(self) -> None:
        if not self._cancel_pending or not self.admission.active:
            return
        lock = self.owner._cancellation.get_lock()
        if not lock.acquire(False):
            return
        try:
            offset = self.admission.slot * 2
            flags = self.owner._cancellation.get_obj()
            if flags[offset] == self.admission.generation:
                flags[offset + 1] = 1
            self._cancel_pending = False
        finally:
            lock.release()

    def cancel(self) -> None:
        self._cancelled = True
        self._cancel_pending = True
        # Cancellation never waits on an IPC lock a dead child may have held.
        # The parent fence is immediate; retirement/admission retry a busy flag.
        self.future.cancel()
        self._signal_cancellation()

    def collect(self) -> CPUReply:
        if not self.future.done():
            raise RuntimeError("CPU request has not completed")
        if not self._collected:
            try:
                self.check_active()
                if self._cancelled or self.owner._closed:
                    raise CPURequestCancelled("CPU logical request cancelled")
                reply = self.future.result()
                if reply.request_digest != self.digest or not reply.main_thread:
                    raise ValueError("CPU reply does not match its request/main-thread contract")
                if reply.error_type is not None:
                    kind = {
                        "ValueError": ValueError,
                        "ValidationError": ValueError,
                        "TimeoutError": TimeoutError,
                        "CapacityExceeded": CapacityExceeded,
                        "CPURequestCancelled": CPURequestCancelled,
                    }.get(reply.error_type, RuntimeError)
                    raise kind(reply.error_message)
                if len(reply.content) > self.owner.policy.max_reply_bytes:
                    raise CapacityExceeded("CPU reply exceeds admitted capacity")
                self.owner.native_thread_reports[reply.pid] = dict(
                    threads=reply.native_thread_limit, pools=reply.native_pools
                )
                self._reply = reply
            except BaseException as error:
                self._error = error
                self.cancel()
            finally:
                self._collected = True
                retained = (
                    0
                    if self._reply is None
                    else len(self._reply.content) + len(self._reply.cost or b"")
                )
                self.owner._collected(self.admission, retained)
        if self._error is not None:
            raise self._error
        if self._cancelled:
            raise CPURequestCancelled("CPU logical request cancelled")
        assert self._reply is not None
        return self._reply

    def retire(self) -> bool:
        self._signal_cancellation()
        if self.owner._closed and not self.owner._physical_retired:
            return False
        if not self.future.done():
            return False
        if not self._collected:
            with suppress(BaseException):
                self.collect()
        self.owner.release_admission(self.admission)
        self.owner._handles.discard(self)
        return True


_COOPERATIVE_CLOSE_SECONDS = 5.0
_WORKER_EXIT_SECONDS = 5.0


@dataclass
class _PoolOwnership:
    """CPython 3.14's actual worker registry, retained across public shutdown.

    _spawn_worker receives this same dictionary before Process.start(), then adds
    the started Process to it. Retaining the dictionary, rather than a snapshot,
    keeps a concurrent spawn owned even after shutdown clears executor attributes.
    No worker recycling is selected. Native locks/state stay inside this adapter.
    """

    registry: dict[int, Any]
    manager: threading.Thread | None
    retired: bool = False

    @property
    def processes(self) -> tuple[Any, ...]:
        return tuple(self.registry.values())

    @classmethod
    def capture(cls, pool: ProcessPoolExecutor) -> _PoolOwnership:
        native = cast(Any, pool)
        registry = native._processes
        if registry is None:
            raise RuntimeError("CPU worker ownership must be captured before shutdown")
        return cls(registry, native._executor_manager_thread)

    def shutdown(
        self,
        pool: ProcessPoolExecutor,
        handles: Callable[[], tuple[CPUHandle, ...]],
        submissions: tuple[threading.Event, ...],
        companions: tuple[threading.Thread, ...],
        deadline: float,
    ) -> None:
        def pending():
            return any(not event.is_set() for event in submissions) or any(
                not handle.future.done() for handle in handles()
            )

        while pending() and monotonic() < deadline:
            threading.Event().wait(min(0.05, max(0, deadline - monotonic())))
        forceful = pending()
        failures: list[BaseException] = []
        finished = threading.Event()

        def shutdown_pool():
            try:
                native = cast(Any, pool)
                with native._shutdown_lock:
                    # Match shutdown's native admission fence before capturing
                    # its manager. A queued submit must not create a new manager
                    # between capture and the public API discarding that handle.
                    native._shutdown_thread = True
                    self.manager = native._executor_manager_thread or self.manager
                if forceful:
                    pool.kill_workers()
                else:
                    pool.shutdown(wait=False, cancel_futures=True)
            except BaseException as error:
                failures.append(error)
            finally:
                finished.set()

        # A broken manager holds the native shutdown lock while joining siblings
        # that may ignore SIGTERM. Keep public shutdown/kill off the caller, and
        # keep the live registry available while native submissions unblock.
        closer = threading.Thread(target=shutdown_pool, name="cpu-pool-close", daemon=True)
        closer.start()

        def join_until(owners, until):
            for owner in owners:
                try:
                    owner.join(max(0, until - monotonic()))
                except BaseException as error:
                    failures.append(error)

        finished.wait(max(0, deadline - monotonic()))
        join_until(self.processes, deadline)
        if self.manager is not None:
            join_until((self.manager,), deadline)

        # Never chain terminate_workers then kill_workers: the first API erases
        # executor ownership. Kill actual owned Process handles, including any
        # late insertion by an already-started native submission. The total
        # grace/death deadline includes native and scope lock acquisition.
        exit_deadline = deadline + _WORKER_EXIT_SECONDS
        while True:
            for process in self.processes:
                try:
                    if process.is_alive():
                        process.kill()
                except ProcessLookupError:
                    pass
                except BaseException as error:
                    failures.append(error)
            interval = min(exit_deadline, monotonic() + 0.05)
            join_until(self.processes, interval)
            if self.manager is not None:
                join_until((self.manager,), interval)
            join_until((closer, *companions), interval)
            living = tuple(process.pid for process in self.processes if process.is_alive())
            if (
                not living
                and all(event.is_set() for event in submissions)
                and (self.manager is None or not self.manager.is_alive())
                and finished.is_set()
                and not closer.is_alive()
                and not any(thread.is_alive() for thread in companions)
            ):
                self.retired = True
                break
            if monotonic() >= exit_deadline:
                unsettled = sum(not event.is_set() for event in submissions)
                live_threads = tuple(
                    thread.name for thread in (closer, *companions) if thread.is_alive()
                )
                failures.append(
                    RuntimeError(
                        f"CPU shutdown could not confirm physical retirement; live PIDs {living}; "
                        f"unfinished submissions/signals {unsettled}; "
                        f"live cleanup threads {live_threads}"
                    )
                )
                break
            threading.Event().wait(min(0.01, max(0, exit_deadline - monotonic())))
        if failures:
            raise BaseExceptionGroup("CPU pool shutdown failed", failures)


def _report_cleanup_failure(error: BaseException) -> None:
    primary = sys.exception()
    if primary is not None and primary is not error:
        primary.add_note(f"CPU cleanup also failed: {error!r}")
    else:
        raise error


class CPUExecutionScope:
    def __init__(
        self, prepared: PreparedRelease, policy: CharacterizationExecutionPolicy | None = None
    ):
        self.prepared = prepared
        self.policy = policy or CharacterizationExecutionPolicy()
        self.budget = OwnedByteBudget(self.policy.max_owned_bytes)
        self._pool: ProcessPoolExecutor | None = None
        self._pool_ownership: _PoolOwnership | None = None
        self._submissions: set[threading.Event] = set()
        self._context = multiprocessing.get_context("spawn")
        self._stop = self._context.Event()
        self._cancellation = self._context.Array("q", self.policy.max_submissions * 2, lock=True)
        self._lock = threading.RLock()
        self._closed = False
        self._close_lock = threading.Lock()
        self._close_finished = False
        self._close_error: BaseException | None = None
        self._physical_retired = False
        self._capsule_bytes = 0
        self._free = list(range(self.policy.max_submissions))
        self._admissions: dict[int, _InputAdmission] = {}
        self._handles: set[CPUHandle] = set()
        self.native_thread_reports: dict[int, dict[str, Any]] = {}

    def _executor(self):
        with self._lock:
            if self._closed:
                raise RuntimeError("CPU invocation is closed")
            if self._pool is None:
                capsule = release_capsule(self.prepared)
                self.budget.reserve(len(capsule))
                self._capsule_bytes = len(capsule)
                self._pool = ProcessPoolExecutor(
                    max_workers=self.policy.workers,
                    mp_context=self._context,
                    initializer=_initialize,
                    initargs=(
                        capsule,
                        self._stop,
                        self._cancellation,
                        self.policy.cpu_native_threads,
                    ),
                )
                self._pool_ownership = _PoolOwnership.capture(self._pool)
            return self._pool

    def try_admit(self, check_active: Callable[[], None] = lambda: None) -> _InputAdmission | None:
        check_active()
        for handle in tuple(self._handles):
            if handle._cancelled:
                handle.retire()
        with self._lock:
            if self._closed:
                raise RuntimeError("CPU invocation is closed")
            if not self._free:
                return None
            self._executor()
            size = self.policy.max_packet_bytes + self.policy.max_reply_bytes
            if size + self._capsule_bytes > self.policy.max_owned_bytes:
                raise CapacityExceeded(
                    "CPU policy cannot hold preparation and one complete request"
                )
            try:
                self.budget.reserve(size)
            except CapacityExceeded:
                return None
            lock = self._cancellation.get_lock()
            if not lock.acquire(timeout=0.1):
                self.budget.release(size)
                raise RuntimeError("CPU cancellation state did not become available")
            try:
                slot = self._free.pop(0)
                flags = self._cancellation.get_obj()
                flags[slot * 2] += 1
                generation = flags[slot * 2]
                flags[slot * 2 + 1] = 0
            finally:
                lock.release()
            permit = _InputAdmission(self, slot, generation, size)
            self._admissions[id(permit)] = permit
            return permit

    def _collected(self, permit, retained):
        with self._lock:
            if not permit.active or (self._closed and not self._physical_retired):
                return
            self.budget.release(permit.reserved - retained)
            permit.reserved = retained
            permit.active = False
            self._free.append(permit.slot)

    def release_admission(self, permit) -> None:
        with self._lock:
            if permit.owner is not self:
                raise ValueError("CPU input admission belongs to another invocation")
            if permit.retired:
                return
            if permit.submitted and permit.active:
                raise RuntimeError("CPU request must drain before retiring admission")
            if permit.active:
                permit.active = False
                self._free.append(permit.slot)
            self.budget.release(permit.reserved)
            permit.reserved = 0
            permit.retired = True
            self._admissions.pop(id(permit), None)

    def submit(
        self,
        admission,
        content: bytes,
        releases: Mapping[str, PreparedRelease],
        check_active: Callable[[], None] = lambda: None,
    ) -> CPUHandle:
        check_active()
        if admission.owner is not self or not admission.active or admission.submitted:
            raise ValueError("CPU input admission is not active for this invocation")
        capsules = tuple(
            release_capsule(value)
            for key, value in releases.items()
            if key != self.prepared.release_id
        )
        if len(content) + sum(map(len, capsules)) > self.policy.max_packet_bytes:
            self.release_admission(admission)
            raise CapacityExceeded("CPU input exceeds admitted packet byte capacity")
        with self._lock:
            pool = self._executor()
            if not admission.active or admission.submitted:
                raise ValueError("CPU input admission is no longer active")
            submitted = threading.Event()
            self._submissions.add(submitted)
            admission.submitted = True
        # Native submit can fail after enqueuing its packet but before returning
        # a future. Its admission stays owned until physical teardown is proven.
        try:
            # The native executor lock may be held by broken-pool cleanup. Never
            # keep the invocation lock while entering that potentially wedged API.
            future = pool.submit(
                _dispatch,
                content,
                capsules,
                self.policy.max_reply_bytes,
                admission.slot,
                admission.generation,
            )
            with self._lock:
                handle = CPUHandle(
                    self, admission, future, sha256(content).hexdigest(), check_active
                )
                handle._cancelled = self._closed
                self._handles.add(handle)
                closed = self._closed
            if closed:
                future.cancel()
                raise CPURequestCancelled("CPU invocation closed during submission")
            return handle
        finally:
            with self._lock:
                submitted.set()
                self._submissions.discard(submitted)

    def collect(
        self, handle: CPUHandle, check_active: Callable[[], None] = lambda: None
    ) -> CPUReply | None:
        check_active()
        return handle.collect() if handle.future.done() else None

    def retire(self, handle: CPUHandle) -> bool:
        return handle.retire()

    def cancel(self, handle: CPUHandle) -> None:
        handle.cancel()

    @contextmanager
    def admitted_inputs(self, check_active: Callable[[], None]) -> Generator[_InputAdmission]:
        permit = None
        try:
            while permit is None:
                permit = self.try_admit(check_active)
                if permit is None:
                    threading.Event().wait(0.1)
            yield permit
        finally:
            if permit is not None and not permit.submitted:
                self.release_admission(permit)

    @contextmanager
    def execute(
        self,
        content: bytes,
        releases: Mapping[str, PreparedRelease],
        check_active: Callable[[], None],
        *,
        admission=None,
    ) -> Generator[CPUReply]:
        if admission is None:
            with (
                self.admitted_inputs(check_active) as owned,
                self.execute(content, releases, check_active, admission=owned) as reply,
            ):
                yield reply
            return
        handle = self.submit(admission, content, releases, check_active)
        try:
            while not handle.future.done():
                check_active()
                if self._closed:
                    raise RuntimeError("CPU invocation is closed")
                with suppress(TimeoutError):
                    handle.future.result(timeout=0.1)
            yield handle.collect()
        except BaseException:
            handle.cancel()
            raise
        finally:
            handle.retire()

    def abort(self) -> None:
        self.close()

    def close(self) -> None:
        deadline = monotonic() + _COOPERATIVE_CLOSE_SECONDS
        if not self._close_lock.acquire(timeout=_COOPERATIVE_CLOSE_SECONDS + _WORKER_EXIT_SECONDS):
            _report_cleanup_failure(RuntimeError("CPU close owner did not finish before deadline"))
            return
        try:
            if not self._close_finished:
                failures: list[BaseException] = []
                self._closed = True
                locked = self._lock.acquire(timeout=max(0, deadline - monotonic()))
                try:
                    # Capture even if a scope operation is wedged: its native
                    # pool registry was retained before any worker could start.
                    handles = tuple(self._handles)
                    submissions = tuple(self._submissions)
                    pool, ownership = self._pool, self._pool_ownership
                    if not locked:
                        failures.append(
                            RuntimeError("CPU scope lock did not drain before deadline")
                        )
                finally:
                    if locked:
                        self._lock.release()
                # Parent fences do not acquire IPC locks. A worker can die
                # holding the shared Event/Array lock, so cooperative signalling
                # itself must not hold up forceful cleanup or its deadline.
                for handle in handles:
                    handle._cancelled = True
                signalled = threading.Event()

                def signal_stop():
                    try:
                        self._stop.set()
                    except BaseException as error:
                        failures.append(error)
                    try:
                        for handle in handles:
                            try:
                                handle.cancel()
                            except BaseException as error:
                                failures.append(error)
                    finally:
                        signalled.set()

                signaler = threading.Thread(target=signal_stop, name="cpu-pool-stop", daemon=True)
                signaler.start()
                if pool is not None and ownership is not None:
                    try:
                        ownership.shutdown(
                            pool,
                            lambda: tuple(self._handles),
                            (*submissions, signalled),
                            (signaler,),
                            deadline,
                        )
                    except BaseException as error:
                        failures.append(error)
                    if ownership.retired:
                        self._physical_retired = True
                        self._pool = None
                else:
                    signaler.join(max(0, deadline + _WORKER_EXIT_SECONDS - monotonic()))
                    self._physical_retired = not signaler.is_alive()
                    if not self._physical_retired:
                        failures.append(
                            RuntimeError("CPU stop signalling did not finish before deadline")
                        )
                if self._physical_retired and locked:
                    # Native submissions finished before retirement was proven,
                    # so include the handles they registered during close.
                    for permit in self._admissions.values():
                        permit.submitted = False
                    # Discarding close must not call collect/check_active or
                    # validate a result with no remaining consumer.
                    self._handles.clear()
                    for permit in tuple(self._admissions.values()):
                        try:
                            self.release_admission(permit)
                        except BaseException as error:
                            failures.append(error)
                    if self._capsule_bytes:
                        try:
                            self.budget.release(self._capsule_bytes)
                        except BaseException as error:
                            failures.append(error)
                        else:
                            self._capsule_bytes = 0
                if failures:
                    self._close_error = BaseExceptionGroup("CPU cleanup failed", failures)
                self._close_finished = True
            error = self._close_error
        finally:
            self._close_lock.release()
        if error is not None:
            _report_cleanup_failure(error)


def cpu_method_plan(method, units, cfg, ctx):
    """Prepare only after admission; yielding private work never blocks the coordinator."""
    from corpus_structure.core._model.shapes import Cost
    from corpus_structure.core.method import PreparedWork, UnitResult
    from corpus_structure.core.vocab import ObservationOutcome

    _base, scope, pins = cfg.require_selection()
    results = []
    owned = []
    try:
        for unit in units:
            ctx.check_active()
            if unit.ref not in method.select(unit.run, cfg):
                raise ValueError("CPU task unit differs from exact selected document")
            reader = unit.run.reader
            operation = dict(ctx.characterization_operation(unit.ref))
            if any(
                operation.get(k) != v
                for k, v in dict(
                    key=method.name,
                    version=method.version,
                    model=cfg.model,
                    grammar=cfg.grammar,
                    context=cfg.context,
                ).items()
            ):
                raise ValueError("CPU task determinants differ from its frozen configuration")
            execution = getattr(reader, "cpu_execution", None)
            if execution is None:
                execution = CPUExecutionScope(
                    reader.prepared, getattr(ctx.settings, "execution_policy", None)
                )
                owned.append(execution)
            prepared_inputs = {}
            executor = cast(CPUExecutionScope, execution)

            def try_submit(
                executor=executor,
                reader=reader,
                unit=unit,
                operation=operation,
                prepared_inputs=prepared_inputs,
            ):
                admission = executor.try_admit(ctx.check_active)
                if admission is None:
                    return None
                try:
                    layers, pending = {}, pins
                    while pending:
                        ctx.check_active()
                        read = reader.characterization_layers(pending)
                        if set(read) != set(pending):
                            raise ValueError("CPU input requires complete exact dependency closure")
                        layers.update(read)
                        pending = tuple(
                            dict.fromkeys(
                                ProductReference(**p)
                                for report in read.values()
                                for p in report.payload["dependencies"]
                                if ProductReference(**p) not in layers
                            )
                        )
                    releases = {reader.prepared.release_id: reader.prepared}
                    for layer in layers.values():
                        ctx.check_active()
                        identity = layer.payload["release_id"]
                        if identity not in releases:
                            releases[identity] = reader.characterization_release(identity)
                    sources = []
                    for identity in scope["source_view_ids"]:
                        ctx.check_active()
                        view = reader.source_view(identity)
                        sources.append(
                            dict(
                                ref=asdict(view.ref),
                                text=view.text,
                                pieces=view.pieces,
                                items=view.items,
                                ancestors=view.ancestors,
                                health=view.health,
                                text_policy=None
                                if view.text_policy is None
                                else asdict(view.text_policy),
                                analysis_enabled=view.analysis_enabled,
                                integrated_context=view.integrated_context,
                            )
                        )
                    content = canonical_bytes(
                        dict(
                            request_id=uuid4().hex,
                            run_id=getattr(unit.run, "run_id", None),
                            claims=tuple(getattr(ctx.check_active, "active", ())),
                            method=method.name,
                            release_id=reader.prepared.release_id,
                            configuration=cfg.model_dump(mode="json"),
                            operation=operation,
                            document_id=unit.ref.unit_id,
                            sources=sources,
                            dependencies=[
                                dict(pin=asdict(pin), content=layer.content.decode())
                                for pin, layer in layers.items()
                            ],
                        )
                    )
                    prepared_inputs.update(layers=layers, releases=releases)
                    return executor.submit(admission, content, releases, ctx.check_active)
                except BaseException:
                    if not admission.submitted:
                        executor.release_admission(admission)
                    raise

            (reply,) = yield (PreparedWork(try_submit),)
            layers, releases = prepared_inputs["layers"], prepared_inputs["releases"]
            layer = validate_layer(
                reader.prepared,
                json.loads(reply.content),
                dependencies=layers,
                releases=releases,
            )
            payload = layer.payload
            if (
                layer.base_document != _base
                or payload["source_scope"] != scope
                or any(payload["operation"].get(key) != value for key, value in operation.items())
            ):
                raise ValueError("CPU result differs from exact source/operation request")
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    characterization_layer=layer,
                    cost=None if reply.cost is None else Cost.model_validate_json(reply.cost),
                )
            )
        return tuple(results)
    finally:
        failures = []
        for execution in owned:
            try:
                execution.close()
            except BaseException as error:
                failures.append(error)
        if failures:
            _report_cleanup_failure(BaseExceptionGroup("CPU method cleanup failed", failures))


def run_cpu_method(method, units, cfg, ctx):
    from corpus_structure.core.method import drive_prepared_work

    return drive_prepared_work(cpu_method_plan(method, units, cfg, ctx), ctx.check_active)
