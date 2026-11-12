"""Invocation-owned, database-free CPU characterization and bounded owned transfer."""

from __future__ import annotations

import json
import multiprocessing
import threading
from collections.abc import Callable, Generator, Mapping
from concurrent.futures import Future, ProcessPoolExecutor, TimeoutError
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass
from hashlib import sha256
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

    def cancel(self) -> None:
        if self.admission.active:
            with self.owner._cancellation.get_lock():
                offset = self.admission.slot * 2
                if self.owner._cancellation[offset] == self.admission.generation:
                    self.owner._cancellation[offset + 1] = 1
        self._cancelled = True
        self.future.cancel()

    def collect(self) -> CPUReply:
        if not self.future.done():
            raise RuntimeError("CPU request has not completed")
        if not self._collected:
            try:
                self.check_active()
                if self._cancelled:
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
        if not self.future.done():
            return False
        if not self._collected:
            with suppress(BaseException):
                self.collect()
        self.owner.release_admission(self.admission)
        self.owner._handles.discard(self)
        return True


class CPUExecutionScope:
    def __init__(
        self, prepared: PreparedRelease, policy: CharacterizationExecutionPolicy | None = None
    ):
        self.prepared = prepared
        self.policy = policy or CharacterizationExecutionPolicy()
        self.budget = OwnedByteBudget(self.policy.max_owned_bytes)
        self._pool: ProcessPoolExecutor | None = None
        self._context = multiprocessing.get_context("spawn")
        self._stop = self._context.Event()
        self._cancellation = self._context.Array("q", self.policy.max_submissions * 2, lock=True)
        self._lock = threading.RLock()
        self._closed = False
        self._capsule_bytes = 0
        self._free = list(range(self.policy.max_submissions))
        self._admissions: dict[int, _InputAdmission] = {}
        self._handles: set[CPUHandle] = set()
        self.native_thread_reports: dict[int, dict[str, Any]] = {}

    def _executor(self):
        with self._lock:
            if self._closed or self._stop.is_set():
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
            return self._pool

    def try_admit(self, check_active: Callable[[], None] = lambda: None) -> _InputAdmission | None:
        check_active()
        for handle in tuple(self._handles):
            if handle._cancelled and handle.future.done():
                handle.retire()
        with self._lock:
            if self._closed or self._stop.is_set():
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
            slot = self._free.pop(0)
            with self._cancellation.get_lock():
                self._cancellation[slot * 2] += 1
                generation = self._cancellation[slot * 2]
                self._cancellation[slot * 2 + 1] = 0
            permit = _InputAdmission(self, slot, generation, size)
            self._admissions[id(permit)] = permit
            return permit

    def _collected(self, permit, retained):
        with self._lock:
            if not permit.active:
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
        try:
            future = self._executor().submit(
                _dispatch,
                content,
                capsules,
                self.policy.max_reply_bytes,
                admission.slot,
                admission.generation,
            )
        except BaseException:
            self.release_admission(admission)
            raise
        admission.submitted = True
        handle = CPUHandle(self, admission, future, sha256(content).hexdigest(), check_active)
        self._handles.add(handle)
        return handle

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
                if self._closed or self._stop.is_set():
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
        self._stop.set()
        for handle in tuple(self._handles):
            handle.cancel()
        pool = self._pool
        self._pool = None
        if pool is not None:
            pool.terminate_workers()

    def close(self):
        self._closed = True
        self._stop.set()
        for handle in tuple(self._handles):
            handle.cancel()
        pool = self._pool
        self._pool = None
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        for handle in tuple(self._handles):
            handle.retire()
        for permit in tuple(self._admissions.values()):
            if not permit.submitted:
                self.release_admission(permit)
        if self._capsule_bytes:
            self.budget.release(self._capsule_bytes)
            self._capsule_bytes = 0


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
        for execution in owned:
            execution.close()


def run_cpu_method(method, units, cfg, ctx):
    from corpus_structure.core.method import drive_prepared_work

    return drive_prepared_work(cpu_method_plan(method, units, cfg, ctx), ctx.check_active)
