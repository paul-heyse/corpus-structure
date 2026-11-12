"""Invocation-owned, database-free CPU characterization and bounded owned transfer."""

from __future__ import annotations

import json
import multiprocessing
import threading
from collections.abc import Callable, Generator, Mapping
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

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


@dataclass(frozen=True)
class CPUExecutionPolicy:
    workers: int = 1
    max_submissions: int = 1
    max_owned_bytes: int = 256 * 1024**2
    max_packet_bytes: int = 64 * 1024**2
    max_reply_bytes: int = 8 * 1024**2

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in asdict(self).values()):
            raise ValueError("CPU policy requires positive finite integer bounds")
        if self.max_packet_bytes + self.max_reply_bytes > self.max_owned_bytes:
            raise ValueError("CPU transfer bounds exceed combined owned-state capacity")


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


def _initialize(capsule: bytes, stop) -> None:
    global _WORKER_STOP
    prepared = hydrate_capsule(capsule)
    _WORKER_RELEASES.clear()
    _WORKER_RELEASES[prepared.release_id] = prepared
    _WORKER_STOP = stop


def _worker_active() -> None:
    if _WORKER_STOP is not None and _WORKER_STOP.is_set():
        raise RuntimeError("CPU invocation cancelled")


def _compute(content: bytes, capsules: tuple[bytes, ...], max_reply_bytes: int) -> CPUReply:
    import os

    from corpus_structure.core.method import MethodContext, SourceRunContext
    from corpus_structure.methods.construction_characterization import (
        ConstructionCharacterizationMethod,
    )
    from corpus_structure.methods.contextual_interpretation import ContextualInterpretationMethod
    from corpus_structure.methods.formal_evidence import FormalEvidenceMethod

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
    )


def _dispatch(content: bytes, capsules: tuple[bytes, ...], max_reply_bytes: int) -> CPUReply:
    import os

    try:
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
    active: bool = True


class CPUExecutionScope:
    def __init__(self, prepared: PreparedRelease, policy: CPUExecutionPolicy | None = None):
        self.prepared = prepared
        self.policy = policy or CPUExecutionPolicy()
        self.budget = OwnedByteBudget(self.policy.max_owned_bytes)
        self._pool: ProcessPoolExecutor | None = None
        self._context = multiprocessing.get_context("spawn")
        self._stop = self._context.Event()
        self._slots = threading.BoundedSemaphore(self.policy.max_submissions)
        self._closed = False
        self._capsule_bytes = 0
        self._lock = threading.Lock()
        self._admission = threading.Condition()
        self._active_transfers = 0

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
                    initargs=(capsule, self._stop),
                )
            return self._pool

    @contextmanager
    def admitted_inputs(self, check_active: Callable[[], None]) -> Generator[_InputAdmission]:
        """Admit before hydration; reserve full packet/reply capacity through consumption."""
        acquired = False
        reserved = False
        permit = _InputAdmission(self)
        reservation = self.policy.max_packet_bytes + self.policy.max_reply_bytes
        try:
            while not self._slots.acquire(timeout=0.1):
                check_active()
                if self._closed or self._stop.is_set():
                    raise RuntimeError("CPU invocation is closed")
            acquired = True
            check_active()
            self._executor()
            with self._admission:
                while True:
                    check_active()
                    if self._closed or self._stop.is_set():
                        raise RuntimeError("CPU invocation is closed")
                    try:
                        self.budget.reserve(reservation)
                        break
                    except CapacityExceeded:
                        if not self._active_transfers:
                            raise
                        self._admission.wait(timeout=0.1)
                self._active_transfers += 1
                reserved = True
            yield permit
        except BaseException:
            self._stop.set()
            raise
        finally:
            permit.active = False
            if reserved:
                with self._admission:
                    self.budget.release(reservation)
                    self._active_transfers -= 1
                    self._admission.notify_all()
            if acquired:
                self._slots.release()

    @contextmanager
    def execute(
        self,
        content: bytes,
        releases: Mapping[str, PreparedRelease],
        check_active: Callable[[], None],
        *,
        admission: _InputAdmission | None = None,
    ) -> Generator[CPUReply]:
        if admission is None:
            with (
                self.admitted_inputs(check_active) as owned,
                self.execute(content, releases, check_active, admission=owned) as reply,
            ):
                yield reply
            return
        if admission.owner is not self or not admission.active:
            raise ValueError("CPU input admission is not active for this invocation")
        capsules = tuple(
            release_capsule(value)
            for key, value in releases.items()
            if key != self.prepared.release_id
        )
        packet_size = len(content) + sum(map(len, capsules))
        if packet_size > self.policy.max_packet_bytes:
            raise CapacityExceeded("CPU input exceeds admitted packet byte capacity")
        future = None
        try:
            check_active()
            pool = self._executor()
            future = pool.submit(_dispatch, content, capsules, self.policy.max_reply_bytes)
            while True:
                check_active()
                if self._closed or self._stop.is_set():
                    raise RuntimeError("CPU invocation is closed")
                try:
                    reply = future.result(timeout=0.1)
                    break
                except TimeoutError:
                    if future.done():
                        raise
                    continue
            check_active()
            if reply.request_digest != sha256(content).hexdigest() or not reply.main_thread:
                raise ValueError("CPU reply does not match its request/main-thread contract")
            if reply.error_type is not None:
                error_class = {
                    "ValueError": ValueError,
                    "ValidationError": ValueError,
                    "TimeoutError": TimeoutError,
                    "CapacityExceeded": CapacityExceeded,
                }.get(reply.error_type, RuntimeError)
                raise error_class(reply.error_message)
            if len(reply.content) > self.policy.max_reply_bytes:
                raise CapacityExceeded("CPU reply exceeds admitted capacity")
            yield reply
        except BaseException:
            self._stop.set()
            if self._pool is not None:
                if future is not None:
                    future.cancel()
                    with suppress(BaseException):
                        future.result(timeout=2.0)
                self._pool.terminate_workers()
                self._pool = None
            raise

    def close(self):
        with self._lock:
            self._closed = True
            if self._pool is not None:
                self._pool.shutdown(wait=True, cancel_futures=True)
                self._pool = None
            if self._capsule_bytes:
                self.budget.release(self._capsule_bytes)
                self._capsule_bytes = 0


def run_cpu_method(method, units, cfg, ctx):
    """Authorize/hydrate in parent, compute in child, validate newly authored output in parent."""
    from corpus_structure.core._model.shapes import Cost
    from corpus_structure.core.method import UnitResult
    from corpus_structure.core.vocab import ObservationOutcome

    _base, scope, pins = cfg.require_selection()
    results = []
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
        shared = getattr(reader, "cpu_execution", None)
        execution = shared if shared is not None else CPUExecutionScope(reader.prepared)
        try:
            with execution.admitted_inputs(ctx.check_active) as admitted:
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
                with execution.execute(
                    content, releases, ctx.check_active, admission=admitted
                ) as reply:
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
                        or any(
                            payload["operation"].get(key) != value
                            for key, value in operation.items()
                        )
                    ):
                        raise ValueError("CPU result differs from exact source/operation request")
                    results.append(
                        UnitResult(
                            ref=unit.ref,
                            outcome=ObservationOutcome.PRODUCED,
                            characterization_layer=layer,
                            cost=None
                            if reply.cost is None
                            else Cost.model_validate_json(reply.cost),
                        )
                    )
        finally:
            if shared is None:
                execution.close()
    return tuple(results)
