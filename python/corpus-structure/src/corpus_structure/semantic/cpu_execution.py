"""Invocation-owned, database-free CPU characterization and bounded owned transfer."""

from __future__ import annotations

import json
import multiprocessing
import sys
import threading
from collections.abc import Callable, Generator
from concurrent.futures import Future, ProcessPoolExecutor, TimeoutError
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic
from typing import Any, Literal, cast

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

from .archive_reader import reconstruct_release
from .archive_wire import encode_products
from .cpu_receipts import CPUExecutionReceipt
from .identity import canonical_bytes
from .types import PreparationProfile, PreparedArtifact, PreparedRelease, SourceBundle


@dataclass(frozen=True)
class _SealedPacket:
    content: bytes
    digest: str

    @classmethod
    def seal(cls, content: bytes):
        if type(content) is not bytes:
            raise TypeError("owned CPU packets require immutable bytes")
        return cls(content, sha256(content).hexdigest())


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

    def admit(self, size: int) -> OwnedByteReservation:
        """One charged reservation, shareable until every physical owner retires."""
        return OwnedByteReservation(self, size)

    def try_admit(self, size: int) -> OwnedByteReservation | None:
        """Reserve atomically, deferring when other owners still hold capacity."""
        if type(size) is not int or size < 0:
            raise ValueError("owned byte reservation must be nonnegative")
        if size > self.limit:
            raise CapacityExceeded("complete request exceeds owned byte capacity")
        with self._lock:
            if size > self.limit - self.used_bytes:
                return None
            self.used_bytes += size
            return OwnedByteReservation(self, size, state={"leases": 1, "lock": threading.Lock()})

    def release(self, size: int) -> None:
        with self._lock:
            if type(size) is not int or not 0 <= size <= self.used_bytes:
                raise ValueError("owned byte release differs from retained capacity")
            self.used_bytes -= size


class OwnedByteReservation:
    """A lease on one existing budget charge; sharing never reserves twice."""

    def __init__(self, budget: OwnedByteBudget, size: int, *, state=None):
        self.budget, self.size = budget, size
        if state is None:
            budget.reserve(size)
        self._state = state or {"leases": 1, "lock": threading.Lock()}
        self._released = False

    def share(self) -> OwnedByteReservation:
        with self._state["lock"]:
            if self._released:
                raise RuntimeError("owned byte reservation has retired")
            self._state["leases"] += 1
            return OwnedByteReservation(self.budget, self.size, state=self._state)

    def reduce_to(self, size: int) -> None:
        """Return excess stage-A credit while this is its sole physical owner."""
        if type(size) is not int or size < 0:
            raise ValueError("owned byte reservation must be nonnegative")
        with self._state["lock"]:
            if self._released:
                raise RuntimeError("owned byte reservation has retired")
            if self._state["leases"] != 1:
                raise RuntimeError("shared owned byte reservation cannot be reduced")
            if size > self.size:
                raise ValueError("owned byte reservation cannot grow")
            self.budget.release(self.size - size)
            self.size = size

    def release(self) -> None:
        with self._state["lock"]:
            if self._released:
                return
            self._released = True
            self._state["leases"] -= 1
            if self._state["leases"] == 0:
                self.budget.release(self.size)


def release_capsule(prepared: PreparedRelease) -> bytes:
    return canonical_bytes(
        dict(
            products=encode_products(prepared),
            manifest=prepared.manifest.decode(),
            artifacts=[dict(kind=a.kind, content=a.content.hex()) for a in prepared.artifacts],
        )
    )


@dataclass(frozen=True)
class _CapsuleReference:
    name: str
    size: int
    digest: str
    release_id: str


@dataclass
class _SharedCapsule:
    memory: Any
    reference: _CapsuleReference
    prepared: PreparedRelease
    ready: bool = False


def _worker_release(reference: _CapsuleReference):
    """Authenticate one shared archive, then reuse the existing worker release cache."""
    from multiprocessing.shared_memory import SharedMemory

    cache_key = "shared-capsule:" + sha256(canonical_bytes(vars(reference))).hexdigest()
    prepared = _WORKER_RELEASES.get(cache_key)
    if prepared is not None:
        return prepared
    memory = SharedMemory(name=reference.name, track=False)
    try:
        if memory.size != reference.size:
            raise ValueError("CPU shared capsule extent differs from acquired archive")
        buffer = memory.buf
        if buffer is None:
            raise RuntimeError("CPU shared capsule buffer is closed")
        content = bytes(buffer)
    finally:
        memory.close()
    if sha256(content).hexdigest() != reference.digest:
        raise ValueError("CPU shared capsule bytes differ from acquired archive")
    prepared = hydrate_capsule(content)
    if prepared.release_id != reference.release_id:
        raise ValueError("CPU shared capsule differs from the exact admitted release")
    _WORKER_RELEASES[cache_key] = prepared
    return prepared


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


@dataclass(frozen=True)
class CPUReply:
    request_digest: str
    content: bytes
    pid: int
    main_thread: bool
    error_type: str | None = None
    error_message: str | None = None
    native_thread_limit: int | None = None
    native_pools: tuple[dict[str, Any], ...] = ()

    @property
    def execution_receipt(self) -> CPUExecutionReceipt:
        return CPUExecutionReceipt(
            self.request_digest,
            self.pid,
            self.main_thread,
            self.native_thread_limit,
            canonical_bytes(self.native_pools),
            sha256(self.content).hexdigest(),
        )


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


def _initialize(capsule: bytes | None, stop, cancellation=None, native_threads: int = 1) -> None:
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
    _WORKER_RELEASES.clear()
    if capsule is not None:
        prepared = hydrate_capsule(capsule)
        _WORKER_RELEASES[prepared.release_id] = prepared
    _apply_native_thread_limits()
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


def _compute_formal(content: bytes, max_reply_bytes: int, request_digest: str) -> CPUReply:
    """Private prepared target work, never a fabricated legacy task or Reader."""
    import os

    from .formal_evidence import grammar_identity
    from .formal_products import FormalEvidenceOptions, formal_product_values, formal_profile_assets
    from .source_products import FrozenNativeSource

    packet = json.loads(content)
    if (
        not isinstance(packet, dict)
        or not {"profile", "assets", "grammar", "source", "options", "member_contracts"}
        <= packet.keys()
        or packet["profile"] != "formal-source-native"
        or packet["assets"] != formal_profile_assets().digest
        or packet["grammar"] != grammar_identity()
    ):
        raise ValueError("CPU formal packet differs from captured implementation/grammar assets")
    # This is private owned transport from an acquired parent, not external ingress.
    # Schema/source/model admission and full typed result validation stay there.
    source = FrozenNativeSource(packet["source"].encode())
    options = FormalEvidenceOptions.model_validate_json(packet["options"])
    _apply_native_thread_limits()
    content_value = formal_product_values(
        source, options, packet["member_contracts"], check_active=_worker_active
    )
    result = canonical_bytes(content_value)
    if len(result) > max_reply_bytes:
        raise CapacityExceeded("CPU formal result exceeds admitted reply byte capacity")
    _worker_active()
    return CPUReply(
        request_digest,
        result,
        os.getpid(),
        threading.current_thread() is threading.main_thread(),
        native_thread_limit=_WORKER_NATIVE_THREADS,
        native_pools=_WORKER_NATIVE_POOLS,
    )


def _dispatch(
    packet: _SealedPacket,
    max_reply_bytes: int,
    slot: int,
    generation: int,
    profile: Literal["formal-source-native", "closed-python", "closed-python-stream"],
    stream_connection=None,
    capsule: _CapsuleReference | None = None,
) -> CPUReply:
    import os

    content, request_digest = packet.content, packet.digest
    global _WORKER_REQUEST
    _WORKER_REQUEST = None if slot < 0 else (slot, generation)
    releases = _WORKER_RELEASES
    try:
        _worker_active()
        if capsule is not None:
            prepared = _worker_release(capsule)
            releases = {prepared.release_id: prepared}
        if profile == "formal-source-native":
            return _compute_formal(content, max_reply_bytes, request_digest)
        if profile in {"closed-python", "closed-python-stream"}:
            from .data_operation_cpu import execute_python_call

            _apply_native_thread_limits()
            if profile == "closed-python-stream":
                from .data_operation_cpu import execute_python_stream

                result = execute_python_stream(
                    content,
                    stream_connection,
                    _worker_active,
                    _apply_native_thread_limits,
                    max_reply_bytes,
                    {"slot": slot, "generation": generation},
                    prepared_releases=releases,
                    request_digest=request_digest,
                )
            else:
                result = execute_python_call(
                    content,
                    _worker_active,
                    _apply_native_thread_limits,
                    prepared_releases=releases,
                )
            if len(result) > max_reply_bytes:
                raise CapacityExceeded("CPU Python result exceeds admitted reply byte capacity")
            return CPUReply(
                request_digest,
                result,
                os.getpid(),
                threading.current_thread() is threading.main_thread(),
                native_thread_limit=_WORKER_NATIVE_THREADS,
                native_pools=_WORKER_NATIVE_POOLS,
            )
        raise ValueError("CPU dispatch has no admitted source-native profile")
    except Exception as error:
        return CPUReply(
            request_digest,
            b"",
            os.getpid(),
            True,
            type(error).__name__,
            str(error)[:2048],
            native_thread_limit=_WORKER_NATIVE_THREADS,
            native_pools=_WORKER_NATIVE_POOLS,
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
    reservation: OwnedByteReservation | None = None


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
                retained = 0 if self._reply is None else len(self._reply.content)
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


class _ReleaseCPUView:
    """Exact per-call capsule on the invocation's existing pool and byte owner."""

    def __init__(self, scope, capsule, prepared):
        self.scope, self.capsule, self.prepared = scope, capsule, prepared

    def __getattr__(self, name):
        return getattr(self.scope, name)

    def submit_closed_python(self, admission, content, check_active):
        return self.scope._submit(
            admission, content, check_active, "closed-python", capsule=self.capsule
        )

    def submit_closed_python_stream(self, admission, content, connection, check_active):
        return self.scope._submit(
            admission,
            content,
            check_active,
            "closed-python-stream",
            connection,
            capsule=self.capsule,
        )


class CPUExecutionScope:
    def __init__(
        self,
        prepared: PreparedRelease,
        policy: CharacterizationExecutionPolicy | None = None,
        *,
        budget: OwnedByteBudget | None = None,
        retain_schema: bool = True,
    ):
        self.prepared = prepared
        self.retain_schema = retain_schema
        self.policy = policy or CharacterizationExecutionPolicy()
        self.budget = budget or OwnedByteBudget(self.policy.max_owned_bytes)
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
        self._release_capsules = {}
        self._free = list(range(self.policy.max_submissions))
        self._admissions: dict[int, _InputAdmission] = {}
        self._handles: set[CPUHandle] = set()
        self._stream_transports = set()
        self._submission_uncertain = False
        self.native_thread_reports: dict[int, dict[str, Any]] = {}

    def _executor(self):
        with self._lock:
            if self._closed or self._submission_uncertain:
                raise RuntimeError("CPU invocation is closed or retains uncertain submission")
            if self._pool is None:
                capsule = release_capsule(self.prepared) if self.retain_schema else None
                size = 0 if capsule is None else len(capsule)
                self.budget.reserve(size)
                self._capsule_bytes += size
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

    def prepare(self) -> None:
        """Retain the one schema capsule before request credits consume capacity."""
        self._executor()

    def for_release(
        self, prepared: PreparedRelease, *, request_bytes: int | None = None, capsule_bytes: bytes | None = None
    ):
        """Retain one shared archive; submit only its bounded authenticated descriptor."""
        from multiprocessing.shared_memory import SharedMemory

        with self._lock:
            if self._closed:
                raise RuntimeError("CPU invocation is closed")
            owned = self._release_capsules.get(prepared.release_id)
            if owned is None:
                content = release_capsule(prepared) if capsule_bytes is None else capsule_bytes
                size = len(content)
                required = (
                    self.policy.max_packet_bytes + self.policy.max_reply_bytes
                    if request_bytes is None
                    else request_bytes
                )
                if self._capsule_bytes + size + required > self.policy.max_owned_bytes:
                    del content
                    raise CapacityExceeded(
                        "native preparation and one complete request exceed owned capacity"
                    )
                # The temporary serialized buffer and native block coexist during
                # transfer. Both are owned until that copy has completed.
                try:
                    self.budget.reserve(size)
                except BaseException:
                    del content
                    raise
                try:
                    self.budget.reserve(size)
                    try:
                        memory = SharedMemory(create=True, size=size)
                    except BaseException:
                        self.budget.release(size)
                        raise
                    reference = _CapsuleReference(
                        memory.name, memory.size, sha256(content).hexdigest(), prepared.release_id
                    )
                    owned = _SharedCapsule(memory, reference, prepared)
                    self._release_capsules[prepared.release_id] = owned
                    self._capsule_bytes += memory.size
                    buffer = memory.buf
                    if buffer is None:
                        raise RuntimeError("CPU shared capsule buffer closed during preparation")
                    buffer[:] = content
                    owned.ready = True
                finally:
                    del content
                    self.budget.release(size)
            if owned.prepared is not prepared and sha256(release_capsule(prepared)).hexdigest() != owned.reference.digest:
                raise ValueError("CPU release capsule differs under its retained identity")
            if not owned.ready:
                raise RuntimeError("CPU shared capsule preparation did not complete")
            return _ReleaseCPUView(self, owned.reference, prepared)

    @property
    def preparation_bytes(self) -> int:
        """The invocation's fixed retained capsule charge, excluding request leases."""
        return self._capsule_bytes

    def reservation_retired(self, reservation: OwnedByteReservation) -> bool:
        """Submission errors do not prove that an accepted CPU request retired."""
        with self._lock:
            return not any(
                permit.reservation is not None
                and permit.reservation._state is reservation._state
                and not permit.retired
                for permit in self._admissions.values()
            )

    def try_admit(
        self,
        check_active: Callable[[], None] = lambda: None,
        *,
        reservation: OwnedByteReservation | None = None,
        packet_bytes: int | None = None,
    ) -> _InputAdmission | None:
        if packet_bytes is None:
            packet_bytes = self.policy.max_packet_bytes
        if type(packet_bytes) is not int or not 0 <= packet_bytes <= self.policy.max_packet_bytes:
            raise CapacityExceeded("CPU input exceeds admitted packet byte capacity")
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
            size = packet_bytes + self.policy.max_reply_bytes
            if size + self._capsule_bytes > self.policy.max_owned_bytes:
                raise CapacityExceeded(
                    "CPU policy cannot hold preparation and one complete request"
                )
            shared = None
            if reservation is None:
                try:
                    self.budget.reserve(size)
                except CapacityExceeded:
                    return None
            else:
                if reservation.budget is not self.budget or reservation.size < size:
                    raise ValueError(
                        "CPU request requires its existing complete shared byte credit"
                    )
                shared = reservation.share()
            lock = self._cancellation.get_lock()
            if not lock.acquire(timeout=0.1):
                if shared is None:
                    self.budget.release(size)
                else:
                    shared.release()
                raise RuntimeError("CPU cancellation state did not become available")
            try:
                slot = self._free.pop(0)
                flags = self._cancellation.get_obj()
                flags[slot * 2] += 1
                generation = flags[slot * 2]
                flags[slot * 2 + 1] = 0
            finally:
                lock.release()
            permit = _InputAdmission(self, slot, generation, size, reservation=shared)
            self._admissions[id(permit)] = permit
            return permit

    def _collected(self, permit, retained):
        with self._lock:
            if not permit.active or (self._closed and not self._physical_retired):
                return
            if permit.reservation is None:
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
            if permit.reservation is None:
                self.budget.release(permit.reserved)
            else:
                permit.reservation.release()
            permit.reserved = 0
            permit.retired = True
            self._admissions.pop(id(permit), None)

    def submit_formal(
        self, admission, content: bytes, check_active: Callable[[], None] = lambda: None
    ) -> CPUHandle:
        return self._submit(admission, content, check_active, "formal-source-native")

    def submit_closed_python(
        self, admission, content: bytes, check_active: Callable[[], None] = lambda: None
    ) -> CPUHandle:
        return self._submit(admission, content, check_active, "closed-python")

    def submit_closed_python_stream(self, admission, content, connection, check_active):
        return self._submit(admission, content, check_active, "closed-python-stream", connection)

    def _submit(
        self, admission, content, check_active, profile, stream_connection=None, *, capsule=None
    ) -> CPUHandle:
        check_active()
        if admission.owner is not self or not admission.active or admission.submitted:
            raise ValueError("CPU input admission is not active for this invocation")
        if (len(content) > self.policy.max_packet_bytes
            or len(content) + self.policy.max_reply_bytes > admission.reserved):
            self.release_admission(admission)
            raise CapacityExceeded("CPU input exceeds admitted packet byte capacity")
        packet = _SealedPacket.seal(content)
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
                packet,
                self.policy.max_reply_bytes,
                admission.slot,
                admission.generation,
                profile,
                stream_connection,
                capsule,
            )
            with self._lock:
                handle = CPUHandle(self, admission, future, packet.digest, check_active)
                handle._cancelled = self._closed
                self._handles.add(handle)
                closed = self._closed
            if closed:
                future.cancel()
                raise CPURequestCancelled("CPU invocation closed during submission")
            return handle
        except BaseException:
            self._submission_uncertain = True
            raise
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
                if self._physical_retired:
                    for transport in tuple(self._stream_transports):
                        if transport.drain_transport(monotonic() + _WORKER_EXIT_SECONDS):
                            self._stream_transports.discard(transport)
                        else:
                            self._physical_retired = False
                            failures.append(RuntimeError("CPU stream transport did not drain"))
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
                    for release_id, capsule in tuple(self._release_capsules.items()):
                        try:
                            capsule.memory.close()
                            capsule.memory.unlink()
                        except BaseException as error:
                            self._physical_retired = False
                            failures.append(error)
                        else:
                            self.budget.release(capsule.reference.size)
                            self._capsule_bytes -= capsule.reference.size
                            del self._release_capsules[release_id]
                    if self._capsule_bytes and not self._release_capsules:
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
